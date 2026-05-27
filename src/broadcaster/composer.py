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

from src.llm import DEFAULT_MODEL

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

_KB_ROOT = Path(__file__).resolve().parent.parent.parent / "data" / "knowledge_base"
_CARD_DIR = _KB_ROOT / "faq"
_SPRING_SUMMER_CARD = _CARD_DIR / "tcm_seasonal_spring_summer.json"
_AUTUMN_WINTER_CARD = _CARD_DIR / "tcm_seasonal_autumn_winter.json"
_PRODUCT_CATALOG = (
    Path(__file__).resolve().parent.parent.parent / "data" / "products" / "product_catalog.json"
)

# Weekly tea tip card
_TEA_CARD = _KB_ROOT / "soups" / "tcm_food_therapy_teas.json"

# Weekly acupressure tip cards
_ACUPRESSURE_PAIN_CARD = _CARD_DIR / "tcm_acupressure_pain.json"
_ACUPRESSURE_ENERGY_STRESS_CARD = _CARD_DIR / "tcm_acupressure_energy_stress.json"
_ACUPRESSURE_BEAUTY_CARD = _CARD_DIR / "tcm_acupressure_beauty.json"
_ACUPRESSURE_WEIGHT_CARD = _CARD_DIR / "tcm_acupressure_weight_slim.json"

# Monthly food tip card
_FOOD_THERAPY_SEASONAL_CARD = _KB_ROOT / "soups" / "tcm_food_therapy_seasonal.json"

# Weekly sleep tip card
_SLEEP_INSOMNIA_CARD = _CARD_DIR / "tcm_sleep_insomnia.json"

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
            model=DEFAULT_MODEL,
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


# ---------------------------------------------------------------------------
# Solar term tip composer
# ---------------------------------------------------------------------------


