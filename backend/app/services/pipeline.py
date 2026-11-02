"""Orchestration d'une analyse, de la lecture des entrées à l'article final."""
from __future__ import annotations

import asyncio
import base64
import logging
from pathlib import Path

from ..config import get_settings
from ..db import get_db
from ..mcp.gateway import get_gateway
from ..schemas import AnalysisResult, Claim, Criterion, ExcludedSource, InputSummary, Preferences
from . import ai_detection, article, evidence, reliability, scoring, stance
from .claims import extract_claims
from .extraction import Extracted, extract_file, extract_text_input
from .llm import LLMClient
from .textutils import truncate

log = logging.getLogger("hoe-aona.pipeline")


def load_preferences() -> Preferences:
    return Preferences(**get_db().get_preferences())


class Progress:
    def __init__(self, analysis_id: str):
        self.id = analysis_id

    def __call__(self, progress: int, step: str) -> None:
        get_db().update_analysis(self.id, status="running", progress=progress, step=step)


def _pct(p: float) -> str:
    return f"{round(p * 100)} %"


async def _read_url(url: str, warnings: list[str]) -> Extracted:
    result = await get_gateway().call("fetch_page", url=url)
    ex = Extracted(kind="url", name=url, url=url)
    if not result.get("ok") or not result.get("items"):
        ex.note = result.get("error", "Page illisible")
        warnings.append(f"Lien non lu : {url} ({ex.note})")
        return ex
    page = result["items"][0]
    ex.text = page.get("text", "")
    ex.name = page.get("title") or url
    ex.meta = {"author": page.get("author"), "published_at": page.get("published_at"),
               "site_name": page.get("site_name"), "generator": page.get("generator")}
    text_ai = ai_detection.text_signals(ex.text)
    meta_ai = ai_detection.metadata_signals({"generator": page.get("generator")}, "site")
    ex.ai = ai_detection.AIResult(ai_detection.noisy_or([text_ai.probability, meta_ai.probability]),
                                  meta_ai.signals + text_ai.signals)
    return ex


async def _remote_image_check(ex: Extracted, prefs: Preferences, tools: set[str], warnings: list[str]) -> None:
    if not (prefs.deep_ai_detection and ex.image_bytes):
        return
    result = await get_gateway().call("detect_ai_image", image_base64=base64.b64encode(ex.image_bytes).decode())
    if result.get("ok") and result.get("items"):
        tools.add("detect_ai_image")
        ex.ai = ai_detection.combine(ex.ai, result["items"][0]["ai_generated"], "Sightengine")
    elif result.get("error") and not result.get("skipped"):
        warnings.append(result["error"])


def _criteria(inputs: list[InputSummary], claims: list[Claim], origin_rel: list[float], ai_prob: float,
              ai_signals: list[str]) -> tuple[list[Criterion], float, float, float]:
    all_evidence = [e for c in claims for e in c.evidence]
    src = scoring.source_score(origin_rel, all_evidence)
    ver = scoring.veracity_score(claims)
    ai = scoring.ai_score(ai_prob)

    decisive = [e for e in all_evidence if e.stance != "context"]
    cats = sorted({e.category for e in decisive})
    src_details = []
    for i in inputs:
        if i.reliability is not None:
            src_details.append(f"Origine fournie : {i.name} — fiabilité {_pct(i.reliability)} ({', '.join(i.reliability_reasons[:3])})")
    if not origin_rel:
        src_details.append("Aucune source d'origine fournie : la provenance du contenu n'est pas établie")
    src_details.append(f"{len(decisive)} preuve(s) décisive(s) sur {len(all_evidence)} trouvée(s)"
                       + (f" : {', '.join(cats)}" if cats else ""))
    src_summary = ("Origine traçable et preuves de qualité" if src >= 7.5 else
                   "Sources partiellement établies" if src >= 5 else "Origine incertaine ou sources faibles")

    confirmed = sum(1 for c in claims if c.verdict in ("vrai", "plutot_vrai"))
    refuted = sum(1 for c in claims if c.verdict in ("faux", "plutot_faux"))
    non_verifiable = sum(1 for c in claims if c.verdict == "non_verifiable")
    ver_summary = (f"{confirmed} affirmation(s) sur {len(claims)} confirmée(s), {refuted} contredite(s)"
                   + (f", {non_verifiable} non Hoe-aona?ble(s)" if non_verifiable else "")) if claims else \
        "Aucune affirmation Hoe-aona?ble identifiée"
    ver_details = [f"« {truncate(c.text, 90)} » : {c.verdict_label} ({c.truth_score}/10)" for c in claims]

    level = "faible" if ai_prob < 0.3 else "modérée" if ai_prob < 0.6 else "élevée"
    ai_summary = f"Probabilité {level} de contenu généré par IA ({_pct(ai_prob)})"
    criteria = [
        Criterion(key="source", label="Source", score=src, summary=src_summary, details=src_details),
        Criterion(key="veracity", label="Véracité des données", score=ver, summary=ver_summary, details=ver_details),
        Criterion(key="ai", label="Fait par IA", score=ai, summary=ai_summary, details=ai_signals[:8]),
    ]
    return criteria, src, ver, ai


