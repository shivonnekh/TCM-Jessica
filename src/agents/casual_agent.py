"""Casual Talk Specialist — friend-style banter for ongoing (non first-touch) chitchat.

Greeting Agent only handles the very first message (verbatim onboarding).
After that, any non-medical / non-product / non-appointment talk should
land here. Job: be a warm presence, ask a caring lifestyle Q, listen,
gently pivot to health if user opens up.

Output payload schema:
    {
      "tone": "warm" | "playful" | "concerned" | "supportive",
      "topic": str,                       # short summary of user thread
      "lifestyle_question": str | None,   # one caring follow-up
      "soft_pivot_hint": str | None,      # if user mentioned health
                                          # implicitly, what topic to gently
                                          # explore next turn
      "intent_flags": list[str]           # e.g. ["empathy_needed",
                                          #       "user_distressed",
                                          #       "good_news"]
    }

The Writer turns this into 1-3 short bubbles. Never makes medical claims.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from src.agents.base import SpecialistInput, SpecialistName, SpecialistOutput
from src.llm import DEFAULT_MODEL, LLMClient
from src.tools import prompt_overrides

logger = logging.getLogger("agents.casual")


_SYSTEM = """你係 Jessica 嘅 Casual Talk Specialist —— 處理朋友式對話。
唔涉及醫療診斷、唔推產品、唔做預約 — 純粹係 emotional + lifestyle layer，
建立 rapport + soft listen。

你 *唔* 直接寫俾用戶嘅嘢。輸出 structured intent 比 Writer。

輸入：用戶最新一句 + 對話歷史 + CRM 狀態 (status / 體質 / 已 pitched 等)
輸出：JSON，schema：
{
  "tone": "warm" | "playful" | "concerned" | "supportive",
  "topic": "...",                        // 一句概括用戶呢 turn 講咩
  "lifestyle_question": "..." | null,    // 一條溫和嘅 follow-up
                                         // 例：「最近瞓得 OK 嗎？」
                                         //     「工作有冇 push 得太緊？」
                                         //     「屋企最近順唔順？」
                                         // 唔系做問卷，係 friend chat
  "soft_pivot_hint": "..." | null,       // 用戶提到健康相關 implicit signal
                                         // 時，建議下 turn explore 邊個方向
                                         // 例：「sleep / stress / digestion」
  "intent_flags": ["..."]                // 例如 ["empathy_needed",
                                         //       "user_distressed",
                                         //       "good_news",
                                         //       "small_complaint"]
}

規則:
- 用戶情緒低落 / distressed → tone=concerned + intent_flags=["empathy_needed"]
- 用戶 share 好消息（升職 / 旅行 / 屋企好事）→ tone=playful + flag good_news
- 用戶 implicit 提到唔舒服（攰、瞓唔好、stress）但未直接問醫療
  → tone=supportive + soft_pivot_hint 填健康方向，Planner 下 turn 可以
    路由 Constitution / FAQ
- 純閒聊 → tone=warm + 隨意 lifestyle_question
- 唔好擺 medical / 體質 / 產品語入 topic — 唔關事就唔提

唔好 markdown，淨係 JSON。"""


class CasualAgent:
    def __init__(
        self,
        client: LLMClient,
        *,
        model: str = DEFAULT_MODEL,
        max_tokens: int = 300,
    ) -> None:
        self._client = client
        self._model = model
        self._max_tokens = max_tokens

    async def run(
        self, inp: SpecialistInput
    ) -> tuple[SpecialistOutput, dict[str, Any]]:
        prompt = _build_prompt(inp)
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            system=prompt_overrides.resolve("casual_system", _SYSTEM),
            messages=[{"role": "user", "content": prompt}],
        )
        raw = "".join(
            block.text for block in response.content if block.type == "text"
        ).strip()
        try:
            payload = _extract_json(raw)
        except Exception as exc:  # noqa: BLE001
            logger.warning("casual JSON parse failed (%s); raw=%r", exc, raw)
            payload = {
                "tone": "warm",
                "topic": "(解析失敗，預設友善聆聽)",
                "lifestyle_question": None,
                "soft_pivot_hint": None,
                "intent_flags": ["parse_error"],
            }
        output = SpecialistOutput(
            specialist=SpecialistName.CASUAL,
            payload=payload,
        )
        usage = {
            "model": self._model,
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        }
        return output, usage


def _build_prompt(inp: SpecialistInput) -> str:
    history_lines = []
    for m in inp.user.conversation_history[-6:]:
        who = "用戶" if m.role == "user" else "Jessica"
        history_lines.append(f"- {who}: {m.content[:100]}")
    history_txt = "\n".join(history_lines) or "(冇歷史)"

    return f"""用戶 phone: {inp.user.phone}
status: {inp.user.status.value}
體質: {inp.user.constitution.value}
最近對話:
{history_txt}

今次訊息: 「{inp.user_message}」

輸出 JSON。"""


def _extract_json(text: str) -> dict[str, Any]:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"no JSON object: {text[:200]!r}")
    return json.loads(text[start : end + 1])
