"""Tests for 月事陪伴 — menstrual phase tracking + care broadcast."""
from __future__ import annotations

import json
import pytest
from datetime import date, datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from src.broadcaster.menstrual_care import (
    PHASE_MENSTRUATION,
    PHASE_FOLLICULAR,
    PHASE_OVULATION,
    PHASE_LUTEAL,
    _calculate_phase,
    _menstrual_fallback,
    _current_iso_week,
    _within_send_window,
    compose_menstrual_care_tip,
    run_menstrual_care,
    BUBBLE_MAX,
    MAX_BUBBLES,
    HKT,
)

# ---------------------------------------------------------------------------
# Phase calculation tests (pure, no async)
# ---------------------------------------------------------------------------


def test_day_1_is_menstruation():
    """Day 0 since start → 行經期."""
    start = date(2026, 5, 1)
    today = date(2026, 5, 1)  # Day 0 (same day as start)
    assert _calculate_phase(start, 28, today) == PHASE_MENSTRUATION


def test_day_4_is_menstruation():
    """Day 4 → 行經期."""
    start = date(2026, 5, 1)
    today = date(2026, 5, 5)  # Day 4
    assert _calculate_phase(start, 28, today) == PHASE_MENSTRUATION


def test_day_5_is_follicular():
    """Day 5 → 經後期."""
    start = date(2026, 5, 1)
    today = date(2026, 5, 6)  # Day 5
    assert _calculate_phase(start, 28, today) == PHASE_FOLLICULAR


def test_day_12_is_follicular():
    """Day 12 → 經後期."""
    start = date(2026, 5, 1)
    today = date(2026, 5, 13)  # Day 12
    assert _calculate_phase(start, 28, today) == PHASE_FOLLICULAR


def test_day_13_is_ovulation():
    """Day 13 → 排卵期."""
    start = date(2026, 5, 1)
    today = date(2026, 5, 14)  # Day 13
    assert _calculate_phase(start, 28, today) == PHASE_OVULATION


def test_day_15_is_ovulation():
    """Day 15 → 排卵期."""
    start = date(2026, 5, 1)
    today = date(2026, 5, 16)  # Day 15
    assert _calculate_phase(start, 28, today) == PHASE_OVULATION


def test_day_16_is_luteal():
    """Day 16 → 黃體期."""
    start = date(2026, 5, 1)
    today = date(2026, 5, 17)  # Day 16
    assert _calculate_phase(start, 28, today) == PHASE_LUTEAL


def test_day_27_is_luteal():
    """Day 27 → 黃體期."""
    start = date(2026, 5, 1)
    today = date(2026, 5, 28)  # Day 27
    assert _calculate_phase(start, 28, today) == PHASE_LUTEAL


def test_day_28_wraps_to_menstruation():
    """Day 28 (= day 0 of next cycle) → 行經期."""
    start = date(2026, 5, 1)
    today = date(2026, 5, 29)  # Day 28 → 28 % 28 == 0
    assert _calculate_phase(start, 28, today) == PHASE_MENSTRUATION


def test_phase_with_30_day_cycle():
    """30-day cycle: day 28 should still be luteal (not wrap yet)."""
    start = date(2026, 5, 1)
    today = date(2026, 5, 29)  # Day 28 of 30-day cycle → 28 % 30 == 28 → 黃體期
    assert _calculate_phase(start, 30, today) == PHASE_LUTEAL


# ---------------------------------------------------------------------------
# Fallback tests
# ---------------------------------------------------------------------------


def test_fallback_for_each_phase():
    """Each of the 4 phases returns a non-empty list."""
    for phase in [PHASE_MENSTRUATION, PHASE_FOLLICULAR, PHASE_OVULATION, PHASE_LUTEAL]:
        result = _menstrual_fallback(phase)
        assert isinstance(result, list), f"Expected list for phase {phase}"
        assert len(result) > 0, f"Expected non-empty list for phase {phase}"
        assert all(isinstance(b, str) and b for b in result), f"Expected non-empty strings for {phase}"


