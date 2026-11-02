"""Transforme chaque entrée utilisateur en texte analysable, avec ses signaux d'origine."""
from __future__ import annotations

import base64
import io
import logging
from dataclasses import dataclass, field
from pathlib import Path

import httpx

from ..config import get_settings
from . import ai_detection
from .llm import LLMClient, LLMUnavailable, parse_json

log = logging.getLogger("hoe-aona.extraction")

IMAGE_PROMPT = (
    "Tu aides un fact-checker. Analyse cette image et réponds en JSON : "
    '{"text": "tout le texte visible, transcrit fidèlement", '
    '"description": "description factuelle et neutre de ce que montre l\'image (lieux, personnes, logos, dates visibles)", '
    '"manipulation_clues": ["indices visuels de retouche ou de génération (mains, textes déformés, ombres incohérentes...)"]}. '
    "N'invente rien ; si un élément est illisible, dis-le."
)


@dataclass
class Extracted:
    kind: str
    name: str
    text: str = ""
    size: int | None = None
    url: str | None = None
    image_bytes: bytes | None = None
    mime: str | None = None
    meta: dict = field(default_factory=dict)
    ai: ai_detection.AIResult = field(default_factory=lambda: ai_detection.AIResult(0.0, []))
    note: str | None = None


def _pdf(data: bytes) -> tuple[str, dict]:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    text = "\n".join((page.extract_text() or "") for page in reader.pages[:40])
    info = reader.metadata or {}
    meta = {"Producer": info.get("/Producer"), "Creator": info.get("/Creator"), "Author": info.get("/Author")}
    return text, meta


def _docx(data: bytes) -> tuple[str, dict]:
    import docx

    document = docx.Document(io.BytesIO(data))
    text = "\n".join(p.text for p in document.paragraphs if p.text.strip())
    props = document.core_properties
    meta = {"Author": props.author, "LastModifiedBy": props.last_modified_by, "Comments": props.comments}
    return text, meta


def _html(data: bytes) -> str:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(data, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    return soup.get_text("\n", strip=True)


async def _ocr_space(data: bytes, mime: str) -> str:
    key = get_settings().ocr_space_api_key
    if not key:
        return ""
    async with httpx.AsyncClient(timeout=60) as http:
        resp = await http.post("https://api.ocr.space/parse/image", data={
            "apikey": key, "language": "fre", "OCREngine": "2",
            "base64Image": f"data:{mime};base64,{base64.b64encode(data).decode()}",
        })
        resp.raise_for_status()
        results = resp.json().get("ParsedResults") or []
    return "\n".join(r.get("ParsedText", "") for r in results)


async def extract_text_input(text: str) -> Extracted:
    ex = Extracted(kind="text", name="Texte saisi", text=text, size=len(text.encode()))
    ex.ai = ai_detection.text_signals(text)
    return ex


async def extract_file(path: Path, kind: str, name: str, mime: str, llm: LLMClient) -> Extracted:
    data = path.read_bytes()
    ex = Extracted(kind=kind, name=name, size=len(data), mime=mime)
    lower = name.lower()

    if kind == "document":
        try:
            if lower.endswith(".pdf") or mime == "application/pdf":
                ex.text, ex.meta = _pdf(data)
            elif lower.endswith(".docx"):
                ex.text, ex.meta = _docx(data)
            elif lower.endswith((".html", ".htm")):
                ex.text = _html(data)
            else:
                ex.text = data.decode("utf-8", errors="replace")
        except Exception as exc:  # noqa: BLE001
            ex.note = f"Lecture du document impossible : {exc}"
        meta_ai = ai_detection.metadata_signals({k: v for k, v in ex.meta.items() if v}, "document")
        text_ai = ai_detection.text_signals(ex.text)
        ex.ai = ai_detection.AIResult(ai_detection.noisy_or([meta_ai.probability, text_ai.probability]),
                                      meta_ai.signals + text_ai.signals)
        if not ex.text.strip() and not ex.note:
            ex.note = "Document sans texte extractible (scan ?) : convertissez-le en image pour l'OCR"

    elif kind == "image":
        ex.image_bytes = data
        ex.ai = ai_detection.image_signatures(data)
        description = ""
        if llm.available:
            try:
                parsed = parse_json(await llm.describe_image(data, mime, IMAGE_PROMPT))
                ex.text = parsed.get("text", "") or ""
                description = parsed.get("description", "") or ""
                clues = [c for c in parsed.get("manipulation_clues", []) or [] if c]
                if clues:
                    ex.ai.signals.append("Indices visuels relevés : " + "; ".join(clues[:3]))
            except Exception as exc:  # noqa: BLE001
                log.warning("Vision LLM indisponible : %s", exc)
        if not ex.text:
            try:
                ex.text = await _ocr_space(data, mime)
            except Exception as exc:  # noqa: BLE001
                log.warning("OCR.space indisponible : %s", exc)
        if description:
            ex.meta["description"] = description
            ex.text = (ex.text + "\n\n[Description de l'image] " + description).strip()
        if not ex.text:
            ex.note = "Aucun texte lisible : configurez une clé LLM (vision) ou OCR.space"

    elif kind == "audio":
        try:
            ex.text = await llm.transcribe(data, name)
            ex.ai = ai_detection.text_signals(ex.text)
            ex.ai.signals.append("Audio : seule la transcription est analysée (pas de détection de voix clonée)")
        except LLMUnavailable as exc:
            ex.note = str(exc)
        except Exception as exc:  # noqa: BLE001
            ex.note = f"Transcription impossible : {exc}"

    return ex
