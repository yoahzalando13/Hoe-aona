"""Vérification physique, réservée à l'application mobile.

Une demande vise un lieu précis ; PostGIS notifie les comptes dont la dernière position est à moins de
2 km. Le premier qui accepte devient vérificateur, l'annonce disparaît chez les autres et le demandeur
est prévenu. Les positions des comptes ne sont jamais renvoyées : ni distance, ni nombre de destinataires.
"""
from __future__ import annotations

import shutil
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse

from .. import attestation
from ..auth import current_user, require_staff
from ..config import get_settings
from ..db import get_db
from ..geo import GeoStore, get_geo
from ..schemas import (LocationIn, LocationStatus, NotificationOut, NotificationRead, ReportOut, VerificationIn,
                       VerificationOut, VerificationOutcome)
from .social import IMAGE_TYPES, MAX_IMAGE_MB

MOBILE_CLIENT = "android"


def mobile_client(x_hoe_client: str | None = Header(None)) -> None:
    if (x_hoe_client or "").lower() != MOBILE_CLIENT:
        raise HTTPException(403, "La vérification physique n'est disponible que dans l'application mobile")


router = APIRouter(prefix="/api/verifications", tags=["vérification physique"],
                   dependencies=[Depends(mobile_client), Depends(require_staff)])


def geo() -> GeoStore:
    store = get_geo()
    if store is None:
        raise HTTPException(503, "Vérification physique indisponible : POSTGIS_URL n'est pas configuré")
    return store


def _report_out(r: dict[str, Any]) -> ReportOut:
    verifier = get_db().get_user(r["verifier_id"]) or {}
    return ReportOut(
        **{k: r[k] for k in ("id", "verifier_id", "outcome", "report", "photo_sha256", "capture_verified", "on_site",
                             "distance_bucket", "mock_location", "received_at")},
        verifier_name=verifier.get("display_name", "?"),
        photo_url=f"/api/verifications/{r['request_id']}/reports/{r['id']}/photo" if r.get("photo_path") else None,
        certified=attestation.verify(r["certificate"], r["signature"]),
        certificate_url=f"/api/attestations/{r['id']}",
    )


def _to_out(row: dict[str, Any], viewer_id: str, store: GeoStore | None = None) -> VerificationOut:
    db = get_db()
    store = store or get_geo()
    requester = db.get_user(row["requester_id"]) or {}
    verifier = db.get_user(row["verifier_id"]) if row.get("verifier_id") else None
    reports = store.list_reports(row["id"]) if store else []
    mine = any(r["verifier_id"] == viewer_id for r in reports)
    role = ("requester" if row["requester_id"] == viewer_id
            else "verifier" if row.get("verifier_id") == viewer_id else "reporter" if mine else "recipient")
    # Second avis indépendant : un vérificateur ne voit que son propre constat avant la clôture.
    if role != "requester" and row["status"] != "completed":
        reports = [r for r in reports if r["verifier_id"] == viewer_id]
    return VerificationOut(
        **{k: row[k] for k in ("id", "created_at", "expires_at", "status", "claim", "details", "place_label",
                               "latitude", "longitude", "radius_m", "analysis_id", "requester_id", "verifier_id",
                               "accepted_at", "outcome", "report", "completed_at")},
        requester_name=requester.get("display_name", "?"),
        requester_organization=requester.get("organization", ""),
        verifier_name=verifier["display_name"] if verifier else None,
        photo_url=f"/api/verifications/{row['id']}/photo" if row.get("photo_path") else None,
        role=role,
        required_reports=row.get("required_reports") or 1,
        consensus=row.get("consensus"),
        reports=[_report_out(r) for r in reports],
    )


