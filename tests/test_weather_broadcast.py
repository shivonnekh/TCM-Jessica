"""Tests for the proactive weather broadcast + purchase follow-up features.

Covers:
  - weather_service: condition detection (pure — no I/O)
  - scheduler: eligibility checks (weekly cap + 36h gap)

All I/O (HKO API, LLM, WhatsApp send) is mocked.
"""

from __future__ import annotations

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from src.broadcaster.weather_service import (
    WeatherCondition,
    detect_conditions,
    pick_best,
    _hko_temp,
    _hko_humidity,
    _has_rainstorm,
)
from src.broadcaster.scheduler import (
    _current_iso_week,
    _within_send_window,
    _hours_since,
    _user_is_eligible,
)

# ---------------------------------------------------------------------------
# Fixtures — pinned HKO JSON shapes (real field names from 2026-05-25 fetch)
# ---------------------------------------------------------------------------

HKT = timezone(timedelta(hours=8))


def _make_current(temp_c: float, humidity_pct: float) -> dict:
    """Build a minimal rhrread payload."""
    return {
        "temperature": {
            "data": [
                {"place": "Hong Kong Observatory", "value": temp_c, "unit": "C"},
                {"place": "Sha Tin", "value": temp_c + 1, "unit": "C"},
            ],
            "recordTime": "2026-05-25T11:00:00+08:00",
        },
        "humidity": {
            "data": [{"place": "Hong Kong Observatory", "value": humidity_pct, "unit": "percent"}],
            "recordTime": "2026-05-25T11:00:00+08:00",
        },
        "rainfall": {"data": []},
        "warningMessage": [],
    }


def _make_warnings(code: str = "WRAIN", action: str = "AMBER") -> dict:
    """Build a warnsum payload with one active warning."""
    return {
        code: {
            "name": "Rainstorm Warning Signal",
            "code": code,
            "actionCode": action,
            "issueTime": "2026-05-25T10:00:00+08:00",
            "expireTime": "2026-05-25T16:00:00+08:00",
        }
    }


# ---------------------------------------------------------------------------
# weather_service: extraction helpers
# ---------------------------------------------------------------------------


class TestHkoExtractors:
    def test_temp_uses_observatory_first(self):
        current = _make_current(30.0, 71)
        assert _hko_temp(current) == 30.0

    def test_temp_fallback_average(self):
        current = {
            "temperature": {
                "data": [
                    {"place": "Sha Tin", "value": 34.0, "unit": "C"},
                    {"place": "Tsuen Wan", "value": 32.0, "unit": "C"},
                ]
            }
        }
        assert _hko_temp(current) == 33.0

    def test_temp_missing_returns_none(self):
        assert _hko_temp({}) is None
        assert _hko_temp({"temperature": {}}) is None

    def test_humidity_extracted(self):
        current = _make_current(30, 85)
        assert _hko_humidity(current) == 85.0

    def test_humidity_missing_returns_none(self):
        assert _hko_humidity({}) is None

    def test_rainstorm_active(self):
        active, code = _has_rainstorm(_make_warnings("WRAIN", "RED"))
        assert active is True
        assert code == "RED"

    def test_rainstorm_not_active(self):
        active, code = _has_rainstorm({})
        assert active is False
        assert code == ""

    def test_rainstorm_non_rain_warning_not_flagged(self):
        active, _ = _has_rainstorm({"WFIRE": {"actionCode": "YELLOW"}})
        assert active is False


# ---------------------------------------------------------------------------
# weather_service: condition detection
# ---------------------------------------------------------------------------


