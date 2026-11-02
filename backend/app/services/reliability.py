"""Fiabilité d'une source (0 à 1) à partir du domaine et des métadonnées de la page.

La liste est volontairement explicite et modifiable : chaque rédaction peut l'adapter
à son contexte (médias locaux, institutions nationales).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from .textutils import domain_of

# (score, catégorie)
KNOWN: dict[str, tuple[float, str]] = {
    # Institutions et statistiques officielles
    "worldbank.org": (0.96, "statistiques officielles"),
    "data.worldbank.org": (0.96, "statistiques officielles"),
    "imf.org": (0.95, "institution internationale"),
    "who.int": (0.95, "institution internationale"),
    "un.org": (0.95, "institution internationale"),
    "unicef.org": (0.93, "institution internationale"),
    "undp.org": (0.92, "institution internationale"),
    "unesco.org": (0.92, "institution internationale"),
    "fao.org": (0.93, "institution internationale"),
    "wfp.org": (0.92, "institution internationale"),
    "ilo.org": (0.92, "institution internationale"),
    "afdb.org": (0.92, "institution internationale"),
    "oecd.org": (0.94, "institution internationale"),
    "europa.eu": (0.93, "institution internationale"),
    "ourworldindata.org": (0.90, "statistiques"),
    "insee.fr": (0.95, "statistiques officielles"),
    "instat.mg": (0.90, "statistiques officielles"),
    "banque-centrale.mg": (0.90, "institution nationale"),
    # Recherche
    "nature.com": (0.95, "revue scientifique"),
    "science.org": (0.95, "revue scientifique"),
    "thelancet.com": (0.95, "revue scientifique"),
    "nejm.org": (0.95, "revue scientifique"),
    "ncbi.nlm.nih.gov": (0.92, "base scientifique"),
    # Fact-checkers
    "factuel.afp.com": (0.93, "fact-checker"),
    "africacheck.org": (0.92, "fact-checker"),
    "fullfact.org": (0.92, "fact-checker"),
    "factcheck.org": (0.90, "fact-checker"),
    "snopes.com": (0.88, "fact-checker"),
    "politifact.com": (0.88, "fact-checker"),
    "observers.france24.com": (0.88, "fact-checker"),
    "lesurligneur.eu": (0.88, "fact-checker"),
    "pesacheck.org": (0.88, "fact-checker"),
    "healthfeedback.org": (0.88, "fact-checker"),
    "sciencefeedback.co": (0.88, "fact-checker"),
    "maldita.es": (0.88, "fact-checker"),
    "correctiv.org": (0.88, "fact-checker"),
    "leadstories.com": (0.85, "fact-checker"),
    # Agences et médias de référence
    "afp.com": (0.92, "agence de presse"),
    "reuters.com": (0.92, "agence de presse"),
    "apnews.com": (0.92, "agence de presse"),
    "bbc.com": (0.90, "média de référence"),
    "bbc.co.uk": (0.90, "média de référence"),
    "lemonde.fr": (0.88, "média de référence"),
    "rfi.fr": (0.88, "média de référence"),
    "france24.com": (0.87, "média de référence"),
    "francetvinfo.fr": (0.86, "média de référence"),
    "dw.com": (0.86, "média de référence"),
    "theguardian.com": (0.87, "média de référence"),
    "nytimes.com": (0.87, "média de référence"),
    "washingtonpost.com": (0.86, "média de référence"),
    "tv5monde.com": (0.84, "média de référence"),
    "lefigaro.fr": (0.84, "média de référence"),
    "liberation.fr": (0.84, "média de référence"),
    "jeuneafrique.com": (0.82, "média de référence"),
    "aljazeera.com": (0.80, "média de référence"),
    # Encyclopédie
    "wikipedia.org": (0.75, "encyclopédie collaborative"),
    # Médias malgaches (à compléter par la rédaction)
    "midi-madagasikara.mg": (0.70, "média national"),
    "lexpress.mg": (0.70, "média national"),
    "newsmada.com": (0.68, "média national"),
    "madagascar-tribune.com": (0.68, "média national"),
    "2424.mg": (0.60, "média en ligne"),
    # Plateformes sans contrôle éditorial
    "facebook.com": (0.30, "réseau social"),
    "x.com": (0.30, "réseau social"),
    "twitter.com": (0.30, "réseau social"),
    "instagram.com": (0.30, "réseau social"),
    "tiktok.com": (0.25, "réseau social"),
    "t.me": (0.25, "messagerie"),
    "whatsapp.com": (0.20, "messagerie"),
    "youtube.com": (0.40, "plateforme vidéo"),
    "reddit.com": (0.35, "forum"),
    "medium.com": (0.45, "plateforme de blog"),
    "substack.com": (0.45, "plateforme de blog"),
    "blogspot.com": (0.35, "plateforme de blog"),
    "wordpress.com": (0.35, "plateforme de blog"),
}

def _madagascar_entries() -> None:
    """Sources officielles et presse malgaches de l'annuaire initial."""
    from .madagascar import MG_MEDIA_DOMAINS, official_domains
    for domain in official_domains():
        KNOWN.setdefault(domain, (0.9, "source officielle"))
    for domain in MG_MEDIA_DOMAINS:
        KNOWN.setdefault(domain, (0.68, "média national"))


