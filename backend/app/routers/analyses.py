"""Routes des analyses : création (multipart), suivi, base personnelle (back office), article.

Chaque analyse appartient à un compte : on ne voit que les siennes, sauf celles publiées sur le fil
(lecture seule pour le personnel média) et l'accès complet des administrateurs.
"""
from __future__ import annotations

import csv
import io
import json
import re
import shutil
import uuid
from pathlib import Path

from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import HTMLResponse, PlainTextResponse, Response

from ..auth import current_user

from ..config import get_settings
from ..db import get_db
from ..schemas import AnalysisOut, AnalysisPage, AnalysisResult, AnalysisStats, AnalysisUpdate, Article, Workflow
from ..services import article as article_service
from ..services.llm import LLMClient
from ..services.pipeline import load_preferences, run_analysis
from ..services.textutils import truncate

router = APIRouter(prefix="/api/analyses", tags=["analyses"])

KINDS = {
    "image": {"image/jpeg", "image/png", "image/webp", "image/gif", "image/heic"},
    "document": {"application/pdf", "text/plain", "text/markdown", "text/html",
                 "application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
    "audio": {"audio/mpeg", "audio/mp3", "audio/wav", "audio/x-wav", "audio/webm", "audio/ogg",
              "audio/mp4", "audio/x-m4a", "audio/m4a", "video/webm"},
}
EXTENSIONS = {
    "image": (".jpg", ".jpeg", ".png", ".webp", ".gif", ".heic"),
    "document": (".pdf", ".txt", ".md", ".html", ".htm", ".docx"),
    "audio": (".mp3", ".wav", ".webm", ".ogg", ".m4a", ".mp4"),
}


def _kind_of(upload: UploadFile) -> str:
    name = (upload.filename or "").lower()
    ctype = (upload.content_type or "").split(";")[0]
    for kind in ("image", "document", "audio"):
        if ctype in KINDS[kind] or name.endswith(EXTENSIONS[kind]):
            return kind
    raise HTTPException(415, f"Type de fichier non pris en charge : {upload.filename} ({ctype or 'inconnu'})")


def _parse_urls(raw: str) -> list[str]:
    raw = raw.strip()
    if not raw:
        return []
    try:
        values = json.loads(raw)
        values = values if isinstance(values, list) else [values]
    except ValueError:
        values = re.split(r"[\s,]+", raw)
    urls = [str(v).strip() for v in values if str(v).strip()]
    bad = [u for u in urls if not re.match(r"^https?://", u)]
    if bad:
        raise HTTPException(422, f"Lien invalide (http ou https attendu) : {bad[0]}")
    return urls[:10]


_COMPUTED = {"result", "owner_id", "owner_name", "editable"}


def _to_out(record: dict, viewer: dict[str, Any]) -> AnalysisOut:
    owner = get_db().get_user(record["user_id"]) if record.get("user_id") else None
    fields = {k: record.get(k) for k in AnalysisOut.model_fields if k not in _COMPUTED and record.get(k) is not None}
    return AnalysisOut(**fields, result=AnalysisResult(**record["result"]) if record.get("result") else None,
                       owner_id=record.get("user_id"), owner_name=owner["display_name"] if owner else None,
                       editable=record.get("user_id") == viewer["id"])


def _readable(analysis_id: str, user: dict[str, Any]) -> dict:
    """Analyse lisible : la sienne, une analyse publiée sur le fil, ou toutes pour un administrateur."""
    db = get_db()
    record = db.get_analysis(analysis_id)
    if not record or not (record.get("user_id") == user["id"] or user["role"] == "admin"
                          or db.is_analysis_published(analysis_id)):
        raise HTTPException(404, "Analyse introuvable")
    return record


def _owned(analysis_id: str, user: dict[str, Any]) -> dict:
    record = get_db().get_analysis(analysis_id)
    if not record or record.get("user_id") != user["id"]:
        raise HTTPException(404, "Analyse introuvable dans votre espace")
    return record


@router.post("", response_model=AnalysisOut, status_code=202)
async def create_analysis(
    background: BackgroundTasks,
    text: str = Form(""),
    urls: str = Form(""),
    files: list[UploadFile] = File(default=[]),
    user: dict[str, Any] = Depends(current_user),
):
    settings = get_settings()
    url_list = _parse_urls(urls)
    if not text.strip() and not files and not url_list:
        raise HTTPException(422, "Ajoutez au moins un texte, un fichier ou un lien à analyser")
    if len(text) > 50_000:
        raise HTTPException(413, "Texte trop long (50 000 caractères maximum)")
    if len(files) > 6:
        raise HTTPException(413, "6 fichiers maximum par analyse")

    analysis_id = uuid.uuid4().hex[:16]
    folder = settings.data_dir / "uploads" / analysis_id
    inputs: list[dict] = []
    if text.strip():
        inputs.append({"kind": "text", "text": text.strip()})
    for url in url_list:
        inputs.append({"kind": "url", "url": url})

    max_bytes = settings.max_upload_mb * 1024 * 1024
    for upload in files:
        kind = _kind_of(upload)
        folder.mkdir(parents=True, exist_ok=True)
        safe = re.sub(r"[^\w.\-]", "_", Path(upload.filename or "fichier").name)[:80]
        dest = folder / f"{len(inputs)}_{safe}"
        with dest.open("wb") as fh:
            shutil.copyfileobj(upload.file, fh)
        if dest.stat().st_size > max_bytes:
            shutil.rmtree(folder, ignore_errors=True)
            raise HTTPException(413, f"{upload.filename} dépasse {settings.max_upload_mb} Mo")
        inputs.append({"kind": kind, "path": str(dest), "name": upload.filename or safe,
                       "mime": upload.content_type or "application/octet-stream"})

    first = inputs[0]
    title = truncate(first.get("text") or first.get("name") or first.get("url") or "Analyse", 80)
    kinds = {i["kind"] for i in inputs}
    input_kind = kinds.pop() if len(kinds) == 1 else "mixte"
    get_db().create_analysis(title, input_kind, inputs, analysis_id, user_id=user["id"])
    background.add_task(run_analysis, analysis_id)
    return _to_out(get_db().get_analysis(analysis_id), user)


@router.get("", response_model=AnalysisPage)
async def list_analyses(q: str = "", verdict: str | None = None, workflow: Workflow | None = None,
                        tag: str | None = None, limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0),
                        user: dict[str, Any] = Depends(current_user)):
    items, total = get_db().list_analyses(q.strip(), verdict, limit, offset, user_id=user["id"],
                                          workflow=workflow, tag=(tag or "").strip() or None)
    return {"items": items, "total": total}


