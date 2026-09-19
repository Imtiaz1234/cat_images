"""AgentMail front door + five bot inboxes. One thread reply. Gmail notify via NotificationBus."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from helpinghand.mail_commands import EmailCommand, parse_email_command

log = logging.getLogger(__name__)

# Display names must match the building manual exactly.
INBOX_SPECS: tuple[tuple[str, str], ...] = (
    ("hhcrew", "Helping Hand Crew"),
    ("captain", "Captain"),
    ("tutor", "Tutor"),
    ("writer", "Writer"),
    ("campus", "Campus"),
    ("focus", "Focus"),
)

FRONT_DOOR = "Helping Hand Crew"

INBOX_TO_SPECIALIST = {
    "Helping Hand Crew": None,
    "Captain": "captain",
    "Tutor": "tutor",
    "Writer": "writer",
    "Campus": "campus",
    "Focus": "focus",
}


@dataclass
class InboundMail:
    from_email: str
    subject: str
    body: str
    inbox_id: str
    message_id: str
    inbox_display: str = FRONT_DOOR
    thread_id: str = ""


@dataclass
class OutboundMail:
    kind: str  # reply | notify
    inbox_id: str
    message_id: str | None
    to: str
    text: str
    subject: str = ""
    channel: str = "gmail"


@dataclass
class MailSession:
    replies: list[OutboundMail] = field(default_factory=list)
    notifies: list[OutboundMail] = field(default_factory=list)


def specialist_for_inbox(display_name: str) -> str | None:
    return INBOX_TO_SPECIALIST.get(display_name)


class AgentMailSender:
    """Sends notify templates from Focus (reminder) or Captain (quota/grant) inboxes."""

    def __init__(self, client: Any, inboxes: dict[str, str]) -> None:
        self.client = client
        self.inboxes = inboxes  # display name → inbox_id

    async def send_gmail(self, *, sender: str, to: str, subject: str, body: str) -> None:
        display = "Focus" if sender == "focus" else "Captain"
        inbox_id = self.inboxes.get(display) or self.inboxes.get(FRONT_DOOR)
        if not inbox_id or self.client is None:
            log.info("gmail notify skipped (no inbox): %s %s", subject, to)
            return
        await self.client.inboxes.messages.send(
            inbox_id=inbox_id,
            to=to,
            subject=subject,
            text=body,
        )


async def ensure_inboxes(client: Any) -> dict[str, str]:
    """Create Helping Hand Crew + five bot inboxes (idempotent client_id)."""
    mapping: dict[str, str] = {}
    listed = await client.inboxes.list(limit=50)
    existing = getattr(listed, "inboxes", None) or getattr(listed, "items", None) or listed
    by_display: dict[str, Any] = {}
    by_username: dict[str, Any] = {}
    for inbox in existing or []:
        display = getattr(inbox, "display_name", None) or ""
        inbox_id = getattr(inbox, "inbox_id", None) or getattr(inbox, "id", None)
        username = getattr(inbox, "username", None) or ""
        if display and inbox_id:
            by_display[display] = inbox
        if username and inbox_id:
            by_username[username] = inbox
    for username, display in INBOX_SPECS:
        hit = by_display.get(display) or by_username.get(username)
        if hit is not None:
            mapping[display] = getattr(hit, "inbox_id", None) or getattr(hit, "id")
            continue
        created = await _create_inbox(client, username, display)
        mapping[display] = getattr(created, "inbox_id", None) or getattr(created, "id")
    return mapping


async def _create_inbox(client: Any, username: str, display: str) -> Any:
    kwargs = dict(username=username, display_name=display, client_id=f"helpinghand-{username}")
    try:
        from agentmail.inboxes.types import CreateInboxRequest

        return await client.inboxes.create(request=CreateInboxRequest(**kwargs))
    except Exception:
        try:
            return await client.inboxes.create(**kwargs)
        except TypeError:
            return await client.inboxes.create()


async def reply_in_thread(client: Any, inbound: InboundMail, text: str) -> None:
    """Exactly one reply on the same thread. Never fan-out to five bots."""
    await client.inboxes.messages.reply(
        inbox_id=inbound.inbox_id,
        message_id=inbound.message_id,
        text=text,
    )


def extract_body(message: Any) -> str:
    return (
        getattr(message, "extracted_text", None)
        or getattr(message, "text", None)
        or getattr(message, "extracted_html", None)
        or getattr(message, "html", None)
        or ""
    )


def extract_from(message: Any) -> str:
    raw = getattr(message, "from_", None) or getattr(message, "from_email", None) or getattr(message, "from", None) or ""
    if hasattr(raw, "email"):
        return str(raw.email)
    text = str(raw)
    if "<" in text and ">" in text:
        return text[text.index("<") + 1 : text.index(">")].strip()
    return text.strip()


async def handle_inbound(
    crew,
    inbound: InboundMail,
    *,
    is_admin: bool | None = None,
) -> str:
    """Parse commands, run one specialist, return the single reply body."""
    parsed = parse_email_command(inbound.subject, inbound.body)
    mentioned = specialist_for_inbox(inbound.inbox_display)
    user_id = inbound.from_email.lower()
    admin = crew.settings.is_mail_admin(inbound.from_email) if is_admin is None else is_admin
    extra = dict(parsed.extra)
    extra["email"] = inbound.from_email
    reply = await crew.handle(
        user_id=user_id,
        content=parsed.text or inbound.body or inbound.subject,
        command=parsed.command,
        mentioned_specialist=mentioned if mentioned and mentioned != "captain" else None,
        display_name=inbound.from_email,
        email=inbound.from_email,
        extra=extra,
        source="mail",
        is_admin=admin,
        allow_classify=parsed.command == "ask" or parsed.command is None,
    )
    return reply.text


async def process_event(crew, client: Any, event: Any, inboxes: dict[str, str]) -> str | None:
    message = getattr(event, "message", event)
    inbox_id = getattr(message, "inbox_id", "")
    message_id = getattr(message, "message_id", None) or getattr(message, "id", None)
    if not inbox_id or not message_id:
        return None
    reverse = {v: k for k, v in inboxes.items()}
    display = reverse.get(inbox_id, FRONT_DOOR)
    body = extract_body(message)
    if not body and client is not None:
        try:
            full = await client.inboxes.messages.get(inbox_id=inbox_id, message_id=message_id)
            body = extract_body(full)
            message = full
        except Exception:
            log.exception("failed to fetch message body")
    inbound = InboundMail(
        from_email=extract_from(message),
        subject=getattr(message, "subject", "") or "",
        body=body,
        inbox_id=inbox_id,
        message_id=str(message_id),
        inbox_display=display,
        thread_id=str(getattr(message, "thread_id", "") or ""),
    )
    if not inbound.from_email:
        return None
    text = await handle_inbound(crew, inbound)
    await reply_in_thread(client, inbound, text)
    return text


async def drain_reminders(crew) -> list:
    sent = []
    for reminder in crew.reminders.due():
        result = await crew.notify.notify(
            user_id=reminder.user_id,
            kind=reminder.kind or "reminder",
            line=reminder.line,
            sender=reminder.sender or "focus",
        )
        if result.sent or result.reason == "stopped":
            crew.reminders.mark_sent(reminder.id)
        sent.append(result)
    return sent


async def run_mail(crew, settings) -> None:
    try:
        from agentmail import AsyncAgentMail, MessageReceivedEvent, Subscribe
    except ImportError as exc:
        raise SystemExit("Install agentmail: pip install agentmail") from exc

    client = AsyncAgentMail(api_key=settings.agentmail_api_key)
    inboxes = await ensure_inboxes(client)
    crew.notify.sender = AgentMailSender(client, inboxes)
    crew.notify.default_to = settings.mail_notify_to
    log.info("AgentMail inboxes: %s", inboxes)
    ids = list(inboxes.values())

    async def reminder_pump() -> None:
        import asyncio

        while True:
            try:
                await drain_reminders(crew)
            except Exception:
                log.exception("gmail reminder pump failed")
            await asyncio.sleep(45)

    import asyncio

    pump = asyncio.create_task(reminder_pump())
    try:
        async with client.websockets.connect() as socket:
            await socket.send_subscribe(Subscribe(inbox_ids=ids, event_types=["message.received"]))
            async for event in socket:
                if MessageReceivedEvent is not None and not isinstance(event, MessageReceivedEvent):
                    name = type(event).__name__
                    if "Received" not in name and not getattr(event, "message", None):
                        continue
                try:
                    await process_event(crew, client, event, inboxes)
                except Exception:
                    log.exception("mail event failed")
    finally:
        pump.cancel()