def test_fallback_has_no_price():
    """None of the fallback strings for any phase contain 'HK$'."""
    for phase in [PHASE_MENSTRUATION, PHASE_FOLLICULAR, PHASE_OVULATION, PHASE_LUTEAL]:
        for bubble in _menstrual_fallback(phase):
            assert "HK$" not in bubble, f"Price leaked in fallback for {phase}: {bubble}"
            assert "$" not in bubble or "HK$" not in bubble


# ---------------------------------------------------------------------------
# Composer tests (LLM mocked)
# ---------------------------------------------------------------------------


def _make_llm_mock(response_text: str) -> MagicMock:
    """Build a mock LLM that returns the given text from messages.create."""
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=response_text)]
    llm = MagicMock()
    llm.messages.create = AsyncMock(return_value=mock_response)
    return llm


def _make_user(
    phone: str = "+85291234567",
    last_period_start: date | None = None,
    cycle_length_days: int = 28,
) -> object:
    from src.crm.models import User
    user = User(phone=phone)
    if last_period_start is not None:
        user = user.with_updates(
            last_period_start=last_period_start,
            cycle_length_days=cycle_length_days,
        )
    return user


@pytest.mark.asyncio
async def test_composer_fallback_on_llm_failure():
    """When LLM raises an exception, fallback is returned."""
    llm = MagicMock()
    llm.messages.create = AsyncMock(side_effect=RuntimeError("LLM down"))
    user = _make_user()

    result = await compose_menstrual_care_tip(llm, user, PHASE_MENSTRUATION)
    assert isinstance(result, list)
    assert len(result) > 0
    # Should be the fallback for 行經期
    assert any("行經" in b or "休息" in b or "生冷" in b for b in result)


@pytest.mark.asyncio
async def test_composer_strips_price_leak():
    """Bubbles containing prices are silently dropped; fallback returned if all stripped."""
    price_response = json.dumps({"bubbles": ["價錢 HK$100 折扣！", "HK$50 另一條"]})
    llm = _make_llm_mock(price_response)
    user = _make_user()

    result = await compose_menstrual_care_tip(llm, user, PHASE_FOLLICULAR)
    # All price-containing bubbles were stripped → fallback
    assert isinstance(result, list)
    assert len(result) > 0
    for bubble in result:
        assert "HK$" not in bubble


@pytest.mark.asyncio
async def test_composer_respects_bubble_length_cap():
    """Bubbles longer than BUBBLE_MAX are truncated to BUBBLE_MAX chars."""
    long_bubble = "A" * 300  # Way over the 150-char cap
    response = json.dumps({"bubbles": [long_bubble]})
    llm = _make_llm_mock(response)
    user = _make_user()

    result = await compose_menstrual_care_tip(llm, user, PHASE_OVULATION)
    assert isinstance(result, list)
    assert len(result) > 0
    for bubble in result:
        assert len(bubble) <= BUBBLE_MAX


@pytest.mark.asyncio
async def test_composer_max_two_bubbles():
    """Even if the LLM returns 5 bubbles, only MAX_BUBBLES (2) are returned."""
    many_bubbles = json.dumps({"bubbles": [f"訊息{i}" for i in range(5)]})
    llm = _make_llm_mock(many_bubbles)
    user = _make_user()

    result = await compose_menstrual_care_tip(llm, user, PHASE_LUTEAL)
    assert len(result) <= MAX_BUBBLES


@pytest.mark.asyncio
async def test_composer_happy_path():
    """Valid LLM response → bubbles returned correctly."""
    good_response = json.dumps({
        "bubbles": [
            "行經期記得多休息，飲熱薑茶好暖胃 🌹",
            "熱水袋暖小腹有助緩解不適，保持心情輕鬆 💕",
        ]
    })
    llm = _make_llm_mock(good_response)
    user = _make_user()

    result = await compose_menstrual_care_tip(llm, user, PHASE_MENSTRUATION)
    assert len(result) == 2
    assert "行經" in result[0]


# ---------------------------------------------------------------------------
# CRM model tests
# ---------------------------------------------------------------------------


def test_user_default_period_start_is_none():
    """User(phone=...).last_period_start is None by default."""
    from src.crm.models import User
    user = User(phone="+85291234567")
    assert user.last_period_start is None


