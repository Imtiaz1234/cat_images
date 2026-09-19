"""Student email commands: ASK/QUIZ/OUTLINE/CITE/CV/PLAN/QUOTA/GRANT/KB/PERMIT/STOP."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

COMMAND_ALIASES = {
    "ask": "ask",
    "quiz": "quiz",
    "outline": "outline",
    "cite": "cite",
    "cv": "cv",
    "plan": "plan",
    "quota": "quota",
    "grant": "grant",
    "kb": "kb",
    "permit": "permit",
    "stop": "stop",
}

_PREFIX = re.compile(
    r"^\s*(ASK|QUIZ|OUTLINE|CITE|CV|PLAN|QUOTA|GRANT|PERMIT|STOP|KB)\b(?:\s*[:\-]\s*|\s+|$)(.*)$",
    re.I | re.S,
)
_GRANT = re.compile(r"GRANT\s+(\S+@\S+)\s+(\d+\s*d(?:ays?)?)", re.I)
_KB_ADD = re.compile(r"KB\s+ADD\s+([^|]+)\|\s*(.+)", re.I | re.S)
_PLAN = re.compile(
    r"PLAN(?:\s*:)?\s*(\d{4}-\d{2}-\d{2})\s*[, ]\s*(.+)$",
    re.I | re.S,
)
_EMAIL = re.compile(r"[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}", re.I)


@dataclass(frozen=True)
class EmailCommand:
    command: str | None
    text: str
    extra: dict[str, str] = field(default_factory=dict)
    source: str = "body"


def _first_lines(subject: str, body: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    if (subject or "").strip():
        out.append (("subject", subject.strip()))
    for line in (body or "").splitlines():
        if line.strip():
            out.append(("body", line.strip()))
            break
    if (body or "").strip() and not any(src == "body" for src, _ in out):
        out.append(("body", body.strip()))
    # whole body for KB ADD which spans lines
    if body and "|" in body:
        out.append(("body", body.strip()))
    return out


def parse_email_command(subject: str = "", body: str = "") -> EmailCommand:
    blobs = _first_lines(subject, body)
    # Prefer a command match in subject, then first body line, then full body.
    candidates: list[tuple[str, str]] = blobs
    if body:
        candidates.append(("body", (body or "").strip()))
    seen: set[str] = set()
    for source, raw in candidates:
        key = raw[:200]
        if key in seen:
            continue
        seen.add(key)
        parsed = _parse_one(raw)
        if parsed.command:
            return EmailCommand(parsed.command, parsed.text, parsed.extra, source)
    text = (body or subject or "").strip()
    return EmailCommand(None, text, {}, "body")


def _parse_one(raw: str) -> EmailCommand:
    blob = (raw or "").strip()
    if not blob:
        return EmailCommand(None, "")
    compact = blob.splitlines()[0].strip()
    upper = compact.upper()
    if upper in {"PERMIT", "STOP", "QUOTA"}:
        extra = {}
        if upper == "PERMIT":
            found = _EMAIL.search(blob)
            if found:
                extra["email"] = found.group(0).lower()
        return EmailCommand(upper.lower(), blob, extra)

    kb = _KB_ADD.search(blob)
    if kb:
        return EmailCommand(
            "kb",
            blob,
            {"title": kb.group(1).strip(), "body": kb.group(2).strip()},
        )

    grant = _GRANT.search(blob)
    if grant:
        return EmailCommand(
            "grant",
            blob,
            {"target": grant.group(1).lower(), "duration": grant.group(2).replace(" ", "")},
        )

    plan = _PLAN.search(blob)
    if plan:
        subjects = re.sub(r"[\n,]+", ",", plan.group(2)).strip(" ,")
        return EmailCommand(
            "plan",
            blob,
            {"exam_date": plan.group(1), "subjects": subjects},
        )

    match = _PREFIX.match(blob)
    if not match:
        return EmailCommand(None, blob)
    verb = match.group(1).lower()
    rest = (match.group(2) or "").strip()
    if verb == "kb":
        return EmailCommand("kb", rest or blob)
    if verb in COMMAND_ALIASES:
        extra: dict[str, str] = {}
        if verb == "permit":
            found = _EMAIL.search(blob)
            if found:
                extra["email"] = found.group(0).lower()
        if verb == "plan" and rest:
            date_m = re.search(r"(\d{4}-\d{2}-\d{2})", rest)
            if date_m:
                extra["exam_date"] = date_m.group(1)
                extra["subjects"] = rest[date_m.end() :].strip(" ,:")
        return EmailCommand(COMMAND_ALIASES[verb], rest or blob, extra)
    return EmailCommand(None, blob)
