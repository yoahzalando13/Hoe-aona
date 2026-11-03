"""Fil média de démonstration : rédactions FICTIVES, analyses et publications d'exemple.

    python -m app.demo_feed           # crée les données (ne fait rien si elles existent déjà)
    python -m app.demo_feed --reset   # supprime puis recrée
    python -m app.demo_feed --remove  # supprime seulement

Tous les comptes ont une adresse @demo.hoe-aona.mg et la mention « Compte fictif de démonstration ».
Les médias, personnes et sources sont inventés ; les liens de preuve pointent vers un domaine de démonstration.
Mot de passe commun : demo-hoe-aona
"""
from __future__ import annotations

import argparse
import random
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .auth import hash_password
from .config import get_settings
from .db import get_db
from .schemas import AnalysisResult

DOMAIN = "demo.hoe-aona.mg"
PASSWORD = "demo-hoe-aona"
SOURCES = f"https://{DOMAIN}/sources"

ACCOUNTS = [
    ("rindra", "Rindra Rakotomalala", "Radio Fanantenana FM", "Antananarivo · journaliste radio, rubrique société."),
    ("hery", "Hery Andrianaivo", "Gazety Vaovao Atsimo", "Toliara · actualité du Grand Sud."),
    ("fara", "Fara Razafindrabe", "Télé Nosy Vaovao", "Toamasina · présentatrice du journal du soir."),
    ("tojo", "Tojo Randriamanana", "Mahajanga Hebdo Info", "Mahajanga · secrétaire de rédaction."),
    ("mialy", "Mialy Rasoanirina", "Sava Online", "Sambava · vanille, routes, vie locale."),
    ("lova", "Lova Rabearisoa", "Collectif Hamarino", "Fianarantsoa · vérificateurs citoyens bénévoles."),
]


def _evidence(i: int, stance: str, title: str, publisher: str, reliability: float, excerpt: str,
              official: bool = False) -> dict:
    return {"id": f"E{i}", "url": f"{SOURCES}/{uuid.uuid4().hex[:8]}", "title": title, "publisher": publisher,
            "domain": DOMAIN, "origin": "official" if official else "news", "category": "officiel" if official else "presse",
            "official": official, "published_at": (datetime.now(timezone.utc) - timedelta(days=i + 2)).date().isoformat(),
            "excerpt": excerpt, "reliability": reliability, "stance": stance, "confidence": 0.8}


def _criteria(source: float, veracity: float, ai: float, ai_note: str) -> list[dict]:
    return [
        {"key": "source", "label": "Fiabilité des sources", "score": source,
         "summary": "Sources concordantes et identifiées." if source >= 6 else "Origine du message inconnue, aucune source primaire."},
        {"key": "veracity", "label": "Véracité des données", "score": veracity,
         "summary": "Les chiffres correspondent aux relevés." if veracity >= 6 else "Les faits annoncés sont contredits par les sources."},
        {"key": "ai", "label": "Part d'IA", "score": ai, "summary": ai_note},
    ]


def _claim(text: str, score: float, verdict: str, label: str, conclusion: str, evidence: list[dict],
           reasoning: list[dict] | None = None, universal: bool = False) -> dict:
    return {"id": f"C{uuid.uuid4().hex[:4]}", "text": text, "search_query": text[:60], "truth_score": score,
            "verdict": verdict, "verdict_label": label, "conclusion": conclusion, "evidence": evidence,
            "reasoning": reasoning or [], "universal": universal,
            "arguments_for": [e["title"] for e in evidence if e["stance"] == "supports"],
            "arguments_against": [e["title"] for e in evidence if e["stance"] == "refutes"]}


