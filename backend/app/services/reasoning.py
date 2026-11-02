"""Tests de raisonnement appliqués à chaque affirmation, en complément des preuves.

- Contre-exemple : une recherche dédiée cherche un cas où l'affirmation ne se vérifie pas. Pour une
  affirmation absolue (« tous », « jamais »…), un seul contre-exemple fiable suffit à la réfuter.
- Raisonnement par l'absurde : on suppose l'affirmation vraie, on en déduit des conséquences qui
  devraient être observables, puis on les confronte aux preuves. Une conséquence démentie réfute l'hypothèse.
- Ordre de grandeur : la valeur annoncée est comparée à la statistique officielle (calcul déterministe).
- Cohérence interne : contradictions dans l'énoncé, chronologie impossible.
- Sophismes : procédés rhétoriques (généralisation hâtive, faux dilemme…), à titre d'information.

Garde-fous : un test ne compte que s'il cite des preuves réellement collectées ([E…], [S…]) ; sinon il est
déclaré non concluant. Son effet sur le score est borné (entre -3 et +1 point) et affiché.
"""
from __future__ import annotations

import re
from typing import Any

from ..schemas import Evidence, ReasoningStep, ReasoningTest, Statistic
from .textutils import numbers_in, truncate

LABELS = {
    "contre_exemple": "Recherche de contre-exemple",
    "absurde": "Raisonnement par l'absurde",
    "ordre_de_grandeur": "Ordre de grandeur",
    "coherence": "Cohérence interne",
    "sophisme": "Procédés rhétoriques",
}
OUTCOMES = {"refute", "affaiblit", "compatible", "non_concluant"}
STEP_OUTCOMES = {"contredite", "compatible", "non_testable"}

PROMPT = """
TESTS DE RAISONNEMENT : ajoute la clé "tests" au même objet JSON ; applique-les en ne citant QUE les identifiants de preuves ci-dessus.
- "contre_exemple" : une preuve montre-t-elle un cas où l'affirmation est fausse ? {universal_hint}
  outcome = "refute" (contre-exemple fiable), "affaiblit" (exception partielle), "compatible" (aucun contre-exemple
  malgré la recherche), "non_concluant" (pas assez d'éléments).
- "absurde" : SUPPOSE l'affirmation vraie, énonce ses conséquences nécessaires (pars de celles-ci : {implications})
  et confronte chacune aux preuves : "contredite", "compatible" ou "non_testable". Une conséquence contredite par une
  preuve fiable rend l'hypothèse intenable.
- "coherence" : en lisant l'ÉNONCÉ SEUL, sans les preuves, se contredit-il lui-même (deux chiffres incompatibles,
  chronologie impossible, événement daté dans le futur présenté comme passé) ? outcome = "affaiblit" si oui, sinon
  "non_concluant". Un désaccord avec les preuves n'est PAS un défaut de cohérence interne.
- "sophismes" : procédés rhétoriques présents dans l'énoncé (généralisation hâtive, appel à l'autorité anonyme,
  faux dilemme, corrélation présentée comme causalité, chiffre sans source…) ; liste vide s'il n'y en a pas.
Format :
"tests": {{
  "contre_exemple": {{"outcome": "...", "summary": "phrase", "refs": ["E2"]}},
  "absurde": {{"hypothesis": "Supposons que …", "steps": [{{"consequence": "…", "outcome": "contredite|compatible|non_testable",
               "refs": ["S1"], "explanation": "phrase"}}], "summary": "phrase"}},
  "coherence": {{"outcome": "affaiblit|non_concluant", "summary": "phrase"}},
  "sophismes": [{{"type": "généralisation hâtive", "passage": "extrait de l'énoncé", "explanation": "phrase"}}]
}}"""


def prompt_section(universal: bool, implications: list[dict], lang_name: str = "français") -> str:
    hint = ("L'affirmation est ABSOLUE : un seul contre-exemple fiable suffit à la réfuter." if universal
            else "L'affirmation n'est pas absolue : un contre-exemple l'affaiblit sans forcément la réfuter.")
    imps = "; ".join(i["consequence"] for i in implications) or "à toi de les formuler"
    return PROMPT.format(universal_hint=hint, implications=imps) + f"\nRédige tous les textes des tests en {lang_name}."


def _refs(value: Any, known: set[str]) -> list[str]:
    refs = []
    for r in value or []:
        r = str(r).strip("[] ")
        if r in known and r not in refs:
            refs.append(r)
    return refs


def _strong(refs: list[str], evidence: dict[str, Evidence], stats: dict[str, Statistic]) -> bool:
    """Au moins une référence fiable : statistique officielle, source officielle ou fiabilité ≥ 0,6."""
    return any(r in stats or (r in evidence and (evidence[r].official or evidence[r].reliability >= 0.6)) for r in refs)


