"""Bangla / English strings for quota, handoff, integrity, and errors."""

from __future__ import annotations

STRINGS: dict[str, dict[str, str]] = {
    "handoff_tutor": {
        "en": "Tutor has this.",
        "bn": "Tutor এটা নিচ্ছে।",
        "mix": "Tutor has this — পড়াশোনার প্রশ্ন।",
    },
    "handoff_writer": {
        "en": "Writer has this.",
        "bn": "Writer এটা নিচ্ছে।",
        "mix": "Writer has this — assignment desk.",
    },
    "handoff_campus": {
        "en": "Campus has this.",
        "bn": "Campus এটা নিচ্ছে।",
        "mix": "Campus has this — ক্যাম্পাস FAQ.",
    },
    "handoff_focus": {
        "en": "Focus has this.",
        "bn": "Focus এটা নিচ্ছে।",
        "mix": "Focus has this — study plan.",
    },
    "quota_exceeded": {
        "en": (
            "You've used all **{used}/{limit}** Crew messages for today. "
            "Free plan is {free}/day. Ask a club admin to `/grant` you **{role}** "
            "({paid}/day) after bKash/Nagad."
        ),
        "bn": (
            "আজকের Crew মেসেজ শেষ (**{used}/{limit}**)। ফ্রি প্ল্যান {free}/দিন। "
            "বিকাশ/নগদ পেমেন্টের পর অ্যাডমিনকে `/grant` দিয়ে **{role}** করতে বলো ({paid}/দিন)।"
        ),
        "mix": (
            "আজকের quota শেষ — **{used}/{limit}** messages. Free {free}/day. "
            "Admin `/grant` দিলে **{role}** পাবে ({paid}/day) after bKash/Nagad."
        ),
    },
    "budget_paused": {
        "en": (
            "Helping Hand Crew paused **AI replies** this month to stay inside the Grok budget. "
            "Campus FAQ search and Focus study plans still work. Ask an admin if this is a mistake."
        ),
        "bn": (
            "এই মাসের Grok বাজেট শেষ, তাই AI উত্তর আপাতত বন্ধ। "
            "ক্যাম্পাস FAQ আর Focus স্টাডি প্ল্যান চালু আছে। অ্যাডমিনকে জানাও যদি ভুল হয়।"
        ),
        "mix": (
            "Grok budget pause — AI replies বন্ধ this month. "
            "Campus FAQ আর Focus plans still চালু। Admin-কে বলো যদি mistake হয়।"
        ),
    },
    "integrity_refuse": {
        "en": (
            "I won't write a full assignment — that would break academic integrity. "
            "Five outline bullets instead:\n"
            "1. Title + one-sentence claim\n"
            "2. Context / why it matters\n"
            "3. Three supporting points with a source each\n"
            "4. Counter-argument and reply\n"
            "5. Close + Harvard/APA/IEEE citation list to collect\n"
            "Reply with the topic if you want these tailored. PERMIT is only for Gmail notifies, never Discord."
        ),
        "bn": (
            "পুরো অ্যাসাইনমেন্ট লিখে দিই না — এটা একাডেমিক ইমানদারির বাইরে। "
            "পাঁচটা আউটলাইন বুলেট:\n"
            "1. শিরোনাম + এক বাক্যের দাবি\n"
            "2. প্রসঙ্গ\n"
            "3. তিনটি যুক্তি + সূত্র\n"
            "4. বিপরীত যুক্তি\n"
            "5. শেষ + Harvard/APA/IEEE তালিকা\n"
            "টপিক বলো, সাজায়ে দিই।"
        ),
        "mix": (
            "Full assignment লিখে দিই না — academic integrity. Five outline bullets:\n"
            "1. Title + claim\n"
            "2. Context\n"
            "3. Three points + sources\n"
            "4. Counter-argument\n"
            "5. Close + citation list\n"
            "Topic বলো."
        ),
    },
    "greet": {
        "en": "Captain. One question — I send it to one teammate. Email PERMIT for Gmail reminders (never Discord).",
        "bn": "Captain. একটা প্রশ্ন পাঠাও — একজন teammate নিবে। Gmail reminder চালু করতে PERMIT লিখো (Discord নয়)।",
        "mix": "Captain. One question, one teammate. PERMIT = Gmail notifies only, never Discord.",
    },
    "campus_empty": {
        "en": (
            "Campus knowledge base has nothing matching that yet. "
            "An admin can `/kb add` the official notice (no web search — that's how we keep Grok cheap)."
        ),
        "bn": (
            "ক্যাম্পাস নলেজ বেসে এখনো এর মিল নেই। "
            "অ্যাডমিন `/kb add` দিয়ে অফিসিয়াল নোটিশ যোগ করতে পারে (ওয়েব সার্চ বন্ধ — Grok খরচ কম রাখতে)।"
        ),
        "mix": (
            "KB-তে match নেই। Admin `/kb add` দিয়ে official notice যোগ করুক — "
            "we don't web-search, that's how Grok stays cheap."
        ),
    },
    "grok_error": {
        "en": "Grok is unreachable right now. Try again in a minute, or ask Campus/Focus (those don't need the API).",
        "bn": "Grok এখন পাওয়া যাচ্ছে না। এক মিনিট পর চেষ্টা করো, অথবা Campus/Focus জিজ্ঞেস করো (API লাগে না)।",
        "mix": "Grok unreachable। একটু পরে try করো, বা Campus/Focus জিজ্ঞেস করো (no API)।",
    },
    "no_permission": {
        "en": "Only server admins (Manage Server) can run this command.",
        "bn": "শুধু সার্ভার অ্যাডমিন (Manage Server) এই কমান্ড চালাতে পারে।",
        "mix": "শুধু admin (Manage Server) এই command চালাতে পারে।",
    },
    "ask_permit": {
        "en": "Reply PERMIT to get this reminder on Gmail only. Never Discord. STOP cancels.",
        "bn": "Gmail reminder চালু করতে PERMIT লিখো। Discord-এ পিং যাবে না। STOP বাতিল করে।",
        "mix": "PERMIT = Gmail reminder only, never Discord. STOP cancels.",
    },
    "notify_permitted": {
        "en": "Gmail notifies on. Crew will email reminders/quota/grant only — never Discord. Reply STOP to cancel.",
        "bn": "Gmail নোটিফাই চালু। শুধু ইমেইল — Discord নয়। বন্ধ করতে STOP।",
        "mix": "Gmail notifies on. Never Discord. STOP cancels.",
    },
    "notify_stopped": {
        "en": "STOP recorded. No more Gmail notifies from Helping Hand Crew.",
        "bn": "STOP রাখা হলো। আর Gmail notify যাবে না।",
        "mix": "STOP recorded. No more Gmail notifies.",
    },
    "notify_stopped_locked": {
        "en": "STOP already recorded. Crew will not email Gmail notifies again.",
        "bn": "STOP আগেই আছে। আর Gmail যাবে না।",
        "mix": "STOP already recorded. No more Gmail.",
    },
}


def t(key: str, lang: str, **kwargs: object) -> str:
    pack = STRINGS[key]
    template = pack.get(lang) or pack["en"]
    return template.format(**kwargs) if kwargs else template
