"""Per-user daily quotas. Paid = Crew Member role or /grant until date."""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Callable

from helpinghand import PAID_ROLE_NAME
from helpinghand.db import connect

_DURATION_RE = re.compile(r"^\s*(\d+)\s*d(?:ays?)?\s*$", re.I)


class QuotaExceededError(Exception):
    def __init__(self, used: int, limit: int, paid: bool) -> None:
        super().__init__(f"quota exceeded {used}/{limit}")
        self.used = used
        self.limit = limit
        self.paid = paid


@dataclass(frozen=True)
class QuotaStatus:
    user_id: str
    day: str
    used: int
    limit: int
    remaining: int
    paid: bool
    granted_until: str | None
    role: str


def parse_duration(spec: str, *, default_days: int = 30) -> timedelta:
    raw = (spec or "").strip() or f"{default_days}d"
    match = _DURATION_RE.fullmatch(raw)
    if not match:
        raise ValueError("duration must look like 30d or 7d")
    days = int(match.group(1))
    if days < 1 or days > 366:
        raise ValueError("duration must be 1–366 days")
    return timedelta(days=days)


class QuotaManager:
    def __init__(
        self,
        conn: sqlite3.Connection,
        *,
        free_daily: int = 15,
        paid_daily: int = 80,
        paid_role_name: str = PAID_ROLE_NAME,
        today: Callable[[], date] | None = None,
    ) -> None:
        self.conn = conn
        self.free_daily = free_daily
        self.paid_daily = paid_daily
        self.paid_role_name = paid_role_name
        self._today = today or (lambda: datetime.now(timezone.utc).date())
        self._init()

    def _init(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS crew_users (
              discord_id TEXT PRIMARY KEY,
              granted_until TEXT,
              note TEXT
            );
            CREATE TABLE IF NOT EXISTS daily_usage (
              discord_id TEXT NOT NULL,
              day TEXT NOT NULL,
              count INTEGER NOT NULL DEFAULT 0,
              PRIMARY KEY (discord_id, day)
            );
            """
        )
        self.conn.commit()

    def today_iso(self) -> str:
        return self._today().isoformat()

    def granted_until(self, user_id: str) -> date | None:
        row = self.conn.execute(
            "SELECT granted_until FROM crew_users WHERE discord_id = ?",
            (user_id,),
        ).fetchone()
        if not row or not row["granted_until"]:
            return None
        return date.fromisoformat(row["granted_until"])

    def is_paid(self, user_id: str, *, has_paid_role: bool = False, on: date | None = None) -> bool:
        if has_paid_role:
            return True
        until = self.granted_until(user_id)
        if until is None:
            return False
        return until >= (on or self._today())

    def daily_limit(self, user_id: str, *, has_paid_role: bool = False) -> int:
        return self.paid_daily if self.is_paid(user_id, has_paid_role=has_paid_role) else self.free_daily

    def used_today(self, user_id: str, *, on: date | None = None) -> int:
        day = (on or self._today()).isoformat()
        row = self.conn.execute(
            "SELECT count FROM daily_usage WHERE discord_id = ? AND day = ?",
            (user_id, day),
        ).fetchone()
        return int(row["count"]) if row else 0

    def status(self, user_id: str, *, has_paid_role: bool = False) -> QuotaStatus:
        used = self.used_today(user_id)
        paid = self.is_paid(user_id, has_paid_role=has_paid_role)
        limit = self.paid_daily if paid else self.free_daily
        until = self.granted_until(user_id)
        return QuotaStatus(
            user_id=user_id,
            day=self.today_iso(),
            used=used,
            limit=limit,
            remaining=max(0, limit - used),
            paid=paid,
            granted_until=until.isoformat() if until else None,
            role=self.paid_role_name if paid else "Free",
        )

    def check(self, user_id: str, *, has_paid_role: bool = False) -> QuotaStatus:
        snap = self.status(user_id, has_paid_role=has_paid_role)
        if snap.used >= snap.limit:
            raise QuotaExceededError(snap.used, snap.limit, snap.paid)
        return snap

    def consume(self, user_id: str, *, has_paid_role: bool = False) -> QuotaStatus:
        self.check(user_id, has_paid_role=has_paid_role)
        day = self.today_iso()
        self.conn.execute(
            """
            INSERT INTO daily_usage (discord_id, day, count) VALUES (?, ?, 1)
            ON CONFLICT(discord_id, day) DO UPDATE SET count = count + 1
            """,
            (user_id, day),
        )
        self.conn.commit()
        return self.status(user_id, has_paid_role=has_paid_role)

    def grant(self, user_id: str, duration: str = "30d", *, note: str | None = None) -> date:
        until = self._today() + parse_duration(duration)
        self.conn.execute(
            """
            INSERT INTO crew_users (discord_id, granted_until, note) VALUES (?, ?, ?)
            ON CONFLICT(discord_id) DO UPDATE SET granted_until = excluded.granted_until,
              note = COALESCE(excluded.note, crew_users.note)
            """,
            (user_id, until.isoformat(), note),
        )
        self.conn.commit()
        return until


def open_quota(path, **kwargs) -> QuotaManager:
    return QuotaManager(connect(path), **kwargs)
