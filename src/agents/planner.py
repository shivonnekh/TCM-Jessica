"""Planner Agent — decides which specialist(s) handle each turn.

Inputs:
- CRM snapshot (User) — status, constitution, pain_points, history
- Buffered user message (post-merge)
- Last 5 turns of history

Output: PlannerDecision
  - specialists: 1-2 (ordered: primary first)
  - mode: "solo" | "sequential" | "parallel"
  - reasoning, notes_for_writer, proactive_hint

Design:
- Specialist menu auto-built from SPECIALIST_CATALOG (DRY — no
  hand-edited list in the prompt). Adding a new specialist = add entry
  in base.py.
- Rule fast-paths bypass the LLM for deterministic cases (tongue photo,
  first-touch greeting).
- Proactive hints fire when CRM state suggests a follow-up the user
  hasn't explicitly asked for (e.g. constitution_done but no pitch yet
  → suggest sales). The Planner can choose to route on these hints OR
  let them propagate to the Writer as a soft prompt.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from src.llm import LLMClient, PLANNER_MODEL

from src.agents.base import (
    SPECIALIST_CATALOG,
    PlannerDecision,
    SpecialistName,
    render_specialist_menu_zh,
)
from src.agents.emotion import detect_emotion
from src.agents.sales_agent import _ORDER_RE, _TS_AWAITING_ADDRESS
from src.crm.models import Constitution, User, UserStatus
from src.tools import prompt_overrides

logger = logging.getLogger("agents.planner")

# Planner uses the higher-tier model (gpt-4o by default) — routing decisions
# benefit materially from better reasoning, even though it costs ~3-5x more.
DEFAULT_MODEL = PLANNER_MODEL


# -------------------------------------------------------------------
# System prompt — built at import-time from the specialist catalog.
# -------------------------------------------------------------------


_SYSTEM_TEMPLATE = """你係 Jessica 嘅 Planner — 一個路由 brain。
你唔對用戶講嘢，淨係決定下面幾個 specialist 邊個處理呢 turn。

可用 specialist:
{menu}

可用 mode:
- solo: 只揀 1 個 specialist (specialists 數組長度 = 1)
- sequential: 揀 2 個，先跑第 0 個，再跑第 1 個 (例如 constitution 完先 sales)
- parallel: 揀 2 個，同時跑 (例如 faq + appointment — output 獨立)

每 turn 最多 2 個 specialist。

路由規則 (硬規矩):
1. 有脷相 (media_urls 非空) → 必須包 constitution，mode=solo
2. 用戶頭一次見面 (status=new + 冇對話歷史) + 簡單問候 → greeting，mode=solo
3. 純閒聊 / 寒暄 / 朋友式問候 (status != new + 冇 medical/product/appointment
   intent) → **casual**，唔係 greeting。Greeting 只做 first-touch。
4. 用戶問知識問題 + 同時想預約 → [faq, appointment] mode=parallel
5. 體質剛診斷完 (status=constitution_done + 用戶仲想繼續) → [constitution, sales] mode=sequential，或者直接 sales solo
6. 用戶 confirm 已 propose 嘅 appointment slot → appointment solo (Phase 4)
7. 用戶問「免費 / 唔使錢 / 自己煮 / 食譜 / DIY / 點煲 / 邊度有得買材料」→
   FAQ solo (KB 有 128 款免費 HK 中醫師家用湯水食譜)。重要：剛 pitch 完
   付費產品唔代表所有後續問題都 route 去 Sales — 用戶 reject 咗付費就要
   俾佢免費 alternatives。
8. 用戶問「點煮 / 材料 / 做法 / 啲咩用 / 邊度買到」+ 任何湯水/食物 名 →
   FAQ solo (KB 有食譜詳情)
9. 用戶問「邊款」「點解」「乜嘢」「邊度」「幾耐」嘅知識問題（同時冇預約意向）
   → FAQ solo

Proactive hints (soft):
- status=constitution_done 但 products_pitched 空 → 寫 proactive_hint="ready_for_pitch"
- 用戶連續 3 turn 都係閒聊 → proactive_hint="re_engage"
- status=churned → proactive_hint="gentle_reactivate"

