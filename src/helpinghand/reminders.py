"""Focus reminders stored for Gmail notify — never Discord."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone

from helpinghand.db import connect


@dataclass(frozen=True)
class Reminder:
    id: int
    user_id: str
    fire_at: datetime
    line: str
    kind: str
    sender: str
    sent: bool
    channel_id: str  # unused leftover; must not be used to ping Discord


class ReminderStore:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reminders (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id TEXT NOT NULL,
              channel_id TEXT NOT NULL DEFAULT '',
              fire_at TEXT NOT NULL,
              payload TEXT NOT NULL,
              sent INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        cols = {row[1] for row in self.conn.execute("PRAGMA table_info(reminders)")}
        if "kind" not in cols:
            self.conn.execute("ALTER TABLE reminders ADD COLUMN kind TEXT NOT NULL DEFAULT 'reminder'")
        if "sender" not in cols:
            self.conn.execute("ALTER TABLE reminders ADD COLUMN sender TEXT NOT NULL DEFAULT 'focus'")
        if "line" not in cols:
            self.conn.execute("ALTER TABLE reminders ADD COLUMN line TEXT NOT NULL DEFAULT ''")
        self.conn.commit()

    def add(
        self,
        *,
        user_id: str,
        fire_at: datetime,
        line: str,
        kind: str = "reminder",
        sender: str = "focus",
        channel_id: str = "",
    ) -> int:
        when = fire_at.astimezone(timezone.utc).isoformat() if fire_at.tzinfo else fire_at.replace(tzinfo=timezone.utc).isoformat()
        cur = self.conn.execute(
            """
            INSERT INTO reminders (user_id, channel_id, fire_at, payload, kind, sender, line)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, channel_id or "", when, line, kind, sender, line),
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
            line = row["line"] or row["payload"]
            out.append(
                Reminder(
                    id=row["id"],
                    user_id=row["user_id"],
                    fire_at=datetime.fromisoformat(row["fire_at"]),
                    line=line,
                    kind=row["kind"] if "kind" in row.keys() else "reminder",
                    sender=row["sender"] if "sender" in row.keys() else "focus",
                    sent=bool(row["sent"]),
                    channel_id=row["channel_id"] or "",
                )
            )
        return out

    def mark_sent(self, reminder_id: int) -> None:
        self.conn.execute("UPDATE reminders SET sent = 1 WHERE id = ?", (reminder_id,))
        self.conn.commit()


def open_reminders(path) -> ReminderStore:
    return ReminderStore(connect(path))
