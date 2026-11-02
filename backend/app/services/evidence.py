"""Collecte, lecture et filtrage des preuves pour une affirmation.

Sources interrogées, avec une priorité au contexte malgache (public cible) :
- sites officiels et presse nationale malgaches (Tavily limité à ces domaines), presse récente du pays
  (NewsData.io, `country=mg`), presse mondiale (GDELT), web général (Tavily), Wikipedia ;
- statistiques officielles à jour : Banque mondiale et FMI (estimation de l'année en cours) ;
- publications du fil média de la plateforme (lecture directe de la base) ;
- annuaire des sources officielles : contacts à joindre pour confirmer.

Tous les appels externes passent par la passerelle MCP (`gateway.call`).
"""
from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field
from typing import Awaitable, Callable

from urllib.parse import urlparse

from ..config import Settings
from ..db import get_db
from ..mcp.gateway import ToolGateway
from ..schemas import Evidence, ExcludedSource, OfficialContact, Preferences, StatPoint, Statistic
from ..tools import imf
from . import ai_detection, madagascar, reliability
from .claims import ClaimDraft
from .textutils import best_excerpt, domain_of, keywords, overlap, split_sentences, truncate

MIN_RELEVANCE = 0.12
MIN_COMMUNITY_RELEVANCE = 0.25
VERDICT_LABELS = {"fiable": "Fiable", "plutot_fiable": "Plutôt fiable", "a_verifier": "À vérifier", "douteux": "Douteux"}
FOUND_VIA = {
    "wikipedia": "Wikipedia", "news": "Presse (GDELT)", "news_mg": "Presse malgache récente (NewsData.io)",
    "web": "Recherche web (Tavily)", "web_mg": "Sites officiels et presse malgaches (Tavily)",
    "community": "Fil média Hoe-aona?",
    "counter": "Recherche de contre-exemples",
    "implication": "Test par l'absurde (conséquence)",
}


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
    found_via: str = ""
    reliability: float | None = None  # imposée (publications de la plateforme)
    reliability_reasons: list[str] = field(default_factory=list)
    probe: str = ""  # requête de contre-exemple ou de conséquence qui a trouvé la page


@dataclass
class Collected:
    evidence: list[Evidence] = field(default_factory=list)
    statistics: list[Statistic] = field(default_factory=list)
    excluded: list[ExcludedSource] = field(default_factory=list)
    tools: set[str] = field(default_factory=set)
    warnings: list[str] = field(default_factory=list)
    contacts: list[OfficialContact] = field(default_factory=list)
    counter_searched: bool = False  # la recherche de contre-exemples a réellement été exécutée


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
    if c.probe:  # une page de contre-exemple parle souvent du sujet sans reprendre l'affirmation mot pour mot
        alt, alt_score = best_excerpt(page.get("paragraphs", []), f"{draft.text} {c.probe}")
        if alt_score > score:
            excerpt, score = alt, alt_score
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


def _directory_domains(sources: list[dict]) -> set[str]:
    out = set()
    for s in sources:
        host = (urlparse(s.get("website") or "").hostname or "").removeprefix("www.")
        if host:
            out.add(host)
    return out


def match_contacts(text: str, sources: list[dict], has_statistic: bool, limit: int = 3) -> list[OfficialContact]:
    """Institutions de l'annuaire compétentes sur le sujet de l'affirmation (mots-clés de l'annuaire)."""
    low = f" {madagascar.fold(text)} "
    scored = []
    for s in sources:
        hits = [k for k in s.get("topics", []) if f" {madagascar.fold(k)}" in low or madagascar.fold(k) in low.split()]
        acronym = (s.get("acronym") or "").lower()
        if acronym and len(acronym) > 2 and f" {acronym} " in low:
            hits.append(s["acronym"])
        if hits:
            scored.append((len(hits), s, hits))
    if not scored and has_statistic:
        scored = [(1, s, ["statistique"]) for s in sources if (s.get("acronym") or "").upper() == "INSTAT"]
    scored.sort(key=lambda x: -x[0])
    return [OfficialContact(
        id=s["id"], name=s["name"], acronym=s.get("acronym", ""), category=s.get("category", ""),
        website=s.get("website", ""), email=s.get("email", ""), phone=s.get("phone", ""),
        address=s.get("address", ""), verified_at=s.get("verified_at"),
        reason="Compétent sur : " + ", ".join(dict.fromkeys(hits[:4])),
    ) for _, s, hits in scored[:limit]]


