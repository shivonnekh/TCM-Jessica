"""Broadcast message composer — dedicated mini-LLM for proactive weather care.

Deliberately NOT the main WriterAgent so broadcast-specific rules stay isolated:
  - 1-2 bubbles only (≤ 150 chars each)
  - No follow-up question
  - No self-introduction
  - No product names or prices
  - No medical diagnoses
  - HK Cantonese 口語

Season card selection by month:
  Mar-Aug → tcm_seasonal_spring_summer
  Sep-Feb → tcm_seasonal_autumn_winter
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.crm.models import User
    from src.broadcaster.weather_service import WeatherCondition

logger = logging.getLogger("broadcaster.composer")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

HKT = timezone(timedelta(hours=8))
BUBBLE_MAX = 150   # hard cap per bubble for broadcasts (tighter than normal)
MAX_BUBBLES = 2

_CARD_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "knowledge_base" / "faq"
_SPRING_SUMMER_CARD = _CARD_DIR / "tcm_seasonal_spring_summer.json"
_AUTUMN_WINTER_CARD = _CARD_DIR / "tcm_seasonal_autumn_winter.json"
_PRODUCT_CATALOG = (
    Path(__file__).resolve().parent.parent.parent / "data" / "products" / "product_catalog.json"
)

# Regex guard — reject any bubble that leaks prices
_PRICE_RE = re.compile(r"HK\$\d+|\$\d+|港幣\s*\d+|價錢|售價")

# ---------------------------------------------------------------------------
# Product catalog loader
# ---------------------------------------------------------------------------


def _load_product_names(product_ids: list[str]) -> list[dict]:
    """Return name + key_benefit for a list of product IDs. Fails silently."""
    try:
        catalog = json.loads(_PRODUCT_CATALOG.read_text(encoding="utf-8"))
        by_id = {p["product_id"]: p for p in catalog.get("products", [])}
        return [
            {"id": pid, "name": by_id[pid]["name"], "benefit": by_id[pid].get("key_benefit", "")}
            for pid in product_ids
            if pid in by_id
        ]
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not load product catalog: %s", exc)
        return []

# ---------------------------------------------------------------------------
# Season card loader
# ---------------------------------------------------------------------------


def _load_season_card(month: int) -> str:
    """Return truncated core_answer from the appropriate seasonal card."""
    path = _SPRING_SUMMER_CARD if 3 <= month <= 8 else _AUTUMN_WINTER_CARD
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        answer: str = raw["knowledge_card"]["core_content"]["core_answer"]
        # Truncate to first ~800 chars so prompt stays lean
        return answer[:800]
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not load season card: %s", exc)
        return ""


# ---------------------------------------------------------------------------
# Composer
# ---------------------------------------------------------------------------


async def compose_broadcast(
    llm: object,
    user: "User",
    condition: "WeatherCondition",
) -> list[str]:
    """Generate 1-2 HK Canto broadcast bubbles.

    Returns a list of bubble strings (1-2 items). Falls back to a safe
    generic message if the LLM call fails or produces garbage.
    """
    now = datetime.now(HKT)
    season_tip = _load_season_card(now.month)
    constitution = user.constitution.value if user.constitution else "unknown"

    system_prompt = """\
你係 Jessica，心宜中醫 Care Plus 嘅中醫健康顧問。
今日你主動向用戶發送一條關心訊息，原因係香港天氣有變化。

⚠️ 重要規則（絕對唔可以違反）：
- 唔好問 follow-up 問題
- 唔好自我介紹（唔好講「我係Jessica」）
- 唔好提任何具體產品名稱、價錢或售價
- 唔好下任何醫療診斷
- 全部用香港廣東話口語（唔好用書面語或普通話）
- 控制在 1-2 條訊息，每條唔超過 150 個字
- 語氣溫暖、關心，像朋友發訊息咁自然

輸出格式（JSON only，唔好有其他文字）：
{"bubbles": ["第一條訊息", "第二條訊息（可選）"]}
"""

    user_prompt = f"""天氣情況：{condition.summary_zh}

用戶體質：{constitution}

季節養生參考（部分節錄，用嚟啟發 tip，唔好逐字抄）：
{season_tip}

