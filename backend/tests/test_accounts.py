"""Comptes, cloisonnement des analyses, réseau social et administration (API de bout en bout)."""
import os
import tempfile

import pytest

os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="hoe-test-")
os.environ["MCP_MODE"] = "direct"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.db import get_db  # noqa: E402


def _client(email, name, password="motdepasse1"):
    c = TestClient(app)
    r = c.post("/api/auth/register", json={"email": email, "password": password, "display_name": name,
                                          "organization": "Radio test"})
    assert r.status_code == 201, r.text
    return c, r.json()


@pytest.fixture(scope="module")
def users():
    admin, admin_user = _client("admin@test.mg", "Admin")
    alice, alice_user = _client("alice@test.mg", "Alice")
    bob, bob_user = _client("bob@test.mg", "Bob")
    return {"admin": (admin, admin_user), "alice": (alice, alice_user), "bob": (bob, bob_user)}


def _done_analysis(user_id, title="Le riz coûte 3000 Ar"):
    db = get_db()
    aid = db.create_analysis(title, "text", [{"kind": "text", "text": title}], user_id=user_id)
    db.update_analysis(aid, status="done", progress=100, global_score=7.2, verdict="plutot_fiable")
    return aid


def test_roles_et_auth(users):
    assert users["admin"][1]["role"] == "admin"
    assert users["alice"][1]["role"] == "media"
    assert TestClient(app).get("/api/analyses").status_code == 401
    assert users["alice"][0].get("/api/auth/me").json()["email"] == "alice@test.mg"
    bad = TestClient(app).post("/api/auth/login", json={"email": "alice@test.mg", "password": "faux"})
    assert bad.status_code == 401


def test_cloisonnement_des_analyses(users):
    alice, a = users["alice"]
    bob, _ = users["bob"]
    aid = _done_analysis(a["id"])
    assert alice.get(f"/api/analyses/{aid}").json()["editable"] is True
    assert bob.get(f"/api/analyses/{aid}").status_code == 404
    assert all(i["id"] != aid for i in bob.get("/api/analyses").json()["items"])
    r = alice.patch(f"/api/analyses/{aid}", json={"notes": "À recouper", "tags": ["économie", "Économie", "prix"],
                                                   "workflow": "en_revue"})
    assert r.json()["tags"] == ["économie", "prix"] and r.json()["workflow"] == "en_revue"
    assert bob.patch(f"/api/analyses/{aid}", json={"notes": "x"}).status_code == 404
    assert alice.get("/api/analyses", params={"tag": "prix"}).json()["total"] == 1
    st = alice.get("/api/analyses/stats").json()
    assert st["total"] >= 1 and st["by_workflow"]["en_revue"] == 1
    assert "À recouper" in alice.get("/api/analyses/export.csv").text


def test_publication_et_reactions(users):
    alice, a = users["alice"]
    bob, _ = users["bob"]
    admin, _ = users["admin"]
    aid = _done_analysis(a["id"], "Intox sur le vaccin")
    assert bob.post("/api/posts", data={"body": "vol", "analysis_id": aid}).status_code == 404
    post = alice.post("/api/posts", data={"body": "Notre vérification du jour", "analysis_id": aid}).json()
    assert post["analysis"]["id"] == aid and post["can_edit"]
    # Une analyse publiée devient lisible (lecture seule) par les autres comptes.
    seen = bob.get(f"/api/analyses/{aid}").json()
    assert seen["editable"] is False and seen["owner_name"] == "Alice"
    assert bob.put(f"/api/posts/{post['id']}/like").json()["likes"] == 1
    comments = bob.post(f"/api/posts/{post['id']}/comments", json={"body": "Merci !"}).json()
    assert comments[0]["author_name"] == "Bob"
    assert bob.patch(f"/api/posts/{post['id']}", json={"body": "pirate"}).status_code == 403
    # Modération : publication masquée pour les autres, visible pour l'auteur et l'administration.
    assert admin.put(f"/api/admin/posts/{post['id']}/hidden").json()["hidden"] is True
    assert bob.get(f"/api/posts/{post['id']}").status_code == 404
    assert bob.get(f"/api/analyses/{aid}").status_code == 404
    assert alice.get(f"/api/posts/{post['id']}").status_code == 200
    admin.delete(f"/api/admin/posts/{post['id']}/hidden")
    assert bob.delete(f"/api/posts/{post['id']}").status_code == 403
    assert admin.delete(f"/api/posts/{post['id']}").status_code == 204


