"""Orchestration d'une analyse, de la lecture des entrées à l'article final."""
from __future__ import annotations

import asyncio
import base64
import logging
import time
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


def load_preferences(user_id: str | None = None) -> Preferences:
    return Preferences(**get_db().get_preferences(user_id))


class Progress:
    """Avancement de l'analyse et journal des agents, écrits en base pour l'affichage en direct."""

    MAX_EVENTS = 200

    def __init__(self, analysis_id: str):
        self.id = analysis_id
        self.t0 = time.monotonic()
        self.events: list[dict] = []
        self.progress = 0
        self.step = ""

    def _flush(self) -> None:
        get_db().update_analysis(self.id, status="running", progress=self.progress, step=self.step,
                                 events=self.events[-self.MAX_EVENTS:])

    def __call__(self, progress: int, step: str) -> None:
        self.progress, self.step = max(self.progress, progress), step
        self._flush()

    def advance(self, progress: float) -> None:
        """Fait progresser la barre sans changer d'étape (sous-étapes d'une phase longue)."""
        value = int(progress)
        if value > self.progress:
            self.progress = value
            self._flush()

    def event(self, agent: str, message: str, status: str = "info", detail: str = "", tool: str = "") -> int:
        self.events.append({"at": round(time.monotonic() - self.t0, 1), "agent": agent, "message": message,
                            "status": status, "detail": detail, "tool": tool})
        self._flush()
        return len(self.events) - 1

    def finish(self, index: int, status: str = "done", detail: str = "") -> None:
        if 0 <= index < len(self.events):
            ev = self.events[index]
            ev["status"] = status
            if detail:
                ev["detail"] = detail
            ev["duration"] = round(time.monotonic() - self.t0 - ev["at"], 1)
            self._flush()

    def close_running(self, status: str = "done") -> None:
        for i, ev in enumerate(self.events):
            if ev["status"] == "running":
                self.finish(i, status)


