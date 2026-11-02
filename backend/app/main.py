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
from .mcp.gateway import get_gateway
from .routers import analyses, settings as settings_router, system
from .services.pipeline import load_preferences

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    s = get_settings()
    db = get_db()
    db.mark_interrupted()
    for analysis_id in db.purge_older_than(load_preferences().history_retention_days):
        shutil.rmtree(s.data_dir / "uploads" / analysis_id, ignore_errors=True)
    gateway = get_gateway()
    await gateway.start()
    yield
    await gateway.stop()


app = FastAPI(title="Hoe-aona? API", version="1.0.0", lifespan=lifespan,
              description="Analyse de la désinformation : sources, véracité, contenus générés par IA.")
app.add_middleware(CORSMiddleware, allow_origins=get_settings().cors_origins,
                   allow_methods=["*"], allow_headers=["*"])
app.include_router(analyses.router)
app.include_router(settings_router.router)
app.include_router(system.router)

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
