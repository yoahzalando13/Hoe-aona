"""Repère les affirmations factuelles vérifiables dans le contenu soumis."""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from ..tools import worldbank
from .llm import LLMClient
from .textutils import keywords, numbers_in, split_sentences, truncate

log = logging.getLogger("hoe-aona.claims")

SYSTEM = (
    "Tu es un fact-checker professionnel. Tu identifies les affirmations vérifiables, sans juger leur "
    "véracité à cette étape. Tu réponds uniquement avec un objet JSON valide."
)


@dataclass
class ClaimDraft:
    text: str
    search_query: str
    search_query_en: str
    language: str
    indicator_code: str | None = None
    country_iso3: str | None = None
    claimed_value: str | None = None
    # Préparation des tests de raisonnement
    counter_query: str | None = None          # recherche d'un contre-exemple
    implications: list[dict] = field(default_factory=list)  # [{"consequence", "query"}] pour le test par l'absurde
    universal: bool = False                   # affirmation absolue (« tous », « jamais »…) : un contre-exemple suffit


LANG_NAMES = {"fr": "français", "en": "anglais", "mg": "malgache"}


def _prompt(text: str, max_claims: int, default_country: str, lang: str = "fr") -> str:
    return f"""Extrais au maximum {max_claims} affirmations factuelles VÉRIFIABLES du contenu ci-dessous :
chiffres, événements datés, citations attribuées, faits scientifiques ou sanitaires. Ignore les opinions,
les questions et les formules vagues. Classe-les de la plus importante à la moins importante.

Pour chaque affirmation :
- "text" : l'affirmation reformulée de façon autonome et précise (qui, quoi, où, quand), dans la langue d'origine ;
- "search_query" : 3 à 8 mots-clés pour la rechercher, dans la langue d'origine ;
- "search_query_en" : la même requête en anglais ;
- "language" : code ISO 639-1 de l'affirmation ;
- "statistic" : null, ou {{"indicator_code": "<code de la liste>", "country_iso3": "<ISO3>", "claimed_value": "<valeur annoncée telle quelle>"}}
  si l'affirmation porte sur une donnée couverte par un indicateur de cette liste : {worldbank.catalog_for_prompt()}
- "universal" : true si l'affirmation est absolue ou générale (« tous », « aucun », « jamais », « toujours », « 100 % »,
  « partout », « le seul ») : un seul contre-exemple fiable suffit alors à la réfuter ;
- "counter_query" : 3 à 8 mots-clés pour chercher un CONTRE-EXEMPLE ou un démenti (cas où l'affirmation ne se vérifie pas) ;
- "implications" : 1 ou 2 conséquences concrètes et vérifiables qui seraient FORCÉMENT observables si l'affirmation
  était vraie (test par l'absurde), chacune {{"consequence": "phrase", "query": "3 à 8 mots-clés pour la vérifier"}}.

Contexte : le public est principalement à Madagascar. Le contenu peut être en malgache (code "mg"), en français
ou mélanger les deux ; dans ce cas, écris "search_query" en français. Les lieux (Antananarivo, Toamasina…),
institutions (JIRAMA, BNGRC, CENI, HCC…) et montants en ariary désignent Madagascar.
Pays par défaut si aucun n'est précisé : {default_country}.
Écris "topic" et "summary" en {LANG_NAMES.get(lang, "français")} ; garde "text" et "search_query" dans la langue d'origine.
Format : {{"topic": "sujet en 6 mots maximum", "summary": "résumé neutre du contenu en une phrase", "claims": [...]}}

CONTENU :
\"\"\"{truncate(text, 12000)}\"\"\""""


UNIVERSAL_MARKERS = re.compile(
    r"\b(tous|toutes|tout le monde|aucun|aucune|personne ne|jamais|toujours|partout|nulle part|le seul|la seule|"
    r"100 ?%|sans exception|n'importe qui|chaque|all|every|never|always|nobody|none)\b", re.IGNORECASE)


