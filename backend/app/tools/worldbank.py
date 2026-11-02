"""API de la Banque mondiale (World Development Indicators), sans clé.

`mrnev=N` renvoie les N dernières valeurs non vides : la donnée affichée est toujours
la plus récente disponible, avec son année et la date de mise à jour de la base.
"""
from __future__ import annotations

from .http import client, error_payload

BASE = "https://api.worldbank.org/v2"

# code -> (libellé français, unité, mots-clés de détection)
CATALOG: dict[str, tuple[str, str, list[str]]] = {
    "SP.POP.TOTL": ("Population totale", "habitants", ["population", "habitants"]),
    "SP.POP.GROW": ("Croissance démographique", "% par an", ["croissance démographique"]),
    "SP.URB.TOTL.IN.ZS": ("Population urbaine", "% de la population", ["urbain", "villes"]),
    "NY.GDP.MKTP.CD": ("PIB", "US$ courants", ["pib", "produit intérieur brut", "gdp"]),
    "NY.GDP.PCAP.CD": ("PIB par habitant", "US$ courants", ["pib par habitant", "revenu par habitant"]),
    "NY.GDP.MKTP.KD.ZG": ("Croissance du PIB", "% annuel", ["croissance économique", "croissance du pib"]),
    "FP.CPI.TOTL.ZG": ("Inflation (prix à la consommation)", "% annuel", ["inflation", "hausse des prix"]),
    "SL.UEM.TOTL.ZS": ("Chômage", "% de la population active (estimation OIT)", ["chômage", "chomeurs"]),
    "SI.POV.DDAY": ("Pauvreté extrême (seuil international)", "% de la population", ["pauvreté", "pauvres"]),
    "SP.DYN.LE00.IN": ("Espérance de vie à la naissance", "années", ["espérance de vie"]),
    "SH.DYN.MORT": ("Mortalité des moins de 5 ans", "pour 1 000 naissances vivantes", ["mortalité infantile"]),
    "SH.STA.MMRT": ("Mortalité maternelle", "pour 100 000 naissances vivantes", ["mortalité maternelle"]),
    "SE.ADT.LITR.ZS": ("Alphabétisation des adultes", "% des 15 ans et plus", ["alphabétisation", "analphabétisme"]),
    "SE.PRM.ENRR": ("Scolarisation primaire (taux brut)", "%", ["scolarisation", "école primaire"]),
    "EG.ELC.ACCS.ZS": ("Accès à l'électricité", "% de la population", ["électricité", "délestage"]),
    "SH.H2O.BASW.ZS": ("Accès à l'eau potable de base", "% de la population", ["eau potable"]),
    "IT.NET.USER.ZS": ("Utilisateurs d'internet", "% de la population", ["internet"]),
    "IT.CEL.SETS.P2": ("Abonnements de téléphonie mobile", "pour 100 habitants", ["téléphone mobile"]),
    "AG.LND.FRST.ZS": ("Surface forestière", "% du territoire", ["forêt", "déforestation"]),
    "NE.EXP.GNFS.ZS": ("Exportations de biens et services", "% du PIB", ["exportations"]),
    "BX.KLT.DINV.CD.WD": ("Investissements directs étrangers (entrées nettes)", "US$ courants", ["investissements étrangers", "ide"]),
    "GC.DOD.TOTL.GD.ZS": ("Dette de l'administration centrale", "% du PIB", ["dette publique"]),
    "SH.XPD.CHEX.GD.ZS": ("Dépenses de santé", "% du PIB", ["dépenses de santé"]),
}

COUNTRIES = {
    "madagascar": "MDG", "france": "FRA", "comores": "COM", "maurice": "MUS", "seychelles": "SYC",
    "mozambique": "MOZ", "afrique du sud": "ZAF", "kenya": "KEN", "tanzanie": "TZA", "éthiopie": "ETH",
    "nigeria": "NGA", "sénégal": "SEN", "côte d'ivoire": "CIV", "cameroun": "CMR", "rdc": "COD",
    "maroc": "MAR", "algérie": "DZA", "tunisie": "TUN", "égypte": "EGY", "belgique": "BEL", "suisse": "CHE",
    "canada": "CAN", "états-unis": "USA", "etats-unis": "USA", "chine": "CHN", "inde": "IND", "japon": "JPN",
    "allemagne": "DEU", "royaume-uni": "GBR", "brésil": "BRA", "russie": "RUS", "monde": "WLD",
    "afrique subsaharienne": "SSF",
}


def catalog_for_prompt() -> str:
    return "; ".join(f"{code} = {label} ({unit})" for code, (label, unit, _) in CATALOG.items())


def guess_country(text: str, default: str = "MDG") -> str:
    low = (text or "").lower()
    for name, iso in COUNTRIES.items():
        if name in low:
            return iso
    return default


async def indicator(indicator: str, country: str = "MDG", years: int = 6) -> dict:
    """Dernières valeurs disponibles d'un indicateur de la Banque mondiale pour un pays (ISO3)."""
    if indicator not in CATALOG:
        return {"ok": False, "error": f"Indicateur inconnu : {indicator}", "items": []}
    country = (country or "MDG").upper()
    try:
        async with client() as http:
            resp = await http.get(f"{BASE}/country/{country}/indicator/{indicator}",
                                  params={"format": "json", "mrnev": years, "per_page": years})
            resp.raise_for_status()
            payload = resp.json()
        if not isinstance(payload, list) or len(payload) < 2 or not payload[1]:
            message = payload[0].get("message") if isinstance(payload, list) and payload else None
            return {"ok": False, "error": f"Banque mondiale : aucune donnée ({message or country})", "items": []}
        meta, rows = payload[0], payload[1]
        series = sorted(
            ({"year": int(r["date"]), "value": float(r["value"])} for r in rows if r.get("value") is not None),
            key=lambda p: p["year"],
        )
        label, unit, _ = CATALOG[indicator]
        latest = series[-1] if series else None
        return {"ok": True, "items": [{
            "indicator_code": indicator,
            "indicator_name": label,
            "indicator_name_source": rows[0].get("indicator", {}).get("value"),
            "country": rows[0].get("country", {}).get("value", country),
            "country_code": rows[0].get("countryiso3code") or country,
            "unit": unit,
            "series": series,
            "latest_year": latest["year"] if latest else None,
            "latest_value": latest["value"] if latest else None,
            "last_updated": meta.get("lastupdated"),
            "source_url": f"https://data.worldbank.org/indicator/{indicator}?locations={rows[0].get('country', {}).get('id', '')}",
        }]}
    except Exception as exc:  # noqa: BLE001
        return error_payload(exc, "Banque mondiale")