async def run_analysis(analysis_id: str) -> None:
    db = get_db()
    record = db.get_analysis(analysis_id)
    if not record:
        return
    settings = get_settings()
    prefs = load_preferences()
    progress = Progress(analysis_id)
    llm = LLMClient(settings)
    warnings: list[str] = []
    tools: set[str] = set()

    try:
        progress(5, "Lecture des données")
        extracted: list[Extracted] = []
        for item in record["inputs"]:
            if item["kind"] == "text":
                extracted.append(await extract_text_input(item["text"]))
            elif item["kind"] == "url":
                extracted.append(await _read_url(item["url"], warnings))
                tools.add("fetch_page")
            else:
                extracted.append(await extract_file(Path(item["path"]), item["kind"], item["name"],
                                                    item.get("mime", "application/octet-stream"), llm))
        for ex in extracted:
            if ex.note and ex.kind != "url":
                warnings.append(f"{ex.name} : {ex.note}")

        progress(20, "Détection des signatures IA")
        for ex in extracted:
            await _remote_image_check(ex, prefs, tools, warnings)

        inputs: list[InputSummary] = []
        origin_rel: list[float] = []
        for ex in extracted:
            summary = InputSummary(kind=ex.kind, name=truncate(ex.name, 120), size=ex.size,
                                   extracted_chars=len(ex.text), ai_probability=ex.ai.probability,
                                   ai_signals=ex.ai.signals, url=ex.url, note=ex.note)
            if ex.kind == "url" and ex.url:
                a = reliability.assess(ex.url, ex.meta, ex.ai.probability)
                summary.reliability, summary.reliability_reasons = a.score, a.reasons
                origin_rel.append(a.score)
            inputs.append(summary)

        # Probabilité IA du contenu soumis : moyenne pondérée par la quantité de texte, mais une
        # signature forte sur une seule entrée (ex. image générée) l'emporte.
        weights = [max(len(ex.text), 300) for ex in extracted] or [1]
        probs = [ex.ai.probability for ex in extracted] or [0.0]
        ai_prob = round(max(sum(p * w for p, w in zip(probs, weights)) / sum(weights),
                            max((p for p in probs if p >= 0.85), default=0.0)), 2)
        ai_signals = [f"{ex.name} : {s}" if len(extracted) > 1 else s for ex in extracted for s in ex.ai.signals]

        progress(30, "Extraction des affirmations")
        full_text = "\n\n".join(ex.text for ex in extracted if ex.text)
        drafts, topic, summary = await extract_claims(full_text, llm, settings.max_claims, prefs.default_country, warnings)
        if not drafts:
            warnings.append("Aucune affirmation Hoe-aona?ble n'a été trouvée dans le contenu")

        progress(45, "Recherche de preuves (MCP)")
        collected = []
        sem = asyncio.Semaphore(2)  # respecte les quotas gratuits

        async def gather_one(draft):
            async with sem:
                return await evidence.gather(draft, get_gateway(), prefs, settings)

        collected = await asyncio.gather(*(gather_one(d) for d in drafts))
        excluded: list[ExcludedSource] = []
        for col in collected:
            tools |= col.tools
            excluded += col.excluded
            for w in col.warnings:
                if w not in warnings:
                    warnings.append(w)

        progress(75, "Évaluation de la véracité")
        claims: list[Claim] = []
        for i, (draft, col) in enumerate(zip(drafts, collected), start=1):
            claims.append(await stance.evaluate(f"C{i}", draft, col, llm, prefs.report_language, warnings))

        progress(88, "Calcul des scores")
        criteria, src, ver, ai = _criteria(inputs, claims, origin_rel, ai_prob, ai_signals)
        g = scoring.global_score(src, ver, ai, ai_prob, prefs.normalized_weights())
        verdict = scoring.global_verdict(g)
        ws, wv, wa = prefs.normalized_weights()
        result = AnalysisResult(
            global_score=g, verdict=verdict, verdict_label=scoring.GLOBAL_LABELS[verdict],
            summary=summary or (truncate(full_text, 200) if full_text else "Contenu sans texte exploitable"),
            topic=topic, criteria=criteria, claims=claims, inputs=inputs,
            excluded_sources=list({e.url: e for e in excluded}.values()),
            warnings=warnings, tools_used=sorted(tools),
            weights={"source": round(ws, 2), "veracity": round(wv, 2), "ai": round(wa, 2)},
        )

        progress(95, "Rédaction de l'article")
        result.article = await article.generate(result, llm, prefs.report_language, warnings)
        result.warnings = warnings

        title = truncate(topic or record["title"], 80)
        db.update_analysis(analysis_id, status="done", progress=100, step="Terminé", title=title,
                           global_score=g, verdict=verdict, result=result.model_dump(mode="json"))
    except Exception as exc:  # noqa: BLE001
        log.exception("Analyse %s en échec", analysis_id)
        db.update_analysis(analysis_id, status="error", step="Erreur", error=f"{type(exc).__name__}: {exc}"[:500])