_madagascar_entries()

OFFICIAL_CATEGORIES = {"statistiques officielles", "institution internationale", "institution nationale",
                       "site gouvernemental", "organisation internationale", "source officielle", "statistiques"}


def is_official(category: str) -> bool:
    return category in OFFICIAL_CATEGORIES


SUFFIXES: list[tuple[str, float, str]] = [
    (".gouv.fr", 0.90, "site gouvernemental"),
    (".gov", 0.88, "site gouvernemental"),
    (".gov.mg", 0.85, "site gouvernemental"),
    (".gouv.mg", 0.85, "site gouvernemental"),
    (".int", 0.90, "organisation internationale"),
    (".edu", 0.82, "université"),
    (".ac.uk", 0.82, "université"),
    (".univ-antananarivo.mg", 0.80, "université"),
]


@dataclass
class Assessment:
    score: float
    category: str
    reasons: list[str]


def _lookup(domain: str) -> tuple[float, str] | None:
    parts = domain.split(".")
    for i in range(len(parts) - 1):
        candidate = ".".join(parts[i:])
        if candidate in KNOWN:
            return KNOWN[candidate]
    for suffix, score, cat in SUFFIXES:
        if domain.endswith(suffix) or ("." + domain).endswith(suffix):
            return score, cat
    return None


def category_of(url: str) -> str:
    found = _lookup(domain_of(url))
    return found[1] if found else "source non répertoriée"


def assess(url: str, meta: dict[str, Any] | None = None, ai_probability: float = 0.0) -> Assessment:
    meta = meta or {}
    domain = domain_of(url)
    reasons: list[str] = []
    found = _lookup(domain)
    if found:
        score, category = found
        reasons.append(f"{category.capitalize()} ({domain})")
    else:
        score, category = 0.5, "source non répertoriée"
        reasons.append(f"Domaine {domain or 'inconnu'} non répertorié : fiabilité non établie")

    if urlparse(url).scheme == "http":
        score -= 0.05
        reasons.append("Connexion non chiffrée (http)")
    if meta.get("author"):
        score += 0.04
        reasons.append("Auteur identifié")
    elif found is None:
        score -= 0.03
        reasons.append("Auteur non indiqué")
    if meta.get("published_at"):
        score += 0.03
        reasons.append("Publication datée")
    elif meta:
        score -= 0.04
        reasons.append("Date de publication absente")
    if ai_probability >= 0.5:
        score -= 0.25 * ai_probability
        reasons.append(f"Signatures de contenu IA ({round(ai_probability * 100)} %)")

    return Assessment(round(min(0.98, max(0.05, score)), 2), category, reasons)
