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
# Weekly tea tip: fallback (pure)
# ---------------------------------------------------------------------------


class TestTeaFallback:
    def test_cold_constitution_gets_warm_tea(self):
        from src.broadcaster.composer import _tea_fallback
        for constitution in ("陽虛質", "氣虛質"):
            bubbles = _tea_fallback(constitution)
            assert len(bubbles) >= 1
            # Should reference a warming tea (薑棗茶)
            assert any("薑" in b or "棗" in b for b in bubbles), (
                f"Expected warming tea for {constitution}, got: {bubbles}"
            )

    def test_hot_constitution_gets_cooling_tea(self):
        from src.broadcaster.composer import _tea_fallback
        for constitution in ("陰虛質", "濕熱質"):
            bubbles = _tea_fallback(constitution)
            assert len(bubbles) >= 1
            # Should reference a cooling tea (菊花 / 枸杞)
            assert any("菊花" in b or "枸杞" in b for b in bubbles), (
                f"Expected cooling tea for {constitution}, got: {bubbles}"
            )

    def test_stagnation_constitution_gets_moving_tea(self):
        from src.broadcaster.composer import _tea_fallback
        for constitution in ("氣鬱質", "血瘀質"):
            bubbles = _tea_fallback(constitution)
            assert len(bubbles) >= 1
            # Should reference 玫瑰花茶 (疏肝)
            assert any("玫瑰" in b for b in bubbles), (
                f"Expected 玫瑰花茶 for {constitution}, got: {bubbles}"
            )

    def test_unknown_constitution_gets_neutral_tea(self):
        from src.broadcaster.composer import _tea_fallback
        bubbles = _tea_fallback("unknown")
        assert len(bubbles) >= 1
        # Should be the neutral / default option (茉莉)
        assert any("茉莉" in b for b in bubbles)

    def test_fallback_respects_bubble_length_cap(self):
        from src.broadcaster.composer import _tea_fallback, BUBBLE_MAX
        for constitution in ("陽虛質", "陰虛質", "氣鬱質", "平和質", "unknown"):
            for bubble in _tea_fallback(constitution):
                assert len(bubble) <= BUBBLE_MAX, (
                    f"Fallback bubble too long for {constitution}: {len(bubble)} chars"
                )

    def test_fallback_has_no_price(self):
        from src.broadcaster.composer import _tea_fallback
        for constitution in ("陽虛質", "陰虛質", "氣鬱質", "unknown"):
            for bubble in _tea_fallback(constitution):
                assert "HK$" not in bubble
                assert "$" not in bubble


# ---------------------------------------------------------------------------
# Weekly tea tip: composer (unit — LLM mocked)
# ---------------------------------------------------------------------------


class TestWeeklyTeaComposer:
    def _make_user(self, constitution: str = "unknown"):
        from src.crm.models import User, Constitution
        u = User(phone="+85291234567")
        for c in Constitution:
            if c.value == constitution:
                object.__setattr__(u, "constitution", c)
                break
        return u

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
            content=[MagicMock(text='{"bubbles": ["今週茶 HK$28 買返去！", "好正！"]}')]
        ))
        user = self._make_user()

        bubbles = await compose_weekly_tea_tip(llm, user)
        for b in bubbles:
            assert "HK$" not in b

    @pytest.mark.asyncio
    async def test_respects_bubble_length_cap(self):
        from src.broadcaster.composer import compose_weekly_tea_tip, BUBBLE_MAX
        long_text = "今週茶飲 " + "A" * 300
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
            content=[MagicMock(text=(
                '{"bubbles": ["第一條", "第二條", "第三條（唔應該出現）"]}'
            ))]
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
        user = self._make_user("氣虛質")

        bubbles = await compose_weekly_tea_tip(llm, user)
        assert len(bubbles) >= 1  # fallback kicks in

    @pytest.mark.asyncio
    async def test_happy_path_returns_llm_bubbles(self):
        from src.broadcaster.composer import compose_weekly_tea_tip
        llm = MagicMock()
        llm.messages.create = AsyncMock(return_value=MagicMock(
            content=[MagicMock(text='{"bubbles": ["今週 DIY：菊花枸杞茶，清肝明目！🌸"]}')]
        ))
        user = self._make_user("陰虛質")

        bubbles = await compose_weekly_tea_tip(llm, user)
        assert bubbles == ["今週 DIY：菊花枸杞茶，清肝明目！🌸"]


# ---------------------------------------------------------------------------
# Weekly tea tip: scheduler run logic
# ---------------------------------------------------------------------------