根據以上天氣情況同季節養生知識，寫 1-2 條溫暖嘅廣東話關心訊息俾用戶。
記住：唔好問問題、唔好賣嘢、淨係關心同送一個實用 tip 就夠。"""

    try:
        response = await llm.messages.create(
            model="gpt-4o-mini",
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
        logger.warning("Broadcast compose failed (%s): %s — using fallback", type(exc).__name__, exc)
        return _fallback(condition)

    if not bubbles:
        logger.warning("Broadcast compose returned empty bubbles — using fallback")
        return _fallback(condition)

    # Safety checks
    cleaned: list[str] = []
    for bubble in bubbles[:MAX_BUBBLES]:
        if _PRICE_RE.search(bubble):
            logger.warning("Broadcast bubble contains price — stripping: %s", bubble)
            continue
        cleaned.append(bubble[:BUBBLE_MAX])

    return cleaned if cleaned else _fallback(condition)


def _fallback(condition: "WeatherCondition") -> list[str]:
    """Safe generic fallback by condition type."""
    messages: dict[str, list[str]] = {
        "cold_front": [
            "天氣轉涼，記得添衫保暖 🧥 頸同背部最怕寒氣，出門前先加件外套。",
            "寒天飲杯薑棗茶好暖胃，簡單又有效 🫖",
        ],
        "heatwave": [
            "天氣咁熱，記住多飲水💧 最好飲溫水，唔好凍飲——凍嘢雖然即時涼快，但傷脾胃。",
        ],
        "rainstorm": [
            "香港而家落大雨，出行小心⚠️ 如果唔係必要，留喺屋企休息更好。",
        ],
        "humidity_heat": [
            "又熱又濕嘅天，容易脾胃唔舒服。可以飲少少冬瓜荷葉水祛濕消暑 🌿",
        ],
    }
    return messages.get(condition.code, ["天氣變化，記得照顧好自己，有咩唔舒服隨時搵我 🌿"])


# ---------------------------------------------------------------------------
# Purchase follow-up composer
# ---------------------------------------------------------------------------


async def compose_purchase_followup(
    llm: object,
    user: "User",
    products: list[dict],
) -> list[str]:
    """Generate a warm purchase follow-up: 'How's the soup?' 1-2 HK Canto bubbles.

    Args:
        llm: LLMClient instance
        user: CRM User object
        products: list of {id, name, benefit} dicts for purchased products

    Returns:
        1-2 bubble strings. Falls back to generic if LLM fails.
    """
    if not products:
        return _followup_fallback([])

    product_lines = "\n".join(
        f"- {p['name']}：{p['benefit']}" for p in products
    )

    system_prompt = """\
你係 Jessica，心宜中醫 Care Plus 嘅中醫健康顧問。
今日你主動問候一位之前買咗嘢嘅用戶，睇下佢用嘅感受點。

⚠️ 絕對規則：
- 唔好問超過一個問題
- 唔好提任何價錢或售價
- 唔好賣新嘢（呢次係純關心，唔係 pitch）
- 全部用香港廣東話口語
- 控制在 1-2 條訊息，每條唔超過 150 個字
- 語氣溫暖自然，像朋友隔幾日後問候

輸出格式（JSON only）：
{"bubbles": ["第一條訊息", "第二條訊息（可選）"]}
"""

    user_prompt = f"""用戶購買咗以下產品：
{product_lines}

用戶體質：{user.constitution.value if user.constitution else 'unknown'}

請寫 1-2 條廣東話訊息，溫暖地問佢：
1. 有冇飲/用到嗰個產品
2. 感覺點樣、有冇幫到佢

記住：唔好賣嘢、唔好提價錢，純粹係朋友式關心。"""

    try:
        response = await llm.messages.create(
            model="gpt-4o-mini",
            max_tokens=300,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        raw = response.content[0].text.strip()

        if raw.startswith("```"):
            raw = re.sub(r"^```[a-z]*\n?", "", raw)
            raw = re.sub(r"\n?```$", "", raw)

        data = json.loads(raw)
        bubbles = [b.strip() for b in data.get("bubbles", []) if b.strip()]

    except Exception as exc:  # noqa: BLE001
        logger.warning("Purchase followup compose failed (%s): %s — using fallback", type(exc).__name__, exc)
        return _followup_fallback(products)

    if not bubbles:
        return _followup_fallback(products)

    cleaned: list[str] = []
    for bubble in bubbles[:MAX_BUBBLES]:
        if _PRICE_RE.search(bubble):
            logger.warning("Followup bubble contains price — stripping: %s", bubble)
            continue
        cleaned.append(bubble[:BUBBLE_MAX])

    return cleaned if cleaned else _followup_fallback(products)


def _followup_fallback(products: list[dict]) -> list[str]:
    """Generic fallback when LLM fails."""
    if products:
        name = products[0]["name"]
        return [
            f"嗨！上次你訂咗{name}，有冇機會飲到呀？🌿",
            "飲完感覺點？有咩唔舒服或者想了解嘅，隨時同我講 😊",
        ]
    return ["嗨！上次買嘅嘢有冇用到呀？🌿 有咩感覺或者問題，隨時搵我！"]
