"""Short rolling memory — never store full chat transcripts."""

from __future__ import annotations

import sqlite3

from helpinghand.db import connect

MAX_SUMMARY_CHARS = 800


class MemoryStore:
    def __init__(self, conn: sqlite3.Connection, *, max_chars: int = MAX_SUMMARY_CHARS) -> None:
        self.conn = conn
        self.max_chars = max_chars
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS memory (
              discord_id TEXT PRIMARY KEY,
              summary TEXT NOT NULL,
              updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        self.conn.commit()

    def get(self, user_id: str) -> str:
        row = self.conn.execute(
            "SELECT summary FROM memory WHERE discord_id = ?", (user_id,)
        ).fetchone()
        return row["summary"] if row else ""

    def remember(self, user_id: str, user_text: str, specialist: str, reply: str) -> str:
        prior = self.get(user_id)
        snippet_user = " ".join((user_text or "").split())[:180]
        snippet_bot = " ".join((reply or "").split())[:180]
        addition = f"U:{snippet_user} | {specialist}:{snippet_bot}"
        summary = f"{prior} // {addition}".strip(" /") if prior else addition
        if len(summary) > self.max_chars:
            summary = summary[-self.max_chars :]
            cut = summary.find(" // ")
            if cut != -1:
                summary = summary[cut + 4 :]
        self.conn.execute(
            """
            INSERT INTO memory (discord_id, summary, updated_at) VALUES (?, ?, datetime('now'))
            ON CONFLICT(discord_id) DO UPDATE SET summary = excluded.summary, updated_at = datetime('now')
            """,
            (user_id, summary),
        )
        self.conn.commit()
        return summary


def open_memory(path) -> MemoryStore:
    return MemoryStore(connect(path))
