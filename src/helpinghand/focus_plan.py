"""Local study-plan builder — Focus uses this instead of Grok whenever possible."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

_ISO = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
_DMY = re.compile(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b")
_IN_DAYS = re.compile(r"\b(?:in|after)\s+(\d{1,3})\s+days?\b", re.I)


@dataclass(frozen=True)
class StudyPlan:
    text: str
    exam_on: date | None
    subjects: tuple[str, ...]
    reminder_at: datetime | None


def parse_exam_date(text: str, *, today: date | None = None) -> date | None:
    today = today or datetime.now(timezone.utc).date()
    iso = _ISO.search(text or "")
    if iso:
        return date(int(iso.group(1)), int(iso.group(2)), int(iso.group(3)))
    dmy = _DMY.search(text or "")
    if dmy:
        day, month, year = int(dmy.group(1)), int(dmy.group(2)), int(dmy.group(3))
        if year < 100:
            year += 2000
        try:
            return date(year, month, day)
        except ValueError:
            try:
                return date(year, day, month)
            except ValueError:
                return None
    rel = _IN_DAYS.search(text or "")
    if rel:
        return today + timedelta(days=int(rel.group(1)))
    return None


def parse_subjects(text: str) -> list[str]:
    blob = text or ""
    labelled = re.search(
        r"(?:subjects?|কোর্স|সাবজেক্ট)\s*[:=]\s*(.+)$", blob, re.I | re.M
    )
    source = labelled.group(1) if labelled else blob
    parts = re.split(r"[,/]| এবং | and ", source)
    out: list[str] = []
    for part in parts:
        token = part.strip(" .:-")
        if 1 < len(token) <= 40 and not token.lower().startswith("exam"):
            if re.search(r"[A-Za-z\u0980-\u09FF]", token):
                # Skip full-sentence leftovers
                if len(token.split()) <= 4:
                    out.append(token)
    # de-dupe
    seen: set[str] = set()
    unique: list[str] = []
    for item in out:
        key = item.lower()
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique[:8]


def build_study_plan(
    text: str,
    *,
    exam_date: date | None = None,
    subjects: list[str] | None = None,
    today: date | None = None,
    lang: str = "en",
) -> StudyPlan:
    today = today or datetime.now(timezone.utc).date()
    exam = exam_date or parse_exam_date(text, today=today)
    subs = subjects or parse_subjects(text)
    if not subs:
        subs = ["Core notes", "Past papers", "Weak topics"]

    if exam is None:
        body = _undated(subs, lang)
        return StudyPlan(body, None, tuple(subs), None)

    days = (exam - today).days
    reminder = None
    if days >= 1:
        reminder = datetime.combine(exam - timedelta(days=1), datetime.min.time()).replace(
            tzinfo=timezone.utc, hour=12
        )
    body = _dated(subs, exam, days, lang)
    return StudyPlan(body, exam, tuple(subs), reminder)


def _undated(subjects: list[str], lang: str) -> str:
    blocks = "\n".join(
        f"• **{name}** — 45 min active recall + 10 min formula/keywords"
        for name in subjects
    )
    if lang == "bn":
        return (
            "**Focus প্ল্যান** (পরীক্ষার তারিখ পাইনি — `/plan` এ তারিখ দাও, যেমন 2026-10-15)\n"
            f"{blocks}\n"
            "• পোমোডোরো: ২৫ মিনিট পড়া, ৫ মিনিট ব্রেক, ৪ রাউন্ডে লম্বা ব্রেক\n"
            "• রাতে ফোন #focus-room এর বাইরে। Grok লাগেনি — এটি লোকাল প্ল্যান।"
        )
    return (
        "**Focus plan** (no exam date spotted — add one with `/plan`, e.g. 2026-10-15)\n"
        f"{blocks}\n"
        "• Pomodoro: 25 min work / 5 min break, long break after 4 rounds\n"
        "• Phone stays outside #focus-room. No Grok used — this plan is local."
    )


def _dated(subjects: list[str], exam: date, days: int, lang: str) -> str:
    if days < 0:
        if lang == "bn":
            return f"পরীক্ষা **{exam.isoformat()}** ইতিমধ্যে চলে গেছে। নতুন তারিখ দিয়ে `/plan` চালাও।"
        return f"Exam date **{exam.isoformat()}** is in the past. Run `/plan` with a future date."
    if days == 0:
        headline_en = "Exam is **today**."
        headline_bn = "পরীক্ষা **আজ**।"
    else:
        headline_en = f"**{days} day(s)** until **{exam.isoformat()}**."
        headline_bn = f"**{exam.isoformat()}** পরীক্ষা — বাকি **{days} দিন**।"

    per = max(1, days // max(1, len(subjects)))
    lines = []
    cursor = 1
    for i, name in enumerate(subjects):
        span = per if i < len(subjects) - 1 else max(1, days - cursor + 1)
        end = min(days, cursor + span - 1)
        lines.append(f"• Days {cursor}–{end}: **{name}** (teach-back notes + 5 recall questions)")
        cursor = end + 1
        if cursor > days:
            break
    if days >= 3:
        lines.append(f"• Last 24h: light review only — formulas, mistakes list, sleep.")
    block = "\n".join(lines)
    if lang == "bn":
        return (
            f"**Focus কাউন্টডাউন** — {headline_bn}\n{block}\n"
            "• পোমোডোরো ২৫/৫। আমি আগের দিন রিমাইন্ডার দিব যদি চ্যানেলে `/plan` চালানো হয়।"
        )
    return (
        f"**Focus countdown** — {headline_en}\n{block}\n"
        "• Pomodoro 25/5. I will ping you the day before if you used `/plan` in this channel."
    )
