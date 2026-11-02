"""Tavily : recherche web conçue pour les agents (offre gratuite : 1 000 crédits par mois)."""
from __future__ import annotations

from ..config import get_settings
from .http import client, error_payload, skipped


async def search(query: str, max_results: int = 6, days: int | None = None,
                 include_domains: list[str] | None = None, country: str | None = None) -> dict:
    """Recherche web ; option : limiter à une liste de domaines (sources officielles, presse nationale)."""
    key = get_settings().tavily_api_key
    if not key:
        return skipped("Tavily", "clé TAVILY_API_KEY absente")
    body = {"query": query[:380], "search_depth": "basic", "max_results": max_results,
            "include_answer": False, "include_images": False}
    if days:
        body["topic"] = "news"
        body["days"] = days
    if include_domains:
        body["include_domains"] = include_domains[:60]
    if country and not days:
        body["country"] = country  # priorise les résultats du pays (nom anglais, ex. "madagascar")
    try:
        async with client() as http:
            resp = await http.post("https://api.tavily.com/search", json=body,
                                   headers={"Authorization": f"Bearer {key}"})
            resp.raise_for_status()
            data = resp.json()
        items = [{
            "url": r.get("url"),
            "title": r.get("title", ""),
            "content": r.get("content", ""),
            "score": r.get("score"),
            "published_date": r.get("published_date"),
        } for r in data.get("results", []) if r.get("url")]
        return {"ok": True, "items": items}
    except Exception as exc:  # noqa: BLE001
        return error_payload(exc, "Tavily")
