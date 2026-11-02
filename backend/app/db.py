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
"""

_UPDATABLE = {"status", "progress", "step", "title", "global_score", "verdict", "result", "error"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Database:
    def __init__(self, path: Path):
        self.path = path
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._lock:
            self._conn.executescript(_SCHEMA)
            self._conn.commit()

    # ---------- analyses ----------
    def create_analysis(self, title: str, input_kind: str, inputs: list[dict[str, Any]],
                        analysis_id: str | None = None) -> str:
        analysis_id = analysis_id or uuid.uuid4().hex[:16]
        now = _now()
        with self._lock:
            self._conn.execute(
                "INSERT INTO analyses (id, created_at, updated_at, status, progress, step, title, input_kind, inputs)"
                " VALUES (?, ?, ?, 'pending', 0, 'En attente', ?, ?, ?)",
                (analysis_id, now, now, title, input_kind, json.dumps(inputs, ensure_ascii=False)),
            )
            self._conn.commit()
        return analysis_id

    def update_analysis(self, analysis_id: str, **fields: Any) -> None:
        unknown = set(fields) - _UPDATABLE
        if unknown:
            raise ValueError(f"Champs non modifiables : {unknown}")
        if "result" in fields and fields["result"] is not None and not isinstance(fields["result"], str):
            fields["result"] = json.dumps(fields["result"], ensure_ascii=False, default=str)
        fields["updated_at"] = _now()
        cols = ", ".join(f"{k} = ?" for k in fields)
        with self._lock:
            self._conn.execute(f"UPDATE analyses SET {cols} WHERE id = ?", (*fields.values(), analysis_id))
            self._conn.commit()

    def get_analysis(self, analysis_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute("SELECT * FROM analyses WHERE id = ?", (analysis_id,)).fetchone()
        return self._row(row) if row else None

    def list_analyses(self, q: str = "", verdict: str | None = None,
                      limit: int = 20, offset: int = 0) -> tuple[list[dict[str, Any]], int]:
        where, params = [], []
        if q:
            where.append("LOWER(title) LIKE ?")
            params.append(f"%{q.lower()}%")
        if verdict:
            where.append("verdict = ?")
            params.append(verdict)
        clause = f"WHERE {' AND '.join(where)}" if where else ""
        with self._lock:
            total = self._conn.execute(f"SELECT COUNT(*) FROM analyses {clause}", params).fetchone()[0]
            rows = self._conn.execute(
                f"SELECT id, created_at, status, title, input_kind, global_score, verdict FROM analyses {clause}"
                " ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (*params, limit, offset),
            ).fetchall()
        return [dict(r) for r in rows], total

    def delete_analysis(self, analysis_id: str) -> bool:
        with self._lock:
            cur = self._conn.execute("DELETE FROM analyses WHERE id = ?", (analysis_id,))
            self._conn.commit()
        return cur.rowcount > 0

    def purge_older_than(self, days: int) -> list[str]:
        limit = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        with self._lock:
            ids = [r[0] for r in self._conn.execute(
                "SELECT id FROM analyses WHERE created_at < ?", (limit,)).fetchall()]
            self._conn.execute("DELETE FROM analyses WHERE created_at < ?", (limit,))
            self._conn.commit()
        return ids

    def mark_interrupted(self) -> None:
        """Au démarrage, les analyses restées « en cours » ne reprendront pas."""
        with self._lock:
            self._conn.execute(
                "UPDATE analyses SET status = 'error', error = 'Analyse interrompue par un redémarrage du serveur'"
                " WHERE status IN ('pending', 'running')")
            self._conn.commit()

    # ---------- préférences ----------
    def get_preferences(self) -> dict[str, Any]:
        with self._lock:
            row = self._conn.execute("SELECT value FROM preferences WHERE key = 'app'").fetchone()
        return json.loads(row[0]) if row else {}

    def save_preferences(self, prefs: dict[str, Any]) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO preferences (key, value) VALUES ('app', ?)"
                " ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (json.dumps(prefs, ensure_ascii=False),),
            )
            self._conn.commit()

    @staticmethod
    def _row(row: sqlite3.Row) -> dict[str, Any]:
        d = dict(row)
        d["inputs"] = json.loads(d["inputs"]) if d.get("inputs") else []
        d["result"] = json.loads(d["result"]) if d.get("result") else None
        return d


_db: Database | None = None


def get_db() -> Database:
    global _db
    if _db is None:
        from .config import get_settings
        _db = Database(get_settings().data_dir / "hoe-aona.sqlite3")
    return _db
