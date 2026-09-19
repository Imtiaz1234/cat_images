"""In-process shared brain: one speaker per turn, Gmail-only notify, per-user lock."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

import httpx

from helpinghand import SPECIALISTS
from helpinghand.config import Settings
from helpinghand.consent import ConsentStore
from helpinghand.db import connect
from helpinghand.grok import BudgetExceededError, BudgetLedger, GrokClient, looks_like_code
from helpinghand.i18n import t
from helpinghand.integrity import is_full_assignment_request
from helpinghand.kb import KnowledgeBase
from helpinghand.language import detect_language
from helpinghand.mail_commands import parse_email_command
from helpinghand.memory import MemoryStore
from helpinghand.notify import NotificationBus
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
    speakers: tuple[str, ...] = ()


def one_speaker_text(specialist: str, body: str, command: str | None) -> str:
    """Captain may add a header in the SAME message. Never a second bot."""
    if specialist != "captain" and command in {None, "ask"}:
        return f"Captain → {specialist.title()}\n\n{body}"
    return body


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
        self.consent = ConsentStore(self.conn)
        self.ledger = BudgetLedger(self.conn, settings.grok_monthly_budget_usd)
        self.grok = grok or GrokClient(settings, self.ledger)
        self.notify = NotificationBus(self.consent, default_to=settings.mail_notify_to)
        self.router = Router()
        self.specialists = {
            "captain": Captain(),
            "tutor": Tutor(),
            "writer": Writer(),
            "campus": Campus(self.kb),
            "focus": Focus(self.reminders),
        }
        self._bots: dict = {}
        self._user_locks: dict[str, asyncio.Lock] = {}
        self._lock_meta = asyncio.Lock()
        if settings.seed_sample_faqs:
            self.kb.seed_sample_faqs()

    @property
    def bots(self) -> dict:
        return self._bots

    def attach_bots(self, bots: dict) -> None:
        self._bots = bots

    async def _user_lock(self, user_id: str) -> asyncio.Lock:
        async with self._lock_meta:
            lock = self._user_locks.get(user_id)
            if lock is None:
                lock = asyncio.Lock()
                self._user_locks[user_id] = lock
            return lock

    def needs_grok(self, specialist: str, *, content: str, command: str | None) -> bool:
        if specialist in {"campus", "focus"}:
            return False
        if command in {"permit", "stop", "quota", "grant", "kb"}:
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
                "permit",
                "stop",
                "quota",
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
        email: str = "",
        source: str = "discord",
        is_admin: bool = False,
    ) -> CrewReply:
        lock = await self._user_lock(user_id)
        async with lock:
            return await self._handle_locked(
                user_id=user_id,
                content=content,
                channel_name=channel_name,
                command=command,
                mentioned_specialist=mentioned_specialist,
                has_paid_role=has_paid_role,
                display_name=display_name,
                channel_id=channel_id,
                extra=extra,
                allow_classify=allow_classify,
                email=email,
                source=source,
                is_admin=is_admin,
            )

    async def _handle_locked(
        self,
        *,
        user_id: str,
        content: str,
        channel_name: str,
        command: str | None,
        mentioned_specialist: str | None,
        has_paid_role: bool,
        display_name: str,
        channel_id: str | None,
        extra: dict[str, str] | None,
        allow_classify: bool,
        email: str,
        source: str,
        is_admin: bool,
    ) -> CrewReply:
        extras = dict(extra or {})
        parsed = parse_email_command("", content)
        if command is None and parsed.command in {"permit", "stop", "quota", "grant", "kb"}:
            command = parsed.command
            extras.update(parsed.extra)
            content = parsed.text or content
        lang = detect_language(content or "")
        notify_email = extras.get("email") or email or self.settings.mail_notify_to

        if command == "permit":
            snap = self.consent.permit(user_id, (extras.get("email") or notify_email or user_id).lower())
            if snap.stopped:
                text = t("notify_stopped_locked", lang)
            else:
                text = t("notify_permitted", lang)
            quota = self.quota.status(user_id, has_paid_role=has_paid_role)
            return CrewReply("captain", text, None, False, quota, Route("captain", "permit"), ("captain",))

        if command == "stop":
            self.consent.stop(user_id)
            quota = self.quota.status(user_id, has_paid_role=has_paid_role)
            return CrewReply(
                "captain", t("notify_stopped", lang), None, False, quota, Route("captain", "stop"), ("captain",)
            )

        if command == "quota":
            quota = self.quota.status(user_id, has_paid_role=has_paid_role)
            text = (
                f"**{quota.role}** — {quota.used}/{quota.limit} today ({quota.remaining} left). "
                "Gmail notifies only after PERMIT. Never Discord."
            )
            return CrewReply("captain", text, None, False, quota, Route("captain", "command"), ("captain",))

        if command == "grant":
            quota = self.quota.status(user_id, has_paid_role=has_paid_role)
            if not is_admin:
                return CrewReply(
                    "captain", t("no_permission", lang), None, False, quota, Route("captain", "grant"), ("captain",)
                )
            target = extras.get("target") or extras.get("user") or ""
            duration = extras.get("duration") or "30d"
            until = self.quota.grant(target, duration, note=f"by:{user_id}")
            nudge = await self.notify.notify(
                user_id=target,
                kind="grant",
                line=f"pass until {until.isoformat()}",
                sender="captain",
                to=target if "@" in target else None,
            )
            text = f"Captain granted {target} until {until.isoformat()}."
            if not nudge.sent:
                text += " Gmail notify skipped (need PERMIT)."
            return CrewReply("captain", text, None, False, quota, Route("captain", "grant"), ("captain",))

        if command == "kb":
            quota = self.quota.status(user_id, has_paid_role=has_paid_role)
            if not is_admin:
                return CrewReply(
                    "captain", t("no_permission", lang), None, False, quota, Route("captain", "kb"), ("captain",)
                )
            title, body = extras.get("title", ""), extras.get("body", "")
            if not title or not body:
                return CrewReply(
                    "campus",
                    "Usage: KB ADD title | official text",
                    None,
                    False,
                    quota,
                    Route("campus", "kb"),
                    ("campus",),
                )
            doc_id = self.kb.add(title, body, added_by=user_id)
            return CrewReply(
                "campus",
                f"Campus FAQ #{doc_id} saved: {title}",
                None,
                False,
                quota,
                Route("campus", "kb"),
                ("campus",),
            )

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
            return CrewReply("captain", text, None, False, quota, Route("captain", "quota"), ("captain",))

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
                ("captain",),
            )

        hits = self.kb.search(content) if specialist == "campus" else []
        if channel_id:
            extras.setdefault("channel_id", channel_id)
        snap = self.consent.get(user_id)
        quota_now = self.quota.status(user_id, has_paid_role=has_paid_role)
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
            email=notify_email,
            permit=snap.permitted,
            stopped=snap.stopped,
            quota_used=quota_now.used,
            quota_limit=quota_now.limit,
            quota_remaining=quota_now.remaining,
        )
        handler = self.specialists[specialist]
        used_grok = False
        try:
            text = await handler.handle(turn, self.grok)
            used_grok = uses_grok
        except BudgetExceededError:
            quota = self.quota.status(user_id, has_paid_role=has_paid_role)
            return CrewReply(
                "captain", t("budget_paused", lang), None, False, quota, Route("captain", "budget"), ("captain",)
            )
        except httpx.HTTPError:
            quota = self.quota.status(user_id, has_paid_role=has_paid_role)
            return CrewReply(specialist, t("grok_error", lang), None, False, quota, route, (specialist,))

        quota = self.quota.consume(user_id, has_paid_role=has_paid_role)
        self.memory.remember(user_id, content, specialist, text)
        text = one_speaker_text(specialist, text, command)

        if specialist == "focus" and not snap.permitted and not snap.stopped:
            text += "\n\n" + t("ask_permit", lang)
        if quota.remaining <= 2 and quota.remaining >= 0:
            day = quota.day
            if snap.last_quota_nudge_day != day:
                nudge = await self.notify.notify(
                    user_id=user_id,
                    kind="quota",
                    line=f"asks almost finished ({quota.remaining} left today)",
                    sender="captain",
                )
                if nudge.sent:
                    self.consent.mark_quota_nudge(user_id, day)

        return CrewReply(specialist, text, None, used_grok, quota, route, (specialist,))

    async def aclose(self) -> None:
        await self.grok.aclose()
        self.conn.close()
