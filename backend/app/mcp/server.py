"""Serveur MCP « hoe-aona-tools » (transport stdio).

Expose chaque source de preuves comme un outil MCP. Il est lancé automatiquement par le
backend (voir gateway.py), mais peut aussi être branché à n'importe quel client MCP :

    cd backend && python -m app.mcp.server
"""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from ..tools import gdelt, imf, newsdata, sightengine, tavily, webpage, wikipedia, worldbank

mcp = FastMCP("hoe-aona-tools")


@mcp.tool()
async def wikipedia_search(query: str, language: str = "fr", limit: int = 3) -> dict:
    """Résumés et images des articles Wikipedia les plus pertinents."""
    return await wikipedia.search(query, language, limit)


@mcp.tool()
async def news_search(query: str, language: str | None = None, timespan: str = "3months", max_records: int = 8,
                      source_country: str | None = None) -> dict:
    """Articles de presse mondiaux récents (GDELT DOC 2.0, 65 langues, 3 derniers mois)."""
    return await gdelt.search(query, language, timespan, max_records, source_country)


@mcp.tool()
async def news_madagascar(query: str, country: str = "mg", language: str = "fr,mg,en", max_results: int = 8) -> dict:
    """Actualités récentes publiées dans un pays (NewsData.io), Madagascar par défaut."""
    return await newsdata.search(query, country, language, max_results)


@mcp.tool()
async def web_search(query: str, max_results: int = 6, days: int | None = None,
                     include_domains: list[str] | None = None, country: str | None = None) -> dict:
    """Recherche web (Tavily) avec extraits ; `include_domains` limite aux sites indiqués."""
    return await tavily.search(query, max_results, days, include_domains, country)


@mcp.tool()
async def imf_indicator(indicator: str, country: str = "MDG", years: int = 8) -> dict:
    """Série récente d'un indicateur du FMI (WEO), avec l'estimation de l'année en cours (ex. PCPIPCH, MDG)."""
    return await imf.indicator(indicator, country, years)


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
