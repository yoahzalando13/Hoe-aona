"""Collecte, lecture et filtrage des preuves pour une affirmation.

Tous les appels externes passent par la passerelle MCP (`gateway.call`).
"""
from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field

from ..config import Settings
from ..mcp.gateway import ToolGateway
from ..schemas import Evidence, ExcludedSource, Preferences, StatPoint, Statistic
from . import ai_detection, reliability
from .claims import ClaimDraft
from .scoring import rating_to_stance
from .textutils import best_excerpt, domain_of, overlap, split_sentences, truncate

MIN_RELEVANCE = 0.12
MIN_FACTCHECK_RELEVANCE = 0.2


@dataclass
class Candidate:
    origin: str
    url: str
    title: str
    publisher: str = ""
    published_at: str | None = None
    excerpt: str = ""
    image_url: str | None = None
    rating: str | None = None
    author: str | None = None
    relevance: float = 0.0
    ai_probability: float = 0.0
    fetched: bool = False


@dataclass
class Collected:
    evidence: list[Evidence] = field(default_factory=list)
    statistics: list[Statistic] = field(default_factory=list)
    excluded: list[ExcludedSource] = field(default_factory=list)
    tools: set[str] = field(default_factory=set)
    warnings: list[str] = field(default_factory=list)


def _gdelt_date(value: str | None) -> str | None:
    m = re.match(r"(\d{4})(\d{2})(\d{2})", value or "")
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else None


def _note(result: dict, collected: Collected, tool: str) -> list[dict]:
    if result.get("ok"):
        collected.tools.add(tool)
        return result.get("items", [])
    if result.get("error"):
        collected.warnings.append(result["error"])
    return []


async def _fetch_and_enrich(c: Candidate, draft: ClaimDraft, gateway: ToolGateway, sem: asyncio.Semaphore,
                            collected: Collected) -> None:
    async with sem:
        result = await gateway.call("fetch_page", url=c.url)
    pages = _note(result, collected, "fetch_page")
    if not pages:
        return
    page = pages[0]
    c.fetched = True
    excerpt, score = best_excerpt(page.get("paragraphs", []), draft.text)
    if excerpt and score >= c.relevance:
        c.excerpt, c.relevance = excerpt, score
    c.title = c.title or page.get("title") or c.url
    c.publisher = page.get("site_name") or c.publisher
    c.author = page.get("author")
    c.published_at = c.published_at or page.get("published_at")
    c.image_url = c.image_url or page.get("image_url")
    text = page.get("text", "")
    signals = ai_detection.text_signals(text) if len(text) > 600 else ai_detection.AIResult(0.0, [])
    meta = ai_detection.metadata_signals({"generator": page.get("generator")}, "site")
    c.ai_probability = ai_detection.noisy_or([signals.probability, meta.probability])


