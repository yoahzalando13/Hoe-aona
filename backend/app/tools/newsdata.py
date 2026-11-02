"""NewsData.io : actualités récentes filtrées par pays (Madagascar : `mg`). Offre gratuite : 200 crédits/jour.

Le point d'accès `latest` couvre les 48 dernières heures environ : utile pour l'actualité chaude,
complété par GDELT (3 mois) et Tavily (web).
"""
from __future__ import annotations

import re

from ..config import get_settings
from .http import client, error_payload, skipped

BASE = "https://newsdata.io/api/1/latest"


def _query(text: str) -> str:
    words = [w for w in re.findall(r"[\wÀ-ÿ]+", text) if len(w) > 2][:6]
    return " ".join(words)[:100]


async def search(query: str, country: str = "mg", language: str = "fr,mg,en", max_results: int = 8) -> dict:
    """Articles d'actualité récents d'un pays (code ISO 3166-1 alpha-2, ex. mg) correspondant aux mots-clés."""
    key = get_settings().newsdata_api_key
    if not key:
        return skipped("NewsData.io", "clé NEWSDATA_API_KEY absente (presse malgache récente non interrogée)")
    q = _query(query)
    if not q:
        return {"ok": True, "items": []}
    params = {"apikey": key, "q": q, "language": language, "size": min(max_results, 10)}
    if country:
        params["country"] = country.lower()
    try:
        async with client() as http:
            resp = await http.get(BASE, params=params)
            resp.raise_for_status()
            data = resp.json()
        if data.get("status") != "success":
            message = (data.get("results") or {}).get("message", "réponse inattendue")
            return {"ok": False, "error": f"NewsData.io : {message}"[:200], "items": []}
        items = [{
            "url": a.get("link"),
            "title": a.get("title") or "",
            "description": a.get("description") or "",
            "published_at": (a.get("pubDate") or "")[:10] or None,
            "source": a.get("source_name") or a.get("source_id") or "",
            "source_url": a.get("source_url"),
            "image_url": a.get("image_url"),
            "country": a.get("country") or [],
        } for a in data.get("results", []) if a.get("link")]
        return {"ok": True, "items": items}
    except Exception as exc:  # noqa: BLE001
        return error_payload(exc, "NewsData.io")