# (clé, titre, type, score, verdict, libellé, résumé, critères, affirmations)
ANALYSES = [
    ("riz", "Le riz coûte 3 000 ariary le kilo partout", "text", 6.4, "plutot_fiable", "Plutôt fiable",
     "Le prix annoncé correspond aux relevés de la capitale, mais pas à ceux du Sud, nettement plus élevés.",
     _criteria(7.8, 5.6, 8.9, "Aucun signe de contenu généré."),
     [_claim("Le riz coûte 3 000 ariary le kilo partout à Madagascar.", 5.1, "mitige", "Mitigé",
             "Exact à Antananarivo, faux pour plusieurs districts du Sud où le kilo dépasse 3 600 ariary.",
             [_evidence(1, "supports", "Relevé mensuel des prix des produits de première nécessité", "Observatoire des prix (fictif)", .9,
                        "Prix moyen du riz local relevé à Antananarivo : 2 950 ariary le kilo.", official=True),
              _evidence(2, "refutes", "Dans le Grand Sud, le kilo de riz franchit les 3 600 ariary", "Gazety Vaovao Atsimo (fictif)", .7,
                        "Sur les marchés d'Ambovombe, les commerçants affichent 3 600 à 3 800 ariary.")],
             [{"kind": "contre_exemple", "label": "Contre-exemple", "outcome": "refute",
               "summary": "« Partout » est réfuté par un relevé fiable dans le Sud [E2].", "effect": "plafond 3/10 pour l'affirmation absolue"}],
             universal=True)]),
    ("cyclone", "Alerte cyclone de catégorie 5 sur Toamasina demain", "image", 2.1, "douteux", "Douteux",
     "Aucun bulletin météo officiel ne mentionne de cyclone ; la carte partagée est une image générée par IA.",
     _criteria(2.4, 1.8, 1.2, "Carte satellite générée par IA (signature de générateur dans les métadonnées)."),
     [_claim("Un cyclone de catégorie 5 frappera Toamasina demain.", 1.4, "faux", "Faux",
             "Aucun système dépressionnaire actif dans l'océan Indien sud-ouest à cette date.",
             [_evidence(1, "refutes", "Bulletin météorologique du jour : aucune perturbation tropicale", "Service météo (fictif)", .95,
                        "Aucune perturbation tropicale n'est suivie dans le bassin.", official=True)])]),
    ("courant", "Coupure générale d'électricité de 72 heures à Mahajanga", "text", 4.6, "a_verifier", "À vérifier",
     "Un délestage est confirmé dans deux quartiers, mais pas la coupure générale de 72 heures : vérification sur place demandée.",
     _criteria(5.2, 4.1, 8.1, "Texte rédigé par une personne."),
     [_claim("Toute la ville de Mahajanga sera privée d'électricité pendant 72 heures.", 3.6, "plutot_faux", "Plutôt faux",
             "Le programme publié ne prévoit que des délestages de 4 heures, par quartier.",
             [_evidence(1, "refutes", "Programme de délestage de la semaine", "Compagnie d'électricité (fictif)", .85,
                        "Délestages de 4 heures, quartiers Tsaramandroso et Mahabibo.", official=True),
              _evidence(2, "context", "Les habitants de Mahabibo dans le noir depuis la veille", "Mahajanga Hebdo Info (fictif)", .65,
                        "Plusieurs rues sans courant depuis 18 heures.")])]),
    ("bac", "Les sujets du baccalauréat ont fuité sur les réseaux sociaux", "image", 2.8, "douteux", "Douteux",
     "Les « sujets » partagés reprennent ceux de 2019 ; l'en-tête de la photo a été retouché.",
     _criteria(3.0, 2.5, 3.4, "Photo retouchée : incohérences de compression autour de la date."),
     [_claim("Les sujets de l'examen de cette année circulent avant l'épreuve.", 2.2, "faux", "Faux",
             "Le texte est identique à l'épreuve de 2019, archivée en ligne.",
             [_evidence(1, "refutes", "Annales 2019 : épreuve de philosophie", "Archives éducatives (fictif)", .9,
                        "Sujet 1 : « Peut-on être libre sans les autres ? »")])]),
    ("route", "La route Antsirabe – Ambositra est entièrement réhabilitée", "url", 6.9, "plutot_fiable", "Plutôt fiable",
     "Les travaux sont achevés sur 85 km ; un tronçon de 6 km reste en chantier.",
     _criteria(7.5, 6.4, 9.0, "Aucun signe de contenu généré."),
     [_claim("Les travaux de la route Antsirabe – Ambositra sont terminés.", 6.6, "plutot_vrai", "Plutôt vrai",
             "Presque vrai : le dernier tronçon sera livré dans deux mois.",
             [_evidence(1, "supports", "Point d'avancement des travaux routiers", "Agence routière (fictif)", .88,
                        "Avancement global : 93 %. Livraison du dernier tronçon prévue fin janvier.", official=True)])]),
    ("carburant", "Note vocale : le carburant deviendrait gratuit dès lundi", "audio", 1.6, "douteux", "Douteux",
     "La voix est clonée par IA ; aucune annonce de ce type n'a été faite.",
     _criteria(1.8, 1.5, 0.6, "Voix synthétique détectée (prosodie régulière, absence de bruit de souffle)."),
     [_claim("Le carburant sera distribué gratuitement à partir de lundi.", 0.9, "faux", "Faux",
             "Aucun communiqué, et les prix à la pompe restent inchangés selon les stations interrogées.",
             [_evidence(1, "refutes", "Prix à la pompe inchangés cette semaine", "Radio Fanantenana FM (fictif)", .7,
                        "Les gérants de stations n'ont reçu aucune consigne.")])]),
]

