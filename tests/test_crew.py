"""Shared brain: one specialist per message, campus/focus skip Grok, quota + budget."""

from __future__ import annotations

import pytest

from helpinghand.crew import HelpingHandCrew
from tests.helpers import FakeGrok, settings


@pytest.mark.asyncio
async def test_one_specialist_and_handoff_line(tmp_path) -> None:
    grok = FakeGrok(reply="Here is a step-by-step on Newton's laws.")
    crew = HelpingHandCrew(settings(tmp_path), grok=grok)
    reply = await crew.handle(user_id="s1", content="explain this exam physics formula")
    assert reply.specialist == "tutor"
    assert reply.handoff_line is not None
    assert "Tutor" in reply.handoff_line
    assert reply.used_grok
    assert grok.chat_calls  # exactly the specialist, not five bots
    assert all(c.get("specialist") == "tutor" for c in grok.chat_calls)
    assert grok.classify_calls == []


@pytest.mark.asyncio
async def test_campus_uses_kb_not_grok(tmp_path) -> None:
    grok = FakeGrok()
    crew = HelpingHandCrew(settings(tmp_path), grok=grok)
    crew.kb.add("Waiver deadline", "Need-based waiver applications close 15 October.")
    reply = await crew.handle(user_id="s1", content="when is the scholarship waiver deadline?")
    assert reply.specialist == "campus"
    assert reply.used_grok is False
    assert "15 October" in reply.text
    assert grok.chat_calls == []


@pytest.mark.asyncio
async def test_focus_local_plan_no_grok(tmp_path) -> None:
    grok = FakeGrok()
    crew = HelpingHandCrew(settings(tmp_path), grok=grok)
    reply = await crew.handle(
        user_id="s1",
        content="study plan",
        command="plan",
        extra={"exam_date": "2026-10-15", "subjects": "PHY101,CHEM101"},
        channel_id="99",
    )
    assert reply.specialist == "focus"
    assert reply.used_grok is False
    assert "PHY101" in reply.text
    assert grok.chat_calls == []
    assert reply.handoff_line is None  # slash command on Focus, no Captain line


@pytest.mark.asyncio
async def test_writer_integrity_counts_as_one_reply(tmp_path) -> None:
    grok = FakeGrok(reply="should not be used")
    crew = HelpingHandCrew(settings(tmp_path), grok=grok)
    reply = await crew.handle(user_id="s1", content="write my full assignment on wetlands")
    assert reply.specialist == "writer"
    assert "integrity" in reply.text.lower() or "ইমানদারি" in reply.text
    assert grok.chat_calls == []


@pytest.mark.asyncio
async def test_quota_block_before_grok(tmp_path) -> None:
    grok = FakeGrok()
    crew = HelpingHandCrew(settings(tmp_path, free_daily_quota=1), grok=grok)
    first = await crew.handle(user_id="s1", content="hello")
    assert first.specialist == "captain"
    second = await crew.handle(user_id="s1", content="explain exam calculus")
    assert "15" in second.text or "1/" in second.text or "quota" in second.text.lower() or "মেসেজ" in second.text
    assert grok.chat_calls == []


@pytest.mark.asyncio
async def test_bangla_language_on_quota(tmp_path) -> None:
    grok = FakeGrok()
    crew = HelpingHandCrew(settings(tmp_path, free_daily_quota=0), grok=grok)
    reply = await crew.handle(user_id="s1", content="আজকে পড়াশোনা")
    assert "দিন" in reply.text or "মেসেজ" in reply.text
