# Helping Hand Crew

Five named Discord bots that look like a real campus helping-hand team — **Captain, Tutor, Writer, Campus, Focus** — sharing **one** xAI Grok API key.

Students join a class or club server and ask in Bangla, Banglish, or English. Each question goes to **one** specialist (never a five-bot debate), so you do not pay Grok five times per message.

This is the product you sell to Bangladesh / South Asia university clubs: exam explainers, assignment *coaching* (not ghostwriting), campus/scholarship FAQs, CV bullets, and study-plan reminders.

## Invite the team

1. Create **five free Discord apps** (see [docs/discord-setup.md](docs/discord-setup.md) and the building manual [docs/BUILD.md](docs/BUILD.md)).
2. Invite all five bots to the club server.
3. Create the demo channels in [docs/demo-channels.md](docs/demo-channels.md): `#study-lab` `#assignment-desk` `#campus-desk` `#focus-room`.
4. Create a Discord role named **Crew Member**.
5. Copy `.env.example` → `.env`, paste **one** `XAI_API_KEY` and the five bot tokens.
6. Run the single always-on process (Discord bots cannot sleep):

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m helpinghand --check-config
python -m helpinghand --mail
# Discord-only (does not send Gmail):
python -m helpinghand
```

Club pitch: *invite the Crew into your helping-hand server; members get the team, you pay one bill.*

## Who speaks

| Bot | Job | When it speaks |
|---|---|---|
| **Captain** | Greets, detects language, routes, enforces quota | Mentions, unknown intent, `/ask`, `/quota`, `/grant` |
| **Tutor** | Concepts, step-by-step, quizzes | Study / exam questions, `/quiz` |
| **Writer** | Outlines, citations, grammar, Bangla↔English, `/cv` | Assignments / reports — **not** full drafts |
| **Campus** | Deadlines, scholarships, club/uni FAQs from **your** knowledge base | Campus life, `/kb add` (admin) |
| **Focus** | Study plans, exam countdowns, **Gmail** reminders after `PERMIT` | Planning — no Grok when a template is enough, `/plan` |

Handoff rule: one student message → **one speaker**. Captain may write `Captain → Tutor` as a header in the **same** message. Notifications are Gmail-only after `PERMIT`. Never Discord pings. `STOP` cancels.

## Pricing (BDT)

Grok unit cost with prompt cache is roughly **$0.001–$0.002 per answer**. 100 students × 50 AI messages/month ≈ **$5–10 Grok** + a small always-on VPS (~$5).

| Offer | Price | What they get |
|---|---|---|
| Student pass | **199–299 BDT / student / month** | 80 messages/day (`Crew Member` role) |
| Campus club server | **1,500–2,500 BDT / month** | Whole helping-hand server, you pay one xAI bill |
| Free trial | 0 BDT | **15 messages/day** per Discord user |

**Payments (v1):** no Stripe. Treasurer collects bKash/Nagad, then an admin runs `/grant @user 30d`. That writes the paid quota and (if the bot can) assigns **Crew Member**.

## Academic honesty

Writer produces outlines, checklists, citation format, and Socratic hints. It **refuses** “write my full assignment.” That is required if you want to sell this into a university.

## Cost controls (one key, not five SuperGrok subs)

- **xAI API** at `https://api.x.ai/v1` — not SuperGrok ($30 × 5), not Grok consumer chat, not the US regional 1.1x endpoint.
- Default model **`grok-4.3`** ($1.25 / $2.50 per 1M tokens; cached input $0.20 / 1M). CSE coding only uses **`grok-build-0.1`** ($1 / $2).
- Never default to `grok-4.5` / `grok-4.6`. Never enable xAI `web_search` / Collections.
- Campus answers come from **local SQLite FTS5** (`/kb add` your notices). Focus study plans are local templates.
- Keyword + slash-command router first; Grok classify only if that fails, capped at ~20 tokens.
- Replies capped at ~180 output tokens. Shared `CREW_PREAMBLE` stays identical so prompt cache hits.
- Hard monthly Grok budget (`GROK_MONTHLY_BUDGET_USD`, default $10) pauses AI replies before you overspend. Campus FAQ + Focus plans still work.
- Memory is a short rolling summary, not full chat.

## Slash commands

| Command | Bot | Who |
|---|---|---|
| `/ask` | Captain | Everyone |
| `/quiz` | Tutor | Everyone |
| `/outline` `/cite` `/cv` | Writer | Everyone |
| `/plan` | Focus | Everyone |
| `/quota` | Captain | Everyone (admins also see Grok spend) |
| `/grant @user 30d` | Captain | Admin, after bKash/Nagad |
| `/kb add` | Campus | Admin, official FAQs only |

## What you must provide before go-live

- One xAI API key (pay-as-you-go credit, **not** SuperGrok).
- One AgentMail API key if you want Gmail (`--mail`).
- Five Discord bot tokens, all invited to the same server (free), if you want Discord.
- Optional: first FAQ pack — uni name, semester dates, scholarship blurbs via `/kb add` or `KB ADD`.

## Tests

```bash
pytest
```

Router, quota, budget, and Gmail notify tests do **not** need live Discord, xAI, or AgentMail keys.

## Out of scope (v1)

WhatsApp/Telegram, Grok image/voice, xAI web search, Stripe, a custom web chat app, five separate Grok accounts.
