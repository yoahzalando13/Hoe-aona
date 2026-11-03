"""Mini réseau social réservé au personnel média : publications, réactions, commentaires, profils."""
from __future__ import annotations

import shutil
import uuid
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse

from ..auth import current_user, require_staff
from ..config import get_settings
from ..db import get_db
from ..schemas import CommentIn, CommentOut, PostOut, PostPage, PostUpdate, PublicUser

router = APIRouter(prefix="/api", tags=["réseau social"])

IMAGE_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif"}
MAX_IMAGE_MB = 8


def to_post(row: dict[str, Any], viewer: dict[str, Any]) -> PostOut:
    is_admin = viewer["role"] == "admin"
    analysis = None
    if row.get("analysis_id") and row.get("analysis_title") is not None:
        analysis = {"id": row["analysis_id"], "title": row["analysis_title"], "global_score": row["analysis_score"],
                    "verdict": row["analysis_verdict"], "input_kind": row["analysis_kind"] or "text"}
    return PostOut(
        id=row["id"], created_at=row["created_at"], updated_at=row["updated_at"], body=row["body"],
        author_id=row["user_id"], author_name=row["author_name"], author_organization=row["author_organization"],
        author_role=row["author_role"], image_url=f"/api/posts/{row['id']}/image" if row.get("image_path") else None,
        analysis=analysis, likes=row["likes"], liked=bool(row["liked"]), comments_count=row["comments_count"],
        hidden=bool(row["hidden"]), can_edit=row["user_id"] == viewer["id"], can_moderate=is_admin,
    )


def _visible_post(post_id: str, viewer: dict[str, Any]) -> dict[str, Any]:
    row = get_db().get_post(post_id, viewer["id"])
    if not row or (row["hidden"] and viewer["role"] != "admin" and row["user_id"] != viewer["id"]):
        raise HTTPException(404, "Publication introuvable")
    return row


@router.get("/posts", response_model=PostPage)
async def feed(q: str = "", author: str | None = None, limit: int = Query(20, ge=1, le=50),
               offset: int = Query(0, ge=0), user: dict[str, Any] = Depends(current_user)):
    rows, total = get_db().list_posts(user["id"], author_id=author, q=q.strip(), limit=limit, offset=offset)
    return {"items": [to_post(r, user) for r in rows], "total": total}


@router.post("/posts", response_model=PostOut, status_code=201)
async def create_post(body: str = Form(""), analysis_id: str = Form(""), image: UploadFile | None = File(None),
                      user: dict[str, Any] = Depends(require_staff)):
    db = get_db()
    body = body.strip()
    analysis_id = analysis_id.strip() or None
    if not body and not analysis_id and not image:
        raise HTTPException(422, "Rédigez un message, joignez une image ou une analyse")
    if len(body) > 20000:
        raise HTTPException(413, "Message trop long (20 000 caractères maximum)")
    if analysis_id:
        record = db.get_analysis(analysis_id)
        if not record or record.get("user_id") != user["id"]:
            raise HTTPException(404, "Analyse introuvable dans votre espace")
        if record["status"] != "done":
            raise HTTPException(409, "Seule une analyse terminée peut être publiée")

    post_id = uuid.uuid4().hex[:16]
    image_path = None
    if image is not None and image.filename:
        ext = IMAGE_TYPES.get((image.content_type or "").split(";")[0])
        if not ext:
            raise HTTPException(415, "Image JPEG, PNG, WebP ou GIF attendue")
        dest = get_settings().data_dir / "posts" / f"{post_id}{ext}"
        with dest.open("wb") as fh:
            shutil.copyfileobj(image.file, fh)
        if dest.stat().st_size > MAX_IMAGE_MB * 1024 * 1024:
            dest.unlink(missing_ok=True)
            raise HTTPException(413, f"Image trop lourde ({MAX_IMAGE_MB} Mo maximum)")
        image_path = dest.name

    db.create_post(user["id"], body, analysis_id, image_path, post_id)
    if analysis_id:
        db.update_analysis(analysis_id, workflow="publie")
    return to_post(db.get_post(post_id, user["id"]), user)


@router.get("/posts/{post_id}", response_model=PostOut)
async def get_post(post_id: str, user: dict[str, Any] = Depends(current_user)):
    return to_post(_visible_post(post_id, user), user)


