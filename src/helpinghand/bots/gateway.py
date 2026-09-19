"""Five Discord gateway clients sharing one HelpingHandCrew brain.

One speaker per turn. No Discord pings for reminders — Gmail only after PERMIT.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from helpinghand import CREW_CHANNELS, PAID_ROLE_NAME, SPECIALISTS
from helpinghand.i18n import t
from helpinghand.language import detect_language
from helpinghand.quota import parse_duration

if TYPE_CHECKING:
    from helpinghand.crew import CrewReply, HelpingHandCrew

log = logging.getLogger(__name__)

DISCORD_LIMIT = 1900


def clip(text: str, limit: int = DISCORD_LIMIT) -> str:
    text = text or ""
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def make_intents() -> discord.Intents:
    intents = discord.Intents.default()
    intents.message_content = True
    intents.guilds = True
    return intents


def is_admin(user: discord.abc.User) -> bool:
    perms = getattr(user, "guild_permissions", None)
    if perms is None:
        return False
    return bool(perms.administrator or perms.manage_guild)


def has_paid_role(user: discord.abc.User, role_name: str) -> bool:
    roles = getattr(user, "roles", [])
    return any(getattr(role, "name", "") == role_name for role in roles)


def mentioned_specialist(message: discord.Message, bots: dict[str, commands.Bot]) -> str | None:
    ids = {m.id for m in message.mentions}
    for name, bot in bots.items():
        user = bot.user
        if user and user.id in ids:
            return name
    return None


def in_crew_channel(channel) -> bool:
    name = getattr(channel, "name", "") or ""
    return name.lstrip("#").lower() in CREW_CHANNELS


async def publish_reply(
    crew: HelpingHandCrew,
    origin: commands.Bot,
    channel: discord.abc.Messageable,
    reply: CrewReply,
    *,
    reference: discord.Message | None = None,
) -> None:
    """Exactly one Discord message. No handoff ping. No reminder pings."""
    del crew  # never fan-out to a second bot
    kwargs = {"reference": reference} if reference is not None else {}
    try:
        await channel.send(clip(reply.text), **kwargs)
    except TypeError:
        await channel.send(clip(reply.text))
    except discord.HTTPException:
        await channel.send(clip(reply.text))


class CrewBot(commands.Bot):
    def __init__(self, *, name: str, crew: HelpingHandCrew) -> None:
        super().__init__(command_prefix=commands.when_mentioned, intents=make_intents(), help_command=None)
        self.specialist_name = name
        self.crew = crew

    async def setup_hook(self) -> None:
        register_commands(self)
        try:
            await self.tree.sync()
            log.info("%s slash commands synced", self.specialist_name)
        except discord.HTTPException:
            log.exception("%s slash sync failed", self.specialist_name)

    async def on_ready(self) -> None:
        log.info("%s online as %s", self.specialist_name, self.user)


def register_commands(bot: CrewBot) -> None:
    name = bot.specialist_name
    crew = bot.crew
    role_name = crew.settings.paid_role_name or PAID_ROLE_NAME

    async def run_turn(
        interaction: discord.Interaction,
        content: str,
        command: str,
        extra: dict | None = None,
        *,
        allow_classify: bool = False,
        is_admin_cmd: bool = False,
    ) -> None:
        await interaction.response.defer(thinking=True)
        reply = await crew.handle(
            user_id=str(interaction.user.id),
            content=content,
            channel_name=getattr(interaction.channel, "name", "") or "",
            command=command,
            has_paid_role=has_paid_role(interaction.user, role_name),
            display_name=interaction.user.display_name,
            extra=extra,
            allow_classify=allow_classify,
            is_admin=is_admin_cmd or is_admin(interaction.user),
        )
        await interaction.followup.send(clip(reply.text))

    if name == "captain":
        @bot.tree.command(name="ask", description="Ask Helping Hand Crew (one teammate replies)")
        @app_commands.describe(question="Your question in Bangla, Banglish, or English")
        async def ask(interaction: discord.Interaction, question: str) -> None:
            await run_turn(interaction, question, "ask", allow_classify=True)

        @bot.tree.command(name="quota", description="See today's remaining Crew messages")
        async def quota(interaction: discord.Interaction) -> None:
            await run_turn(interaction, "QUOTA", "quota")

        @bot.tree.command(name="grant", description="Admin: grant Crew Member quota after bKash/Nagad")
        @app_commands.describe(user="Student to upgrade", duration="e.g. 30d or 7d")
        async def grant(interaction: discord.Interaction, user: discord.Member, duration: str = "30d") -> None:
            lang = detect_language("")
            if not is_admin(interaction.user):
                await interaction.response.send_message(t("no_permission", lang), ephemeral=True)
                return
            try:
                parse_duration(duration)
            except ValueError as exc:
                await interaction.response.send_message(str(exc), ephemeral=True)
                return
            await run_turn(
                interaction,
                f"GRANT {user.id} {duration}",
                "grant",
                extra={"target": str(user.id), "duration": duration},
                is_admin_cmd=True,
            )
            role = discord.utils.get(interaction.guild.roles, name=role_name) if interaction.guild else None
            if role and interaction.guild and interaction.guild.me.guild_permissions.manage_roles:
                try:
                    await user.add_roles(role, reason="Helping Hand Crew /grant")
                except discord.HTTPException:
                    pass

    if name == "tutor":
        @bot.tree.command(name="quiz", description="Tutor: quiz me on a topic")
        @app_commands.describe(topic="Course or concept")
        async def quiz(interaction: discord.Interaction, topic: str) -> None:
            await run_turn(interaction, f"Quiz me on: {topic}", "quiz")

    if name == "writer":
        @bot.tree.command(name="outline", description="Writer: assignment outline (not a full draft)")
        @app_commands.describe(topic="Essay / report topic")
        async def outline(interaction: discord.Interaction, topic: str) -> None:
            await run_turn(interaction, f"Please outline (not a full essay): {topic}", "outline")

        @bot.tree.command(name="cite", description="Writer: citation format help")
        @app_commands.describe(style="harvard, apa, ieee, mla, chicago", source="Book, paper, or website details")
        async def cite(interaction: discord.Interaction, source: str, style: str = "harvard") -> None:
            await run_turn(interaction, f"Format a citation in {style} style for: {source}", "cite")

        @bot.tree.command(name="cv", description="Writer: tighten CV bullets (not a fake CV)")
        @app_commands.describe(role="Target role or scholarship", highlights="What you've actually done")
        async def cv(interaction: discord.Interaction, role: str, highlights: str) -> None:
            await run_turn(interaction, f"Help tighten CV bullets for {role}. Experience: {highlights}", "cv")

    if name == "campus":
        kb = app_commands.Group(name="kb", description="Campus knowledge base (local, no web search)")

        @kb.command(name="add", description="Admin: add a campus FAQ")
        @app_commands.describe(title="Short title", body="Official text")
        async def kb_add(interaction: discord.Interaction, title: str, body: str) -> None:
            lang = detect_language(body)
            if not is_admin(interaction.user):
                await interaction.response.send_message(t("no_permission", lang), ephemeral=True)
                return
            await run_turn(
                interaction,
                f"KB ADD {title} | {body}",
                "kb",
                extra={"title": title, "body": body},
                is_admin_cmd=True,
            )

        bot.tree.add_command(kb)

    if name == "focus":
        @bot.tree.command(name="plan", description="Focus: exam countdown (Gmail reminder after PERMIT)")
        @app_commands.describe(exam_date="YYYY-MM-DD", subjects="Comma-separated courses")
        async def plan(interaction: discord.Interaction, exam_date: str, subjects: str) -> None:
            await run_turn(
                interaction,
                f"Study plan. exam_date={exam_date}. subjects: {subjects}",
                "plan",
                extra={"exam_date": exam_date, "subjects": subjects},
            )


async def on_message_captain(bot: CrewBot, message: discord.Message) -> None:
    if message.author.bot:
        return
    crew = bot.crew
    bots = crew.bots
    mentioned = mentioned_specialist(message, bots)
    addressed = bool(mentioned) or in_crew_channel(message.channel) or isinstance(
        message.channel, discord.DMChannel
    )
    if not addressed:
        return
    content = message.content
    for other in bots.values():
        if other.user:
            content = content.replace(other.user.mention, "").strip()
    async with message.channel.typing():
        reply = await crew.handle(
            user_id=str(message.author.id),
            content=content,
            channel_name=getattr(message.channel, "name", "") or "",
            mentioned_specialist=mentioned,
            has_paid_role=has_paid_role(message.author, crew.settings.paid_role_name),
            display_name=message.author.display_name,
        )
    await publish_reply(crew, bot, message.channel, reply, reference=message)


def build_bot(name: str, crew: HelpingHandCrew) -> CrewBot:
    if name not in SPECIALISTS:
        raise ValueError(name)
    bot = CrewBot(name=name, crew=crew)
    if name == "captain":

        @bot.event
        async def on_message(message: discord.Message) -> None:
            await on_message_captain(bot, message)

    return bot