# (auteur, analyse jointe, image, il y a (heures), texte, commentaires [(auteur, texte)])
POSTS = [
    ("lova", "carburant", "verdict", 3,
     "🔴 FAUX — La note vocale qui annonce la gratuité du carburant dès lundi circule depuis ce matin sur WhatsApp. "
     "La voix est clonée par IA et aucune annonce n'existe. Ne la transférez pas.",
     [("fara", "On l'a reçue trois fois à la rédaction ce matin. Merci, on reprend au journal de 19 h."),
      ("rindra", "Même constat chez nous : plusieurs auditeurs ont appelé pour demander confirmation."),
      ("hery", "Elle arrive maintenant dans les groupes de Toliara.")]),
    ("fara", "cyclone", "verdict", 7,
     "Fausse alerte cyclone sur Toamasina : la « carte satellite » est une image générée. Le service météo ne suit "
     "aucune perturbation. Restez attentifs aux bulletins officiels.",
     [("tojo", "La même image circulait pour Mahajanga le mois dernier."),
      ("lova", "On l'ajoute à notre liste des visuels recyclés.")]),
    ("tojo", "courant", None, 20,
     "Coupure de 72 h à Mahajanga ? Non : délestages de 4 h par quartier selon le programme publié. Mahabibo reste "
     "sans courant depuis hier soir, une vérification sur place est en cours.",
     [("mialy", "Vous avez pu joindre quelqu'un sur place ?"),
      ("tojo", "Oui, un membre du réseau est allé constater : le courant est revenu à 9 h.")]),
    ("rindra", "riz", "chart", 30,
     "Prix du riz : 2 950 Ar le kilo à Antananarivo, mais plus de 3 600 Ar dans le Grand Sud. « Partout le même "
     "prix » est donc faux. Notre analyse complète, sources à l'appui :",
     [("hery", "Confirmé à Ambovombe hier : 3 700 Ar au marché."),
      ("fara", "Très utile pour notre sujet de jeudi sur le pouvoir d'achat.")]),
    ("mialy", "route", None, 52,
     "Route Antsirabe – Ambositra : 93 % des travaux achevés, il reste un tronçon de 6 km. Les photos « route "
     "terminée » qui circulent sont presque vraies, mais pas tout à fait.",
     [("lova", "Les automobilistes confirment des déviations vers le PK 210.")]),
    ("hery", "bac", "verdict", 75,
     "⚠️ Les « sujets du bac » partagés ce week-end sont ceux de 2019, avec une date retouchée. Inutile de les "
     "télécharger ou de payer pour les obtenir.",
     [("rindra", "Des groupes demandent 5 000 Ar pour « les corrigés ». C'est une arnaque."),
      ("mialy", "Partagé avec les associations de parents d'élèves."),
      ("tojo", "Bon travail sur la comparaison avec les annales.")]),
    ("lova", None, None, 100,
     "Rappel de méthode : avant de partager une capture d'écran, cherchez la source primaire (communiqué, bulletin, "
     "relevé). Pas de source, pas de partage. Notre fiche réflexe est épinglée sur notre page.",
     [("fara", "On la diffuse en malagasy à l'antenne cette semaine.")]),
    ("fara", None, None, 130,
     "Question aux rédactions : quelqu'un a-t-il vu passer la vidéo du « pont effondré » à Brickaville ? On "
     "cherche l'original avant de l'analyser.",
     [("tojo", "Elle date de 2022, inondations dans un autre pays. On a retrouvé la première publication."),
      ("lova", "Confirmé par une recherche d'image inversée.")]),
    ("rindra", None, None, 160,
     "Atelier vérification à Antananarivo samedi : comment lire un relevé de prix et un bulletin météo. Ouvert à "
     "toutes les rédactions membres.", []),
    ("mialy", None, None, 205,
     "Sava : la rumeur d'une « interdiction d'exporter la vanille » est sans fondement. Aucun texte en ce sens, "
     "les exportateurs interrogés n'ont reçu aucune instruction.",
     [("hery", "Merci, la question revenait souvent chez nos lecteurs.")]),
]


