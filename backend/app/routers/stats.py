"""Recherche de statistiques à jour : Madagascar d'abord, comparaisons internationales ensuite.

Les données viennent de la Banque mondiale (valeurs officielles révolues) et du FMI (estimations de
l'année en cours), via la passerelle MCP. Les réponses sont gardées en mémoire quelques heures pour
ménager les API publiques.
"""
from __future__ import annotations

import asyncio
import time
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query

from ..auth import current_user
from ..mcp.gateway import get_gateway
from ..services import demo_activity
from ..tools import imf, worldbank

router = APIRouter(prefix="/api/stats", tags=["statistiques"])

Provider = Literal["worldbank", "imf"]
CACHE_TTL = 6 * 3600
_cache: dict[tuple, tuple[float, dict]] = {}

COUNTRY_NAMES: dict[str, str] = {
    "MDG": "Madagascar", "COM": "Comores", "MUS": "Maurice", "SYC": "Seychelles", "MOZ": "Mozambique",
    "ZAF": "Afrique du Sud", "KEN": "Kenya", "TZA": "Tanzanie", "ETH": "Éthiopie", "NGA": "Nigeria",
    "SEN": "Sénégal", "CIV": "Côte d'Ivoire", "CMR": "Cameroun", "COD": "RD Congo", "RWA": "Rwanda",
    "MAR": "Maroc", "DZA": "Algérie", "TUN": "Tunisie", "EGY": "Égypte", "FRA": "France", "BEL": "Belgique",
    "CHE": "Suisse", "DEU": "Allemagne", "GBR": "Royaume-Uni", "CAN": "Canada", "USA": "États-Unis",
    "BRA": "Brésil", "CHN": "Chine", "IND": "Inde", "JPN": "Japon", "RUS": "Russie",
    "WLD": "Monde", "SSF": "Afrique subsaharienne",
}
REGIONS = {"WLD", "SSF"}  # agrégats Banque mondiale, absents du FMI sous ces codes
NEIGHBOURS = ["MDG", "MUS", "COM", "MOZ", "SYC", "KEN", "TZA", "SSF"]

# Tableau de bord Madagascar : indicateurs clés, avec l'estimation FMI de l'année quand elle existe.
DASHBOARD = [
    "SP.POP.TOTL", "NY.GDP.MKTP.KD.ZG", "FP.CPI.TOTL.ZG", "NY.GDP.PCAP.CD", "SI.POV.DDAY",
    "EG.ELC.ACCS.ZS", "IT.NET.USER.ZS", "SP.DYN.LE00.IN", "SE.ADT.LITR.ZS", "GC.DOD.TOTL.GD.ZS",
]

THEMES: dict[str, list[str]] = {
    "Population": ["SP.POP.TOTL", "SP.POP.GROW", "SP.URB.TOTL.IN.ZS", "SP.DYN.LE00.IN"],
    "Économie": ["NY.GDP.MKTP.CD", "NY.GDP.PCAP.CD", "NY.GDP.MKTP.KD.ZG", "FP.CPI.TOTL.ZG", "SL.UEM.TOTL.ZS",
                 "NE.EXP.GNFS.ZS", "BX.KLT.DINV.CD.WD", "GC.DOD.TOTL.GD.ZS"],
    "Social": ["SI.POV.DDAY", "SH.DYN.MORT", "SH.STA.MMRT", "SE.ADT.LITR.ZS", "SE.PRM.ENRR", "SH.XPD.CHEX.GD.ZS"],
    "Infrastructures": ["EG.ELC.ACCS.ZS", "SH.H2O.BASW.ZS", "IT.NET.USER.ZS", "IT.CEL.SETS.P2"],
    "Environnement": ["AG.LND.FRST.ZS"],
}


async def _fetch(provider: Provider, code: str, country: str, years: int) -> dict:
    key = (provider, code, country, years)
    hit = _cache.get(key)
    if hit and time.monotonic() - hit[0] < CACHE_TTL:
        return hit[1]
    if provider == "imf":
        result = await get_gateway().call("imf_indicator", indicator=imf.FROM_WORLDBANK.get(code, code),
                                          country=country, years=years)
    else:
        result = await get_gateway().call("worldbank_indicator", indicator=code, country=country, years=years)
    if result.get("ok"):
        _cache[key] = (time.monotonic(), result)
    return result


