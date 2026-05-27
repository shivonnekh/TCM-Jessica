"""Proactive broadcast scheduler — weather care + purchase follow-up.

Runs as an asyncio background task (same pattern as ``start_token_refresh_loop``).
Enable via environment variable: ``BROADCAST_ENABLED=true``

Weather broadcast:
  - Per-user cap: max 2/ISO week, min 36h gap
  - Send window: 08:00–21:00 HKT
  - HKO free API: cold front, heatwave, rainstorm, humidity

Purchase follow-up:
  - Triggered when user has products_purchased + gone quiet ≥ 3 days
  - Max 1 follow-up per 30-day window per user
  - Warm "How's the soup?" check-in, no sales pitch

The loop wakes every BROADCAST_CHECK_INTERVAL_S (default 6h) and runs both.
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone

from src.broadcaster.composer import (
    compose_broadcast,
    compose_constitution_recheck,
    compose_purchase_followup,
    compose_solar_term_tip,
    compose_weekly_tea_tip,
    compose_weekly_acupressure_tip,
    compose_appointment_prep,
    compose_monthly_food_tip,
    compose_weekly_sleep_tip,
    compose_tongue_nudge,
    _load_product_names,
)
from src.broadcaster.menstrual_care import run_menstrual_care
from src.broadcaster.solar_terms import (
    get_active_solar_term,
    solar_term_condition_code_for_year,
)
from src.broadcaster.weather_service import (
    WeatherCondition,
    detect_conditions,
    fetch_current,
    fetch_warnings,
    pick_best,
)
from src.whatsapp import client as wa_client
from src.whatsapp.blocklist import is_blocked

logger = logging.getLogger("broadcaster.scheduler")

# ---------------------------------------------------------------------------
# Config (all overridable via env)
# ---------------------------------------------------------------------------

HKT = timezone(timedelta(hours=8))

BROADCAST_CHECK_INTERVAL_S = int(
    os.environ.get("BROADCAST_CHECK_INTERVAL_S", str(6 * 3600))
)
BROADCAST_SEND_PACE_S = float(os.environ.get("BROADCAST_SEND_PACE_S", "2.0"))
BROADCAST_WEEKLY_CAP = int(os.environ.get("BROADCAST_WEEKLY_CAP", "2"))
BROADCAST_MIN_GAP_H = int(os.environ.get("BROADCAST_MIN_GAP_H", "36"))
SEND_WINDOW_START_H = 8   # 08:00 HKT
SEND_WINDOW_END_H = 21    # 21:00 HKT

# Purchase follow-up config
FOLLOWUP_QUIET_DAYS = int(os.environ.get("FOLLOWUP_QUIET_DAYS", "3"))
FOLLOWUP_COOLDOWN_DAYS = int(os.environ.get("FOLLOWUP_COOLDOWN_DAYS", "30"))

# Constitution recheck config
RECHECK_COOLDOWN_DAYS = int(os.environ.get("RECHECK_COOLDOWN_DAYS", "90"))
RECHECK_ACTIVITY_GAP_DAYS = int(os.environ.get("RECHECK_ACTIVITY_GAP_DAYS", "7"))

# Tongue nudge: how long since last tongue photo before we ping them.
# 30 days = one rough TCM调理 cycle, gives time for visible change.
TONGUE_NUDGE_GAP_DAYS = int(os.environ.get("TONGUE_NUDGE_GAP_DAYS", "30"))

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _current_iso_week(now: datetime) -> str:
    """Return ISO week string, e.g. '2026-W21'."""
    year, week, _ = now.date().isocalendar()
    return f"{year}-W{week:02d}"


def _within_send_window(now: datetime) -> bool:
    """True if current HKT time is within the allowed send window."""
    hkt_now = now.astimezone(HKT)
    return SEND_WINDOW_START_H <= hkt_now.hour < SEND_WINDOW_END_H


def _hours_since(iso_ts: str | None, now: datetime) -> float:
    """Hours elapsed since the given ISO timestamp. Returns inf if None."""
    if not iso_ts:
        return float("inf")
    try:
        past = datetime.fromisoformat(iso_ts)
        return (now - past).total_seconds() / 3600
    except Exception:  # noqa: BLE001
        return float("inf")


async def _user_is_eligible(
    crm: object,
    phone: str,
    iso_week: str,
    now: datetime,
) -> bool:
    """Check per-user weekly cap + minimum gap."""
    count = await crm.get_broadcast_count_this_week(phone, iso_week)
    if count >= BROADCAST_WEEKLY_CAP:
        return False
    last_at = await crm.get_last_broadcast_at(phone)
    if _hours_since(last_at, now) < BROADCAST_MIN_GAP_H:
        return False
    return True


# ---------------------------------------------------------------------------
# Main broadcast run (single weather-check cycle)
# ---------------------------------------------------------------------------


async def _run_broadcast(crm: object, llm: object, account_id: str) -> None:
    """Execute one broadcast cycle. Called from the loop on each wake."""
    now = datetime.now(HKT)

    if not _within_send_window(now):
        logger.debug("Broadcast: outside send window (%s HKT) — skip", now.strftime("%H:%M"))
        return

    # ── Fetch HKO ───────────────────────────────────────────────────
    current, warnings = await asyncio.gather(fetch_current(), fetch_warnings())

    conditions = detect_conditions(current, warnings)
    condition = pick_best(conditions)

    if condition is None:
        logger.debug("Broadcast: no notable condition today — skip")
        return

    logger.info("Broadcast: detected condition %s (%s)", condition.code, condition.severity)

    # ── Recipients ──────────────────────────────────────────────────
    iso_week = _current_iso_week(now)
    phones = await crm.list_active_phones()

    sent_count = 0
    skipped_cap = 0
    skipped_block = 0
    errors = 0

    for phone in phones:
        if is_blocked(phone):
            skipped_block += 1
            continue

        if not await _user_is_eligible(crm, phone, iso_week, now):
            skipped_cap += 1
            continue

        # ── Compose ─────────────────────────────────────────────────
        try:
            user = await crm.get_user(phone)
            if user is None:
                continue

            bubbles = await compose_broadcast(llm, user, condition)
            if not bubbles:
                logger.warning("Broadcast: empty compose for %s — skip", phone[-4:])
                continue

            # ── Send ─────────────────────────────────────────────────
            full_text = "\n\n".join(bubbles)
            await wa_client.send_long_message(account_id, phone, full_text)

            # ── Record ───────────────────────────────────────────────
            sent_at = datetime.now(HKT).isoformat()
            await crm.record_broadcast(phone, condition.code, iso_week, sent_at)
            sent_count += 1

        except Exception as exc:  # noqa: BLE001
            logger.error("Broadcast: failed for %s: %s", phone[-4:], exc)
            errors += 1

        await asyncio.sleep(BROADCAST_SEND_PACE_S)

    logger.info(
        "Broadcast cycle done — condition=%s sent=%d skipped_cap=%d skipped_block=%d errors=%d",
        condition.code, sent_count, skipped_cap, skipped_block, errors,
    )


# ---------------------------------------------------------------------------
# Purchase follow-up run
# ---------------------------------------------------------------------------


async def _run_purchase_followup(crm: object, llm: object, account_id: str) -> None:
    """Check for users who bought something, went quiet, and need a follow-up."""
    now = datetime.now(HKT)

    if not _within_send_window(now):
        return

    activity_cutoff = (now - timedelta(days=FOLLOWUP_QUIET_DAYS)).isoformat()
    followup_cutoff = (now - timedelta(days=FOLLOWUP_COOLDOWN_DAYS)).isoformat()

    phones = await crm.list_phones_for_purchase_followup(activity_cutoff, followup_cutoff)

    if not phones:
        logger.debug("Followup: no eligible users")
        return

    logger.info("Followup: %d users eligible for purchase follow-up", len(phones))

    iso_week = _current_iso_week(now)
    sent_count = 0
    errors = 0

    for phone in phones:
        if is_blocked(phone):
            continue

        try:
            user = await crm.get_user(phone)
            if user is None or not user.products_purchased:
                continue

            products = _load_product_names(user.products_purchased)
            bubbles = await compose_purchase_followup(llm, user, products)
            if not bubbles:
                continue

            full_text = "\n\n".join(bubbles)
            await wa_client.send_long_message(account_id, phone, full_text)

            sent_at = datetime.now(HKT).isoformat()
            await crm.record_broadcast(phone, "purchase_followup", iso_week, sent_at)
            sent_count += 1

        except Exception as exc:  # noqa: BLE001
            logger.error("Followup: failed for %s: %s", phone[-4:], exc)
            errors += 1

        await asyncio.sleep(BROADCAST_SEND_PACE_S)

    logger.info("Followup cycle done — sent=%d errors=%d", sent_count, errors)


# ---------------------------------------------------------------------------
# Solar term broadcast
# ---------------------------------------------------------------------------


async def _run_solar_term(crm: object, llm: object, account_id: str) -> None:
    """Send a 節氣養生 tip if today is within ±2 days of a solar term."""
    now = datetime.now(HKT)

    if not _within_send_window(now):
        return

    term = get_active_solar_term(now.date())
    if term is None:
        logger.debug("Solar term: no active term today")
        return

    condition_code = solar_term_condition_code_for_year(term, now.year)
    logger.info("Solar term: %s (%s) is active", term.name_zh, condition_code)

    # Only send to users who haven't received this term+year combo
    # Re-use the purchase followup query pattern: "not in user_broadcasts for this code"
    # We query manually here since it's a per-code check, not a cooldown window
    iso_week = _current_iso_week(now)
    phones = await crm.list_active_phones()

    sent_count = 0
    errors = 0

    for phone in phones:
        if is_blocked(phone):
            continue

        # Check: already sent this term this year?
        try:
            cur_week_count = await crm.get_broadcast_count_this_week(phone, f"{now.year}-{term.name_en}")
        except Exception:  # noqa: BLE001
            # Fallback: use a synthetic "iso_week" key unique to this term+year
            cur_week_count = 0

        # Use a synthetic iso_week key: "<year>-<term_en>" to dedup per-term per-year
        dedup_week = f"{now.year}-{term.name_en}"
        already_sent = await crm.get_broadcast_count_this_week(phone, dedup_week)
        if already_sent > 0:
            continue

        # Also respect normal weekly weather cap — count combined
        if not await _user_is_eligible(crm, phone, iso_week, now):
            continue

        try:
            user = await crm.get_user(phone)
            if user is None:
                continue

            bubbles = await compose_solar_term_tip(
                llm, user,
                term_name_zh=term.name_zh,
                term_focus_zh=term.tcm_focus_zh,
                term_tip_zh=term.season_tip_zh,
                organ_zh=term.organ_zh,
            )
            if not bubbles:
                continue

            await wa_client.send_long_message(account_id, phone, "\n\n".join(bubbles))

            sent_at = datetime.now(HKT).isoformat()
            # Record under both the dedup key AND the normal weekly iso_week
            await crm.record_broadcast(phone, condition_code, dedup_week, sent_at)
            sent_count += 1

        except Exception as exc:  # noqa: BLE001
            logger.error("Solar term: failed for %s: %s", phone[-4:], exc)
            errors += 1

        await asyncio.sleep(BROADCAST_SEND_PACE_S)

    logger.info("Solar term cycle done — term=%s sent=%d errors=%d", term.name_zh, sent_count, errors)


# ---------------------------------------------------------------------------
# Constitution recheck
# ---------------------------------------------------------------------------


async def _run_constitution_recheck(crm: object, llm: object, account_id: str) -> None:
    """Nudge users whose constitution was set 90+ days ago to re-assess."""
    now = datetime.now(HKT)

    if not _within_send_window(now):
        return

    recheck_cutoff = (now - timedelta(days=RECHECK_COOLDOWN_DAYS)).isoformat()
    activity_cutoff = (now - timedelta(days=RECHECK_ACTIVITY_GAP_DAYS)).isoformat()

    phones = await crm.list_phones_for_constitution_recheck(recheck_cutoff, activity_cutoff)

    if not phones:
        logger.debug("Constitution recheck: no eligible users")
        return

    logger.info("Constitution recheck: %d users eligible", len(phones))

    iso_week = _current_iso_week(now)
    sent_count = 0
    errors = 0

    for phone in phones:
        if is_blocked(phone):
            continue

        if not await _user_is_eligible(crm, phone, iso_week, now):
            continue

        try:
            user = await crm.get_user(phone)
            if user is None:
                continue

            bubbles = await compose_constitution_recheck(llm, user)
            if not bubbles:
                continue

            await wa_client.send_long_message(account_id, phone, "\n\n".join(bubbles))

            sent_at = datetime.now(HKT).isoformat()
            await crm.record_broadcast(phone, "constitution_recheck", iso_week, sent_at)
            sent_count += 1

        except Exception as exc:  # noqa: BLE001
            logger.error("Constitution recheck: failed for %s: %s", phone[-4:], exc)
            errors += 1

        await asyncio.sleep(BROADCAST_SEND_PACE_S)

    logger.info("Constitution recheck done — sent=%d errors=%d", sent_count, errors)


# ---------------------------------------------------------------------------
# Weekly tea tip broadcast
# ---------------------------------------------------------------------------


async def _run_weekly_tea(crm: object, llm: object, account_id: str) -> None:
    """Send a personalised weekly tea therapy tip to all active users (once per ISO week)."""
    now = datetime.now(HKT)

    if not _within_send_window(now):
        return

    iso_week = _current_iso_week(now)
    tea_dedup_key = f"tea-{iso_week}"

    phones = await crm.list_active_phones()

    sent_count = 0
    errors = 0

    for phone in phones:
        if is_blocked(phone):
            continue

        already_sent = await crm.get_broadcast_count_this_week(phone, tea_dedup_key)
        if already_sent > 0:
            continue

        try:
            user = await crm.get_user(phone)
            if user is None:
                continue

            bubbles = await compose_weekly_tea_tip(llm, user)
            if not bubbles:
                continue

            await wa_client.send_long_message(account_id, phone, "\n\n".join(bubbles))
            await crm.record_broadcast(phone, "weekly_tea", tea_dedup_key, datetime.now(HKT).isoformat())
            sent_count += 1

        except Exception as exc:  # noqa: BLE001
            logger.error("Weekly tea: failed for %s: %s", phone[-4:], exc)
            errors += 1

        await asyncio.sleep(BROADCAST_SEND_PACE_S)

    logger.info("Weekly tea cycle done — sent=%d errors=%d", sent_count, errors)


# ---------------------------------------------------------------------------
# Weekly acupressure tip broadcast
# ---------------------------------------------------------------------------


async def _run_weekly_acupressure(crm: object, llm: object, account_id: str) -> None:
    """Send a personalised weekly acupressure tip to all active users (once per ISO week)."""
    now = datetime.now(HKT)

    if not _within_send_window(now):
        return

    iso_week = _current_iso_week(now)
    dedup_key = f"acupressure-{iso_week}"

    phones = await crm.list_active_phones()

    sent_count = 0
    errors = 0

    for phone in phones:
        if is_blocked(phone):
            continue

        already_sent = await crm.get_broadcast_count_this_week(phone, dedup_key)
        if already_sent > 0:
            continue

        try:
            user = await crm.get_user(phone)
            if user is None:
                continue

            bubbles = await compose_weekly_acupressure_tip(llm, user)
            if not bubbles:
                continue

            await wa_client.send_long_message(account_id, phone, "\n\n".join(bubbles))
            await crm.record_broadcast(phone, "weekly_acupressure", dedup_key, datetime.now(HKT).isoformat())
            sent_count += 1

        except Exception as exc:  # noqa: BLE001
            logger.error("Weekly acupressure: failed for %s: %s", phone[-4:], exc)
            errors += 1

        await asyncio.sleep(BROADCAST_SEND_PACE_S)

    logger.info("Weekly acupressure cycle done — sent=%d errors=%d", sent_count, errors)


# ---------------------------------------------------------------------------
# Appointment prep broadcast
# ---------------------------------------------------------------------------


async def _run_appointment_prep(crm: object, llm: object, account_id: str) -> None:
    """Send appointment prep messages to users with upcoming appointments (within 48h)."""
    now = datetime.now(HKT)

    if not _within_send_window(now):
        return

    iso_week = _current_iso_week(now)
    dedup_key = f"appt-prep-{iso_week}"

    phones = await crm.list_phones_for_upcoming_appointments(within_hours=48)

    if not phones:
        logger.debug("Appointment prep: no upcoming appointments")
        return

    logger.info("Appointment prep: %d users with upcoming appointments", len(phones))

    sent_count = 0
    errors = 0

    for phone in phones:
        if is_blocked(phone):
            continue

        already_sent = await crm.get_broadcast_count_this_week(phone, dedup_key)
        if already_sent > 0:
            continue

        try:
            user = await crm.get_user(phone)
            if user is None:
                continue

            bubbles = await compose_appointment_prep(llm, user)
            if not bubbles:
                continue

            await wa_client.send_long_message(account_id, phone, "\n\n".join(bubbles))
            await crm.record_broadcast(phone, "appointment_prep", dedup_key, datetime.now(HKT).isoformat())
            sent_count += 1

        except Exception as exc:  # noqa: BLE001
            logger.error("Appointment prep: failed for %s: %s", phone[-4:], exc)
            errors += 1

        await asyncio.sleep(BROADCAST_SEND_PACE_S)

    logger.info("Appointment prep cycle done — sent=%d errors=%d", sent_count, errors)


# ---------------------------------------------------------------------------
# Tongue progress monthly nudge
# ---------------------------------------------------------------------------


async def _run_tongue_nudge(crm: object, llm: object, account_id: str) -> None:
    """Once-per-month nudge for users who uploaded a tongue photo >30 days
    ago to re-upload. Without this, the TongueProgress vision comparison
    feature stays dormant — users never come back on their own.
    """
    now = datetime.now(HKT)

    if not _within_send_window(now):
        return

    tongue_cutoff = (now - timedelta(days=TONGUE_NUDGE_GAP_DAYS)).isoformat()
    nudge_cutoff = (now - timedelta(days=TONGUE_NUDGE_GAP_DAYS)).isoformat()

    phones = await crm.list_phones_for_tongue_nudge(tongue_cutoff, nudge_cutoff)

    if not phones:
        logger.debug("Tongue nudge: no eligible users")
        return

    logger.info("Tongue nudge: %d users eligible", len(phones))

    iso_week = _current_iso_week(now)
    sent_count = 0
    errors = 0

    for phone in phones:
        if is_blocked(phone):
            continue

        if not await _user_is_eligible(crm, phone, iso_week, now):
            continue

        try:
            user = await crm.get_user(phone)
            if user is None:
                continue

            bubbles = await compose_tongue_nudge(llm, user)
            if not bubbles:
                continue

            await wa_client.send_long_message(account_id, phone, "\n\n".join(bubbles))

            sent_at = datetime.now(HKT).isoformat()
            await crm.record_broadcast(phone, "tongue_nudge", iso_week, sent_at)
            sent_count += 1

        except Exception as exc:  # noqa: BLE001
            logger.error("Tongue nudge: failed for %s: %s", phone[-4:], exc)
            errors += 1

        await asyncio.sleep(BROADCAST_SEND_PACE_S)

    logger.info("Tongue nudge cycle done — sent=%d errors=%d", sent_count, errors)


# ---------------------------------------------------------------------------
# Monthly food tip broadcast
# ---------------------------------------------------------------------------


async def _run_monthly_food_tip(crm: object, llm: object, account_id: str) -> None:
    """Send a personalised monthly seasonal food therapy tip to all active users."""
    now = datetime.now(HKT)

    if not _within_send_window(now):
        return

    dedup_key = f"food-{now.year}-{now.month:02d}"

    phones = await crm.list_active_phones()

    sent_count = 0
    errors = 0

    for phone in phones:
        if is_blocked(phone):
            continue

        already_sent = await crm.get_broadcast_count_this_week(phone, dedup_key)
        if already_sent > 0:
            continue

        try:
            user = await crm.get_user(phone)
            if user is None:
                continue

            bubbles = await compose_monthly_food_tip(llm, user, now.month)
            if not bubbles:
                continue

            await wa_client.send_long_message(account_id, phone, "\n\n".join(bubbles))
            await crm.record_broadcast(phone, "monthly_food_tip", dedup_key, datetime.now(HKT).isoformat())
            sent_count += 1

        except Exception as exc:  # noqa: BLE001
            logger.error("Monthly food tip: failed for %s: %s", phone[-4:], exc)
            errors += 1

        await asyncio.sleep(BROADCAST_SEND_PACE_S)

    logger.info("Monthly food tip cycle done — sent=%d errors=%d", sent_count, errors)


# ---------------------------------------------------------------------------
# Weekly sleep tip broadcast
# ---------------------------------------------------------------------------


async def _run_weekly_sleep_tip(crm: object, llm: object, account_id: str) -> None:
    """Send a personalised weekly sleep wellness tip to all active users (once per ISO week)."""
    now = datetime.now(HKT)

    if not _within_send_window(now):
        return

    iso_week = _current_iso_week(now)
    dedup_key = f"sleep-{iso_week}"

    phones = await crm.list_active_phones()

    sent_count = 0
    errors = 0

    for phone in phones:
        if is_blocked(phone):
            continue

        already_sent = await crm.get_broadcast_count_this_week(phone, dedup_key)
        if already_sent > 0:
            continue

        try:
            user = await crm.get_user(phone)
            if user is None:
                continue

            bubbles = await compose_weekly_sleep_tip(llm, user)
            if not bubbles:
                continue

            await wa_client.send_long_message(account_id, phone, "\n\n".join(bubbles))
            await crm.record_broadcast(phone, "weekly_sleep_tip", dedup_key, datetime.now(HKT).isoformat())
            sent_count += 1

        except Exception as exc:  # noqa: BLE001
            logger.error("Weekly sleep tip: failed for %s: %s", phone[-4:], exc)
            errors += 1

        await asyncio.sleep(BROADCAST_SEND_PACE_S)

    logger.info("Weekly sleep tip cycle done — sent=%d errors=%d", sent_count, errors)


# ---------------------------------------------------------------------------
# Background loop (entry point wired from web.py lifespan)
# ---------------------------------------------------------------------------


async def start_broadcast_loop(crm: object, llm: object, account_id: str) -> None:
    """Long-running coroutine — mirrors ``start_token_refresh_loop`` pattern.

    Sleeps BROADCAST_CHECK_INTERVAL_S between cycles. First sleep before
    first run so we don't broadcast at boot.
    """
    logger.info(
        "Broadcast loop started — interval=%ds cap=%d/week min_gap=%dh",
        BROADCAST_CHECK_INTERVAL_S, BROADCAST_WEEKLY_CAP, BROADCAST_MIN_GAP_H,
    )
    while True:
        await asyncio.sleep(BROADCAST_CHECK_INTERVAL_S)
        try:
            await _run_broadcast(crm, llm, account_id)
        except Exception as exc:  # noqa: BLE001
            logger.error("Broadcast loop error (will retry next cycle): %s", exc)
        try:
            await _run_purchase_followup(crm, llm, account_id)
        except Exception as exc:  # noqa: BLE001
            logger.error("Followup loop error (will retry next cycle): %s", exc)
        try:
            await _run_solar_term(crm, llm, account_id)
        except Exception as exc:  # noqa: BLE001
            logger.error("Solar term loop error (will retry next cycle): %s", exc)
        try:
            await _run_constitution_recheck(crm, llm, account_id)
        except Exception as exc:  # noqa: BLE001
            logger.error("Constitution recheck loop error (will retry next cycle): %s", exc)
        try:
            await _run_weekly_tea(crm, llm, account_id)
        except Exception as exc:  # noqa: BLE001
            logger.error("Weekly tea loop error (will retry next cycle): %s", exc)
        try:
            await _run_weekly_acupressure(crm, llm, account_id)
        except Exception as exc:  # noqa: BLE001
            logger.error("Weekly acupressure loop error (will retry next cycle): %s", exc)
        try:
            await _run_appointment_prep(crm, llm, account_id)
        except Exception as exc:  # noqa: BLE001
            logger.error("Appointment prep loop error (will retry next cycle): %s", exc)
        try:
            await _run_tongue_nudge(crm, llm, account_id)
        except Exception as exc:  # noqa: BLE001
            logger.error("Tongue nudge loop error (will retry next cycle): %s", exc)
        try:
            await _run_monthly_food_tip(crm, llm, account_id)
        except Exception as exc:  # noqa: BLE001
            logger.error("Monthly food tip loop error (will retry next cycle): %s", exc)
        try:
            await _run_weekly_sleep_tip(crm, llm, account_id)
        except Exception as exc:  # noqa: BLE001
            logger.error("Weekly sleep tip loop error (will retry next cycle): %s", exc)
        try:
            await run_menstrual_care(crm, llm, account_id)
        except Exception as exc:  # noqa: BLE001
            logger.error("Menstrual care loop error (will retry next cycle): %s", exc)
