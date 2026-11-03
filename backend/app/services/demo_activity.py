"""Activité de la plateforme par région et contenus truqués repérés : DONNÉES FICTIVES de démonstration.

Les chiffres sont générés de façon déterministe (graine fixe) pour illustrer les tableaux de bord.
Ils ne proviennent pas des analyses réelles ; l'API les marque `demo: true` et l'interface l'affiche.
"""
from __future__ import annotations

import random
from datetime import date

# 23 régions de Madagascar : chef-lieu, population estimée (ordre de grandeur), poids de connexion.
REGIONS: list[tuple[str, str, str, int, float]] = [
    ("ANA", "Analamanga", "Antananarivo", 3_900_000, 1.9),
    ("VAK", "Vakinankaratra", "Antsirabe", 2_100_000, 1.1),
    ("ITA", "Itasy", "Miarinarivo", 900_000, 0.8),
    ("BON", "Bongolava", "Tsiroanomandidy", 670_000, 0.55),
    ("HMA", "Haute Matsiatra", "Fianarantsoa", 1_450_000, 1.0),
    ("AMO", "Amoron'i Mania", "Ambositra", 840_000, 0.7),
    ("VAT", "Vatovavy", "Mananjary", 900_000, 0.55),
    ("FIT", "Fitovinany", "Manakara", 830_000, 0.6),
    ("IHO", "Ihorombe", "Ihosy", 420_000, 0.45),
    ("ASA", "Atsimo-Atsinanana", "Farafangana", 1_030_000, 0.5),
    ("ATS", "Atsinanana", "Toamasina", 1_480_000, 1.35),
    ("ANJ", "Analanjirofo", "Fenoarivo Atsinanana", 1_150_000, 0.7),
    ("ALM", "Alaotra-Mangoro", "Ambatondrazaka", 1_250_000, 0.8),
    ("BOE", "Boeny", "Mahajanga", 930_000, 1.3),
    ("SOF", "Sofia", "Antsohihy", 1_500_000, 0.6),
    ("BET", "Betsiboka", "Maevatanana", 390_000, 0.5),
    ("MEL", "Melaky", "Maintirano", 310_000, 0.4),
    ("ASO", "Atsimo-Andrefana", "Toliara", 1_800_000, 0.85),
    ("AND", "Androy", "Ambovombe", 900_000, 0.45),
    ("ANO", "Anosy", "Taolagnaro", 810_000, 0.75),
    ("MEN", "Menabe", "Morondava", 700_000, 0.7),
    ("DIA", "Diana", "Antsiranana", 890_000, 1.25),
    ("SAV", "Sava", "Sambava", 1_120_000, 0.8),
]

DEEPFAKE_KINDS = [
    ("image", "Images générées ou retouchées"),
    ("voix", "Voix clonées (notes vocales)"),
    ("video", "Vidéos truquées"),
    ("texte", "Textes rédigés par IA présentés comme témoignages"),
]

MONTHS = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."]


def _round(value: float, digits: int = 1) -> float:
    return round(value, digits)


def activity(today: date | None = None) -> dict:
    today = today or date.today()
    rng = random.Random(20261103)

    regions = []
    for code, name, capital, population, connectivity in REGIONS:
        analyses = int(population / 100_000 * connectivity * rng.uniform(7.5, 11.5))
        previous = int(analyses * rng.uniform(0.72, 1.18))
        verifications = int(analyses * rng.uniform(0.06, 0.16) * (1.3 if connectivity < 0.7 else 1.0))
        members = max(2, int(analyses * rng.uniform(0.18, 0.3)))
        media = int(analyses * rng.uniform(0.32, 0.48))  # images, audio, vidéos analysés
        deepfake_rate = rng.uniform(0.035, 0.11) * (1.25 if connectivity > 1.2 else 1.0)
        deepfakes = round(media * deepfake_rate)
        regions.append({
            "code": code, "name": name, "capital": capital, "population": population,
            "analyses": analyses, "verifications": verifications, "members": members,
            "rate_per_100k": _round(analyses / population * 100_000),
            "trend_pct": _round((analyses - previous) / previous * 100) if previous else None,
            "media_analysed": media, "deepfakes": deepfakes,
            "deepfake_rate": _round(deepfakes / media * 100) if media else 0.0,
        })

    total_media = sum(r["media_analysed"] for r in regions)
    total_fakes = sum(r["deepfakes"] for r in regions)
    shares = [0.46, 0.27, 0.15, 0.12]
    by_kind = [{"kind": k, "label": label, "count": round(total_fakes * share),
                "share": _round(share * 100)} for (k, label), share in zip(DEEPFAKE_KINDS, shares)]

    monthly = []
    for i in range(12):
        month_index = (today.month - 12 + i) % 12
        year = today.year if today.month - 12 + i >= 0 else today.year - 1
        analysed = int(total_media / 12 * (0.55 + i * 0.06) * rng.uniform(0.9, 1.1))
        rate = 3.2 + i * 0.42 + rng.uniform(-0.5, 0.5)  # hausse progressive des contenus générés
        monthly.append({"month": f"{MONTHS[month_index]} {str(year)[2:]}", "analysed": analysed,
                        "flagged": round(analysed * rate / 100), "rate": _round(rate)})

    total_analyses = sum(r["analyses"] for r in regions)
    return {
        "demo": True,
        "period_days": 30,
        "generated_on": today.isoformat(),
        "totals": {
            "analyses": total_analyses,
            "verifications": sum(r["verifications"] for r in regions),
            "members": sum(r["members"] for r in regions),
            "rate_per_100k": _round(total_analyses / sum(r["population"] for r in regions) * 100_000),
            "media_analysed": total_media,
            "deepfakes": total_fakes,
            "deepfake_rate": _round(total_fakes / total_media * 100) if total_media else 0.0,
        },
        "regions": sorted(regions, key=lambda r: r["rate_per_100k"], reverse=True),
        "deepfake_by_kind": by_kind,
        "deepfake_monthly": monthly,
    }