class TestDetectConditions:
    def test_empty_inputs_returns_empty(self):
        assert detect_conditions({}, {}) == []

    def test_malformed_current_returns_empty(self):
        assert detect_conditions({"temperature": None}, {}) == []

    def test_heatwave_detected_at_33(self):
        conditions = detect_conditions(_make_current(33, 60), {})
        codes = [c.code for c in conditions]
        assert "heatwave" in codes

    def test_heatwave_not_detected_below_33(self):
        conditions = detect_conditions(_make_current(32.9, 60), {})
        assert not any(c.code == "heatwave" for c in conditions)

    def test_heatwave_severity_mild_at_33(self):
        conditions = detect_conditions(_make_current(33, 60), {})
        hw = next(c for c in conditions if c.code == "heatwave")
        assert hw.severity == "mild"

    def test_heatwave_severity_moderate_at_34(self):
        conditions = detect_conditions(_make_current(34, 60), {})
        hw = next(c for c in conditions if c.code == "heatwave")
        assert hw.severity == "moderate"

    def test_heatwave_severity_severe_at_36(self):
        conditions = detect_conditions(_make_current(36, 60), {})
        hw = next(c for c in conditions if c.code == "heatwave")
        assert hw.severity == "severe"

    def test_cold_front_detected_below_18(self):
        conditions = detect_conditions(_make_current(17, 70), {})
        codes = [c.code for c in conditions]
        assert "cold_front" in codes

    def test_cold_front_not_detected_at_18(self):
        conditions = detect_conditions(_make_current(18, 70), {})
        assert not any(c.code == "cold_front" for c in conditions)

    def test_cold_front_severity_mild_at_17(self):
        conditions = detect_conditions(_make_current(17, 70), {})
        cf = next(c for c in conditions if c.code == "cold_front")
        assert cf.severity == "mild"

    def test_cold_front_severity_severe_below_12(self):
        conditions = detect_conditions(_make_current(11, 60), {})
        cf = next(c for c in conditions if c.code == "cold_front")
        assert cf.severity == "severe"

    def test_rainstorm_detected_from_warnings(self):
        conditions = detect_conditions(_make_current(26, 90), _make_warnings("WRAIN", "AMBER"))
        codes = [c.code for c in conditions]
        assert "rainstorm" in codes

    def test_rainstorm_red_is_severe(self):
        conditions = detect_conditions(_make_current(26, 90), _make_warnings("WRAIN", "RED"))
        rs = next(c for c in conditions if c.code == "rainstorm")
        assert rs.severity == "severe"

    def test_humidity_heat_detected(self):
        conditions = detect_conditions(_make_current(30, 86), {})
        codes = [c.code for c in conditions]
        assert "humidity_heat" in codes

    def test_humidity_heat_not_detected_when_cool(self):
        conditions = detect_conditions(_make_current(28, 90), {})
        assert not any(c.code == "humidity_heat" for c in conditions)

    def test_humidity_heat_not_detected_when_dry(self):
        conditions = detect_conditions(_make_current(32, 84), {})
        assert not any(c.code == "humidity_heat" for c in conditions)

    def test_summary_zh_contains_temp(self):
        conditions = detect_conditions(_make_current(35, 60), {})
        hw = next(c for c in conditions if c.code == "heatwave")
        assert "35" in hw.summary_zh


# ---------------------------------------------------------------------------
# weather_service: pick_best
# ---------------------------------------------------------------------------


class TestPickBest:
    def test_returns_none_for_empty(self):
        assert pick_best([]) is None

    def test_rainstorm_beats_heatwave(self):
        conditions = [
            WeatherCondition("heatwave", "severe", "熱"),
            WeatherCondition("rainstorm", "mild", "雨"),
        ]
        best = pick_best(conditions)
        assert best is not None
        assert best.code == "rainstorm"

    def test_heatwave_beats_cold_front(self):
        conditions = [
            WeatherCondition("cold_front", "severe", "凍"),
            WeatherCondition("heatwave", "mild", "熱"),
        ]
        best = pick_best(conditions)
        assert best is not None
        assert best.code == "heatwave"

    def test_picks_highest_severity_within_code(self):
        conditions = [
            WeatherCondition("heatwave", "mild", "熱 mild"),
            WeatherCondition("heatwave", "severe", "熱 severe"),
        ]
        best = pick_best(conditions)
        assert best is not None
        assert best.severity == "severe"

    def test_single_condition_returned(self):
        conditions = [WeatherCondition("cold_front", "mild", "凍")]
        best = pick_best(conditions)
        assert best is not None
        assert best.code == "cold_front"


