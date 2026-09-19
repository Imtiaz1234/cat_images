"""Writer refuses full-assignment ghostwriting."""

from __future__ import annotations

import pytest

from helpinghand.integrity import is_full_assignment_request
from helpinghand.specialists.writer import Writer
from tests.helpers import FakeGrok


@pytest.mark.parametrize(
    "text",
    [
        "write my full assignment on climate policy",
        "please do my homework for CSE 210",
        "ghostwrite a 2000 word essay on wetlands",
        "পুরো অ্যাসাইনমেন্ট লিখে দাও",
    ],
)
def test_detects_full_assignment(text: str) -> None:
    assert is_full_assignment_request(text)


@pytest.mark.parametrize(
    "text",
    [
        "outline my assignment on climate policy",
        "harvard citation for this paper",
        "fix grammar in this paragraph",
        "অ্যাসাইনমেন্ট এর আউটলাইন চাই",
    ],
)
def test_allows_coaching(text: str) -> None:
    assert not is_full_assignment_request(text)


@pytest.mark.asyncio
async def test_writer_refuses_without_calling_grok() -> None:
    grok = FakeGrok()
    writer = Writer()

    class Turn:
        content = "write my full assignment tonight"
        language = "en"
        extra = {}
        code = False
        memory = ""
        kb_hits = []
        user_id = "1"
        display_name = "s"
        channel_name = "assignment-desk"
        command = None

    text = await writer.handle(Turn(), grok)
    assert "academic integrity" in text.lower()
    assert "1." in text and "5." in text
    assert grok.chat_calls == []
