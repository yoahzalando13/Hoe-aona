"""Google Fact Check Tools : désactivé pour ce projet.

La recherche web principale s'appuie désormais sur Tavily. Les fonctions ci-dessous
sont conservées comme code historique et renvoyent un statut explicite si elles sont
appelées par erreur.
"""
from __future__ import annotations


async def search(query: str, language: str = "fr", max_results: int = 6) -> dict:
    """Désactivé : Google Fact Check est volontairement hors service."""
    return {
        "ok": False,
        "error": "Google Fact Check est désactivé. Tavily est la source de recherche web utilisée par l'application.",
        "items": [],
    }


async def image_search(image_url: str, max_results: int = 6) -> dict:
    """Désactivé : Google Fact Check est volontairement hors service."""
    return {
        "ok": False,
        "error": "Google Fact Check est désactivé. Tavily est la source de recherche web utilisée par l'application.",
        "items": [],
    }