def _image(kind: str, title: str, verdict: str, score: float, path: Path) -> None:
    """Visuel de partage généré : fiche verdict ou petit graphique, aux couleurs du logo."""
    from PIL import Image, ImageDraw, ImageFont

    def font(size: int, bold: bool = False):
        for name in (("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"),
                     "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
            try:
                return ImageFont.truetype(name, size)
            except OSError:
                continue
        return ImageFont.load_default(size)

    img = Image.new("RGB", (1200, 675), (250, 247, 242))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 1200, 14], fill=(177, 13, 35))
    d.text((60, 50), "HOE-AONA ? · VÉRIFICATION", font=font(26, True), fill=(90, 82, 77))
    if kind == "verdict":
        color = (163, 20, 31) if score < 4.5 else (165, 104, 10) if score < 6.5 else (46, 107, 60)
        d.rectangle([60, 130, 420, 210], outline=color, width=5)
        d.text((84, 142), verdict.upper(), font=font(46, True), fill=color)
        words, lines, line = title.split(), [], ""
        for w in words:
            if len(line + " " + w) > 34:
                lines.append(line)
                line = w
            else:
                line = (line + " " + w).strip()
        lines.append(line)
        lines = lines[:4]
        for i, ln in enumerate(lines):
            d.text((60, 260 + i * 70), ln, font=font(52, True), fill=(31, 26, 23))
        # Score juste sous le titre, puis rognage : pas de grand vide quand le titre est court.
        bottom = 260 + len(lines) * 70 + 30
        d.text((60, bottom), f"Score {str(score).replace('.', ',')}/10 · données de démonstration", font=font(26), fill=(138, 128, 121))
        img = img.crop((0, 0, 1200, bottom + 80))
    else:
        d.text((60, 110), "Prix du kilo de riz local (ariary)", font=font(40, True), fill=(31, 26, 23))
        bars = [("Antananarivo", 2950), ("Fianarantsoa", 3050), ("Toamasina", 3200), ("Toliara", 3450), ("Ambovombe", 3700)]
        for i, (city, price) in enumerate(bars):
            y = 200 + i * 80
            w = int((price - 2000) / 1800 * 700)
            d.text((60, y + 8), city, font=font(30), fill=(90, 82, 77))
            d.rectangle([330, y, 330 + w, y + 50], fill=(177, 13, 35) if city == "Ambovombe" else (207, 196, 185))
            d.text((345 + w, y + 6), f"{price:,}".replace(",", " "), font=font(34, True), fill=(31, 26, 23))
        d.text((60, 610), "Relevés fictifs · données de démonstration", font=font(24), fill=(138, 128, 121))
    img.save(path, "PNG")


def _set_times(table: str, row_id: str, when: datetime, *cols: str) -> None:
    db = get_db()
    assignments = ", ".join(f"{c} = ?" for c in cols)
    with db._lock:
        db._conn.execute(f"UPDATE {table} SET {assignments} WHERE id = ?", (*[when.isoformat()] * len(cols), row_id))
        db._conn.commit()


def demo_users() -> list[dict]:
    db = get_db()
    return [u for u in (db.get_user_by_email(f"{k}@{DOMAIN}") for k, *_ in ACCOUNTS) if u]


