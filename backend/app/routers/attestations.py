"""Vérification publique des certificats de constat (web et mobile, compte connecté).

Un journaliste qui reçoit une photo de constat peut vérifier qu'elle n'a pas été retouchée :
son empreinte SHA-256 doit correspondre à un certificat signé par le serveur.
"""
from __future__ import annotations

import hashlib
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import PlainTextResponse

from .. import attestation
from ..auth import current_user
from ..geo import get_geo
from ..schemas import AttestationOut

router = APIRouter(prefix="/api/attestations", tags=["certificats de constat"])


def _out(rep: dict[str, Any], photo_matches: bool | None = None) -> AttestationOut:
    return AttestationOut(report_id=rep["id"], certificate=rep["certificate"], signature=rep["signature"],
                          key_id=rep["certificate"].get("key_id", ""),
                          signature_valid=attestation.verify(rep["certificate"], rep["signature"]),
                          photo_matches=photo_matches)


def _store():
    store = get_geo()
    if store is None:
        raise HTTPException(503, "Certificats indisponibles : POSTGIS_URL n'est pas configuré")
    return store


@router.get("/public-key", response_class=PlainTextResponse)
async def public_key():
    """Clé publique Ed25519 (PEM) : permet de vérifier un certificat hors de la plateforme."""
    return attestation.public_key_pem()


@router.post("/verify", response_model=list[AttestationOut])
async def verify_photo(photo: UploadFile = File(...), _: dict[str, Any] = Depends(current_user)):
    """Retrouve les certificats correspondant exactement à cette photo (empreinte SHA-256)."""
    digest = hashlib.sha256()
    while chunk := await photo.read(65536):
        digest.update(chunk)
    reports = _store().reports_by_hash(digest.hexdigest())
    if not reports:
        raise HTTPException(404, "Aucun constat certifié pour cette photo : elle a pu être retouchée ou recadrée")
    return [_out(r, photo_matches=True) for r in reports]


@router.get("/{report_id}", response_model=AttestationOut)
async def certificate(report_id: str, _: dict[str, Any] = Depends(current_user)):
    rep = _store().get_report(report_id)
    if not rep:
        raise HTTPException(404, "Certificat introuvable")
    return _out(rep)
