"""CLI entry: python -m helpinghand [--mail] [--check-config]"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from helpinghand import SPECIALISTS
from helpinghand.config import Settings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Helping Hand Crew — five bots, one xAI key, Gmail-only notifies"
    )
    parser.add_argument(
        "--check-config",
        action="store_true",
        help="Validate .env (does not connect to Discord, xAI, or AgentMail)",
    )
    parser.add_argument(
        "--mail",
        action="store_true",
        help="Gmail personal assistant + notifications (AgentMail). Discord is not started.",
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
        missing: list[str] = []
        if not settings.xai_api_key:
            missing.append("XAI_API_KEY")
        if args.mail:
            if not settings.agentmail_api_key:
                missing.append("AGENTMAIL_API_KEY")
            if not settings.mail_notify_to:
                missing.append("MAIL_NOTIFY_TO")
        else:
            missing.extend(f"DISCORD_TOKEN_{n.upper()}" for n in settings.missing_discord_tokens())
        print(f"default_model={settings.grok_default_model}")
        print(f"code_model={settings.grok_code_model}")
        print(f"max_output_tokens={settings.grok_max_output_tokens}")
        print(f"budget_usd={settings.grok_monthly_budget_usd}")
        print(f"specialists={','.join(SPECIALISTS)}")
        print(f"sqlite={settings.sqlite_path}")
        print(f"notify_channel=gmail")
        print(f"mail_notify_to={settings.mail_notify_to or '(unset)'}")
        if missing:
            print("missing=" + ",".join(missing))
            raise SystemExit(1)
        print("config=ok")
        return

    from helpinghand.crew import HelpingHandCrew

    if args.mail:
        settings.require_mail()
        crew = HelpingHandCrew(settings)
        from helpinghand.mail import run_mail

        try:
            asyncio.run(run_mail(crew, settings))
        except KeyboardInterrupt:
            sys.exit(0)
        return

    settings.require_live()
    from helpinghand.bots.runner import start_crew

    crew = HelpingHandCrew(settings)
    try:
        asyncio.run(start_crew(crew, settings))
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
