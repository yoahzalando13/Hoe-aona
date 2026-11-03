"""Vérification physique : positions des comptes et demandes géolocalisées (PostgreSQL + PostGIS).

Les positions des comptes ne quittent jamais ce module : aucune requête ne les renvoie à l'API.
Seule la base calcule qui se trouve dans le rayon d'une demande (ST_DWithin sur des `geography`).
"""
from __future__ import annotations

import logging
import threading
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

_SCHEMA = """
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE TABLE IF NOT EXISTS user_locations (
    user_id TEXT PRIMARY KEY,
    position geography(Point, 4326) NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_user_locations_position ON user_locations USING GIST (position);
CREATE TABLE IF NOT EXISTS verification_requests (
    id TEXT PRIMARY KEY,
    requester_id TEXT NOT NULL,
    analysis_id TEXT,
    claim TEXT NOT NULL,
    details TEXT NOT NULL DEFAULT '',
    place_label TEXT NOT NULL,
    place geography(Point, 4326) NOT NULL,
    radius_m INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    verifier_id TEXT,
    accepted_at timestamptz,
    outcome TEXT,
    report TEXT NOT NULL DEFAULT '',
    photo_path TEXT,
    completed_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    expires_at timestamptz NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_verifications_requester ON verification_requests(requester_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_verifications_verifier ON verification_requests(verifier_id, created_at DESC);
CREATE TABLE IF NOT EXISTS verification_recipients (
    request_id TEXT NOT NULL REFERENCES verification_requests(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL,
    declined BOOLEAN NOT NULL DEFAULT false,
    PRIMARY KEY (request_id, user_id)
);
CREATE INDEX IF NOT EXISTS idx_recipients_user ON verification_recipients(user_id);
CREATE TABLE IF NOT EXISTS notifications (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    request_id TEXT NOT NULL REFERENCES verification_requests(id) ON DELETE CASCADE,
    created_at timestamptz NOT NULL DEFAULT now(),
    delivered_at timestamptz,
    read_at timestamptz
);
CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id, created_at DESC);
"""

# Colonnes renvoyées pour une demande : le point visé est exposé, jamais la position d'un compte.
_REQUEST_COLS = ("id, requester_id, analysis_id, claim, details, place_label, ST_Y(place::geometry) AS latitude,"
                 " ST_X(place::geometry) AS longitude, radius_m, status, verifier_id, accepted_at, outcome, report,"
                 " photo_path, completed_at, created_at, expires_at")


def _point(latitude: float, longitude: float) -> tuple[float, float]:
    return longitude, latitude  # ordre attendu par ST_MakePoint


