"""Fil média de démonstration : création rejouable, affichage dans le fil, suppression complète."""
import os
import tempfile

os.environ.setdefault("DATA_DIR", tempfile.mkdtemp(prefix="hoe-test-"))
os.environ["MCP_MODE"] = "direct"

from fastapi.testclient import TestClient  # noqa: E402

from app import demo_feed  # noqa: E402
from app.main import app  # noqa: E402


def test_fil_de_demonstration():
    demo_feed.remove()
    assert demo_feed.seed() == {"users": 6, "posts": len(demo_feed.POSTS)}
    assert demo_feed.seed() == {"users": 0, "posts": 0}  # rejouable sans doublon
    assert all(u["bio"].endswith("Compte fictif de démonstration.") for u in demo_feed.demo_users())

    c = TestClient(app)
    assert c.post("/api/auth/login", json={"email": f"lova@{demo_feed.DOMAIN}", "password": demo_feed.PASSWORD}).status_code == 200
    feed = c.get("/api/posts", params={"limit": 50}).json()
    demo = [p for p in feed["items"] if p["author_organization"] in {a[2] for a in demo_feed.ACCOUNTS}]
    assert len(demo) == len(demo_feed.POSTS)
    assert demo[0]["body"].startswith("🔴 FAUX")  # le plus récent en tête
    with_analysis = [p for p in demo if p["analysis"]]
    assert with_analysis and c.get(f"/api/analyses/{with_analysis[0]['analysis']['id']}").json()["result"]["claims"]
    with_image = [p for p in demo if p["image_url"]]
    assert len(with_image) == 4 and c.get(with_image[0]["image_url"]).headers["content-type"] == "image/png"
    assert sum(p["comments_count"] for p in demo) >= 15 and sum(p["likes"] for p in demo) > 0

    assert demo_feed.remove() == 6
    assert demo_feed.demo_users() == []
