"""CLI entry: python -m helpinghand"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from helpinghand import SPECIALISTS
from helpinghand.config import Settings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Helping Hand Crew — five Discord bots, one xAI key")
    parser.add_argument(
        "--check-config",
        action="store_true",
        help="Validate .env (does not connect to Discord or xAI)",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    settings = Settings.from_env()
    if args.check_config:
        settings.warn_if_expensive()
        missing = []
        if not settings.xai_api_key:
            missing.append("XAI_API_KEY")
        missing.extend(f"DISCORD_TOKEN_{n.upper()}" for n in settings.missing_discord_tokens())
        print(f"default_model={settings.grok_default_model}")
        print(f"code_model={settings.grok_code_model}")
        print(f"budget_usd={settings.grok_monthly_budget_usd}")
        print(f"specialists={','.join(SPECIALISTS)}")
        print(f"sqlite={settings.sqlite_path}")
        if missing:
            print("missing=" + ",".join(missing))
            raise SystemExit(1)
        print("config=ok")
        return

    settings.require_live()
    from helpinghand.bots.runner import start_crew
    from helpinghand.crew import HelpingHandCrew

    crew = HelpingHandCrew(settings)
    try:
        asyncio.run(start_crew(crew, settings))
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
