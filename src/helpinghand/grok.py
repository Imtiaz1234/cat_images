"""Single xAI client: grok-4.3 default, grok-build-0.1 for code, budget kill-switch."""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

import httpx

from helpinghand.config import CODE_MODEL, DEFAULT_MODEL, Settings
from helpinghand.db import connect

log = logging.getLogger(__name__)

# USD per 1M tokens. Cached input is billed cheaper; never enable xAI web_search.
PRICING: dict[str, dict[str, float]] = {
    "grok-4.3": {"input": 1.25, "output": 2.50, "cached": 0.20},
    "grok-build-0.1": {"input": 1.00, "output": 2.00, "cached": 0.20},
    "grok-4.5": {"input": 2.00, "output": 6.00, "cached": 0.30},
    "grok-4.6": {"input": 2.00, "output": 6.00, "cached": 0.50},
}

_CODE_HINTS = (
    "```",
    "stack trace",
    "syntax error",
    "compiler",
    "write a function",
    "write a program",
    "debug this",
    "leetcode",
    "runtime error",
    "nullpointer",
    "traceback",
    "কোড লিখ",
    "প্রোগ্রাম লিখ",
    "বাগ ফিক্স",
)
_LANG_TOKENS = ("python", "javascript", "typescript", "c++", "java", "golang", "rust", "sql")
_CODE_VERBS = ("code", "function", "program", "compile", "debug", "implement", "snippet", "script", "refactor")


class BudgetExceededError(Exception):
    """Monthly Grok spend cap reached; AI replies must pause."""


@dataclass(frozen=True)
class ChatResult:
    text: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    cached_tokens: int
    cost_usd: float
    max_tokens: int


@dataclass(frozen=True)
class BudgetSnapshot:
    year_month: str
    input_tokens: int
    output_tokens: int
    cached_tokens: int
    estimated_usd: float
    paused: bool
    cap_usd: float

    @property
    def remaining_usd(self) -> float:
        return max(0.0, self.cap_usd - self.estimated_usd)


def looks_like_code(text: str) -> bool:
    t = (text or "").lower()
    if any(h in t for h in _CODE_HINTS):
        return True
    has_lang = any(tok in t for tok in _LANG_TOKENS)
    has_verb = any(v in t for v in _CODE_VERBS)
    return has_lang and has_verb


def pricing_for(model: str) -> dict[str, float]:
    for key, prices in PRICING.items():
        if model == key or model.startswith(key):
            return prices
    return PRICING["grok-4.3"]


def estimate_cost_usd(
    model: str,
    *,
    prompt_tokens: int,
    completion_tokens: int,
    cached_tokens: int = 0,
) -> float:
    prices = pricing_for(model)
    cached = max(0, min(cached_tokens, prompt_tokens))
    uncached = max(0, prompt_tokens - cached)
    return (
        uncached / 1_000_000 * prices["input"]
        + cached / 1_000_000 * prices["cached"]
        + completion_tokens / 1_000_000 * prices["output"]
    )


def cached_tokens_from_usage(usage: dict[str, Any] | None) -> int:
    if not usage:
        return 0
    details = usage.get("prompt_tokens_details") or {}
    for key in ("cached_tokens", "cached_prompt_tokens", "cached_text_tokens"):
        if key in details and details[key] is not None:
            return int(details[key])
        if key in usage and usage[key] is not None:
            return int(usage[key])
    return 0


def build_chat_payload(
    *,
    model: str,
    messages: list[dict[str, str]],
    max_tokens: int,
    classify: bool,
    reasoning_effort: str | None,
) -> dict[str, Any]:
    """OpenAI-compatible body. Never attaches tools / web_search."""
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.0 if classify else 0.4,
    }
    if reasoning_effort and model.startswith("grok-4.3"):
        payload["reasoning_effort"] = reasoning_effort
    return payload


