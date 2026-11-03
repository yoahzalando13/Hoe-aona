"""Compte lecteur : lire, aimer et commenter le fil ; aucune fonction de rédaction."""
import os
import tempfile

os.environ.setdefault("DATA_DIR", tempfile.mkdtemp(prefix="hoe-test-"))
os.environ["MCP_MODE"] = "direct"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


def _register(email, name, account_type=None):
    c = TestClient(app)
    payload = {"email": email, "password": "motdepasse1", "display_name": name}
    if account_type:
        payload["account_type"] = account_type
    r = c.post("/api/auth/register", json=payload)
    if r.status_code == 409:
        r = c.post("/api/auth/login", json={"email": email, "password": "motdepasse1"})
    assert r.status_code in (200, 201), r.text
    return c, r.json()


def test_lecteur_ne_voit_que_le_fil():
    media, _ = _register("redac@lecteur.mg", "Rédaction", "media")
    reader, me = _register("citoyen@lecteur.mg", "Citoyen", "reader")
    assert me["role"] == "reader"

    post = media.post("/api/posts", data={"body": "Fausse alerte cyclone : aucun bulletin."}).json()
    # Fil : lecture, J'apprécie, commentaires, profils.
    assert any(p["id"] == post["id"] for p in reader.get("/api/posts").json()["items"])
    assert reader.put(f"/api/posts/{post['id']}/like").json()["liked"] is True
    assert reader.post(f"/api/posts/{post['id']}/comments", json={"body": "Merci !"}).status_code == 201
    assert reader.get(f"/api/users/{post['author_id']}").status_code == 200
    assert reader.patch("/api/auth/me", json={"bio": "Lecteur à Fianarantsoa"}).status_code == 200

    # Aucune fonction de rédaction.
    assert reader.post("/api/posts", data={"body": "Je publie"}).status_code == 403
    for path in ("/api/analyses", "/api/analyses/stats", "/api/stats/activity", "/api/stats/catalog",
                 "/api/sources", "/api/settings", "/api/attestations/public-key"):
        assert reader.get(path).status_code == 403, path
    assert reader.post("/api/analyses", data={"text": "x"}).status_code == 403
    assert reader.get("/api/verifications/nearby", headers={"X-Hoe-Client": "android"}).status_code == 403
    assert reader.get("/api/admin/stats").status_code == 403


def test_administrateur_change_le_type_de_compte():
    admin, first = _register("premier@lecteur.mg", "Premier compte")
    from app.db import get_db
    get_db().update_user(first["id"], role="admin")  # la base est partagée avec les autres modules de test
    _, me = _register("citoyen@lecteur.mg", "Citoyen", "reader")
    assert admin.patch(f"/api/admin/users/{me['id']}", json={"role": "media"}).json()["role"] == "media"
    assert admin.patch(f"/api/admin/users/{me['id']}", json={"role": "reader"}).json()["role"] == "reader"
