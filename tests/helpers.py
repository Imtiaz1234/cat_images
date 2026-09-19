"""Test doubles. No live Discord or xAI keys required."""

from __future__ import annotations

from pathlib import Path

from helpinghand.config import Settings
from helpinghand.grok import ChatResult


def settings(tmp_path: Path, **overrides) -> Settings:
    values = dict(
        xai_api_key="test-key",
        sqlite_path=tmp_path / "crew.db",
        seed_sample_faqs=False,
        grok_monthly_budget_usd=10.0,
    )
    values.update(overrides)
    return Settings(**values)


class FakeGrok:
    def __init__(self, reply: str = "mocked specialist reply", classify_as: str = "tutor") -> None:
        self.reply = reply
        self.classify_as = classify_as
        self.chat_calls: list[dict] = []
        self.classify_calls: list[str] = []

    async def chat(self, messages, **kwargs):
        self.chat_calls.append({"messages": messages, **kwargs})
        return ChatResult(
            text=self.reply,
            model=kwargs.get("model") or ("grok-build-0.1" if kwargs.get("code") else "grok-4.3"),
            prompt_tokens=40,
            completion_tokens=12,
            cached_tokens=30,
            cost_usd=0.0001,
            max_tokens=20 if kwargs.get("classify") else 350,
        )

    async def classify(self, text: str) -> str:
        self.classify_calls.append(text)
        return self.classify_as

    async def aclose(self) -> None:
        return None
