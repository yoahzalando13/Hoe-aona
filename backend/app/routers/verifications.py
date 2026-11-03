"""Vérification physique, réservée à l'application mobile.

Une demande vise un lieu précis ; PostGIS notifie les comptes dont la dernière position est à moins de
2 km. Le premier qui accepte devient vérificateur, l'annonce disparaît chez les autres et le demandeur
est prévenu. Les positions des comptes ne sont jamais renvoyées : ni distance, ni nombre de destinataires.
"""
from __future__ import annotations

import shutil
from typing import Any

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse

from ..auth import current_user
from ..config import get_settings
from ..db import get_db
from ..geo import GeoStore, get_geo
from ..schemas import (LocationIn, LocationStatus, NotificationOut, NotificationRead, VerificationIn,
                       VerificationOut, VerificationOutcome)
from .social import IMAGE_TYPES, MAX_IMAGE_MB

MOBILE_CLIENT = "android"


def mobile_client(x_hoe_client: str | None = Header(None)) -> None:
    if (x_hoe_client or "").lower() != MOBILE_CLIENT:
        raise HTTPException(403, "La vérification physique n'est disponible que dans l'application mobile")


router = APIRouter(prefix="/api/verifications", tags=["vérification physique"],
                   dependencies=[Depends(mobile_client)])


def geo() -> GeoStore:
    store = get_geo()
    if store is None:
        raise HTTPException(503, "Vérification physique indisponible : POSTGIS_URL n'est pas configuré")
    return store


def _to_out(row: dict[str, Any], viewer_id: str) -> VerificationOut:
    db = get_db()
    requester = db.get_user(row["requester_id"]) or {}
    verifier = db.get_user(row["verifier_id"]) if row.get("verifier_id") else None
    role = ("requester" if row["requester_id"] == viewer_id
            else "verifier" if row.get("verifier_id") == viewer_id else "recipient")
    return VerificationOut(
        **{k: row[k] for k in ("id", "created_at", "expires_at", "status", "claim", "details", "place_label",
                               "latitude", "longitude", "radius_m", "analysis_id", "requester_id", "verifier_id",
                               "accepted_at", "outcome", "report", "completed_at")},
        requester_name=requester.get("display_name", "?"),
        requester_organization=requester.get("organization", ""),
        verifier_name=verifier["display_name"] if verifier else None,
        photo_url=f"/api/verifications/{row['id']}/photo" if row.get("photo_path") else None,
        role=role,
    )


def _visible(store: GeoStore, request_id: str, user: dict[str, Any]) -> dict[str, Any]:
    """Demandeur et vérificateur voient la demande ; un destinataire seulement tant qu'elle est ouverte."""
    row = store.get_request(request_id)
    if row and (user["id"] in (row["requester_id"], row["verifier_id"])
                or (row["status"] == "open" and store.is_recipient(request_id, user["id"]))):
        return row
    raise HTTPException(404, "Demande introuvable ou déjà prise en charge")


# ---------- position du compte ----------
@router.get("/location", response_model=LocationStatus)
async def location_status(user: dict[str, Any] = Depends(current_user), store: GeoStore = Depends(geo)):
    updated = store.location_status(user["id"])
    return LocationStatus(sharing=updated is not None, updated_at=updated)


@router.put("/location", status_code=204)
async def update_location(payload: LocationIn, user: dict[str, Any] = Depends(current_user),
                          store: GeoStore = Depends(geo)):
    store.set_location(user["id"], payload.latitude, payload.longitude)


@router.delete("/location", status_code=204)
async def stop_sharing(user: dict[str, Any] = Depends(current_user), store: GeoStore = Depends(geo)):
    store.delete_location(user["id"])


# ---------- demandes ----------
@router.post("", response_model=VerificationOut, status_code=201)
async def create_request(payload: VerificationIn, user: dict[str, Any] = Depends(current_user),
                         store: GeoStore = Depends(geo)):
    s = get_settings()
    store.expire_requests()
    if store.count_open_by_requester(user["id"]) >= s.max_open_verifications:
        raise HTTPException(429, f"{s.max_open_verifications} demandes en cours au plus : clôturez-en une")
    analysis_id = (payload.analysis_id or "").strip() or None
    if analysis_id:
        record = get_db().get_analysis(analysis_id)
        if not record or record.get("user_id") != user["id"]:
            raise HTTPException(404, "Analyse introuvable dans votre espace")
    request_id = store.create_request(
        user["id"], payload.claim.strip(), payload.details.strip(), payload.place_label.strip(),
        payload.latitude, payload.longitude, s.verification_radius_m, s.verification_hours,
        s.location_max_age_minutes, analysis_id)
    return _to_out(store.get_request(request_id), user["id"])


@router.get("/nearby", response_model=list[VerificationOut])
async def nearby(user: dict[str, Any] = Depends(current_user), store: GeoStore = Depends(geo)):
    """Demandes ouvertes reçues par le compte (il se trouvait dans le rayon à leur création)."""
    store.expire_requests()
    return [_to_out(r, user["id"]) for r in store.list_nearby(user["id"])]


@router.get("/mine", response_model=list[VerificationOut])
async def mine(user: dict[str, Any] = Depends(current_user), store: GeoStore = Depends(geo)):
    store.expire_requests()
    return [_to_out(r, user["id"]) for r in store.list_by_requester(user["id"])]


