"""Annuaire des sources officielles : consultable par tous les comptes, tenu à jour par l'administration."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from ..auth import current_user, require_admin
from ..db import get_db
from ..schemas import OfficialSourceIn, OfficialSourceOut

router = APIRouter(prefix="/api/sources", tags=["sources officielles"])


@router.get("", response_model=list[OfficialSourceOut])
async def list_sources(q: str = "", all: bool = False, user: dict[str, Any] = Depends(current_user)):
    return get_db().list_sources(q.strip(), include_inactive=all and user["role"] == "admin")


@router.post("", response_model=OfficialSourceOut, status_code=201)
async def create_source(payload: OfficialSourceIn, _: dict[str, Any] = Depends(require_admin)):
    db = get_db()
    return db.get_source(db.save_source(payload.model_dump()))


@router.put("/{source_id}", response_model=OfficialSourceOut)
async def update_source(source_id: str, payload: OfficialSourceIn, _: dict[str, Any] = Depends(require_admin)):
    db = get_db()
    if not db.get_source(source_id):
        raise HTTPException(404, "Source introuvable")
    db.save_source(payload.model_dump(), source_id)
    return db.get_source(source_id)


@router.delete("/{source_id}", status_code=204)
async def delete_source(source_id: str, _: dict[str, Any] = Depends(require_admin)):
    if not get_db().delete_source(source_id):
        raise HTTPException(404, "Source introuvable")