class BudgetLedger:
    """SQLite monthly spend + kill-switch."""

    def __init__(
        self,
        conn: sqlite3.Connection,
        monthly_budget_usd: float,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self.conn = conn
        self.monthly_budget_usd = float(monthly_budget_usd)
        self._now = now or (lambda: datetime.now(timezone.utc))
        self._init()

    def _init(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS grok_budget (
              year_month TEXT PRIMARY KEY,
              input_tokens INTEGER NOT NULL DEFAULT 0,
              output_tokens INTEGER NOT NULL DEFAULT 0,
              cached_tokens INTEGER NOT NULL DEFAULT 0,
              estimated_usd REAL NOT NULL DEFAULT 0,
              paused INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS grok_calls (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              ts TEXT NOT NULL,
              model TEXT NOT NULL,
              specialist TEXT,
              prompt_tokens INTEGER NOT NULL,
              completion_tokens INTEGER NOT NULL,
              cached_tokens INTEGER NOT NULL,
              cost_usd REAL NOT NULL,
              max_tokens INTEGER NOT NULL
            );
            """
        )
        self.conn.commit()

    def year_month(self, when: datetime | None = None) -> str:
        return (when or self._now()).strftime("%Y-%m")

    def snapshot(self, when: datetime | None = None) -> BudgetSnapshot:
        key = self.year_month(when)
        row = self.conn.execute(
            "SELECT * FROM grok_budget WHERE year_month = ?", (key,)
        ).fetchone()
        if row is None:
            return BudgetSnapshot(key, 0, 0, 0, 0.0, False, self.monthly_budget_usd)
        paused = bool(row["paused"]) or row["estimated_usd"] >= self.monthly_budget_usd
        return BudgetSnapshot(
            year_month=key,
            input_tokens=row["input_tokens"],
            output_tokens=row["output_tokens"],
            cached_tokens=row["cached_tokens"],
            estimated_usd=row["estimated_usd"],
            paused=paused,
            cap_usd=self.monthly_budget_usd,
        )

    def is_paused(self, when: datetime | None = None) -> bool:
        return self.snapshot(when).paused

    def record(
        self,
        *,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        cached_tokens: int,
        cost_usd: float,
        max_tokens: int,
        specialist: str | None = None,
        when: datetime | None = None,
    ) -> BudgetSnapshot:
        moment = when or self._now()
        key = self.year_month(moment)
        self.conn.execute(
            "INSERT INTO grok_budget (year_month) VALUES (?) ON CONFLICT(year_month) DO NOTHING",
            (key,),
        )
        self.conn.execute(
            """
            UPDATE grok_budget
            SET input_tokens = input_tokens + ?,
                output_tokens = output_tokens + ?,
                cached_tokens = cached_tokens + ?,
                estimated_usd = estimated_usd + ?
            WHERE year_month = ?
            """,
            (prompt_tokens, completion_tokens, cached_tokens, cost_usd, key),
        )
        self.conn.execute(
            """
            INSERT INTO grok_calls
              (ts, model, specialist, prompt_tokens, completion_tokens, cached_tokens, cost_usd, max_tokens)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                moment.isoformat(),
                model,
                specialist,
                prompt_tokens,
                completion_tokens,
                cached_tokens,
                cost_usd,
                max_tokens,
            ),
        )
        snap = self.snapshot(moment)
        if snap.estimated_usd >= self.monthly_budget_usd and not snap.paused:
            self.conn.execute(
                "UPDATE grok_budget SET paused = 1 WHERE year_month = ?", (key,)
            )
            snap = self.snapshot(moment)
        self.conn.commit()
        return snap


class GrokClient:
    def __init__(
        self,
        settings: Settings,
        ledger: BudgetLedger,
        http: httpx.AsyncClient | None = None,
    ) -> None:
        self.settings = settings
        self.ledger = ledger
        self._owns_http = http is None
        self.http = http or httpx.AsyncClient(
            base_url=settings.xai_base_url.rstrip("/"),
            headers={
                "Authorization": f"Bearer {settings.xai_api_key}",
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(60.0),
        )

    def select_model(self, *, code: bool = False) -> str:
        if code:
            return self.settings.grok_code_model or CODE_MODEL
        return self.settings.grok_default_model or DEFAULT_MODEL

    def conv_header(self, conv_id: str) -> dict[str, str]:
        return {"x-grok-conv-id": conv_id}

    async def aclose(self) -> None:
        if self._owns_http:
            await self.http.aclose()

    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        code: bool = False,
        classify: bool = False,
        conv_id: str = "helpinghand",
        specialist: str | None = None,
        max_tokens: int | None = None,
    ) -> ChatResult:
        if self.ledger.is_paused():
            raise BudgetExceededError("monthly Grok budget reached")
        model = self.select_model(code=code and not classify)
        cap = (
            self.settings.grok_classify_max_tokens
            if classify
            else (max_tokens or self.settings.grok_max_output_tokens)
        )
        payload = build_chat_payload(
            model=model,
            messages=messages,
            max_tokens=cap,
            classify=classify,
            reasoning_effort=self.settings.grok_reasoning_effort,
        )
        if "tools" in payload or "web_search" in payload:
            raise RuntimeError("xAI web_search/tools must stay disabled")
        response = await self.http.post(
            "/chat/completions",
            json=payload,
            headers=self.conv_header(conv_id),
        )
        response.raise_for_status()
        data = response.json()
        text = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            or ""
        )
        usage = data.get("usage") or {}
        prompt_tokens = int(usage.get("prompt_tokens") or 0)
        completion_tokens = int(usage.get("completion_tokens") or 0)
        cached = cached_tokens_from_usage(usage)
        cost = estimate_cost_usd(
            model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cached_tokens=cached,
        )
        snap = self.ledger.record(
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cached_tokens=cached,
            cost_usd=cost,
            max_tokens=cap,
            specialist=specialist,
        )
        log.info(
            "grok model=%s specialist=%s prompt=%s cached=%s out=%s cost=$%.6f month=$%.4f/%s paused=%s",
            model,
            specialist,
            prompt_tokens,
            cached,
            completion_tokens,
            cost,
            snap.estimated_usd,
            snap.cap_usd,
            snap.paused,
        )
        return ChatResult(
            text=text.strip(),
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cached_tokens=cached,
            cost_usd=cost,
            max_tokens=cap,
        )

    async def classify(self, text: str) -> str:
        messages = [
            {
                "role": "system",
                "content": (
                    "You route campus student questions for Helping Hand Crew. "
                    "Reply with exactly one word: captain, tutor, writer, campus, or focus."
                ),
            },
            {"role": "user", "content": text[:1500]},
        ]
        result = await self.chat(
            messages,
            classify=True,
            conv_id="helpinghand-classify",
            specialist="router",
        )
        token = (result.text.split() or ["captain"])[0].strip().lower().strip(".,!*:")
        from helpinghand import SPECIALISTS

        return token if token in SPECIALISTS else "captain"