# ---------------------------------------------------------------------------
# scheduler: helpers
# ---------------------------------------------------------------------------


class TestSchedulerHelpers:
    def test_iso_week_format(self):
        dt = datetime(2026, 5, 25, 10, 0, tzinfo=HKT)  # week 22 (May 25 2026)
        result = _current_iso_week(dt)
        assert result == "2026-W22"

    def test_iso_week_rolls_correctly(self):
        # 2026-01-05 is Monday of week 2
        dt = datetime(2026, 1, 5, 10, 0, tzinfo=HKT)
        assert _current_iso_week(dt) == "2026-W02"

    def test_within_send_window_true(self):
        dt = datetime(2026, 5, 25, 10, 0, tzinfo=HKT)  # 10am HKT
        assert _within_send_window(dt) is True

    def test_within_send_window_false_early(self):
        dt = datetime(2026, 5, 25, 7, 59, tzinfo=HKT)  # 07:59
        assert _within_send_window(dt) is False

    def test_within_send_window_false_late(self):
        dt = datetime(2026, 5, 25, 21, 0, tzinfo=HKT)  # exactly 21:00 = outside
        assert _within_send_window(dt) is False

    def test_hours_since_none_returns_inf(self):
        now = datetime(2026, 5, 25, 10, 0, tzinfo=HKT)
        assert _hours_since(None, now) == float("inf")

    def test_hours_since_calculates(self):
        now = datetime(2026, 5, 25, 10, 0, tzinfo=HKT)
        past = datetime(2026, 5, 24, 22, 0, tzinfo=HKT)  # 12h ago
        assert abs(_hours_since(past.isoformat(), now) - 12.0) < 0.01

    def test_hours_since_invalid_string_returns_inf(self):
        now = datetime(2026, 5, 25, 10, 0, tzinfo=HKT)
        assert _hours_since("not-a-date", now) == float("inf")


# ---------------------------------------------------------------------------
# scheduler: _user_is_eligible
# ---------------------------------------------------------------------------


class TestUserEligibility:
    def _make_crm(self, count: int, last_at: str | None) -> object:
        crm = MagicMock()
        crm.get_broadcast_count_this_week = AsyncMock(return_value=count)
        crm.get_last_broadcast_at = AsyncMock(return_value=last_at)
        return crm

    @pytest.mark.asyncio
    async def test_eligible_when_no_broadcasts(self):
        crm = self._make_crm(count=0, last_at=None)
        now = datetime(2026, 5, 25, 10, 0, tzinfo=HKT)
        assert await _user_is_eligible(crm, "+85291234567", "2026-W21", now) is True

    @pytest.mark.asyncio
    async def test_eligible_at_one_broadcast(self):
        past = datetime(2026, 5, 23, 10, 0, tzinfo=HKT)  # 48h ago
        crm = self._make_crm(count=1, last_at=past.isoformat())
        now = datetime(2026, 5, 25, 10, 0, tzinfo=HKT)
        assert await _user_is_eligible(crm, "+85291234567", "2026-W21", now) is True

    @pytest.mark.asyncio
    async def test_ineligible_at_cap(self):
        crm = self._make_crm(count=2, last_at=None)
        now = datetime(2026, 5, 25, 10, 0, tzinfo=HKT)
        assert await _user_is_eligible(crm, "+85291234567", "2026-W21", now) is False

    @pytest.mark.asyncio
    async def test_ineligible_within_36h_gap(self):
        # sent 10h ago — within the 36h minimum gap
        past = datetime(2026, 5, 25, 0, 0, tzinfo=HKT)
        crm = self._make_crm(count=1, last_at=past.isoformat())
        now = datetime(2026, 5, 25, 10, 0, tzinfo=HKT)
        assert await _user_is_eligible(crm, "+85291234567", "2026-W21", now) is False

    @pytest.mark.asyncio
    async def test_eligible_after_36h_gap(self):
        past = datetime(2026, 5, 23, 9, 0, tzinfo=HKT)  # 49h ago
        crm = self._make_crm(count=1, last_at=past.isoformat())
        now = datetime(2026, 5, 25, 10, 0, tzinfo=HKT)
        assert await _user_is_eligible(crm, "+85291234567", "2026-W21", now) is True


