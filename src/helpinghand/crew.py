"""In-process shared brain: one specialist reply per student message."""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from helpinghand import SPECIALISTS
from helpinghand.config import Settings
from helpinghand.db import connect
from helpinghand.grok import BudgetExceededError, BudgetLedger, GrokClient, looks_like_code
from helpinghand.i18n import t
from helpinghand.integrity import is_full_assignment_request
from helpinghand.kb import KnowledgeBase
from helpinghand.language import detect_language
from helpinghand.memory import MemoryStore
from helpinghand.quota import QuotaExceededError, QuotaManager
from helpinghand.reminders import ReminderStore
from helpinghand.router import Route, Router
from helpinghand.specialists import Campus, Captain, Focus, Tutor, Writer
from helpinghand.specialists.base import StudentTurn


@dataclass(frozen=True)
class CrewReply:
    specialist: str
    text: str
    handoff_line: str | None
    used_grok: bool
    quota: object
    route: Route


class HelpingHandCrew:
    def __init__(self, settings: Settings, grok: GrokClient | None = None) -> None:
        self.settings = settings
        self.conn = connect(settings.sqlite_path)
        self.quota = QuotaManager(
            self.conn,
            free_daily=settings.free_daily_quota,
            paid_daily=settings.paid_daily_quota,
            paid_role_name=settings.paid_role_name,
        )
        self.kb = KnowledgeBase(self.conn)
        self.memory = MemoryStore(self.conn)
        self.reminders = ReminderStore(self.conn)
        self.ledger = BudgetLedger(self.conn, settings.grok_monthly_budget_usd)
        self.grok = grok or GrokClient(settings, self.ledger)
        self.router = Router()
        self.specialists = {
            "captain": Captain(),
            "tutor": Tutor(),
            "writer": Writer(),
            "campus": Campus(self.kb),
            "focus": Focus(self.reminders),
        }
        self._bots: dict = {}
        if settings.seed_sample_faqs:
            self.kb.seed_sample_faqs()

    @property
    def bots(self) -> dict:
        return self._bots

    def attach_bots(self, bots: dict) -> None:
        self._bots = bots

    def needs_grok(self, specialist: str, *, content: str, command: str | None) -> bool:
        if specialist in {"campus", "focus"}:
            return False
        if specialist == "writer" and is_full_assignment_request(content):
            return False
        if specialist == "captain":
            compact = (content or "").lower().strip(" !.?,")
            if not compact or compact in {
                "hi",
                "hello",
                "hey",
                "yo",
                "salam",
                "help",
                "হ্যালো",
                "হাই",
                "সালাম",
                "সাহায্য",
            }:
                return False
        return True

    async def handle(
        self,
        *,
        user_id: str,
        content: str,
        channel_name: str = "",
        command: str | None = None,
        mentioned_specialist: str | None = None,
        has_paid_role: bool = False,
        display_name: str = "student",
        channel_id: str | None = None,
        extra: dict[str, str] | None = None,
        allow_classify: bool = True,
    ) -> CrewReply:
        lang = detect_language(content or "")
        try:
            self.quota.check(user_id, has_paid_role=has_paid_role)
        except QuotaExceededError as exc:
            quota = self.quota.status(user_id, has_paid_role=has_paid_role)
            text = t(
                "quota_exceeded",
                lang,
                used=exc.used,
                limit=exc.limit,
                free=self.settings.free_daily_quota,
                paid=self.settings.paid_daily_quota,
                role=self.settings.paid_role_name,
            )
            return CrewReply("captain", text, None, False, quota, Route("captain", "quota"))

        paused = self.ledger.is_paused()
        classifier = None if paused else self.grok
        route = await self.router.route(
            text=content,
            command=command,
            channel_name=channel_name,
            mentioned_specialist=mentioned_specialist,
            classifier=classifier,
            allow_classify=allow_classify and not paused,
        )
        specialist = route.specialist if route.specialist in SPECIALISTS else "captain"
        uses_grok = self.needs_grok(specialist, content=content, command=command)
        if paused and uses_grok:
            quota = self.quota.status(user_id, has_paid_role=has_paid_role)
            return CrewReply(
                "captain",
                t("budget_paused", lang),
                None,
                False,
                quota,
                Route("captain", "budget"),
            )

        hits = self.kb.search(content) if specialist == "campus" else []
        extras = dict(extra or {})
        if channel_id:
            extras.setdefault("channel_id", channel_id)
        turn = StudentTurn(
            user_id=user_id,
            content=content,
            language=lang,
            channel_name=channel_name,
            command=command,
            display_name=display_name,
            memory=self.memory.get(user_id),
            kb_hits=hits,
            code=looks_like_code(content),
            extra=extras,
        )
        handler = self.specialists[specialist]
        used_grok = False
        try:
            text = await handler.handle(turn, self.grok)
            used_grok = uses_grok
        except BudgetExceededError:
            quota = self.quota.status(user_id, has_paid_role=has_paid_role)
            return CrewReply("captain", t("budget_paused", lang), None, False, quota, Route("captain", "budget"))
        except httpx.HTTPError:
            quota = self.quota.status(user_id, has_paid_role=has_paid_role)
            return CrewReply(specialist, t("grok_error", lang), None, False, quota, route)

        quota = self.quota.consume(user_id, has_paid_role=has_paid_role)
        self.memory.remember(user_id, content, specialist, text)
        handoff = None
        # Captain may add a one-line pointer on chat or /ask. Never a second Grok reply.
        if specialist != "captain" and command in {None, "ask"}:
            handoff = t(f"handoff_{specialist}", lang)
        return CrewReply(specialist, text, handoff, used_grok, quota, route)

    async def aclose(self) -> None:
        await self.grok.aclose()
        self.conn.close()