class GeoStore:
    def __init__(self, url: str):
        import psycopg
        from psycopg.rows import dict_row

        self._connect = lambda: psycopg.connect(url, autocommit=True, row_factory=dict_row)
        self._lock = threading.Lock()
        self._conn = self._connect()
        with self._lock:
            self._conn.execute(_SCHEMA)

    def _exec(self, sql: str, params: tuple | dict = ()) -> list[dict[str, Any]]:
        with self._lock:
            if self._conn.closed:
                self._conn = self._connect()
            cur = self._conn.execute(sql, params)
            return cur.fetchall() if cur.description else []

    def _transaction(self, steps):
        """Exécute `steps(conn)` dans une transaction et renvoie son résultat."""
        with self._lock:
            if self._conn.closed:
                self._conn = self._connect()
            with self._conn.transaction():
                return steps(self._conn)

    # ---------- positions (jamais relues par l'API) ----------
    def set_location(self, user_id: str, latitude: float, longitude: float) -> None:
        self._exec(
            "INSERT INTO user_locations (user_id, position, updated_at)"
            " VALUES (%s, ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography, now())"
            " ON CONFLICT (user_id) DO UPDATE SET position = EXCLUDED.position, updated_at = now()",
            (user_id, *_point(latitude, longitude)),
        )

    def delete_location(self, user_id: str) -> None:
        self._exec("DELETE FROM user_locations WHERE user_id = %s", (user_id,))

    def location_status(self, user_id: str) -> datetime | None:
        rows = self._exec("SELECT updated_at FROM user_locations WHERE user_id = %s", (user_id,))
        return rows[0]["updated_at"] if rows else None

    def purge_locations(self, max_age_minutes: int) -> None:
        self._exec("DELETE FROM user_locations WHERE updated_at < now() - make_interval(mins => %s)",
                   (max_age_minutes,))

    # ---------- demandes ----------
    def create_request(self, requester_id: str, claim: str, details: str, place_label: str, latitude: float,
                       longitude: float, radius_m: int, hours: int, max_age_minutes: int,
                       analysis_id: str | None = None) -> str:
        request_id = uuid.uuid4().hex[:16]
        expires = datetime.now(timezone.utc) + timedelta(hours=hours)
        lon, lat = _point(latitude, longitude)

        def steps(conn):
            conn.execute(
                "INSERT INTO verification_requests (id, requester_id, analysis_id, claim, details, place_label, place,"
                " radius_m, expires_at) VALUES (%s, %s, %s, %s, %s, %s,"
                " ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography, %s, %s)",
                (request_id, requester_id, analysis_id, claim, details, place_label, lon, lat, radius_m, expires),
            )
            self._notify_nearby(conn, request_id, exclude=[requester_id], max_age_minutes=max_age_minutes)
        self._transaction(steps)
        return request_id

    @staticmethod
    def _notify_nearby(conn, request_id: str, exclude: list[str], max_age_minutes: int) -> None:
        """Destinataires : positions récentes dans le rayon de la demande, calculées par PostGIS seul."""
        conn.execute(
            "INSERT INTO verification_recipients (request_id, user_id)"
            " SELECT r.id, l.user_id FROM verification_requests r JOIN user_locations l"
            "   ON ST_DWithin(l.position, r.place, r.radius_m)"
            " WHERE r.id = %s AND l.user_id <> ALL(%s)"
            "   AND l.updated_at >= now() - make_interval(mins => %s)"
            " ON CONFLICT DO NOTHING",
            (request_id, exclude, max_age_minutes),
        )
        conn.execute(
            "INSERT INTO notifications (id, user_id, kind, request_id)"
            " SELECT substr(md5(random()::text || user_id), 1, 16), user_id, 'verification_request', request_id"
            " FROM verification_recipients WHERE request_id = %s AND NOT declined"
            "   AND user_id <> ALL(%s)",
            (request_id, exclude),
        )

    def get_request(self, request_id: str) -> dict[str, Any] | None:
        rows = self._exec(f"SELECT {_REQUEST_COLS} FROM verification_requests WHERE id = %s", (request_id,))
        return rows[0] if rows else None

    def is_recipient(self, request_id: str, user_id: str) -> bool:
        rows = self._exec("SELECT declined FROM verification_recipients WHERE request_id = %s AND user_id = %s",
                          (request_id, user_id))
        return bool(rows) and not rows[0]["declined"]

    def expire_requests(self) -> None:
        self._exec("UPDATE verification_requests SET status = 'expired' WHERE status = 'open' AND expires_at < now()")
        self._exec("DELETE FROM notifications n USING verification_requests r WHERE n.request_id = r.id"
                   " AND n.kind = 'verification_request' AND r.status = 'expired'")

    def list_nearby(self, user_id: str) -> list[dict[str, Any]]:
        return self._exec(
            f"SELECT {_REQUEST_COLS} FROM verification_requests WHERE status = 'open' AND id IN"
            " (SELECT request_id FROM verification_recipients WHERE user_id = %s AND NOT declined)"
            " ORDER BY created_at DESC", (user_id,))

    def list_by_requester(self, user_id: str, limit: int = 50) -> list[dict[str, Any]]:
        return self._exec(f"SELECT {_REQUEST_COLS} FROM verification_requests WHERE requester_id = %s"
                          " ORDER BY created_at DESC LIMIT %s", (user_id, limit))

    def list_by_verifier(self, user_id: str, limit: int = 50) -> list[dict[str, Any]]:
        return self._exec(f"SELECT {_REQUEST_COLS} FROM verification_requests WHERE verifier_id = %s"
                          " ORDER BY (status = 'accepted') DESC, created_at DESC LIMIT %s", (user_id, limit))

    def count_open_by_requester(self, user_id: str) -> int:
        rows = self._exec("SELECT count(*) AS n FROM verification_requests WHERE requester_id = %s"
                          " AND status IN ('open', 'accepted')", (user_id,))
        return rows[0]["n"]

    def accept(self, request_id: str, verifier_id: str) -> bool:
        """Attribution atomique : un seul compte peut accepter ; l'annonce disparaît chez les autres."""
        def steps(conn):
            row = conn.execute(
                "UPDATE verification_requests SET status = 'accepted', verifier_id = %s, accepted_at = now()"
                " WHERE id = %s AND status = 'open' AND expires_at >= now() RETURNING requester_id",
                (verifier_id, request_id)).fetchone()
            if not row:
                return False
            conn.execute("DELETE FROM notifications WHERE request_id = %s AND kind = 'verification_request'",
                         (request_id,))
            self._add_notification(conn, row["requester_id"], "verification_accepted", request_id)
            return True
        return self._transaction(steps)

    def decline(self, request_id: str, user_id: str) -> None:
        self._exec("UPDATE verification_recipients SET declined = true WHERE request_id = %s AND user_id = %s",
                   (request_id, user_id))
        self._exec("DELETE FROM notifications WHERE request_id = %s AND user_id = %s"
                   " AND kind = 'verification_request'", (request_id, user_id))

    def release(self, request_id: str, verifier_id: str, max_age_minutes: int) -> bool:
        """Le vérificateur renonce : la demande est rouverte et proposée de nouveau aux autres destinataires."""
        def steps(conn):
            row = conn.execute(
                "UPDATE verification_requests SET status = 'open', verifier_id = NULL, accepted_at = NULL"
                " WHERE id = %s AND status = 'accepted' AND verifier_id = %s RETURNING requester_id",
                (request_id, verifier_id)).fetchone()
            if not row:
                return False
            conn.execute("UPDATE verification_recipients SET declined = true WHERE request_id = %s AND user_id = %s",
                         (request_id, verifier_id))
            self._notify_nearby(conn, request_id, exclude=[row["requester_id"], verifier_id],
                                max_age_minutes=max_age_minutes)
            self._add_notification(conn, row["requester_id"], "verification_released", request_id)
            return True
        return self._transaction(steps)

    def complete(self, request_id: str, verifier_id: str, outcome: str, report: str,
                 photo_path: str | None) -> bool:
        def steps(conn):
            row = conn.execute(
                "UPDATE verification_requests SET status = 'completed', outcome = %s, report = %s, photo_path = %s,"
                " completed_at = now() WHERE id = %s AND status = 'accepted' AND verifier_id = %s"
                " RETURNING requester_id",
                (outcome, report, photo_path, request_id, verifier_id)).fetchone()
            if not row:
                return False
            self._add_notification(conn, row["requester_id"], "verification_completed", request_id)
            return True
        return self._transaction(steps)

    def cancel(self, request_id: str, requester_id: str) -> bool:
        def steps(conn):
            row = conn.execute(
                "UPDATE verification_requests SET status = 'cancelled' WHERE id = %s AND requester_id = %s"
                " AND status IN ('open', 'accepted') RETURNING verifier_id",
                (request_id, requester_id)).fetchone()
            if not row:
                return False
            conn.execute("DELETE FROM notifications WHERE request_id = %s AND kind = 'verification_request'",
                         (request_id,))
            if row["verifier_id"]:
                self._add_notification(conn, row["verifier_id"], "verification_cancelled", request_id)
            return True
        return self._transaction(steps)

    # ---------- notifications ----------
    @staticmethod
    def _add_notification(conn, user_id: str, kind: str, request_id: str) -> None:
        conn.execute("INSERT INTO notifications (id, user_id, kind, request_id) VALUES (%s, %s, %s, %s)",
                     (uuid.uuid4().hex[:16], user_id, kind, request_id))

    def list_notifications(self, user_id: str, undelivered: bool = False, limit: int = 50) -> list[dict[str, Any]]:
        """Notifications du compte ; `undelivered` ne renvoie que les nouvelles et les marque comme remises."""
        if undelivered:
            return self._exec(
                "UPDATE notifications SET delivered_at = now() WHERE user_id = %s AND delivered_at IS NULL"
                " RETURNING id, kind, request_id, created_at, read_at", (user_id,))
        return self._exec("SELECT id, kind, request_id, created_at, read_at FROM notifications WHERE user_id = %s"
                          " ORDER BY created_at DESC LIMIT %s", (user_id, limit))

    def mark_read(self, user_id: str, ids: list[str] | None = None) -> None:
        if ids:
            self._exec("UPDATE notifications SET read_at = now() WHERE user_id = %s AND id = ANY(%s)"
                       " AND read_at IS NULL", (user_id, ids))
        else:
            self._exec("UPDATE notifications SET read_at = now() WHERE user_id = %s AND read_at IS NULL", (user_id,))

    def forget_user(self, user_id: str) -> None:
        """Compte désactivé : sa position disparaît et il ne reçoit plus de demandes."""
        self.delete_location(user_id)
        self._exec("DELETE FROM verification_recipients WHERE user_id = %s", (user_id,))
        self._exec("DELETE FROM notifications WHERE user_id = %s AND kind = 'verification_request'", (user_id,))


_geo: GeoStore | None = None


def get_geo() -> GeoStore | None:
    """Stockage PostGIS, ou None si POSTGIS_URL n'est pas configuré."""
    global _geo
    if _geo is None:
        from .config import get_settings
        url = get_settings().postgis_url
        if url:
            try:
                _geo = GeoStore(url)
            except Exception as exc:  # base injoignable : nouvel essai au prochain appel
                logging.getLogger(__name__).warning("PostGIS injoignable : %s", exc)
    return _geo