class TestRunWeeklyTea:
    def _make_crm(
        self,
        phones: list[str],
        already_sent: int = 0,
    ) -> object:
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
    async def test_skips_when_no_active_phones(self):
        from src.broadcaster.scheduler import _run_weekly_tea
        crm = self._make_crm(phones=[])
        llm = MagicMock()

        with patch("src.broadcaster.scheduler.is_blocked", return_value=False), \
             patch("src.broadcaster.scheduler.wa_client") as mock_wa:
            await _run_weekly_tea(crm, llm, "acc_123")
            mock_wa.send_long_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_blocked_phone(self):
        from src.broadcaster.scheduler import _run_weekly_tea
        crm = self._make_crm(phones=["+85291234567"])
        llm = MagicMock()

        with patch("src.broadcaster.scheduler.is_blocked", return_value=True), \
             patch("src.broadcaster.scheduler.wa_client") as mock_wa:
            await _run_weekly_tea(crm, llm, "acc_123")
            mock_wa.send_long_message.assert_not_called()
            crm.record_broadcast.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_already_sent_this_week(self):
        """If user already got a tea tip this ISO week, skip."""
        from src.broadcaster.scheduler import _run_weekly_tea
        crm = self._make_crm(phones=["+85291234567"], already_sent=1)
        llm = MagicMock()

        with patch("src.broadcaster.scheduler.is_blocked", return_value=False), \
             patch("src.broadcaster.scheduler.wa_client") as mock_wa:
            await _run_weekly_tea(crm, llm, "acc_123")
            mock_wa.send_long_message.assert_not_called()
            crm.record_broadcast.assert_not_called()

    @pytest.mark.asyncio
    async def test_sends_and_records_for_eligible_user(self):
        from src.broadcaster.scheduler import _run_weekly_tea
        phone = "+85291234567"
        crm = self._make_crm(phones=[phone], already_sent=0)
        llm = MagicMock()
        mock_bubbles = ["今週茶飲：薑棗茶，暖胃驅寒 🌿"]

        with patch("src.broadcaster.scheduler.is_blocked", return_value=False), \
             patch("src.broadcaster.scheduler.wa_client") as mock_wa, \
             patch("src.broadcaster.scheduler.compose_weekly_tea_tip",
                   new_callable=AsyncMock, return_value=mock_bubbles):
            mock_wa.send_long_message = AsyncMock()
            await _run_weekly_tea(crm, llm, "acc_123")

        mock_wa.send_long_message.assert_called_once_with(
            "acc_123", phone, mock_bubbles[0]
        )
        crm.record_broadcast.assert_called_once()
        args = crm.record_broadcast.call_args[0]
        assert args[0] == phone
        assert args[1] == "weekly_tea"
        # Dedup key should follow the tea-{iso_week} pattern
        assert args[2].startswith("tea-")

    @pytest.mark.asyncio
    async def test_dedup_key_uses_tea_prefix(self):
        """The dedup key passed to get_broadcast_count_this_week starts with 'tea-'."""
        from src.broadcaster.scheduler import _run_weekly_tea
        phone = "+85291234567"
        crm = self._make_crm(phones=[phone], already_sent=0)
        llm = MagicMock()

        with patch("src.broadcaster.scheduler.is_blocked", return_value=False), \
             patch("src.broadcaster.scheduler.wa_client") as mock_wa, \
             patch("src.broadcaster.scheduler.compose_weekly_tea_tip",
                   new_callable=AsyncMock, return_value=["嗨！菊花枸杞茶 🌸"]):
            mock_wa.send_long_message = AsyncMock()
            await _run_weekly_tea(crm, llm, "acc_123")

        # get_broadcast_count_this_week was called with the tea dedup key
        call_args = crm.get_broadcast_count_this_week.call_args[0]
        assert call_args[0] == phone
        assert call_args[1].startswith("tea-")

    @pytest.mark.asyncio
    async def test_does_not_check_weather_cap(self):
        """Weekly tea should NOT gate on _user_is_eligible (weather cap)."""
        from src.broadcaster.scheduler import _run_weekly_tea
        phone = "+85291234567"
        crm = self._make_crm(phones=[phone], already_sent=0)
        llm = MagicMock()

        with patch("src.broadcaster.scheduler.is_blocked", return_value=False), \
             patch("src.broadcaster.scheduler.wa_client") as mock_wa, \
             patch("src.broadcaster.scheduler._user_is_eligible",
                   new_callable=AsyncMock, return_value=False) as mock_eligible, \
             patch("src.broadcaster.scheduler.compose_weekly_tea_tip",
                   new_callable=AsyncMock, return_value=["嗨！薑棗茶 ☕"]):
            mock_wa.send_long_message = AsyncMock()
            await _run_weekly_tea(crm, llm, "acc_123")

        # Weather cap was NOT consulted — tea is independent
        mock_eligible.assert_not_called()
        # And the message was still sent
        mock_wa.send_long_message.assert_called_once()
