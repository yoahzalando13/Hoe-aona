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
    "non_verifiable": "Non vérifiable",
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
MIN_EVIDENCE_WEIGHT = 0.35

def _weight(e: Evidence) -> float:
    return e.reliability * e.confidence


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