def _community_candidates(draft: ClaimDraft) -> list[Candidate]:
    """Publications du fil média proches de l'affirmation : témoignages de rédactions, à recouper."""
    terms = [k for k in keywords(draft.text, 8) if not k.isdigit()]
    out = []
    for row in get_db().search_platform_posts(terms):
        text = " ".join(filter(None, [row.get("analysis_title"), row["body"]]))
        excerpt, score = best_excerpt(split_sentences(row["body"]) or [row["body"]], draft.text)
        score = max(score, overlap(draft.text, text))
        if score < MIN_COMMUNITY_RELEVANCE:
            continue
        rel, reasons = 0.55, [f"Publication d'un membre de la plateforme ({row['author_organization'] or 'personnel média'})"]
        rating = None
        if row.get("analysis_verdict"):
            rel += 0.1
            rating = f"{VERDICT_LABELS.get(row['analysis_verdict'], row['analysis_verdict'])} " \
                     f"({str(round(row['analysis_score'] or 0, 1)).replace('.', ',')}/10)"
            reasons.append(f"Accompagnée d'une analyse Hoe-aona? : {rating}")
        else:
            reasons.append("Sans analyse jointe : témoignage à recouper")
        title = row.get("analysis_title") or truncate(row["body"], 90)
        out.append(Candidate(
            origin="community", url=f"/publication/{row['id']}", title=title,
            publisher=f"{row['author_name']}" + (f" ({row['author_organization']})" if row['author_organization'] else ""),
            published_at=row["created_at"][:10], excerpt=excerpt or truncate(row["body"], 420),
            image_url=f"/api/posts/{row['id']}/image" if row.get("image_path") else None,
            rating=rating, relevance=score, fetched=True, found_via=FOUND_VIA["community"],
            reliability=round(rel, 2), reliability_reasons=reasons,
        ))
    return out[:3]


Reporter = Callable[[str, str, str, str], None]  # (clé, outil, "start" | "ok" | "error", détail)

_PROBE_LABEL = {"counter": "contre-exemple", "implication": "conséquence (par l'absurde)"}


async def _tracked(key: str, tool: str, detail: str, coro: Awaitable[dict], report: Reporter | None) -> dict:
    if report:
        report(key, tool, "start", detail)
    result = await coro
    if report:
        if result.get("ok"):
            n = len(result.get("items") or [])
            report(key, tool, "ok", f"{n} résultat(s)")
        else:
            report(key, tool, "error", "ignoré (non configuré)" if result.get("skipped")
                   else truncate(str(result.get("error", "échec")), 90))
    return result