def test_user_cycle_length_default_28():
    """User(phone=...).cycle_length_days == 28 by default."""
    from src.crm.models import User
    user = User(phone="+85291234567")
    assert user.cycle_length_days == 28


def test_user_with_updates_period_start():
    """with_updates(last_period_start=...) sets the field correctly."""
    from src.crm.models import User
    user = User(phone="+85291234567")
    updated = user.with_updates(last_period_start=date(2026, 5, 1))
    assert updated.last_period_start == date(2026, 5, 1)
    # Original is unchanged (immutability)
    assert user.last_period_start is None


# ---------------------------------------------------------------------------
# Scheduler run tests
# ---------------------------------------------------------------------------


def _make_crm(
    phones: list[str],
    already_sent: int = 0,
    has_period_data: bool = True,
) -> MagicMock:
    from src.crm.models import User
    crm = MagicMock()
    crm.list_active_phones = AsyncMock(return_value=phones)
    crm.get_broadcast_count_this_week = AsyncMock(return_value=already_sent)
    crm.record_broadcast = AsyncMock()
    if phones:
        user = User(phone=phones[0])
        if has_period_data:
            user = user.with_updates(
                last_period_start=date(2026, 5, 1),
                cycle_length_days=28,
            )
        crm.get_user = AsyncMock(return_value=user)
    return crm


_FIXED_ISO_WEEK = "2026-W21"
_FIXED_TODAY = date(2026, 5, 25)
_FIXED_ISO_TS = "2026-05-25T10:00:00+08:00"


@pytest.mark.asyncio
async def test_skips_users_without_period_data():
    """Users without last_period_start set should not receive a broadcast."""
    phone = "+85291234567"
    crm = _make_crm([phone], has_period_data=False)
    llm = _make_llm_mock(json.dumps({"bubbles": ["test"]}))

    with (
        patch("src.broadcaster.menstrual_care.is_blocked", return_value=False),
        patch("src.broadcaster.menstrual_care.wa_client.send_long_message", new_callable=AsyncMock) as mock_send,
        patch("src.broadcaster.menstrual_care._within_send_window", return_value=True),
        patch("src.broadcaster.menstrual_care._current_iso_week", return_value=_FIXED_ISO_WEEK),
        patch("src.broadcaster.menstrual_care.datetime") as mock_dt,
        patch("src.broadcaster.menstrual_care.asyncio.sleep", new_callable=AsyncMock),
    ):
        # .now() is called for: send window check (bypassed) + .date() for _calculate_phase
        fixed_now = MagicMock()
        fixed_now.date = MagicMock(return_value=_FIXED_TODAY)
        fixed_now.isoformat = MagicMock(return_value=_FIXED_ISO_TS)
        mock_dt.now.return_value = fixed_now

        await run_menstrual_care(crm, llm, "test-account")
        mock_send.assert_not_called()


@pytest.mark.asyncio
async def test_skips_blocked_phone():
    """Blocked phones should not receive a broadcast."""
    phone = "+85291234567"
    crm = _make_crm([phone], has_period_data=True)
    llm = _make_llm_mock(json.dumps({"bubbles": ["test"]}))

    with (
        patch("src.broadcaster.menstrual_care.is_blocked", return_value=True),
        patch("src.broadcaster.menstrual_care.wa_client.send_long_message", new_callable=AsyncMock) as mock_send,
        patch("src.broadcaster.menstrual_care._within_send_window", return_value=True),
        patch("src.broadcaster.menstrual_care._current_iso_week", return_value=_FIXED_ISO_WEEK),
        patch("src.broadcaster.menstrual_care.datetime") as mock_dt,
        patch("src.broadcaster.menstrual_care.asyncio.sleep", new_callable=AsyncMock),
    ):
        fixed_now = MagicMock()
        fixed_now.date = MagicMock(return_value=_FIXED_TODAY)
        fixed_now.isoformat = MagicMock(return_value=_FIXED_ISO_TS)
        mock_dt.now.return_value = fixed_now

        await run_menstrual_care(crm, llm, "test-account")
        mock_send.assert_not_called()


