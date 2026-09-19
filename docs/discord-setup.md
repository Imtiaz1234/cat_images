# Create the five free Discord apps

Gmail-only notifications, shared prompts, and the 10-minute session script: [BUILD.md](BUILD.md).

Helping Hand Crew is **one Python process** and **five Discord application identities**. Apps are free. You do not buy five Grok subscriptions.

## 1. Open the developer portal

Go to [https://discord.com/developers/applications](https://discord.com/developers/applications) and sign in.

## 2. Repeat this five times

Create applications named so the member list looks like a team:

1. `HH Captain` (or `Captain — Helping Hand`)
2. `HH Tutor`
3. `HH Writer`
4. `HH Campus`
5. `HH Focus`

For each app:

1. **Bot** → Add Bot → Reset Token → copy into `.env`:
   - `DISCORD_TOKEN_CAPTAIN`
   - `DISCORD_TOKEN_TUTOR`
   - `DISCORD_TOKEN_WRITER`
   - `DISCORD_TOKEN_CAMPUS`
   - `DISCORD_TOKEN_FOCUS`
2. **Privileged Gateway Intents** → enable **Message Content Intent** (Captain reads questions in the desk channels).
3. **OAuth2 → URL Generator**
   - Scopes: `bot` and `applications.commands`
   - Bot permissions: Send Messages, Read Message History, Embed Links, Add Reactions, Use Slash Commands.
   - Optional: **Manage Roles** so `/grant` can assign **Crew Member**. Put the bot role *above* Crew Member.
4. Open the generated invite URL while logged in as a server admin and authorize.

## 3. Server role

Create a role exactly named `Crew Member` (or set `PAID_ROLE_NAME` in `.env`). Free users get 15 messages/day; this role (or a `/grant`) gets 80/day.

## 4. One xAI key

Create a pay-as-you-go key at [https://console.x.ai](https://console.x.ai). Put it in `XAI_API_KEY`. Keep `XAI_BASE_URL=https://api.x.ai/v1`. Start with a small credit, not SuperGrok.

## 5. Host

Run `python -m helpinghand` on a cheap always-on VPS or Railway. Discord gateway connections drop if the process sleeps.

```bash
python -m helpinghand --check-config
python -m helpinghand
```

Slash commands appear after the bots sync (a few seconds after boot). If `/ask` is missing, kick/re-invite with the `applications.commands` scope.