def is_universal(text: str) -> bool:
    """Affirmation absolue : un seul contre-exemple fiable suffit à la réfuter."""
    return bool(UNIVERSAL_MARKERS.search(text or ""))


def _heuristic(text: str, max_claims: int, default_country: str) -> tuple[list[ClaimDraft], str, str]:
    """Sans LLM : phrases contenant chiffres, dates ou noms propres, les plus informatives d'abord."""
    scored = []
    for sentence in split_sentences(text):
        if len(sentence) < 30 or sentence.endswith("?"):
            continue
        score = 2 * len(numbers_in(sentence)) + len(re.findall(r"\b[A-ZÀ-Ý][a-zà-ÿ]{2,}", sentence[1:]))
        score += 1 if re.search(r"\b(19|20)\d{2}\b", sentence) else 0
        if score:
            scored.append((score, sentence))
    picked = [s for _, s in sorted(scored, key=lambda x: -x[0])[:max_claims]]
    drafts = []
    for sentence in picked:
        query = " ".join(keywords(sentence, 7))
        code = None
        low = sentence.lower()
        for indicator, (_, _, words) in worldbank.CATALOG.items():
            if any(w in low for w in words):
                code = indicator
                break
        drafts.append(ClaimDraft(truncate(sentence, 300), query, query, "fr", code,
                                 worldbank.guess_country(sentence, default_country) if code else None,
                                 (numbers_in(sentence) or [None])[0] if code else None,
                                 counter_query=f"démenti faux {query}"[:120], universal=is_universal(sentence)))
    first = split_sentences(text)[:1]
    return drafts, " ".join(keywords(text, 4)), truncate(first[0], 200) if first else ""


async def extract_claims(text: str, llm: LLMClient, max_claims: int, default_country: str,
                         warnings: list[str], lang: str = "fr") -> tuple[list[ClaimDraft], str, str]:
    """Retourne (affirmations, sujet, résumé)."""
    if not text.strip():
        return [], "", ""
    if llm.available:
        try:
            data = await llm.chat_json(SYSTEM, _prompt(text, max_claims, default_country, lang))
            drafts = []
            for c in data.get("claims", [])[:max_claims]:
                if not isinstance(c, dict) or not c.get("text"):
                    continue
                stat = c.get("statistic") or {}
                code = stat.get("indicator_code") if stat.get("indicator_code") in worldbank.CATALOG else None
                implications = [
                    {"consequence": truncate(str(i.get("consequence", "")), 240), "query": truncate(str(i.get("query", "")), 120)}
                    for i in (c.get("implications") or [])[:2]
                    if isinstance(i, dict) and i.get("consequence") and i.get("query")
                ]
                drafts.append(ClaimDraft(
                    text=truncate(c["text"], 400),
                    search_query=c.get("search_query") or " ".join(keywords(c["text"], 7)),
                    search_query_en=c.get("search_query_en") or c.get("search_query") or "",
                    language=(c.get("language") or "fr")[:2],
                    indicator_code=code,
                    country_iso3=(stat.get("country_iso3") or default_country).upper()[:3] if code else None,
                    claimed_value=str(stat.get("claimed_value")) if code and stat.get("claimed_value") else None,
                    counter_query=truncate(str(c.get("counter_query") or ""), 120) or None,
                    implications=implications,
                    universal=bool(c.get("universal")) or is_universal(c["text"]),
                ))
            if drafts:
                return drafts, data.get("topic", ""), data.get("summary", "")
            warnings.append("Le LLM n'a trouvé aucune affirmation vérifiable ; repli heuristique utilisé")
        except Exception as exc:  # noqa: BLE001
            log.warning("Extraction LLM échouée : %s", exc)
            warnings.append("Extraction des affirmations par LLM indisponible ; repli heuristique utilisé")
    else:
        warnings.append("Aucune clé LLM : affirmations repérées par heuristique (moins précises)")
    return _heuristic(text, max_claims, default_country)
