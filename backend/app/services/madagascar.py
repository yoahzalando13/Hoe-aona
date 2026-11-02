"""Contexte malgache : annuaire initial des sources officielles et domaines de la presse nationale.

Coordonnées relevées le 2 novembre 2026 sur les sites officiels eux-mêmes (page d'accueil ou contact).
Les administrateurs les tiennent à jour depuis le back office (page « Sources officielles ») ;
ce fichier ne sert qu'à remplir l'annuaire au premier lancement.
"""
from __future__ import annotations

from .textutils import strip_accents

VERIFIED_AT = "2026-11-02"

OFFICIAL_SOURCES: list[dict] = [
    {"name": "Institut National de la Statistique", "acronym": "INSTAT", "category": "Statistiques officielles",
     "website": "https://www.instat.mg", "phone": "+261 32 11 086 66",
     "address": "Rue Jules Ranaivo, Anosy, BP 485, Antananarivo 101",
     "topics": ["statistique", "population", "recensement", "habitants", "prix", "inflation", "pauvrete", "emploi",
                "chomage", "menages", "pib", "croissance", "indice des prix", "demographie", "naissances"]},
    {"name": "Banky Foiben'i Madagasikara (Banque centrale)", "acronym": "BFM", "category": "Institution monétaire",
     "website": "https://banque-centrale.mg",
     "topics": ["ariary", "taux de change", "euro", "dollar", "inflation", "monnaie", "billet", "banque",
                "reserves de change", "taux directeur", "credit", "devise"]},
    {"name": "Ministère de l'Économie et des Finances", "acronym": "MEF", "category": "Ministère",
     "website": "https://mef.gov.mg", "phone": "+261 38 30 000 11 / +261 32 05 222 05",
     "topics": ["budget", "loi de finances", "dette", "finances publiques", "croissance", "salaire", "fonctionnaires",
                "subvention", "carburant", "tresor", "economie", "investissement", "fmi", "bailleurs"]},
    {"name": "Présidence de la République", "acronym": "", "category": "Institution",
     "website": "https://presidency.gov.mg",
     "topics": ["president", "presidence", "chef de l'etat", "conseil des ministres", "decret", "discours"]},
    {"name": "Haute Cour Constitutionnelle", "acronym": "HCC", "category": "Institution",
     "website": "https://www.hcc.gov.mg", "email": "hcc@hcc.gov.mg", "address": "Rue Rabobalahy, BP 835, Antananarivo",
     "topics": ["constitution", "constitutionnel", "hcc", "resultats officiels", "investiture", "election", "decision"]},
    {"name": "Commission Électorale Nationale Indépendante", "acronym": "CENI", "category": "Institution",
     "website": "https://www.ceni-madagascar.mg",
     "topics": ["election", "electoral", "vote", "electeurs", "scrutin", "bureau de vote", "liste electorale",
                "candidat", "resultats provisoires", "fifidianana"]},
    {"name": "Sénat de Madagascar", "acronym": "", "category": "Parlement",
     "website": "https://senat.mg", "email": "contact@senat.mg",
     "topics": ["senat", "senateur", "loi", "parlement", "session parlementaire"]},
    {"name": "Assemblée nationale", "acronym": "", "category": "Parlement",
     "website": "https://assemblee-nationale.mg",
     "topics": ["assemblee nationale", "depute", "loi", "parlement", "session parlementaire", "motion"]},
    {"name": "Bureau National de Gestion des Risques et des Catastrophes", "acronym": "BNGRC", "category": "Gestion des risques",
     "website": "https://bngrc.gov.mg", "phone": "+261 34 05 480 68 / +261 34 05 480 69",
     "address": "Antanimora, route du Mausolée, Antananarivo 101",
     "topics": ["cyclone", "inondation", "catastrophe", "sinistres", "sinistre", "deplaces", "secheresse", "kere",
                "alerte", "victimes", "eboulement", "secours", "tempete"]},
    {"name": "Direction Générale de la Météorologie (Météo Madagascar)", "acronym": "DGM", "category": "Météorologie",
     "website": "https://www.meteomadagascar.mg", "phone": "+261 34 05 582 46 (communication)",
     "email": "comrp.meteomadagascar@gmail.com",
     "topics": ["meteo", "cyclone", "pluie", "temperature", "chaleur", "secheresse", "vent", "alerte", "climat",
                "tempete", "avis de cyclone"]},
    {"name": "Ministère de l'Éducation nationale", "acronym": "MEN", "category": "Ministère",
     "website": "https://www.education.gov.mg",
     "topics": ["ecole", "education", "eleves", "enseignants", "examen", "cepe", "bepc", "baccalaureat", "bac",
                "rentree scolaire", "lycee", "college"]},
    {"name": "Ministère de l'Enseignement supérieur et de la Recherche scientifique", "acronym": "MESupReS",
     "category": "Ministère", "website": "https://mesupres.gov.mg", "email": "commesupres@mesupres.mg",
     "topics": ["universite", "etudiants", "bourse", "enseignement superieur", "recherche", "master", "licence"]},
    {"name": "Ministère de l'Intérieur et de la Décentralisation", "acronym": "MID", "category": "Ministère",
     "website": "http://mid.gov.mg",
     "topics": ["commune", "maire", "fokontany", "decentralisation", "etat civil", "carte d'identite", "cin",
                "prefet", "region", "district"]},
    {"name": "Ministère de la Justice", "acronym": "", "category": "Ministère",
     "website": "https://www.justice.gov.mg",
     "topics": ["justice", "tribunal", "proces", "prison", "detenus", "juge", "condamne", "magistrat", "arrestation"]},
    {"name": "Bureau Indépendant Anti-Corruption", "acronym": "BIANCO", "category": "Lutte contre la corruption",
     "website": "https://www.bianco-mg.org", "email": "bianco.dg@bianco-mg.org",
     "phone": "+261 33 02 002 96 / +261 34 84 253 22 / +261 37 44 249 61",
     "topics": ["corruption", "pot-de-vin", "detournement", "bianco", "enrichissement illicite", "plainte"]},
    {"name": "Direction Générale des Douanes", "acronym": "DGD", "category": "Administration",
     "website": "https://www.douanes.gov.mg", "email": "assistance@douanes.mg",
     "topics": ["douane", "importation", "exportation", "saisie", "contrebande", "trafic", "port", "conteneur"]},
    {"name": "Direction Générale des Impôts", "acronym": "DGI", "category": "Administration",
     "website": "https://www.impots.mg",
     "topics": ["impot", "taxe", "tva", "fiscal", "fiscalite", "contribuable"]},
    {"name": "JIRAMA (eau et électricité)", "acronym": "JIRAMA", "category": "Entreprise publique",
     "website": "https://www.jirama.mg",
     "topics": ["jirama", "delestage", "electricite", "coupure", "eau potable", "courant", "tarif", "facture"]},
    {"name": "OMS, bureau de Madagascar", "acronym": "OMS", "category": "Institution internationale",
     "website": "https://www.afro.who.int/fr/countries/madagascar",
     "topics": ["sante", "epidemie", "vaccin", "vaccination", "paludisme", "peste", "rougeole", "cholera", "covid",
                "maladie", "hopital", "medicament", "mpox", "tuberculose"]},
    {"name": "UNFPA Madagascar", "acronym": "UNFPA", "category": "Institution internationale",
     "website": "https://madagascar.unfpa.org/fr",
     "topics": ["sante maternelle", "planification familiale", "grossesse", "demographie", "jeunes", "violences basees sur le genre"]},
    {"name": "Banque mondiale, Madagascar", "acronym": "", "category": "Institution internationale",
     "website": "https://www.worldbank.org/fr/country/madagascar",
     "topics": ["pauvrete", "croissance", "pib", "developpement", "financement", "projet", "electricite"]},
]

