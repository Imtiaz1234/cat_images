"""Gmail-only NotificationBus. Templates, never Grok, never Discord."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from helpinghand.consent import ConsentStore

NOTIFY_PROMPT = (
    "NOTIFY CHANNEL = Gmail only. Target: YOUR_GMAIL@gmail.com\n"
    "Never notify on Discord, WhatsApp, Messenger, or Instagram.\n"
    "Send a notification only if this student already replied PERMIT in email or chat.\n"
    "If no PERMIT, do not email. Ask them to reply PERMIT.\n"
    "If they reply STOP, never email again.\n"
    "Do not ask Grok to write the mail. Send this template only:\n"
    "\n"
    "Subject: Helping Hand — {kind}\n"
    "Body: Focus here. {one line}. Reply STOP to cancel.\n"
    "\n"
    "Kinds: reminder (exam tomorrow), quota (asks almost finished), grant (pass until date).\n"
    "Who sends: Focus sends reminder. Captain sends quota and grant. Others never email."
)

ALLOWED_SENDERS = {
    "reminder": "focus",
    "quota": "captain",
    "grant": "captain",
}

FORBIDDEN_CHANNELS = ("discord", "whatsapp", "messenger", "instagram")


class GmailSender(Protocol):
    async def send_gmail(self, *, sender: str, to: str, subject: str, body: str) -> None: ...


class RecordingSender:
    """Test double — records Gmail payloads, never touches Discord."""

    def __init__(self) -> None:
        self.sends: list[dict[str, str]] = []

    async def send_gmail(self, *, sender: str, to: str, subject: str, body: str) -> None:
        self.sends.append({"channel": "gmail", "sender": sender, "to": to, "subject": subject, "body": body})


@dataclass(frozen=True)
class MailTemplate:
    kind: str
    sender: str
    subject: str
    body: str
    channel: str = "gmail"


@dataclass
class NotifyResult:
    sent: bool
    reason: str
    template: MailTemplate | None = None
    to: str = ""
    extra: dict = field(default_factory=dict)


def render_notification(kind: str, line: str) -> MailTemplate:
    if kind not in ALLOWED_SENDERS:
        raise ValueError(f"unknown notify kind: {kind}")
    sender = ALLOWED_SENDERS[kind]
    subject = f"Helping Hand — {kind}"
    who = "Focus" if sender == "focus" else "Captain"
    body = f"{who} here. {line}. Reply STOP to cancel."
    return MailTemplate(kind=kind, sender=sender, subject=subject, body=body, channel="gmail")


class NotificationBus:
    """Focus → reminder; Captain → quota/grant. Gmail only after PERMIT."""

    channel = "gmail"

    def __init__(
        self,
        consent: ConsentStore,
        sender: GmailSender | None = None,
        *,
        default_to: str = "",
    ) -> None:
        self.consent = consent
        self.sender = sender
        self.default_to = default_to
        self.outbox: list[dict[str, str]] = []

    def render(self, kind: str, line: str) -> MailTemplate:
        return render_notification(kind, line)

    def _target(self, user_id: str) -> str:
        snap = self.consent.get(user_id)
        return (snap.email or self.default_to or "").strip()

    async def notify(
        self,
        *,
        user_id: str,
        kind: str,
        line: str,
        sender: str,
        to: str | None = None,
    ) -> NotifyResult:
        if kind not in ALLOWED_SENDERS:
            return NotifyResult(False, "unknown_kind")
        if sender != ALLOWED_SENDERS[kind]:
            return NotifyResult(False, "forbidden_sender")
        if sender not in {"focus", "captain"}:
            return NotifyResult(False, "others_never_email")
        snap = self.consent.get(user_id)
        if snap.stopped:
            return NotifyResult(False, "stopped")
        if not snap.permitted:
            return NotifyResult(False, "need_permit")
        target = (to or self._target(user_id)).strip()
        if not target:
            return NotifyResult(False, "no_target")
        template = render_notification(kind, line)
        blob = f"{template.subject}\n{template.body}".lower()
        if any(ch in blob for ch in FORBIDDEN_CHANNELS if ch != "gmail"):
            # template must stay Gmail-only; STOP mention is fine
            pass
        if "discord" in template.subject.lower() or "discord" in template.body.lower():
            return NotifyResult(False, "discord_forbidden", template=template)
        record = {
            "channel": "gmail",
            "sender": template.sender,
            "to": target,
            "subject": template.subject,
            "body": template.body,
            "kind": kind,
            "user_id": user_id,
        }
        self.outbox.append(record)
        if self.sender is not None:
            await self.sender.send_gmail(
                sender=template.sender,
                to=target,
                subject=template.subject,
                body=template.body,
            )
        return NotifyResult(True, "sent", template=template, to=target, extra=record)
