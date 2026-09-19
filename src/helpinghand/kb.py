"""Campus knowledge base — local SQLite FTS5, no xAI web search."""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from importlib import resources
from pathlib import Path

from helpinghand.db import connect

_SAFE_TOKEN = re.compile(r"[\w\u0980-\u09FF]+", re.UNICODE)
_STOP = frozenset(
    {
        "a",
        "an",
        "the",
        "is",
        "are",
        "was",
        "when",
        "what",
        "where",
        "who",
        "how",
        "why",
        "of",
        "for",
        "to",
        "in",
        "on",
        "at",
        "my",
        "me",
        "our",
        "your",
        "about",
        "this",
        "that",
        "with",
        "from",
        "and",
        "or",
        "please",
        "tell",
        "do",
        "does",
        "can",
        "i",
        "we",
        "it",
        "কখন",
        "কি",
        "কী",
        "কে",
        "আমার",
        "আমাদের",
        "কিভাবে",
    }
)


@dataclass(frozen=True)
class KbHit:
    id: int
    title: str
    body: str


@dataclass(frozen=True)
class KbDoc:
    id: int
    title: str
    body: str
    added_by: str | None
    added_at: str


def _fts_query(raw: str) -> str:
    found = _SAFE_TOKEN.findall(raw or "")
    tokens = [tok for tok in found if tok.lower() not in _STOP and len(tok) > 1]
    if not tokens:
        tokens = [tok for tok in found if len(tok) > 1][:8]
    if not tokens:
        return ""
    return " OR ".join(f'"{tok}"' for tok in tokens[:12])


class KnowledgeBase:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn
        self._init()

    def _init(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS kb_docs (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              title TEXT NOT NULL,
              body TEXT NOT NULL,
              added_by TEXT,
              added_at TEXT NOT NULL
            );
            CREATE VIRTUAL TABLE IF NOT EXISTS kb_fts USING fts5(
              title,
              body,
              content='kb_docs',
              content_rowid='id',
              tokenize='unicode61'
            );
            CREATE TRIGGER IF NOT EXISTS kb_docs_ai AFTER INSERT ON kb_docs BEGIN
              INSERT INTO kb_fts(rowid, title, body) VALUES (new.id, new.title, new.body);
            END;
            CREATE TRIGGER IF NOT EXISTS kb_docs_ad AFTER DELETE ON kb_docs BEGIN
              INSERT INTO kb_fts(kb_fts, rowid, title, body) VALUES('delete', old.id, old.title, old.body);
            END;
            CREATE TRIGGER IF NOT EXISTS kb_docs_au AFTER UPDATE ON kb_docs BEGIN
              INSERT INTO kb_fts(kb_fts, rowid, title, body) VALUES('delete', old.id, old.title, old.body);
              INSERT INTO kb_fts(rowid, title, body) VALUES (new.id, new.title, new.body);
            END;
            """
        )
        self.conn.commit()

    def count(self) -> int:
        row = self.conn.execute("SELECT COUNT(*) AS n FROM kb_docs").fetchone()
        return int(row["n"])

    def add(self, title: str, body: str, *, added_by: str | None = None) -> int:
        title = (title or "").strip()
        body = (body or "").strip()
        if not title or not body:
            raise ValueError("title and body are required")
        cur = self.conn.execute(
            "INSERT INTO kb_docs (title, body, added_by, added_at) VALUES (?, ?, ?, ?)",
            (title, body, added_by, datetime.now(timezone.utc).isoformat()),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def search(self, query: str, *, limit: int = 5) -> list[KbHit]:
        match = _fts_query(query)
        if not match:
            return []
        rows = self.conn.execute(
            """
            SELECT kb_docs.id, kb_docs.title, kb_docs.body
            FROM kb_fts
            JOIN kb_docs ON kb_docs.id = kb_fts.rowid
            WHERE kb_fts MATCH ?
            ORDER BY rank
            LIMIT ?
            """,
            (match, limit),
        ).fetchall()
        return [KbHit(int(r["id"]), r["title"], r["body"]) for r in rows]

    def format_hits(self, hits: list[KbHit], *, lang: str = "en") -> str:
        if not hits:
            return ""
        chunks = []
        for hit in hits:
            body = hit.body if len(hit.body) < 900 else hit.body[:880] + "…"
            chunks.append(f"**{hit.title}**\n{body}")
        header = {
            "en": "From the campus knowledge base:",
            "bn": "ক্যাম্পাস নলেজ বেস থেকে:",
            "mix": "Campus KB থেকে:",
        }.get(lang, "From the campus knowledge base:")
        return header + "\n\n" + "\n\n".join(chunks)

    def seed_sample_faqs(self) -> int:
        if self.count():
            return 0
        payload = resources.files("helpinghand.data").joinpath("sample_faqs.json").read_text(encoding="utf-8")
        docs = json.loads(payload)
        added = 0
        for doc in docs:
            self.add(doc["title"], doc["body"], added_by="seed")
            added += 1
        return added


def open_kb(path: str | Path) -> KnowledgeBase:
    return KnowledgeBase(connect(path))