def remove() -> int:
    """Supprime les comptes de démonstration, leurs analyses, publications, réactions et images."""
    db = get_db()
    users = demo_users()
    posts_dir = get_settings().data_dir / "posts"
    with db._lock:
        for u in users:
            for (image,) in db._conn.execute("SELECT image_path FROM posts WHERE user_id = ? AND image_path IS NOT NULL",
                                              (u["id"],)).fetchall():
                (posts_dir / image).unlink(missing_ok=True)
            db._conn.execute("DELETE FROM analyses WHERE user_id = ?", (u["id"],))
            db._conn.execute("DELETE FROM users WHERE id = ?", (u["id"],))  # publications, likes, commentaires en cascade
        db._conn.commit()
    return len(users)


def seed() -> dict[str, int]:
    db = get_db()
    if demo_users():
        return {"users": 0, "posts": 0}
    rng = random.Random(42)
    now = datetime.now(timezone.utc)
    users: dict[str, dict] = {}
    for key, name, org, bio in ACCOUNTS:
        u = db.create_user(f"{key}@{DOMAIN}", hash_password(PASSWORD), name, org, "media")
        db.update_user(u["id"], bio=f"{bio} Compte fictif de démonstration.")
        _set_times("users", u["id"], now - timedelta(days=rng.randint(40, 200)), "created_at")
        users[key] = u

    owners = {"riz": "rindra", "cyclone": "fara", "courant": "tojo", "bac": "hery", "route": "mialy", "carburant": "lova"}
    analyses: dict[str, tuple[str, dict]] = {}
    for key, title, kind, score, verdict, label, summary, criteria, claims in ANALYSES:
        result = AnalysisResult(global_score=score, verdict=verdict, verdict_label=label, summary=summary,
                                criteria=criteria, claims=claims,
                                inputs=[{"kind": kind, "name": "Contenu soumis", "extracted_chars": 240}],
                                weights={"source": .4, "veracity": .4, "ai": .2})
        aid = db.create_analysis(title, kind, [{"kind": "text", "text": title}], user_id=users[owners[key]]["id"])
        db.update_analysis(aid, status="done", progress=100, step="Terminé", global_score=score, verdict=verdict,
                           result=result.model_dump(mode="json"), workflow="publie", tags=["démo"])
        analyses[key] = (aid, {"title": title, "verdict": label, "score": score})

    posts_dir = get_settings().data_dir / "posts"
    count = 0
    for author, analysis_key, image_kind, hours, body, comments in POSTS:
        when = now - timedelta(hours=hours, minutes=rng.randint(0, 50))
        post_id = uuid.uuid4().hex[:16]
        image = None
        if image_kind:
            info = analyses[analysis_key][1] if analysis_key else {"title": body[:60], "verdict": "", "score": 0}
            image = f"{post_id}.png"
            _image(image_kind, info["title"], info["verdict"], info["score"], posts_dir / image)
        aid = analyses[analysis_key][0] if analysis_key else None
        db.create_post(users[author]["id"], body, aid, image, post_id)
        _set_times("posts", post_id, when, "created_at", "updated_at")
        for i, (who, text) in enumerate(comments):
            cid = db.add_comment(post_id, users[who]["id"], text)
            _set_times("comments", cid, when + timedelta(minutes=12 + 25 * i), "created_at")
        for key, u in users.items():
            if key != author and rng.random() < 0.65:
                db.set_like(post_id, u["id"], True)
        count += 1
    return {"users": len(users), "posts": count}


def main() -> None:
    parser = argparse.ArgumentParser(description="Fil média de démonstration (données fictives).")
    parser.add_argument("--reset", action="store_true", help="supprime puis recrée les données")
    parser.add_argument("--remove", action="store_true", help="supprime les données sans les recréer")
    args = parser.parse_args()
    if args.reset or args.remove:
        print(f"{remove()} comptes de démonstration supprimés.")
        if args.remove:
            return
    done = seed()
    if done["posts"]:
        print(f"{done['users']} rédactions fictives et {done['posts']} publications créées. Mot de passe : {PASSWORD}")
    else:
        print("Les données de démonstration existent déjà (--reset pour les recréer).")


if __name__ == "__main__":
    main()
