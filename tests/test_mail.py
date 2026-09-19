"""Gmail-only notify, PERMIT/STOP, one speaker, integrity, email commands.

No live Discord, xAI, or AgentMail keys required.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from helpinghand.crew import HelpingHandCrew
from helpinghand.mail import (
    FRONT_DOOR,
    INBOX_SPECS,
    InboundMail,
    drain_reminders,
    handle_inbound,
    process_event,
    specialist_for_inbox,
)
from helpinghand.mail_commands import parse_email_command
from helpinghand.notify import ALLOWED_SENDERS, NOTIFY_PROMPT, render_notification as render_n
from helpinghand.specialists.prompts import CREW_PREAMBLE, DELTAS
from tests.helpers import FakeGrok, settings


def test_inbox_names_match_building_manual() -> None:
    names = [display for _, display in INBOX_SPECS]
    assert names == ["Helping Hand Crew", "Captain", "Tutor", "Writer", "Campus", "Focus"]
    assert FRONT_DOOR == "Helping Hand Crew"
    assert specialist_for_inbox("Tutor") == "tutor"
    assert specialist_for_inbox("Helping Hand Crew") is None


def test_shared_preamble_identical_and_deltas_tiny() -> None:
    assert "Never Discord" in CREW_PREAMBLE
    assert "Trust [CREW] facts" in CREW_PREAMBLE
    for name, delta in DELTAS.items():
        assert delta.startswith(f"You are {name.title()}.")
        assert CREW_PREAMBLE not in delta


@pytest.mark.parametrize(
    "subject,body,command",
    [
        ("ASK: linked list Bangla", "", "ask"),
        ("", "QUIZ: stacks", "quiz"),
        ("OUTLINE: climate policy", "", "outline"),
        ("CITE: harvard", "book", "cite"),
        ("CV: intern", "", "cv"),
        ("PLAN: 2026-10-15 CSE, ENG", "", "plan"),
        ("PERMIT", "", "permit"),
        ("STOP", "", "stop"),
        ("QUOTA", "", "quota"),
        ("GRANT someone@gmail.com 30d", "", "grant"),
        ("", "KB ADD hall fees | 1200 BDT per month", "kb"),
    ],
)
def test_email_commands_parse(subject: str, body: str, command: str) -> None:
    parsed = parse_email_command(subject, body)
    assert parsed.command == command
    if command == "plan":
        assert parsed.extra["exam_date"] == "2026-10-15"
        assert "CSE" in parsed.extra["subjects"]
    if command == "grant":
        assert parsed.extra["target"] == "someone@gmail.com"
        assert parsed.extra["duration"].startswith("30")
    if command == "kb":
        assert parsed.extra["title"].lower().startswith("hall")
        assert "1200" in parsed.extra["body"]


def test_notify_template_gmail_only_never_grok() -> None:
    tpl = render_n("reminder", "exam tomorrow: CSE, ENG")
    assert tpl.channel == "gmail"
    assert tpl.sender == "focus"
    assert tpl.subject == "Helping Hand — reminder"
    assert tpl.body.startswith("Focus here.")
    assert "Reply STOP to cancel" in tpl.body
    assert "discord" not in tpl.subject.lower()
    assert "discord" not in tpl.body.lower()
    assert "Do not ask Grok" in NOTIFY_PROMPT
    assert ALLOWED_SENDERS["quota"] == "captain"
    assert ALLOWED_SENDERS["grant"] == "captain"


@pytest.mark.asyncio
async def test_permit_then_gmail_reminder_not_discord(tmp_path) -> None:
    grok = FakeGrok()
    crew = HelpingHandCrew(settings(tmp_path, mail_notify_to="you@gmail.com"), grok=grok)
    user = "student@gmail.com"
    inbound_plan = InboundMail(
        from_email=user,
        subject="PLAN: 2026-10-15 CSE, ENG",
        body="",
        inbox_id="in_front",
        message_id="m1",
        inbox_display=FRONT_DOOR,
    )
    plan_text = await handle_inbound(crew, inbound_plan)
    assert "CSE" in plan_text or "Core" in plan_text or "Focus" in plan_text
    assert grok.chat_calls == []
    assert crew.notify.outbox == []

    denied = await crew.notify.notify(
        user_id=user, kind="reminder", line="exam tomorrow: CSE, ENG", sender="focus"
    )
    assert denied.sent is False
    assert denied.reason == "need_permit"

    permit_text = await handle_inbound(
        crew,
        InboundMail(user, "PERMIT", "", "in_front", "m2", FRONT_DOOR),
    )
    assert "Gmail" in permit_text
    assert "Discord" in permit_text

    sender = crew.notify.sender
    from helpinghand.notify import RecordingSender

    rec = RecordingSender()
    crew.notify.sender = rec
    ok = await crew.notify.notify(
        user_id=user, kind="reminder", line="exam tomorrow: CSE, ENG", sender="focus"
    )
    assert ok.sent
    assert ok.template.channel == "gmail"
    assert rec.sends[0]["channel"] == "gmail"
    assert rec.sends[0]["to"] == user
    assert rec.sends[0]["subject"] == "Helping Hand — reminder"
    assert all(s["channel"] == "gmail" for s in rec.sends)


@pytest.mark.asyncio
async def test_stop_never_emails_again(tmp_path) -> None:
    crew = HelpingHandCrew(settings(tmp_path, mail_notify_to="you@gmail.com"), grok=FakeGrok())
    user = "student@gmail.com"
    await handle_inbound(crew, InboundMail(user, "PERMIT", "", "in", "1", FRONT_DOOR))
    await handle_inbound(crew, InboundMail(user, "STOP", "", "in", "2", FRONT_DOOR))
    result = await crew.notify.notify(
        user_id=user, kind="reminder", line="exam tomorrow", sender="focus"
    )
    assert result.sent is False
    assert result.reason == "stopped"
    locked = await handle_inbound(crew, InboundMail(user, "PERMIT", "", "in", "3", FRONT_DOOR))
    assert "STOP" in locked
    again = await crew.notify.notify(
        user_id=user, kind="quota", line="asks almost finished", sender="captain"
    )
    assert again.sent is False


@pytest.mark.asyncio
async def test_writer_and_campus_never_email(tmp_path) -> None:
    crew = HelpingHandCrew(settings(tmp_path), grok=FakeGrok())
    crew.consent.permit("u", "u@gmail.com")
    for sender in ("writer", "tutor", "campus"):
        result = await crew.notify.notify(
            user_id="u", kind="reminder", line="hi", sender=sender
        )
        assert result.sent is False
        assert result.reason == "forbidden_sender"


@pytest.mark.asyncio
async def test_one_speaker_on_ask_email(tmp_path) -> None:
    grok = FakeGrok(reply="A linked list is nodes + pointers. Check: what is the tail?")
    crew = HelpingHandCrew(settings(tmp_path), grok=grok)
    text = await handle_inbound(
        crew,
        InboundMail(
            "stu@gmail.com",
            "ASK: linked list Bangla",
            "",
            "in_front",
            "m9",
            FRONT_DOOR,
        ),
    )
    assert text.startswith("Captain → Tutor")
    assert text.count("Captain →") == 1
    specialists = {c.get("specialist") for c in grok.chat_calls}
    assert specialists <= {"tutor", "router"}
    assert "writer" not in specialists
    assert "campus" not in specialists
    assert "focus" not in specialists


@pytest.mark.asyncio
async def test_integrity_refuse_on_write_my_full_assignment(tmp_path) -> None:
    grok = FakeGrok(reply="should not run")
    crew = HelpingHandCrew(settings(tmp_path), grok=grok)
    await handle_inbound(
        crew,
        InboundMail("stu@gmail.com", "OUTLINE: climate policy", "", "in", "1", FRONT_DOOR),
    )
    grok.chat_calls.clear()
    text = await handle_inbound(
        crew,
        InboundMail("stu@gmail.com", "write my full assignment", "", "in", "2", FRONT_DOOR),
    )
    assert "integrity" in text.lower()
    assert "1." in text and "5." in text
    assert grok.chat_calls == []
    assert "Captain → Writer" in text


@pytest.mark.asyncio
async def test_campus_and_focus_skip_grok(tmp_path) -> None:
    grok = FakeGrok()
    crew = HelpingHandCrew(settings(tmp_path), grok=grok)
    crew.kb.add("Waiver deadline", "Need-based waiver applications close 15 October.")
    campus = await handle_inbound(
        crew,
        InboundMail("stu@gmail.com", "when is the scholarship waiver deadline?", "", "in", "1", "Campus"),
    )
    assert "15 October" in campus
    focus = await handle_inbound(
        crew,
        InboundMail("stu@gmail.com", "PLAN: 2026-10-15 CSE, ENG", "", "in", "2", "Focus"),
    )
    assert "CSE" in focus or "2026-10-15" in focus
    assert grok.chat_calls == []


@pytest.mark.asyncio
async def test_one_thread_reply_not_five(tmp_path) -> None:
    class Messages:
        def __init__(self) -> None:
            self.replies: list[dict] = []
            self.sends: list[dict] = []

        async def reply(self, **kwargs) -> None:
            self.replies.append(kwargs)

        async def send(self, **kwargs) -> None:
            self.sends.append(kwargs)

        async def get(self, **kwargs):
            return SimpleNamespace(
                extracted_text="ASK: linked list Bangla",
                text="ASK: linked list Bangla",
                subject="ASK: linked list Bangla",
                from_="stu@gmail.com",
                inbox_id=kwargs["inbox_id"],
                message_id=kwargs["message_id"],
            )

    class Client:
        def __init__(self) -> None:
            self.inboxes = SimpleNamespace(messages=Messages())

    grok = FakeGrok(reply="nodes and next pointers")
    crew = HelpingHandCrew(settings(tmp_path), grok=grok)
    client = Client()
    event = SimpleNamespace(
        message=SimpleNamespace(
            inbox_id="in_hhcrew",
            message_id="msg_1",
            subject="ASK: linked list Bangla",
            extracted_text="ASK: linked list Bangla",
            text="ASK: linked list Bangla",
            from_="stu@gmail.com",
            thread_id="th_1",
        )
    )
    inboxes = {FRONT_DOOR: "in_hhcrew", "Tutor": "in_tutor"}
    await process_event(crew, client, event, inboxes)
    assert len(client.inboxes.messages.replies) == 1
    assert client.inboxes.messages.replies[0]["message_id"] == "msg_1"
    assert client.inboxes.messages.replies[0]["inbox_id"] == "in_hhcrew"


@pytest.mark.asyncio
async def test_reminder_pump_gmail_after_permit(tmp_path) -> None:
    crew = HelpingHandCrew(settings(tmp_path, mail_notify_to="you@gmail.com"), grok=FakeGrok())
    user = "stu@gmail.com"
    past = datetime.now(timezone.utc) - timedelta(minutes=1)
    crew.reminders.add(user_id=user, fire_at=past, line="exam tomorrow: CSE, ENG", kind="reminder", sender="focus")
    skipped = await drain_reminders(crew)
    assert skipped[0].reason == "need_permit"
    assert crew.reminders.due()  # still pending until PERMIT
    crew.consent.permit(user, user)
    rec_results = await drain_reminders(crew)
    assert rec_results[0].sent
    assert rec_results[0].template.channel == "gmail"
    assert crew.reminders.due() == []


@pytest.mark.asyncio
async def test_facts_packet_in_user_turn(tmp_path) -> None:
    grok = FakeGrok(reply="ok")
    crew = HelpingHandCrew(settings(tmp_path), grok=grok)
    await crew.handle(user_id="s1", content="explain this exam physics formula")
    user_msg = grok.chat_calls[0]["messages"][-1]["content"]
    assert user_msg.startswith("[CREW]")
    assert "notify: gmail" in user_msg
    assert grok.chat_calls[0]["messages"][0]["content"] == CREW_PREAMBLE
    assert grok.chat_calls[0]["messages"][1]["content"] == DELTAS["tutor"]
