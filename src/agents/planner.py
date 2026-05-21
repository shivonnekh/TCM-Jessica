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

from anthropic import AsyncAnthropic

from src.agents.base import (
    SPECIALIST_CATALOG,
    PlannerDecision,
    SpecialistName,
    render_specialist_menu_zh,
)
from src.crm.models import Constitution, User, UserStatus

logger = logging.getLogger("agents.planner")

DEFAULT_MODEL = "claude-sonnet-4-5-20250929"


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
3. 用戶問知識問題 + 同時想預約 → [faq, appointment] mode=parallel
4. 體質剛診斷完 (status=constitution_done + 用戶仲想繼續) → [constitution, sales] mode=sequential，或者直接 sales solo
5. 用戶 confirm 已 propose 嘅 appointment slot → appointment solo (Phase 4)

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
        client: AsyncAnthropic,
        *,
        model: str = DEFAULT_MODEL,
        max_tokens: int = 500,
    ) -> None:
        self._client = client
        self._model = model
        self._max_tokens = max_tokens
        self._system = _build_system_prompt()

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

    # Tongue photo → constitution is mandatory
    if media_urls:
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

    # Empty / extremely short greeting → greeting only
    stripped = user_message.strip()
    if stripped in {"hi", "hello", "你好", "Hi", "HI"} and not user.conversation_history:
        return PlannerDecision(
            specialists=[SpecialistName.GREETING],
            mode="solo",
            reasoning="rule: first-touch greeting",
        )

    return None


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
