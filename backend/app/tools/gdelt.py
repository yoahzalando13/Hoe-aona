"""GDELT DOC 2.0 : articles de presse mondiaux des trois derniers mois (sans clé).

Conditions d'utilisation : citer le GDELT Project (https://www.gdeltproject.org/).
"""
from __future__ import annotations

import asyncio
import re
import time

from .http import client, error_payload

BASE = "https://api.gdeltproject.org/api/v2/doc/doc"
# GDELT refuse plus d'une requête toutes les 5 secondes : les appels sont mis en file.
_MIN_INTERVAL = 5.2
_lock = asyncio.Lock()
_last_call = 0.0

# Codes pays FIPS utilisés par GDELT (sourcecountry), pour les pays de la zone.
FIPS = {"MDG": "MA", "COM": "CN", "MUS": "MP", "SYC": "SE", "MOZ": "MZ", "ZAF": "SF", "FRA": "FR"}

LANGS = {"fr": "french", "en": "english", "mg": "malagasy", "es": "spanish", "pt": "portuguese", "de": "german"}


def _clean_query(query: str) -> str:
    words = [w for w in re.findall(r"[\wÀ-ÿ]+", query) if len(w) > 2][:7]
    return " ".join(words)


async def search(query: str, language: str | None = None, timespan: str = "3months", max_records: int = 8,
                 source_country: str | None = None) -> dict:
    """Articles de presse récents correspondant aux mots-clés (option : pays des médias, ISO3)."""
    global _last_call
    q = _clean_query(query)
    if not q:
        return {"ok": True, "items": []}
    if language in LANGS:
        q = f"{q} sourcelang:{LANGS[language]}"
    if source_country and source_country.upper() in FIPS:
        q = f"{q} sourcecountry:{FIPS[source_country.upper()]}"
    params = {"query": q, "mode": "ArtList", "format": "json", "maxrecords": max_records,
              "sort": "HybridRel", "timespan": timespan}
    try:
        async with _lock:
            for attempt in range(2):  # une seconde tentative si GDELT signale un dépassement de cadence
                wait = _MIN_INTERVAL * (attempt + 1) - (time.monotonic() - _last_call)
                if wait > 0:
                    await asyncio.sleep(wait)
                try:
                    async with client() as http:
                        resp = await http.get(BASE, params=params)
                finally:
                    _last_call = time.monotonic()
                if resp.status_code != 429:
                    break
        resp.raise_for_status()
        if "json" not in resp.headers.get("content-type", "") and not resp.text.lstrip().startswith("{"):
            return {"ok": False, "error": f"GDELT : {resp.text.strip()[:160]}", "items": []}
        data = resp.json() if resp.text.strip() else {}
        items = [{
            "url": a.get("url"),
            "title": a.get("title", ""),
            "domain": a.get("domain"),
            "seen_date": a.get("seendate"),
            "language": a.get("language"),
            "source_country": a.get("sourcecountry"),
            "image_url": a.get("socialimage") or None,
        } for a in data.get("articles", []) if a.get("url")]
        return {"ok": True, "items": items}
    except Exception as exc:  # noqa: BLE001
        return error_payload(exc, "GDELT")
