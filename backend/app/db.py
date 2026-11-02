"""Stockage SQLite minimal, sans ORM, utilisable depuis du code asynchrone."""
from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

_SCHEMA = """
CREATE TABLE IF NOT EXISTS analyses (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    status TEXT NOT NULL,
    progress INTEGER NOT NULL DEFAULT 0,
    step TEXT NOT NULL DEFAULT '',
    title TEXT NOT NULL,
    input_kind TEXT NOT NULL,
    global_score REAL,
    verdict TEXT,
    inputs TEXT NOT NULL,
    result TEXT,
    error TEXT
);
CREATE INDEX IF NOT EXISTS idx_analyses_created ON analyses(created_at DESC);
CREATE TABLE IF NOT EXISTS preferences (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    display_name TEXT NOT NULL,
    organization TEXT NOT NULL DEFAULT '',
    bio TEXT NOT NULL DEFAULT '',
    role TEXT NOT NULL DEFAULT 'media',
    active INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS posts (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    body TEXT NOT NULL,
    image_path TEXT,
    analysis_id TEXT,
    hidden INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_posts_created ON posts(created_at DESC);
CREATE TABLE IF NOT EXISTS post_likes (
    post_id TEXT NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    PRIMARY KEY (post_id, user_id)
);
CREATE TABLE IF NOT EXISTS comments (
    id TEXT PRIMARY KEY,
    post_id TEXT NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL,
    body TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_comments_post ON comments(post_id, created_at);
CREATE TABLE IF NOT EXISTS official_sources (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    name TEXT NOT NULL,
    acronym TEXT NOT NULL DEFAULT '',
    category TEXT NOT NULL DEFAULT '',
    website TEXT NOT NULL DEFAULT '',
    email TEXT NOT NULL DEFAULT '',
    phone TEXT NOT NULL DEFAULT '',
    address TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',
    topics TEXT NOT NULL DEFAULT '[]',
    verified_at TEXT,
    active INTEGER NOT NULL DEFAULT 1
);
"""

_SOURCE_FIELDS = ("name", "acronym", "category", "website", "email", "phone", "address", "notes", "topics",
                  "verified_at", "active")

# Colonnes ajoutées après la première version : migrées à l'ouverture de la base.
_ANALYSIS_COLUMNS = {
    "user_id": "TEXT",
    "notes": "TEXT NOT NULL DEFAULT ''",
    "tags": "TEXT NOT NULL DEFAULT '[]'",
    "workflow": "TEXT NOT NULL DEFAULT 'a_traiter'",
}

_UPDATABLE = {"status", "progress", "step", "title", "global_score", "verdict", "result", "error",
              "notes", "tags", "workflow"}
