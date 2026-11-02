"""FMI, World Economic Outlook (DataMapper API, sans clé).

Complète la Banque mondiale : le FMI publie des estimations pour l'année en cours et des
prévisions. Les années postérieures à la dernière année révolue sont signalées comme estimations.
"""
from __future__ import annotations

from datetime import date

from .http import client, error_payload

BASE = "https://www.imf.org/external/datamapper/api/v1"

# code FMI -> (libellé, unité, facteur pour revenir à l'unité de base)
CATALOG: dict[str, tuple[str, str, float]] = {
    "PCPIPCH": ("Inflation (prix à la consommation, moyenne annuelle)", "% annuel", 1.0),
    "NGDP_RPCH": ("Croissance du PIB réel", "% annuel", 1.0),
    "NGDPD": ("PIB", "US$ courants", 1e9),
    "NGDPDPC": ("PIB par habitant", "US$ courants", 1.0),
    "LP": ("Population", "habitants", 1e6),
    "GGXWDG_NGDP": ("Dette publique brute", "% du PIB", 1.0),
    "LUR": ("Taux de chômage", "% de la population active", 1.0),
    "BCA_NGDPD": ("Solde des transactions courantes", "% du PIB", 1.0),
}

# Correspondance avec les indicateurs Banque mondiale choisis à l'extraction des affirmations.
FROM_WORLDBANK = {
    "FP.CPI.TOTL.ZG": "PCPIPCH",
    "NY.GDP.MKTP.KD.ZG": "NGDP_RPCH",
    "NY.GDP.MKTP.CD": "NGDPD",
    "NY.GDP.PCAP.CD": "NGDPDPC",
    "SP.POP.TOTL": "LP",
    "GC.DOD.TOTL.GD.ZS": "GGXWDG_NGDP",
    "SL.UEM.TOTL.ZS": "LUR",
}


async def indicator(indicator: str, country: str = "MDG", years: int = 8) -> dict:
    """Série récente d'un indicateur du FMI (WEO) pour un pays ISO3, avec l'estimation de l'année en cours."""
    if indicator not in CATALOG:
        return {"ok": False, "error": f"Indicateur FMI inconnu : {indicator}", "items": []}
    country = (country or "MDG").upper()
    try:
        async with client() as http:
            resp = await http.get(f"{BASE}/{indicator}/{country}")
            resp.raise_for_status()
            values = (resp.json().get("values") or {}).get(indicator, {}).get(country) or {}
        if not values:
            return {"ok": False, "error": f"FMI : aucune donnée {indicator} pour {country}", "items": []}
        label, unit, factor = CATALOG[indicator]
        this_year = date.today().year
        series = sorted(({"year": int(y), "value": float(v) * factor} for y, v in values.items()
                         if v is not None and int(y) <= this_year), key=lambda p: p["year"])[-years:]
        if not series:
            return {"ok": False, "error": f"FMI : aucune valeur récente pour {country}", "items": []}
        latest = series[-1]
        return {"ok": True, "items": [{
            "indicator_code": indicator,
            "indicator_name": label,
            "country": country,
            "country_code": country,
            "unit": unit,
            "series": series,
            "latest_year": latest["year"],
            "latest_value": latest["value"],
            # Le WEO couvre l'année en cours et la précédente par des estimations.
            "estimate_from_year": this_year - 1,
            "source_name": "FMI, World Economic Outlook",
            "source_url": f"https://www.imf.org/external/datamapper/{indicator}@WEO/{country}",
            "last_updated": None,
        }]}
    except Exception as exc:  # noqa: BLE001
        return error_payload(exc, "FMI")