@router.get("/assigned", response_model=list[VerificationOut])
async def assigned(user: dict[str, Any] = Depends(current_user), store: GeoStore = Depends(geo)):
    return [_to_out(r, user["id"]) for r in store.list_by_verifier(user["id"])]


# ---------- notifications ----------
@router.get("/notifications", response_model=list[NotificationOut])
async def notifications(undelivered: bool = False, user: dict[str, Any] = Depends(current_user),
                        store: GeoStore = Depends(geo)):
    """`undelivered=true` : nouvelles notifications à afficher sur le téléphone, marquées comme remises."""
    store.expire_requests()
    out = []
    for n in store.list_notifications(user["id"], undelivered=undelivered):
        row = store.get_request(n["request_id"])
        out.append(NotificationOut(id=n["id"], kind=n["kind"], created_at=n["created_at"],
                                   read=n["read_at"] is not None,
                                   request=_to_out(row, user["id"]) if row else None))
    return out


@router.post("/notifications/read", status_code=204)
async def read_notifications(payload: NotificationRead, user: dict[str, Any] = Depends(current_user),
                             store: GeoStore = Depends(geo)):
    store.mark_read(user["id"], payload.ids)


@router.get("/{request_id}", response_model=VerificationOut)
async def get_request(request_id: str, user: dict[str, Any] = Depends(current_user), store: GeoStore = Depends(geo)):
    return _to_out(_visible(store, request_id, user), user["id"])


@router.post("/{request_id}/accept", response_model=VerificationOut)
async def accept(request_id: str, user: dict[str, Any] = Depends(current_user), store: GeoStore = Depends(geo)):
    row = _visible(store, request_id, user)
    if row["requester_id"] == user["id"]:
        raise HTTPException(409, "Vous ne pouvez pas vérifier votre propre demande")
    if not store.accept(request_id, user["id"]):
        raise HTTPException(409, "Cette demande a déjà été acceptée par quelqu'un d'autre")
    return _to_out(store.get_request(request_id), user["id"])


@router.post("/{request_id}/decline", status_code=204)
async def decline(request_id: str, user: dict[str, Any] = Depends(current_user), store: GeoStore = Depends(geo)):
    _visible(store, request_id, user)
    store.decline(request_id, user["id"])


@router.post("/{request_id}/release", response_model=VerificationOut)
async def release(request_id: str, user: dict[str, Any] = Depends(current_user), store: GeoStore = Depends(geo)):
    if not store.release(request_id, user["id"], get_settings().location_max_age_minutes):
        raise HTTPException(409, "Vous n'êtes pas le vérificateur de cette demande")
    return _to_out(store.get_request(request_id), user["id"])


@router.post("/{request_id}/report", response_model=VerificationOut)
async def report(request_id: str, outcome: VerificationOutcome = Form(...), report: str = Form(""),
                 photo: UploadFile | None = File(None), user: dict[str, Any] = Depends(current_user),
                 store: GeoStore = Depends(geo)):
    """Le vérificateur confirme si l'information est correcte, incorrecte ou impossible à établir sur place."""
    row = _visible(store, request_id, user)
    if row["verifier_id"] != user["id"] or row["status"] != "accepted":
        raise HTTPException(409, "Seul le vérificateur d'une demande acceptée peut rendre son constat")
    if len(report) > 4000:
        raise HTTPException(413, "Constat trop long (4 000 caractères maximum)")
    photo_path = None
    if photo is not None and photo.filename:
        ext = IMAGE_TYPES.get((photo.content_type or "").split(";")[0])
        if not ext:
            raise HTTPException(415, "Image JPEG, PNG, WebP ou GIF attendue")
        dest = get_settings().data_dir / "verifications" / f"{request_id}{ext}"
        with dest.open("wb") as fh:
            shutil.copyfileobj(photo.file, fh)
        if dest.stat().st_size > MAX_IMAGE_MB * 1024 * 1024:
            dest.unlink(missing_ok=True)
            raise HTTPException(413, f"Photo trop lourde ({MAX_IMAGE_MB} Mo maximum)")
        photo_path = dest.name
    if not store.complete(request_id, user["id"], outcome, report.strip(), photo_path):
        raise HTTPException(409, "Cette demande n'attend plus de constat")
    return _to_out(store.get_request(request_id), user["id"])


@router.post("/{request_id}/cancel", response_model=VerificationOut)
async def cancel(request_id: str, user: dict[str, Any] = Depends(current_user), store: GeoStore = Depends(geo)):
    if not store.cancel(request_id, user["id"]):
        raise HTTPException(409, "Seule une demande en cours peut être annulée par son auteur")
    return _to_out(store.get_request(request_id), user["id"])


@router.get("/{request_id}/photo", include_in_schema=False)
async def photo(request_id: str, user: dict[str, Any] = Depends(current_user), store: GeoStore = Depends(geo)):
    row = _visible(store, request_id, user)
    if not row.get("photo_path"):
        raise HTTPException(404, "Aucune photo")
    folder = (get_settings().data_dir / "verifications").resolve()
    path = (folder / row["photo_path"]).resolve()
    if folder not in path.parents or not path.is_file():
        raise HTTPException(404, "Photo introuvable")
    return FileResponse(path, headers={"Cache-Control": "private, max-age=86400"})