def parse_number(text: str | None) -> float | None:
    if not text:
        return None
    nums = numbers_in(text)
    if not nums:
        return None
    try:
        value = float(re.sub(r"[\s  ]", "", nums[0]).replace(",", "."))
    except ValueError:
        return None
    low = text.lower()
    if "milliard" in low or "billion" in low:
        value *= 1e9
    elif "million" in low:
        value *= 1e6
    return value


def magnitude_test(statistics: list[Statistic]) -> ReasoningTest | None:
    """Comparaison déterministe de la valeur annoncée avec la statistique officielle la plus récente."""
    for s in statistics:
        claimed, official = parse_number(s.claimed_value), s.latest_value
        if claimed is None or not official:
            continue
        ratio = claimed / official
        factor = max(ratio, 1 / ratio) if ratio > 0 else float("inf")
        gap = abs(claimed - official) / abs(official)
        year = f" en {s.latest_year}" if s.latest_year else ""
        base = f"Valeur annoncée {s.claimed_value} contre {_fmt(official)} {s.unit}{year} ({s.source_name})"
        if factor >= 3:
            outcome, summary = "refute", f"{base} : écart d'un facteur {factor:.1f}, invraisemblable."
        elif gap > 0.3:
            outcome, summary = "affaiblit", f"{base} : écart de {round(gap * 100)} %."
        elif gap <= 0.1:
            outcome, summary = "compatible", f"{base} : même ordre de grandeur (écart de {round(gap * 100)} %)."
        else:
            outcome, summary = "non_concluant", f"{base} : écart de {round(gap * 100)} %, à préciser."
        return ReasoningTest(kind="ordre_de_grandeur", label=LABELS["ordre_de_grandeur"], outcome=outcome,
                             summary=summary, refs=[s.id])
    return None


def _fmt(value: float) -> str:
    if abs(value) >= 1e9:
        return f"{value / 1e9:.2f} milliards".replace(".", ",")
    if abs(value) >= 1e6:
        return f"{value / 1e6:.2f} millions".replace(".", ",")
    return f"{value:,.2f}".replace(",", " ").replace(".", ",").rstrip("0").rstrip(",")


def parse_tests(data: dict, evidence: list[Evidence], statistics: list[Statistic], universal: bool,
                counter_searched: bool) -> list[ReasoningTest]:
    """Valide la réponse du LLM : les tests sans référence réelle deviennent « non concluants »."""
    ev = {e.id: e for e in evidence}
    st = {s.id: s for s in statistics}
    known = set(ev) | set(st)
    tests: list[ReasoningTest] = []
    raw = data.get("tests") if isinstance(data.get("tests"), dict) else {}

    ce = raw.get("contre_exemple") if isinstance(raw.get("contre_exemple"), dict) else None
    if ce:
        outcome = ce.get("outcome") if ce.get("outcome") in OUTCOMES else "non_concluant"
        refs = _refs(ce.get("refs"), known)
        summary = truncate(str(ce.get("summary", "")), 400)
        if outcome in ("refute", "affaiblit") and not refs:
            outcome, summary = "non_concluant", "Contre-exemple évoqué sans preuve collectée à l'appui : non retenu."
        elif outcome == "refute" and not _strong(refs, ev, st):
            outcome = "affaiblit"
        elif outcome == "compatible" and not counter_searched:
            outcome = "non_concluant"
        tests.append(ReasoningTest(kind="contre_exemple", label=LABELS["contre_exemple"], outcome=outcome,
                                   summary=summary, refs=refs))

    ab = raw.get("absurde") if isinstance(raw.get("absurde"), dict) else None
    if ab:
        steps = []
        for s in (ab.get("steps") or [])[:4]:
            if not isinstance(s, dict) or not s.get("consequence"):
                continue
            refs = _refs(s.get("refs"), known)
            outcome = s.get("outcome") if s.get("outcome") in STEP_OUTCOMES else "non_testable"
            if outcome != "non_testable" and not refs:
                outcome = "non_testable"
            steps.append(ReasoningStep(text=truncate(str(s["consequence"]), 260), outcome=outcome, refs=refs,
                                       explanation=truncate(str(s.get("explanation", "")), 300)))
        contradicted = [s for s in steps if s.outcome == "contredite"]
        if contradicted:
            outcome = "refute" if any(_strong(s.refs, ev, st) for s in contradicted) else "affaiblit"
        elif steps and all(s.outcome == "compatible" for s in steps):
            outcome = "compatible"
        else:
            outcome = "non_concluant"
        tests.append(ReasoningTest(
            kind="absurde", label=LABELS["absurde"], outcome=outcome, steps=steps,
            hypothesis=truncate(str(ab.get("hypothesis") or "Supposons que l'affirmation soit vraie."), 300),
            summary=truncate(str(ab.get("summary", "")), 400),
            refs=sorted({r for s in steps for r in s.refs})))

    co = raw.get("coherence") if isinstance(raw.get("coherence"), dict) else None
    co_text = str((co or {}).get("summary", ""))
    external = re.search(r"\[[ES]\d+\]|\b(source|preuve|statistique|officiel|donnée|S\d|E\d)", co_text, re.IGNORECASE)
    if co and co.get("outcome") == "affaiblit" and co_text and not external:
        tests.append(ReasoningTest(kind="coherence", label=LABELS["coherence"], outcome="affaiblit",
                                   summary=truncate(str(co["summary"]), 400)))

    fallacies = [f for f in (raw.get("sophismes") or []) if isinstance(f, dict) and f.get("type")][:3]
    if fallacies:
        tests.append(ReasoningTest(
            kind="sophisme", label=LABELS["sophisme"], outcome="non_concluant",
            summary="Procédés repérés dans l'énoncé (sans effet sur le score, à signaler au lecteur).",
            steps=[ReasoningStep(text=f"{truncate(str(f['type']), 60)} : « {truncate(str(f.get('passage', '')), 160)} »",
                                 explanation=truncate(str(f.get("explanation", "")), 260)) for f in fallacies]))

    magnitude = magnitude_test(statistics)
    if magnitude:
        tests.insert(0, magnitude)
    return _ordered(tests)


