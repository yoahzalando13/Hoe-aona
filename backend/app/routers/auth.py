"""Inscription, connexion, profil du compte connecté."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from ..auth import (close_session, current_token_hash, current_user, hash_password, open_session, public_user,
                    verify_password)
from ..config import get_settings
from ..db import get_db
from ..geo import get_geo
from ..schemas import AuthConfig, LoginIn, PasswordChange, ProfileUpdate, RegisterIn, UserOut

router = APIRouter(prefix="/api/auth", tags=["comptes"])


@router.get("/config", response_model=AuthConfig)
async def auth_config():
    db = get_db()
    has_users = db.count_users() > 0
    # Le tout premier compte peut toujours être créé, pour désigner l'administrateur.
    return AuthConfig(allow_registration=get_settings().allow_registration or not has_users, has_users=has_users)


@router.post("/register", response_model=UserOut, status_code=201)
async def register(payload: RegisterIn, response: Response):
    db = get_db()
    first = db.count_users() == 0
    if not first and not get_settings().allow_registration:
        raise HTTPException(403, "Les inscriptions sont fermées : demandez un compte à un administrateur")
    if db.get_user_by_email(payload.email):
        raise HTTPException(409, "Un compte existe déjà avec cette adresse")
    user = db.create_user(payload.email, hash_password(payload.password), payload.display_name,
                          payload.organization, "admin" if first else "media")
    if first:
        db.claim_orphan_analyses(user["id"])
    open_session(response, user["id"])
    return public_user(user)


@router.post("/login", response_model=UserOut)
async def login(payload: LoginIn, response: Response):
    user = get_db().get_user_by_email(payload.email.strip().lower())
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(401, "Adresse ou mot de passe incorrect")
    if not user["active"]:
        raise HTTPException(403, "Compte désactivé : contactez un administrateur")
    open_session(response, user["id"])
    return public_user(user)


@router.post("/logout", status_code=204)
async def logout(request: Request, response: Response):
    token_hash = current_token_hash(request)
    user = get_db().session_user(token_hash) if token_hash else None
    if user and (geo := get_geo()):
        geo.delete_location(user["id"])  # plus de demandes de vérification hors connexion
    close_session(request, response)


@router.get("/me", response_model=UserOut)
async def me(user: dict[str, Any] = Depends(current_user)):
    return public_user(user)


@router.patch("/me", response_model=UserOut)
async def update_me(payload: ProfileUpdate, user: dict[str, Any] = Depends(current_user)):
    fields = {k: " ".join(v.split()) if k != "bio" else v.strip()
              for k, v in payload.model_dump(exclude_none=True).items()}
    get_db().update_user(user["id"], **fields)
    return public_user(get_db().get_user(user["id"]))


@router.post("/password", status_code=204)
async def change_password(payload: PasswordChange, request: Request, user: dict[str, Any] = Depends(current_user)):
    if not verify_password(payload.current_password, user["password_hash"]):
        raise HTTPException(400, "Mot de passe actuel incorrect")
    db = get_db()
    db.update_user(user["id"], password_hash=hash_password(payload.new_password))
    db.delete_user_sessions(user["id"], keep=current_token_hash(request))
