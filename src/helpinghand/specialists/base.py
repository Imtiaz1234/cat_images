"""Shared user-turn payload + [CREW] facts packet (never put facts in the system prompt)."""

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
    email: str = ""
    permit: bool = False
    stopped: bool = False
    quota_used: int = 0
    quota_limit: int = 15
    quota_remaining: int = 15


def facts_packet(turn: StudentTurn) -> str:
    lines = [
        "[CREW]",
        f"lang: {turn.language}",
        f"quota: {turn.quota_used}/{turn.quota_limit} used, {turn.quota_remaining} left",
        f"permit: {'yes' if turn.permit else 'no'}",
        f"stop: {'yes' if turn.stopped else 'no'}",
        "notify: gmail",
        "never: discord, whatsapp",
    ]
    if turn.command:
        lines.append(f"command: {turn.command}")
    if turn.kb_hits:
        lines.append("faq:")
        for hit in turn.kb_hits[:4]:
            body = hit.body if len(hit.body) < 400 else hit.body[:380] + "…"
            lines.append(f"- {hit.title}: {body}")
    if turn.memory:
        lines.append(f"memory: {turn.memory}")
    return "\n".join(lines)


def format_user_message(turn: StudentTurn, *, kb_block: str = "") -> str:
    parts = [
        facts_packet(turn),
        language_instruction(turn.language),
        f"Student name: {turn.display_name}",
    ]
    if kb_block:
        parts.append(kb_block)
    for key, value in turn.extra.items():
        if key in {"channel_id"}:
            continue
        parts.append(f"{key}: {value}")
    parts.append("Student message:\n" + turn.content)
    return "\n\n".join(parts)
