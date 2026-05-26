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
        "intent": "pitch_products" | "answer_pricing" | "share_catalog" | "no_match"
                | "purchase_confirmed" | "order_received" | "delivery_address_received",
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
import re
from typing import Any

from src.llm import DEFAULT_MODEL, LLMClient

from src.agents.base import SpecialistInput, SpecialistName, SpecialistOutput
from src.crm.models import Promotion
from src.tools import prompt_overrides
from src.tools.pitch_playbook import PitchPlaybook
from src.tools.product_catalog import ProductCatalog, ProductMatch
from src.tools.promotions import PromotionsLoader

logger = logging.getLogger("agents.sales")

MAX_PRODUCTS_PER_TURN = 3
MIN_CANDIDATES_TO_INVOKE_LLM = 1

# ---------------------------------------------------------------------------
# temp_state keys — namespaced to avoid collisions with other agents
# ---------------------------------------------------------------------------
_TS_AWAITING_ADDRESS = "order_awaiting_delivery"   # bool: True when collecting address
_TS_PENDING_ORDER_ID = "order_pending_product_id"  # str: product_id being fulfilled
_TS_PENDING_ORDER_NAME = "order_pending_product_name"  # str: display name for writer


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
        playbook: PitchPlaybook | None = None,
        model: str = DEFAULT_MODEL,
        max_tokens: int = 500,
    ) -> None:
        self._client = client
        self._catalog = catalog or ProductCatalog()
        self._promotions = promotions or PromotionsLoader()
        try:
            self._playbook = playbook or PitchPlaybook()
        except Exception as exc:  # noqa: BLE001
            logger.warning("PitchPlaybook unavailable: %s", exc)
            self._playbook = None
        self._model = model
        self._max_tokens = max_tokens

    async def run(
        self, inp: SpecialistInput
    ) -> tuple[SpecialistOutput, dict[str, Any]]:
        user = inp.user

        # Detect purchase order message FIRST — highest priority.
        # When user clicks the wa.me purchase link, they send exactly:
        #   「想訂【彭魚鰓解毒湯 HK$120】」
        # This arrives at Jessica's number. Parse it, confirm the order,
        # update CRM, ask for delivery address.
        parsed_order = _parse_order_message(inp.user_message, self._catalog)
        if parsed_order is not None:
            return (
                self._order_received_output(user, parsed_order),
                _no_llm_usage(),
            )

        # Mid-delivery-address collection — user is replying with their
        # address after an order was received. Route here before any pitch
        # logic so the address doesn't get misinterpreted as a symptom.
        if user.temp_state.get(_TS_AWAITING_ADDRESS):
            return (
                self._handle_address_reply(user, inp.user_message),
                _no_llm_usage(),
            )

        # Detect past-tense purchase confirmation ("我訂咗" / "買咗") as a
        # secondary fallback — user may have ordered out-of-band or via voice.
        if _is_purchase_confirmation(inp.user_message) and user.products_pitched:
            return (
                self._purchase_confirmed_output(user),
                _no_llm_usage(),
            )

        # Detect "where to buy / 邊度買" intent. When user explicitly asks
        # about how/where to purchase, we always show real products with
        # names + prices + images — never deflect to customer service.
        wants_where = _wants_where_to_buy(inp.user_message)
        if wants_where:
            return (
                self._where_to_buy_output(user, inp.user_message),
                _no_llm_usage(),
            )

        # Playbook category match — if message hits a clear category
        # (skin/cough/eye/etc.), surface ONLY those products + the
        # category angle. Beats generic catalog match.
        if self._playbook is not None:
            cats = self._playbook.match_categories(inp.user_message, limit=1)
            if cats:
                return (
                    self._playbook_output(user, cats[0], inp.user_message),
                    _no_llm_usage(),
                )

        # Detect ointment intent — user explicitly asks about creams /
        # 藥膏 / 塗. Hard-code surface all 3 ointments with images.
        if _wants_ointment_local(inp.user_message):
            return (
                self._ointments_output(user),
                _no_llm_usage(),
            )

        # Detect "show me soups" repeat — user already saw free recipes
        # and is asking again. Planner has routed here on purpose; surface
        # all 10 paid soups with images.
        if _wants_soups_local(inp.user_message):
            return (
                self._soups_output(user),
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
                system=prompt_overrides.resolve("sales_system", _SYSTEM),
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
            "writer_must_not_say": [
                "我哋冇新產品",
                "我哋唔賣",
                "市售產品",
                "唔係我哋自己做",
                "WhatsApp 我哋",
                "+852 5241 7448",
                "wa.me",
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

    def _playbook_output(
        self, user: Any, category: Any, user_message: str
    ) -> SpecialistOutput:
        """Category-targeted pitch driven by data/promotions/pitch_playbook.json.

        Picks only the products in the category's soup_ids + ointment_ids
        (typically 1-3), uses the category's '方向' angle in the writer
        hint, and ends with the safety + consultation backstop.

        Honours contraindications (e.g. pregnant → no 川芎/活血) by
        reusing ProductCatalog scoring for the safety filter.
        """
        ids = list(category.soup_ids) + list(category.ointment_ids)
        all_p = {p.product_id: p for p in self._catalog.all_products}

        # Safety filter — use ProductCatalog.match_products to get the
        # full contraindication-checked candidate list, then intersect
        # with our playbook ids.
        safe_match = self._catalog.match_products(
            constitution=user.constitution.value if user.constitution else None,
            pain_points=list(user.pain_points),
            already_pitched=[],
            user_tags=list(user.tags),
            user_notes=user.notes,
            max_results=20,
            min_score=0.0,
        )
        # match_products already drops contraindicated products. Build a
        # safe-id set; if it's empty (no signal) fall back to raw catalog
        # but still apply the same contraindication rules.
        safe_ids = {pm.product.product_id for pm in safe_match}
        if not safe_ids:
            # Manual filter for tags-based contraindications (pregnancy)
            tags_lc = " ".join((user.tags or []) + [user.notes or ""]).lower()
            is_pregnant = any(t in tags_lc for t in ("pregnant", "懷孕", "怀孕", "孕婦", "孕妇"))
            for p in all_p.values():
                contras = " ".join(p.contraindications or []).lower()
                if is_pregnant and ("孕" in contras or "活血" in contras or "blood-act" in contras):
                    continue
                safe_ids.add(p.product_id)

        chosen = [
            _product_dict_simple(all_p[pid])
            for pid in ids
            if pid in all_p and pid in safe_ids
        ]
        if not chosen:
            # Fallback to no-match if catalog drift breaks the playbook
            return self._no_match_output(user, [
                {"name": "PitchPlaybook.match", "args": {"key": category.key},
                 "result": {"error": "no matching products in catalog"}}
            ])

        playbook = self._playbook
        offers = _collect_offers(
            self._promotions,
            ["sales_pitch", "ointment_pitch", "soup_pitch", "consultation_backstop"],
        )
        payload = {
            "intent": "pitch_products",
            "products_to_pitch": chosen,
            "active_offers": offers,
            "stage": f"playbook_pitch:{category.key}",
            "playbook_safety": playbook.safety_disclaimer if playbook else "",
            "playbook_backstop": playbook.consultation_backstop if playbook else "",
            "playbook_category_key": category.key,
            "playbook_category_angle": category.pitch_angle,
            "writer_hint": (
                f"用戶嘅情況落入「{category.key}」 category。\n"
                f"Bubble 1 (安全話術): 「{playbook.safety_disclaimer if playbook else ''}」\n"
                f"Bubble 2: 講「如果你主要係 {category.pitch_angle}，可以了解：」\n"
                "之後 bubbles: 列 products_to_pitch 入面每款"
                " (名 + 價錢 + 「方向：…」框架)，每款 1 bubble + 圖。\n"
                f"倒數第二 bubble: 「{playbook.consultation_backstop if playbook else ''}」\n"
                "最後一 bubble: 「想要邊款？或者要我幫你預約視診？同我講聲」\n\n"
                "嚴格遵守：用「方向：」「適合想了解...嘅方向」軟性語；唔講"
                "「你應該買」、「治療」、「療效」、「包好」、「完全治好」"
                "等斷言。"
            ),
            "writer_must_not_say": [
                "你應該買", "治療", "保證療效", "包好", "完全治好",
                "WhatsApp 我哋", "+852 5241 7448", "wa.me",
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
                    "name": "PitchPlaybook.match",
                    "args": {"query": user_message[:80]},
                    "result": {
                        "category": category.key,
                        "products": [p["product_id"] for p in chosen],
                    },
                }
            ],
        )

    def _soups_output(self, user: Any) -> SpecialistOutput:
        """Surface 3 paid soup recommendations targeted by constitution
        + pain points. 唔系倒晒 10 款，係**揀** 3 款最啱。"""
        all_soups = [
            p for p in self._catalog.all_products if p.product_type == "soup"
        ]
        # Personalise via ProductCatalog scoring (handles contraindications
        # for pregnancy etc.). max_results=4 in case top-3 has a tie.
        candidates = self._catalog.match_products(
            constitution=user.constitution.value if user.constitution else None,
            pain_points=list(user.pain_points),
            already_pitched=list(user.products_pitched or []),
            user_tags=list(user.tags),
            user_notes=user.notes,
            max_results=4,
            min_score=0.0,
        )
        if candidates:
            soups = [
                pm.product for pm in candidates
                if pm.product.product_type == "soup"
            ][:3]
            # Top up to 3 with broad fallback if scoring under-picked
            if len(soups) < 3:
                seen = {p.product_id for p in soups}
                for s in sorted(all_soups, key=lambda p: p.price_hkd or 999):
                    if s.product_id in seen:
                        continue
                    if s.product_id in (user.products_pitched or []):
                        continue
                    soups.append(s)
                    seen.add(s.product_id)
                    if len(soups) >= 3:
                        break
        else:
            # No constitution / pain points — show 3 popular/middle-priced
            soups = sorted(
                all_soups, key=lambda p: p.price_hkd or 999
            )[:3]

        products = [_product_dict_simple(p) for p in soups]
        offers = _collect_offers(
            self._promotions, ["soup_pitch", "sales_pitch", "consultation_backstop"]
        )
        constitution_str = (
            user.constitution.value if user.constitution else "未評估"
        )
        playbook = self._playbook
        payload = {
            "intent": "pitch_products",
            "products_to_pitch": products,
            "active_offers": offers,
            "stage": "soup_pitch",
            "user_constitution": constitution_str,
            "playbook_safety": playbook.safety_disclaimer if playbook else "",
            "playbook_backstop": playbook.consultation_backstop if playbook else "",
            "catalog_facts": {
                "total_paid_soups": len(all_soups),
                "shown_now": len(products),
                "made_by": "Care Plus 心宜中醫",
                "selection_basis": (
                    f"按用戶 constitution={constitution_str} + "
                    f"pain_points={list(user.pain_points) or '無'} 揀"
                ),
            },
            "writer_hint": (
                f"用戶想要湯水推介。依家揀咗 {len(products)} 款最啱嘅 "
                f"(依據: 體質 {constitution_str}、需求 "
                f"{list(user.pain_points) or '一般調理'})。\n"
                "Bubble 1 (open): 1 句講「按你嘅情況，我幫你揀咗呢 3 款」。\n"
                f"Bubble 2-{len(products)+1} (每款 1 bubble): 名 + 價錢 + "
                "「方向：xxx」(用軟性語，唔好斷言「治療」)。每款附返圖。\n"
                f"Bubble {len(products)+2} (backstop): 「"
                + (playbook.consultation_backstop if playbook else "")
                + "」\n"
                f"Bubble {len(products)+3} (CTA): 問「想試邊款？同我講你嘅"
                "選擇 + 收件地址，我幫你跟進。」\n"
                "唔好提 WhatsApp 號碼，唔好倒晒 10 款 — focus 呢 3 款。"
            ),
            "writer_must_not_say": [
                "WhatsApp 我哋", "+852 5241 7448", "wa.me",
                "市售產品", "唔係我哋自己做",
                "你應該買", "保證療效", "包好",
            ],
        }
        return SpecialistOutput(
            specialist=SpecialistName.SALES,
            payload=payload,
            suggested_user_state_diff={
                "products_pitched_append": [p["product_id"] for p in products]
            },
            cards_used=[],
            tools_called=[
                {
                    "name": "Sales.soups_pitch",
                    "args": {
                        "constitution": user.constitution.value if user.constitution else None,
                    },
                    "result": {"count": len(products), "ids": [p["product_id"] for p in products]},
                }
            ],
        )

    def _ointments_output(self, user: Any) -> SpecialistOutput:
        """Hard-coded surface of all 3 ointments. Bypasses scoring —
        user explicitly asked for topicals."""
        ointments = [
            p for p in self._catalog.all_products if p.product_type == "ointment"
        ]
        products = [_product_dict_simple(p) for p in ointments]
        offers = _collect_offers(
            self._promotions,
            ["ointment_pitch", "sales_pitch", "consultation_backstop"],
        )
        playbook = self._playbook
        safety = playbook.safety_disclaimer if playbook else ""
        backstop = playbook.consultation_backstop if playbook else ""
        payload = {
            "intent": "pitch_products",
            "products_to_pitch": products,
            "active_offers": offers,
            "stage": "ointment_pitch",
            "playbook_safety": safety,
            "playbook_backstop": backstop,
            "writer_hint": (
                "用戶問藥膏。\n"
                "Bubble 1 (open with 安全話術): 「" + safety + "」\n"
                "Bubble 2-4: 列我哋 3 款藥膏，**每款 1 bubble + 圖**：\n"
                "  · 茶樹綠豆濕敏膏 $90 — 方向：濕敏、皮膚泛紅、敏感護理\n"
                "  · 蛋黃油乳液 $120 — 方向：皮膚乾燥、修護、日常滋潤\n"
                "  · 止痕濕疹膏 $180 — 方向：痕癢、濕疹反覆、需要重點護理\n"
                "Bubble 5 (consultation backstop): 「" + backstop + "」\n"
                "Bubble 6: 問用戶「想要邊款？同我講你嘅選擇 + 收件地址我幫"
                "你跟進。」唔好叫客 WhatsApp 任何外部號碼。\n\n"
                "規矩：用「方向：」「適合想了解...嘅人」呢類軟性語，"
                "絕對唔講「你應該買」或者「治療」「療效」等斷言。"
            ),
            "writer_must_not_say": [
                "你應該買", "治療", "保證療效", "包好",
                "WhatsApp 我哋", "+852 5241 7448", "wa.me",
            ],
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

    def _order_received_output(
        self, user: Any, order: "OrderParsed"
    ) -> SpecialistOutput:
        """User sent the wa.me pre-filled order message — we know exactly what they ordered.

        Records the purchase in CRM and composes an acknowledgment + delivery
        address collection. This is the primary purchase confirmation path.
        """
        needs_address = not (user.location or user.district)

        writer_hint = (
            f"用戶剛剛訂咗：{order.product_name}（HK${order.price_hkd}）。\n"
            "Bubble 1: 溫暖確認收到訂單，講一句產品名 + 感謝（例如「好嘢！"
            f"收到你嘅{order.product_name}訂單 🎉」）。\n"
        )
        if needs_address:
            writer_hint += (
                "Bubble 2: 問收件地址（全名 + 地址 + 電話）。\n"
                "例如：「方便俾我收件人全名、送貨地址同聯絡電話嗎？"
                "我幫你跟診所安排 🙏」\n"
            )
        else:
            writer_hint += (
                f"Bubble 2: 話知道地區係 {user.district or user.location}，"
                "問埋全名同電話確認。\n"
            )
        writer_hint += (
            "Bubble 3（可選）：輕輕提一句保存方法或飲法，一句就夠，唔好太長。\n"
            "唔好再 pitch 其他產品，唔好提價錢，呢轉係確認訂單。"
        )

        # Build updated temp_state: mark that we're awaiting the delivery address.
        # Persist product info so the address-reply handler can reference it.
        new_temp_state = {
            **user.temp_state,
            _TS_AWAITING_ADDRESS: needs_address,  # False if address already known
            _TS_PENDING_ORDER_ID: order.product_id or "",
            _TS_PENDING_ORDER_NAME: order.product_name,
        }

        payload = {
            "intent": "order_received",
            "ordered_product_id": order.product_id,
            "ordered_product_name": order.product_name,
            "price_hkd": order.price_hkd,
            "needs_delivery_address": needs_address,
            "stage": "post_purchase",
            "writer_hint": writer_hint,
        }
        return SpecialistOutput(
            specialist=SpecialistName.SALES,
            payload=payload,
            suggested_user_state_diff={
                "status": "bought",
                "products_purchased_append": [order.product_id] if order.product_id else [],
                "temp_state": new_temp_state,
            },
            cards_used=[],
            tools_called=[
                {
                    "name": "Sales.order_received",
                    "args": {
                        "raw_message": order.raw_text,
                        "product_name": order.product_name,
                        "product_id": order.product_id,
                    },
                    "result": {
                        "status_set": "bought",
                        "needs_address": needs_address,
                    },
                }
            ],
        )

    def _handle_address_reply(self, user: Any, message: str) -> SpecialistOutput:
        """User is replying with their delivery address after placing an order.

        Two cases:
        - Message looks like address info → save, clear state, confirm.
        - Message looks like a question → re-ask gently, keep state alive.
        """
        product_name = user.temp_state.get(_TS_PENDING_ORDER_NAME, "你嘅產品")
        product_id = user.temp_state.get(_TS_PENDING_ORDER_ID, "")

        if not _is_address_content(message):
            # User asked a question or sent something ambiguous — hold the state,
            # re-ask for address after answering.
            payload = {
                "intent": "address_pending_question",
                "pending_product_name": product_name,
                "stage": "post_purchase",
                "writer_hint": (
                    f"用戶係落咗{product_name}單之後問咗一個問題。\n"
                    "Bubble 1: 簡短回答問題（如果係養生/飲法問題就答，否則話唔知）。\n"
                    "Bubble 2: 溫和提醒仍然需要收件資料：「順帶一提，"
                    "方便俾我全名、送貨地址同聯絡電話嗎？我幫你跟診所安排寄出 🙏」"
                ),
            }
            # Keep temp_state unchanged — still awaiting address
            return SpecialistOutput(
                specialist=SpecialistName.SALES,
                payload=payload,
                suggested_user_state_diff={},  # no change
                cards_used=[],
                tools_called=[{
                    "name": "Sales.address_pending",
                    "args": {"message_classified_as": "question"},
                    "result": {"state": "still_awaiting_address"},
                }],
            )

        # Address content received — save it, clear the pending state.
        cleared_temp_state = {
            k: v for k, v in user.temp_state.items()
            if k not in (_TS_AWAITING_ADDRESS, _TS_PENDING_ORDER_ID, _TS_PENDING_ORDER_NAME)
        }

        # Try to extract a HK district for the structured district field.
        detected_district = _extract_district(message) or user.district

        payload = {
            "intent": "delivery_address_received",
            "delivery_info_raw": message.strip(),
            "product_name": product_name,
            "stage": "post_purchase",
            "writer_hint": (
                f"用戶提供咗送貨資料俾{product_name}。\n"
                "Bubble 1: 溫暖確認已收到地址（一句，唔好重複地址）。\n"
                "Bubble 2: 話會轉俾診所安排，叫用戶稍候（唔好承諾具體送貨日期）。\n"
                "Bubble 3: 邀請佢收到貨後話我知感受 😊\n"
                "唔好再 pitch 嘢，唔好提價錢，呢轉係純粹完成訂單流程。"
            ),
        }
        diff: dict[str, Any] = {
            "location": message.strip(),
            "temp_state": cleared_temp_state,
        }
        if detected_district and not user.district:
            diff["district"] = detected_district

        return SpecialistOutput(
            specialist=SpecialistName.SALES,
            payload=payload,
            suggested_user_state_diff=diff,
            cards_used=[],
            tools_called=[{
                "name": "Sales.address_received",
                "args": {
                    "product_id": product_id,
                    "delivery_info_length": len(message),
                    "district_extracted": detected_district,
                },
                "result": {"state": "address_saved", "location_set": True},
            }],
        )

    def _purchase_confirmed_output(self, user: Any) -> SpecialistOutput:
        """User confirmed they placed an order. Record it + signal Writer to celebrate.

        We mark the last-pitched products (up to 3) as purchased, since we
        can't know exactly which item was bought without asking. This is a
        deliberate approximation — close enough for care follow-ups.
        """
        # Identify what was most likely purchased: last 3 pitched products.
        purchased_ids = list(user.products_pitched[-3:])

        # Resolve product names for the writer hint.
        all_products = {p.product_id: p for p in self._catalog.all_products}
        purchased_names = [
            all_products[pid].name for pid in purchased_ids if pid in all_products
        ]

        payload = {
            "intent": "purchase_confirmed",
            "purchased_product_ids": purchased_ids,
            "purchased_product_names": purchased_names,
            "stage": "post_purchase",
            "writer_hint": (
                "用戶確認咗已經落單！\n"
                "Bubble 1: 恭喜 / 好嘢嘅口吻，一句就夠，唔好太長（例如「好嘢！"
                "訂咗就放心喇 🎉」）。\n"
                "Bubble 2: 溫馨提示佢點樣保存 / 飲法（唔知就講「收到貨後包裝上"
                "有說明」）。\n"
                "Bubble 3: 邀請佢飲完之後話我知感受（「飲完記得同我分享吓感覺呀！」）。\n"
                "唔好賣更多嘢，唔好提價錢，唔好問多餘問題 — 今次係純粹慶祝同關心。"
            ),
        }
        return SpecialistOutput(
            specialist=SpecialistName.SALES,
            payload=payload,
            suggested_user_state_diff={
                "status": "bought",
                "products_purchased_append": purchased_ids,
            },
            cards_used=[],
            tools_called=[
                {
                    "name": "Sales.purchase_confirmed",
                    "args": {"pitched_last_3": purchased_ids},
                    "result": {"recorded_as_purchased": purchased_ids},
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
                max_results=3,
                min_score=0.0,        # accept anything
            )
            if not candidates:
                # Truly nothing scored — just take the first 4 from catalog.
                for prod in list(all_products.values())[:4]:  # noqa: PLR2004
                    chosen.append(_product_dict_simple(prod))
            else:
                for pm in candidates[:4]:
                    chosen.append(_product_dict_simple(pm.product))

        offers = _collect_offers(
            self._promotions,
            ["sales_pitch", "sales_close", "consultation_backstop"],
        )
        playbook = self._playbook
        # Detect category from user message + pain_points to add focused
        # pitch angle if available.
        category_angle = ""
        if playbook:
            text_blob = f"{user_message} {' '.join(user.pain_points or [])}"
            cats = playbook.match_categories(text_blob, limit=1)
            if cats:
                category_angle = cats[0].pitch_angle
        payload = {
            "intent": "where_to_buy",
            "products_to_pitch": chosen,
            "active_offers": offers,
            "stage": "where_to_buy",
            "playbook_safety": playbook.safety_disclaimer if playbook else "",
            "playbook_backstop": playbook.consultation_backstop if playbook else "",
            "playbook_category_angle": category_angle,
            "catalog_facts": {
                "total_paid_soups": 10,
                "total_ointments": 3,
                "made_by": "Care Plus 心宜中醫",
            },
            "writer_hint": (
                "用戶問點買 / 想要產品。\n"
                f"Bubble 1: 安全話術「{playbook.safety_disclaimer if playbook else ''}」\n"
                + (f"Bubble 2: 用戶睇起來係 {category_angle} 方向\n" if category_angle else "")
                + "之後 bubbles: 列每個 products_to_pitch 入面嘅產品 "
                "(名 + 價錢 + 「方向：...」框架)，每款 1 bubble + image_url\n"
                "倒數第二 bubble: 「"
                + (playbook.consultation_backstop if playbook else "")
                + "」\n"
                "最後一 bubble: 「想要邊款？同我講你嘅選擇 + 收件地址我幫你跟"
                "進。」**絕對唔好**叫客 WhatsApp 任何外部號碼。\n\n"
                "規矩：用「方向：xxx」框架，唔好用「你應該買」「治療」「療效」"
                "「包好」呢類斷言。"
            ),
            "writer_must_not_say": [
                "我哋冇新產品",
                "市售產品",
                "唔係我哋自己做",
                "WhatsApp 客服問",
                "自己問客服",
                "WhatsApp 我哋",
                "+852 5241 7448",
                "wa.me",
                "你應該買", "保證療效", "包好你", "完全治好",
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


# ---------------------------------------------------------------------------
# Order message parser
# ---------------------------------------------------------------------------

# wa.me pre-filled order format: 想訂【<name> HK$<price>】
_ORDER_RE = re.compile(r"想訂【([^】]+)\s+HK\$(\d+)】")


class OrderParsed:
    """Parsed result from a wa.me order message."""

    __slots__ = ("raw_text", "product_name", "price_hkd", "product_id")

    def __init__(
        self,
        raw_text: str,
        product_name: str,
        price_hkd: int,
        product_id: str | None,
    ) -> None:
        self.raw_text = raw_text
        self.product_name = product_name
        self.price_hkd = price_hkd
        self.product_id = product_id


def _parse_order_message(text: str, catalog: Any) -> "OrderParsed | None":
    """If ``text`` is a wa.me pre-filled order message, parse and return it.

    Matches: 「想訂【彭魚鰓解毒湯 HK$120】」
    Looks up the product ID by name from the catalog (best-effort, None if
    not found — we still record the order even without a known ID).
    Returns None if the text does not match the order format.
    """
    if not text:
        return None
    m = _ORDER_RE.search(text)
    if not m:
        return None

    product_name = m.group(1).strip()
    price_hkd = int(m.group(2))

    # Look up product ID by name (case-insensitive partial match)
    product_id: str | None = None
    for prod in catalog.all_products:
        if product_name in prod.name or prod.name in product_name:
            product_id = prod.product_id
            break

    return OrderParsed(
        raw_text=text,
        product_name=product_name,
        price_hkd=price_hkd,
        product_id=product_id,
    )


def _wants_where_to_buy(text: str) -> bool:
    if not text:
        return False
    return any(kw in text for kw in _WHERE_TO_BUY_KEYWORDS)


# Past-tense purchase confirmation signals — user already placed an order.
# Distinct from _WHERE_TO_BUY_KEYWORDS (which express *intent* to buy).
# All of these indicate a completed action: "咗" suffix or equivalent.
_PURCHASE_CONFIRM_KEYWORDS = (
    "訂咗", "订咗", "落咗單", "落單咗", "落咗order", "落咗 order",
    "買咗", "买咗", "訂好", "订好", "訂好咗",
    "已經訂", "已经订", "已下單", "已下单", "已訂購", "已订购",
    "落咗", "俾咗錢", "付咗款", "付款咗",
    "confirm 咗", "confirmed 咗", "done 喇", "done了", "done咗",
    "搞掂", "搞定", "完成咗", "下咗單",
)


# ---------------------------------------------------------------------------
# Address content helpers
# ---------------------------------------------------------------------------

# Common HK districts for extraction from free-text address replies.
_HK_DISTRICTS: tuple[str, ...] = (
    "尖沙咀", "荃灣", "葵涌", "青衣", "馬鞍山", "將軍澳",
    "鴨脷洲", "黃竹坑", "堅尼地城", "上水", "粉嶺", "大埔", "火炭",
    "大圍", "沙田", "九龍塘", "旺角", "佐敦", "油麻地", "美孚",
    "荔枝角", "黃大仙", "鑽石山", "中環", "銅鑼灣", "北角", "太古",
    "鰂魚涌", "西灣河", "筲箕灣", "灣仔", "金鐘", "上環", "香港仔",
    "烏溪沙", "西貢", "坑口", "寶琳", "元朗", "屯門",
)


def _extract_district(text: str) -> str | None:
    """Return the first HK district found in the text, or None."""
    for d in _HK_DISTRICTS:
        if d in text:
            return d
    return None


def _is_address_content(text: str) -> bool:
    """True if the message looks like delivery address info (not a question).

    Heuristics (in order of confidence):
    - Contains a `？` / `?` → question, not an address.
    - Shorter than 4 chars → too short to be an address (e.g. "ok", "好").
    - Otherwise → treat as address content.

    We err on the side of accepting — users in address-collection state
    are almost always replying with address info, not complex queries.
    """
    stripped = text.strip() if text else ""
    if not stripped:
        return False
    if "？" in stripped or "?" in stripped:
        return False
    if len(stripped) < 4:  # noqa: PLR2004
        return False
    return True


def _is_purchase_confirmation(text: str) -> bool:
    """True if the user is confirming they already placed an order.

    Checks for past-tense purchase language. Only meaningful when the user
    has previously seen a pitch (products_pitched non-empty).
    """
    if not text:
        return False
    return any(kw in text for kw in _PURCHASE_CONFIRM_KEYWORDS)


_OINTMENT_KEYWORDS_LOCAL = (
    "塗", "涂", "搽", "藥膏", "药膏", "外用", "外搽",
    "cream", "ointment", "lotion",
)


def _wants_ointment_local(text: str) -> bool:
    if not text:
        return False
    return any(kw in text for kw in _OINTMENT_KEYWORDS_LOCAL)


_SOUP_KEYWORDS_LOCAL = (
    "湯水", "汤水", "邊款湯", "有咩湯", "有什麼湯", "有什么汤",
    "推介湯", "推荐汤", "湯水推介", "湯水推薦",
)


def _wants_soups_local(text: str) -> bool:
    if not text:
        return False
    return any(kw in text for kw in _SOUP_KEYWORDS_LOCAL)


def _collect_offers(
    promos: PromotionsLoader, stages: list[str]
) -> list[dict[str, Any]]:
    """Pull offers matching any of the given stages, deduped by id."""
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for stage in stages:
        for p in promos.for_stage(stage):
            if p.id in seen:
                continue
            seen.add(p.id)
            out.append(_promo_dict(p))
    return out


def _product_dict_simple(prod: Any) -> dict[str, Any]:
    """Product dict shown to Writer — MUST include 功效 + image so the Writer
    can render rich pitches (name + price + 功效 + 適合 + image), never bare
    name + price.

    Post-launch fix 2026-05-26: previously this returned only product_id /
    name / price / image_url / purchase_url, which forced the Writer to
    say "抗病毒湯 $88" with no context. Now: indications, constitution_match,
    key_benefit, contraindications all surfaced.
    """
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
        "price_display": getattr(prod, "price_display", None) or f"HK${prod.price_hkd}",
        "image_url": image_url,
        "purchase_url": prod.purchase_url,
        # ── Detail fields (REQUIRED for rich pitch) ─────────────────
        "indications": list(prod.indications),                   # 功效 list
        "constitution_match": list(prod.constitution_match),     # 適合體質
        "key_benefit": prod.key_benefit or "",                   # one-liner
        "contraindications": list(prod.contraindications),       # safety
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
    base = os.environ.get(
        "PUBLIC_BASE_URL", "https://tcm-jessica.onrender.com"
    ).rstrip("/")
    image_url = p.image_url or ""
    if image_url and not image_url.startswith(("http://", "https://")):
        rel = image_url[len("data/"):] if image_url.startswith("data/") else image_url
        image_url = f"{base}/{rel}" if not rel.startswith("/") else f"{base}{rel}"
    return {
        "product_id": p.product_id,
        "name": p.name,
        "price_hkd": p.price_hkd,
        "price_display": getattr(p, "price_display", None) or f"HK${p.price_hkd}",
        "image_url": image_url,
        "purchase_url": p.purchase_url,
        "pitch_angle_hint": pitch_angles.get(p.product_id) or _default_angle(match),
        "match_reasons": list(match.match_reasons),
        # ── Detail fields (REQUIRED for rich pitch) ─────────────────
        "indications": list(p.indications),                   # 功效 list
        "constitution_match": list(p.constitution_match),     # 適合體質
        "key_benefit": p.key_benefit or "",                   # one-liner
        "contraindications": list(p.contraindications),       # safety
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
