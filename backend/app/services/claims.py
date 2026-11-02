"""Repère les affirmations factuelles Hoe-aona?bles dans le contenu soumis."""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from ..tools import worldbank
from .llm import LLMClient
from .textutils import keywords, numbers_in, split_sentences, truncate

log = logging.getLogger("hoe-aona.claims")

SYSTEM = (
    "Tu es un fact-checker professionnel. Tu identifies les affirmations Hoe-aona?bles, sans juger leur "
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


def _prompt(text: str, max_claims: int, default_country: str) -> str:
    return f"""Extrais au maximum {max_claims} affirmations factuelles Hoe-aona?BLES du contenu ci-dessous :
chiffres, événements datés, citations attribuées, faits scientifiques ou sanitaires. Ignore les opinions,
les questions et les formules vagues. Classe-les de la plus importante à la moins importante.

Pour chaque affirmation :
- "text" : l'affirmation reformulée de façon autonome et précise (qui, quoi, où, quand), dans la langue d'origine ;
- "search_query" : 3 à 8 mots-clés pour la rechercher, dans la langue d'origine ;
- "search_query_en" : la même requête en anglais ;
- "language" : code ISO 639-1 de l'affirmation ;
- "statistic" : null, ou {{"indicator_code": "<code de la liste>", "country_iso3": "<ISO3>", "claimed_value": "<valeur annoncée telle quelle>"}}
  si l'affirmation porte sur une donnée couverte par un indicateur de cette liste : {worldbank.catalog_for_prompt()}

Pays par défaut si aucun n'est précisé : {default_country}.
Format : {{"topic": "sujet en 6 mots maximum", "summary": "résumé neutre du contenu en une phrase", "claims": [...]}}

CONTENU :
\"\"\"{truncate(text, 12000)}\"\"\""""


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
                                 (numbers_in(sentence) or [None])[0] if code else None))
    first = split_sentences(text)[:1]
    return drafts, " ".join(keywords(text, 4)), truncate(first[0], 200) if first else ""


async def extract_claims(text: str, llm: LLMClient, max_claims: int, default_country: str,
                         warnings: list[str]) -> tuple[list[ClaimDraft], str, str]:
    """Retourne (affirmations, sujet, résumé)."""
    if not text.strip():
        return [], "", ""
    if llm.available:
        try:
            data = await llm.chat_json(SYSTEM, _prompt(text, max_claims, default_country))
            drafts = []
            for c in data.get("claims", [])[:max_claims]:
                if not isinstance(c, dict) or not c.get("text"):
                    continue
                stat = c.get("statistic") or {}
                code = stat.get("indicator_code") if stat.get("indicator_code") in worldbank.CATALOG else None
                drafts.append(ClaimDraft(
                    text=truncate(c["text"], 400),
                    search_query=c.get("search_query") or " ".join(keywords(c["text"], 7)),
                    search_query_en=c.get("search_query_en") or c.get("search_query") or "",
                    language=(c.get("language") or "fr")[:2],
                    indicator_code=code,
                    country_iso3=(stat.get("country_iso3") or default_country).upper()[:3] if code else None,
                    claimed_value=str(stat.get("claimed_value")) if code and stat.get("claimed_value") else None,
                ))
            if drafts:
                return drafts, data.get("topic", ""), data.get("summary", "")
            warnings.append("Le LLM n'a trouvé aucune affirmation Hoe-aona?ble ; repli heuristique utilisé")
        except Exception as exc:  # noqa: BLE001
            log.warning("Extraction LLM échouée : %s", exc)
            warnings.append("Extraction des affirmations par LLM indisponible ; repli heuristique utilisé")
    else:
        warnings.append("Aucune clé LLM : affirmations repérées par heuristique (moins précises)")
    return _heuristic(text, max_claims, default_country)
