"""Greeting / Others Agent — casual, warm, gentle.

Two modes:

1. FIRST-TOUCH (status=NEW + no history): loads the OFFICIAL intro from
   data/greetings.json verbatim — fixed bubbles + 洪醫師 portrait. No LLM
   ad-libbing. Brand consistency.

2. ONGOING small-talk: LLM-driven structured output (tone + topic +
   suggested_followup + intent_flags) for the Writer to compose.

Output schema:
    {
        "official_intro": bool,                # True → Writer renders verbatim
        "intro_bubbles": [str, ...],           # only when official_intro=True
        "intro_media": [{url_path, alt, after_bubble_idx}],
        "tone": "warm" | "playful" | "concerned",
        "topic": str,
        "suggested_followup": str | None,
        "intent_flags": list[str]              # ["new_user_intro"] when official
    }
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from src.llm import LLMClient

from src.agents.base import (
    SpecialistInput,
    SpecialistName,
    SpecialistOutput,
)
from src.crm.models import UserStatus

logger = logging.getLogger("agents.greeting")

DEFAULT_MODEL = "gpt-4o-mini"  # cheap — Greeting doesn't need Sonnet

# Greetings JSON — official intro lives here, hot-reloaded on every read so
# editing the file in prod doesn't require a redeploy.
DEFAULT_GREETINGS_PATH = (
    Path(__file__).resolve().parent.parent.parent / "data" / "greetings.json"
)


def _load_greetings(path: Path = DEFAULT_GREETINGS_PATH) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        logger.warning("could not load %s: %s — falling back to embedded default", path, exc)
        return {
            "first_touch": {
                "id": "jessica_intro_fallback",
                "bubbles": [
                    "Hi 嗨 ☺️ 我係 Jessica",
                    "Care Plus 心宜中醫嘅註冊中醫師 🌿",
                    "最近身體點啊？有冇邊度唔舒服？",
                ],
                "media": [],
            }
        }


def _public_base_url() -> str:
    """Public origin used to build absolute media URLs ChatDaddy can fetch."""
    return os.environ.get(
        "PUBLIC_BASE_URL", "https://tcm-jessica.onrender.com"
    ).rstrip("/")

_SYSTEM = """你係 Jessica 嘅 Greeting Specialist —— 處理寒暄、閒聊、初次見面。

你 *唔* 直接寫俾用戶嘅嘢。你淨係輸出 structured intent 比 Writer。

輸入：用戶最新一句 + 對話歷史 + CRM 狀態
輸出：純 JSON，schema：
{
  "tone": "warm" | "playful" | "concerned",
  "topic": "...",                          // 一句概括用戶講咩
  "suggested_followup": "..." | null,      // Writer 可以用嘅 follow-up 問題（中文）
  "intent_flags": ["..."]                  // 例如 ["new_user_intro", "rapport_check"]
}

規則：
- 第一次見面 → tone=warm, intent_flags=["new_user_intro"]，suggested_followup 應該係邀請用戶講下自己嘅 health concerns
- 用戶情緒低落 → tone=concerned
- 隨意閒聊 → tone=playful
- topic 用一句中文總結，唔好用英文

唔好輸出 markdown，淨係 JSON。"""


class GreetingAgent:
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

    async def run(self, inp: SpecialistInput) -> tuple[SpecialistOutput, dict[str, Any]]:
        is_first_touch = (
            inp.user.status == UserStatus.NEW
            and not inp.user.conversation_history
        )

        # FIRST-TOUCH → return the OFFICIAL intro verbatim. No LLM call.
        if is_first_touch:
            greetings = _load_greetings()
            ft = greetings.get("first_touch", {})
            bubbles = list(ft.get("bubbles", []))
            base = _public_base_url()
            media = [
                {
                    "url": f"{base}{m['url_path']}" if m.get("url_path", "").startswith("/") else m.get("url_path", ""),
                    "alt": m.get("alt", ""),
                    "after_bubble_idx": int(m.get("after_bubble_idx", 0)),
                }
                for m in ft.get("media", [])
            ]
            payload = {
                "official_intro": True,
                "intro_bubbles": bubbles,
                "intro_media": media,
                "tone": "warm",
                "topic": "first-touch self-introduction",
                "suggested_followup": None,
                "intent_flags": ["new_user_intro"],
            }
            output = SpecialistOutput(
                specialist=SpecialistName.GREETING,
                payload=payload,
                suggested_user_state_diff={"status": UserStatus.QUALIFIED.value},
            )
            return output, {"model": "no_llm_first_touch", "input_tokens": 0, "output_tokens": 0}

        # ONGOING small-talk → LLM
        prompt = _build_prompt(inp, is_first_touch=is_first_touch)
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            system=_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )

        raw = "".join(
            block.text for block in response.content if block.type == "text"
        ).strip()

        try:
            payload = _extract_json(raw)
        except Exception as exc:  # noqa: BLE001
            logger.warning("greeting JSON parse failed (%s); raw=%r", exc, raw)
            payload = {
                "tone": "warm",
                "topic": "（解析失敗，預設友善寒暄）",
                "suggested_followup": None,
                "intent_flags": ["parse_error"],
            }
        payload.setdefault("official_intro", False)

        suggested_diff: dict[str, Any] = {}

        output = SpecialistOutput(
            specialist=SpecialistName.GREETING,
            payload=payload,
            suggested_user_state_diff=suggested_diff,
        )
        usage = {
            "model": self._model,
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        }
        return output, usage


def _build_prompt(inp: SpecialistInput, *, is_first_touch: bool) -> str:
    history_lines = []
    for m in inp.user.conversation_history[-4:]:
        who = "用戶" if m.role == "user" else "Jessica"
        history_lines.append(f"- {who}: {m.content[:80]}")
    history_txt = "\n".join(history_lines) or "(冇歷史)"

    first_touch_hint = (
        "\n** 呢個係首次見面，記得 warm + new_user_intro **" if is_first_touch else ""
    )

    return f"""用戶 phone: {inp.user.phone}
status: {inp.user.status.value}
最近對話:
{history_txt}

今次訊息: 「{inp.user_message}」
{first_touch_hint}

輸出 JSON。"""


def _extract_json(text: str) -> dict[str, Any]:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"no JSON object: {text[:200]!r}")
    return json.loads(text[start : end + 1])
