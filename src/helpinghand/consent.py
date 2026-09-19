"""PERMIT / STOP consent. STOP is permanent — never email that student again."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class Consent:
    user_id: str
    email: str
    permitted: bool
    stopped: bool
    last_quota_nudge_day: str | None


class ConsentStore:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS consent (
              user_id TEXT PRIMARY KEY,
              email TEXT,
              permitted INTEGER NOT NULL DEFAULT 0,
              stopped INTEGER NOT NULL DEFAULT 0,
              last_quota_nudge_day TEXT,
              updated_at TEXT
            )
            """
        )
        self.conn.commit()

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def get(self, user_id: str) -> Consent:
        row = self.conn.execute(
            "SELECT * FROM consent WHERE user_id = ?", (user_id,)
        ).fetchone()
        if row is None:
            return Consent(user_id, "", False, False, None)
        return Consent(
            user_id=row["user_id"],
            email=row["email"] or "",
            permitted=bool(row["permitted"]),
            stopped=bool(row["stopped"]),
            last_quota_nudge_day=row["last_quota_nudge_day"],
        )

    def permit(self, user_id: str, email: str) -> Consent:
        current = self.get(user_id)
        if current.stopped:
            return current
        self.conn.execute(
            """
            INSERT INTO consent (user_id, email, permitted, stopped, updated_at)
            VALUES (?, ?, 1, 0, ?)
            ON CONFLICT(user_id) DO UPDATE SET
              email = excluded.email,
              permitted = 1,
              updated_at = excluded.updated_at
            """,
            (user_id, email, self._now()),
        )
        self.conn.commit()
        return self.get(user_id)

    def stop(self, user_id: str) -> Consent:
        self.conn.execute(
            """
            INSERT INTO consent (user_id, email, permitted, stopped, updated_at)
            VALUES (?, '', 0, 1, ?)
            ON CONFLICT(user_id) DO UPDATE SET
              permitted = 0,
              stopped = 1,
              updated_at = excluded.updated_at
            """,
            (user_id, self._now()),
        )
        self.conn.commit()
        return self.get(user_id)

    def can_email(self, user_id: str) -> bool:
        snap = self.get(user_id)
        return snap.permitted and not snap.stopped

    def mark_quota_nudge(self, user_id: str, day: str) -> None:
        self.conn.execute(
            """
            INSERT INTO consent (user_id, email, permitted, stopped, last_quota_nudge_day, updated_at)
            VALUES (?, '', 0, 0, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
              last_quota_nudge_day = excluded.last_quota_nudge_day,
              updated_at = excluded.updated_at
            """,
            (user_id, day, self._now()),
        )
        self.conn.commit()
