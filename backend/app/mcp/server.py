"""Serveur MCP « hoe-aona-tools » (transport stdio).

Expose chaque source de preuves comme un outil MCP. Il est lancé automatiquement par le
backend (voir gateway.py), mais peut aussi être branché à n'importe quel client MCP :

    cd backend && python -m app.mcp.server
"""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from ..tools import factcheck, gdelt, sightengine, tavily, webpage, wikipedia, worldbank

mcp = FastMCP("hoe-aona-tools")


# Google Fact Check est désactivé pour ce projet. L'API Tavily est désormais
# la source principale pour les recherches web.
# @mcp.tool()
# async def factcheck_search(query: str, language: str = "fr", max_results: int = 6) -> dict:
#     """Fact-checks déjà publiés (ClaimReview via Google Fact Check Tools) correspondant à une affirmation."""
#     return await factcheck.search(query, language, max_results)
#
#
# @mcp.tool()
# async def factcheck_image_search(image_url: str, max_results: int = 6) -> dict:
#     """Fact-checks publiés portant sur une image accessible publiquement."""
#     return await factcheck.image_search(image_url, max_results)


@mcp.tool()
async def wikipedia_search(query: str, language: str = "fr", limit: int = 3) -> dict:
    """Résumés et images des articles Wikipedia les plus pertinents."""
    return await wikipedia.search(query, language, limit)


@mcp.tool()
async def news_search(query: str, language: str | None = None, timespan: str = "3months", max_records: int = 8) -> dict:
    """Articles de presse mondiaux récents (GDELT DOC 2.0, 65 langues, 3 derniers mois)."""
    return await gdelt.search(query, language, timespan, max_records)


@mcp.tool()
async def web_search(query: str, max_results: int = 6, days: int | None = None) -> dict:
    """Recherche web générale (Tavily) avec extraits."""
    return await tavily.search(query, max_results, days)


@mcp.tool()
async def worldbank_indicator(indicator: str, country: str = "MDG", years: int = 6) -> dict:
    """Dernières valeurs officielles d'un indicateur de la Banque mondiale (ex. SP.POP.TOTL, MDG)."""
    return await worldbank.indicator(indicator, country, years)


@mcp.tool()
async def fetch_page(url: str) -> dict:
    """Lit une page publique : texte éditorial, auteur, date, image principale, logiciel générateur."""
    return await webpage.fetch(url)


@mcp.tool()
async def detect_ai_image(image_base64: str | None = None, image_url: str | None = None) -> dict:
    """Probabilité qu'une image soit générée par IA (Sightengine, modèle genai)."""
    return await sightengine.detect_ai_image(image_base64, image_url)


if __name__ == "__main__":
    mcp.run()
