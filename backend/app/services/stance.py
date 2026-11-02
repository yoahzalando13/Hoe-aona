"""Évalue une affirmation face aux preuves : position de chaque preuve, arguments, conclusion.

Le LLM ne reçoit que les extraits collectés et doit citer leurs identifiants ; les
identifiants inventés sont ignorés. Sans LLM, seuls les verdicts des fact-checks et la
comparaison numérique avec la statistique officielle sont utilisés.
"""
from __future__ import annotations

import logging
import re

from ..schemas import Claim
from . import scoring
from .claims import ClaimDraft
from .evidence import Collected
from .llm import LLMClient
from .textutils import numbers_in, truncate

log = logging.getLogger("hoe-aona.stance")

LANG_NAMES = {"fr": "français", "en": "anglais", "mg": "malgache"}

SYSTEM = (
    "Tu es un fact-checker rigoureux. Tu juges UNIQUEMENT à partir des preuves fournies, sans "
    "connaissances extérieures, et tu cites chaque preuve par son identifiant. Réponds en JSON valide."
)


def _fmt_value(value: float | None) -> str:
    if value is None:
        return "n.d."
    if abs(value) >= 1e9:
        return f"{value / 1e9:.2f} milliards".replace(".", ",")
    if abs(value) >= 1e6:
        return f"{value / 1e6:.2f} millions".replace(".", ",")
    return f"{value:,.2f}".replace(",", " ").replace(".", ",").rstrip("0").rstrip(",")


def _prompt(draft: ClaimDraft, col: Collected, lang: str) -> str:
    lines = []
    for e in col.evidence:
        extra = f" | Verdict du fact-checker : {e.rating}" if e.rating else ""
        lines.append(f"[{e.id}] {e.publisher} ({e.category}, fiabilité {e.reliability:.2f}, date {e.published_at or 'inconnue'})"
                     f" — {e.title}{extra}\n    Extrait : « {e.excerpt} »")
    for s in col.statistics:
        serie = ", ".join(f"{p.year} : {_fmt_value(p.value)}" for p in s.series[-5:])
        lines.append(f"[{s.id}] Statistique officielle — {s.indicator_name}, {s.country} ({s.unit}) : "
                     f"dernière valeur {_fmt_value(s.latest_value)} en {s.latest_year} ; série : {serie} ; "
                     f"base mise à jour le {s.last_updated or 'n.d.'}. Valeur annoncée dans le contenu : {s.claimed_value or 'non précisée'}")
    evidence_block = "\n".join(lines) or "(aucune preuve trouvée)"
    return f"""Affirmation à vérifier : « {draft.text} »

Preuves disponibles :
{evidence_block}

Pour chaque preuve, indique si elle CONFIRME l'affirmation (supports), la CONTREDIT (refutes) ou n'apporte
que du CONTEXTE (context), avec une confiance entre 0 et 1. Un fact-check ne compte que s'il porte bien sur la
même affirmation. Pour une statistique, compare la valeur annoncée à la donnée officielle en tenant compte de
l'année et de l'unité ; signale un écart chiffré.

Réponds en {LANG_NAMES.get(lang, 'français')} avec ce JSON :
{{"evidence": [{{"id": "E1", "stance": "supports|refutes|context", "confidence": 0.0, "reason": "phrase courte"}}],
 "statistics": [{{"id": "S1", "stance": "supports|refutes|context", "comment": "comparaison chiffrée"}}],
 "arguments_for": ["argument qui soutient l'affirmation, terminé par la référence, ex. [E2]"],
 "arguments_against": ["argument qui la contredit, terminé par la référence, ex. [S1]"],
 "conclusion": "une phrase de conclusion prudente"}}
Si les preuves sont insuffisantes, laisse les listes d'arguments vides et dis-le dans la conclusion."""


