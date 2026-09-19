"""Environment-backed settings. Defaults keep Grok spend low."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from helpinghand import PAID_ROLE_NAME

log = logging.getLogger(__name__)

EXPENSIVE_MODELS = frozenset({"grok-4.5", "grok-4.6", "grok-4.5-latest", "grok-4.6-latest"})
DEFAULT_MODEL = "grok-4.3"
CODE_MODEL = "grok-build-0.1"
GLOBAL_XAI_URL = "https://api.x.ai/v1"


def _f(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return float(raw)


def _i(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return int(raw)


def _b(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    xai_api_key: str
    xai_base_url: str = GLOBAL_XAI_URL
    grok_default_model: str = DEFAULT_MODEL
    grok_code_model: str = CODE_MODEL
    grok_monthly_budget_usd: float = 10.0
    grok_max_output_tokens: int = 350
    grok_classify_max_tokens: int = 20
    grok_reasoning_effort: str = "none"
    discord_token_captain: str = ""
    discord_token_tutor: str = ""
    discord_token_writer: str = ""
    discord_token_campus: str = ""
    discord_token_focus: str = ""
    sqlite_path: Path = Path("data/crew.db")
    free_daily_quota: int = 15
    paid_daily_quota: int = 80
    paid_role_name: str = PAID_ROLE_NAME
    seed_sample_faqs: bool = True

    @classmethod
    def from_env(cls, *, dotenv: bool = True) -> Settings:
        if dotenv:
            load_dotenv()
        settings = cls(
            xai_api_key=os.getenv("XAI_API_KEY", "").strip(),
            xai_base_url=os.getenv("XAI_BASE_URL", GLOBAL_XAI_URL).strip() or GLOBAL_XAI_URL,
            grok_default_model=os.getenv("GROK_DEFAULT_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL,
            grok_code_model=os.getenv("GROK_CODE_MODEL", CODE_MODEL).strip() or CODE_MODEL,
            grok_monthly_budget_usd=_f("GROK_MONTHLY_BUDGET_USD", 10.0),
            grok_max_output_tokens=_i("GROK_MAX_OUTPUT_TOKENS", 350),
            grok_classify_max_tokens=_i("GROK_CLASSIFY_MAX_TOKENS", 20),
            grok_reasoning_effort=os.getenv("GROK_REASONING_EFFORT", "none").strip() or "none",
            discord_token_captain=os.getenv("DISCORD_TOKEN_CAPTAIN", "").strip(),
            discord_token_tutor=os.getenv("DISCORD_TOKEN_TUTOR", "").strip(),
            discord_token_writer=os.getenv("DISCORD_TOKEN_WRITER", "").strip(),
            discord_token_campus=os.getenv("DISCORD_TOKEN_CAMPUS", "").strip(),
            discord_token_focus=os.getenv("DISCORD_TOKEN_FOCUS", "").strip(),
            sqlite_path=Path(os.getenv("SQLITE_PATH", "data/crew.db")),
            free_daily_quota=_i("FREE_DAILY_QUOTA", 15),
            paid_daily_quota=_i("PAID_DAILY_QUOTA", 80),
            paid_role_name=os.getenv("PAID_ROLE_NAME", PAID_ROLE_NAME).strip() or PAID_ROLE_NAME,
            seed_sample_faqs=_b("SEED_SAMPLE_FAQS", True),
        )
        settings.warn_if_expensive()
        return settings

    def warn_if_expensive(self) -> None:
        for label, model in (
            ("GROK_DEFAULT_MODEL", self.grok_default_model),
            ("GROK_CODE_MODEL", self.grok_code_model),
        ):
            stem = model.lower()
            if any(stem.startswith(exp) for exp in EXPENSIVE_MODELS):
                log.warning(
                    "%s=%s is a costly Grok model; Helping Hand Crew defaults to grok-4.3 "
                    "($1.25/$2.50 per 1M) and grok-build-0.1 for code. This will burn budget faster.",
                    label,
                    model,
                )
        if "1.1" in self.xai_base_url or "us-west" in self.xai_base_url.lower():
            log.warning("XAI_BASE_URL looks regional; prefer %s (global, no 1.1x surcharge).", GLOBAL_XAI_URL)

    def discord_tokens(self) -> dict[str, str]:
        return {
            "captain": self.discord_token_captain,
            "tutor": self.discord_token_tutor,
            "writer": self.discord_token_writer,
            "campus": self.discord_token_campus,
            "focus": self.discord_token_focus,
        }

    def missing_discord_tokens(self) -> list[str]:
        return [name for name, token in self.discord_tokens().items() if not token]

    def require_live(self) -> None:
        missing = []
        if not self.xai_api_key:
            missing.append("XAI_API_KEY")
        for name in self.missing_discord_tokens():
            missing.append(f"DISCORD_TOKEN_{name.upper()}")
        if missing:
            raise SystemExit(
                "Missing required env vars: "
                + ", ".join(missing)
                + ". Copy .env.example to .env and add one xAI key plus five Discord bot tokens."
            )
