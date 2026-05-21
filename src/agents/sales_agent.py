"""Sales Agent — pitches paid soups + ointments from 心宜中醫.

Two-stage pipeline (mirrors FAQAgent):
  1. ProductCatalog.match_products(...) — deterministic, no LLM. Filters
     out contraindications (pregnancy → exclude 川芎白芷天麻湯 etc.),
     down-weights already-pitched products, scores remaining candidates.
  2. LLM (Haiku) — pick 1-3 of the top candidates and write a one-sentence
     `pitch_angle_hint` per product. The Writer composes the actual
     user-facing bubble.

If `client is None`, we skip step 2 and return the top-N deterministic
matches with a templated `pitch_angle_hint`. This is the offline mode
used by tests.

Output payload schema:
    {
        "intent": "pitch_products" | "answer_pricing" | "share_catalog" | "no_match",
        "products_to_pitch": [
            {
                "product_id": str,
                "name": str,
                "price_hkd": int,
                "image_url": str,
                "purchase_url": str,
                "pitch_angle_hint": str,
                "match_reasons": [str, ...]
            },
            ...
        ],
        "active_offers": [<promotion dict>, ...],
        "stage": "first_pitch" | "follow_up" | "closing",
        "no_match_reason": str | None
    }

The Sales Agent NEVER produces user-facing copy. Writer composes that.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from src.llm import LLMClient

from src.agents.base import SpecialistInput, SpecialistName, SpecialistOutput
from src.crm.models import Promotion
from src.tools.product_catalog import ProductCatalog, ProductMatch
from src.tools.promotions import PromotionsLoader

logger = logging.getLogger("agents.sales")

DEFAULT_MODEL = "gpt-4o-mini"
MAX_PRODUCTS_PER_TURN = 3
MIN_CANDIDATES_TO_INVOKE_LLM = 1


_SYSTEM = """你係 Jessica 嘅 Sales Specialist —— 揀啱嘅產品比 Writer 推介。

你 *唔* 直接寫俾用戶嘅嘢。淨係輸出 structured data。

輸入：用戶體質 + 主訴 + 已 pitch 過嘅產品 + 候選產品清單
輸出：純 JSON，schema：
{
  "picked_product_ids": ["...", "..."],     // 1-3 個 ID，按優先級排
  "pitch_angles": {
     "<product_id>": "..."                  // 一句廣東話 fragment，講點解呢款啱用戶
  },
  "stage": "first_pitch" | "follow_up" | "closing"
}

規則：
- 揀 1-3 款最啱嘅，唔好亂揀 6-7 款
- pitch_angle 係「fragment」，唔係完整 bubble — 例如「最啱你嘅捱夜失眠 +
  陰虛體質」。唔好寫 "你好" / "我建議" 呢啲開場白，留俾 Writer
- 寫廣東話口語（口語 ≠ 書面語）
- stage:
  - first_pitch = 用戶頭一次睇產品
  - follow_up = 之前 pitch 過，今次跟進 / 加碼
  - closing = 用戶有意買，今次係 closing turn

