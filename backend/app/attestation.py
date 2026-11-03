"""Certificats de constat : empreinte de la photo et contrôles de terrain, signés par le serveur (Ed25519).

Inspiré de C2PA sans en être une implémentation : le certificat est un JSON canonique signé, vérifiable
par quiconque avec la clé publique (`GET /api/attestations/public-key`).
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from .config import get_settings


@lru_cache
def _private_key() -> Ed25519PrivateKey:
    path: Path = get_settings().data_dir / "attestation_ed25519.pem"
    if path.exists():
        key = serialization.load_pem_private_key(path.read_bytes(), password=None)
        assert isinstance(key, Ed25519PrivateKey)
        return key
    key = Ed25519PrivateKey.generate()
    pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                            serialization.NoEncryption())
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as fh:
        fh.write(pem)
    return key


def _public_key() -> Ed25519PublicKey:
    return _private_key().public_key()


def public_key_pem() -> str:
    return _public_key().public_bytes(serialization.Encoding.PEM,
                                      serialization.PublicFormat.SubjectPublicKeyInfo).decode()


def key_id() -> str:
    raw = _public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return hashlib.sha256(raw).hexdigest()[:16]


def canonical(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sign(payload: dict[str, Any]) -> str:
    return base64.b64encode(_private_key().sign(canonical(payload))).decode()


def verify(payload: dict[str, Any], signature: str) -> bool:
    try:
        _public_key().verify(base64.b64decode(signature), canonical(payload))
        return True
    except (InvalidSignature, ValueError):
        return False


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def exif_capture(path: Path) -> tuple[bool, datetime | None]:
    """(photo issue d'un appareil photo, heure de prise de vue locale sans fuseau) d'après l'EXIF."""
    try:
        from PIL import Image
        with Image.open(path) as img:
            exif = img.getexif()
            make_model = bool(exif.get(0x010F) or exif.get(0x0110))  # Make, Model
            raw = exif.get_ifd(0x8769).get(0x9003) or exif.get(0x0132)  # DateTimeOriginal, DateTime
        taken = datetime.strptime(str(raw).strip(), "%Y:%m:%d %H:%M:%S") if raw else None
        return make_model, taken
    except Exception:
        return False, None


def distance_bucket(meters: float | None) -> str:
    """Tranche de distance au lieu : seule information conservée sur la position du vérificateur."""
    if meters is None:
        return "inconnue"
    for limit in (50, 150, 300, 1000):
        if meters < limit:
            return f"<{limit}"
    return ">1000"
