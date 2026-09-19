"""Start all five Discord bots on one asyncio loop."""

from __future__ import annotations

import asyncio
import logging

from helpinghand.bots.gateway import build_bot
from helpinghand.config import Settings
from helpinghand.crew import HelpingHandCrew

log = logging.getLogger(__name__)


async def start_crew(crew: HelpingHandCrew, settings: Settings) -> None:
    tokens = settings.discord_tokens()
    bots = {name: build_bot(name, crew) for name in tokens}
    crew.attach_bots(bots)

    async def run_one(name: str) -> None:
        bot = bots[name]
        log.info("starting %s gateway", name)
        await bot.start(tokens[name])

    try:
        await asyncio.gather(*(run_one(name) for name in bots))
    finally:
        await asyncio.gather(*(bot.close() for bot in bots.values()), return_exceptions=True)
        await crew.aclose()