def _visible(store: GeoStore, request_id: str, user: dict[str, Any]) -> dict[str, Any]:
    """Demandeur et vérificateur voient la demande ; un destinataire seulement tant qu'elle est ouverte."""
    row = store.get_request(request_id)
    if row and (user["id"] in (row["requester_id"], row["verifier_id"])
                or store.has_report(request_id, user["id"])
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
    if store.has_report(request_id, user["id"]):
        raise HTTPException(409, "Vous avez déjà rendu un constat : le second avis doit venir d'une autre personne")
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


@router.post("/{request_id}/capture")
async def capture_token(request_id: str, user: dict[str, Any] = Depends(current_user), store: GeoStore = Depends(geo)):
    """Jeton à usage unique demandé à l'ouverture de l'appareil photo : la photo devra être prise après."""
    row = _visible(store, request_id, user)
    if row["verifier_id"] != user["id"] or row["status"] != "accepted":
        raise HTTPException(409, "Seul le vérificateur d'une demande acceptée peut photographier le constat")
    minutes = get_settings().capture_token_minutes
    return {"token": store.issue_capture_token(request_id, user["id"]), "valid_minutes": minutes}


def _parse_device_time(raw: str) -> datetime | None:
    try:
        value = datetime.fromisoformat(raw.strip())
        return value if value.tzinfo else None
    except ValueError:
        return None


@router.post("/{request_id}/report", response_model=VerificationOut)
async def report(request_id: str, outcome: VerificationOutcome = Form(...), report: str = Form(""),
                 photo: UploadFile | None = File(None), capture_token: str = Form(""),
                 latitude: float | None = Form(None), longitude: float | None = Form(None),
                 accuracy: float | None = Form(None), mock_location: bool = Form(False), device_time: str = Form(""),
                 user: dict[str, Any] = Depends(current_user), store: GeoStore = Depends(geo)):
    """Constat certifié : correct, incorrect ou impossible à établir sur place.

    Contrôles : photo prise après l'émission du jeton (EXIF d'appareil photo), présence à moins de
    `VERIFICATION_ON_SITE_M` du lieu (position non simulée, précise), empreinte SHA-256 signée.
    Si un contrôle échoue, un second vérificateur indépendant est sollicité.
    """
    s = get_settings()
    row = _visible(store, request_id, user)
    if row["verifier_id"] != user["id"] or row["status"] != "accepted":
        raise HTTPException(409, "Seul le vérificateur d'une demande acceptée peut rendre son constat")
    if len(report) > 4000:
        raise HTTPException(413, "Constat trop long (4 000 caractères maximum)")

    report_id = uuid.uuid4().hex[:16]
    received_at = datetime.now(timezone.utc)
    photo_path = photo_sha = None
    capture = {"token": False, "exif_camera": False, "taken_after_token": False, "device_clock_ok": False}
    if photo is not None and photo.filename:
        ext = IMAGE_TYPES.get((photo.content_type or "").split(";")[0])
        if not ext:
            raise HTTPException(415, "Image JPEG, PNG, WebP ou GIF attendue")
        dest = s.data_dir / "verifications" / f"{request_id}-{report_id}{ext}"
        with dest.open("wb") as fh:
            shutil.copyfileobj(photo.file, fh)
        if dest.stat().st_size > MAX_IMAGE_MB * 1024 * 1024:
            dest.unlink(missing_ok=True)
            raise HTTPException(413, f"Photo trop lourde ({MAX_IMAGE_MB} Mo maximum)")
        photo_path, photo_sha = dest.name, attestation.sha256_file(dest)
        issued = store.consume_capture_token(capture_token, request_id, user["id"], s.capture_token_minutes) \
            if capture_token else None
        device = _parse_device_time(device_time)
        camera, taken = attestation.exif_capture(dest)
        capture["token"] = issued is not None
        capture["exif_camera"] = camera
        capture["device_clock_ok"] = device is not None and abs((device - received_at).total_seconds()) <= 20 * 60
        if issued and device and taken:
            # L'EXIF est en heure locale sans fuseau : on le compare dans le fuseau du téléphone.
            issued_local = issued.astimezone(device.tzinfo).replace(tzinfo=None)
            device_local = device.replace(tzinfo=None)
            capture["taken_after_token"] = issued_local - timedelta(minutes=2) <= taken <= device_local + timedelta(minutes=2)
    capture_verified = all(capture.values())

    distance = None
    if latitude is not None and longitude is not None:
        distance = store.distance_to_place(request_id, latitude, longitude)  # position jamais enregistrée
    precise = accuracy is not None and accuracy <= s.verification_max_accuracy_m
    on_site = distance is not None and distance <= s.verification_on_site_m and precise and not mock_location
    bucket = attestation.distance_bucket(distance)

    certificate = {
        "version": 1, "type": "hoe-aona.constat", "key_id": attestation.key_id(),
        "report_id": report_id, "request_id": request_id, "claim": row["claim"], "place_label": row["place_label"],
        "outcome": outcome, "verifier": {"id": user["id"], "name": user["display_name"]},
        "received_at": received_at.isoformat(), "photo_sha256": photo_sha,
        "capture": capture, "location": {"on_site": on_site, "distance_bucket": bucket,
                                         "accuracy_ok": precise, "mock": bool(mock_location)},
    }
    needs_second = not (photo_sha and capture_verified and on_site)
    status = store.add_report(request_id, user["id"], {
        "id": report_id, "request_id": request_id, "verifier_id": user["id"], "outcome": outcome,
        "report": report.strip(), "photo_path": photo_path, "photo_sha256": photo_sha,
        "capture_verified": capture_verified, "on_site": on_site, "distance_bucket": bucket,
        "mock_location": bool(mock_location), "received_at": received_at,
        "certificate": certificate, "signature": attestation.sign(certificate),
    }, needs_second, s.verification_hours, s.location_max_age_minutes)
    if status is None:
        raise HTTPException(409, "Cette demande n'attend plus de constat")
    return _to_out(store.get_request(request_id), user["id"], store)


@router.post("/{request_id}/dispute", response_model=VerificationOut)
async def dispute(request_id: str, user: dict[str, Any] = Depends(current_user), store: GeoStore = Depends(geo)):
    """Le demandeur conteste un constat unique : la demande repart vers un second vérificateur."""
    s = get_settings()
    if not store.dispute(request_id, user["id"], s.verification_hours, s.location_max_age_minutes):
        raise HTTPException(409, "Seul un constat unique peut être contesté, par l'auteur de la demande")
    return _to_out(store.get_request(request_id), user["id"], store)


@router.get("/{request_id}/reports/{report_id}/photo", include_in_schema=False)
async def report_photo(request_id: str, report_id: str, user: dict[str, Any] = Depends(current_user),
                       store: GeoStore = Depends(geo)):
    row = _visible(store, request_id, user)
    rep = store.get_report(report_id)
    if not rep or rep["request_id"] != request_id or not rep.get("photo_path"):
        raise HTTPException(404, "Photo introuvable")
    if rep["verifier_id"] != user["id"] and user["id"] != row["requester_id"] and row["status"] != "completed":
        raise HTTPException(404, "Photo introuvable")
    return _photo_file(rep["photo_path"])


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
    return _photo_file(row["photo_path"])


def _photo_file(name: str) -> FileResponse:
    folder = (get_settings().data_dir / "verifications").resolve()
    path = (folder / name).resolve()
    if folder not in path.parents or not path.is_file():
        raise HTTPException(404, "Photo introuvable")
    return FileResponse(path, headers={"Cache-Control": "private, max-age=86400"})
