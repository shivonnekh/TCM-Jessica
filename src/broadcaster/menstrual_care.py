"""月事陪伴 — Menstrual phase care broadcast.

Standalone module: does NOT import from scheduler.py to avoid circular imports.
Sends weekly phase-appropriate TCM menstrual care tips to users with known cycle data.

Phases (TCM 月經週期四期):
  行經期 (Day 1-5):  Active flow — rest, warmth, avoid cold
  經後期 (Day 6-13): Post-flow — nourish blood/yin
  排卵期 (Day 14-16): Ovulation peak — warmth, avoid fatigue
  黃體期 (Day 17-28): Pre-period — liver qi, emotional regulation

Dedup: once per ISO week per user (key: "menstrual-<YYYY-Wnn>").
Does NOT gate on the weather broadcast weekly cap.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.crm.models import User

from src.llm import DEFAULT_MODEL
from src.whatsapp import client as wa_client
from src.whatsapp.blocklist import is_blocked

logger = logging.getLogger("broadcaster.menstrual_care")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

HKT = timezone(timedelta(hours=8))
BROADCAST_SEND_PACE_S = float(os.environ.get("BROADCAST_SEND_PACE_S", "2.0"))
SEND_WINDOW_START_H = 8
SEND_WINDOW_END_H = 21

BUBBLE_MAX = 150
MAX_BUBBLES = 2

# ---------------------------------------------------------------------------
# Knowledge base card
# ---------------------------------------------------------------------------

_MENSTRUAL_CARD = (
    Path(__file__).resolve().parent.parent.parent
    / "data" / "knowledge_base" / "faq" / "tcm_womens_menstrual.json"
)

# Regex guard — reject any bubble that leaks prices
_PRICE_RE = re.compile(r"HK\$\d+|\$\d+|港幣\s*\d+|價錢|售價")


def _load_menstrual_card() -> str:
    """Return truncated core_answer from the menstrual knowledge card."""
    try:
        raw = json.loads(_MENSTRUAL_CARD.read_text(encoding="utf-8"))
        answer: str = raw["knowledge_card"]["core_content"]["core_answer"]
        return answer[:800]
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not load menstrual card: %s", exc)
        return ""


# ---------------------------------------------------------------------------
# TCM Menstrual Phase Constants
# ---------------------------------------------------------------------------

PHASE_MENSTRUATION = "行經期"   # Day 1-5: active flow
PHASE_FOLLICULAR   = "經後期"   # Day 6-13: post-flow, build up
PHASE_OVULATION    = "排卵期"   # Day 14-16: peak
PHASE_LUTEAL       = "黃體期"   # Day 17-28: pre-period

_PHASE_GUIDANCE: dict[str, str] = {
    PHASE_MENSTRUATION: "避免生冷，活血通暢，可適量活動但避免劇烈運動",
    PHASE_FOLLICULAR:   "養血補陰，可多吃滋補食材（紅棗、枸杞），適合開始補充",
    PHASE_OVULATION:    "注意保暖，避免過度勞累，可以活血食材助排卵",
    PHASE_LUTEAL:       "疏肝解鬱，情緒調節，注意避免刺激食物",
}

# ---------------------------------------------------------------------------
# Phase calculation
# ---------------------------------------------------------------------------


def _calculate_phase(last_start: date, cycle_length: int, today: date) -> str:
    """Return the TCM phase name for today given last period start.

    Returns one of the 4 PHASE_* constants. Handles cycles of any length by
    using the modulo of days-since-start within the cycle.
    """
    days_since = (today - last_start).days % cycle_length
    if days_since < 5:
        return PHASE_MENSTRUATION
    elif days_since < 13:
        return PHASE_FOLLICULAR
    elif days_since < 16:
        return PHASE_OVULATION
    else:
        return PHASE_LUTEAL


# ---------------------------------------------------------------------------
# Fallback messages (one per phase — no LLM needed)
# ---------------------------------------------------------------------------


def _menstrual_fallback(phase_zh: str) -> list[str]:
    fallbacks: dict[str, list[str]] = {
        PHASE_MENSTRUATION: [
            "行經期間記得多休息 🌹 避免生冷食物同劇烈運動，用熱水袋暖小腹有助緩解不適。"
        ],
        PHASE_FOLLICULAR: [
            "月經剛完，係補充精氣嘅好時機 🌿 可以多食紅棗、枸杞或者飲一碗暖湯，幫身體恢復元氣。"
        ],
        PHASE_OVULATION: [
            "而家係排卵期前後，記得保暖、充足休息 ✨ 避免過度勞累，保持好心情。"
        ],
        PHASE_LUTEAL: [
            "經前一兩週，情緒容易波動係正常嘅 💕 可以試下玫瑰花茶或者菊花茶疏肝解鬱，心情自然好啲。"
        ],
    }
    return fallbacks.get(phase_zh, ["記得照顧好自己 🌸 有任何唔舒服隨時搵我。"])


# ---------------------------------------------------------------------------
# Composer
# ---------------------------------------------------------------------------


async def compose_menstrual_care_tip(
    llm: object,
    user: "User",
    phase_zh: str,
) -> list[str]:
    """Generate a 1-2 bubble menstrual phase care tip in HK Canto.

    Personalised to phase + constitution. No products pitched, no prices.
    Falls back to _menstrual_fallback on any LLM failure.
    """
    constitution = user.constitution.value if user.constitution else "unknown"
    card_content = _load_menstrual_card()
    phase_guidance = _PHASE_GUIDANCE.get(phase_zh, "")

    system_prompt = """\