唔好 markdown，淨係 JSON。"""


class SalesAgent:
    def __init__(
        self,
        *,
        client: LLMClient | None = None,
        catalog: ProductCatalog | None = None,
        promotions: PromotionsLoader | None = None,
        model: str = DEFAULT_MODEL,
        max_tokens: int = 500,
    ) -> None:
        self._client = client
        self._catalog = catalog or ProductCatalog()
        self._promotions = promotions or PromotionsLoader()
        self._model = model
        self._max_tokens = max_tokens

    async def run(
        self, inp: SpecialistInput
    ) -> tuple[SpecialistOutput, dict[str, Any]]:
        user = inp.user

        # Detect "where to buy / 邊度買" intent. When user explicitly asks
        # about how/where to purchase, we always show real products with
        # names + prices + images — never deflect to customer service.
        wants_where = _wants_where_to_buy(inp.user_message)
        if wants_where:
            return (
                self._where_to_buy_output(user, inp.user_message),
                _no_llm_usage(),
            )

        # Detect ointment intent — user explicitly asks about creams /
        # 藥膏 / 塗. Hard-code surface all 3 ointments with images.
        if _wants_ointment_local(inp.user_message):
            return (
                self._ointments_output(user),
                _no_llm_usage(),
            )

        candidates = self._catalog.match_products(
            constitution=user.constitution.value if user.constitution else None,
            pain_points=list(user.pain_points),
            already_pitched=list(user.products_pitched),
            user_tags=list(user.tags),
            user_notes=user.notes,
            max_results=6,  # over-fetch — LLM narrows to 1-3
            # Require a real signal (constitution+5 OR pain_point+3) — a
            # weak "any"-constitution +1 bump should NOT count as a match.
            min_score=3.0,
        )

        # Filter out anything already pitched — the "one new pitch per
        # session" rule. Down-weighted items can sneak above min_score on
        # rich user signal, so we enforce the hard rule HERE.
        candidates = [
            c for c in candidates if c.product.product_id not in user.products_pitched
        ]

        tools_log: list[dict[str, Any]] = [
            {
                "name": "ProductCatalog.match_products",
                "args": {
                    "constitution": user.constitution.value,
                    "pain_points": list(user.pain_points),
                    "already_pitched": list(user.products_pitched),
                },
                "result": {
                    "candidate_count": len(candidates),
                    "top_candidates": [
                        {
                            "product_id": c.product.product_id,
                            "score": c.score,
                            "reasons": list(c.match_reasons),
                        }
                        for c in candidates[:5]
                    ],
                },
            }
        ]

        if not candidates:
            return self._no_match_output(user, tools_log), _no_llm_usage()

        # --- offline mode: deterministic top-N
        if self._client is None or len(candidates) < MIN_CANDIDATES_TO_INVOKE_LLM:
            picked = candidates[:MAX_PRODUCTS_PER_TURN]
            return self._build_output(
                picked=picked,
                stage=_default_stage(user),
                tools_log=tools_log,
                pitch_angles=None,
            ), _no_llm_usage()

        # --- LLM mode
        prompt = _build_pick_prompt(inp, candidates)
        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                system=_SYSTEM,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = "".join(
                b.text for b in response.content if b.type == "text"
            ).strip()
            parsed = _parse_pick(raw)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "sales LLM call/parse failed (%s); falling back to top-%d",
                exc,
                MAX_PRODUCTS_PER_TURN,
            )
            picked = candidates[:MAX_PRODUCTS_PER_TURN]
            return self._build_output(
                picked=picked,
                stage=_default_stage(user),
                tools_log=tools_log,
                pitch_angles=None,
            ), _no_llm_usage()

        picked_ids = parsed.get("picked_product_ids", [])[:MAX_PRODUCTS_PER_TURN]
        picked = _resolve_picks(picked_ids, candidates)
        if not picked:
            # LLM hallucinated IDs — fall back deterministically.
            picked = candidates[:MAX_PRODUCTS_PER_TURN]

        stage = _normalise_stage(parsed.get("stage")) or _default_stage(user)
        output = self._build_output(
            picked=picked,
            stage=stage,
            tools_log=tools_log,
            pitch_angles=parsed.get("pitch_angles", {}),
        )
        usage = {
            "model": self._model,
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        }
        return output, usage

    # -----------------------------------------------------------------
    # Builders
    # -----------------------------------------------------------------

    def _build_output(
        self,
        *,
        picked: list[ProductMatch],
        stage: str,
        tools_log: list[dict[str, Any]],
        pitch_angles: dict[str, str] | None,
    ) -> SpecialistOutput:
        promo_stage = "sales_close" if stage == "closing" else "product_pitch"
        offers = self._promotions.for_stage(
            promo_stage, applies_to="product_pitch"
        )
        # `product_pitch` lives under trigger_stage="sales_close" in the
        # current offers file — try the inverse too so promos surface in
        # both first_pitch and closing turns.
        if not offers and promo_stage == "product_pitch":
            offers = self._promotions.for_stage(
                "sales_close", applies_to="product_pitch"
            )

        products = [
            _product_dict(match, pitch_angles or {}) for match in picked
        ]
        pitched_ids = [m.product.product_id for m in picked]

        payload = {
            "intent": "pitch_products" if products else "no_match",
            "products_to_pitch": products,
            "active_offers": [_promo_dict(p) for p in offers],
            "stage": stage,
            "no_match_reason": None,
        }
        suggested_diff: dict[str, Any] = {}
        if pitched_ids:
            # We can't know previous list from here without re-injecting
            # it, so the orchestrator merges; safer to provide additive
            # "_extend" hint as a list of new ids.
            suggested_diff["products_pitched_append"] = pitched_ids

        return SpecialistOutput(
            specialist=SpecialistName.SALES,
            payload=payload,
            suggested_user_state_diff=suggested_diff,
            cards_used=_cards_used_for(picked),
            tools_called=tools_log,
        )

    def _no_match_output(
        self, user: Any, tools_log: list[dict[str, Any]]
    ) -> SpecialistOutput:
        reason = _no_match_reason(user)
        payload = {
            "intent": "no_match",
            "products_to_pitch": [],
            "active_offers": [],
            "stage": _default_stage(user),
            "no_match_reason": reason,
            # Hard fact — always available even when nothing new to pitch.
            "order_channel": {
                "whatsapp": os.environ.get("ORDER_WHATSAPP", "+852 5241 7448"),
                "url": f"https://wa.me/{os.environ.get('ORDER_WHATSAPP', '+852 5241 7448').lstrip('+').replace(' ', '')}",
            },
            "writer_must_not_say": [
                "我哋冇新產品",
                "我哋唔賣",
                "市售產品",
                "唔係我哋自己做",
            ],
            "catalog_facts": {
                "total_paid_soups": 10,
                "total_ointments": 3,
                "made_by": "Care Plus 心宜中醫",
            },
        }
        return SpecialistOutput(
            specialist=SpecialistName.SALES,
            payload=payload,
            cards_used=[],
            tools_called=tools_log,
        )

    def _ointments_output(self, user: Any) -> SpecialistOutput:
        """Hard-coded surface of all 3 ointments. Bypasses scoring —
        user explicitly asked for topicals."""
        ointments = [
            p for p in self._catalog.all_products if p.product_type == "ointment"
        ]
        products = [_product_dict_simple(p) for p in ointments]
        whatsapp = os.environ.get("ORDER_WHATSAPP", "+852 5241 7448")
        clean = whatsapp.lstrip("+").replace(" ", "")
        payload = {
            "intent": "pitch_products",
            "products_to_pitch": products,
            "active_offers": [
                _promo_dict(p)
                for p in self._promotions.for_stage(
                    "sales_close", applies_to="product_pitch"
                )
            ],
            "stage": "ointment_pitch",
            "order_channel": {
                "whatsapp": whatsapp,
                "url": f"https://wa.me/{clean}",
            },
            "writer_hint": (
                "用戶問藥膏。**必須**列晒呢 3 款 (名 + 價錢 + 1 句用途)，"
                "每款 1 bubble + 圖。最尾講 order WhatsApp 連結。"
            ),
        }
        return SpecialistOutput(
            specialist=SpecialistName.SALES,
            payload=payload,
            suggested_user_state_diff={
                "products_pitched_append": [p["product_id"] for p in products],
            },
            cards_used=[],
            tools_called=[
                {
                    "name": "Sales.ointments_lookup",
                    "args": {},
                    "result": {"count": len(products)},
                }
            ],
        )

    def _where_to_buy_output(
        self, user: Any, user_message: str
    ) -> SpecialistOutput:
        """User asked HOW / WHERE to buy. Always show real products with
        names + prices + images + order channel — never deflect.

        Pick logic:
          - If user has products_pitched → re-show those (continuity).
          - Otherwise → broad catalog match (no constitution required)
            and surface top 3-4 most-relevant soups.
        """
        all_products = {p.product_id: p for p in self._catalog.all_products}

        chosen: list[dict[str, Any]] = []
        if user.products_pitched:
            for pid in user.products_pitched[-3:]:
                prod = all_products.get(pid)
                if prod is not None:
                    chosen.append(_product_dict_simple(prod))

        if not chosen:
            # Broad pitch — no constitution filter. Let the catalog rank
            # by pain_points / tags it has, else fall back to first N.
            candidates = self._catalog.match_products(
                constitution=user.constitution.value if user.constitution else None,
                pain_points=list(user.pain_points),
                already_pitched=[],   # ignore one-pitch rule for explicit ask
                user_tags=list(user.tags),
                user_notes=user.notes,
                max_results=4,
                min_score=0.0,        # accept anything
            )
            if not candidates:
                # Truly nothing scored — just take the first 4 from catalog.
                for prod in list(all_products.values())[:4]:  # noqa: PLR2004
                    chosen.append(_product_dict_simple(prod))
            else:
                for pm in candidates[:4]:
                    chosen.append(_product_dict_simple(pm.product))

        whatsapp = os.environ.get("ORDER_WHATSAPP", "+852 5241 7448")
        clean = whatsapp.lstrip("+").replace(" ", "")
        payload = {
            "intent": "where_to_buy",
            "products_to_pitch": chosen,
            "active_offers": [
                _promo_dict(p)
                for p in self._promotions.for_stage(
                    "sales_close", applies_to="product_pitch"
                )
            ],
            "stage": "where_to_buy",
            "order_channel": {
                "whatsapp": whatsapp,
                "url": f"https://wa.me/{clean}",
            },
            "catalog_facts": {
                "total_paid_soups": 10,
                "total_ointments": 3,
                "made_by": "Care Plus 心宜中醫",
            },
            "writer_hint": (
                "用戶問點買 / 想要產品。**必須**列晒 products_to_pitch 入面每"
                "款 (名 + 價錢 HK$)，每款 1 個 bubble，並且每款都要附返"
                "image_url 落 media_to_send。最尾加一個 bubble 講 order "
                "WhatsApp 號碼 + 連結。**絕對唔好**只講「我哋有 10 款」"
                "然後叫客 WhatsApp 客服自己問 — 必須立刻 show 產品。"
            ),
            "writer_must_not_say": [
                "我哋冇新產品",
                "市售產品",
                "唔係我哋自己做",
                "WhatsApp 客服問",
                "自己問客服",
            ],
        }
        return SpecialistOutput(
            specialist=SpecialistName.SALES,
            payload=payload,
            suggested_user_state_diff={
                "products_pitched_append": [p["product_id"] for p in chosen]
            },
            cards_used=[],
            tools_called=[
                {
                    "name": "Sales.where_to_buy_lookup",
                    "args": {
                        "products_pitched_count": len(user.products_pitched),
                        "chosen_count": len(chosen),
                    },
                    "result": {"reshown": [p["product_id"] for p in chosen]},
                }
            ],
        )


# ---------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------


# Phrases that signal "tell me HOW / WHERE to buy these" — distinct
# from general buying intent. When the user is past the diagnose phase
# and already saw a pitch, this triggers a re-show with order info
# instead of fabricating a "no_match".
_WHERE_TO_BUY_KEYWORDS = (
    "邊度買", "邊度可以買", "點買", "點訂", "點訂購", "邊度有得買",
    "落單", "預訂", "預定", "where", "buy", "order",
    "點樣買", "點樣訂", "WhatsApp", "whatsapp", "連結", "link",
    "係咪你哋", "你哋自己", "你哋出", "你哋整",  # "Is it your own product?"
)


def _wants_where_to_buy(text: str) -> bool:
    if not text:
        return False
    return any(kw in text for kw in _WHERE_TO_BUY_KEYWORDS)


_OINTMENT_KEYWORDS_LOCAL = (
    "塗", "涂", "搽", "藥膏", "药膏", "外用", "外搽",
    "cream", "ointment", "lotion",
)


def _wants_ointment_local(text: str) -> bool:
    if not text:
        return False
    return any(kw in text for kw in _OINTMENT_KEYWORDS_LOCAL)


def _product_dict_simple(prod: Any) -> dict[str, Any]:
    """Minimal product dict for re-shows (no pitch_angle_hint needed)."""
    base = os.environ.get(
        "PUBLIC_BASE_URL", "https://tcm-jessica.onrender.com"
    ).rstrip("/")
    image_url = prod.image_url or ""
    if image_url and not image_url.startswith(("http://", "https://")):
        # Convert relative path like 'data/media/products/soups/...'
        rel = image_url[len("data/"):] if image_url.startswith("data/") else image_url
        image_url = f"{base}/{rel}" if not rel.startswith("/") else f"{base}{rel}"
    return {
        "product_id": prod.product_id,
        "name": prod.name,
        "price_hkd": prod.price_hkd,
        "image_url": image_url,
        "purchase_url": prod.purchase_url,
    }


def _no_llm_usage() -> dict[str, Any]:
    return {"model": "no_llm", "input_tokens": 0, "output_tokens": 0}


def _default_stage(user: Any) -> str:
    if user.products_pitched:
        return "follow_up"
    return "first_pitch"


def _normalise_stage(raw: Any) -> str | None:
    if raw in ("first_pitch", "follow_up", "closing"):
        return raw
    return None


def _no_match_reason(user: Any) -> str:
    parts: list[str] = []
    const = user.constitution.value if user.constitution else None
    if not const or const == "unknown":
        parts.append("體質未知（建議先做體質測試）")
    if not user.pain_points:
        parts.append("用戶未講主訴")
    if user.products_pitched:
        already = "、".join(user.products_pitched[:3])
        parts.append(f"剩餘候選都已 pitch 過 ({already})")
    return "；".join(parts) or "冇任何匹配產品"


def _resolve_picks(
    picked_ids: list[str], candidates: list[ProductMatch]
) -> list[ProductMatch]:
    by_id = {m.product.product_id: m for m in candidates}
    resolved: list[ProductMatch] = []
    for pid in picked_ids:
        if pid in by_id:
            resolved.append(by_id[pid])
    return resolved


def _product_dict(
    match: ProductMatch, pitch_angles: dict[str, str]
) -> dict[str, Any]:
    p = match.product
    return {
        "product_id": p.product_id,
        "name": p.name,
        "price_hkd": p.price_hkd,
        "image_url": p.image_url,
        "purchase_url": p.purchase_url,
        "pitch_angle_hint": pitch_angles.get(p.product_id) or _default_angle(match),
        "match_reasons": list(match.match_reasons),
    }


def _default_angle(match: ProductMatch) -> str:
    """Fallback pitch_angle when no LLM picked one."""
    p = match.product
    benefit = p.key_benefit or (p.indications[0] if p.indications else "養生")
    reasons = "、".join(match.match_reasons[:2]) if match.match_reasons else "一般推薦"
    return f"{benefit}（{reasons}）"


def _promo_dict(promo: Promotion) -> dict[str, Any]:
    return {
        "id": promo.id,
        "title_zh": promo.title_zh,
        "description_zh": promo.description_zh,
        "applies_to": list(promo.applies_to),
        "discount_pct": promo.discount_pct,
        "free_item": promo.free_item,
    }


def _cards_used_for(matches: list[ProductMatch]) -> list[str]:
    cards: list[str] = []
    for m in matches:
        if m.product.product_type == "soup" and "tcm_paid_soups" not in cards:
            cards.append("tcm_paid_soups")
        if m.product.product_type == "ointment" and "tcm_paid_ointments" not in cards:
            cards.append("tcm_paid_ointments")
    return cards


def _build_pick_prompt(
    inp: SpecialistInput, candidates: list[ProductMatch]
) -> str:
    user = inp.user
    lines = []
    for c in candidates[:6]:
        p = c.product
        lines.append(
            f"- {p.product_id} | {p.name} | HK${p.price_hkd} | "
            f"score={c.score:.1f} | reasons=[{'、'.join(c.match_reasons)}] | "
            f"benefit={p.key_benefit}"
        )
    candidates_txt = "\n".join(lines) or "(冇候選)"

    pitched_txt = "、".join(user.products_pitched) or "(冇)"

    return f"""用戶資料：
- 體質: {user.constitution.value}
- 主訴: {'、'.join(user.pain_points) or '(未填)'}
- 之前 pitch 過: {pitched_txt}
- 今次訊息: 「{inp.user_message}」

候選產品（已排序，分數高 = 越啱）：
{candidates_txt}

揀 1-3 款（最多 3）。輸出 JSON。"""


def _parse_pick(text: str) -> dict[str, Any]:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"no JSON: {text[:200]!r}")
    parsed = json.loads(text[start : end + 1])
    if not isinstance(parsed, dict):
        raise ValueError("parsed JSON is not an object")
    return parsed
