"""Tests for the proactive broadcast features:
  - weather_service: condition detection (pure)
  - scheduler: eligibility, weather cap, purchase followup
  - solar_terms: detection + dedup key
  - constitution_recheck: cutoffs

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
             patch("src.broadcaster.scheduler._within_send_window", return_value=True), \
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


# ---------------------------------------------------------------------------
# Solar terms: detection (pure)
# ---------------------------------------------------------------------------


class TestSolarTermDetection:
    def test_detects_term_on_exact_date(self):
        from src.broadcaster.solar_terms import get_active_solar_term
        from datetime import date
        # 小滿 is 2026-05-21
        result = get_active_solar_term(date(2026, 5, 21))
        assert result is not None
        assert result.name_zh == "小滿"

    def test_detects_term_one_day_before(self):
        from src.broadcaster.solar_terms import get_active_solar_term
        from datetime import date
        result = get_active_solar_term(date(2026, 5, 20))
        assert result is not None
        assert result.name_zh == "小滿"

    def test_detects_term_two_days_after(self):
        from src.broadcaster.solar_terms import get_active_solar_term
        from datetime import date
        result = get_active_solar_term(date(2026, 5, 23))
        assert result is not None
        assert result.name_zh == "小滿"

    def test_no_term_far_from_any_date(self):
        from src.broadcaster.solar_terms import get_active_solar_term
        from datetime import date
        # May 10 is between 立夏 (May 6) and 小滿 (May 21) — ~9 days from either
        result = get_active_solar_term(date(2026, 5, 10))
        assert result is None

    def test_condition_code_format(self):
        from src.broadcaster.solar_terms import get_active_solar_term, solar_term_condition_code_for_year
        from datetime import date
        term = get_active_solar_term(date(2026, 12, 22))  # 冬至
        assert term is not None
        code = solar_term_condition_code_for_year(term, 2026)
        assert code == "solar_dongzhi_2026"

    def test_all_24_terms_have_dates(self):
        from src.broadcaster.solar_terms import SOLAR_TERMS
        assert len(SOLAR_TERMS) == 24
        for term in SOLAR_TERMS:
            assert len(term.dates) >= 1
            assert term.name_zh
            assert term.season_tip_zh
            assert term.organ_zh

    def test_different_years_give_different_codes(self):
        from src.broadcaster.solar_terms import SOLAR_TERMS, solar_term_condition_code_for_year
        term = SOLAR_TERMS[0]
        assert solar_term_condition_code_for_year(term, 2026) != solar_term_condition_code_for_year(term, 2027)

    def test_detection_window_boundary(self):
        from src.broadcaster.solar_terms import get_active_solar_term, DETECTION_WINDOW_DAYS
        from datetime import date, timedelta
        # Exactly at the boundary — day of + DETECTION_WINDOW_DAYS should still match
        term_date = date(2026, 6, 21)  # 夏至
        edge = term_date + timedelta(days=DETECTION_WINDOW_DAYS)
        result = get_active_solar_term(edge)
        assert result is not None
        assert result.name_zh == "夏至"

    def test_just_outside_window_returns_none(self):
        from src.broadcaster.solar_terms import get_active_solar_term, DETECTION_WINDOW_DAYS
        from datetime import date, timedelta
        term_date = date(2026, 6, 21)  # 夏至
        outside = term_date + timedelta(days=DETECTION_WINDOW_DAYS + 1)
        result = get_active_solar_term(outside)
        # Should not be 夏至 (芒種 ends, 夏至 hasn't started for next year)
        if result is not None:
            assert result.name_zh != "夏至"


# ---------------------------------------------------------------------------
# Constitution recheck: cutoff helpers
# ---------------------------------------------------------------------------


class TestConstitutionRecheckCutoffs:
    def test_recheck_cutoff_is_90_days(self):
        from src.broadcaster.scheduler import RECHECK_COOLDOWN_DAYS
        now = datetime(2026, 5, 25, 10, 0, tzinfo=HKT)
        cutoff = (now - timedelta(days=RECHECK_COOLDOWN_DAYS)).isoformat()
        delta = now - datetime.fromisoformat(cutoff)
        assert abs(delta.total_seconds() - RECHECK_COOLDOWN_DAYS * 86400) < 60

    def test_activity_gap_is_7_days(self):
        from src.broadcaster.scheduler import RECHECK_ACTIVITY_GAP_DAYS
        now = datetime(2026, 5, 25, 10, 0, tzinfo=HKT)
        cutoff = (now - timedelta(days=RECHECK_ACTIVITY_GAP_DAYS)).isoformat()
        delta = now - datetime.fromisoformat(cutoff)
        assert abs(delta.total_seconds() - RECHECK_ACTIVITY_GAP_DAYS * 86400) < 60


# ---------------------------------------------------------------------------
# Constitution recheck composer: fallback
# ---------------------------------------------------------------------------


class TestConstitutionRecheckComposer:
    def _make_user(self, constitution: str = "氣虛"):
        from src.crm.models import User, Constitution
        u = User(phone="+85291234567")
        # Set constitution via field
        object.__setattr__(u, "constitution", Constitution(constitution) if constitution in [c.value for c in Constitution] else u.constitution)
        return u

    @pytest.mark.asyncio
    async def test_fallback_on_llm_failure(self):
        from src.broadcaster.composer import compose_constitution_recheck
        llm = MagicMock()
        llm.messages.create = AsyncMock(side_effect=Exception("LLM down"))
        user = self._make_user()
        bubbles = await compose_constitution_recheck(llm, user)
        assert len(bubbles) >= 1
        assert all(isinstance(b, str) and len(b) > 0 for b in bubbles)

    @pytest.mark.asyncio
    async def test_no_price_in_output(self):
        from src.broadcaster.composer import compose_constitution_recheck
        llm = MagicMock()
        llm.messages.create = AsyncMock(return_value=MagicMock(
            content=[MagicMock(text='{"bubbles": ["嗨！體質評估 HK$50 再做一次？", "謝謝！"]}')]
        ))
        user = self._make_user()
        bubbles = await compose_constitution_recheck(llm, user)
        for b in bubbles:
            assert "HK$" not in b


# ---------------------------------------------------------------------------
# Weekly tea tip: composer + scheduler
# ---------------------------------------------------------------------------


class TestWeeklyTeaComposer:
    def _make_user(self):
        from src.crm.models import User
        return User(phone="+85291234567")

    @pytest.mark.asyncio
    async def test_fallback_on_llm_failure(self):
        from src.broadcaster.composer import compose_weekly_tea_tip
        llm = MagicMock()
        llm.messages.create = AsyncMock(side_effect=Exception("LLM down"))
        user = self._make_user()
        bubbles = await compose_weekly_tea_tip(llm, user)
        assert len(bubbles) >= 1
        assert all(isinstance(b, str) and len(b) > 0 for b in bubbles)

    @pytest.mark.asyncio
    async def test_strips_price_leak(self):
        from src.broadcaster.composer import compose_weekly_tea_tip
        llm = MagicMock()
        llm.messages.create = AsyncMock(return_value=MagicMock(
            content=[MagicMock(text='{"bubbles": ["今週茶療 HK$48 一包", "好飲！"]}')]
        ))
        user = self._make_user()
        bubbles = await compose_weekly_tea_tip(llm, user)
        for b in bubbles:
            assert "HK$" not in b

    @pytest.mark.asyncio
    async def test_respects_bubble_length_cap(self):
        from src.broadcaster.composer import compose_weekly_tea_tip, BUBBLE_MAX
        long_text = "A" * 300
        llm = MagicMock()
        llm.messages.create = AsyncMock(return_value=MagicMock(
            content=[MagicMock(text=f'{{"bubbles": ["{long_text}"]}}')]
        ))
        user = self._make_user()
        bubbles = await compose_weekly_tea_tip(llm, user)
        for b in bubbles:
            assert len(b) <= BUBBLE_MAX

    @pytest.mark.asyncio
    async def test_max_two_bubbles(self):
        from src.broadcaster.composer import compose_weekly_tea_tip
        llm = MagicMock()
        llm.messages.create = AsyncMock(return_value=MagicMock(
            content=[MagicMock(text='{"bubbles": ["第一條", "第二條", "第三條"]}')]
        ))
        user = self._make_user()
        bubbles = await compose_weekly_tea_tip(llm, user)
        assert len(bubbles) <= 2

    @pytest.mark.asyncio
    async def test_returns_fallback_on_empty_bubbles(self):
        from src.broadcaster.composer import compose_weekly_tea_tip
        llm = MagicMock()
        llm.messages.create = AsyncMock(return_value=MagicMock(
            content=[MagicMock(text='{"bubbles": []}')]
        ))
        user = self._make_user()
        bubbles = await compose_weekly_tea_tip(llm, user)
        assert len(bubbles) >= 1

    @pytest.mark.asyncio
    async def test_happy_path_returns_llm_bubbles(self):
        from src.broadcaster.composer import compose_weekly_tea_tip
        llm = MagicMock()
        llm.messages.create = AsyncMock(return_value=MagicMock(
            content=[MagicMock(text='{"bubbles": ["今週飲紅棗枸杞茶養血補氣 🍵"]}')]
        ))
        user = self._make_user()
        bubbles = await compose_weekly_tea_tip(llm, user)
        assert bubbles == ["今週飲紅棗枸杞茶養血補氣 🍵"]


class TestRunWeeklyTea:
    def _make_crm(self, phones, already_sent=0):
        from src.crm.models import User
        crm = MagicMock()
        crm.list_active_phones = AsyncMock(return_value=phones)
        crm.get_broadcast_count_this_week = AsyncMock(return_value=already_sent)
        crm.record_broadcast = AsyncMock()
        if phones:
            user = User(phone=phones[0])
            crm.get_user = AsyncMock(return_value=user)
        else:
            crm.get_user = AsyncMock(return_value=None)
        return crm

    @pytest.mark.asyncio
    async def test_skips_blocked_phone(self):
        from src.broadcaster.scheduler import _run_weekly_tea
        crm = self._make_crm(["+85291234567"])
        with patch("src.broadcaster.scheduler.is_blocked", return_value=True), \
             patch("src.broadcaster.scheduler._within_send_window", return_value=True), \
             patch("src.broadcaster.scheduler.wa_client") as mock_wa:
            mock_wa.send_long_message = AsyncMock()
            await _run_weekly_tea(crm, MagicMock(), "acc_123")
        mock_wa.send_long_message.assert_not_called()
        crm.record_broadcast.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_already_sent_this_week(self):
        from src.broadcaster.scheduler import _run_weekly_tea
        crm = self._make_crm(["+85291234567"], already_sent=1)
        with patch("src.broadcaster.scheduler.is_blocked", return_value=False), \
             patch("src.broadcaster.scheduler._within_send_window", return_value=True), \
             patch("src.broadcaster.scheduler.wa_client") as mock_wa:
            mock_wa.send_long_message = AsyncMock()
            await _run_weekly_tea(crm, MagicMock(), "acc_123")
        mock_wa.send_long_message.assert_not_called()
        crm.record_broadcast.assert_not_called()

    @pytest.mark.asyncio
    async def test_sends_and_records_for_eligible_user(self):
        from src.broadcaster.scheduler import _run_weekly_tea
        phone = "+85291234567"
        crm = self._make_crm([phone], already_sent=0)
        mock_bubbles = ["今週飲紅棗枸杞茶養血補氣 🍵"]
        with patch("src.broadcaster.scheduler.is_blocked", return_value=False), \
             patch("src.broadcaster.scheduler._within_send_window", return_value=True), \
             patch("src.broadcaster.scheduler.wa_client") as mock_wa, \
             patch("src.broadcaster.scheduler.compose_weekly_tea_tip",
                   new_callable=AsyncMock, return_value=mock_bubbles):
            mock_wa.send_long_message = AsyncMock()
            await _run_weekly_tea(crm, MagicMock(), "acc_123")
        mock_wa.send_long_message.assert_called_once()
        crm.record_broadcast.assert_called_once()
        args = crm.record_broadcast.call_args[0]
        assert args[1] == "weekly_tea"
        assert args[2].startswith("tea-")

    @pytest.mark.asyncio
    async def test_dedup_key_uses_correct_prefix(self):
        from src.broadcaster.scheduler import _run_weekly_tea
        phone = "+85291234567"
        crm = self._make_crm([phone], already_sent=0)
        with patch("src.broadcaster.scheduler.is_blocked", return_value=False), \
             patch("src.broadcaster.scheduler._within_send_window", return_value=True), \
             patch("src.broadcaster.scheduler.wa_client") as mock_wa, \
             patch("src.broadcaster.scheduler.compose_weekly_tea_tip",
                   new_callable=AsyncMock, return_value=["tip"]):
            mock_wa.send_long_message = AsyncMock()
            await _run_weekly_tea(crm, MagicMock(), "acc_123")
        call_args = crm.get_broadcast_count_this_week.call_args[0]
        assert call_args[1].startswith("tea-")


# ---------------------------------------------------------------------------
# Weekly acupressure tip: composer + scheduler
# ---------------------------------------------------------------------------


class TestWeeklyAcupressureComposer:
    def _make_user(self, pain_points=None, tags=None):
        from src.crm.models import User
        u = User(phone="+85291234567")
        if pain_points is not None:
            object.__setattr__(u, "pain_points", pain_points)
        if tags is not None:
            object.__setattr__(u, "tags", tags)
        return u

    @pytest.mark.asyncio
    async def test_fallback_on_llm_failure(self):
        from src.broadcaster.composer import compose_weekly_acupressure_tip
        llm = MagicMock()
        llm.messages.create = AsyncMock(side_effect=Exception("LLM down"))
        user = self._make_user()
        bubbles = await compose_weekly_acupressure_tip(llm, user)
        assert len(bubbles) >= 1
        assert all(isinstance(b, str) and len(b) > 0 for b in bubbles)

    @pytest.mark.asyncio
    async def test_strips_price_leak(self):
        from src.broadcaster.composer import compose_weekly_acupressure_tip
        llm = MagicMock()
        llm.messages.create = AsyncMock(return_value=MagicMock(
            content=[MagicMock(text='{"bubbles": ["按摩套餐 HK$48 包搞掂", "好正！"]}')]
        ))
        user = self._make_user()
        bubbles = await compose_weekly_acupressure_tip(llm, user)
        for b in bubbles:
            assert "HK$" not in b

    @pytest.mark.asyncio
    async def test_respects_bubble_length_cap(self):
        from src.broadcaster.composer import compose_weekly_acupressure_tip, BUBBLE_MAX
        long_text = "A" * 300
        llm = MagicMock()
        llm.messages.create = AsyncMock(return_value=MagicMock(
            content=[MagicMock(text=f'{{"bubbles": ["{long_text}"]}}')]
        ))
        user = self._make_user()
        bubbles = await compose_weekly_acupressure_tip(llm, user)
        for b in bubbles:
            assert len(b) <= BUBBLE_MAX

    @pytest.mark.asyncio
    async def test_max_two_bubbles(self):
        from src.broadcaster.composer import compose_weekly_acupressure_tip
        llm = MagicMock()
        llm.messages.create = AsyncMock(return_value=MagicMock(
            content=[MagicMock(text='{"bubbles": ["第一條", "第二條", "第三條"]}')]
        ))
        user = self._make_user()
        bubbles = await compose_weekly_acupressure_tip(llm, user)
        assert len(bubbles) <= 2

    @pytest.mark.asyncio
    async def test_returns_fallback_on_empty_bubbles(self):
        from src.broadcaster.composer import compose_weekly_acupressure_tip
        llm = MagicMock()
        llm.messages.create = AsyncMock(return_value=MagicMock(
            content=[MagicMock(text='{"bubbles": []}')]
        ))
        user = self._make_user()
        bubbles = await compose_weekly_acupressure_tip(llm, user)
        assert len(bubbles) >= 1

    @pytest.mark.asyncio
    async def test_happy_path_returns_llm_bubbles(self):
        from src.broadcaster.composer import compose_weekly_acupressure_tip
        llm = MagicMock()
        llm.messages.create = AsyncMock(return_value=MagicMock(
            content=[MagicMock(text='{"bubbles": ["今週穴位：神門穴 🤚"]}')]
        ))
        user = self._make_user()
        bubbles = await compose_weekly_acupressure_tip(llm, user)
        assert bubbles == ["今週穴位：神門穴 🤚"]


class TestWeeklyAcupressureScheduler:
    def _make_crm(self, phones, already_sent=0):
        from src.crm.models import User
        crm = MagicMock()
        crm.list_active_phones = AsyncMock(return_value=phones)
        crm.get_broadcast_count_this_week = AsyncMock(return_value=already_sent)
        crm.record_broadcast = AsyncMock()
        if phones:
            user = User(phone=phones[0])
            crm.get_user = AsyncMock(return_value=user)
        else:
            crm.get_user = AsyncMock(return_value=None)
        return crm

    @pytest.mark.asyncio
    async def test_skips_blocked_phone(self):
        from src.broadcaster.scheduler import _run_weekly_acupressure
        crm = self._make_crm(["+85291234567"])
        with patch("src.broadcaster.scheduler.is_blocked", return_value=True), \
             patch("src.broadcaster.scheduler._within_send_window", return_value=True), \
             patch("src.broadcaster.scheduler.wa_client") as mock_wa:
            mock_wa.send_long_message = AsyncMock()
            await _run_weekly_acupressure(crm, MagicMock(), "acc_123")
        mock_wa.send_long_message.assert_not_called()
        crm.record_broadcast.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_already_sent_this_week(self):
        from src.broadcaster.scheduler import _run_weekly_acupressure
        crm = self._make_crm(["+85291234567"], already_sent=1)
        with patch("src.broadcaster.scheduler.is_blocked", return_value=False), \
             patch("src.broadcaster.scheduler._within_send_window", return_value=True), \
             patch("src.broadcaster.scheduler.wa_client") as mock_wa:
            mock_wa.send_long_message = AsyncMock()
            await _run_weekly_acupressure(crm, MagicMock(), "acc_123")
        mock_wa.send_long_message.assert_not_called()
        crm.record_broadcast.assert_not_called()

    @pytest.mark.asyncio
    async def test_sends_and_records_for_eligible_user(self):
        from src.broadcaster.scheduler import _run_weekly_acupressure
        phone = "+85291234567"
        crm = self._make_crm([phone], already_sent=0)
        mock_bubbles = ["今週穴位：神門穴 🤚"]
        with patch("src.broadcaster.scheduler.is_blocked", return_value=False), \
             patch("src.broadcaster.scheduler._within_send_window", return_value=True), \
             patch("src.broadcaster.scheduler.wa_client") as mock_wa, \
             patch("src.broadcaster.scheduler.compose_weekly_acupressure_tip",
                   new_callable=AsyncMock, return_value=mock_bubbles):
            mock_wa.send_long_message = AsyncMock()
            await _run_weekly_acupressure(crm, MagicMock(), "acc_123")
        mock_wa.send_long_message.assert_called_once()
        crm.record_broadcast.assert_called_once()
        args = crm.record_broadcast.call_args[0]
        assert args[1] == "weekly_acupressure"
        assert args[2].startswith("acupressure-")

    @pytest.mark.asyncio
    async def test_dedup_key_uses_correct_prefix(self):
        from src.broadcaster.scheduler import _run_weekly_acupressure
        phone = "+85291234567"
        crm = self._make_crm([phone], already_sent=0)
        with patch("src.broadcaster.scheduler.is_blocked", return_value=False), \
             patch("src.broadcaster.scheduler._within_send_window", return_value=True), \
             patch("src.broadcaster.scheduler.wa_client") as mock_wa, \
             patch("src.broadcaster.scheduler.compose_weekly_acupressure_tip",
                   new_callable=AsyncMock, return_value=["tip"]):
            mock_wa.send_long_message = AsyncMock()
            await _run_weekly_acupressure(crm, MagicMock(), "acc_123")
        call_args = crm.get_broadcast_count_this_week.call_args[0]
        assert call_args[1].startswith("acupressure-")


# ---------------------------------------------------------------------------
# Appointment prep: composer + scheduler
# ---------------------------------------------------------------------------


class TestAppointmentPrepComposer:
    def _make_user(self):
        from src.crm.models import User
        return User(phone="+85291234567")

    @pytest.mark.asyncio
    async def test_fallback_on_llm_failure(self):
        from src.broadcaster.composer import compose_appointment_prep
        llm = MagicMock()
        llm.messages.create = AsyncMock(side_effect=Exception("LLM down"))
        user = self._make_user()
        bubbles = await compose_appointment_prep(llm, user)
        assert len(bubbles) >= 1
        assert all(isinstance(b, str) and len(b) > 0 for b in bubbles)

    @pytest.mark.asyncio
    async def test_strips_price_leak(self):
        from src.broadcaster.composer import compose_appointment_prep
        llm = MagicMock()
        llm.messages.create = AsyncMock(return_value=MagicMock(
            content=[MagicMock(text='{"bubbles": ["覆診費 HK$48 記得帶", "加油！"]}')]
        ))
        user = self._make_user()
        bubbles = await compose_appointment_prep(llm, user)
        for b in bubbles:
            assert "HK$" not in b

    @pytest.mark.asyncio
    async def test_respects_bubble_length_cap(self):
        from src.broadcaster.composer import compose_appointment_prep, BUBBLE_MAX
        long_text = "A" * 300
        llm = MagicMock()
        llm.messages.create = AsyncMock(return_value=MagicMock(
            content=[MagicMock(text=f'{{"bubbles": ["{long_text}"]}}')]
        ))
        user = self._make_user()
        bubbles = await compose_appointment_prep(llm, user)
        for b in bubbles:
            assert len(b) <= BUBBLE_MAX

    @pytest.mark.asyncio
    async def test_max_two_bubbles(self):
        from src.broadcaster.composer import compose_appointment_prep
        llm = MagicMock()
        llm.messages.create = AsyncMock(return_value=MagicMock(
            content=[MagicMock(text='{"bubbles": ["第一條", "第二條", "第三條"]}')]
        ))
        user = self._make_user()
        bubbles = await compose_appointment_prep(llm, user)
        assert len(bubbles) <= 2

    @pytest.mark.asyncio
    async def test_returns_fallback_on_empty_bubbles(self):
        from src.broadcaster.composer import compose_appointment_prep
        llm = MagicMock()
        llm.messages.create = AsyncMock(return_value=MagicMock(
            content=[MagicMock(text='{"bubbles": []}')]
        ))
        user = self._make_user()
        bubbles = await compose_appointment_prep(llm, user)
        assert len(bubbles) >= 1

    @pytest.mark.asyncio
    async def test_happy_path_returns_llm_bubbles(self):
        from src.broadcaster.composer import compose_appointment_prep
        llm = MagicMock()
        llm.messages.create = AsyncMock(return_value=MagicMock(
            content=[MagicMock(text='{"bubbles": ["快到見醫師喇，記得唔使空腹 🌿"]}')]
        ))
        user = self._make_user()
        bubbles = await compose_appointment_prep(llm, user)
        assert bubbles == ["快到見醫師喇，記得唔使空腹 🌿"]


class TestAppointmentPrepScheduler:
    def _make_crm(self, phones, already_sent=0):
        from src.crm.models import User
        crm = MagicMock()
        crm.list_phones_for_upcoming_appointments = AsyncMock(return_value=phones)
        crm.get_broadcast_count_this_week = AsyncMock(return_value=already_sent)
        crm.record_broadcast = AsyncMock()
        if phones:
            user = User(phone=phones[0])
            crm.get_user = AsyncMock(return_value=user)
        else:
            crm.get_user = AsyncMock(return_value=None)
        return crm

    @pytest.mark.asyncio
    async def test_skips_blocked_phone(self):
        from src.broadcaster.scheduler import _run_appointment_prep
        crm = self._make_crm(["+85291234567"])
        with patch("src.broadcaster.scheduler.is_blocked", return_value=True), \
             patch("src.broadcaster.scheduler._within_send_window", return_value=True), \
             patch("src.broadcaster.scheduler.wa_client") as mock_wa:
            mock_wa.send_long_message = AsyncMock()
            await _run_appointment_prep(crm, MagicMock(), "acc_123")
        mock_wa.send_long_message.assert_not_called()
        crm.record_broadcast.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_already_sent_this_week(self):
        from src.broadcaster.scheduler import _run_appointment_prep
        crm = self._make_crm(["+85291234567"], already_sent=1)
        with patch("src.broadcaster.scheduler.is_blocked", return_value=False), \
             patch("src.broadcaster.scheduler._within_send_window", return_value=True), \
             patch("src.broadcaster.scheduler.wa_client") as mock_wa:
            mock_wa.send_long_message = AsyncMock()
            await _run_appointment_prep(crm, MagicMock(), "acc_123")
        mock_wa.send_long_message.assert_not_called()
        crm.record_broadcast.assert_not_called()

    @pytest.mark.asyncio
    async def test_sends_and_records_for_eligible_user(self):
        from src.broadcaster.scheduler import _run_appointment_prep
        phone = "+85291234567"
        crm = self._make_crm([phone], already_sent=0)
        mock_bubbles = ["快到見醫師喇，記得唔使空腹 🌿"]
        with patch("src.broadcaster.scheduler.is_blocked", return_value=False), \
             patch("src.broadcaster.scheduler._within_send_window", return_value=True), \
             patch("src.broadcaster.scheduler.wa_client") as mock_wa, \
             patch("src.broadcaster.scheduler.compose_appointment_prep",
                   new_callable=AsyncMock, return_value=mock_bubbles):
            mock_wa.send_long_message = AsyncMock()
            await _run_appointment_prep(crm, MagicMock(), "acc_123")
        mock_wa.send_long_message.assert_called_once()
        crm.record_broadcast.assert_called_once()
        args = crm.record_broadcast.call_args[0]
        assert args[1] == "appointment_prep"
        assert args[2].startswith("appt-prep-")

    @pytest.mark.asyncio
    async def test_dedup_key_uses_correct_prefix(self):
        from src.broadcaster.scheduler import _run_appointment_prep
        phone = "+85291234567"
        crm = self._make_crm([phone], already_sent=0)
        with patch("src.broadcaster.scheduler.is_blocked", return_value=False), \
             patch("src.broadcaster.scheduler._within_send_window", return_value=True), \
             patch("src.broadcaster.scheduler.wa_client") as mock_wa, \
             patch("src.broadcaster.scheduler.compose_appointment_prep",
                   new_callable=AsyncMock, return_value=["tip"]):
            mock_wa.send_long_message = AsyncMock()
            await _run_appointment_prep(crm, MagicMock(), "acc_123")
        call_args = crm.get_broadcast_count_this_week.call_args[0]
        assert call_args[1].startswith("appt-prep-")


# ---------------------------------------------------------------------------
# Monthly food tip: composer + scheduler
# ---------------------------------------------------------------------------


class TestMonthlyFoodTipComposer:
    def _make_user(self):
        from src.crm.models import User
        return User(phone="+85291234567")

    @pytest.mark.asyncio
    async def test_fallback_on_llm_failure(self):
        from src.broadcaster.composer import compose_monthly_food_tip
        llm = MagicMock()
        llm.messages.create = AsyncMock(side_effect=Exception("LLM down"))
        user = self._make_user()
        bubbles = await compose_monthly_food_tip(llm, user, month=6)
        assert len(bubbles) >= 1
        assert all(isinstance(b, str) and len(b) > 0 for b in bubbles)

    @pytest.mark.asyncio
    async def test_strips_price_leak(self):
        from src.broadcaster.composer import compose_monthly_food_tip
        llm = MagicMock()
        llm.messages.create = AsyncMock(return_value=MagicMock(
            content=[MagicMock(text='{"bubbles": ["今月食療套餐 HK$48", "好正！"]}')]
        ))
        user = self._make_user()
        bubbles = await compose_monthly_food_tip(llm, user, month=6)
        for b in bubbles:
            assert "HK$" not in b

    @pytest.mark.asyncio
    async def test_respects_bubble_length_cap(self):
        from src.broadcaster.composer import compose_monthly_food_tip, BUBBLE_MAX
        long_text = "A" * 300
        llm = MagicMock()
        llm.messages.create = AsyncMock(return_value=MagicMock(
            content=[MagicMock(text=f'{{"bubbles": ["{long_text}"]}}')]
        ))
        user = self._make_user()
        bubbles = await compose_monthly_food_tip(llm, user, month=3)
        for b in bubbles:
            assert len(b) <= BUBBLE_MAX

    @pytest.mark.asyncio
    async def test_max_two_bubbles(self):
        from src.broadcaster.composer import compose_monthly_food_tip
        llm = MagicMock()
        llm.messages.create = AsyncMock(return_value=MagicMock(
            content=[MagicMock(text='{"bubbles": ["第一條", "第二條", "第三條"]}')]
        ))
        user = self._make_user()
        bubbles = await compose_monthly_food_tip(llm, user, month=10)
        assert len(bubbles) <= 2

    @pytest.mark.asyncio
    async def test_returns_fallback_on_empty_bubbles(self):
        from src.broadcaster.composer import compose_monthly_food_tip
        llm = MagicMock()
        llm.messages.create = AsyncMock(return_value=MagicMock(
            content=[MagicMock(text='{"bubbles": []}')]
        ))
        user = self._make_user()
        bubbles = await compose_monthly_food_tip(llm, user, month=12)
        assert len(bubbles) >= 1

    @pytest.mark.asyncio
    async def test_happy_path_returns_llm_bubbles(self):
        from src.broadcaster.composer import compose_monthly_food_tip
        llm = MagicMock()
        llm.messages.create = AsyncMock(return_value=MagicMock(
            content=[MagicMock(text='{"bubbles": ["今月宜多食梨同百合潤肺 🍐"]}')]
        ))
        user = self._make_user()
        bubbles = await compose_monthly_food_tip(llm, user, month=10)
        assert bubbles == ["今月宜多食梨同百合潤肺 🍐"]


class TestMonthlyFoodTipScheduler:
    def _make_crm(self, phones, already_sent=0):
        from src.crm.models import User
        crm = MagicMock()
        crm.list_active_phones = AsyncMock(return_value=phones)
        crm.get_broadcast_count_this_week = AsyncMock(return_value=already_sent)
        crm.record_broadcast = AsyncMock()
        if phones:
            user = User(phone=phones[0])
            crm.get_user = AsyncMock(return_value=user)
        else:
            crm.get_user = AsyncMock(return_value=None)
        return crm

    @pytest.mark.asyncio
    async def test_skips_blocked_phone(self):
        from src.broadcaster.scheduler import _run_monthly_food_tip
        crm = self._make_crm(["+85291234567"])
        with patch("src.broadcaster.scheduler.is_blocked", return_value=True), \
             patch("src.broadcaster.scheduler._within_send_window", return_value=True), \
             patch("src.broadcaster.scheduler.wa_client") as mock_wa:
            mock_wa.send_long_message = AsyncMock()
            await _run_monthly_food_tip(crm, MagicMock(), "acc_123")
        mock_wa.send_long_message.assert_not_called()
        crm.record_broadcast.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_already_sent_this_week(self):
        from src.broadcaster.scheduler import _run_monthly_food_tip
        crm = self._make_crm(["+85291234567"], already_sent=1)
        with patch("src.broadcaster.scheduler.is_blocked", return_value=False), \
             patch("src.broadcaster.scheduler._within_send_window", return_value=True), \
             patch("src.broadcaster.scheduler.wa_client") as mock_wa:
            mock_wa.send_long_message = AsyncMock()
            await _run_monthly_food_tip(crm, MagicMock(), "acc_123")
        mock_wa.send_long_message.assert_not_called()
        crm.record_broadcast.assert_not_called()

    @pytest.mark.asyncio
    async def test_sends_and_records_for_eligible_user(self):
        from src.broadcaster.scheduler import _run_monthly_food_tip
        phone = "+85291234567"
        crm = self._make_crm([phone], already_sent=0)
        mock_bubbles = ["今月宜多食梨同百合潤肺 🍐"]
        with patch("src.broadcaster.scheduler.is_blocked", return_value=False), \
             patch("src.broadcaster.scheduler._within_send_window", return_value=True), \
             patch("src.broadcaster.scheduler.wa_client") as mock_wa, \
             patch("src.broadcaster.scheduler.compose_monthly_food_tip",
                   new_callable=AsyncMock, return_value=mock_bubbles):
            mock_wa.send_long_message = AsyncMock()
            await _run_monthly_food_tip(crm, MagicMock(), "acc_123")
        mock_wa.send_long_message.assert_called_once()
        crm.record_broadcast.assert_called_once()
        args = crm.record_broadcast.call_args[0]
        assert args[1] == "monthly_food_tip"
        assert args[2].startswith("food-")

    @pytest.mark.asyncio
    async def test_dedup_key_uses_correct_prefix(self):
        from src.broadcaster.scheduler import _run_monthly_food_tip
        phone = "+85291234567"
        crm = self._make_crm([phone], already_sent=0)
        with patch("src.broadcaster.scheduler.is_blocked", return_value=False), \
             patch("src.broadcaster.scheduler._within_send_window", return_value=True), \
             patch("src.broadcaster.scheduler.wa_client") as mock_wa, \
             patch("src.broadcaster.scheduler.compose_monthly_food_tip",
                   new_callable=AsyncMock, return_value=["tip"]):
            mock_wa.send_long_message = AsyncMock()
            await _run_monthly_food_tip(crm, MagicMock(), "acc_123")
        call_args = crm.get_broadcast_count_this_week.call_args[0]
        assert call_args[1].startswith("food-")


# ---------------------------------------------------------------------------
# Weekly sleep tip: composer + scheduler
# ---------------------------------------------------------------------------


class TestWeeklySleepTipComposer:
    def _make_user(self):
        from src.crm.models import User
        return User(phone="+85291234567")

    @pytest.mark.asyncio
    async def test_fallback_on_llm_failure(self):
        from src.broadcaster.composer import compose_weekly_sleep_tip
        llm = MagicMock()
        llm.messages.create = AsyncMock(side_effect=Exception("LLM down"))
        user = self._make_user()
        bubbles = await compose_weekly_sleep_tip(llm, user)
        assert len(bubbles) >= 1
        assert all(isinstance(b, str) and len(b) > 0 for b in bubbles)

    @pytest.mark.asyncio
    async def test_strips_price_leak(self):
        from src.broadcaster.composer import compose_weekly_sleep_tip
        llm = MagicMock()
        llm.messages.create = AsyncMock(return_value=MagicMock(
            content=[MagicMock(text='{"bubbles": ["睡眠套餐 HK$48 包好瞓", "正！"]}')]
        ))
        user = self._make_user()
        bubbles = await compose_weekly_sleep_tip(llm, user)
        for b in bubbles:
            assert "HK$" not in b

    @pytest.mark.asyncio
    async def test_respects_bubble_length_cap(self):
        from src.broadcaster.composer import compose_weekly_sleep_tip, BUBBLE_MAX
        long_text = "A" * 300
        llm = MagicMock()
        llm.messages.create = AsyncMock(return_value=MagicMock(
            content=[MagicMock(text=f'{{"bubbles": ["{long_text}"]}}')]
        ))
        user = self._make_user()
        bubbles = await compose_weekly_sleep_tip(llm, user)
        for b in bubbles:
            assert len(b) <= BUBBLE_MAX

    @pytest.mark.asyncio
    async def test_max_two_bubbles(self):
        from src.broadcaster.composer import compose_weekly_sleep_tip
        llm = MagicMock()
        llm.messages.create = AsyncMock(return_value=MagicMock(
            content=[MagicMock(text='{"bubbles": ["第一條", "第二條", "第三條"]}')]
        ))
        user = self._make_user()
        bubbles = await compose_weekly_sleep_tip(llm, user)
        assert len(bubbles) <= 2

    @pytest.mark.asyncio
    async def test_returns_fallback_on_empty_bubbles(self):
        from src.broadcaster.composer import compose_weekly_sleep_tip
        llm = MagicMock()
        llm.messages.create = AsyncMock(return_value=MagicMock(
            content=[MagicMock(text='{"bubbles": []}')]
        ))
        user = self._make_user()
        bubbles = await compose_weekly_sleep_tip(llm, user)
        assert len(bubbles) >= 1

    @pytest.mark.asyncio
    async def test_happy_path_returns_llm_bubbles(self):
        from src.broadcaster.composer import compose_weekly_sleep_tip
        llm = MagicMock()
        llm.messages.create = AsyncMock(return_value=MagicMock(
            content=[MagicMock(text='{"bubbles": ["今晚11點前入睡補氣最好 💤"]}')]
        ))
        user = self._make_user()
        bubbles = await compose_weekly_sleep_tip(llm, user)
        assert bubbles == ["今晚11點前入睡補氣最好 💤"]


class TestWeeklySleepTipScheduler:
    def _make_crm(self, phones, already_sent=0):
        from src.crm.models import User
        crm = MagicMock()
        crm.list_active_phones = AsyncMock(return_value=phones)
        crm.get_broadcast_count_this_week = AsyncMock(return_value=already_sent)
        crm.record_broadcast = AsyncMock()
        if phones:
            user = User(phone=phones[0])
            crm.get_user = AsyncMock(return_value=user)
        else:
            crm.get_user = AsyncMock(return_value=None)
        return crm

    @pytest.mark.asyncio
    async def test_skips_blocked_phone(self):
        from src.broadcaster.scheduler import _run_weekly_sleep_tip
        crm = self._make_crm(["+85291234567"])
        with patch("src.broadcaster.scheduler.is_blocked", return_value=True), \
             patch("src.broadcaster.scheduler._within_send_window", return_value=True), \
             patch("src.broadcaster.scheduler.wa_client") as mock_wa:
            mock_wa.send_long_message = AsyncMock()
            await _run_weekly_sleep_tip(crm, MagicMock(), "acc_123")
        mock_wa.send_long_message.assert_not_called()
        crm.record_broadcast.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_already_sent_this_week(self):
        from src.broadcaster.scheduler import _run_weekly_sleep_tip
        crm = self._make_crm(["+85291234567"], already_sent=1)
        with patch("src.broadcaster.scheduler.is_blocked", return_value=False), \
             patch("src.broadcaster.scheduler._within_send_window", return_value=True), \
             patch("src.broadcaster.scheduler.wa_client") as mock_wa:
            mock_wa.send_long_message = AsyncMock()
            await _run_weekly_sleep_tip(crm, MagicMock(), "acc_123")
        mock_wa.send_long_message.assert_not_called()
        crm.record_broadcast.assert_not_called()

    @pytest.mark.asyncio
    async def test_sends_and_records_for_eligible_user(self):
        from src.broadcaster.scheduler import _run_weekly_sleep_tip
        phone = "+85291234567"
        crm = self._make_crm([phone], already_sent=0)
        mock_bubbles = ["今晚11點前入睡補氣最好 💤"]
        with patch("src.broadcaster.scheduler.is_blocked", return_value=False), \
             patch("src.broadcaster.scheduler._within_send_window", return_value=True), \
             patch("src.broadcaster.scheduler.wa_client") as mock_wa, \
             patch("src.broadcaster.scheduler.compose_weekly_sleep_tip",
                   new_callable=AsyncMock, return_value=mock_bubbles):
            mock_wa.send_long_message = AsyncMock()
            await _run_weekly_sleep_tip(crm, MagicMock(), "acc_123")
        mock_wa.send_long_message.assert_called_once()
        crm.record_broadcast.assert_called_once()
        args = crm.record_broadcast.call_args[0]
        assert args[1] == "weekly_sleep_tip"
        assert args[2].startswith("sleep-")

    @pytest.mark.asyncio
    async def test_dedup_key_uses_correct_prefix(self):
        from src.broadcaster.scheduler import _run_weekly_sleep_tip
        phone = "+85291234567"
        crm = self._make_crm([phone], already_sent=0)
        with patch("src.broadcaster.scheduler.is_blocked", return_value=False), \
             patch("src.broadcaster.scheduler._within_send_window", return_value=True), \
             patch("src.broadcaster.scheduler.wa_client") as mock_wa, \
             patch("src.broadcaster.scheduler.compose_weekly_sleep_tip",
                   new_callable=AsyncMock, return_value=["tip"]):
            mock_wa.send_long_message = AsyncMock()
            await _run_weekly_sleep_tip(crm, MagicMock(), "acc_123")
        call_args = crm.get_broadcast_count_this_week.call_args[0]
        assert call_args[1].startswith("sleep-")


# ---------------------------------------------------------------------------
# Tongue nudge (monthly): composer + scheduler + cutoffs
# ---------------------------------------------------------------------------


class TestTongueNudgeCutoffs:
    def test_nudge_gap_is_30_days(self):
        from src.broadcaster.scheduler import TONGUE_NUDGE_GAP_DAYS
        assert TONGUE_NUDGE_GAP_DAYS == 30


class TestTongueNudgeComposer:
    def _make_user(self, n_photos: int = 1):
        from datetime import datetime as _dt

        from src.crm.models import Constitution, TongueRecord, User
        photos = [
            TongueRecord(
                photo_url=f"https://example.com/t{i}.jpg",
                captured_at=_dt(2026, 4, 1, 10, 0),
            )
            for i in range(n_photos)
        ]
        return User(
            phone="+85291234567",
            constitution=Constitution.YANGXU,
            tongue_photos=photos,
        )

    @pytest.mark.asyncio
    async def test_fallback_on_llm_failure(self):
        from src.broadcaster.composer import compose_tongue_nudge
        llm = MagicMock()
        llm.messages.create = AsyncMock(side_effect=Exception("LLM down"))
        user = self._make_user()
        bubbles = await compose_tongue_nudge(llm, user)
        assert len(bubbles) >= 1
        assert all(isinstance(b, str) and len(b) > 0 for b in bubbles)

    @pytest.mark.asyncio
    async def test_no_price_in_output(self):
        from src.broadcaster.composer import compose_tongue_nudge
        llm = MagicMock()
        llm.messages.create = AsyncMock(return_value=MagicMock(
            content=[MagicMock(text='{"bubbles": ["影張新脷相 HK$50?", "等我比較變化"]}')]
        ))
        user = self._make_user()
        bubbles = await compose_tongue_nudge(llm, user)
        for b in bubbles:
            assert "HK$" not in b

    @pytest.mark.asyncio
    async def test_fallback_mentions_constitution(self):
        from src.broadcaster.composer import _tongue_nudge_fallback
        bubbles = _tongue_nudge_fallback("陽虛質")
        assert any("陽虛質" in b for b in bubbles)


class TestTongueNudgeScheduler:
    def _make_crm(self, phones, already_sent=0):
        from src.crm.models import Constitution, User
        crm = MagicMock()
        crm.list_phones_for_tongue_nudge = AsyncMock(return_value=phones)
        crm.get_broadcast_count_this_week = AsyncMock(return_value=already_sent)
        crm.get_last_broadcast_at = AsyncMock(return_value=None)
        crm.record_broadcast = AsyncMock()
        if phones:
            user = User(
                phone=phones[0],
                constitution=Constitution.YANGXU,
            )
            crm.get_user = AsyncMock(return_value=user)
        else:
            crm.get_user = AsyncMock(return_value=None)
        return crm

    @pytest.mark.asyncio
    async def test_skips_when_no_eligible_users(self):
        from src.broadcaster.scheduler import _run_tongue_nudge
        crm = self._make_crm([])  # zero phones
        with patch("src.broadcaster.scheduler._within_send_window", return_value=True), \
             patch("src.broadcaster.scheduler.wa_client") as mock_wa:
            mock_wa.send_long_message = AsyncMock()
            await _run_tongue_nudge(crm, MagicMock(), "acc_123")
        mock_wa.send_long_message.assert_not_called()
        crm.record_broadcast.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_blocked_phone(self):
        from src.broadcaster.scheduler import _run_tongue_nudge
        crm = self._make_crm(["+85291234567"])
        with patch("src.broadcaster.scheduler.is_blocked", return_value=True), \
             patch("src.broadcaster.scheduler._within_send_window", return_value=True), \
             patch("src.broadcaster.scheduler.wa_client") as mock_wa:
            mock_wa.send_long_message = AsyncMock()
            await _run_tongue_nudge(crm, MagicMock(), "acc_123")
        mock_wa.send_long_message.assert_not_called()
        crm.record_broadcast.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_already_capped_this_week(self):
        from src.broadcaster.scheduler import _run_tongue_nudge, BROADCAST_WEEKLY_CAP
        crm = self._make_crm(["+85291234567"], already_sent=BROADCAST_WEEKLY_CAP)
        with patch("src.broadcaster.scheduler.is_blocked", return_value=False), \
             patch("src.broadcaster.scheduler._within_send_window", return_value=True), \
             patch("src.broadcaster.scheduler.wa_client") as mock_wa:
            mock_wa.send_long_message = AsyncMock()
            await _run_tongue_nudge(crm, MagicMock(), "acc_123")
        mock_wa.send_long_message.assert_not_called()
        crm.record_broadcast.assert_not_called()

    @pytest.mark.asyncio
    async def test_sends_and_records_for_eligible_user(self):
        from src.broadcaster.scheduler import _run_tongue_nudge
        phone = "+85291234567"
        crm = self._make_crm([phone], already_sent=0)
        mock_bubbles = ["影張新脷相俾我睇下 📷"]
        with patch("src.broadcaster.scheduler.is_blocked", return_value=False), \
             patch("src.broadcaster.scheduler._within_send_window", return_value=True), \
             patch("src.broadcaster.scheduler.wa_client") as mock_wa, \
             patch("src.broadcaster.scheduler.compose_tongue_nudge",
                   new_callable=AsyncMock, return_value=mock_bubbles):
            mock_wa.send_long_message = AsyncMock()
            await _run_tongue_nudge(crm, MagicMock(), "acc_123")
        mock_wa.send_long_message.assert_called_once()
        crm.record_broadcast.assert_called_once()
        args = crm.record_broadcast.call_args[0]
        assert args[1] == "tongue_nudge"

    @pytest.mark.asyncio
    async def test_passes_correct_cutoffs_to_crm(self):
        """Both cutoff args should be ~30 days ago in ISO format."""
        from src.broadcaster.scheduler import _run_tongue_nudge
        crm = self._make_crm([])
        with patch("src.broadcaster.scheduler._within_send_window", return_value=True):
            await _run_tongue_nudge(crm, MagicMock(), "acc_123")
        call_args = crm.list_phones_for_tongue_nudge.call_args[0]
        # Both cutoffs are isoformat strings ~30 days back
        assert len(call_args) == 2
        for cutoff in call_args:
            assert "T" in cutoff  # ISO format has T separator


# ---------------------------------------------------------------------------
# CRM query for tongue nudge eligibility (SQLite end-to-end)
# ---------------------------------------------------------------------------


class TestTongueNudgeCRMQuery:
    @pytest.mark.asyncio
    async def test_excludes_users_with_no_tongue_photos(self, tmp_path):
        from datetime import datetime as _dt
        from src.crm.models import Constitution, User
        from src.crm.repo import CRMRepo
        repo = await CRMRepo.connect(tmp_path / "test.db")
        try:
            # User with known constitution but NO tongue photos
            u = await repo.get_or_create_user("+85291000001")
            await repo.save_user(u.with_updates(constitution=Constitution.YANGXU))
            cutoff = _dt(2026, 4, 1).isoformat()
            phones = await repo.list_phones_for_tongue_nudge(cutoff, cutoff)
            assert "+85291000001" not in phones
        finally:
            await repo.close()

    @pytest.mark.asyncio
    async def test_excludes_users_with_recent_tongue_photo(self, tmp_path):
        from datetime import datetime as _dt
        from src.crm.models import Constitution, TongueRecord
        from src.crm.repo import CRMRepo
        repo = await CRMRepo.connect(tmp_path / "test.db")
        try:
            phone = "+85291000002"
            u = await repo.get_or_create_user(phone)
            await repo.save_user(u.with_updates(constitution=Constitution.YANGXU))
            # Recent photo (today)
            await repo.add_tongue_record(phone, TongueRecord(
                photo_url="https://x/now.jpg",
                captured_at=_dt(2026, 5, 26),
            ))
            cutoff = _dt(2026, 4, 26).isoformat()  # 30 days back
            phones = await repo.list_phones_for_tongue_nudge(cutoff, cutoff)
            assert phone not in phones
        finally:
            await repo.close()

    @pytest.mark.asyncio
    async def test_includes_user_with_old_tongue_photo(self, tmp_path):
        from datetime import datetime as _dt
        from src.crm.models import Constitution, TongueRecord
        from src.crm.repo import CRMRepo
        repo = await CRMRepo.connect(tmp_path / "test.db")
        try:
            phone = "+85291000003"
            u = await repo.get_or_create_user(phone)
            await repo.save_user(u.with_updates(constitution=Constitution.YANGXU))
            # Photo from 60 days ago (older than cutoff)
            await repo.add_tongue_record(phone, TongueRecord(
                photo_url="https://x/old.jpg",
                captured_at=_dt(2026, 3, 27),
            ))
            cutoff = _dt(2026, 4, 26).isoformat()
            phones = await repo.list_phones_for_tongue_nudge(cutoff, cutoff)
            assert phone in phones
        finally:
            await repo.close()

    @pytest.mark.asyncio
    async def test_excludes_unknown_constitution(self, tmp_path):
        from datetime import datetime as _dt
        from src.crm.models import TongueRecord
        from src.crm.repo import CRMRepo
        repo = await CRMRepo.connect(tmp_path / "test.db")
        try:
            phone = "+85291000004"
            await repo.get_or_create_user(phone)  # constitution defaults UNKNOWN
            await repo.add_tongue_record(phone, TongueRecord(
                photo_url="https://x/old.jpg",
                captured_at=_dt(2026, 3, 1),
            ))
            cutoff = _dt(2026, 4, 26).isoformat()
            phones = await repo.list_phones_for_tongue_nudge(cutoff, cutoff)
            assert phone not in phones
        finally:
            await repo.close()

    @pytest.mark.asyncio
    async def test_excludes_users_already_nudged_this_period(self, tmp_path):
        from datetime import datetime as _dt
        from src.crm.models import Constitution, TongueRecord
        from src.crm.repo import CRMRepo
        repo = await CRMRepo.connect(tmp_path / "test.db")
        try:
            phone = "+85291000005"
            u = await repo.get_or_create_user(phone)
            await repo.save_user(u.with_updates(constitution=Constitution.YANGXU))
            # Old tongue photo (would normally qualify)
            await repo.add_tongue_record(phone, TongueRecord(
                photo_url="https://x/old.jpg",
                captured_at=_dt(2026, 3, 1),
            ))
            # But already nudged recently
            await repo.record_broadcast(
                phone, "tongue_nudge", "2026-W21", _dt(2026, 5, 20).isoformat()
            )
            cutoff = _dt(2026, 4, 26).isoformat()
            phones = await repo.list_phones_for_tongue_nudge(cutoff, cutoff)
            assert phone not in phones
        finally:
            await repo.close()
