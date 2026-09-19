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
            "I **will** help with an outline, citation format, a checklist, and Socratic hints "
            "so you can write it yourself. Tell me the topic and citation style (Harvard / APA / IEEE)."
        ),
        "bn": (
            "পুরো অ্যাসাইনমেন্ট লিখে দিই না — এটা একাডেমিক ইমানদারির বাইরে। "
            "আউটলাইন, রেফারেন্স ফরম্যাট, চেকলিস্ট আর ইঙ্গিত দিতে পারি যাতে তুমি নিজে লেখো। "
            "টপিক আর সাইটেশন স্টাইল বলো (Harvard / APA / IEEE)।"
        ),
        "mix": (
            "Full assignment লিখে দিই না — academic integrity. "
            "Outline, citation format, checklist আর Socratic hints দিব, তুমি লিখবে। "
            "Topic আর style বলো (Harvard / APA / IEEE)."
        ),
    },
    "greet": {
        "en": (
            "I'm **Captain** of Helping Hand Crew — Tutor, Writer, Campus, and Focus. "
            "Ask a study question, an assignment outline, a campus FAQ, or a study plan. "
            "Bangla, Banglish, or English is fine. Use `/quota` to see today's remaining messages."
        ),
        "bn": (
            "আমি **Captain**, Helping Hand Crew — সাথে Tutor, Writer, Campus আর Focus। "
            "পড়াশোনার প্রশ্ন, অ্যাসাইনমেন্ট আউটলাইন, ক্যাম্পাস FAQ, বা স্টাডি প্ল্যান জিজ্ঞেস করো। "
            "বাংলা, ইংরেজি, বাংলা-ইংলিশ সব চলে। আজকের বাকি মেসেজ `/quota`।"
        ),
        "mix": (
            "I'm **Captain** of Helping Hand Crew — Tutor, Writer, Campus, Focus। "
            "Study question, assignment outline, campus FAQ, বা study plan জিজ্ঞেস করো। "
            "`/quota` দিলে remaining messages দেখবে।"
        ),
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
}


def t(key: str, lang: str, **kwargs: object) -> str:
    pack = STRINGS[key]
    template = pack.get(lang) or pack["en"]
    return template.format(**kwargs) if kwargs else template
