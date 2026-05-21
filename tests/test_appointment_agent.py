"""Appointment Agent tests — offline (no LLM), 4-phase state machine."""

from __future__ import annotations

from datetime import datetime

import pytest

from src.agents.appointment_agent import (
    AppointmentAgent,
    _classify_confirmation,
    _parse_district,
    _parse_mode,
    _propose_slot,
)
from src.agents.base import SpecialistInput, SpecialistName
from src.crm.models import User, UserStatus

# Deterministic clock for tests — a Monday at 10am.
_FIXED_NOW = datetime(2026, 5, 25, 10, 0)


@pytest.fixture
def agent() -> AppointmentAgent:
    return AppointmentAgent(now_fn=lambda: _FIXED_NOW)


# ── Phase 1: ask mode when nothing set ───────────────────────────────


@pytest.mark.asyncio
async def test_phase1_asks_mode_with_offer(agent: AppointmentAgent) -> None:
    user = User(phone="+85291234567")
    inp = SpecialistInput(user=user, user_message="我想預約")
    out, _ = await agent.run(inp)

    assert out.specialist == SpecialistName.APPOINTMENT
    assert out.payload["phase"] == "asking_mode"
    assert "in_person" in out.payload["available_modes"]
    assert "online_video" in out.payload["available_modes"]
    # The 包郵 promotion should be surfaced
    offer_ids = [o["id"] for o in out.payload["active_offers"]]
    assert "online_consult_free_shipping_v1" in offer_ids


# ── Phase 2: ask location when in_person + no district ───────────────


@pytest.mark.asyncio
async def test_phase2_asks_location_after_choosing_in_person(
    agent: AppointmentAgent,
) -> None:
    user = User(phone="+85291234567")
    inp = SpecialistInput(user=user, user_message="我想到診")
    out, _ = await agent.run(inp)

    assert out.payload["phase"] == "asking_location"
    # mode should be persisted to temp_state for next turn
    assert out.suggested_user_state_diff["temp_state"]["appointment_mode"] == "in_person"


@pytest.mark.asyncio
async def test_phase2_skipped_for_online_video(agent: AppointmentAgent) -> None:
    """Online video doesn't need a district → jump straight to proposing."""
    user = User(phone="+85291234567")
    inp = SpecialistInput(user=user, user_message="想視診")
    out, _ = await agent.run(inp)

    assert out.payload["phase"] == "proposing_slot"
    assert out.payload["mode"] == "online_video"
    assert out.payload["proposed_slot"]["mode"] == "online_video"


# ── Phase 3: propose slot when district known ────────────────────────


@pytest.mark.asyncio
async def test_phase3_proposes_clinic_slot_for_shatin(
    agent: AppointmentAgent,
) -> None:
    user = User(
        phone="+85291234567",
        district="沙田",
        temp_state={"appointment_mode": "in_person"},
    )
    inp = SpecialistInput(user=user, user_message="幾時得？")
    out, _ = await agent.run(inp)

    assert out.payload["phase"] == "proposing_slot"
    assert out.payload["clinic"]["id"] == "careplus_shatin"
    slot = out.payload["proposed_slot"]
    assert slot["mode"] == "in_person"
    assert slot["clinic_id"] == "careplus_shatin"
    # Tomorrow = Tuesday — clinic is open 09:30
    assert slot["date"] == "2026-05-26"
    assert slot["time"] == "09:30"
    # Slot must be saved to temp_state for next-turn confirmation
    saved = out.suggested_user_state_diff["temp_state"]["appointment_proposed"]
    assert saved == slot
    # Free consult fee offer surfaced
    offer_ids = [o["id"] for o in out.payload["active_offers"]]
    assert "free_consult_fee_v1" in offer_ids
    # Tool log captured
    assert any(t["name"] == "ClinicMatcher.match" for t in out.tools_called)


@pytest.mark.asyncio
async def test_phase3_extracts_district_from_message(agent: AppointmentAgent) -> None:
    """User says 「我住沙田」 in the same turn they pick in_person."""
    user = User(phone="+85291234567", temp_state={"appointment_mode": "in_person"})
    inp = SpecialistInput(user=user, user_message="我住沙田，方便嗎？")
    out, _ = await agent.run(inp)

    assert out.suggested_user_state_diff["district"] == "沙田"
    assert out.payload["phase"] == "proposing_slot"


@pytest.mark.asyncio
async def test_phase3_skips_closed_day_for_maanshan(agent: AppointmentAgent) -> None:
    """Tomorrow is Tue → 馬鞍山 open. We test with Wed where 馬鞍山 is closed."""
    wed = datetime(2026, 5, 27, 10, 0)  # Wednesday
    agent_wed = AppointmentAgent(now_fn=lambda: wed)
    user = User(
        phone="+85291234567",
        district="馬鞍山",
        temp_state={"appointment_mode": "in_person"},
    )
    inp = SpecialistInput(user=user, user_message="幾時可以？")
    out, _ = await agent_wed.run(inp)

    slot = out.payload["proposed_slot"]
    # Thu = next day after Wed; 馬鞍山 open Thu → 2026-05-28
    assert slot["date"] == "2026-05-28"


