"""Tests des règles pures (sans réseau) : `pytest` depuis le dossier backend."""
import io
from types import SimpleNamespace as NS

from app.services import ai_detection, reliability, scoring, textutils


# ---------- textutils ----------
def test_keywords_favorise_noms_propres_et_chiffres():
    kw = textutils.keywords("Madagascar compte 32 millions d'habitants selon la Banque mondiale en 2024")
    assert "madagascar" in kw and "32" in kw


def test_best_excerpt_trouve_le_bon_passage():
    paras = ["La météo sera clémente demain sur les hauts plateaux de la région.",
             "Selon la Banque mondiale, la population de Madagascar atteint 31,9 millions d'habitants en 2024."]
    excerpt, score = textutils.best_excerpt(paras, "Madagascar compte 32 millions d'habitants")
    assert "Banque mondiale" in excerpt and score > 0.3


def test_domain_of_retire_www():
    assert textutils.domain_of("https://www.lemonde.fr/article") == "lemonde.fr"


# ---------- fiabilité ----------
def test_fiabilite_institution_superieure_reseau_social():
    assert reliability.assess("https://data.worldbank.org/x").score > 0.9
    assert reliability.assess("https://www.facebook.com/post/1").score < 0.4


def test_fiabilite_sous_domaine_et_suffixe():
    assert reliability.assess("https://fr.wikipedia.org/wiki/Madagascar").category == "encyclopédie collaborative"
    assert reliability.assess("https://www.service-public.gouv.fr/x").score >= 0.85


def test_fiabilite_inconnue_sans_date_ni_auteur():
    a = reliability.assess("http://blog-inconnu.xyz/a", {"author": None, "published_at": None})
    assert a.score < 0.45 and any("non chiffrée" in r for r in a.reasons)


# ---------- détection IA ----------
def test_formule_assistant_detectee():
    r = ai_detection.text_signals("En tant qu'IA, je ne peux pas confirmer cette information. " * 3)
    assert r.probability >= 0.95


def test_texte_humain_faible_probabilite():
    texte = ("Hier soir, au marché d'Analakely, les vendeurs se plaignaient. Le riz a encore pris 200 ariary. "
             "Rakoto, qui vend des légumes depuis vingt ans, n'y croit plus ! Il dit que ça ne durera pas. "
             "Personne ne sait vraiment pourquoi les prix montent si vite cette saison, et les rumeurs vont bon train. "
             "Certains accusent les importateurs ; d'autres, la sécheresse dans le Sud. Une cliente hausse les épaules. "
             "« On fera avec », lâche-t-elle avant de repartir avec un demi-kapoaka.")
    assert ai_detection.text_signals(texte).probability < 0.3


def test_signature_iptc_image():
    data = b"\xff\xd8\xff" + b"x" * 100 + b"http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia"
    assert ai_detection.image_signatures(data).probability >= 0.95


def test_png_parametres_stable_diffusion():
    from PIL import Image, PngImagePlugin
    meta = PngImagePlugin.PngInfo()
    meta.add_text("parameters", "a cat, Steps: 20, Sampler: Euler a, CFG scale: 7")
    buf = io.BytesIO()
    Image.new("RGB", (8, 8)).save(buf, "PNG", pnginfo=meta)
    assert ai_detection.image_signatures(buf.getvalue()).probability >= 0.95


def test_metadonnees_pdf_chatgpt():
    assert ai_detection.metadata_signals({"Producer": "ChatGPT export"}).probability >= 0.8


# ---------- scores ----------
def ev(stance, reliability_=0.9, confidence=0.9, origin="news"):
    return NS(stance=stance, reliability=reliability_, confidence=confidence, origin=origin)


def test_verdict_factcheck():
    assert scoring.rating_to_stance("Faux")[0] == "refutes"
    assert scoring.rating_to_stance("Mostly True") == ("supports", 0.75)
    assert scoring.rating_to_stance("Not true")[0] == "refutes"
    assert scoring.rating_to_stance("Trompeur") == ("refutes", 0.5)


def test_sans_preuve_non_verifiable():
    score, weight = scoring.claim_truth([], [])
    assert score == 5.0 and scoring.claim_verdict(score, weight) == "non_verifiable"


def test_preuves_qui_contredisent():
    score, weight = scoring.claim_truth([ev("refutes", origin="factcheck"), ev("refutes")], [])
    assert score < 2 and scoring.claim_verdict(score, weight) == "faux"


def test_preuves_qui_confirment():
    score, weight = scoring.claim_truth([ev("supports"), ev("supports"), ev("context")], [NS(stance="supports")])
    assert score >= 8 and scoring.claim_verdict(score, weight) == "vrai"


def test_plafond_si_information_fausse():
    g = scoring.global_score(source=9, veracity=2, ai=10, ai_probability=0.05, weights=(0.4, 0.4, 0.2))
    assert g <= 4.4 and scoring.global_verdict(g) == "douteux"


def test_plafond_contenu_genere():
    g = scoring.global_score(source=9, veracity=9, ai=0.5, ai_probability=0.95, weights=(0.4, 0.4, 0.2))
    assert g <= 5.9


def test_exemple_maquette():
    g = scoring.global_score(8.5, 6.5, 8.0, 0.18, (0.4, 0.4, 0.2))
    assert g == 7.6 and scoring.global_verdict(g) == "plutot_fiable"
