"""Point d'entrée FastAPI : `uvicorn app.main:app --reload` depuis le dossier backend."""
from __future__ import annotations

import logging
import shutil
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from .config import get_settings
from .db import get_db
from .geo import get_geo
from .mcp.gateway import get_gateway
from .routers import (admin, analyses, auth as auth_router, settings as settings_router, social, sources, stats, system,
                      verifications)
from .services.pipeline import load_preferences

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    s = get_settings()
    db = get_db()
    db.mark_interrupted()
    db.purge_sessions()
    # Rétention propre à chaque compte ; les analyses sans propriétaire suivent la valeur par défaut.
    expired = db.purge_older_than(load_preferences().history_retention_days)
    for user in db.list_users():
        expired += db.purge_older_than(load_preferences(user["id"]).history_retention_days, user["id"])
    for analysis_id in expired:
        shutil.rmtree(s.data_dir / "uploads" / analysis_id, ignore_errors=True)
    if geo := get_geo():  # sans PostGIS, seule la vérification physique est désactivée
        geo.purge_locations(s.location_max_age_minutes)
    gateway = get_gateway()
    await gateway.start()
    yield
    await gateway.stop()


app = FastAPI(title="Hoe-aona? API", version="1.0.0", lifespan=lifespan,
              description="Analyse de la désinformation : sources, véracité, contenus générés par IA.")
app.add_middleware(CORSMiddleware, allow_origins=get_settings().cors_origins,
                   allow_methods=["*"], allow_headers=["*"], allow_credentials=True)
app.include_router(auth_router.router)
app.include_router(analyses.router)
app.include_router(social.router)
app.include_router(admin.router)
app.include_router(sources.router)
app.include_router(stats.router)
app.include_router(settings_router.router)
app.include_router(system.router)
app.include_router(verifications.router)

# En production, le build Angular peut être servi par FastAPI (une seule origine).
_dist = get_settings().frontend_dist
if _dist.exists():
    @app.get("/{path:path}", include_in_schema=False)
    async def spa(path: str):
        if path.startswith("api/"):
            raise HTTPException(404, "Route inconnue")
        target = (_dist / path).resolve()
        if path and target.is_file() and _dist.resolve() in target.parents:
            return FileResponse(target)
        return FileResponse(_dist / "index.html")
