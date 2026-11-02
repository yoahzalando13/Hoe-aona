"""Back office d'administration : comptes, modération, statistiques de la plateforme."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from ..auth import public_user, require_admin
from ..db import get_db
from ..schemas import AdminUser, AdminUserUpdate, AnalysisStats, PlatformStats, PostOut, PostPage
from .social import to_post

router = APIRouter(prefix="/api/admin", tags=["administration"])


@router.get("/stats", response_model=PlatformStats)
async def stats(_: dict[str, Any] = Depends(require_admin)):
    return get_db().platform_stats()


@router.get("/analyses/stats", response_model=AnalysisStats)
async def analyses_stats(_: dict[str, Any] = Depends(require_admin)):
    return get_db().analysis_stats(None)


@router.get("/users", response_model=list[AdminUser])
async def users(q: str = "", _: dict[str, Any] = Depends(require_admin)):
    return [public_user(u) for u in get_db().list_users(q.strip())]


@router.patch("/users/{user_id}", response_model=AdminUser)
async def update_user(user_id: str, payload: AdminUserUpdate, admin: dict[str, Any] = Depends(require_admin)):
    db = get_db()
    target = db.get_user(user_id)
    if not target:
        raise HTTPException(404, "Compte introuvable")
    removes_admin = target["role"] == "admin" and target["active"] and (
        payload.role == "media" or payload.active is False)
    if removes_admin and db.count_admins() <= 1:
        raise HTTPException(409, "Il doit rester au moins un administrateur actif")
    fields: dict[str, Any] = {}
    if payload.role is not None:
        fields["role"] = payload.role
    if payload.active is not None:
        fields["active"] = int(payload.active)
    db.update_user(user_id, **fields)
    if payload.active is False:
        db.delete_user_sessions(user_id)
    updated = next(u for u in db.list_users() if u["id"] == user_id)
    return public_user(updated)


@router.get("/posts", response_model=PostPage)
async def all_posts(q: str = "", limit: int = Query(30, ge=1, le=100), offset: int = Query(0, ge=0),
                    admin: dict[str, Any] = Depends(require_admin)):
    rows, total = get_db().list_posts(admin["id"], q=q.strip(), include_hidden=True, limit=limit, offset=offset)
    return {"items": [to_post(r, admin) for r in rows], "total": total}


@router.put("/posts/{post_id}/hidden", response_model=PostOut)
async def hide(post_id: str, admin: dict[str, Any] = Depends(require_admin)):
    return _set_hidden(post_id, True, admin)


@router.delete("/posts/{post_id}/hidden", response_model=PostOut)
async def unhide(post_id: str, admin: dict[str, Any] = Depends(require_admin)):
    return _set_hidden(post_id, False, admin)


def _set_hidden(post_id: str, hidden: bool, admin: dict[str, Any]) -> PostOut:
    db = get_db()
    if not db.get_post(post_id, admin["id"]):
        raise HTTPException(404, "Publication introuvable")
    db.update_post(post_id, hidden=int(hidden))
    return to_post(db.get_post(post_id, admin["id"]), admin)