TOOL_NAMES = {
    "wikipedia_search": "Wikipedia", "news_search": "GDELT (presse mondiale)", "web_search": "recherche web",
    "news_madagascar": "presse malgache", "worldbank_indicator": "Banque mondiale", "imf_indicator": "FMI",
    "fetch_page": "lecture de page", "detect_ai_image": "Sightengine", "platform_posts": "fil média",
}


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
                   + (f", {non_verifiable} non vérifiable(s)" if non_verifiable else "")) if claims else \
        "Aucune affirmation vérifiable identifiée"
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
    prefs = load_preferences(record.get("user_id"))
    progress = Progress(analysis_id)
    llm = LLMClient(settings)
    warnings: list[str] = []
    tools: set[str] = set()

    try:
        progress(5, "Lecture des données")
        extracted: list[Extracted] = []
        n_inputs = max(len(record["inputs"]), 1)
        for k, item in enumerate(record["inputs"]):
            label = "Lecture du texte saisi" if item["kind"] == "text" else \
                f"Lecture de {truncate(item.get('url') or item.get('name') or 'la pièce jointe', 70)}"
            how = {"image": "OCR et métadonnées", "audio": "transcription", "url": "lecture de la page",
                   "document": "extraction du texte"}.get(item["kind"], "")
            ev = progress.event("lecteur", label, "running", how)
            if item["kind"] == "text":
                ex = await extract_text_input(item["text"])
            elif item["kind"] == "url":
                ex = await _read_url(item["url"], warnings)
                tools.add("fetch_page")
            else:
                ex = await extract_file(Path(item["path"]), item["kind"], item["name"],
                                        item.get("mime", "application/octet-stream"), llm)
            extracted.append(ex)
            progress.finish(ev, "error" if ex.note and not ex.text else "done",
                            f"{len(ex.text):,} caractères extraits".replace(",", " ") if ex.text else (ex.note or "aucun texte"))
            progress.advance(5 + 15 * (k + 1) / n_inputs)
        for ex in extracted:
            if ex.note and ex.kind != "url":
                warnings.append(f"{ex.name} : {ex.note}")

        progress(20, "Détection des signatures IA")
        for ex in extracted:
            ev = progress.event("detecteur", f"Recherche de signatures IA dans {truncate(ex.name, 60)}", "running",
                                "style, métadonnées" + (", analyse d'image" if ex.image_bytes else ""))
            await _remote_image_check(ex, prefs, tools, warnings)
            progress.finish(ev, detail=f"probabilité IA {_pct(ex.ai.probability)}")

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
        ev = progress.event("extracteur", "Repérage des affirmations vérifiables", "running",
                            "modèle de langage" if llm.available else "règles linguistiques")
        drafts, topic, summary = await extract_claims(full_text, llm, settings.max_claims, prefs.default_country, warnings,
                                                  prefs.report_language)
        progress.finish(ev, detail=f"{len(drafts)} affirmation(s)" + (f" · sujet : {topic}" if topic else ""))
        for i, d in enumerate(drafts, start=1):
            progress.event("extracteur", f"C{i} · « {truncate(d.text, 110)} »", "info")
        if not drafts:
            warnings.append("Aucune affirmation vérifiable n'a été trouvée dans le contenu")

        progress(45, "Recherche de preuves (MCP)")
        collected = []
        sem = asyncio.Semaphore(2)  # respecte les quotas gratuits

        done_claims = 0

        async def gather_one(i: int, draft):
            nonlocal done_claims
            async with sem:
                head = progress.event("chercheur", f"C{i} · recherche de preuves", "running",
                                      truncate(draft.search_query, 80))

                open_events: dict[str, int] = {}

                def report(key: str, tool: str, phase: str, detail: str = "") -> None:
                    if phase == "start":
                        open_events[key] = progress.event("chercheur", f"C{i} · interroge {TOOL_NAMES.get(tool, tool)}",
                                                          "running", detail, tool)
                    else:
                        progress.finish(open_events.pop(key, -1), "done" if phase == "ok" else "error", detail)

                col = await evidence.gather(draft, get_gateway(), prefs, settings, report)
            done_claims += 1
            progress.finish(head, detail=f"{len(col.evidence)} preuve(s), {len(col.statistics)} statistique(s)")
            progress.advance(45 + 30 * done_claims / max(len(drafts), 1))
            return col

        collected = await asyncio.gather(*(gather_one(i, d) for i, d in enumerate(drafts, start=1)))
        excluded: list[ExcludedSource] = []
        for col in collected:
            tools |= col.tools
            excluded += col.excluded
            for w in col.warnings:
                if w not in warnings:
                    warnings.append(w)

        progress(75, "Évaluation : preuves, contre-exemples, raisonnement par l'absurde")
        claims: list[Claim] = []
        for i, (draft, col) in enumerate(zip(drafts, collected), start=1):
            ev = progress.event("evaluateur", f"C{i} · confrontation des preuves et tests de raisonnement", "running",
                                "contre-exemples, raisonnement par l'absurde, ordres de grandeur")
            claim = await stance.evaluate(f"C{i}", draft, col, llm, prefs.report_language, warnings)
            claims.append(claim)
            progress.finish(ev, detail=f"{claim.verdict_label} ({claim.truth_score}/10)")
            progress.advance(75 + 13 * i / max(len(drafts), 1))

        progress(88, "Calcul des scores")
        ev = progress.event("calculateur", "Pondération source · véracité · part d'IA", "running")
        criteria, src, ver, ai = _criteria(inputs, claims, origin_rel, ai_prob, ai_signals)
        g = scoring.global_score(src, ver, ai, ai_prob, prefs.normalized_weights())
        progress.finish(ev, detail=f"score global {g}/10")
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
        ev = progress.event("redacteur", "Rédaction de l'article suggéré", "running",
                            f"{len(claims)} affirmation(s), sources numérotées")
        result.article = await article.generate(result, llm, prefs.report_language, warnings)
        progress.finish(ev, detail=f"{len(result.article.body_markdown.split())} mots, "
                                   f"{len(result.article.sources)} source(s)")
        progress.event("redacteur", "Analyse terminée", "done")
        result.warnings = warnings

        title = truncate(topic or record["title"], 80)
        db.update_analysis(analysis_id, status="done", progress=100, step="Terminé", title=title,
                           global_score=g, verdict=verdict, result=result.model_dump(mode="json"),
                           events=progress.events[-Progress.MAX_EVENTS:])
    except Exception as exc:  # noqa: BLE001
        log.exception("Analyse %s en échec", analysis_id)
        progress.close_running("error")
        db.update_analysis(analysis_id, status="error", step="Erreur", error=f"{type(exc).__name__}: {exc}"[:500],
                           events=progress.events[-Progress.MAX_EVENTS:])
