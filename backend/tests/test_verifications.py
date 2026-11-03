"""Vérification physique : rayon de 2 km (PostGIS), attribution unique, confidentialité des positions.

Nécessite une base PostgreSQL avec PostGIS : TEST_POSTGIS_URL=postgresql://... pytest tests/test_verifications.py
"""
import os
import tempfile

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


def _request(c):
    r = c.post("/api/verifications", json={"claim": "Le marché d'Analakely est fermé ce matin",
                                           "place_label": "Marché d'Analakely", "latitude": ANALAKELY[0],
                                           "longitude": ANALAKELY[1]})
    assert r.status_code == 201, r.text
    return r.json()


def test_reserve_au_mobile(clients):
    web = TestClient(app, cookies=clients["demandeur"].cookies)
    assert web.get("/api/verifications/nearby").status_code == 403


def test_rayon_attribution_et_constat(clients):
    d, proche, voisin, lointain = (clients[k] for k in ("demandeur", "proche", "voisin", "lointain"))
    _locate(d, ANALAKELY)
    _locate(proche, PRES)
    _locate(voisin, PRES)
    _locate(lointain, LOIN)

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
    kinds = [n["kind"] for n in d.get("/api/verifications/notifications").json()]
    assert kinds == ["verification_accepted"]
    assert d.get(f"/api/verifications/{req['id']}").json()["verifier_name"] == "Proche"

    # Constat : seul le vérificateur le rend, le demandeur est notifié.
    assert voisin.post(f"/api/verifications/{req['id']}/report", data={"outcome": "correct"}).status_code == 404
    r = proche.post(f"/api/verifications/{req['id']}/report",
                    data={"outcome": "incorrect", "report": "Le marché est ouvert, photo à l'appui."},
                    files={"photo": ("marche.png", b"\x89PNG\r\n\x1a\n" + b"0" * 64, "image/png")})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "completed" and r.json()["outcome"] == "incorrect"
    done = d.get(f"/api/verifications/{req['id']}").json()
    assert done["report"].startswith("Le marché est ouvert") and done["photo_url"]
    assert d.get(done["photo_url"]).status_code == 200
    assert d.get("/api/verifications/notifications").json()[0]["kind"] == "verification_completed"


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