_USER_UPDATABLE = {"display_name", "organization", "bio", "role", "active", "password_hash"}
_LIST_COLS = "id, created_at, updated_at, status, title, input_kind, global_score, verdict, notes, tags, workflow"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Database:
    def __init__(self, path: Path):
        self.path = path
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._lock:
            self._conn.execute("PRAGMA foreign_keys = ON")
            self._conn.executescript(_SCHEMA)
            existing = {r[1] for r in self._conn.execute("PRAGMA table_info(analyses)")}
            for col, decl in _ANALYSIS_COLUMNS.items():
                if col not in existing:
                    self._conn.execute(f"ALTER TABLE analyses ADD COLUMN {col} {decl}")
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_analyses_user ON analyses(user_id, created_at DESC)")
            self._conn.commit()
        self._seed_sources()

    # ---------- analyses ----------
    def create_analysis(self, title: str, input_kind: str, inputs: list[dict[str, Any]],
                        analysis_id: str | None = None, user_id: str | None = None) -> str:
        analysis_id = analysis_id or uuid.uuid4().hex[:16]
        now = _now()
        with self._lock:
            self._conn.execute(
                "INSERT INTO analyses (id, created_at, updated_at, status, progress, step, title, input_kind, inputs,"
                " user_id) VALUES (?, ?, ?, 'pending', 0, 'En attente', ?, ?, ?, ?)",
                (analysis_id, now, now, title, input_kind, json.dumps(inputs, ensure_ascii=False), user_id),
            )
            self._conn.commit()
        return analysis_id

    def update_analysis(self, analysis_id: str, **fields: Any) -> None:
        unknown = set(fields) - _UPDATABLE
        if unknown:
            raise ValueError(f"Champs non modifiables : {unknown}")
        if "result" in fields and fields["result"] is not None and not isinstance(fields["result"], str):
            fields["result"] = json.dumps(fields["result"], ensure_ascii=False, default=str)
        if "tags" in fields and not isinstance(fields["tags"], str):
            fields["tags"] = json.dumps(fields["tags"], ensure_ascii=False)
        fields["updated_at"] = _now()
        cols = ", ".join(f"{k} = ?" for k in fields)
        with self._lock:
            self._conn.execute(f"UPDATE analyses SET {cols} WHERE id = ?", (*fields.values(), analysis_id))
            self._conn.commit()

    def get_analysis(self, analysis_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute("SELECT * FROM analyses WHERE id = ?", (analysis_id,)).fetchone()
        return self._row(row) if row else None

    def list_analyses(self, q: str = "", verdict: str | None = None, limit: int = 20, offset: int = 0,
                      user_id: str | None = None, workflow: str | None = None,
                      tag: str | None = None) -> tuple[list[dict[str, Any]], int]:
        """Liste les analyses d'un utilisateur (toutes si user_id est None, réservé à l'administration)."""
        where, params = [], []
        if user_id is not None:
            where.append("user_id = ?")
            params.append(user_id)
        if q:
            where.append("(LOWER(title) LIKE ? OR LOWER(notes) LIKE ?)")
            params += [f"%{q.lower()}%"] * 2
        if verdict:
            where.append("verdict = ?")
            params.append(verdict)
        if workflow:
            where.append("workflow = ?")
            params.append(workflow)
        if tag:
            where.append("EXISTS (SELECT 1 FROM json_each(analyses.tags) WHERE LOWER(json_each.value) = ?)")
            params.append(tag.lower())
        clause = f"WHERE {' AND '.join(where)}" if where else ""
        with self._lock:
            total = self._conn.execute(f"SELECT COUNT(*) FROM analyses {clause}", params).fetchone()[0]
            rows = self._conn.execute(
                f"SELECT {_LIST_COLS} FROM analyses {clause} ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (*params, limit, offset),
            ).fetchall()
        return [self._list_row(r) for r in rows], total

    def analysis_stats(self, user_id: str | None = None) -> dict[str, Any]:
        clause, params = ("WHERE user_id = ?", [user_id]) if user_id is not None else ("", [])
        with self._lock:
            total, avg = self._conn.execute(
                f"SELECT COUNT(*), AVG(global_score) FROM analyses {clause}", params).fetchone()
            by_verdict = dict(self._conn.execute(
                f"SELECT COALESCE(verdict, 'aucun'), COUNT(*) FROM analyses {clause} GROUP BY 1", params).fetchall())
            by_workflow = dict(self._conn.execute(
                f"SELECT workflow, COUNT(*) FROM analyses {clause} GROUP BY 1", params).fetchall())
            by_status = dict(self._conn.execute(
                f"SELECT status, COUNT(*) FROM analyses {clause} GROUP BY 1", params).fetchall())
            tag_rows = self._conn.execute(
                f"SELECT json_each.value, COUNT(*) FROM analyses, json_each(analyses.tags) {clause}"
                " GROUP BY 1 ORDER BY 2 DESC LIMIT 20", params).fetchall()
        return {"total": total, "average_score": round(avg, 2) if avg is not None else None,
                "by_verdict": by_verdict, "by_workflow": by_workflow, "by_status": by_status,
                "tags": [{"tag": r[0], "count": r[1]} for r in tag_rows]}

    def all_analysis_rows(self, user_id: str) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                f"SELECT {_LIST_COLS} FROM analyses WHERE user_id = ? ORDER BY created_at DESC", (user_id,)).fetchall()
        return [self._list_row(r) for r in rows]

    def claim_orphan_analyses(self, user_id: str) -> None:
        """Rattache les analyses créées avant l'arrivée des comptes au premier administrateur."""
        with self._lock:
            self._conn.execute("UPDATE analyses SET user_id = ? WHERE user_id IS NULL", (user_id,))
            self._conn.commit()

    def delete_analysis(self, analysis_id: str) -> bool:
        with self._lock:
            cur = self._conn.execute("DELETE FROM analyses WHERE id = ?", (analysis_id,))
            self._conn.execute("UPDATE posts SET analysis_id = NULL WHERE analysis_id = ?", (analysis_id,))
            self._conn.commit()
        return cur.rowcount > 0

    def purge_older_than(self, days: int, user_id: str | None = None) -> list[str]:
        """Supprime les analyses trop anciennes d'un utilisateur (ou les analyses sans propriétaire)."""
        limit = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        owner = "user_id = ?" if user_id is not None else "user_id IS NULL"
        params = (limit, user_id) if user_id is not None else (limit,)
        with self._lock:
            ids = [r[0] for r in self._conn.execute(
                f"SELECT id FROM analyses WHERE created_at < ? AND {owner}", params).fetchall()]
            for analysis_id in ids:
                self._conn.execute("DELETE FROM analyses WHERE id = ?", (analysis_id,))
                self._conn.execute("UPDATE posts SET analysis_id = NULL WHERE analysis_id = ?", (analysis_id,))
            self._conn.commit()
        return ids

    def mark_interrupted(self) -> None:
        """Au démarrage, les analyses restées « en cours » ne reprendront pas."""
        with self._lock:
            self._conn.execute(
                "UPDATE analyses SET status = 'error', error = 'Analyse interrompue par un redémarrage du serveur'"
                " WHERE status IN ('pending', 'running')")
            self._conn.commit()

    # ---------- préférences (propres à chaque utilisateur, « app » sert de valeur par défaut) ----------
    def get_preferences(self, user_id: str | None = None) -> dict[str, Any]:
        with self._lock:
            row = None
            if user_id:
                row = self._conn.execute("SELECT value FROM preferences WHERE key = ?", (f"user:{user_id}",)).fetchone()
            row = row or self._conn.execute("SELECT value FROM preferences WHERE key = 'app'").fetchone()
        return json.loads(row[0]) if row else {}

    def save_preferences(self, prefs: dict[str, Any], user_id: str | None = None) -> None:
        key = f"user:{user_id}" if user_id else "app"
        with self._lock:
            self._conn.execute(
                "INSERT INTO preferences (key, value) VALUES (?, ?)"
                " ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, json.dumps(prefs, ensure_ascii=False)),
            )
            self._conn.commit()

    # ---------- utilisateurs et sessions ----------
    def count_users(self) -> int:
        with self._lock:
            return self._conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]

    def create_user(self, email: str, password_hash: str, display_name: str, organization: str,
                    role: str) -> dict[str, Any]:
        user_id = uuid.uuid4().hex[:16]
        with self._lock:
            self._conn.execute(
                "INSERT INTO users (id, created_at, email, password_hash, display_name, organization, role)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (user_id, _now(), email, password_hash, display_name, organization, role))
            self._conn.commit()
        return self.get_user(user_id)  # type: ignore[return-value]

    def get_user(self, user_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row) if row else None

    def get_user_by_email(self, email: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        return dict(row) if row else None

    def update_user(self, user_id: str, **fields: Any) -> None:
        unknown = set(fields) - _USER_UPDATABLE
        if unknown:
            raise ValueError(f"Champs non modifiables : {unknown}")
        if not fields:
            return
        cols = ", ".join(f"{k} = ?" for k in fields)
        with self._lock:
            self._conn.execute(f"UPDATE users SET {cols} WHERE id = ?", (*fields.values(), user_id))
            self._conn.commit()

    def list_users(self, q: str = "") -> list[dict[str, Any]]:
        where, params = "", []
        if q:
            where = "WHERE LOWER(u.display_name) LIKE ? OR LOWER(u.email) LIKE ? OR LOWER(u.organization) LIKE ?"
            params = [f"%{q.lower()}%"] * 3
        with self._lock:
            rows = self._conn.execute(
                "SELECT u.*, (SELECT COUNT(*) FROM analyses a WHERE a.user_id = u.id) AS analyses_count,"
                " (SELECT COUNT(*) FROM posts p WHERE p.user_id = u.id) AS posts_count"
                f" FROM users u {where} ORDER BY u.created_at", params).fetchall()
        return [dict(r) for r in rows]

    def count_admins(self) -> int:
        with self._lock:
            return self._conn.execute("SELECT COUNT(*) FROM users WHERE role = 'admin' AND active = 1").fetchone()[0]

    def create_session(self, token_hash: str, user_id: str, days: int) -> None:
        now = datetime.now(timezone.utc)
        with self._lock:
            self._conn.execute(
                "INSERT INTO sessions (token_hash, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
                (token_hash, user_id, now.isoformat(), (now + timedelta(days=days)).isoformat()))
            self._conn.commit()

    def session_user(self, token_hash: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT u.* FROM sessions s JOIN users u ON u.id = s.user_id"
                " WHERE s.token_hash = ? AND s.expires_at > ?", (token_hash, _now())).fetchone()
        return dict(row) if row else None

    def delete_session(self, token_hash: str) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash,))
            self._conn.commit()

    def delete_user_sessions(self, user_id: str, keep: str | None = None) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM sessions WHERE user_id = ? AND token_hash != ?", (user_id, keep or ""))
            self._conn.commit()

    def purge_sessions(self) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM sessions WHERE expires_at <= ?", (_now(),))
            self._conn.commit()

    # ---------- réseau social ----------
    def create_post(self, user_id: str, body: str, analysis_id: str | None, image_path: str | None,
                    post_id: str | None = None) -> str:
        post_id = post_id or uuid.uuid4().hex[:16]
        now = _now()
        with self._lock:
            self._conn.execute(
                "INSERT INTO posts (id, user_id, created_at, updated_at, body, image_path, analysis_id)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)", (post_id, user_id, now, now, body, image_path, analysis_id))
            self._conn.commit()
        return post_id

    _POST_SELECT = (
        "SELECT p.*, u.display_name AS author_name, u.organization AS author_organization, u.role AS author_role,"
        " (SELECT COUNT(*) FROM post_likes l WHERE l.post_id = p.id) AS likes,"
        " (SELECT COUNT(*) FROM comments c WHERE c.post_id = p.id) AS comments_count,"
        " EXISTS (SELECT 1 FROM post_likes l WHERE l.post_id = p.id AND l.user_id = ?) AS liked,"
        " a.title AS analysis_title, a.global_score AS analysis_score, a.verdict AS analysis_verdict,"
        " a.input_kind AS analysis_kind"
        " FROM posts p JOIN users u ON u.id = p.user_id LEFT JOIN analyses a ON a.id = p.analysis_id"
    )

    def get_post(self, post_id: str, viewer_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute(f"{self._POST_SELECT} WHERE p.id = ?", (viewer_id, post_id)).fetchone()
        return dict(row) if row else None

    def list_posts(self, viewer_id: str, author_id: str | None = None, q: str = "", include_hidden: bool = False,
                   limit: int = 20, offset: int = 0) -> tuple[list[dict[str, Any]], int]:
        where, params = [], []
        if not include_hidden:
            where.append("p.hidden = 0")
        if author_id:
            where.append("p.user_id = ?")
            params.append(author_id)
        if q:
            where.append("(LOWER(p.body) LIKE ? OR LOWER(u.display_name) LIKE ?)")
            params += [f"%{q.lower()}%"] * 2
        clause = f"WHERE {' AND '.join(where)}" if where else ""
        with self._lock:
            total = self._conn.execute(
                f"SELECT COUNT(*) FROM posts p JOIN users u ON u.id = p.user_id {clause}", params).fetchone()[0]
            rows = self._conn.execute(
                f"{self._POST_SELECT} {clause} ORDER BY p.created_at DESC LIMIT ? OFFSET ?",
                (viewer_id, *params, limit, offset)).fetchall()
        return [dict(r) for r in rows], total

    def update_post(self, post_id: str, **fields: Any) -> None:
        unknown = set(fields) - {"body", "hidden"}
        if unknown:
            raise ValueError(f"Champs non modifiables : {unknown}")
        fields["updated_at"] = _now()
        cols = ", ".join(f"{k} = ?" for k in fields)
        with self._lock:
            self._conn.execute(f"UPDATE posts SET {cols} WHERE id = ?", (*fields.values(), post_id))
            self._conn.commit()

    def delete_post(self, post_id: str) -> bool:
        with self._lock:
            cur = self._conn.execute("DELETE FROM posts WHERE id = ?", (post_id,))
            self._conn.commit()
        return cur.rowcount > 0

    def is_analysis_published(self, analysis_id: str) -> bool:
        with self._lock:
            return self._conn.execute(
                "SELECT 1 FROM posts WHERE analysis_id = ? AND hidden = 0", (analysis_id,)).fetchone() is not None

    def set_like(self, post_id: str, user_id: str, liked: bool) -> None:
        with self._lock:
            if liked:
                self._conn.execute("INSERT OR IGNORE INTO post_likes (post_id, user_id) VALUES (?, ?)", (post_id, user_id))
            else:
                self._conn.execute("DELETE FROM post_likes WHERE post_id = ? AND user_id = ?", (post_id, user_id))
            self._conn.commit()

    def add_comment(self, post_id: str, user_id: str, body: str) -> str:
        comment_id = uuid.uuid4().hex[:16]
        with self._lock:
            self._conn.execute("INSERT INTO comments (id, post_id, user_id, created_at, body) VALUES (?, ?, ?, ?, ?)",
                               (comment_id, post_id, user_id, _now(), body))
            self._conn.commit()
        return comment_id

    def list_comments(self, post_id: str) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT c.*, u.display_name AS author_name, u.organization AS author_organization"
                " FROM comments c JOIN users u ON u.id = c.user_id WHERE c.post_id = ? ORDER BY c.created_at",
                (post_id,)).fetchall()
        return [dict(r) for r in rows]

    def get_comment(self, comment_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute("SELECT * FROM comments WHERE id = ?", (comment_id,)).fetchone()
        return dict(row) if row else None

    def delete_comment(self, comment_id: str) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM comments WHERE id = ?", (comment_id,))
            self._conn.commit()

    def platform_stats(self) -> dict[str, int]:
        with self._lock:
            q = lambda sql: self._conn.execute(sql).fetchone()[0]  # noqa: E731
            return {
                "users": q("SELECT COUNT(*) FROM users"),
                "active_users": q("SELECT COUNT(*) FROM users WHERE active = 1"),
                "admins": q("SELECT COUNT(*) FROM users WHERE role = 'admin'"),
                "analyses": q("SELECT COUNT(*) FROM analyses"),
                "posts": q("SELECT COUNT(*) FROM posts"),
                "hidden_posts": q("SELECT COUNT(*) FROM posts WHERE hidden = 1"),
                "comments": q("SELECT COUNT(*) FROM comments"),
                "likes": q("SELECT COUNT(*) FROM post_likes"),
            }

    # ---------- annuaire des sources officielles ----------
    def _seed_sources(self) -> None:
        """Remplit l'annuaire une seule fois ; ensuite il appartient aux administrateurs."""
        from .services.madagascar import OFFICIAL_SOURCES, VERIFIED_AT
        with self._lock:
            done = self._conn.execute("SELECT 1 FROM preferences WHERE key = 'official_sources_seeded'").fetchone()
            if done:
                return
            now = _now()
            for s in OFFICIAL_SOURCES:
                self._conn.execute(
                    "INSERT INTO official_sources (id, created_at, updated_at, name, acronym, category, website, email,"
                    " phone, address, notes, topics, verified_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '', ?, ?)",
                    (uuid.uuid4().hex[:16], now, now, s["name"], s.get("acronym", ""), s.get("category", ""),
                     s.get("website", ""), s.get("email", ""), s.get("phone", ""), s.get("address", ""),
                     json.dumps(s.get("topics", []), ensure_ascii=False), VERIFIED_AT))
            self._conn.execute("INSERT INTO preferences (key, value) VALUES ('official_sources_seeded', 'true')")
            self._conn.commit()

    def list_sources(self, q: str = "", include_inactive: bool = False) -> list[dict[str, Any]]:
        where, params = [], []
        if not include_inactive:
            where.append("active = 1")
        if q:
            where.append("(LOWER(name) LIKE ? OR LOWER(acronym) LIKE ? OR LOWER(category) LIKE ? OR LOWER(topics) LIKE ?)")
            params += [f"%{q.lower()}%"] * 4
        clause = f"WHERE {' AND '.join(where)}" if where else ""
        with self._lock:
            rows = self._conn.execute(f"SELECT * FROM official_sources {clause} ORDER BY category, name", params).fetchall()
        return [self._source_row(r) for r in rows]

    def get_source(self, source_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute("SELECT * FROM official_sources WHERE id = ?", (source_id,)).fetchone()
        return self._source_row(row) if row else None

    def save_source(self, data: dict[str, Any], source_id: str | None = None) -> str:
        fields = {k: data[k] for k in _SOURCE_FIELDS if k in data}
        if "topics" in fields:
            fields["topics"] = json.dumps(fields["topics"], ensure_ascii=False)
        if "active" in fields:
            fields["active"] = int(bool(fields["active"]))
        now = _now()
        with self._lock:
            if source_id is None:
                source_id = uuid.uuid4().hex[:16]
                fields |= {"id": source_id, "created_at": now, "updated_at": now}
                cols = ", ".join(fields)
                self._conn.execute(f"INSERT INTO official_sources ({cols}) VALUES ({', '.join('?' * len(fields))})",
                                   tuple(fields.values()))
            else:
                fields["updated_at"] = now
                cols = ", ".join(f"{k} = ?" for k in fields)
                self._conn.execute(f"UPDATE official_sources SET {cols} WHERE id = ?", (*fields.values(), source_id))
            self._conn.commit()
        return source_id

    def delete_source(self, source_id: str) -> bool:
        with self._lock:
            cur = self._conn.execute("DELETE FROM official_sources WHERE id = ?", (source_id,))
            self._conn.commit()
        return cur.rowcount > 0

    def search_platform_posts(self, terms: list[str], limit: int = 40) -> list[dict[str, Any]]:
        """Publications visibles du fil contenant au moins un des termes (rangement fin fait par l'appelant)."""
        terms = [t for t in terms if len(t) > 2][:8]
        if not terms:
            return []
        cond = " OR ".join(["LOWER(p.body) LIKE ?", "LOWER(COALESCE(a.title, '')) LIKE ?"] * len(terms))
        params = [v for t in terms for v in (f"%{t.lower()}%", f"%{t.lower()}%")]
        with self._lock:
            rows = self._conn.execute(
                "SELECT p.id, p.created_at, p.body, p.image_path, p.analysis_id, u.display_name AS author_name,"
                " u.organization AS author_organization, u.role AS author_role, a.title AS analysis_title,"
                " a.global_score AS analysis_score, a.verdict AS analysis_verdict,"
                " (SELECT COUNT(*) FROM post_likes l WHERE l.post_id = p.id) AS likes"
                " FROM posts p JOIN users u ON u.id = p.user_id LEFT JOIN analyses a ON a.id = p.analysis_id"
                f" WHERE p.hidden = 0 AND u.active = 1 AND ({cond}) ORDER BY p.created_at DESC LIMIT ?",
                (*params, limit)).fetchall()
        return [dict(r) for r in rows]

    @staticmethod
    def _source_row(row: sqlite3.Row) -> dict[str, Any]:
        d = dict(row)
        d["topics"] = json.loads(d["topics"]) if d.get("topics") else []
        d["active"] = bool(d["active"])
        return d

    @staticmethod
    def _row(row: sqlite3.Row) -> dict[str, Any]:
        d = dict(row)
        d["inputs"] = json.loads(d["inputs"]) if d.get("inputs") else []
        d["result"] = json.loads(d["result"]) if d.get("result") else None
        d["tags"] = json.loads(d["tags"]) if d.get("tags") else []
        return d

    @staticmethod
    def _list_row(row: sqlite3.Row) -> dict[str, Any]:
        d = dict(row)
        d["tags"] = json.loads(d["tags"]) if d.get("tags") else []
        return d


_db: Database | None = None


def get_db() -> Database:
    global _db
    if _db is None:
        from .config import get_settings
        _db = Database(get_settings().data_dir / "hoe-aona.sqlite3")
    return _db
