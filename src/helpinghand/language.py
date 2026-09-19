"""Detect Bangla / English / mix from the student message. No translation API."""

from __future__ import annotations

import re

_BANGLA_RE = re.compile(r"[\u0980-\u09FF]")
_LATIN_RE = re.compile(r"[A-Za-z]")


def detect_language(text: str) -> str:
    """Return 'bn', 'en', or 'mix'."""
    has_bn = bool(_BANGLA_RE.search(text or ""))
    has_en = bool(_LATIN_RE.search(text or ""))
    if has_bn and has_en:
        return "mix"
    if has_bn:
        return "bn"
    return "en"


def language_instruction(lang: str) -> str:
    if lang == "bn":
        return (
            "Reply in Bangla (বাংলা). Keep Discord formatting. "
            "Do not switch into English except for course codes, formulas, or citations."
        )
    if lang == "mix":
        return (
            "The student is writing Banglish (Bangla + English). "
            "Reply in the same mix: natural campus Banglish, not formal translation."
        )
    return "Reply in English. Keep Discord formatting."
