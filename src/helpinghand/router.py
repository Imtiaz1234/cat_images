"""Cheap intent router: slash command + keywords first; Grok classify only if needed."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Protocol

from helpinghand import CREW_CHANNELS, SPECIALISTS

COMMAND_TO_SPECIALIST: dict[str, str | None] = {
    "ask": None,  # still keyword-route the question
    "quiz": "tutor",
    "outline": "writer",
    "cite": "writer",
    "cv": "writer",
    "plan": "focus",
    "kb": "campus",
    "quota": "captain",
    "grant": "captain",
}

TUTOR_KEYWORDS = (
    "exam",
    "midterm",
    "finals",
    "quiz",
    "mcq",
    "concept",
    "explain",
    "derivation",
    "formula",
    "theorem",
    "lecture",
    "study",
    "homework",
    "tutorial",
    "physics",
    "chemistry",
    "biology",
    "calculus",
    "algebra",
    "statistics",
    "maths",
    "math",
    "পরীক্ষা",
    "মিডটার্ম",
    "ফাইনাল",
    "কুইজ",
    "ব্যাখ্যা",
    "কনসেপ্ট",
    "পড়াশোনা",
    "পড়াশোনা",
    "লেকচার",
    "গণিত",
    "পদার্থ",
    "রসায়ন",
    "রসায়ন",
)
WRITER_KEYWORDS = (
    "assignment",
    "essay",
    "report",
    "thesis",
    "outline",
    "citation",
    "cite",
    "bibliography",
    "grammar",
    "paraphrase",
    "rewrite",
    "proofread",
    "cv",
    "resume",
    "cover letter",
    "harvard",
    "apa",
    "ieee",
    "translation",
    "translate",
    "অ্যাসাইনমেন্ট",
    "এসাইনমেন্ট",
    "প্রবন্ধ",
    "রিপোর্ট",
    "আউটলাইন",
    "ব্যাকরণ",
    "অনুবাদ",
    "সিভি",
    "রেজুমে",
    "উদ্ধৃতি",
)
CAMPUS_KEYWORDS = (
    "scholarship",
    "waiver",
    "deadline",
    "registrar",
    "campus",
    "hall",
    "hostel",
    "club",
    "admission",
    "tuition",
    "notice",
    "office hour",
    "semester date",
    "বৃত্তি",
    "স্কলারশিপ",
    "ডেডলাইন",
    "ক্যাম্পাস",
    "হল",
    "ক্লাব",
    "ভর্তি",
    "টিউশন",
    "রেজিস্ট্রার",
    "নোটিশ",
)
FOCUS_KEYWORDS = (
    "study plan",
    "timetable",
    "time table",
    "schedule",
    "countdown",
    "reminder",
    "pomodoro",
    "focus",
    "revision plan",
    "routine",
    "পরিকল্পনা",
    "রুটিন",
    "রিমাইন্ডার",
    "কাউন্টডাউন",
    "স্টাডি প্ল্যান",
)
GREET_KEYWORDS = (
    "hi",
    "hello",
    "hey",
    "yo",
    "salam",
    "assalamu",
    "হ্যালো",
    "হাই",
    "সালাম",
    "সাহায্য",
    "help",
    "crew",
)

KEYWORD_MAP: dict[str, tuple[str, ...]] = {
    "tutor": TUTOR_KEYWORDS,
    "writer": WRITER_KEYWORDS,
    "campus": CAMPUS_KEYWORDS,
    "focus": FOCUS_KEYWORDS,
}


class Classifier(Protocol):
    async def classify(self, text: str) -> str: ...


@dataclass(frozen=True)
class Route:
    specialist: str
    source: str
    scores: dict[str, int] = field(default_factory=dict)


def _has_bangla(token: str) -> bool:
    return any("\u0980" <= ch <= "\u09FF" for ch in token)


def score_keywords(text: str) -> dict[str, int]:
    blob = (text or "").lower()
    scores = {name: 0 for name in KEYWORD_MAP}
    for specialist, keywords in KEYWORD_MAP.items():
        total = 0
        for kw in keywords:
            if _has_bangla(kw) or " " in kw:
                if kw.lower() in blob:
                    total += 2 if _has_bangla(kw) else 1
            else:
                if re.search(rf"\b{re.escape(kw.lower())}\b", blob):
                    total += 1
        scores[specialist] = total
    return scores


def _is_greeting(text: str) -> bool:
    blob = (text or "").strip().lower()
    if not blob or len(blob) > 48:
        return False
    cleaned = re.sub(r"[^\w\u0980-\u09FF\s]", "", blob)
    return any(
        cleaned == g or cleaned.startswith(g + " ") or cleaned.endswith(" " + g)
        for g in GREET_KEYWORDS
    )


def pick_winner(scores: dict[str, int], *, channel_hint: str | None = None) -> str | None:
    best = max(scores.values()) if scores else 0
    if best <= 0:
        return channel_hint if channel_hint in SPECIALISTS else None
    winners = [name for name, val in scores.items() if val == best]
    if len(winners) == 1:
        return winners[0]
    if channel_hint in winners:
        return channel_hint
    return None


class Router:
    """One student message → one specialist. Never a 5-bot debate."""

    async def route(
        self,
        *,
        text: str = "",
        command: str | None = None,
        channel_name: str = "",
        mentioned_specialist: str | None = None,
        classifier: Classifier | None = None,
        allow_classify: bool = True,
    ) -> Route:
        channel = (channel_name or "").lstrip("#").lower()
        hint = CREW_CHANNELS.get(channel)

        if command:
            mapped = COMMAND_TO_SPECIALIST.get(command.lower())
            if mapped:
                return Route(mapped, "command", score_keywords(text))

        if mentioned_specialist and mentioned_specialist in SPECIALISTS:
            if mentioned_specialist != "captain":
                return Route(mentioned_specialist, "mention", score_keywords(text))

        scores = score_keywords(text)
        winner = pick_winner(scores, channel_hint=None)
        if winner:
            return Route(winner, "keyword", scores)

        if hint:
            return Route(hint, "channel", scores)

        if _is_greeting(text):
            return Route("captain", "greeting", scores)

        if allow_classify and classifier is not None and (text or "").strip():
            try:
                labelled = await classifier.classify(text)
            except Exception:
                labelled = "captain"
            if labelled not in SPECIALISTS:
                labelled = "captain"
            return Route(labelled, "classify", scores)

        return Route("captain", "default", scores)