def fallback_tests(evidence: list[Evidence], statistics: list[Statistic], universal: bool) -> list[ReasoningTest]:
    """Sans LLM : ordre de grandeur et contre-exemple tirés des positions déjà établies."""
    tests = []
    magnitude = magnitude_test(statistics)
    if magnitude:
        tests.append(magnitude)
    refuting = [e for e in evidence if e.stance == "refutes"]
    if refuting:
        strong = [e for e in refuting if e.official or e.reliability >= 0.6]
        tests.append(ReasoningTest(
            kind="contre_exemple", label=LABELS["contre_exemple"],
            outcome="refute" if strong and universal else "affaiblit",
            summary=f"{len(refuting)} source(s) décrivent un cas contraire"
                    + (" ; l'affirmation étant absolue, cela suffit à la réfuter." if strong and universal else "."),
            refs=[e.id for e in (strong or refuting)[:3]]))
    return _ordered(tests)


def _ordered(tests: list[ReasoningTest]) -> list[ReasoningTest]:
    order = list(LABELS)
    return sorted(tests, key=lambda t: order.index(t.kind))


def apply(score: float, weight: float, tests: list[ReasoningTest], universal: bool) -> tuple[float, float, float]:
    """Ajuste le score de vérité selon les tests fondés sur des preuves. Retourne (score, poids, ajustement)."""
    delta, cap, extra_weight = 0.0, 10.0, 0.0
    for t in tests:
        effect = ""
        if t.kind == "contre_exemple":
            if t.outcome == "refute" and universal:
                cap, effect = min(cap, 3.0), "Affirmation absolue réfutée par un contre-exemple : score plafonné à 3/10"
            elif t.outcome == "refute":
                delta, effect = delta - 1.0, "-1 point"
            elif t.outcome == "affaiblit":
                delta, effect = delta - 0.5, "-0,5 point"
        elif t.kind == "absurde":
            if t.outcome == "refute":
                delta, effect = delta - 1.5, "Conséquence nécessaire démentie : -1,5 point"
            elif t.outcome == "affaiblit":
                delta, effect = delta - 0.75, "-0,75 point"
            elif t.outcome == "compatible":
                delta, effect = delta + 0.5, "Conséquences vérifiées : +0,5 point"
        elif t.kind == "ordre_de_grandeur":
            if t.outcome == "refute":
                cap, effect = min(cap, 3.0), "Écart invraisemblable avec la donnée officielle : score plafonné à 3/10"
            elif t.outcome == "affaiblit":
                delta, effect = delta - 0.5, "-0,5 point"
            elif t.outcome == "compatible":
                delta, effect = delta + 0.5, "+0,5 point"
        elif t.kind == "coherence" and t.outcome == "affaiblit":
            delta, effect = delta - 0.5, "-0,5 point"
        if effect:
            t.effect = effect
            if t.outcome in ("refute", "compatible") and t.kind != "coherence":
                extra_weight += 0.3
    delta = max(-3.0, min(1.0, delta))
    new = round(max(0.0, min(cap, score + delta, 10.0)), 1)
    return new, round(weight + extra_weight, 2), round(new - score, 1)
