"""xAI client: model routing, cache-aware cost, output caps, monthly kill-switch."""

from __future__ import annotations

import json

import httpx
import pytest

from helpinghand.config import Settings
from helpinghand.db import connect
from helpinghand.grok import (
    BudgetExceededError,
    BudgetLedger,
    GrokClient,
    build_chat_payload,
    estimate_cost_usd,
    looks_like_code,
)


def test_default_and_code_models(tmp_path) -> None:
    settings = Settings(xai_api_key="k", sqlite_path=tmp_path / "b.db")
    ledger = BudgetLedger(connect(tmp_path / "b.db"), 10)
    client = GrokClient(settings, ledger, http=httpx.AsyncClient())
    assert client.select_model() == "grok-4.3"
    assert client.select_model(code=True) == "grok-build-0.1"


def test_estimate_uses_cached_input_rate() -> None:
    uncached = estimate_cost_usd("grok-4.3", prompt_tokens=1_000_000, completion_tokens=0, cached_tokens=0)
    cached = estimate_cost_usd("grok-4.3", prompt_tokens=1_000_000, completion_tokens=0, cached_tokens=1_000_000)
    assert uncached == pytest.approx(1.25)
    assert cached == pytest.approx(0.20)
    code_out = estimate_cost_usd("grok-build-0.1", prompt_tokens=0, completion_tokens=1_000_000)
    assert code_out == pytest.approx(2.00)


def test_payload_caps_and_no_web_search() -> None:
    specialist = build_chat_payload(
        model="grok-4.3",
        messages=[{"role": "system", "content": "stable"}, {"role": "user", "content": "q"}],
        max_tokens=350,
        classify=False,
        reasoning_effort="none",
    )
    classify = build_chat_payload(
        model="grok-4.3",
        messages=[{"role": "user", "content": "q"}],
        max_tokens=20,
        classify=True,
        reasoning_effort="none",
    )
    assert specialist["max_tokens"] == 350
    assert classify["max_tokens"] == 20
    assert classify["temperature"] == 0.0
    assert specialist["reasoning_effort"] == "none"
    dumped = json.dumps(specialist)
    assert "web_search" not in dumped
    assert "tools" not in specialist


def test_looks_like_code() -> None:
    assert looks_like_code("debug this python function please")
    assert looks_like_code("```python\nprint(1)\n```")
    assert not looks_like_code("explain photosynthesis for the biology exam")


def test_kill_switch_pauses_after_cap(tmp_path) -> None:
    conn = connect(tmp_path / "b.db")
    ledger = BudgetLedger(conn, monthly_budget_usd=0.00001)
    assert not ledger.is_paused()
    snap = ledger.record(
        model="grok-4.3",
        prompt_tokens=1000,
        completion_tokens=1000,
        cached_tokens=0,
        cost_usd=0.001,
        max_tokens=350,
        specialist="tutor",
    )
    assert snap.paused
    assert ledger.is_paused()


@pytest.mark.asyncio
async def test_chat_records_cache_and_raises_when_paused(tmp_path) -> None:
    captured: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(
            {
                "url": str(request.url),
                "headers": dict(request.headers),
                "body": json.loads(request.content),
            }
        )
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "tutor"}}],
                "usage": {
                    "prompt_tokens": 100,
                    "completion_tokens": 8,
                    "prompt_tokens_details": {"cached_tokens": 80},
                },
            },
        )

    settings = Settings(
        xai_api_key="k",
        sqlite_path=tmp_path / "b.db",
        grok_monthly_budget_usd=0.00001,
        grok_max_output_tokens=350,
        grok_classify_max_tokens=20,
    )
    ledger = BudgetLedger(connect(tmp_path / "b.db"), settings.grok_monthly_budget_usd)
    transport = httpx.MockTransport(handler)
    http = httpx.AsyncClient(base_url="https://api.x.ai/v1", transport=transport)
    client = GrokClient(settings, ledger, http=http)

    first = await client.chat(
        [{"role": "system", "content": "stable prompt"}, {"role": "user", "content": "hi"}],
        conv_id="helpinghand-tutor",
        specialist="tutor",
    )
    assert first.model == "grok-4.3"
    assert first.cached_tokens == 80
    assert first.max_tokens == 350
    assert first.cost_usd > 0
    assert captured[0]["body"]["max_tokens"] == 350
    assert "web_search" not in captured[0]["body"]
    assert captured[0]["headers"].get("x-grok-conv-id") == "helpinghand-tutor"
    assert ledger.is_paused()

    with pytest.raises(BudgetExceededError):
        await client.chat([{"role": "user", "content": "again"}])

    labelled = None
    # classify path uses 20 token cap — unpause by using a fresh month ledger
    settings2 = Settings(xai_api_key="k", sqlite_path=tmp_path / "b2.db", grok_monthly_budget_usd=10)
    ledger2 = BudgetLedger(connect(tmp_path / "b2.db"), 10)
    client2 = GrokClient(settings2, ledger2, http=http)
    result = await client2.chat([{"role": "user", "content": "route me"}], classify=True)
    assert result.max_tokens == 20
    assert captured[-1]["body"]["max_tokens"] == 20
    assert captured[-1]["body"]["temperature"] == 0.0
    assert labelled is None

    code = await client2.chat([{"role": "user", "content": "fix"}], code=True)
    assert code.model == "grok-build-0.1"
    assert captured[-1]["body"]["model"] == "grok-build-0.1"
