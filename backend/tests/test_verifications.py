"""Vérification physique : rayon de 2 km (PostGIS), attribution unique, confidentialité des positions.

Nécessite une base PostgreSQL avec PostGIS : TEST_POSTGIS_URL=postgresql://... pytest tests/test_verifications.py
"""
import hashlib
import io
import os
import tempfile
from datetime import datetime, timedelta, timezone

import pytest

POSTGIS = os.environ.get("TEST_POSTGIS_URL")
pytestmark = pytest.mark.skipif(not POSTGIS, reason="TEST_POSTGIS_URL non défini")

os.environ.setdefault("DATA_DIR", tempfile.mkdtemp(prefix="hoe-test-"))
os.environ["MCP_MODE"] = "direct"
if POSTGIS:
    os.environ["POSTGIS_URL"] = POSTGIS

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

MOBILE = {"X-Hoe-Client": "android"}
ANALAKELY = (-18.9064, 47.5255)          # point de la demande
PRES = (-18.9100, 47.5300)               # environ 600 m
LOIN = (-18.8792, 47.5079)               # environ 3,5 km (Ivandry)
MG = timezone(timedelta(hours=3))


def _client(name):
    c = TestClient(app, headers=MOBILE)
    r = c.post("/api/auth/register", json={"email": f"{name}@verif.mg", "password": "motdepasse1",
                                          "display_name": name.capitalize(), "organization": "Radio test"})
    if r.status_code == 409:
        r = c.post("/api/auth/login", json={"email": f"{name}@verif.mg", "password": "motdepasse1"})
    assert r.status_code in (200, 201), r.text
    return c


@pytest.fixture(scope="module")
def clients():
    from app.config import get_settings
    from app.geo import get_geo
    get_settings().postgis_url = POSTGIS  # la configuration a pu être mise en cache par un autre module de test
    geo = get_geo()
    geo._exec("TRUNCATE verification_requests, user_locations CASCADE")
    return {n: _client(n) for n in ("demandeur", "proche", "voisin", "lointain")}


def _locate(c, point):
    assert c.put("/api/verifications/location", json={"latitude": point[0], "longitude": point[1]}).status_code == 204


@pytest.fixture(autouse=True)
def _fresh(clients):
    """Chaque test part sans demande en cours ; les positions sont remises à jour."""
    from app.geo import get_geo
    get_geo()._exec("TRUNCATE verification_requests CASCADE")
    _locate(clients["demandeur"], ANALAKELY)
    for name in ("proche", "voisin"):
        _locate(clients[name], PRES)
    _locate(clients["lointain"], LOIN)


def _request(c):
    r = c.post("/api/verifications", json={"claim": "Le marché d'Analakely est fermé ce matin",
                                           "place_label": "Marché d'Analakely", "latitude": ANALAKELY[0],
                                           "longitude": ANALAKELY[1]})
    assert r.status_code == 201, r.text
    return r.json()


def _photo(minutes_ago=0, camera=True):
    """JPEG avec EXIF d'appareil photo, heure de prise de vue en heure locale de Madagascar (UTC+3)."""
    from PIL import Image
    img = Image.new("RGB", (64, 48), (180, 40, 50))
    exif = Image.Exif()
    if camera:
        exif[0x010F], exif[0x0110] = "Samsung", "Galaxy A15"
    taken = (datetime.now(MG) - timedelta(minutes=minutes_ago)).strftime("%Y:%m:%d %H:%M:%S")
    exif.get_ifd(0x8769)[0x9003] = taken
    buf = io.BytesIO()
    img.save(buf, "JPEG", exif=exif)
    return buf.getvalue()


def _certified_report(c, req_id, outcome="incorrect", position=ANALAKELY, mock=False, photo=None):
    token = c.post(f"/api/verifications/{req_id}/capture").json()["token"]
    return c.post(f"/api/verifications/{req_id}/report",
                  data={"outcome": outcome, "report": "Le marché est ouvert, photo à l'appui.", "capture_token": token,
                        "latitude": position[0], "longitude": position[1], "accuracy": 12,
                        "mock_location": str(mock).lower(), "device_time": datetime.now(MG).isoformat()},
                  files={"photo": ("constat.jpg", photo or _photo(), "image/jpeg")})


def test_reserve_au_mobile(clients):
    web = TestClient(app, cookies=clients["demandeur"].cookies)
    assert web.get("/api/verifications/nearby").status_code == 403


