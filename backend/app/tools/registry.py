"""Registre unique des outils : utilisé par le serveur MCP et par le mode « direct »."""
from __future__ import annotations

from typing import Awaitable, Callable

from . import gdelt, sightengine, tavily, webpage, wikipedia, worldbank

ToolFn = Callable[..., Awaitable[dict]]

TOOLS: dict[str, tuple[ToolFn, str]] = {
    # Google Fact Check est temporairement désactivé : l'application ne s'appuie
    # que sur Tavily pour la recherche web générale.
    "wikipedia_search": (wikipedia.search, "Résumés d'articles Wikipedia pertinents, avec image"),
    "news_search": (gdelt.search, "Articles de presse mondiaux récents (GDELT DOC 2.0)"),
    "web_search": (tavily.search, "Recherche web générale (Tavily)"),
    "worldbank_indicator": (worldbank.indicator, "Dernières valeurs officielles d'un indicateur de la Banque mondiale"),
    "fetch_page": (webpage.fetch, "Lecture sécurisée d'une page : texte, auteur, date, image"),
    "detect_ai_image": (sightengine.detect_ai_image, "Probabilité qu'une image soit générée par IA (Sightengine)"),
}