async def gather(draft: ClaimDraft, gateway: ToolGateway, prefs: Preferences, settings: Settings) -> Collected:
    collected = Collected()
    lang = draft.language if draft.language in {"fr", "en", "mg", "es", "pt", "de"} else "fr"

    calls = {
        # Google Fact Check est désactivé pour ce projet. Les preuves proviennent
        # désormais de Wikipedia, GDELT, Tavily et des données officielles.
        "wikipedia_search": gateway.call("wikipedia_search", query=draft.search_query, language=lang),
        "news_search": gateway.call("news_search", query=draft.search_query_en or draft.search_query),
        "web_search": gateway.call("web_search", query=draft.text),
    }
    if draft.indicator_code:
        calls["worldbank_indicator"] = gateway.call(
            "worldbank_indicator", indicator=draft.indicator_code,
            country=draft.country_iso3 or prefs.default_country)
    results = dict(zip(calls, await asyncio.gather(*calls.values())))

    candidates: dict[str, Candidate] = {}

    def add(c: Candidate) -> None:
        if c.url and c.url not in candidates:
            candidates[c.url] = c

    # Google Fact Check est désactivé : l'ancienne logique a été retirée pour
    # laisser Tavily comme moteur principal de recherche web (voir app/tools/registry.py).
    for item in _note(results["wikipedia_search"], collected, "wikipedia_search"):
        excerpt, score = best_excerpt(split_sentences(item.get("extract", "")) or [item.get("extract", "")], draft.text)
        add(Candidate(
            origin="wikipedia", url=item["url"], title=item.get("title", ""), publisher="Wikipedia",
            published_at=(item.get("last_modified") or "")[:10] or None, image_url=item.get("image_url"),
            excerpt=excerpt or truncate(item.get("extract", ""), 420), relevance=score, fetched=True,
        ))
    for item in _note(results["news_search"], collected, "news_search"):
        add(Candidate(
            origin="news", url=item["url"], title=item.get("title", ""), publisher=item.get("domain", ""),
            published_at=_gdelt_date(item.get("seen_date")), image_url=item.get("image_url"),
            relevance=overlap(draft.text, item.get("title", "")),
        ))
    for item in _note(results["web_search"], collected, "web_search"):
        excerpt, score = best_excerpt([item.get("content", "")], draft.text)
        add(Candidate(
            origin="web", url=item["url"], title=item.get("title", ""), publisher=domain_of(item["url"]),
            published_at=item.get("published_date"), excerpt=excerpt or truncate(item.get("content", ""), 420),
            relevance=score,
        ))

    # Lecture des pages les plus prometteuses : extrait ciblé, auteur, date, image, signatures IA.
    to_fetch = sorted((c for c in candidates.values() if not c.fetched),
                      key=lambda c: (c.origin != "factcheck", -c.relevance))[:settings.max_pages_fetched_per_claim]
    sem = asyncio.Semaphore(4)
    await asyncio.gather(*(_fetch_and_enrich(c, draft, gateway, sem, collected) for c in to_fetch))

    evidences: list[Evidence] = []
    for c in candidates.values():
        if c.ai_probability >= prefs.ai_exclusion_threshold:
            collected.excluded.append(ExcludedSource(
                url=c.url, title=c.title or c.url, ai_probability=c.ai_probability,
                reason=f"Contenu probablement généré par IA ({round(c.ai_probability * 100)} %), exclu du calcul"))
            continue
        if c.relevance < (MIN_FACTCHECK_RELEVANCE if c.origin == "factcheck" else MIN_RELEVANCE):
            continue
        if not c.excerpt:
            continue
        a = reliability.assess(c.url, {"author": c.author, "published_at": c.published_at} if c.fetched else None,
                               c.ai_probability)
        if c.origin != "factcheck" and a.score < prefs.min_source_reliability:
            collected.excluded.append(ExcludedSource(
                url=c.url, title=c.title or c.url, ai_probability=c.ai_probability,
                reason=f"Fiabilité insuffisante ({round(a.score * 100)} %) : {a.reasons[0]}"))
            continue
        # Le verdict d'un fact-check ne s'applique d'emblée que s'il porte clairement sur la même affirmation ;
        # sinon l'évaluation (LLM) décide.
        stance, confidence = ("context", 0.0)
        if c.origin == "factcheck" and c.relevance >= 0.35:
            stance, confidence = rating_to_stance(c.rating)
        evidences.append(Evidence(
            id="", url=c.url, title=truncate(c.title or c.url, 160),
            publisher=c.publisher or domain_of(c.url), domain=domain_of(c.url), origin=c.origin,
            category=a.category, published_at=c.published_at, excerpt=c.excerpt, image_url=c.image_url,
            reliability=a.score, reliability_reasons=a.reasons, relevance=round(c.relevance, 2),
            stance=stance, confidence=confidence, rating=c.rating, ai_probability=c.ai_probability,
        ))

    evidences.sort(key=lambda e: (e.origin != "factcheck", -(0.5 * e.reliability + 0.5 * e.relevance)))
    for i, e in enumerate(evidences[:settings.max_evidence_per_claim], start=1):
        e.id = f"E{i}"
        collected.evidence.append(e)

    if "worldbank_indicator" in results:
        for i, item in enumerate(_note(results["worldbank_indicator"], collected, "worldbank_indicator"), start=1):
            collected.statistics.append(Statistic(
                id=f"S{i}", indicator_code=item["indicator_code"], indicator_name=item["indicator_name"],
                country=item["country"], country_code=item["country_code"], unit=item.get("unit", ""),
                latest_year=item.get("latest_year"), latest_value=item.get("latest_value"),
                series=[StatPoint(**p) for p in item.get("series", [])], claimed_value=draft.claimed_value,
                source_url=item["source_url"], last_updated=item.get("last_updated"),
            ))
    return collected