def test_rayon_et_attribution_unique(clients):
    d, proche, voisin, lointain = (clients[k] for k in ("demandeur", "proche", "voisin", "lointain"))
    req = _request(d)
    assert req["status"] == "open" and req["role"] == "requester" and req["radius_m"] == 2000
    # Rien dans la réponse ne trahit les positions ou le nombre de comptes à proximité.
    assert not {"recipients", "distance", "distance_m"} & set(req)
    assert set(d.get("/api/verifications/location").json()) == {"sharing", "updated_at"}

    # Seuls les comptes à moins de 2 km reçoivent la demande ; jamais le demandeur.
    assert [r["id"] for r in proche.get("/api/verifications/nearby").json()] == [req["id"]]
    assert [r["id"] for r in voisin.get("/api/verifications/nearby").json()] == [req["id"]]
    assert lointain.get("/api/verifications/nearby").json() == []
    assert d.get("/api/verifications/nearby").json() == []
    assert lointain.get(f"/api/verifications/{req['id']}").status_code == 404
    notes = proche.get("/api/verifications/notifications", params={"undelivered": True}).json()
    assert [n["kind"] for n in notes] == ["verification_request"]
    assert proche.get("/api/verifications/notifications", params={"undelivered": True}).json() == []

    # Le premier qui accepte l'emporte ; l'annonce disparaît chez l'autre, le demandeur est prévenu.
    assert proche.post(f"/api/verifications/{req['id']}/accept").json()["status"] == "accepted"
    assert voisin.post(f"/api/verifications/{req['id']}/accept").status_code in (404, 409)
    assert voisin.get("/api/verifications/nearby").json() == []
    assert all(n["kind"] != "verification_request" for n in voisin.get("/api/verifications/notifications").json())
    assert [n["kind"] for n in d.get("/api/verifications/notifications").json()] == ["verification_accepted"]
    assert d.get(f"/api/verifications/{req['id']}").json()["verifier_name"] == "Proche"


def test_constat_certifie(clients):
    d, proche, voisin = clients["demandeur"], clients["proche"], clients["voisin"]
    req = _request(d)
    proche.post(f"/api/verifications/{req['id']}/accept")
    assert voisin.post(f"/api/verifications/{req['id']}/capture").status_code in (404, 409)
    photo = _photo()
    r = _certified_report(proche, req["id"], photo=photo)
    assert r.status_code == 200, r.text
    done = r.json()
    # Tous les contrôles passent : un seul constat suffit.
    assert done["status"] == "completed" and done["consensus"] == "single" and done["outcome"] == "incorrect"
    rep = done["reports"][0]
    assert rep["capture_verified"] and rep["on_site"] and rep["certified"] and not rep["mock_location"]
    assert rep["distance_bucket"] == "<50"
    assert rep["photo_sha256"] == hashlib.sha256(photo).hexdigest()

    # Certificat signé, vérifiable avec la clé publique ; aucune coordonnée du vérificateur.
    cert = d.get(rep["certificate_url"]).json()
    assert cert["signature_valid"] and cert["certificate"]["photo_sha256"] == rep["photo_sha256"]
    assert "latitude" not in str(cert["certificate"]) and "longitude" not in str(cert["certificate"])
    assert "BEGIN PUBLIC KEY" in d.get("/api/attestations/public-key").text
    from app import attestation
    forged = dict(cert["certificate"], outcome="correct")
    assert not attestation.verify(forged, cert["signature"])

    # Vérification par la photo elle-même : l'originale correspond, une retouche non.
    web = TestClient(app, cookies=d.cookies)
    ok = web.post("/api/attestations/verify", files={"photo": ("x.jpg", photo, "image/jpeg")})
    assert ok.status_code == 200 and ok.json()[0]["report_id"] == rep["id"]
    assert web.post("/api/attestations/verify", files={"photo": ("x.jpg", photo + b"0", "image/jpeg")}).status_code == 404
    assert d.get(rep["photo_url"]).status_code == 200
    assert [n["kind"] for n in d.get("/api/verifications/notifications").json()][0] == "verification_completed"


