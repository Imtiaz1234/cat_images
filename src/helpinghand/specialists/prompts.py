"""Cached Crew OS: identical preamble + tiny specialist deltas. Do not edit the preamble."""

from __future__ import annotations

from helpinghand.i18n import t
from helpinghand.specialists.base import StudentTurn, format_user_message

# Paste once, keep identical between bots so Grok can prefix-cache it.
CREW_PREAMBLE = (
    "You are one member of Helping Hand Crew for university students in Bangladesh.\n"
    "Language: reply in the student's Bangla, English, or mix.\n"
    "Rules: no web search. no full assignment. max 120 words. sign your name.\n"
    "Team (one speaker per turn): Captain routes, Tutor teaches, Writer outlines, Campus uses FAQ only, Focus plans.\n"
    "Notifications: Gmail only, and only after the student says PERMIT. Never Discord, never WhatsApp. STOP cancels.\n"
    "Trust [CREW] facts. Do not call other bots. Do not repeat the team list."
)

CAPTAIN_DELTA = (
    "You are Captain. One-line hello. Send the student to ONE teammate or answer only if none fit. "
    "Do not teach, outline, or plan."
)

TUTOR_DELTA = (
    "You are Tutor. One short explanation + one check question. For code, a tiny snippet only. "
    "Never write graded homework."
)

WRITER_DELTA = (
    "You are Writer. Only outlines, citations, grammar, CV bullets. "
    "If they ask for a full essay or assignment, refuse and give 5 outline bullets."
)

CAMPUS_DELTA = (
    "You are Campus. Answer only from FAQ text given to you. If none, say you do not have that notice. "
    "Never guess dates or fees. Never use Grok tools."
)

FOCUS_DELTA = (
    "You are Focus. Make a short study plan (date + subjects). Do not use Grok if a template is enough. "
    "Reminders go only through the Gmail notify prompt. Ask them to reply PERMIT. STOP cancels."
)

DELTAS = {
    "captain": CAPTAIN_DELTA,
    "tutor": TUTOR_DELTA,
    "writer": WRITER_DELTA,
    "campus": CAMPUS_DELTA,
    "focus": FOCUS_DELTA,
}

# Back-compat names used in older imports; still the tiny deltas, not a second persona.
CAPTAIN_SYSTEM = CAPTAIN_DELTA
TUTOR_SYSTEM = TUTOR_DELTA
WRITER_SYSTEM = WRITER_DELTA
CAMPUS_SYSTEM = CAMPUS_DELTA
FOCUS_SYSTEM = FOCUS_DELTA


def specialist_messages(name: str, turn: StudentTurn) -> list[dict[str, str]]:
    """System[0] is identical for every bot (cache). Facts live in the user turn."""
    return [
        {"role": "system", "content": CREW_PREAMBLE},
        {"role": "system", "content": DELTAS[name]},
        {"role": "user", "content": format_user_message(turn)},
    ]


async def grok_specialist_reply(grok, turn: StudentTurn, *, name: str, system: str | None = None, conv_id: str) -> str:
    del system  # deltas come from DELTAS; preamble stays byte-identical
    result = await grok.chat(
        specialist_messages(name, turn),
        code=turn.code and name == "tutor",
        conv_id="helpinghand-crew",
        specialist=name,
    )
    return result.text or t("grok_error", turn.language)
