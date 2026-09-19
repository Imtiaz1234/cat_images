"""Daily quotas, Crew Member grants, and role gating."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from helpinghand.db import connect
from helpinghand.quota import QuotaExceededError, QuotaManager, parse_duration


class Clock:
    def __init__(self, day: date) -> None:
        self.day = day

    def __call__(self) -> date:
        return self.day


@pytest.fixture
def quota(tmp_path) -> tuple[QuotaManager, Clock]:
    clock = Clock(date(2026, 9, 19))
    mgr = QuotaManager(connect(tmp_path / "q.db"), free_daily=15, paid_daily=80, today=clock)
    return mgr, clock


def test_parse_duration() -> None:
    assert parse_duration("30d") == timedelta(days=30)
    assert parse_duration("7 days") == timedelta(days=7)
    with pytest.raises(ValueError):
        parse_duration("monthly")


def test_free_user_blocked_after_15(quota) -> None:
    mgr, _ = quota
    user = "u-free"
    for _ in range(15):
        snap = mgr.consume(user)
        assert snap.limit == 15
        assert not snap.paid
    with pytest.raises(QuotaExceededError) as exc:
        mgr.consume(user)
    assert exc.value.used == 15
    assert exc.value.limit == 15
    assert mgr.status(user).remaining == 0


def test_paid_role_gets_80(quota) -> None:
    mgr, _ = quota
    user = "u-role"
    for _ in range(80):
        mgr.consume(user, has_paid_role=True)
    with pytest.raises(QuotaExceededError) as exc:
        mgr.consume(user, has_paid_role=True)
    assert exc.value.limit == 80
    assert exc.value.paid


def test_grant_30d_upgrades_limit(quota) -> None:
    mgr, clock = quota
    user = "u-grant"
    until = mgr.grant(user, "30d", note="bkash")
    assert until == clock.day + timedelta(days=30)
    snap = mgr.consume(user)
    assert snap.paid
    assert snap.limit == 80
    assert snap.granted_until == until.isoformat()


def test_grant_expires(quota) -> None:
    mgr, clock = quota
    user = "u-exp"
    mgr.grant(user, "1d")
    clock.day = clock.day + timedelta(days=2)
    snap = mgr.status(user)
    assert not snap.paid
    assert snap.limit == 15


def test_daily_reset(quota) -> None:
    mgr, clock = quota
    user = "u-reset"
    for _ in range(15):
        mgr.consume(user)
    with pytest.raises(QuotaExceededError):
        mgr.consume(user)
    clock.day = clock.day + timedelta(days=1)
    snap = mgr.consume(user)
    assert snap.used == 1
    assert snap.remaining == 14


def test_check_does_not_consume(quota) -> None:
    mgr, _ = quota
    mgr.check("u1")
    assert mgr.used_today("u1") == 0