@router.patch("/posts/{post_id}", response_model=PostOut)
async def edit_post(post_id: str, payload: PostUpdate, user: dict[str, Any] = Depends(current_user)):
    row = _visible_post(post_id, user)
    if row["user_id"] != user["id"]:
        raise HTTPException(403, "Seul l'auteur peut modifier cette publication")
    get_db().update_post(post_id, body=payload.body.strip())
    return to_post(get_db().get_post(post_id, user["id"]), user)


@router.delete("/posts/{post_id}", status_code=204)
async def delete_post(post_id: str, user: dict[str, Any] = Depends(current_user)):
    row = _visible_post(post_id, user)
    if row["user_id"] != user["id"] and user["role"] != "admin":
        raise HTTPException(403, "Vous ne pouvez pas supprimer cette publication")
    get_db().delete_post(post_id)
    if row.get("image_path"):
        (get_settings().data_dir / "posts" / row["image_path"]).unlink(missing_ok=True)


@router.get("/posts/{post_id}/image", include_in_schema=False)
async def post_image(post_id: str, user: dict[str, Any] = Depends(current_user)):
    row = _visible_post(post_id, user)
    if not row.get("image_path"):
        raise HTTPException(404, "Aucune image")
    folder = (get_settings().data_dir / "posts").resolve()
    path = (folder / row["image_path"]).resolve()
    if folder not in path.parents or not path.is_file():
        raise HTTPException(404, "Image introuvable")
    return FileResponse(path, headers={"Cache-Control": "private, max-age=86400"})


@router.put("/posts/{post_id}/like", response_model=PostOut)
async def like(post_id: str, user: dict[str, Any] = Depends(current_user)):
    _visible_post(post_id, user)
    get_db().set_like(post_id, user["id"], True)
    return to_post(get_db().get_post(post_id, user["id"]), user)


@router.delete("/posts/{post_id}/like", response_model=PostOut)
async def unlike(post_id: str, user: dict[str, Any] = Depends(current_user)):
    _visible_post(post_id, user)
    get_db().set_like(post_id, user["id"], False)
    return to_post(get_db().get_post(post_id, user["id"]), user)


def _comment(row: dict[str, Any], post_author: str, viewer: dict[str, Any]) -> CommentOut:
    can_delete = viewer["id"] in (row["user_id"], post_author) or viewer["role"] == "admin"
    return CommentOut(id=row["id"], created_at=row["created_at"], body=row["body"], author_id=row["user_id"],
                      author_name=row["author_name"], author_organization=row["author_organization"],
                      can_delete=can_delete)


@router.get("/posts/{post_id}/comments", response_model=list[CommentOut])
async def comments(post_id: str, user: dict[str, Any] = Depends(current_user)):
    post = _visible_post(post_id, user)
    return [_comment(c, post["user_id"], user) for c in get_db().list_comments(post_id)]


@router.post("/posts/{post_id}/comments", response_model=list[CommentOut], status_code=201)
async def add_comment(post_id: str, payload: CommentIn, user: dict[str, Any] = Depends(current_user)):
    post = _visible_post(post_id, user)
    get_db().add_comment(post_id, user["id"], payload.body.strip())
    return [_comment(c, post["user_id"], user) for c in get_db().list_comments(post_id)]


@router.delete("/posts/{post_id}/comments/{comment_id}", status_code=204)
async def delete_comment(post_id: str, comment_id: str, user: dict[str, Any] = Depends(current_user)):
    post = _visible_post(post_id, user)
    comment = get_db().get_comment(comment_id)
    if not comment or comment["post_id"] != post_id:
        raise HTTPException(404, "Commentaire introuvable")
    if user["id"] not in (comment["user_id"], post["user_id"]) and user["role"] != "admin":
        raise HTTPException(403, "Vous ne pouvez pas supprimer ce commentaire")
    get_db().delete_comment(comment_id)


@router.get("/users/{user_id}", response_model=PublicUser)
async def profile(user_id: str, user: dict[str, Any] = Depends(current_user)):
    target = get_db().get_user(user_id)
    if not target or (not target["active"] and user["role"] != "admin"):
        raise HTTPException(404, "Profil introuvable")
    _, posts = get_db().list_posts(user["id"], author_id=user_id, limit=1)
    return PublicUser(**{k: target[k] for k in ("id", "created_at", "display_name", "organization", "bio", "role")},
                      posts_count=posts)