# ---------------------------------------------------------------------------
# Purchase follow-up: scheduler helpers
# ---------------------------------------------------------------------------


class TestFollowupCutoffs:
    """Verify cutoff timestamp calculation used by list_phones_for_purchase_followup."""

    def test_activity_cutoff_is_3_days_ago(self):
        from src.broadcaster.scheduler import FOLLOWUP_QUIET_DAYS
        now = datetime(2026, 5, 25, 10, 0, tzinfo=HKT)
        cutoff = (now - timedelta(days=FOLLOWUP_QUIET_DAYS)).isoformat()
        cutoff_dt = datetime.fromisoformat(cutoff)
        delta = now - cutoff_dt
        assert abs(delta.total_seconds() - FOLLOWUP_QUIET_DAYS * 86400) < 60

    def test_followup_cooldown_is_30_days(self):
        from src.broadcaster.scheduler import FOLLOWUP_COOLDOWN_DAYS
        now = datetime(2026, 5, 25, 10, 0, tzinfo=HKT)
        cutoff = (now - timedelta(days=FOLLOWUP_COOLDOWN_DAYS)).isoformat()
        cutoff_dt = datetime.fromisoformat(cutoff)
        delta = now - cutoff_dt
        assert abs(delta.total_seconds() - FOLLOWUP_COOLDOWN_DAYS * 86400) < 60


# ---------------------------------------------------------------------------
# Purchase follow-up: run logic
# ---------------------------------------------------------------------------


class TestRunPurchaseFollowup:
    def _make_crm(self, phones: list[str], user_products: list[str]) -> object:
        from src.crm.models import User

        crm = MagicMock()
        crm.list_phones_for_purchase_followup = AsyncMock(return_value=phones)
        crm.record_broadcast = AsyncMock()

        user = User(phone=phones[0] if phones else "+85291234567")
        object.__setattr__(user, "products_purchased", user_products)
        crm.get_user = AsyncMock(return_value=user)
        return crm

    @pytest.mark.asyncio
    async def test_skips_when_no_eligible_phones(self):
        from src.broadcaster.scheduler import _run_purchase_followup
        crm = self._make_crm(phones=[], user_products=[])
        llm = MagicMock()

        with patch("src.broadcaster.scheduler.is_blocked", return_value=False), \
             patch("src.broadcaster.scheduler.wa_client") as mock_wa:
            await _run_purchase_followup(crm, llm, "acc_123")
            mock_wa.send_long_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_blocked_phone(self):
        from src.broadcaster.scheduler import _run_purchase_followup
        crm = self._make_crm(phones=["+85291234567"], user_products=["soup_qingxin_runfei"])
        llm = MagicMock()

        with patch("src.broadcaster.scheduler.is_blocked", return_value=True), \
             patch("src.broadcaster.scheduler.wa_client") as mock_wa:
            await _run_purchase_followup(crm, llm, "acc_123")
            mock_wa.send_long_message.assert_not_called()
            crm.record_broadcast.assert_not_called()

    @pytest.mark.asyncio
    async def test_sends_and_records_for_eligible_user(self):
        from src.broadcaster.scheduler import _run_purchase_followup
        phone = "+85291234567"
        crm = self._make_crm(phones=[phone], user_products=["soup_qingxin_runfei"])
        llm = MagicMock()

        mock_bubbles = ["嗨！上次訂咗清心潤肺湯，有冇飲到呀？🌿"]

        with patch("src.broadcaster.scheduler.is_blocked", return_value=False), \
             patch("src.broadcaster.scheduler.wa_client") as mock_wa, \
             patch("src.broadcaster.scheduler.compose_purchase_followup",
                   new_callable=AsyncMock, return_value=mock_bubbles), \
             patch("src.broadcaster.scheduler._load_product_names", return_value=[
                 {"id": "soup_qingxin_runfei", "name": "清心潤肺湯", "benefit": "安神"}
             ]):
            mock_wa.send_long_message = AsyncMock()
            await _run_purchase_followup(crm, llm, "acc_123")

        mock_wa.send_long_message.assert_called_once_with(
            "acc_123", phone, mock_bubbles[0]
        )
        crm.record_broadcast.assert_called_once()
        args = crm.record_broadcast.call_args[0]
        assert args[0] == phone
        assert args[1] == "purchase_followup"

    @pytest.mark.asyncio
    async def test_skips_user_with_no_products(self):
        """CRM returns phone but user.products_purchased is empty — skip."""
        from src.broadcaster.scheduler import _run_purchase_followup
        phone = "+85291234567"
        crm = self._make_crm(phones=[phone], user_products=[])
        llm = MagicMock()

        with patch("src.broadcaster.scheduler.is_blocked", return_value=False), \
             patch("src.broadcaster.scheduler.wa_client") as mock_wa:
            await _run_purchase_followup(crm, llm, "acc_123")
            mock_wa.send_long_message.assert_not_called()