def _numeric_stance(claimed: str | None, official: float | None) -> tuple[str, str]:
    """Repli sans LLM : compare la première valeur annoncée à la donnée officielle (tolérance 10 %)."""
    if not claimed or official is None:
        return "context", ""
    nums = numbers_in(claimed)
    if not nums:
        return "context", ""
    try:
        value = float(re.sub(r"[\s\u202f\u00a0]", "", nums[0]).replace(",", "."))
    except ValueError:
        return "context", ""
    low = claimed.lower()
    if "milliard" in low or "billion" in low:
        value *= 1e9
    elif "million" in low:
        value *= 1e6
    if official == 0:
        return "context", ""
    gap = abs(value - official) / abs(official)
    comment = f"Valeur annoncée {_fmt_value(value)} contre {_fmt_value(official)} (écart de {round(gap * 100)} %)"
    return ("supports" if gap <= 0.1 else "refutes" if gap >= 0.3 else "context"), comment


def _valid_refs(items: list, known: set[str]) -> list[str]:
    """Garde les arguments qui citent au moins une preuve existante."""
    kept = []
    for arg in items or []:
        if not isinstance(arg, str):
            continue
        refs = set(re.findall(r"\[([ES]\d+)\]", arg))
        if refs and refs <= known:
            kept.append(truncate(arg, 400))
    return kept


async def evaluate(claim_id: str, draft: ClaimDraft, col: Collected, llm: LLMClient, lang: str,
                   warnings: list[str]) -> Claim:
    known = {e.id for e in col.evidence} | {s.id for s in col.statistics}
    arguments_for: list[str] = []
    arguments_against: list[str] = []
    conclusion = ""

    if llm.available and known:
        try:
            data = await llm.chat_json(SYSTEM, _prompt(draft, col, lang), max_tokens=4000)
            by_id = {e.id: e for e in col.evidence}
            for item in data.get("evidence", []):
                e = by_id.get(str(item.get("id")))
                if e and item.get("stance") in ("supports", "refutes", "context"):
                    e.stance = item["stance"]
                    e.confidence = max(0.0, min(1.0, float(item.get("confidence", 0.5) or 0.5)))
                    e.justification = truncate(str(item.get("reason", "")), 300)
            stats = {s.id: s for s in col.statistics}
            for item in data.get("statistics", []):
                s = stats.get(str(item.get("id")))
                if s and item.get("stance") in ("supports", "refutes", "context"):
                    s.stance = item["stance"]
                    s.comment = truncate(str(item.get("comment", "")), 300)
            arguments_for = _valid_refs(data.get("arguments_for"), known)
            arguments_against = _valid_refs(data.get("arguments_against"), known)
            conclusion = truncate(str(data.get("conclusion", "")), 400)
        except Exception as exc:  # noqa: BLE001
            log.warning("Évaluation LLM échouée : %s", exc)
            warnings.append("Évaluation par LLM indisponible pour une affirmation : verdicts des fact-checks et chiffres officiels seulement")

    if not conclusion:  # repli déterministe
        for s in col.statistics:
            if s.stance == "context":
                s.stance, s.comment = _numeric_stance(s.claimed_value, s.latest_value)
        for e in col.evidence:
            if e.stance == "supports":
                arguments_for.append(f"{e.publisher} : « {truncate(e.excerpt, 180)} » [{e.id}]")
            elif e.stance == "refutes":
                arguments_against.append(f"{e.publisher} ({e.rating or 'contredit'}) : « {truncate(e.excerpt, 180)} » [{e.id}]")
        for s in col.statistics:
            if s.comment and s.stance != "context":
                (arguments_for if s.stance == "supports" else arguments_against).append(f"{s.comment} [{s.id}]")
        conclusion = ("Aucune preuve suffisante n'a été trouvée." if not (arguments_for or arguments_against)
                      else "Conclusion établie à partir des fact-checks et des statistiques officielles.")

    score, weight = scoring.claim_truth(col.evidence, col.statistics)
    verdict = scoring.claim_verdict(score, weight)
    return Claim(
        id=claim_id, text=draft.text, search_query=draft.search_query,
        truth_score=score, evidence_weight=weight, verdict=verdict,
        verdict_label=scoring.CLAIM_LABELS[verdict], conclusion=conclusion,
        arguments_for=arguments_for, arguments_against=arguments_against,
        evidence=col.evidence, statistics=col.statistics,
    )
