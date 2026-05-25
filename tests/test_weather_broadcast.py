"""Tests for the proactive weather broadcast feature.

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
