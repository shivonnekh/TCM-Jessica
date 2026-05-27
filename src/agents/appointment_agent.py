"""Appointment Agent — books clinic visits OR online video consults.

4-phase state machine, phase inferred from CRM state (mirrors Constitution
Agent — no separate state store). Mode choice + location collection +
slot proposal + confirmation.

  Phase 1 "asking_mode":      no mode chosen yet → ask in_person vs online.
                              Surfaces 「網上視診（包郵）」 promotion.

  Phase 2 "asking_location":  mode=in_person but user.district unknown →
                              ask which HK district. (online_video skips
                              straight to phase 3 — no clinic required.)

  Phase 3 "proposing_slot":   district known → match clinic via
                              ClinicMatcher → propose a slot (default:
                              tomorrow, first open shift). Surfaces
                              「診所睇症免診金」 promotion.

  Phase 4 "confirming":       slot proposed; user replies. Confirm →
                              emit AppointmentRecord via _append diff →
                              orchestrator persists. Reject → loop back
                              to slot proposal (TODO: alt-slot logic).

State lives in user.temp_state under "appointment_*" keys.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta
from typing import Any

from src.agents.base import SpecialistInput, SpecialistName, SpecialistOutput
from src.crm.models import AppointmentRecord, UserStatus
from src.tools.clinic_matcher import ClinicMatcher
from src.tools.promotions import PromotionsLoader

logger = logging.getLogger("agents.appointment")

# temp_state keys (namespaced)
_TS_MODE = "appointment_mode"            # "in_person" | "online_video"
_TS_PROPOSED = "appointment_proposed"    # {clinic_id, date, time, mode}
_TS_MODE_ASK_COUNT = "appointment_mode_ask_count"      # int
_TS_DISTRICT_ASK_COUNT = "appointment_district_ask_count"  # int

_VALID_MODES = ("in_person", "online_video")

# Default clinic for in-person appointments when the user is evasive
# about district. 沙田 is the main 心宜中醫 branch + most central.
_DEFAULT_DISTRICT_FALLBACK = "沙田"

# Vague "you decide / whatever" replies — user is OK with any clinic.
# When seen at asking_location, default to the main clinic instead of
# looping forever asking for a district.
_VAGUE_YES_TOKENS = (
    "都可以", "都得", "都ok", "都OK",
    "隨便", "随便", "邊度都得", "哪都行",
    "冇所謂", "无所谓", "你揀", "你选",
    "你話事", "都行",
)


def _looks_vague_yes(text: str) -> bool:
    if not text:
        return False
    return any(tok in text for tok in _VAGUE_YES_TOKENS)

# Scheduling-intent signals — user is clearly trying to BOOK, not browse.
# When seen, we treat them as a strong signal to default mode + propose.
_SCHEDULING_HINT_TOKENS = (
    "下星期", "下禮拜", "下周", "聽日", "聽朝", "明天", "後日",
    "點", "時", "上午", "下午", "晚上", "朝早",
    "得唔得", "可以嗎", "可不可以",
)


def _has_scheduling_intent(text: str) -> bool:
    if not text:
        return False
    return any(tok in text for tok in _SCHEDULING_HINT_TOKENS)

# Map common Cantonese user utterances → mode.
_MODE_PATTERNS: dict[str, str] = {
    "到診": "in_person",
    "到店": "in_person",
    "親身": "in_person",
    "in-person": "in_person",
    "in person": "in_person",
    "現場": "in_person",
    "視診": "online_video",
    "視像": "online_video",
    "video": "online_video",
    "online": "online_video",
    "網上": "online_video",
    "remote": "online_video",
}

# Common HK districts — used to extract from free-text user reply.
# Order matters: longer matches first to avoid '元朗' matching '元'.
_HK_DISTRICTS: tuple[str, ...] = (
    "尖沙咀", "荃灣", "葵涌", "青衣", "馬鞍山", "將軍澳",
    "鴨脷洲", "黃竹坑", "堅尼地城", "上水", "粉嶺", "大埔", "火炭",
    "大圍", "沙田", "九龍塘", "旺角", "佐敦", "油麻地", "美孚",
    "荔枝角", "黃大仙", "鑽石山", "中環", "銅鑼灣", "北角", "太古",
    "鰂魚涌", "西灣河", "筲箕灣", "灣仔", "金鐘", "上環", "香港仔",
    "烏溪沙", "西貢", "坑口", "寶琳", "元朗", "屯門",
)

# User confirmation parsing.
_CONFIRM_PATTERNS = ("好", "ok", "okay", "確認", "確定", "yes", "可以", "得", "好的")
_REJECT_PATTERNS = ("唔得", "唔可以", "改", "唔好", "no", "另一", "其他", "不")


class AppointmentAgent:
    def __init__(
        self,
        clinic_matcher: ClinicMatcher | None = None,
        promotions: PromotionsLoader | None = None,
        *,
        now_fn: Any = None,  # injectable clock for tests
    ) -> None:
        self._matcher = clinic_matcher or ClinicMatcher()
        self._promos = promotions or PromotionsLoader()
        self._now = now_fn or datetime.now

    async def run(
        self, inp: SpecialistInput
    ) -> tuple[SpecialistOutput, dict[str, Any]]:
        usage = {"model": "rule_based", "input_tokens": 0, "output_tokens": 0}
        ts = dict(inp.user.temp_state)
        suggested_diff: dict[str, Any] = {}
        tools_called: list[dict[str, Any]] = []

        # Parse user-supplied mode + district from the latest message
        # (idempotent — only writes if not already set).
        mode = ts.get(_TS_MODE) or _parse_mode(inp.user_message)
        if mode and mode != ts.get(_TS_MODE):
            ts[_TS_MODE] = mode
            suggested_diff["temp_state"] = ts

        user_district = inp.user.district or _parse_district(inp.user_message)
        if user_district and user_district != inp.user.district:
            suggested_diff["district"] = user_district

        proposed = ts.get(_TS_PROPOSED)

        # ── PHASE 4: a slot was proposed last turn → handle reply ────
        if proposed:
            decision = _classify_confirmation(inp.user_message)
            if decision == "confirm":
                appointment = _materialise_appointment(proposed, when=self._now())
                # Clear the temp slot now that it's committed.
                ts.pop(_TS_PROPOSED, None)
                suggested_diff["temp_state"] = ts
                suggested_diff["appointments_append"] = [
                    appointment.model_dump(mode="json")
                ]
                suggested_diff["status"] = UserStatus.BOOKED.value
                payload = {
                    "phase": "confirmed",
                    "appointment": appointment.model_dump(mode="json"),
                    "booking_url": _booking_url_for(proposed),
                    "writer_hint": "確認預約成功，俾佢 booking link，提醒佢提早 10 分鐘到。",
                }
                tools_called.append(
                    {"name": "AppointmentAgent.confirm", "args": {}, "result": "confirmed"}
                )
                return _wrap(payload, suggested_diff, tools_called), usage

            if decision == "reject":
                # Drop the proposed slot, loop back to proposing.
                ts.pop(_TS_PROPOSED, None)
                suggested_diff["temp_state"] = ts
                # Fall through — phase 3 will re-propose.
                proposed = None

        # ── PHASE 1: no mode yet ─────────────────────────────────────
        if not mode:
            ask_count = int(ts.get(_TS_MODE_ASK_COUNT, 0))

            # Fallback: if user has clear scheduling intent ("下星期三 3 點")
            # AND we've already asked about mode at least once, default to
            # in_person rather than loop forever. Dry-run trace 2026-05-26
            # showed users supplying date/time but never picking a mode,
            # leaving the agent stuck on asking_mode.
            if ask_count >= 1 and _has_scheduling_intent(inp.user_message):
                mode = "in_person"
                ts[_TS_MODE] = mode
                # Don't reset ask_count — we still want to flow forward
                suggested_diff["temp_state"] = ts
                logger.info(
                    "appointment: defaulted mode=in_person (ask_count=%d, "
                    "scheduling intent in %r)",
                    ask_count, inp.user_message[:50]
                )
                # Fall through to subsequent phases (district / propose)
            else:
                # Ask, and remember we asked
                ts[_TS_MODE_ASK_COUNT] = ask_count + 1
                suggested_diff["temp_state"] = ts
                offers = [
                    p.model_dump(mode="json")
                    for p in self._promos.for_stage("appointment_mode_choice")
                ]
                payload = {
                    "phase": "asking_mode",
                    "available_modes": list(_VALID_MODES),
                    "active_offers": offers,
                    "writer_hint": (
                        "用戶仲未揀到診定視診，俾佢揀。提到視診包郵嘅優惠。"
                    ),
                }
                return _wrap(payload, suggested_diff, tools_called), usage

        # ── PHASE 2: in-person requires district ────────────────────
        if mode == "in_person" and not user_district:
            ask_count = int(ts.get(_TS_DISTRICT_ASK_COUNT, 0))

            # Fallback: after asking once + user is being evasive
            # ("都可以" / "你揀") OR has clear scheduling intent without
            # naming a district, default to the main clinic (沙田).
            # Prevents the asking_location loop pathology mirror of the
            # asking_mode bug fixed earlier.
            is_vague = _looks_vague_yes(inp.user_message)
            has_scheduling = _has_scheduling_intent(inp.user_message)

            if ask_count >= 1 and (is_vague or has_scheduling):
                user_district = _DEFAULT_DISTRICT_FALLBACK
                suggested_diff["district"] = user_district
                # Don't reset counter — record we resolved.
                suggested_diff["temp_state"] = ts
                logger.info(
                    "appointment: defaulted district=%s (ask_count=%d, "
                    "vague=%s scheduling=%s, msg=%r)",
                    user_district, ask_count, is_vague, has_scheduling,
                    inp.user_message[:50],
                )
                # Fall through to Phase 3 with the default district set.
            else:
                ts[_TS_DISTRICT_ASK_COUNT] = ask_count + 1
                suggested_diff["temp_state"] = ts
                payload = {
                    "phase": "asking_location",
                    "writer_hint": (
                        "問用戶住邊區 / 喺邊區方便，溫和咁問，唔係列表式。"
                        if ask_count == 0 else
                        # Second ask: more direct + offer the default
                        "用戶第二次冇答到區。直接問住沙田定馬鞍山方便啲？"
                        "或者話佢知唔肯定就會幫佢約沙田主分店。"
                    ),
                }
                return _wrap(payload, suggested_diff, tools_called), usage

        # ── PHASE 3: propose slot ────────────────────────────────────
        clinic_payload: dict[str, Any] | None = None
        if mode == "in_person":
            match = self._matcher.match(user_district)
            tools_called.append(
                {
                    "name": "ClinicMatcher.match",
                    "args": {"district": user_district},
                    "result": {
                        "clinic_id": match.clinic.get("id"),
                        "match_reason": match.match_reason,
                    },
                }
            )
            clinic_payload = match.clinic

        slot = _propose_slot(
            mode=mode,
            clinic=clinic_payload,
            now=self._now(),
        )
        if slot is None:
            # No open day in lookahead window — shouldn't happen with
            # current clinic data, but defend against future config changes.
            payload = {
                "phase": "no_slots_available",
                "writer_hint": "未搵到可用時段，請用戶直接到 booking URL 揀。",
                "booking_url": (
                    clinic_payload.get("booking_url") if clinic_payload else None
                ),
            }
            return _wrap(payload, suggested_diff, tools_called), usage

        # Persist the proposed slot — confirming turn will pick it up.
        ts[_TS_PROPOSED] = slot
        suggested_diff["temp_state"] = ts

        close_offers = [
            p.model_dump(mode="json")
            for p in self._promos.for_stage("appointment_close")
        ]
        payload = {
            "phase": "proposing_slot",
            "mode": mode,
            "clinic": clinic_payload,
            "proposed_slot": slot,
            "active_offers": close_offers,
            "writer_hint": (
                "向用戶提議具體日期+時間，問確認。提到免診金優惠。"
            ),
        }
        return _wrap(payload, suggested_diff, tools_called), usage


# ───────────────────────────────────────────────────────────────────
# Pure helpers (unit-testable)
# ───────────────────────────────────────────────────────────────────


def _parse_mode(text: str) -> str | None:
    if not text:
        return None
    low = text.lower()
    for needle, mode in _MODE_PATTERNS.items():
        if needle in low or needle in text:
            return mode
    return None


def _parse_district(text: str) -> str | None:
    if not text:
        return None
    for d in _HK_DISTRICTS:
        if d in text:
            return d
    return None


def _classify_confirmation(text: str) -> str:
    """Return 'confirm' | 'reject' | 'ambiguous'."""
    if not text:
        return "ambiguous"
    low = text.strip().lower()
    # Reject patterns take priority over confirm (「唔得」 contains 「得」)
    for r in _REJECT_PATTERNS:
        if r in low:
            return "reject"
    for c in _CONFIRM_PATTERNS:
        if c in low:
            return "confirm"
    return "ambiguous"


# Map weekday index → opening_hours key (must match ClinicMatcher convention)
_WEEKDAY_KEY = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


def _propose_slot(
    *, mode: str, clinic: dict[str, Any] | None, now: datetime
) -> dict[str, Any] | None:
    """Propose the next available slot.

    Strategy:
      - in_person: walk forward 1..14 days, pick first open day at clinic.
        Time = start of first shift.
      - online_video: pick tomorrow at 10:30 (placeholder — Care Plus
        doesn't expose video calendar to us yet).
    """
    if mode == "online_video":
        date = (now + timedelta(days=1)).date()
        return {
            "mode": mode,
            "clinic_id": None,
            "date": date.isoformat(),
            "time": "10:30",
        }

    if clinic is None:
        return None

    hours = clinic.get("opening_hours") or {}
    for offset in range(1, 15):
        candidate = now + timedelta(days=offset)
        key = _WEEKDAY_KEY[candidate.weekday()]
        slot_str = hours.get(key)
        if not slot_str or slot_str.lower() == "closed":
            continue
        # Take the first shift's start time. Format examples:
        #   '09:30-14:00|15:30-19:30'  → '09:30'
        #   '09:30-14:00'              → '09:30'
        first_shift = slot_str.split("|")[0]
        start_time = first_shift.split("-")[0].strip()
        return {
            "mode": "in_person",
            "clinic_id": clinic.get("id"),
            "date": candidate.date().isoformat(),
            "time": start_time,
        }
    return None


def _materialise_appointment(
    proposed: dict[str, Any], *, when: datetime
) -> AppointmentRecord:
    return AppointmentRecord(
        clinic_id=proposed.get("clinic_id") or "online",
        date=proposed["date"],
        time=proposed["time"],
        mode=proposed["mode"],
        status="confirmed",
        booked_at=when,
    )


def _booking_url_for(proposed: dict[str, Any]) -> str:
    """Build a deep-link to Care Plus booking with proposed date hint."""
    base = "https://careplustcm.com/booking"
    if proposed.get("clinic_id"):
        return f"{base}?clinic={proposed['clinic_id']}&date={proposed['date']}&time={proposed['time']}"
    return f"{base}?mode=online_video&date={proposed['date']}&time={proposed['time']}"


def _wrap(
    payload: dict[str, Any],
    suggested_diff: dict[str, Any],
    tools_called: list[dict[str, Any]],
) -> SpecialistOutput:
    return SpecialistOutput(
        specialist=SpecialistName.APPOINTMENT,
        payload=payload,
        suggested_user_state_diff=suggested_diff,
        tools_called=tools_called,
    )