def _item(result: dict, provider: Provider, code: str, country: str) -> dict[str, Any]:
    if not result.get("ok") or not result.get("items"):
        return {"ok": False, "provider": provider, "indicator_code": code, "country_code": country,
                "country": COUNTRY_NAMES.get(country, country), "error": result.get("error", "Aucune donnée")}
    item = dict(result["items"][0])
    label, unit, _ = worldbank.CATALOG.get(code, (item.get("indicator_name", code), item.get("unit", ""), []))
    item.update(ok=True, provider=provider, indicator_code=code, indicator_name=label, unit=unit,
                country_code=country, country=COUNTRY_NAMES.get(country, item.get("country", country)),
                source_name=item.get("source_name") or "Banque mondiale, World Development Indicators")
    if provider == "imf":
        item["provider_code"] = imf.FROM_WORLDBANK.get(code, code)
    return item


def _check(code: str, country: str) -> str:
    if code not in worldbank.CATALOG:
        raise HTTPException(404, f"Indicateur inconnu : {code}")
    country = country.upper()
    if country not in COUNTRY_NAMES:
        raise HTTPException(404, f"Pays non pris en charge : {country}")
    return country


@router.get("/catalog")
async def catalog(_: dict[str, Any] = Depends(current_user)):
    indicators = [{"code": code, "label": label, "unit": unit,
                   "theme": next((t for t, codes in THEMES.items() if code in codes), "Autres"),
                   "imf": code in imf.FROM_WORLDBANK}
                  for code, (label, unit, _) in worldbank.CATALOG.items()]
    countries = [{"code": c, "name": n, "region": c in REGIONS} for c, n in COUNTRY_NAMES.items()]
    return {"indicators": indicators, "themes": list(THEMES), "countries": countries, "neighbours": NEIGHBOURS}


@router.get("/series")
async def series(indicator: str, country: str = "MDG", years: int = Query(20, ge=3, le=40),
                 _: dict[str, Any] = Depends(current_user)):
    """Série d'un indicateur pour un pays : Banque mondiale, plus l'estimation FMI quand elle existe."""
    country = _check(indicator, country)
    calls = [_fetch("worldbank", indicator, country, years)]
    with_imf = indicator in imf.FROM_WORLDBANK and country not in REGIONS
    if with_imf:
        calls.append(_fetch("imf", indicator, country, min(years, 12)))
    results = await asyncio.gather(*calls)
    return {"worldbank": _item(results[0], "worldbank", indicator, country),
            "imf": _item(results[1], "imf", indicator, country) if with_imf else None}


@router.get("/compare")
async def compare(indicator: str, countries: str = ",".join(NEIGHBOURS),
                  _: dict[str, Any] = Depends(current_user)):
    """Dernière valeur disponible d'un indicateur pour plusieurs pays (10 au plus)."""
    codes = [c.strip().upper() for c in countries.split(",") if c.strip()][:10] or ["MDG"]
    for c in codes:
        _check(indicator, c)
    results = await asyncio.gather(*(_fetch("worldbank", indicator, c, 6) for c in codes))
    return [_item(r, "worldbank", indicator, c) for r, c in zip(results, codes)]


@router.get("/madagascar")
async def madagascar_dashboard(_: dict[str, Any] = Depends(current_user)):
    """Chiffres clés de Madagascar : dernière valeur officielle et, si disponible, estimation FMI récente."""
    async def one(code: str) -> dict:
        wb, im = await asyncio.gather(
            _fetch("worldbank", code, "MDG", 10),
            _fetch("imf", code, "MDG", 6) if code in imf.FROM_WORLDBANK else asyncio.sleep(0, {"ok": False}),
        )
        out = _item(wb, "worldbank", code, "MDG")
        out["imf"] = _item(im, "imf", code, "MDG") if code in imf.FROM_WORLDBANK and im.get("ok") else None
        return out

    return await asyncio.gather(*(one(c) for c in DASHBOARD))


@router.get("/activity")
async def platform_activity(_: dict[str, Any] = Depends(current_user)):
    """Activité par région (30 jours) et contenus truqués repérés. Données fictives de démonstration (`demo`)."""
    return demo_activity.activity()
