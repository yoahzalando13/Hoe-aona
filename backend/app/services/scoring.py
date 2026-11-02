"""Règles de calcul des scores, décrites dans docs/ANALYSE.md (section 6)."""
from __future__ import annotations

from statistics import mean
from typing import TYPE_CHECKING, Iterable, Sequence

if TYPE_CHECKING:  # import léger : le module reste testable sans dépendances
    from ..schemas import Claim, Evidence, Statistic

CLAIM_LABELS = {
    "vrai": "Vrai",
    "plutot_vrai": "Plutôt vrai",
    "mitige": "Mitigé",
    "non_verifiable": "Non Hoe-aona?ble",
    "plutot_faux": "Plutôt faux",
    "faux": "Faux",
}
GLOBAL_LABELS = {
    "fiable": "Fiable",
    "plutot_fiable": "Plutôt fiable",
    "a_verifier": "À vérifier",
    "douteux": "Douteux",
}

PRIOR = 0.6            # pseudo-compte : sans preuve, le score reste à 5/10
FACTCHECK_BOOST = 1.5  # un fact-check publié pèse plus qu'un article ordinaire
MIN_EVIDENCE_WEIGHT = 0.35

_MOSTLY_FALSE = ["mostly false", "plutôt faux", "plutot faux", "largement faux", "en grande partie faux"]
_MOSTLY_TRUE = ["mostly true", "plutôt vrai", "plutot vrai", "largement vrai", "en grande partie vrai"]
_MISLEADING = ["trompeur", "misleading", "partly", "partiellement", "en partie", "manque de contexte",
               "missing context", "exagér", "exaggerat", "mixed", "mitigé", "half true", "demi-vrai",
               "hors contexte", "out of context", "sorti de son contexte", "imprécis", "needs context"]
_FALSE = ["faux", "false", "fausse", "pants on fire", "incorrect", "inexact", "fake", "infondé", "mensong",
          "wrong", "not true", "fabricated", "inventé", "canular", "hoax", "satire", "montage", "altered",
          "retouché", "scam", "arnaque"]
_TRUE = ["vrai", "true", "correct", "exact", "accurate", "confirmé", "confirmed", "authentique", "authentic"]


def rating_to_stance(rating: str | None) -> tuple[str, float]:
    """Convertit le verdict textuel d'un fact-checker en (position, confiance)."""
    if not rating:
        return "context", 0.0
    r = rating.lower().strip()
    if any(k in r for k in _MOSTLY_FALSE):
        return "refutes", 0.75
    if any(k in r for k in _MOSTLY_TRUE):
        return "supports", 0.75
    if any(k in r for k in _MISLEADING):
        return "refutes", 0.5
    if any(k in r for k in _FALSE):
        return "refutes", 0.95
    if any(k in r for k in _TRUE):
        return "supports", 0.9
    return "context", 0.2


def _weight(e: Evidence) -> float:
    w = e.reliability * e.confidence
    return w * FACTCHECK_BOOST if e.origin == "factcheck" else w


def claim_truth(evidence: Sequence[Evidence], statistics: Sequence[Statistic] = ()) -> tuple[float, float]:
    """Retourne (score de vérité sur 10, poids total des preuves décisives)."""
    s = sum(_weight(e) for e in evidence if e.stance == "supports")
    r = sum(_weight(e) for e in evidence if e.stance == "refutes")
    for st in statistics:  # donnée officielle : fiabilité 0,96, confiance 0,9
        if st.stance == "supports":
            s += 0.86
        elif st.stance == "refutes":
            r += 0.86
    score = 10 * (s + PRIOR / 2) / (s + r + PRIOR)
    return round(score, 1), round(s + r, 2)


def claim_verdict(score: float, weight: float) -> str:
    if weight < MIN_EVIDENCE_WEIGHT:
        return "non_verifiable"
    if score >= 8:
        return "vrai"
    if score >= 6:
        return "plutot_vrai"
    if score > 4:
        return "mitige"
    if score >= 2:
        return "plutot_faux"
    return "faux"


def veracity_score(claims: Iterable[Claim]) -> float:
    claims = list(claims)
    if not claims:
        return 5.0
    weights = [0.5 + min(c.evidence_weight, 3.0) for c in claims]
    return round(sum(c.truth_score * w for c, w in zip(claims, weights)) / sum(weights), 1)


def source_score(origin_reliabilities: Sequence[float], evidence: Sequence[Evidence]) -> float:
    origin = mean(origin_reliabilities) if origin_reliabilities else 0.45
    decisive = [e.reliability for e in evidence if e.stance != "context"]
    pool = decisive or [e.reliability for e in evidence]
    if not pool:
        return round(10 * origin, 1)
    return round(10 * (0.55 * origin + 0.45 * mean(pool)), 1)


def ai_score(probability: float) -> float:
    return round(10 * (1 - max(0.0, min(1.0, probability))), 1)


def global_score(source: float, veracity: float, ai: float, ai_probability: float,
                 weights: tuple[float, float, float]) -> float:
    ws, wv, wa = weights
    score = source * ws + veracity * wv + ai * wa
    if veracity < 4:
        score = min(score, 4.4)   # une information fausse ne peut pas être jugée fiable
    if ai_probability >= 0.85:
        score = min(score, 5.9)   # contenu très probablement généré : jamais « plutôt fiable »
    return round(score, 1)


def global_verdict(score: float) -> str:
    if score >= 8:
        return "fiable"
    if score >= 6.5:
        return "plutot_fiable"
    if score >= 4.5:
        return "a_verifier"
    return "douteux"
