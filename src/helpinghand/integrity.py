"""Assignment-integrity gate for Writer (required to sell to universities)."""

from __future__ import annotations

import re

# Full-assignment / ghostwriting asks. Outlines, citations, grammar, and hints stay allowed.
_PATTERNS = [
    re.compile(
        r"\b(write|draft|compose|ghostwrite|generate)\b.{0,40}\b("
        r"full |entire |whole |complete )?(assignment|essay|paper|thesis|report|coursework)\b",
        re.I,
    ),
    re.compile(r"\bdo my (homework|assignment|essay|coursework)\b", re.I),
    re.compile(r"\b(complete|finish|submit).{0,20}\b(assignment|essay|paper|thesis|report)\b", re.I),
    re.compile(r"\b(2000|1500|1000|3000)\s*(word|words)\b.{0,30}\b(essay|assignment|paper|report)\b", re.I),
    re.compile(r"\b(essay|assignment|paper|report)\b.{0,30}\b(2000|1500|1000|3000)\s*(word|words)\b", re.I),
    re.compile(r"\bwrite it for me\b", re.I),
    re.compile(r"\bghost ?write\b", re.I),
    re.compile(r"পুরো.{0,24}(অ্যাসাইনমেন্ট|এসাইনমেন্ট|এসাইনমেন্ট|প্রবন্ধ|রিপোর্ট|থিসিস)", re.I),
    re.compile(r"(অ্যাসাইনমেন্ট|এসাইনমেন্ট|প্রবন্ধ|রিপোর্ট|থিসিস).{0,24}(লিখে দাও|লিখে দে|লিখে দিন|লিখে দাওন)", re.I),
    re.compile(r"(অ্যাসাইনমেন্ট|এসাইনমেন্ট).{0,16}(পুরোটা|পুরোটা|সম্পূর্ণ).{0,12}(লিখ|বানিয়ে|বানা)", re.I),
    re.compile(r"আমার হয়ে.{0,16}(লিখে|assignment|essay)", re.I),
]


def is_full_assignment_request(text: str) -> bool:
    blob = (text or "").strip()
    if not blob:
        return False
    return any(p.search(blob) for p in _PATTERNS)
