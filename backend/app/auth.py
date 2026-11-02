"""Comptes et sessions : mots de passe PBKDF2 (bibliothèque standard), jeton opaque en cookie HttpOnly."""
from __future__ import annotations

import hashlib
import hmac
import secrets
from typing import Any

from fastapi import Depends, HTTPException, Request, Response

from .config import get_settings
from .db import get_db

COOKIE = "hoe_session"
_ITERATIONS = 240_000


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), _ITERATIONS).hex()
    return f"pbkdf2_sha256${_ITERATIONS}${salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iterations, salt, digest = stored.split("$")
    except ValueError:
        return False
    if algo != "pbkdf2_sha256":
        return False
    candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(iterations)).hex()
    return hmac.compare_digest(candidate, digest)


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def open_session(response: Response, user_id: str) -> None:
    s = get_settings()
    token = secrets.token_urlsafe(32)
    get_db().create_session(_token_hash(token), user_id, s.session_days)
    response.set_cookie(COOKIE, token, max_age=s.session_days * 86400, httponly=True, samesite="lax",
                        secure=s.cookie_secure, path="/")


def close_session(request: Request, response: Response) -> None:
    token = request.cookies.get(COOKIE)
    if token:
        get_db().delete_session(_token_hash(token))
    response.delete_cookie(COOKIE, path="/")


def current_token_hash(request: Request) -> str | None:
    token = request.cookies.get(COOKIE)
    return _token_hash(token) if token else None


def current_user(request: Request) -> dict[str, Any]:
    token = request.cookies.get(COOKIE)
    user = get_db().session_user(_token_hash(token)) if token else None
    if not user:
        raise HTTPException(401, "Connexion requise")
    if not user["active"]:
        raise HTTPException(403, "Compte désactivé : contactez un administrateur")
    return user


def require_admin(user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    if user["role"] != "admin":
        raise HTTPException(403, "Réservé aux administrateurs")
    return user


def public_user(user: dict[str, Any]) -> dict[str, Any]:
    """Champs d'un compte sans le hachage du mot de passe."""
    return {k: v for k, v in user.items() if k != "password_hash"} | {"active": bool(user["active"])}