async def compose_solar_term_tip(
    llm: object,
    user: "User",
    term_name_zh: str,
    term_focus_zh: str,
    term_tip_zh: str,
    organ_zh: str,
) -> list[str]:
    """Generate a 節氣養生 tip for the current solar term. 1-2 HK Canto bubbles."""
    constitution = user.constitution.value if user.constitution else "unknown"

    system_prompt = """\
你係 Jessica，心宜中醫 Care Plus 嘅中醫健康顧問。
今日係香港嘅一個重要節氣，你主動向用戶分享一條節氣養生 tip。

⚠️ 規則：
- 唔好問 follow-up 問題
- 唔好提任何價錢或產品名稱
- 全部用香港廣東話口語（唔好書面語）
- 1-2 條訊息，每條唔超過 150 個字
- 語氣親切自然，像朋友傳知識咁

輸出格式（JSON only）：
{"bubbles": ["第一條訊息", "第二條訊息（可選）"]}
"""

    user_prompt = f"""今日節氣：{term_name_zh}
養生重點：{term_focus_zh}（對應臟腑：{organ_zh}）
中醫建議：{term_tip_zh}
用戶體質：{constitution}

根據以上節氣資料，寫 1-2 條廣東話養生訊息俾用戶，要提一下今日係{term_name_zh}同埋中醫上可以做咩。如果用戶有特定體質，可以輕輕個人化。"""

    try:
        response = await llm.messages.create(
            model=DEFAULT_MODEL,
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
        logger.warning("Solar term compose failed (%s) — fallback", type(exc).__name__)
        return [f"今日係{term_name_zh} 🌿 {term_tip_zh[:100]}"]

    cleaned = [b[:BUBBLE_MAX] for b in bubbles[:MAX_BUBBLES] if b and not _PRICE_RE.search(b)]
    return cleaned if cleaned else [f"今日係{term_name_zh} 🌿 {term_tip_zh[:100]}"]


# ---------------------------------------------------------------------------
# Constitution recheck composer
# ---------------------------------------------------------------------------


async def compose_constitution_recheck(
    llm: object,
    user: "User",
) -> list[str]:
    """Generate a gentle 3-month constitution re-assessment nudge. 1-2 bubbles."""
    constitution = user.constitution.value if user.constitution else "unknown"

    system_prompt = """\
你係 Jessica，心宜中醫 Care Plus 嘅中醫健康顧問。
你主動聯絡一位之前做過體質評估嘅用戶，提醒佢體質係會變嘅，建議佢定期重新評估。

⚠️ 規則：
- 唔好賣嘢，呢次係純粹關心
- 唔好提價錢
- 廣東話口語
- 1-2 條訊息，每條唔超過 150 個字
- 溫暖輕鬆，唔好太正式

輸出格式（JSON only）：
{"bubbles": ["第一條訊息", "第二條訊息（可選）"]}
"""

    user_prompt = f"""用戶上次評估體質係：{constitution}
距今已大約 3 個月。

請寫 1-2 條廣東話訊息，溫柔提醒用戶：
- 中醫體質唔係固定嘅，會隨季節、壓力、飲食變化
- 可以重新評估睇下有冇改善
- 可以傳一張舌頭相俾你，或者重新回答幾條問題

語氣要輕鬆，像朋友關心咁，唔好太像推銷或提醒。"""

    try:
        response = await llm.messages.create(
            model=DEFAULT_MODEL,
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
        logger.warning("Constitution recheck compose failed (%s) — fallback", type(exc).__name__)
        return _constitution_recheck_fallback(constitution)

    cleaned = [b[:BUBBLE_MAX] for b in bubbles[:MAX_BUBBLES] if b and not _PRICE_RE.search(b)]
    return cleaned if cleaned else _constitution_recheck_fallback(constitution)


def _constitution_recheck_fallback(constitution: str) -> list[str]:
    return [
        f"嗨！上次你評估係{constitution}體質，已經過咗幾個月喇 🌿",
        "體質係會變嘅，特別係換季後。有時間嘅話可以傳張舌頭相俾我，睇下而家體質點？😊",
    ]


# ---------------------------------------------------------------------------
# Tongue progress nudge (monthly)
# ---------------------------------------------------------------------------


async def compose_tongue_nudge(
    llm: object,
    user: "User",
) -> list[str]:
    """Generate a gentle monthly nudge for users to re-upload a tongue photo.

    Completes the 舌診進度追蹤 (TongueProgress) feature loop — without this,
    users never come back to re-upload, and the before/after comparison
    feature stays dormant.
    """
    constitution = user.constitution.value if user.constitution else "unknown"
    n_prior_photos = len(user.tongue_photos)

    system_prompt = """\
你係 Jessica，心宜中醫 Care Plus 嘅中醫健康顧問。
你主動聯絡一位之前做過舌診嘅用戶，邀請佢再影一張脷相，
等你可以對比變化、報告調理進度。

⚠️ 規則：
- 唔好賣嘢，純粹關心 + 想睇進度
- 唔好提價錢
- 廣東話口語
- 1-2 條訊息，每條唔超過 150 個字
- 溫暖、好奇、令用戶有興趣再影一張

輸出格式（JSON only）：
{"bubbles": ["第一條訊息", "第二條訊息（可選）"]}
"""

    user_prompt = f"""用戶體質：{constitution}
已有 {n_prior_photos} 張歷史脷相。
距上次影脷相大約 1 個月。

請寫 1-2 條廣東話訊息，邀請用戶再影一張脷相：
- 提一提佢之前影過、可以對比
- 提示影相小貼士（自然光、伸出脷、唔好啱啱刷牙）
- 唔需要解釋好多 — 短、輕鬆、令人想拎電話影一張就 send 過嚟

語氣：好奇 + 輕鬆，唔好像 spam reminder。"""

    try:
        response = await llm.messages.create(
            model=DEFAULT_MODEL,
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
        logger.warning("Tongue nudge compose failed (%s) — fallback", type(exc).__name__)
        return _tongue_nudge_fallback(constitution)

    cleaned = [b[:BUBBLE_MAX] for b in bubbles[:MAX_BUBBLES] if b and not _PRICE_RE.search(b)]
    return cleaned if cleaned else _tongue_nudge_fallback(constitution)


def _tongue_nudge_fallback(constitution: str) -> list[str]:
    return [
        f"嗨！上次你影脷相已經一個月喇 📷 你嘅{constitution}體質調理得點？",
        "得閒影返張新嘅俾我，我幫你睇下進度 — 自然光、伸出脷、唔好啱啱刷牙就 OK 😊",
    ]


# ---------------------------------------------------------------------------
# Card loader helpers (new features)
# ---------------------------------------------------------------------------


def _load_kb_card(path: Path) -> str:
    """Return truncated core_answer from a knowledge card JSON. Max 800 chars."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        answer: str = raw["knowledge_card"]["core_content"]["core_answer"]
        return answer[:800]
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not load KB card %s: %s", path.name, exc)
        return ""


def _load_tea_card() -> str:
    """Return truncated tea card content."""
    return _load_kb_card(_TEA_CARD)


def _load_acupressure_card(category: str) -> str:
    """Return acupressure KB card content for the given category."""
    card_map = {
        "pain": _ACUPRESSURE_PAIN_CARD,
        "energy_stress": _ACUPRESSURE_ENERGY_STRESS_CARD,
        "beauty": _ACUPRESSURE_BEAUTY_CARD,
        "weight": _ACUPRESSURE_WEIGHT_CARD,
    }
    path = card_map.get(category, _ACUPRESSURE_ENERGY_STRESS_CARD)
    return _load_kb_card(path)


def _pick_acupressure_category(user: "User") -> str:
    """Choose acupressure category based on user pain_points and tags."""
    pain_points = [p.lower() for p in (user.pain_points or [])]
    tags = [t.lower() for t in (user.tags or [])]
    combined = pain_points + tags

    pain_keywords = {"頭痛", "肩頸", "腰痛", "痛"}
    if any(kw in combined for kw in pain_keywords):
        return "pain"

    energy_keywords = {"失眠", "壓力", "焦慮", "唔夠瞓"}
    if any(kw in combined for kw in energy_keywords):
        return "energy_stress"

    beauty_keywords = {"皮膚", "暗瘡", "美容"}
    if any(kw in combined for kw in beauty_keywords):
        return "beauty"

    weight_keywords = {"肥", "減重", "消腫"}
    if any(kw in combined for kw in weight_keywords):
        return "weight"

    return "energy_stress"


def _load_food_seasonal_card() -> str:
    """Return truncated seasonal food therapy card content."""
    return _load_kb_card(_FOOD_THERAPY_SEASONAL_CARD)


def _load_sleep_card() -> str:
    """Return truncated sleep insomnia card content."""
    return _load_kb_card(_SLEEP_INSOMNIA_CARD)


def _month_to_season_zh(month: int) -> str:
    """Map month to TCM season name in Chinese."""
    if 3 <= month <= 5:
        return "春季"
    if 6 <= month <= 8:
        return "夏季"
    if month == 9:
        return "長夏"
    if 10 <= month <= 11:
        return "秋季"
    return "冬季"


# ---------------------------------------------------------------------------
# Weekly tea tip composer
# ---------------------------------------------------------------------------


async def compose_weekly_tea_tip(llm: object, user: "User") -> list[str]:
    """Generate 1-2 HK Canto bubbles for the weekly tea tip broadcast.

    Personalised to user constitution. Falls back to a safe generic tip.
    """
    constitution = user.constitution.value if user.constitution else "unknown"
    tea_knowledge = _load_tea_card()

    system_prompt = """\
你係 Jessica，心宜中醫 Care Plus 嘅中醫健康顧問。
今日你主動向用戶分享一條每週茶療養生 tip。

⚠️ 重要規則（絕對唔可以違反）：
- 唔好問 follow-up 問題
- 唔好自我介紹（唔好講「我係Jessica」）
- 唔好提任何具體產品名稱、價錢或售價
- 唔好下任何醫療診斷
- 全部用香港廣東話口語（唔好用書面語或普通話）
- 控制在 1-2 條訊息，每條唔超過 150 個字
- 語氣溫暖、親切，像朋友分享知識咁自然

輸出格式（JSON only，唔好有其他文字）：
{"bubbles": ["第一條訊息", "第二條訊息（可選）"]}
"""

    user_prompt = f"""用戶體質：{constitution}

茶療養生參考（部分節錄，用嚟啟發 tip，唔好逐字抄）：
{tea_knowledge}

根據用戶體質同以上茶療知識，寫 1-2 條溫暖嘅廣東話養生訊息。
提醒用戶今週可以飲邊款茶、點飲、對佢體質有咩好處。
記住：唔好問問題、唔好賣嘢、淨係送一個實用茶療 tip 就夠。"""

    try:
        response = await llm.messages.create(
            model=DEFAULT_MODEL,
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
        logger.warning(
            "Weekly tea compose failed (%s): %s — using fallback",
            type(exc).__name__, exc,
        )
        return _tea_fallback(constitution)

    if not bubbles:
        return _tea_fallback(constitution)

    cleaned = [b[:BUBBLE_MAX] for b in bubbles[:MAX_BUBBLES] if b and not _PRICE_RE.search(b)]
    return cleaned if cleaned else _tea_fallback(constitution)


def _tea_fallback(constitution: str) -> list[str]:
    """Safe generic tea tip fallback."""
    tips: dict[str, list[str]] = {
        "氣虛質": ["今週試下飲紅棗桂圓茶 🍵 補氣暖身，對氣虛體質特別好！"],
        "陽虛質": ["天氣唔穩定，陽虛體質記得飲杯薑棗茶暖身 🫖 驅寒效果好好！"],
        "陰虛質": ["陰虛體質今週可以飲麥冬菊花茶 🌸 滋陰降火，解決口乾問題。"],
        "痰濕質": ["痰濕體質今週飲荷葉薏米水 🌿 祛濕化痰，幫你排走體內濕氣！"],
        "濕熱質": ["濕熱體質今週飲菊花蜂蜜水 🌼 清熱解毒，舒緩煩躁感。"],
        "血瘀質": ["血瘀體質今週試下飲玫瑰花茶 🌹 活血化瘀，幫助血液循環！"],
        "氣鬱質": ["氣鬱體質今週飲佛手柑茶 🌿 疏肝解鬱，令心情輕鬆啲 😊"],
        "特稟質": ["特稟體質今週飲太子參紅棗茶 🍵 提升免疫力，減少過敏反應。"],
        "平和質": ["恭喜你係平和體質！今週飲枸杞菊花茶 🌼 日常保健，保持健康平衡。"],
    }
    default = ["今週養生茶 tip：飲杯紅棗枸杞茶 🍵 補氣養血，簡單又有效！"]
    return tips.get(constitution, default)


# ---------------------------------------------------------------------------
# Weekly acupressure tip composer
# ---------------------------------------------------------------------------


async def compose_weekly_acupressure_tip(llm: object, user: "User") -> list[str]:
    """Generate 1-2 HK Canto bubbles with a weekly acupressure tip.

    Picks the most relevant acupressure card based on user pain_points + tags.
    Falls back to a safe hardcoded tip if LLM fails.
    """
    constitution = user.constitution.value if user.constitution else "unknown"
    category = _pick_acupressure_category(user)
    acupressure_knowledge = _load_acupressure_card(category)

    system_prompt = """\
你係 Jessica，心宜中醫 Care Plus 嘅中醫健康顧問。
今日你主動向用戶分享一條每週穴位按摩 tip。

⚠️ 重要規則（絕對唔可以違反）：
- 唔好問 follow-up 問題
- 唔好自我介紹（唔好講「我係Jessica」）
- 唔好提任何具體產品名稱、價錢或售價
- 唔好下任何醫療診斷
- 全部用香港廣東話口語（唔好用書面語或普通話）
- 控制在 1-2 條訊息，每條唔超過 150 個字
- 語氣溫暖、親切，像朋友分享知識咁自然
- 必須提及一個具體穴位名、位置、按壓方法同功效

輸出格式（JSON only，唔好有其他文字）：
{"bubbles": ["第一條訊息", "第二條訊息（可選）"]}
"""

    user_prompt = f"""用戶體質：{constitution}

穴位養生參考（部分節錄，用嚟啟發 tip，唔好逐字抄）：
{acupressure_knowledge}

根據用戶體質同以上穴位知識，寫 1-2 條溫暖嘅廣東話養生訊息俾用戶。
提醒佢今週可以按邊個穴位、點樣按（位置 + 力度 + 時間）、有咩好處。
記住：唔好問問題、唔好賣嘢，淨係送一個實用穴位 tip 就夠。"""

    try:
        response = await llm.messages.create(
            model=DEFAULT_MODEL,
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
        logger.warning(
            "Weekly acupressure compose failed (%s): %s — using fallback",
            type(exc).__name__, exc,
        )
        return _acupressure_fallback(category)

    if not bubbles:
        return _acupressure_fallback(category)

    cleaned = [b[:BUBBLE_MAX] for b in bubbles[:MAX_BUBBLES] if b and not _PRICE_RE.search(b)]
    return cleaned if cleaned else _acupressure_fallback(category)


def _acupressure_fallback(category: str) -> list[str]:
    """Safe hardcoded acupressure tip fallback by category."""
    tips: dict[str, list[str]] = {
        "pain": ["今週穴位：合谷穴 👋 喺虎口位置，用拇指按壓 1 分鐘，有助緩解頭痛同肩頸痛！"],
        "energy_stress": ["今週穴位：神門穴 🤚 喺手腕內側橫紋尺側，輕輕按壓 1 分鐘，安神助眠、舒緩壓力。"],
        "beauty": ["今週穴位：足三里 🦵 喺膝蓋下四橫指、脛骨外側，每日按壓 1 分鐘，補氣養顏 ✨"],
        "weight": ["今週穴位：豐隆穴 🦵 喺小腿外側中點，每日按壓 1 分鐘，化痰祛濕助消脂！"],
    }
    default = ["今週穴位：神門穴 🤚 喺手腕內側橫紋尺側，輕輕按壓 1 分鐘，安神助眠。"]
    return tips.get(category, default)


# ---------------------------------------------------------------------------
# Appointment prep composer
# ---------------------------------------------------------------------------


async def compose_appointment_prep(llm: object, user: "User") -> list[str]:
    """Generate a warm pre-appointment care message. 1-2 HK Canto bubbles.

    Reminds the user about their upcoming clinic visit, constitution, pain
    points, and one practical prep tip.
    """
    constitution = user.constitution.value if user.constitution else "未知"
    pain_points_str = "、".join(user.pain_points[:3]) if user.pain_points else "暫無記錄"

    system_prompt = """\
你係 Jessica，心宜中醫 Care Plus 嘅中醫健康顧問。
今日你主動提醒一位即將去診所覆診嘅用戶，作出溫馨提示。

⚠️ 重要規則（絕對唔可以違反）：
- 唔好問 follow-up 問題
- 唔好自我介紹（唔好講「我係Jessica」）
- 唔好提任何具體產品名稱、價錢或售價
- 唔好下任何醫療診斷
- 全部用香港廣東話口語（唔好用書面語或普通話）
- 控制在 1-2 條訊息，每條唔超過 150 個字
- 語氣溫暖鼓勵，像朋友提醒咁自然
- 唔好講具體時間（我哋唔知確實時間）

輸出格式（JSON only，唔好有其他文字）：
{"bubbles": ["第一條訊息", "第二條訊息（可選）"]}
"""

    user_prompt = f"""用戶體質：{constitution}
用戶主要不適：{pain_points_str}

請寫 1-2 條溫暖廣東話訊息，提醒用戶：
1. 即將去診所見中醫（唔好講具體時間）
2. 根據佢體質同不適，提一個實用準備 tip（例如：唔使空腹、可以記錄最近不適情況、如有舌頭相可帶埋）
3. 語氣鼓勵、輕鬆，唔好太正式

記住：唔好問問題、唔好賣嘢，純粹係朋友式提醒。"""

    try:
        response = await llm.messages.create(
            model=DEFAULT_MODEL,
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
        logger.warning(
            "Appointment prep compose failed (%s): %s — using fallback",
            type(exc).__name__, exc,
        )
        return _appointment_prep_fallback(user)

    if not bubbles:
        return _appointment_prep_fallback(user)

    cleaned = [b[:BUBBLE_MAX] for b in bubbles[:MAX_BUBBLES] if b and not _PRICE_RE.search(b)]
    return cleaned if cleaned else _appointment_prep_fallback(user)


def _appointment_prep_fallback(user: "User") -> list[str]:
    """Generic fallback for appointment prep."""
    constitution = user.constitution.value if user.constitution else "未知"
    return [
        f"快到見醫師喇！你係{constitution}體質，記得唔使空腹去，可以寫低最近唔舒服嘅情況 📝",
        "如果有舌頭相都可以帶埋俾醫師參考，祝你覆診順利 🌿",
    ]


# ---------------------------------------------------------------------------
# Monthly food tip composer
# ---------------------------------------------------------------------------


async def compose_monthly_food_tip(llm: object, user: "User", month: int) -> list[str]:
    """Generate 1-2 HK Canto bubbles with a monthly seasonal food therapy tip.

    Personalised to user constitution and current season.
    """
    constitution = user.constitution.value if user.constitution else "unknown"
    season_zh = _month_to_season_zh(month)
    food_knowledge = _load_food_seasonal_card()

    system_prompt = """\
你係 Jessica，心宜中醫 Care Plus 嘅中醫健康顧問。
今日你主動向用戶分享本月嘅季節食療養生 tip。

⚠️ 重要規則（絕對唔可以違反）：
- 唔好問 follow-up 問題
- 唔好自我介紹（唔好講「我係Jessica」）
- 唔好提任何具體產品名稱、價錢或售價
- 唔好下任何醫療診斷
- 全部用香港廣東話口語（唔好用書面語或普通話）
- 控制在 1-2 條訊息，每條唔超過 150 個字
- 語氣溫暖、親切，像朋友分享知識咁自然

輸出格式（JSON only，唔好有其他文字）：
{"bubbles": ["第一條訊息", "第二條訊息（可選）"]}
"""

    user_prompt = f"""而家係{season_zh}（{month}月），用戶體質：{constitution}

季節食療參考（部分節錄，用嚟啟發 tip，唔好逐字抄）：
{food_knowledge}

根據用戶體質同{season_zh}特點，寫 1-2 條廣東話食療養生訊息：
- 提 2-3 種今個月宜多食嘅食物（要符合體質）
- 提 1-2 種宜少食或避免嘅食物
- 用中醫角度簡單解釋原因

記住：唔好問問題、唔好賣嘢，淨係分享實用食療知識就夠。"""

    try:
        response = await llm.messages.create(
            model=DEFAULT_MODEL,
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
        logger.warning(
            "Monthly food tip compose failed (%s): %s — using fallback",
            type(exc).__name__, exc,
        )
        return _food_tip_fallback(month, constitution)

    if not bubbles:
        return _food_tip_fallback(month, constitution)

    cleaned = [b[:BUBBLE_MAX] for b in bubbles[:MAX_BUBBLES] if b and not _PRICE_RE.search(b)]
    return cleaned if cleaned else _food_tip_fallback(month, constitution)


def _food_tip_fallback(month: int, constitution: str) -> list[str]:
    """Generic seasonal food tip fallback."""
    season_zh = _month_to_season_zh(month)

    # Map broad constitution groups to fallback advice
    yang_xu_group = {"陽虛質"}
    yin_xu_group = {"陰虛質"}
    shi_re_group = {"濕熱質", "痰濕質"}

    if season_zh == "冬季":
        if constitution in yang_xu_group:
            return ["冬季陽虛體質宜多食羊肉、核桃、黑芝麻 🌰 溫補腎陽，少食生冷食物！"]
        return ["冬季宜多食黑豆、核桃、山藥補腎暖身 🍵 少食生冷，保護脾胃陽氣！"]

    if season_zh == "夏季":
        if constitution in yin_xu_group:
            return ["夏季陰虛體質宜多食百合、蓮子、綠豆 🌿 滋陰清熱，少食辛辣燒烤！"]
        if constitution in shi_re_group:
            return ["夏季濕熱體質宜多食冬瓜、薏米、赤小豆 🌱 祛濕清熱，少食肥膩甜品！"]
        return ["夏季宜多食冬瓜、苦瓜、綠豆消暑祛濕 🌿 少食煎炸燒烤，保護脾胃！"]

    if season_zh in {"春季"}:
        return ["春季宜多食春菜、豆芽、枸杞養肝疏肝 🌱 少食辛辣刺激，幫助肝氣舒展！"]

    if season_zh == "秋季":
        return ["秋季宜多食梨、百合、銀耳潤肺滋陰 🍐 少食辛辣，保持肺部滋潤！"]

    # Late summer / 長夏
    return ["長夏宜多食山藥、蓮子、薏米健脾祛濕 🌿 少食生冷甜食，保護脾胃功能！"]


# ---------------------------------------------------------------------------
# Weekly sleep tip composer
# ---------------------------------------------------------------------------


async def compose_weekly_sleep_tip(llm: object, user: "User") -> list[str]:
    """Generate 1-2 HK Canto bubbles with a weekly TCM sleep wellness tip.

    Personalised to user constitution. Falls back to a safe hardcoded tip.
    """
    constitution = user.constitution.value if user.constitution else "unknown"
    sleep_knowledge = _load_sleep_card()

    system_prompt = """\
你係 Jessica，心宜中醫 Care Plus 嘅中醫健康顧問。
今日你主動向用戶分享一條每週睡眠養生 tip。

⚠️ 重要規則（絕對唔可以違反）：
- 唔好問 follow-up 問題
- 唔好自我介紹（唔好講「我係Jessica」）
- 唔好提任何具體產品名稱、價錢或售價
- 唔好下任何醫療診斷
- 全部用香港廣東話口語（唔好用書面語或普通話）
- 控制在 1-2 條訊息，每條唔超過 150 個字
- 語氣溫暖、親切，像朋友分享知識咁自然

輸出格式（JSON only，唔好有其他文字）：
{"bubbles": ["第一條訊息", "第二條訊息（可選）"]}
"""

    user_prompt = f"""用戶體質：{constitution}

睡眠養生參考（部分節錄，用嚟啟發 tip，唔好逐字抄）：
{sleep_knowledge}

根據用戶體質同以上睡眠知識，寫 1-2 條溫暖嘅廣東話睡眠養生訊息。
提一個具體可以即做嘅 tip（例如：子時前入睡、睡前泡腳、避免睡前用手機、按特定穴位）。
如果有特定體質，根據體質個人化（例如：腎虛體質補腎安神、肝鬱體質疏肝助眠）。
記住：唔好問問題、唔好賣嘢，淨係送一個實用睡眠 tip 就夠。"""

    try:
        response = await llm.messages.create(
            model=DEFAULT_MODEL,
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
        logger.warning(
            "Weekly sleep tip compose failed (%s): %s — using fallback",
            type(exc).__name__, exc,
        )
        return _sleep_fallback(constitution)

    if not bubbles:
        return _sleep_fallback(constitution)

    cleaned = [b[:BUBBLE_MAX] for b in bubbles[:MAX_BUBBLES] if b and not _PRICE_RE.search(b)]
    return cleaned if cleaned else _sleep_fallback(constitution)


def _sleep_fallback(constitution: str) -> list[str]:
    """Safe hardcoded sleep tip fallback by constitution."""
    tips: dict[str, list[str]] = {
        "氣虛質": ["氣虛體質宜早瞓，最好子時（晚上11點）前入睡補氣 💤 睡前可按神門穴安神。"],
        "陽虛質": ["陽虛體質宜睡前用熱水泡腳15分鐘 🦶 加幾片薑，溫陽助眠效果好好！"],
        "陰虛質": ["陰虛體質睡前唔好用手機 📵 可以喝少少溫牛奶或蜂蜜水，滋陰有助入睡。"],
        "痰濕質": ["痰濕體質宜早瞓早起，睡前唔好食嘢 🌙 側睡有助排濕，改善睡眠質素。"],
        "濕熱質": ["濕熱體質睡前避免辛辣食物，可以按太衝穴（腳背拇趾間）舒緩煩躁助眠 💤"],
        "血瘀質": ["血瘀體質宜睡前按揉足三里穴促進血循環 🦵 保持房間空氣流通，有助深層睡眠。"],
        "氣鬱質": ["氣鬱體質睡前可以做幾個深呼吸舒展肝氣 🌬️ 或者聽輕柔音樂放鬆心情再入睡。"],
        "特稟質": ["特稟體質宜保持固定睡眠時間，睡前用溫水洗鼻 💤 減少過敏原影響，幫助安睡。"],
        "平和質": ["恭喜你係平和體質！保持子時前入睡嘅習慣 🌙 睡前30分鐘遠離手機，睡眠質素更好。"],
    }
    default = ["今晚記得早啲瞓 💤 中醫建議子時（晚上11點）前入睡，最能補充元氣，養好身體！"]
    return tips.get(constitution, default)