# ── Phase 4: user confirms → appointment created ─────────────────────


@pytest.mark.asyncio
async def test_phase4_user_confirms_creates_appointment(
    agent: AppointmentAgent,
) -> None:
    user = User(
        phone="+85291234567",
        district="沙田",
        temp_state={
            "appointment_mode": "in_person",
            "appointment_proposed": {
                "mode": "in_person",
                "clinic_id": "careplus_shatin",
                "date": "2026-05-26",
                "time": "09:30",
            },
        },
    )
    inp = SpecialistInput(user=user, user_message="好啊 OK")
    out, _ = await agent.run(inp)

    assert out.payload["phase"] == "confirmed"
    assert out.payload["appointment"]["clinic_id"] == "careplus_shatin"
    # Diff carries an appointments_append for orchestrator persistence
    diff = out.suggested_user_state_diff
    assert "appointments_append" in diff
    assert diff["appointments_append"][0]["clinic_id"] == "careplus_shatin"
    # User status flips to booked
    assert diff["status"] == UserStatus.BOOKED.value
    # Booking URL deep-link
    assert "careplustcm.com/booking" in out.payload["booking_url"]
    assert "clinic=careplus_shatin" in out.payload["booking_url"]
    # Proposed slot cleared from temp_state
    assert "appointment_proposed" not in diff["temp_state"]


@pytest.mark.asyncio
async def test_phase4_user_rejects_loops_back_to_propose(
    agent: AppointmentAgent,
) -> None:
    user = User(
        phone="+85291234567",
        district="沙田",
        temp_state={
            "appointment_mode": "in_person",
            "appointment_proposed": {
                "mode": "in_person",
                "clinic_id": "careplus_shatin",
                "date": "2026-05-26",
                "time": "09:30",
            },
        },
    )
    inp = SpecialistInput(user=user, user_message="唔得啊改時間")
    out, _ = await agent.run(inp)

    # Falls back to proposing a (new — same logic) slot
    assert out.payload["phase"] == "proposing_slot"
    # Proposed should still be there (the new one) but the OLD was dropped
    # mid-turn before re-propose
    assert "appointment_proposed" in out.suggested_user_state_diff["temp_state"]


# ── Pure helper tests ────────────────────────────────────────────────


def test_parse_mode_in_person_variants() -> None:
    assert _parse_mode("我想到診") == "in_person"
    assert _parse_mode("到店預約") == "in_person"
    assert _parse_mode("親身嚟睇") == "in_person"


def test_parse_mode_online_variants() -> None:
    assert _parse_mode("可以視診嗎") == "online_video"
    assert _parse_mode("網上得唔得") == "online_video"
    assert _parse_mode("video call") == "online_video"


def test_parse_mode_no_signal() -> None:
    assert _parse_mode("我覺得唔舒服") is None
    assert _parse_mode("") is None


def test_parse_district_picks_longest_match_first() -> None:
    # 馬鞍山 should win over '山'
    assert _parse_district("我住馬鞍山") == "馬鞍山"
    # 元朗 not 元
    assert _parse_district("我喺元朗") == "元朗"


def test_parse_district_no_match() -> None:
    assert _parse_district("我喺火星") is None


def test_classify_confirmation_confirm() -> None:
    assert _classify_confirmation("好啊") == "confirm"
    assert _classify_confirmation("OK") == "confirm"
    assert _classify_confirmation("確認") == "confirm"


def test_classify_confirmation_reject_priority() -> None:
    """「唔得」 contains 「得」 — reject must win."""
    assert _classify_confirmation("唔得") == "reject"
    assert _classify_confirmation("改時間啦") == "reject"


def test_classify_confirmation_ambiguous() -> None:
    assert _classify_confirmation("...") == "ambiguous"
    assert _classify_confirmation("") == "ambiguous"


def test_propose_slot_online_video_picks_tomorrow_1030() -> None:
    now = datetime(2026, 5, 25, 10, 0)
    slot = _propose_slot(mode="online_video", clinic=None, now=now)
    assert slot is not None
    assert slot["mode"] == "online_video"
    assert slot["clinic_id"] is None
    assert slot["date"] == "2026-05-26"
    assert slot["time"] == "10:30"


def test_propose_slot_in_person_requires_clinic() -> None:
    now = datetime(2026, 5, 25, 10, 0)
    slot = _propose_slot(mode="in_person", clinic=None, now=now)
    assert slot is None
