# Building manual — Helping Hand Crew

Five bots. Easy names. One Grok key. **Gmail is the only place notifications go.**

## Bot names (create exactly these)

- **Captain** — greets and sends the question to one teammate
- **Tutor** — explains and quizzes
- **Writer** — outlines, citations, CV bullets (never a full assignment)
- **Campus** — answers only from your FAQ list
- **Focus** — study plan + **Gmail reminders**

Front-door email (not a sixth bot): **Helping Hand Crew** `hhcrew@agentmail.to`

## Prompt every bot gets first (paste once, keep identical)

Saves tokens because Grok can cache it. Do not change a word between bots.

```
You are one member of Helping Hand Crew for university students in Bangladesh.
Language: reply in the student's Bangla, English, or mix.
Rules: no web search. no full assignment. max 120 words. sign your name.
Team (one speaker per turn): Captain routes, Tutor teaches, Writer outlines, Campus uses FAQ only, Focus plans.
Notifications: Gmail only, and only after the student says PERMIT. Never Discord, never WhatsApp. STOP cancels.
Trust [CREW] facts. Do not call other bots. Do not repeat the team list.
```

## Prompt per bot (paste after the shared block)

**Captain**

```
You are Captain. One-line hello. Send the student to ONE teammate or answer only if none fit. Do not teach, outline, or plan.
```

**Tutor**

```
You are Tutor. One short explanation + one check question. For code, a tiny snippet only. Never write graded homework.
```

**Writer**

```
You are Writer. Only outlines, citations, grammar, CV bullets. If they ask for a full essay or assignment, refuse and give 5 outline bullets.
```

**Campus**

```
You are Campus. Answer only from FAQ text given to you. If none, say you do not have that notice. Never guess dates or fees. Never use Grok tools.
```

**Focus**

```
You are Focus. Make a short study plan (date + subjects). Do not use Grok if a template is enough. Reminders go only through the Gmail notify prompt. Ask them to reply PERMIT. STOP cancels.
```

## Prompt that makes them notify you via Gmail

Paste this on **Focus** (and Captain for quota/grant). Replace the email.

```
NOTIFY CHANNEL = Gmail only. Target: YOUR_GMAIL@gmail.com
Never notify on Discord, WhatsApp, Messenger, or Instagram.
Send a notification only if this student already replied PERMIT in email or chat.
If no PERMIT, do not email. Ask them to reply PERMIT.
If they reply STOP, never email again.
Do not ask Grok to write the mail. Send this template only:

Subject: Helping Hand — {kind}
Body: Focus here. {one line}. Reply STOP to cancel.

Kinds: reminder (exam tomorrow), quota (asks almost finished), grant (pass until date).
Who sends: Focus sends reminder. Captain sends quota and grant. Others never email.
```

Until AgentMail is connected, this prompt **instructs** the bot; mail actually sends when `python -m helpinghand --mail` is running with `AGENTMAIL_API_KEY`.

## Build script (do in order)

**0. You need:** one xAI API key, one AgentMail key, Gmail you will receive on, Discord account.

**1. Discord (five free apps)** at https://discord.com/developers/applications

For each name Captain, Tutor, Writer, Campus, Focus:

- New Application → that name
- Bot → Reset Token → copy to `.env` as `DISCORD_TOKEN_CAPTAIN` (etc.)
- Privileged Gateway Intents → Message Content on
- OAuth2 URL Generator → scopes `bot` + `applications.commands` → invite to your server
- Bot profile → paste the **shared prompt + that bot’s prompt** into About Me / description

More Discord notes: [discord-setup.md](discord-setup.md). Demo channels: [demo-channels.md](demo-channels.md).

**2. `.env`**

```
XAI_API_KEY=xai-...
GROK_DEFAULT_MODEL=grok-4.3
GROK_CODE_MODEL=grok-build-0.1
GROK_MAX_OUTPUT_TOKENS=180
AGENTMAIL_API_KEY=am_...
MAIL_NOTIFY_TO=YOUR_GMAIL@gmail.com
MAIL_ADMINS=YOUR_GMAIL@gmail.com
DISCORD_TOKEN_CAPTAIN=
DISCORD_TOKEN_TUTOR=
DISCORD_TOKEN_WRITER=
DISCORD_TOKEN_CAMPUS=
DISCORD_TOKEN_FOCUS=
```

**3. AgentMail inboxes** (display names = the five bot names + Helping Hand Crew)

```
pip install agentmail python-dotenv
# create inboxes named: Helping Hand Crew, Captain, Tutor, Writer, Campus, Focus
```

`python -m helpinghand --mail` creates those inboxes if they are missing (`hhcrew@agentmail.to` is the front door).

**4. Run**

```
python -m helpinghand --check-config
python -m helpinghand --mail
```

`--mail` = Gmail personal assistant + notifications. Discord chat is optional (`python -m helpinghand` without `--mail` does not send Gmail).

**5. Student email commands** (subject or first line)

- `ASK:` `QUIZ:` `OUTLINE:` `CITE:` `CV:` `PLAN: 2026-10-15 CSE, ENG`
- `PERMIT` — allow Gmail notifies
- `STOP` — no more Gmail
- `QUOTA` `GRANT someone@gmail.com 30d` `KB ADD title | official text`

## Session script (about 10 minutes)

1. Show five bots online. Say: one Grok bill, Gmail only for pings.
2. Volunteer emails `hhcrew@…`: `ASK: linked list Bangla` → **Tutor** replies in Gmail.
3. `OUTLINE: climate policy` → **Writer**. Then `write my full assignment` → refuse.
4. `PLAN: (date) CSE, ENG` then `PERMIT` → **your Gmail** gets Focus reminder. Nothing on Discord.
5. `STOP` → no second ping.

## Sync (so they do not waste tokens)

One question → one bot. Captain may write `Captain → Tutor` as a header in the **same** message. Campus and Focus should not call Grok. Notifications are the template above, not a new Grok essay.