# Presse nationale (sites vérifiés joignables le 2 novembre 2026) : utilisée pour cibler la recherche web.
MG_MEDIA_DOMAINS = [
    "lexpress.mg", "midi-madagasikara.mg", "newsmada.com", "madagascar-tribune.com", "2424.mg",
    "lagazette-dgi.com", "moov.mg",
]


def official_domains() -> list[str]:
    from urllib.parse import urlparse
    out = []
    for s in OFFICIAL_SOURCES:
        host = (urlparse(s["website"]).hostname or "").removeprefix("www.")
        if host and host not in out:
            out.append(host)
    return out


MG_PLACES = [
    "madagascar", "malgache", "malagasy", "antananarivo", "tana", "toamasina", "tamatave", "mahajanga", "majunga",
    "fianarantsoa", "toliara", "tulear", "antsiranana", "diego", "antsirabe", "morondava", "nosy be", "sambava",
    "fort-dauphin", "taolagnaro", "ariary", "fokontany", "jirama", "analamanga",
]


def fold(text: str) -> str:
    return strip_accents((text or "").lower())


def is_madagascar(text: str, default_country: str) -> bool:
    """Le sujet concerne-t-il Madagascar ? Oui si un lieu malgache est cité, ou par défaut si le pays est MDG."""
    from ..tools.worldbank import guess_country
    low = fold(text)
    if any(p in low for p in MG_PLACES):
        return True
    named = guess_country(text, "")
    if named and named != "MDG":
        return False  # l'affirmation porte explicitement sur un autre pays
    return default_country.upper() == "MDG"