你係 Jessica，心宜中醫 Care Plus 嘅中醫健康顧問。
今日你主動向用戶發送一條月經周期養生關心訊息。

⚠️ 重要規則（絕對唔可以違反）：
- 唔好問 follow-up 問題
- 唔好自我介紹（唔好講「我係Jessica」）
- 唔好提任何具體產品名稱、價錢或售價
- 唔好下任何醫療診斷
- 全部用香港廣東話口語（唔好用書面語或普通話）
- 控制在 1-2 條訊息，每條唔超過 150 個字
- 語氣溫暖、關心，像知識豐富嘅朋友發訊息咁自然

輸出格式（JSON only，唔好有其他文字）：
{"bubbles": ["第一條訊息", "第二條訊息（可選）"]}
"""

    user_prompt = f"""用戶而家處於月經周期嘅：{phase_zh}

呢個時期嘅中醫養生重點：{phase_guidance}

用戶體質：{constitution}

月經健康參考知識（部分節錄，用嚟啟發 tip，唔好逐字抄）：
{card_content}

根據以上資料，寫 1-2 條溫暖嘅廣東話養生訊息俾用戶，針對而家嘅{phase_zh}。
如果用戶有特定體質，可以輕輕個人化。
記住：唔好問問題、唔好賣嘢、淨係關心同送一個實用 tip 就夠。"""

    try:
        response = await llm.messages.create(
            model=DEFAULT_MODEL,
            max_tokens=300,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        raw = response.content[0].text.strip()

        # Strip markdown fences if model wraps response
        if raw.startswith("```"):
            raw = re.sub(r"^```[a-z]*\n?", "", raw)
            raw = re.sub(r"\n?```$", "", raw)

        data = json.loads(raw)
        bubbles = [b.strip() for b in data.get("bubbles", []) if b.strip()]

    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Menstrual care compose failed (%s): %s — using fallback",
            type(exc).__name__, exc,
        )
        return _menstrual_fallback(phase_zh)

    if not bubbles:
        logger.warning("Menstrual care compose returned empty bubbles — using fallback")
        return _menstrual_fallback(phase_zh)

    # Safety checks
    cleaned: list[str] = []
    for bubble in bubbles[:MAX_BUBBLES]:
        if _PRICE_RE.search(bubble):
            logger.warning("Menstrual care bubble contains price — stripping: %s", bubble)
            continue
        cleaned.append(bubble[:BUBBLE_MAX])

    return cleaned if cleaned else _menstrual_fallback(phase_zh)


# ---------------------------------------------------------------------------
# Scheduler helpers (standalone — does NOT modify scheduler.py)
# ---------------------------------------------------------------------------


def _current_iso_week(now: datetime) -> str:
    """Return ISO week string, e.g. '2026-W21'."""
    year, week, _ = now.date().isocalendar()
    return f"{year}-W{week:02d}"


def _within_send_window(now: datetime) -> bool:
    """True if current HKT time is within the allowed send window."""
    hkt = now.astimezone(HKT)
    return SEND_WINDOW_START_H <= hkt.hour < SEND_WINDOW_END_H


# ---------------------------------------------------------------------------
# Scheduler runner
# ---------------------------------------------------------------------------


async def run_menstrual_care(crm: object, llm: object, account_id: str) -> None:
    """Send phase-appropriate menstrual care tips to users with known cycle data.

    Only runs for users with last_period_start set. Dedup: once per ISO week.
    Does NOT gate on the weather broadcast cap.
    """
    now = datetime.now(HKT)

    if not _within_send_window(now):
        logger.debug("Menstrual care: outside send window (%s HKT) — skip", now.strftime("%H:%M"))
        return

    iso_week = _current_iso_week(now)
    dedup_key = f"menstrual-{iso_week}"

    phones = await crm.list_active_phones()

    sent_count = 0
    skipped_no_data = 0
    skipped_block = 0
    skipped_dedup = 0
    errors = 0

    for phone in phones:
        if is_blocked(phone):
            skipped_block += 1
            continue

        already_sent = await crm.get_broadcast_count_this_week(phone, dedup_key)
        if already_sent > 0:
            skipped_dedup += 1
            continue

        user = await crm.get_user(phone)
        if user is None:
            continue

        if user.last_period_start is None:
            skipped_no_data += 1
            continue

        # Calculate current TCM phase
        phase_zh = _calculate_phase(
            user.last_period_start,
            user.cycle_length_days,
            now.date(),
        )

        try:
            bubbles = await compose_menstrual_care_tip(llm, user, phase_zh)
            if not bubbles:
                logger.warning("Menstrual care: empty compose for %s — skip", phone[-4:])
                continue

            await wa_client.send_long_message(account_id, phone, "\n\n".join(bubbles))

            sent_at = datetime.now(HKT).isoformat()
            await crm.record_broadcast(phone, "menstrual_care", dedup_key, sent_at)
            sent_count += 1

        except Exception as exc:  # noqa: BLE001
            logger.error("Menstrual care: failed for %s: %s", phone[-4:], exc)
            errors += 1

        await asyncio.sleep(BROADCAST_SEND_PACE_S)

    logger.info(
        "Menstrual care cycle done — sent=%d skipped_no_data=%d skipped_block=%d "
        "skipped_dedup=%d errors=%d",
        sent_count, skipped_no_data, skipped_block, skipped_dedup, errors,
    )