輸出純 JSON，唔好 markdown:
{{
  "specialists": ["...", "..."],          // 1 or 2
  "mode": "solo" | "sequential" | "parallel",
  "reasoning": "一句中文，講你點解咁路由",
  "notes_for_writer": "...",              // 比 Writer 嘅 tone/urgency hint，可以空
  "proactive_hint": "..."                 // CRM 推導出嚟嘅 follow-up signal，可以空
}}"""


def _build_system_prompt() -> str:
    return _SYSTEM_TEMPLATE.format(menu=render_specialist_menu_zh())


# -------------------------------------------------------------------
# Planner
# -------------------------------------------------------------------


class PlannerAgent:
    def __init__(
        self,
        client: LLMClient,
        *,
        model: str = DEFAULT_MODEL,
        max_tokens: int = 500,
    ) -> None:
        self._client = client
        self._model = model
        self._max_tokens = max_tokens

    @property
    def _system(self) -> str:
        """Resolve live override every call so /admin edits take effect immediately."""
        return prompt_overrides.resolve("planner_system", _build_system_prompt())

    async def decide(
        self,
        user: User,
        user_message: str,
        media_urls: list[str] | None = None,
    ) -> tuple[PlannerDecision, dict[str, Any]]:
        media_urls = media_urls or []

        # Rule-based fast paths
        override = _rule_overrides(user, user_message, media_urls)
        if override is not None:
            return override, {
                "model": "rule",
                "input_tokens": 0,
                "output_tokens": 0,
                "shortcut": True,
            }

        # LLM-based routing
        prompt = _build_user_prompt(user, user_message, media_urls)
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            system=self._system,
            messages=[{"role": "user", "content": prompt}],
        )

        raw_text = "".join(
            block.text for block in response.content if block.type == "text"
        ).strip()

        try:
            data = _extract_json(raw_text)
            decision = PlannerDecision.model_validate(data)
        except Exception as exc:  # noqa: BLE001
            logger.warning("planner JSON parse failed (%s); raw=%r", exc, raw_text)
            decision = PlannerDecision(
                specialists=[SpecialistName.GREETING],
                mode="solo",
                reasoning=f"fallback after parse error: {exc}",
            )

        usage = {
            "model": self._model,
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "shortcut": False,
        }
        return decision, usage


# -------------------------------------------------------------------
# Rule overrides — deterministic short-circuits
# -------------------------------------------------------------------


def _rule_overrides(
    user: User, user_message: str, media_urls: list[str]
) -> PlannerDecision | None:
    """Skip the LLM for routes where the answer is obvious."""

    # wa.me pre-filled order message: 「想訂【product HK$price】」
    # This arrives when the user clicks the purchase link in Jessica's chat.
    # Route to Sales immediately — it will parse the product and collect address.
    if _ORDER_RE.search(user_message):
        return PlannerDecision(
            specialists=[SpecialistName.SALES],
            mode="solo",
            reasoning="rule: wa.me order message detected → confirm order + collect address",
            notes_for_writer=(
                "用戶係透過購買連結落單。Sales Agent 已經識別產品同定咗 CRM。"
                "唔好再 pitch，唔好再介紹產品 — 依照 writer_hint 確認訂單 + 問收件資料。"
            ),
        )

    # Mid-delivery-address collection — user is responding to "please send
    # your address". Route to Sales so it can save the address and close
    # the order flow. Mirrors the appointment_proposed pattern.
    if user.temp_state.get(_TS_AWAITING_ADDRESS):
        return PlannerDecision(
            specialists=[SpecialistName.SALES],
            mode="solo",
            reasoning="rule: awaiting delivery address → Sales (address collection)",
            notes_for_writer=(
                "用戶正在提供收件資料。Sales Agent 已處理。"
                "依照 writer_hint 確認收到地址，唔好 pitch 嘢。"
            ),
        )

    # Tongue photo handling:
    #   - User has prior tongue history + known constitution → TONGUE_PROGRESS
    #     (track improvement instead of re-diagnosing)
    #   - First-time tongue OR unknown constitution → CONSTITUTION (existing flow)
    if media_urls:
        if (
            user.constitution != Constitution.UNKNOWN
            and len(user.tongue_photos) >= 1
        ):
            return PlannerDecision(
                specialists=[SpecialistName.TONGUE_PROGRESS],
                mode="solo",
                reasoning="rule: new tongue photo + prior history → progress tracking",
                notes_for_writer=(
                    "【舌診進度追蹤】Tongue Progress Agent 已分析新脷相 + 同上次比較。"
                    "Writer 直接用 payload.narrative_zh 作為主體回覆，加自然開場。"
                    "可以提到 changes 入面嘅具體變化。唔好突然 pitch 產品。"
                ),
            )
        if user.status in (UserStatus.NEW, UserStatus.QUALIFIED):
            return PlannerDecision(
                specialists=[SpecialistName.CONSTITUTION],
                mode="solo",
                reasoning="rule: media present → constitution",
            )

    # User is mid-appointment confirmation → don't second-guess
    if user.temp_state.get("appointment_proposed"):
        return PlannerDecision(
            specialists=[SpecialistName.APPOINTMENT],
            mode="solo",
            reasoning="rule: pending appointment confirmation",
        )

    # User is mid-constitution flow (already started MCQ) → stay
    if (
        user.temp_state.get("constitution_tongue_findings")
        and user.constitution == Constitution.UNKNOWN
    ):
        return PlannerDecision(
            specialists=[SpecialistName.CONSTITUTION],
            mode="solo",
            reasoning="rule: mid constitution assessment",
        )

    # ── Farewell detection → warm closing summary ──────────────────────
    # Only fire when the user has prior history (pure first-touch farewell
    # is pathological; just let Greeting handle it).
    stripped = user_message.strip()
    if user.conversation_history and _is_farewell(stripped):
        return PlannerDecision(
            specialists=[SpecialistName.GREETING],
            mode="solo",
            reasoning="rule: farewell detected → closing summary",
            notes_for_writer=_build_closing_notes(user),
        )

    # ── Simple greeting ─────────────────────────────────────────────────
    # First-touch → onboarding. Returning → casual + proactive follow-up.
    if stripped in _SIMPLE_GREETINGS:
        if not user.conversation_history:
            return PlannerDecision(
                specialists=[SpecialistName.GREETING],
                mode="solo",
                reasoning="rule: first-touch greeting",
            )
        # Returning user — inject proactive CRM context so Writer can
        # ask a meaningful follow-up question instead of generic "點呀？"
        return PlannerDecision(
            specialists=[SpecialistName.CASUAL],
            mode="solo",
            reasoning="rule: returning user greeting — proactive follow-up",
            notes_for_writer=_build_returning_hint(user),
        )

    # ── 急救穴位 reactive — acute pain detection ────────────────────────
    # Fires for "我頭好痛 😭" type messages — user is in distress AND has
    # a recognised symptom. Route to FAQ + CASUAL so we lead with empathy
    # + immediate 30-second acupoint relief. Stays out of the way for
    # casual mentions like "我有頭痛問題" (no acute signal).
    from src.agents.acute_pain import detect_acute_pain  # noqa: PLC0415

    acute = detect_acute_pain(user_message)
    if acute is not None:
        backup_line = (
            f"後備穴位：{acute.backup_acupoint_zh}（如果第一個按完未夠）"
            if acute.backup_acupoint_zh else ""
        )
        return PlannerDecision(
            specialists=[SpecialistName.CASUAL, SpecialistName.FAQ],
            mode="parallel",
            reasoning=f"rule: 急救 — acute {acute.symptom_zh} detected",
            notes_for_writer=(
                f"【急救穴位 — 即刻緩解】\n\n"
                f"用戶有急性「{acute.symptom_zh}」，宜先 give relief 而唔係解釋原因。\n\n"
                f"主穴：{acute.primary_acupoint_zh}\n"
                f"位置：{acute.location_zh}\n"
                f"按法：{acute.press_instruction_zh}\n"
                f"中醫角度：{acute.tcm_rationale_zh}\n"
                f"{backup_line}\n\n"
                f"Writer 嘅 3-bubble 順序：\n"
                f"1. 短共情（一句，例：「咁辛苦😭」）\n"
                f"2. 即刻畀解決方法 — 穴位位置 + 按法（用清晰嘅指引，唔好過長）\n"
                f"3. 簡短中醫詮釋 + 問一句跟進「按完點啊？」\n\n"
                f"FAQ Agent 會搵相關 KB cards 同自動 attach 穴位相 / 影片。\n"
                f"唔好喺呢一 turn pitch 產品 — 純關心。"
            ),
        )

    # User explicitly wants free / DIY content → KB lookup, NOT Sales.
    # Even if last turn was a Sales pitch — they may be rejecting paid
    # options and want free alternatives.
    if _wants_free_or_diy(user_message):
        return PlannerDecision(
            specialists=[SpecialistName.FAQ],
            mode="solo",
            reasoning="rule: user wants free / DIY recipes → KB lookup",
            notes_for_writer=(
                "用戶想要免費 / 自己煮嘅選擇。記住我哋 KB 有 128 款香港中醫師"
                "publish 嘅家用食譜。唔好講「冇免費」之類嘅錯嘢。"
            ),
        )

    # FUNNEL: user asks for soups again → pivot to paid pitch. We
    # detect "repeat ask" from any of three signals:
    #   (a) temp_state.faq_recipes_shown_count >= 1
    #   (b) user message includes "再" / "more" / "其他" / "另外" — even
    #       first turn, the wording itself implies they want more
    #   (c) prior Jessica reply in last 4 turns mentioned a recipe title
    #       (e.g. healthy-food.hk free recipe — they're cycling back)
    if _wants_soup_list(user_message):
        shown_count = int((user.temp_state or {}).get("faq_recipes_shown_count", 0))
        wants_more = _wants_more(user_message)
        history_shows_recipes = _history_has_recipe_mention(user.conversation_history)
        if shown_count >= 1 or wants_more or history_shows_recipes:
            why = (
                f"shown_count={shown_count}, wants_more={wants_more},"
                f" history_recipe={history_shows_recipes}"
            )
            return PlannerDecision(
                specialists=[SpecialistName.SALES],
                mode="solo",
                reasoning=f"rule: repeat soup ask ({why}) → pivot to paid",
                notes_for_writer=(
                    "用戶想要更多湯水推介 — pivot 去付費。**必須**列晒我哋 10 款"
                    "預製湯水：每款 名 + 價錢 + 1 句功效 + 圖片。最後問「想要"
                    "邊款，我幫你跟進」。唔好再推免費食譜。"
                ),
            )

    # User has finished constitution + now shows buying interest →
    # NOW pitch paid products (Sales). Constitution itself does FREE
    # recipes; Sales kicks in when user signals they want convenience.
    if (
        user.status == UserStatus.CONSTITUTION_DONE
        and _wants_to_buy(user_message)
    ):
        return PlannerDecision(
            specialists=[SpecialistName.SALES],
            mode="solo",
            reasoning="rule: constitution_done + buying intent → sales pitch",
            notes_for_writer=(
                "用戶之前做完體質評估，而家表達咗想了解付費產品。可以正式介紹"
                "預製湯水 / 藥膏。"
            ),
        )

    # User wants to book a clinic visit / online consult / asks about
    # location → Appointment Agent (regardless of status).
    if _wants_appointment(user_message):
        return PlannerDecision(
            specialists=[SpecialistName.APPOINTMENT],
            mode="solo",
            reasoning="rule: user wants appointment / clinic / online consult",
            notes_for_writer=(
                "用戶想預約 / 睇醫師 / 問診所。引導佢揀「到診」or「網上視診」。"
                "已揀模式就 collect 地區或者直接 propose slot — 切記要跟到尾，"
                "唔好淨係提一句然後 drop。"
            ),
        )

    # User asks about 藥膏 / 外用 / 搽 → Sales solo, prioritise ointments.
    if _wants_ointment(user_message):
        return PlannerDecision(
            specialists=[SpecialistName.SALES],
            mode="solo",
            reasoning="rule: user wants ointment / topical → sales (prioritise ointments)",
            notes_for_writer=(
                "用戶問「塗 / 藥膏 / 外用」— 必須列我哋 3 款藥膏：茶樹綠豆濕敏膏 "
                "$90 (輕度痕癢、蚊咬)、蛋黃油乳液 $120 (敏感肌、BB)、"
                "止痕濕疹膏 $180 (中至重度濕疹)。每款 1 bubble + 圖。"
                "如果用戶問「邊一款適合我」→ 直接喺對話度幫佢推介："
                "問下情況 (輕度／中度／嚴重) + 邀請佢影脷相做體質測試，"
                "唔好叫佢 WhatsApp 任何外部號碼。"
            ),
        )

    # User mentions skin condition (痕/癢/濕疹/暗瘡/痘) → Sales (ointments)
    # first. These are conditions we have specific products for. We
    # still let Planner route to Constitution on its own merits later;
    # this rule fires when buying intent is implicit in the complaint.
    if _has_skin_condition(user_message) and user.status != UserStatus.NEW:
        return PlannerDecision(
            specialists=[SpecialistName.SALES],
            mode="solo",
            reasoning="rule: skin condition → ointments-first sales",
            notes_for_writer=(
                "用戶提到皮膚問題（痕/癢/濕疹/暗瘡/痘）。我哋有 3 款藥膏專門針對："
                "茶樹綠豆濕敏膏 $90, 蛋黃油乳液 $120, 止痕濕疹膏 $180。"
                "直接列晒，唔好繞去湯水或者體質評估。"
            ),
        )

    # User asks for "other options / alternatives" → enumerate all
    # solution tracks (soups + ointments + clinic + recipes).
    if _wants_alternatives(user_message):
        return PlannerDecision(
            specialists=[SpecialistName.SALES, SpecialistName.APPOINTMENT],
            mode="parallel",
            reasoning="rule: user wants alternatives — surface multi-track options",
            notes_for_writer=(
                "用戶問「其他方法 / 仲有冇 / 還有」。要列**所有**選擇途徑："
                "(1) 湯水 + 藥膏 (Sales payload), (2) 到診 + 網上視診 "
                "(Appointment payload), (3) 免費食譜 (KB)。唔好淨講一樣。"
            ),
        )

    # First-touch BUT user already mentioned a symptom in their opening
    # message → compact intro PLUS Constitution Agent on the same turn,
    # so we don't ask "what's bothering you?" after the user already
    # told us.
    if (
        user.status == UserStatus.NEW
        and not user.conversation_history
        and _user_has_complaint_lite(user_message)
    ):
        return PlannerDecision(
            specialists=[SpecialistName.GREETING, SpecialistName.CONSTITUTION],
            mode="sequential",
            reasoning="rule: first-touch with symptom — compact intro + tongue ask",
            notes_for_writer=(
                "用戶第一句已經講咗症狀。短短自我介紹後，acknowledge 佢嘅問題，"
                "然後直接問脷相 — 唔好叫佢再講一次唔舒服喺邊。"
            ),
        )

    # 情志調理 — user mentions emotional distress → connect to TCM organ mapping.
    # Fires only when no higher-priority rule matched (e.g. not a product query,
    # not an appointment ask). Routes CASUAL + FAQ in parallel:
    #   CASUAL: empathy + warmth
    #   FAQ: finds KB cards for the affected organ (stress/sleep/urban lifestyle)
    # notes_for_writer carries the 七情 → 臟腑 frame so Writer can make the
    # TCM connection feel natural, not preachy.
    emotion = detect_emotion(user_message)
    if emotion is not None:
        probe_str = "、".join(emotion.probe_symptoms[:3])
        return PlannerDecision(
            specialists=[SpecialistName.CASUAL, SpecialistName.FAQ],
            mode="parallel",
            reasoning=f"rule: emotion detected ({emotion.emotion_zh}) → 七情/{emotion.tcm_emotion} 傷{emotion.organ_zh}",
            notes_for_writer=(
                f"【情志調理】用戶表達了「{emotion.emotion_zh}」嘅情緒。\n"
                f"中醫角度：{emotion.imbalance_zh}。\n"
                f"Writer 嘅任務：\n"
                f"1. 先共情（一句就夠，唔好過度）\n"
                f"2. 輕輕帶出中醫嘅角度：「中醫話{emotion.tcm_emotion}傷{emotion.organ_zh}…」\n"
                f"3. 探問相關身體症狀：佢有冇試過 {probe_str}？\n"
                f"4. 如果有症狀確認 → 自然帶出{emotion.soup_angle}嘅養生方向\n"
                f"5. 唔好硬銷，呢轉係關心，唔係 pitch\n"
                f"FAQ Agent 會提供相關 KB 內容，Writer 用嚟豐富回答即可。"
            ),
        )

    # 症狀記憶 — fire only if no other rule matched, and user has history
    # showing a recurring symptom we haven't explicitly addressed this session.
    if user.conversation_history:
        from src.agents.symptom_memory import detect_recurring_symptom  # noqa: PLC0415
        recurring = detect_recurring_symptom(user)
        if recurring is not None:
            return PlannerDecision(
                specialists=[SpecialistName.CASUAL, SpecialistName.FAQ],
                mode="parallel",
                reasoning=f"rule: recurring symptom '{recurring}' detected in history",
                notes_for_writer=(
                    f"【症狀記憶】用戶最近多次提到「{recurring}」。\n"
                    f"Writer 嘅任務：溫柔地提到「你最近好似幾次都有提到 {recurring}」，\n"
                    f"問下係咪一直有呢個困擾，然後提供相關中醫養生建議。\n"
                    f"FAQ Agent 會搜尋相關 KB 內容，用嚟豐富回答。\n"
                    f"唔好突然推銷產品 — 呢次係關心同了解。"
                ),
            )

    return None


# ── Simple greeting token set ───────────────────────────────────────────────
_SIMPLE_GREETINGS = frozenset({
    "hi", "Hi", "HI", "hello", "Hello", "hey", "Hey",
    "你好", "你好啊", "你好呀", "喂", "喂喂", "早", "早晨", "早上好",
    "下午好", "晚上好", "午安", "晚安",
})

# ── Farewell keywords ────────────────────────────────────────────────────────
_FAREWELL_TOKENS = frozenset({
    "拜拜", "再見", "再见", "bye", "bye bye", "goodbye",
    "謝謝", "谢谢", "多謝", "多谢", "thx", "thanks", "thank you", "thank u",
    "唔緊要", "唔使", "夠喇", "夠了", "够了", "知道了", "明白了",
    "good night", "goodnight", "晚安", "好啦", "好了",
    "ok", "OK", "okay", "okok",
})


def _is_farewell(text: str) -> bool:
    """Return True if the message looks like a goodbye / sign-off.

    Heuristic (post-launch fix 2026-05-26):
      - Empty / question marks → False (can't be a wrap-up)
      - Exact token match → True
      - Token appears in the TAIL (last 12 chars) of the message → True
        Sign-offs sit at the end. Embedded mentions (e.g. "我唔係想再見你")
        sit in the middle and are correctly rejected.
    """
    lower = text.lower().strip()
    if not lower:
        return False
    if "?" in lower or "？" in lower:
        return False
    if lower in _FAREWELL_TOKENS:
        return True
    tail = lower[-12:]
    return any(tok in tail for tok in _FAREWELL_TOKENS)


def _build_closing_notes(user: User) -> str:
    """Build notes_for_writer for a farewell turn — personalised closing summary."""
    parts: list[str] = []

    from src.crm.models import Constitution
    if user.constitution != Constitution.UNKNOWN:
        parts.append(f"體質：{user.constitution.value}")

    if user.pain_points:
        parts.append("關注：" + "、".join(user.pain_points[:3]))

    if user.products_purchased:
        parts.append("已購：" + "、".join(user.products_purchased[:2]))

    if user.notes and len(user.notes) > 10:
        # Trim to first 80 chars so the prompt doesn't bloat
        short = user.notes.strip()[:80].rstrip("，。\n")
        parts.append(f"筆記摘要：{short}…")

    crm_context = "\n   ".join(f"- {p}" for p in parts) if parts else "（未有詳細記錄）"

    return (
        "【對話結束 — 請生成暖心道別訊息】\n\n"
        f"用戶 CRM 記錄：\n   {crm_context}\n\n"
        "Writer 嘅任務（兩至三個 bubble）：\n"
        "1. 輕鬆溫暖嘅道別（一句，唔好太正式）\n"
        "2. 簡單總結今次記低咗啲咩（根據以上 CRM 資料，自然地提）\n"
        "   例：「我幫你記住咗你有失眠同腰痛嘅困擾 📝」\n"
        "3. 提醒隨時可以返嚟（唔係 CTA，係真心邀請）\n"
        "4. 可選：一句應景養生 tip（短，輕鬆，唔係 pitch）\n\n"
        "語氣：像朋友送別，唔好太商業。"
    )


def _build_returning_hint(user: User) -> str:
    """Build notes_for_writer for a returning-user greeting — proactive follow-up."""
    from src.crm.models import Constitution

    hooks: list[str] = []

    # Most recent pain point is the most natural thing to follow up on
    if user.pain_points:
        hooks.append(f"上次提到：「{user.pain_points[-1]}」")

    # Constitution unlocks personalised lifestyle angle
    if user.constitution != Constitution.UNKNOWN:
        hooks.append(f"體質：{user.constitution.value}")

    # Recent purchase — follow up on how it's going
    if user.products_purchased:
        hooks.append(f"買過：{user.products_purchased[-1]}")

    # Freeform notes from memory consolidator
    if user.notes and len(user.notes) > 10:
        short = user.notes.strip()[:100].rstrip("，。\n")
        hooks.append(f"記憶摘要：{short}…")

    if not hooks:
        # No meaningful context yet — just greet warmly
        return (
            "用戶打招呼返嚟，但 CRM 未有太多資料。"
            "Jessica 溫暖地回應，問下今日有咩想傾。"
        )

    context_str = "\n".join(f"   • {h}" for h in hooks)

    return (
        "【回頭用戶打招呼 — 請主動跟進】\n\n"
        f"用戶 CRM 背景：\n{context_str}\n\n"
        "Writer 嘅任務：\n"
        "1. 溫暖歡迎（一句）\n"
        "2. 主動提起之前嘅話題 / 狀況\n"
        "   例：「你上次話有失眠，最近係咪有好啲？😊」\n"
        "   或：「飲完上次介紹嘅湯，感覺點樣？」\n"
        "3. 問一個具體嘅跟進問題（唔係開放式嘅『有咩可以幫你』）\n\n"
        "語氣：像老朋友重遇，自然地記得佢，唔係 CRM lookup。"
    )


# Lightweight version of greeting_agent._user_has_complaint — kept here
# to avoid circular imports. Sync changes if the keyword list changes.
_COMPLAINT_KEYWORDS_LITE = (
    "攰", "累", "倦", "痕", "癢", "痛", "感冒", "咳", "失眠", "便秘",
    "肚瀉", "皮膚", "暗瘡", "濕疹", "敏感", "口乾", "心煩", "唔舒服",
    "問題", "症狀", "病", "氣虛", "陽虛", "陰虛", "濕熱", "痰濕",
)


def _user_has_complaint_lite(text: str) -> bool:
    if not text:
        return False
    return any(kw in text for kw in _COMPLAINT_KEYWORDS_LITE)


# Phrases that signal "user wants the FREE / DIY path" — must route to FAQ
# regardless of prior turn's context, since the KB has 128 free recipes.
_FREE_DIY_KEYWORDS = (
    "免費", "免费", "唔使錢", "唔使钱", "不要錢", "不要钱", "免錢", "免钱",
    "自己煮", "自己煲", "DIY", "食譜", "食谱", "點煮", "点煮", "點煲", "点煲",
    "材料邊度買", "材料邊度有", "邊度有得買材料", "邊度可以買到材料",
    "可唔可以自己整", "可以自己整嗎", "屋企可以煮嗎", "屋企整",
)


def _wants_free_or_diy(text: str) -> bool:
    if not text:
        return False
    return any(kw in text for kw in _FREE_DIY_KEYWORDS)


# General "what soups do you have" intent (broader than free/DIY).
_SOUP_LIST_KEYWORDS = (
    "湯水", "汤水", "有咩湯", "有什麼湯", "有什么汤", "有咩飲",
    "邊款湯", "哪款汤", "推介湯", "推荐汤", "湯水推介",
    "什麼湯水", "什么汤水", "汤水推荐",
)


def _wants_soup_list(text: str) -> bool:
    if not text:
        return False
    return any(kw in text for kw in _SOUP_LIST_KEYWORDS)


# Phrases that signal "give me more" — strong pivot-to-paid signal even
# on first turn (e.g. user lands and says '再嚟啲湯水推介').
_WANTS_MORE_KEYWORDS = (
    "再", "再嚟", "再来", "更多", "其他", "另外", "別嘅", "别的",
    "more", "another", "其他款", "別款", "别款",
)


def _wants_more(text: str) -> bool:
    if not text:
        return False
    return any(kw in text for kw in _WANTS_MORE_KEYWORDS)


_RECIPE_TITLE_MARKERS = (
    "—",      # 「健脾安神—太子參淮蓮紅棗粥」 style
    "healthy-food.hk",
    "免費食譜",
    "家用食譜",
)


def _history_has_recipe_mention(history: Any) -> bool:
    """Did Jessica recently send free-recipe content?"""
    if not history:
        return False
    for msg in list(history)[-6:]:
        if getattr(msg, "role", None) != "jessica":
            continue
        content = (getattr(msg, "content", "") or "")[:600]
        if any(m in content for m in _RECIPE_TITLE_MARKERS):
            return True
    return False


# Buying-intent signals — when user post-diagnosis says any of these,
# they're ready for paid pitch. Order doesn't matter.
_BUYING_INTENT_KEYWORDS = (
    "想試", "想试", "好啊", "想要", "點買", "点买", "幾錢", "几钱", "價錢", "价钱",
    "點訂", "点订", "落單", "落单", "預訂", "预订", "想睇", "詳細", "详细",
    "邊度買", "边度买", "邊度可以買", "送上門", "送上门", "包郵", "包邮", "方便啲",
    "我要", "賣嘅", "卖的", "你哋有咩賣", "你们有什么卖",
    "係咪你哋", "你哋自己", "你哋出", "你哋做", "你哋整",  # "is it yours?"
    "連結", "link", "WhatsApp", "whatsapp", "落order", "落 order",
)


def _wants_to_buy(text: str) -> bool:
    if not text:
        return False
    return any(kw in text for kw in _BUYING_INTENT_KEYWORDS)


# Appointment-intent signals. When user wants to book / see doctor /
# visit clinic / use online consultation.
_APPOINTMENT_INTENT_KEYWORDS = (
    "預約", "预约", "睇醫師", "看医师", "睇中醫", "看中医",
    "到診", "到诊", "親身", "亲身", "到店", "上門", "上门",
    "視診", "视诊", "視像", "视像", "video", "視頻",
    "幾時可以", "几时可以", "幾點", "几点", "今日", "今天",
    "聽日", "听日", "明天", "後日", "后日",
    "診所喺邊", "诊所在哪", "點去", "点去", "地址",
)


def _wants_appointment(text: str) -> bool:
    if not text:
        return False
    return any(kw in text for kw in _APPOINTMENT_INTENT_KEYWORDS)


# Topical / ointment intent (we have 3 ointments).
_OINTMENT_INTENT_KEYWORDS = (
    "塗", "涂", "搽", "藥膏", "药膏", "膏", "外用", "外搽",
    "topical", "cream", "ointment", "lotion",
)


def _wants_ointment(text: str) -> bool:
    if not text:
        return False
    return any(kw in text for kw in _OINTMENT_INTENT_KEYWORDS)


# "Are there other / additional options?" signals — surface multi-track.
_ALTERNATIVES_INTENT_KEYWORDS = (
    "其他方法", "其他選擇", "其他选择", "其他辦法", "其他办法",
    "仲有冇", "还有什么", "還有", "还有",
    "其他嘅", "其他的", "alternative", "other option", "another",
)


def _wants_alternatives(text: str) -> bool:
    if not text:
        return False
    return any(kw in text for kw in _ALTERNATIVES_INTENT_KEYWORDS)


# Skin-specific symptom keywords — we have 3 specific ointments for these
_SKIN_CONDITION_KEYWORDS = (
    "皮膚痕", "皮肤痒", "皮肤痕", "痕癢", "痒",
    "濕疹", "湿疹", "暗瘡", "暗疮", "痘痘", "暗瘡",
    "敏感肌", "蚊咬", "皮膚問題", "皮肤问题",
    "皮膚紅", "皮肤红", "起紅疹", "起红疹",
)


def _has_skin_condition(text: str) -> bool:
    if not text:
        return False
    return any(kw in text for kw in _SKIN_CONDITION_KEYWORDS)


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------


def _build_user_prompt(
    user: User, user_message: str, media_urls: list[str]
) -> str:
    history_snippet = _format_history(user.conversation_history[-5:])
    media_note = (
        f"用戶 send 咗 {len(media_urls)} 個 media (可能係脷相)。" if media_urls else ""
    )

    # Compact CRM signals — only what matters for routing decisions.
    crm_signals = (
        f"status={user.status.value}, "
        f"體質={user.constitution.value if user.constitution != Constitution.UNKNOWN else '未評估'}, "
        f"pain_points={user.pain_points or '(無)'}, "
        f"products_pitched_count={len(user.products_pitched)}, "
        f"appointments_count={len(user.appointments)}"
    )

    return f"""用戶 CRM signals:
{crm_signals}

最近對話 (舊→新):
{history_snippet or "(冇歷史)"}

今次用戶訊息:
「{user_message}」
{media_note}

決定點 route，輸出 JSON。"""


def _format_history(messages: list[Any]) -> str:
    lines = []
    for m in messages:
        who = "用戶" if m.role == "user" else "Jessica"
        lines.append(f"- {who}: {m.content[:80]}")
    return "\n".join(lines)


def _extract_json(text: str) -> dict[str, Any]:
    """Pull the first JSON object out of `text`, tolerating leading prose."""
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"no JSON object in planner output: {text[:200]!r}")
    return json.loads(text[start : end + 1])