async def gather(draft: ClaimDraft, gateway: ToolGateway, prefs: Preferences, settings: Settings,
                 report: Reporter | None = None) -> Collected:
    collected = Collected()
    lang = draft.language if draft.language in {"fr", "en", "es", "pt", "de"} else "fr"  # malgache → wiki français
    local = madagascar.is_madagascar(f"{draft.text} {draft.search_query}", draft.country_iso3 or prefs.default_country)
    news_query = draft.search_query_en or draft.search_query
    if local and "madagascar" not in madagascar.fold(news_query):
        news_query = f"{news_query} Madagascar"

    calls = {
        "wikipedia": gateway.call("wikipedia_search", query=draft.search_query, language=lang),
        "news": gateway.call("news_search", query=news_query),
        "web": gateway.call("web_search", query=draft.text),
    }
    if local:
        domains = madagascar.official_domains() + madagascar.MG_MEDIA_DOMAINS
        calls["web_mg"] = gateway.call("web_search", query=f"{draft.search_query} Madagascar",
                                       include_domains=domains, max_results=8)
        calls["news_mg"] = gateway.call("news_madagascar", query=draft.search_query, country="mg")
    # Recherches dédiées aux tests de raisonnement : contre-exemple et conséquences (par l'absurde).
    probes: list[tuple[str, str, str]] = []
    if draft.counter_query:
        probes.append(("counter", draft.counter_query, ""))
    for imp in draft.implications[:2]:
        probes.append(("implication", imp["query"], imp["consequence"]))
    for i, (kind, query, _) in enumerate(probes):
        q = f"{query} Madagascar" if local and "madagascar" not in madagascar.fold(query) else query
        calls[f"probe{i}"] = gateway.call("web_search", query=q, max_results=4)
    country = draft.country_iso3 or prefs.default_country
    if draft.indicator_code:
        calls["worldbank"] = gateway.call("worldbank_indicator", indicator=draft.indicator_code, country=country)
        if draft.indicator_code in imf.FROM_WORLDBANK:
            calls["imf"] = gateway.call("imf_indicator", indicator=imf.FROM_WORLDBANK[draft.indicator_code],
                                        country=country)
    tool_of = {"wikipedia": "wikipedia_search", "news": "news_search", "web": "web_search", "web_mg": "web_search",
               "news_mg": "news_madagascar", "worldbank": "worldbank_indicator", "imf": "imf_indicator",
               **{f"probe{i}": "web_search" for i in range(len(probes))}}
    call_detail = {"web_mg": "sites officiels et presse malgaches", "news_mg": "actualités de Madagascar",
                   "worldbank": f"{draft.indicator_code} · {country}", "imf": f"estimations WEO · {country}",
                   **{f"probe{i}": f"{_PROBE_LABEL[k]} : {truncate(q, 60)}" for i, (k, q, _) in enumerate(probes)}}
    results = dict(zip(calls, await asyncio.gather(*(
        _tracked(key, tool_of[key], call_detail.get(key, ""), coro, report) for key, coro in calls.items()))))

    candidates: dict[str, Candidate] = {}

    def add(c: Candidate) -> None:
        if c.url and c.url not in candidates:
            candidates[c.url] = c

    def items(key: str) -> list[dict]:
        return _note(results[key], collected, tool_of[key]) if key in results else []

    # Sources malgaches d'abord : en cas de doublon, c'est leur version qui est conservée.
    for item in items("web_mg"):
        excerpt, score = best_excerpt([item.get("content", "")], draft.text)
        add(Candidate(
            origin="web", url=item["url"], title=item.get("title", ""), publisher=domain_of(item["url"]),
            published_at=item.get("published_date"), excerpt=excerpt or truncate(item.get("content", ""), 420),
            relevance=score, found_via=FOUND_VIA["web_mg"],
        ))
    for item in items("news_mg"):
        text = " ".join(filter(None, [item.get("title"), item.get("description")]))
        excerpt, score = best_excerpt(split_sentences(text) or [text], draft.text)
        add(Candidate(
            origin="news", url=item["url"], title=item.get("title", ""),
            publisher=item.get("source") or domain_of(item["url"]), published_at=item.get("published_at"),
            excerpt=excerpt, image_url=item.get("image_url"), relevance=max(score, overlap(draft.text, text)),
            found_via=FOUND_VIA["news_mg"],
        ))
    for item in items("wikipedia"):
        excerpt, score = best_excerpt(split_sentences(item.get("extract", "")) or [item.get("extract", "")], draft.text)
        add(Candidate(
            origin="wikipedia", url=item["url"], title=item.get("title", ""), publisher="Wikipedia",
            published_at=(item.get("last_modified") or "")[:10] or None, image_url=item.get("image_url"),
            excerpt=excerpt or truncate(item.get("extract", ""), 420), relevance=score, fetched=True,
            found_via=FOUND_VIA["wikipedia"],
        ))
    for item in items("news"):
        add(Candidate(
            origin="news", url=item["url"], title=item.get("title", ""), publisher=item.get("domain", ""),
            published_at=_gdelt_date(item.get("seen_date")), image_url=item.get("image_url"),
            relevance=overlap(draft.text, item.get("title", "")), found_via=FOUND_VIA["news"],
        ))
    for item in items("web"):
        excerpt, score = best_excerpt([item.get("content", "")], draft.text)
        add(Candidate(
            origin="web", url=item["url"], title=item.get("title", ""), publisher=domain_of(item["url"]),
            published_at=item.get("published_date"), excerpt=excerpt or truncate(item.get("content", ""), 420),
            relevance=score, found_via=FOUND_VIA["web"],
        ))
    collected.counter_searched = any(kind == "counter" and results[f"probe{i}"].get("ok")
                                     for i, (kind, _, _) in enumerate(probes))
    for i, (kind, query, consequence) in enumerate(probes):
        target = f"{draft.text} {query} {consequence}"
        for item in items(f"probe{i}"):
            excerpt, score = best_excerpt([item.get("content", "")], target)
            add(Candidate(
                origin="web", url=item["url"], title=item.get("title", ""), publisher=domain_of(item["url"]),
                published_at=item.get("published_date"), excerpt=excerpt or truncate(item.get("content", ""), 420),
                relevance=max(score, 0.5 * overlap(query, item.get("content", ""))), found_via=FOUND_VIA[kind],
                probe=f"{query} {consequence}".strip(),
            ))
    for c in _community_candidates(draft):
        add(c)
    if any(c.origin == "community" for c in candidates.values()):
        collected.tools.add("platform_posts")

    directory = get_db().list_sources()
    official_hosts = _directory_domains(directory)

    def is_directory(url: str) -> bool:
        host = domain_of(url)
        return any(host == h or host.endswith("." + h) for h in official_hosts)

    # Lecture des pages les plus prometteuses (sources officielles en premier) : extrait ciblé, auteur, date.
    to_fetch = sorted((c for c in candidates.values() if not c.fetched),
                      key=lambda c: (not is_directory(c.url), -c.relevance))[:settings.max_pages_fetched_per_claim]
    sem = asyncio.Semaphore(4)
    if to_fetch and report:
        report("pages", "fetch_page", "start", f"{len(to_fetch)} page(s) : " + ", ".join(
            sorted({domain_of(c.url) for c in to_fetch})[:4]))
    await asyncio.gather(*(_fetch_and_enrich(c, draft, gateway, sem, collected) for c in to_fetch))
    if to_fetch and report:
        report("pages", "fetch_page", "ok", f"{sum(1 for c in to_fetch if c.fetched)}/{len(to_fetch)} page(s) lue(s)")

    evidences: list[Evidence] = []
    for c in candidates.values():
        if c.ai_probability >= prefs.ai_exclusion_threshold:
            collected.excluded.append(ExcludedSource(
                url=c.url, title=c.title or c.url, ai_probability=c.ai_probability,
                reason=f"Contenu probablement généré par IA ({round(c.ai_probability * 100)} %), exclu du calcul"))
            continue
        if c.relevance < MIN_RELEVANCE or not c.excerpt:
            continue
        if c.origin == "community":
            score, category, reasons, official = c.reliability or 0.55, "publication de la plateforme", c.reliability_reasons, False
        else:
            a = reliability.assess(c.url, {"author": c.author, "published_at": c.published_at} if c.fetched else None,
                                   c.ai_probability)
            score, category, reasons = a.score, a.category, a.reasons
            official = reliability.is_official(category) or is_directory(c.url)
            if is_directory(c.url) and score < 0.9:
                score, category = 0.9, "source officielle"
                reasons = [f"Inscrit à l'annuaire des sources officielles ({domain_of(c.url)})", *reasons[1:]]
        if score < prefs.min_source_reliability:
            collected.excluded.append(ExcludedSource(
                url=c.url, title=c.title or c.url, ai_probability=c.ai_probability,
                reason=f"Fiabilité insuffisante ({round(score * 100)} %) : {reasons[0]}"))
            continue
        evidences.append(Evidence(
            id="", url=c.url, title=truncate(c.title or c.url, 160),
            publisher=c.publisher or domain_of(c.url), domain=domain_of(c.url) if c.origin != "community" else "hoe-aona",
            origin="official" if official and c.origin == "web" else c.origin, official=official,
            found_via=c.found_via, category=category, published_at=c.published_at, excerpt=c.excerpt,
            image_url=c.image_url, reliability=score, reliability_reasons=reasons, relevance=round(c.relevance, 2),
            ai_probability=c.ai_probability,
            justification=f"Verdict de l'analyse jointe : {c.rating}" if c.rating else "",
        ))

    # Officielles d'abord, puis par fiabilité et pertinence ; une publication de la plateforme au plus 2 fois.
    evidences.sort(key=lambda e: (not e.official, -(0.5 * e.reliability + 0.5 * e.relevance)))
    kept, community = [], 0
    for e in evidences:
        if e.origin == "community":
            community += 1
            if community > 2:
                continue
        kept.append(e)
    for i, e in enumerate(kept[:settings.max_evidence_per_claim], start=1):
        e.id = f"E{i}"
        collected.evidence.append(e)

    n = 0
    for key in ("imf", "worldbank"):  # FMI d'abord : il couvre l'année en cours
        for item in items(key):
            n += 1
            collected.statistics.append(Statistic(
                id=f"S{n}", indicator_code=item["indicator_code"], indicator_name=item["indicator_name"],
                country=item["country"], country_code=item["country_code"], unit=item.get("unit", ""),
                latest_year=item.get("latest_year"), latest_value=item.get("latest_value"),
                series=[StatPoint(**p) for p in item.get("series", [])], claimed_value=draft.claimed_value,
                source_name=item.get("source_name") or "Banque mondiale, World Development Indicators",
                source_url=item["source_url"], last_updated=item.get("last_updated"),
                estimate_from_year=item.get("estimate_from_year"),
            ))

    collected.contacts = match_contacts(f"{draft.text} {draft.search_query}", directory, bool(draft.indicator_code))
    return collected