def test_second_avis_independant(clients):
    d, proche, voisin = clients["demandeur"], clients["proche"], clients["voisin"]
    req = _request(d)
    proche.post(f"/api/verifications/{req['id']}/accept")
    # Position simulée et jeton réutilisé : constat non certifié, second avis automatique.
    token = proche.post(f"/api/verifications/{req['id']}/capture").json()["token"]
    first = proche.post(f"/api/verifications/{req['id']}/report",
                        data={"outcome": "correct", "capture_token": token, "latitude": ANALAKELY[0],
                              "longitude": ANALAKELY[1], "accuracy": 10, "mock_location": "true",
                              "device_time": datetime.now(MG).isoformat()},
                        files={"photo": ("c.jpg", _photo(), "image/jpeg")}).json()
    assert first["status"] == "open" and first["required_reports"] == 2
    assert not first["reports"][0]["on_site"] and first["reports"][0]["mock_location"]
    assert "verification_second" in [n["kind"] for n in d.get("/api/verifications/notifications").json()]
    # Le premier vérificateur ne peut pas donner le second avis ; il garde la demande dans « Mes vérifications ».
    assert proche.post(f"/api/verifications/{req['id']}/accept").status_code == 409
    assert [r["id"] for r in proche.get("/api/verifications/assigned").json()] == [req["id"]]
    assert [r["id"] for r in voisin.get("/api/verifications/nearby").json()] == [req["id"]]

    # Le second vérificateur ne voit pas le premier constat avant de rendre le sien.
    taken = voisin.post(f"/api/verifications/{req['id']}/accept").json()
    assert taken["reports"] == []
    final = _certified_report(voisin, req["id"], outcome="incorrect").json()
    assert final["status"] == "completed" and final["consensus"] == "divergent" and final["outcome"] == "indetermine"
    assert len(final["reports"]) == 2
    assert len(proche.get(f"/api/verifications/{req['id']}").json()["reports"]) == 2  # visibles après clôture


def test_contestation(clients):
    d, proche, voisin = clients["demandeur"], clients["proche"], clients["voisin"]
    req = _request(d)
    proche.post(f"/api/verifications/{req['id']}/accept")
    assert _certified_report(proche, req["id"], outcome="correct").json()["consensus"] == "single"
    assert proche.post(f"/api/verifications/{req['id']}/dispute").status_code == 409  # réservé au demandeur
    reopened = d.post(f"/api/verifications/{req['id']}/dispute").json()
    assert reopened["status"] == "open" and reopened["required_reports"] == 2
    voisin.post(f"/api/verifications/{req['id']}/accept")
    final = _certified_report(voisin, req["id"], outcome="correct").json()
    assert final["consensus"] == "agreed" and final["outcome"] == "correct"


def test_controles_capture(clients):
    d, proche = clients["demandeur"], clients["proche"]
    req = _request(d)
    proche.post(f"/api/verifications/{req['id']}/accept")
    # Photo prise avant l'ouverture de l'appareil (ancienne photo de galerie) et position à 3,5 km.
    rep = _certified_report(proche, req["id"], position=LOIN, photo=_photo(minutes_ago=90)).json()["reports"][0]
    assert not rep["capture_verified"] and not rep["on_site"] and rep["distance_bucket"] == ">1000"


def test_renoncement_et_annulation(clients):
    d, proche, voisin = clients["demandeur"], clients["proche"], clients["voisin"]
    req = _request(d)
    proche.post(f"/api/verifications/{req['id']}/accept")
    # Le vérificateur renonce : la demande revient chez les autres, pas chez lui.
    assert proche.post(f"/api/verifications/{req['id']}/release").json()["status"] == "open"
    assert [r["id"] for r in voisin.get("/api/verifications/nearby").json()] == [req["id"]]
    assert proche.get("/api/verifications/nearby").json() == []
    # Annulation par le demandeur.
    assert d.post(f"/api/verifications/{req['id']}/cancel").json()["status"] == "cancelled"
    assert voisin.get("/api/verifications/nearby").json() == []


def test_positions_effacees(clients):
    d, proche = clients["demandeur"], clients["proche"]
    assert proche.delete("/api/verifications/location").status_code == 204
    assert proche.get("/api/verifications/location").json()["sharing"] is False
    req = _request(d)
    assert all(r["id"] != req["id"] for r in proche.get("/api/verifications/nearby").json())
    d.post(f"/api/verifications/{req['id']}/cancel")
    # La déconnexion efface aussi la position.
    _locate(proche, PRES)
    proche.post("/api/auth/logout")
    again = _client("proche")
    assert again.get("/api/verifications/location").json()["sharing"] is False