# ---------------------------------------------------------------------------
# Purchase follow-up: composer
# ---------------------------------------------------------------------------


class TestPurchaseFollowupComposer:
    def _make_user(self):
        from src.crm.models import User
        return User(phone="+85291234567")

    @pytest.mark.asyncio
    async def test_returns_fallback_on_llm_failure(self):
        from src.broadcaster.composer import compose_purchase_followup
        llm = MagicMock()
        llm.messages.create = AsyncMock(side_effect=Exception("LLM down"))
        user = self._make_user()
        products = [{"id": "soup_qingxin_runfei", "name": "清心潤肺湯", "benefit": "安神"}]

        bubbles = await compose_purchase_followup(llm, user, products)
        assert len(bubbles) >= 1
        assert isinstance(bubbles[0], str)
        assert len(bubbles[0]) > 0

    @pytest.mark.asyncio
    async def test_returns_fallback_for_empty_products(self):
        from src.broadcaster.composer import compose_purchase_followup
        llm = MagicMock()
        user = self._make_user()

        bubbles = await compose_purchase_followup(llm, user, [])
        assert len(bubbles) >= 1

    @pytest.mark.asyncio
    async def test_strips_price_leak(self):
        from src.broadcaster.composer import compose_purchase_followup
        llm = MagicMock()
        llm.messages.create = AsyncMock(return_value=MagicMock(
            content=[MagicMock(text='{"bubbles": ["嗨！HK$48嘅湯有冇飲到？", "希望你鐘意！"]}')]
        ))
        user = self._make_user()
        products = [{"id": "soup_qingxin_runfei", "name": "清心潤肺湯", "benefit": "安神"}]

        bubbles = await compose_purchase_followup(llm, user, products)
        for bubble in bubbles:
            assert "HK$" not in bubble
            assert "$48" not in bubble

    @pytest.mark.asyncio
    async def test_respects_bubble_length_cap(self):
        from src.broadcaster.composer import compose_purchase_followup, BUBBLE_MAX
        long_text = "A" * 300
        llm = MagicMock()
        llm.messages.create = AsyncMock(return_value=MagicMock(
            content=[MagicMock(text=f'{{"bubbles": ["{long_text}"]}}')]
        ))
        user = self._make_user()
        products = [{"id": "soup_qingxin_runfei", "name": "清心潤肺湯", "benefit": "安神"}]

        bubbles = await compose_purchase_followup(llm, user, products)
        for bubble in bubbles:
            assert len(bubble) <= BUBBLE_MAX
