"""Discord reminders for Focus (no Grok)."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone

from helpinghand.db import connect


@dataclass(frozen=True)
class Reminder:
    id: int
    user_id: str
    channel_id: str
    fire_at: datetime
    payload: str


class ReminderStore:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reminders (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id TEXT NOT NULL,
              channel_id TEXT NOT NULL,
              fire_at TEXT NOT NULL,
              payload TEXT NOT NULL,
              sent INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        self.conn.commit()

    def add(self, *, user_id: str, channel_id: str, fire_at: datetime, payload: str) -> int:
        cur = self.conn.execute(
            "INSERT INTO reminders (user_id, channel_id, fire_at, payload) VALUES (?, ?, ?, ?)",
            (user_id, channel_id, fire_at.astimezone(timezone.utc).isoformat(), payload),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def due(self, now: datetime | None = None) -> list[Reminder]:
        moment = (now or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat()
        rows = self.conn.execute(
            "SELECT * FROM reminders WHERE sent = 0 AND fire_at <= ? ORDER BY fire_at",
            (moment,),
        ).fetchall()
        out: list[Reminder] = []
        for row in rows:
            out.append(
                Reminder(
                    id=row["id"],
                    user_id=row["user_id"],
                    channel_id=row["channel_id"],
                    fire_at=datetime.fromisoformat(row["fire_at"]),
                    payload=row["payload"],
                )
            )
        return out

    def mark_sent(self, reminder_id: int) -> None:
        self.conn.execute("UPDATE reminders SET sent = 1 WHERE id = ?", (reminder_id,))
        self.conn.commit()


def open_reminders(path) -> ReminderStore:
    return ReminderStore(connect(path))