@pytest.mark.asyncio
async def test_skips_already_sent_this_week():
    """Users already sent a menstrual care tip this week should be skipped."""
    phone = "+85291234567"
    crm = _make_crm([phone], already_sent=1, has_period_data=True)
    llm = _make_llm_mock(json.dumps({"bubbles": ["test"]}))

    with (
        patch("src.broadcaster.menstrual_care.is_blocked", return_value=False),
        patch("src.broadcaster.menstrual_care.wa_client.send_long_message", new_callable=AsyncMock) as mock_send,
        patch("src.broadcaster.menstrual_care._within_send_window", return_value=True),
        patch("src.broadcaster.menstrual_care._current_iso_week", return_value=_FIXED_ISO_WEEK),
        patch("src.broadcaster.menstrual_care.datetime") as mock_dt,
        patch("src.broadcaster.menstrual_care.asyncio.sleep", new_callable=AsyncMock),
    ):
        fixed_now = MagicMock()
        fixed_now.date = MagicMock(return_value=_FIXED_TODAY)
        fixed_now.isoformat = MagicMock(return_value=_FIXED_ISO_TS)
        mock_dt.now.return_value = fixed_now

        await run_menstrual_care(crm, llm, "test-account")
        mock_send.assert_not_called()


@pytest.mark.asyncio
async def test_sends_for_user_with_known_cycle():
    """Users with last_period_start set and not yet sent this week receive a tip."""
    phone = "+85291234567"
    crm = _make_crm([phone], already_sent=0, has_period_data=True)
    good_response = json.dumps({"bubbles": ["行經期多休息 🌹"]})
    llm = _make_llm_mock(good_response)

    with (
        patch("src.broadcaster.menstrual_care.is_blocked", return_value=False),
        patch("src.broadcaster.menstrual_care.wa_client.send_long_message", new_callable=AsyncMock) as mock_send,
        patch("src.broadcaster.menstrual_care._within_send_window", return_value=True),
        patch("src.broadcaster.menstrual_care._current_iso_week", return_value=_FIXED_ISO_WEEK),
        patch("src.broadcaster.menstrual_care.datetime") as mock_dt,
        patch("src.broadcaster.menstrual_care.asyncio.sleep", new_callable=AsyncMock),
    ):
        fixed_now = MagicMock()
        fixed_now.date = MagicMock(return_value=_FIXED_TODAY)
        fixed_now.isoformat = MagicMock(return_value=_FIXED_ISO_TS)
        mock_dt.now.return_value = fixed_now

        await run_menstrual_care(crm, llm, "test-account")
        mock_send.assert_called_once()


@pytest.mark.asyncio
async def test_dedup_key_uses_menstrual_prefix():
    """The dedup key passed to record_broadcast starts with 'menstrual-'."""
    phone = "+85291234567"
    crm = _make_crm([phone], already_sent=0, has_period_data=True)
    good_response = json.dumps({"bubbles": ["行經期多休息 🌹"]})
    llm = _make_llm_mock(good_response)

    with (
        patch("src.broadcaster.menstrual_care.is_blocked", return_value=False),
        patch("src.broadcaster.menstrual_care.wa_client.send_long_message", new_callable=AsyncMock),
        patch("src.broadcaster.menstrual_care._within_send_window", return_value=True),
        patch("src.broadcaster.menstrual_care._current_iso_week", return_value=_FIXED_ISO_WEEK),
        patch("src.broadcaster.menstrual_care.datetime") as mock_dt,
        patch("src.broadcaster.menstrual_care.asyncio.sleep", new_callable=AsyncMock),
    ):
        fixed_now = MagicMock()
        fixed_now.date = MagicMock(return_value=_FIXED_TODAY)
        fixed_now.isoformat = MagicMock(return_value=_FIXED_ISO_TS)
        mock_dt.now.return_value = fixed_now

        await run_menstrual_care(crm, llm, "test-account")

        # Verify record_broadcast was called with a key starting with "menstrual-"
        crm.record_broadcast.assert_called_once()
        call_args = crm.record_broadcast.call_args
        dedup_key_arg = call_args[0][2]  # positional: phone, broadcast_type, dedup_key, sent_at
        assert dedup_key_arg.startswith("menstrual-"), (
            f"Expected dedup key to start with 'menstrual-', got: {dedup_key_arg}"
        )