@router.get("/stats", response_model=AnalysisStats)
async def stats(user: dict[str, Any] = Depends(current_user)):
    return get_db().analysis_stats(user["id"])


@router.get("/export.csv", response_class=PlainTextResponse)
async def export_csv(user: dict[str, Any] = Depends(current_user)):
    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=";")
    writer.writerow(["id", "date", "titre", "type", "statut", "score", "verdict", "suivi", "etiquettes", "notes"])
    for r in get_db().all_analysis_rows(user["id"]):
        writer.writerow([r["id"], r["created_at"], r["title"], r["input_kind"], r["status"],
                         "" if r["global_score"] is None else str(r["global_score"]).replace(".", ","),
                         r["verdict"] or "", r["workflow"], ", ".join(r["tags"]), r["notes"]])
    return Response("\ufeff" + buf.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": 'attachment; filename="mes-analyses.csv"'})


@router.get("/{analysis_id}", response_model=AnalysisOut)
async def get_analysis(analysis_id: str, user: dict[str, Any] = Depends(current_user)):
    return _to_out(_readable(analysis_id, user), user)


@router.patch("/{analysis_id}", response_model=AnalysisOut)
async def update_analysis(analysis_id: str, payload: AnalysisUpdate, user: dict[str, Any] = Depends(current_user)):
    _owned(analysis_id, user)
    fields = payload.model_dump(exclude_none=True)
    if "title" in fields:
        fields["title"] = fields["title"].strip()
    if fields:
        get_db().update_analysis(analysis_id, **fields)
    return _to_out(get_db().get_analysis(analysis_id), user)


@router.delete("/{analysis_id}", status_code=204)
async def delete_analysis(analysis_id: str, user: dict[str, Any] = Depends(current_user)):
    record = get_db().get_analysis(analysis_id)
    if not record or not (record.get("user_id") == user["id"] or user["role"] == "admin"):
        raise HTTPException(404, "Analyse introuvable")
    get_db().delete_analysis(analysis_id)
    shutil.rmtree(get_settings().data_dir / "uploads" / analysis_id, ignore_errors=True)


def _result(record: dict) -> AnalysisResult:
    if not record.get("result"):
        raise HTTPException(404, "Résultat indisponible")
    return AnalysisResult(**record["result"])


@router.post("/{analysis_id}/article", response_model=Article)
async def regenerate_article(analysis_id: str, user: dict[str, Any] = Depends(current_user)):
    result = _result(_owned(analysis_id, user))
    warnings: list[str] = []
    result.article = await article_service.generate(result, LLMClient(), load_preferences(user["id"]).report_language,
                                                    warnings)
    get_db().update_analysis(analysis_id, result=result.model_dump(mode="json"))
    return result.article


@router.get("/{analysis_id}/article.md", response_class=PlainTextResponse)
async def article_markdown(analysis_id: str, user: dict[str, Any] = Depends(current_user)):
    result = _result(_readable(analysis_id, user))
    if not result.article:
        raise HTTPException(404, "Article non généré")
    return PlainTextResponse(article_service.to_markdown(result.article), media_type="text/markdown; charset=utf-8",
                             headers={"Content-Disposition": f'attachment; filename="verification-{analysis_id}.md"'})


@router.get("/{analysis_id}/article.html", response_class=HTMLResponse)
async def article_html(analysis_id: str, user: dict[str, Any] = Depends(current_user)):
    result = _result(_readable(analysis_id, user))
    if not result.article:
        raise HTTPException(404, "Article non généré")
    return HTMLResponse(article_service.to_html(result.article),
                        headers={"Content-Disposition": f'attachment; filename="verification-{analysis_id}.html"'})
