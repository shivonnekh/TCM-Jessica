"""Proactive broadcast scheduler — daily weather check + per-user cap enforcement.

Runs as an asyncio background task (same pattern as ``start_token_refresh_loop``).
Enable via environment variable: ``BROADCAST_ENABLED=true``

Per-user cap:
  - Max 2 broadcasts per ISO week per user
  - Min 36 hours between consecutive broadcasts per user

Send window: 08:00 – 21:00 HKT only (no late-night pings).

The loop wakes every BROADCAST_CHECK_INTERVAL_S (default 6h) and:
  1. Checks if current time is within send window
  2. Fetches HKO weather + detects notable condition
  3. For each active user: checks weekly count + 36h gap
  4. Composes + sends to eligible users
  5. Records each send in ``user_broadcasts`` table
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone

from src.broadcaster.composer import compose_broadcast
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
