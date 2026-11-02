"""Préférences de chaque compte (pondérations, seuils, pays, langue, rétention)."""
from typing import Any

from fastapi import APIRouter, Depends

from ..auth import current_user
from ..db import get_db
from ..schemas import Preferences
from ..services.pipeline import load_preferences

router = APIRouter(prefix="/api/settings", tags=["paramètres"])


@router.get("", response_model=Preferences)
async def read_settings(user: dict[str, Any] = Depends(current_user)):
    return load_preferences(user["id"])


@router.put("", response_model=Preferences)
async def update_settings(prefs: Preferences, user: dict[str, Any] = Depends(current_user)):
    get_db().save_preferences(prefs.model_dump(), user["id"])
    return prefs