def test_administration(users):
    admin, admin_user = users["admin"]
    alice, a = users["alice"]
    bob, b = users["bob"]
    assert alice.get("/api/admin/users").status_code == 403
    assert len(admin.get("/api/admin/users").json()) == 3
    assert admin.patch(f"/api/admin/users/{admin_user['id']}", json={"role": "media"}).status_code == 409
    assert admin.patch(f"/api/admin/users/{b['id']}", json={"active": False}).json()["active"] is False
    assert bob.get("/api/auth/me").status_code == 401  # sessions révoquées
    assert admin.get("/api/admin/stats").json()["users"] == 3


def test_preferences_propres_a_chaque_compte(users):
    alice, _ = users["alice"]
    admin, _ = users["admin"]
    prefs = alice.get("/api/settings").json()
    prefs["default_country"] = "FRA"
    alice.put("/api/settings", json=prefs)
    assert alice.get("/api/settings").json()["default_country"] == "FRA"
    assert admin.get("/api/settings").json()["default_country"] == "MDG"


# ---------- annuaire officiel, contacts et fil comme source ----------
def test_annuaire_initial_et_droits(users):
    alice, _ = users["alice"]
    admin, _ = users["admin"]
    sources = alice.get("/api/sources").json()
    instat = next(s for s in sources if s["acronym"] == "INSTAT")
    assert instat["website"] == "https://www.instat.mg" and instat["phone"].startswith("+261")
    assert alice.post("/api/sources", json={"name": "Faux ministère"}).status_code == 403
    created = admin.post("/api/sources", json={"name": "Ministère de la Santé publique", "website": "sante.example.mg",
                                               "topics": ["Santé", "vaccin", "santé"]}).json()
    assert created["website"] == "https://sante.example.mg" and created["topics"] == ["santé", "vaccin"]
    assert admin.delete(f"/api/sources/{created['id']}").status_code == 204


def test_contacts_selon_le_sujet():
    from app.services.evidence import match_contacts
    sources = get_db().list_sources()
    names = [c.acronym for c in match_contacts("Le cyclone a fait 12 sinistrés à Toamasina selon la météo", sources, False)]
    assert "BNGRC" in names
    assert [c.acronym for c in match_contacts("L'inflation atteint 8 %", sources, True)][:2] != []
    assert match_contacts("Un texte sans sujet institutionnel", sources, False) == []


def test_publications_du_fil_comme_preuves(users):
    from app.services.claims import ClaimDraft
    from app.services.evidence import _community_candidates
    alice, a = users["alice"]
    aid = _done_analysis(a["id"], "Délestages JIRAMA à Antananarivo")
    alice.post("/api/posts", data={"body": "La JIRAMA annonce des délestages de quatre heures à Antananarivo cette semaine.",
                                   "analysis_id": aid})
    draft = ClaimDraft("La JIRAMA impose des délestages de quatre heures à Antananarivo", "délestages JIRAMA Antananarivo",
                       "power cuts", "fr")
    found = _community_candidates(draft)
    assert found and found[0].origin == "community" and found[0].url.startswith("/publication/")
    assert found[0].rating and found[0].reliability == 0.65


def test_cible_madagascar():
    from app.services import madagascar
    assert madagascar.is_madagascar("Le prix du riz à Toamasina", "FRA")
    assert madagascar.is_madagascar("Le prix du riz a doublé", "MDG")
    assert not madagascar.is_madagascar("Le chômage en France a baissé", "MDG")
