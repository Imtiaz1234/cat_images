"""Shared user-turn payload for specialists."""

from __future__ import annotations

from dataclasses import dataclass, field

from helpinghand.kb import KbHit
from helpinghand.language import language_instruction


@dataclass
class StudentTurn:
    user_id: str
    content: str
    language: str
    channel_name: str = ""
    command: str | None = None
    display_name: str = "student"
    memory: str = ""
    kb_hits: list[KbHit] = field(default_factory=list)
    code: bool = False
    extra: dict[str, str] = field(default_factory=dict)


def format_user_message(turn: StudentTurn, *, kb_block: str = "") -> str:
    parts = [
        language_instruction(turn.language),
        f"Student name: {turn.display_name}",
        f"Discord channel: #{turn.channel_name or 'unknown'}",
    ]
    if turn.command:
        parts.append(f"Slash command: /{turn.command}")
    if turn.memory:
        parts.append(f"Short rolling summary (not full chat):\n{turn.memory}")
    if kb_block:
        parts.append(kb_block)
    for key, value in turn.extra.items():
        parts.append(f"{key}: {value}")
    parts.append("Student message:\n" + turn.content)
    return "\n\n".join(parts)
