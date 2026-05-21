"""FAQ Agent — TCM knowledge questions (湯水、穴位、養生、食療、體質常識).

Two-stage pipeline:
  1. KBSearch (deterministic, no LLM)
     query → ranked SearchHit list, top 3 cards
  2. LLM extract (Haiku)
     top cards + user query → structured answer_facts

Output payload:
    {
        "answer_facts": [
            { "fact": str, "card_id": str }
        ],
        "confidence": float,        # 0.0 – 1.0 based on top-hit score
        "next_best_question": str | None,
        "no_match": bool            # True if KB had nothing relevant
    }

The Writer is responsible for turning answer_facts into Cantonese bubbles.
The FAQ Agent NEVER produces user-facing text.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from src.llm import LLMClient

from src.agents.base import SpecialistInput, SpecialistName, SpecialistOutput
from src.crm.models import Constitution
from src.tools.kb_index import KBIndex
from src.tools.kb_search import KBSearch, SearchHit
from src.tools.recipe_extractor import RecipeExtractor, recipe_to_dict

logger = logging.getLogger("agents.faq")

DEFAULT_MODEL = "gpt-4o-mini"
MAX_FACTS = 5

_SYSTEM = """你係 Jessica 嘅 FAQ Specialist —— 從 TCM 知識卡片入面抽取相關 facts 比 Writer 用。

你 *唔* 直接寫俾用戶嘅嘢。淨係輸出 structured facts。

輸入：用戶問題 + 1-3 張相關 KB cards 嘅 excerpt
輸出：JSON，schema：
{
  "answer_facts": [
    {"fact": "...", "card_id": "..."}
  ],
  "confidence": 0.0,
  "next_best_question": "..." | null,
  "no_match": false
}

規則：
- 每個 fact 要 grounded 喺 card，唔好作
- fact 用「事實陳述」(general) 風格，講「X 體質會有 ...症狀」可以，但
  **絕對唔可以推測呢個 specific 用戶係 X 體質**。診斷係 Constitution
  Agent 嘅工，唔係 FAQ。如果用戶問「我係咩體質」→ no_match=true +
  next_best_question="想知體質可以發脷相 + 答 4 條題，我幫你評估"
- 唔好用「請」「我建議」「你應該」 — 留俾 Writer
- 最多 5 個 fact
- 完全唔相關 → no_match=true，answer_facts=[]

唔好輸出 markdown。淨係 JSON。"""


class FAQAgent:
    def __init__(
        self,
        *,
        kb_index: KBIndex | None = None,
        client: LLMClient | None = None,
        model: str = DEFAULT_MODEL,
        max_tokens: int = 600,
    ) -> None:
        self._kb = kb_index or KBIndex.load()
        self._search = KBSearch(self._kb)
        self._recipes = RecipeExtractor()
        self._client = client
        self._model = model
        self._max_tokens = max_tokens

    async def run(self, inp: SpecialistInput) -> tuple[SpecialistOutput, dict[str, Any]]:
        # FAST PATH: user asks for soup recipes / list → extract NAMED
        # recipes from KB, not abstract card titles. Bypasses LLM.
        if _wants_recipes(inp.user_message):
            recipes = self._pick_recipes_for_user(inp.user)
            if recipes:
                payload = {
                    "answer_facts": [],
                    "named_recipes": [recipe_to_dict(r) for r in recipes],
                    "confidence": 0.9,
                    "next_best_question": (
                        "想我幫你按你嘅體質揀啱嘅食譜？發張脷相 + 答 4 題我幫你睇"
                    ),
                    "no_match": False,
                    "intent": "list_recipes",
                }
                return SpecialistOutput(
                    specialist=SpecialistName.FAQ,
                    payload=payload,
                    cards_used=list({r.source_card for r in recipes}),
                    tools_called=[
                        {
                            "name": "RecipeExtractor.pick",
                            "args": {
                                "constitution": inp.user.constitution.value
                                if inp.user.constitution else None,
                            },
                            "result": {
                                "count": len(recipes),
                                "titles": [r.title for r in recipes],
                            },
                        }
                    ],
                ), {"model": "no_llm_recipes", "input_tokens": 0, "output_tokens": 0}

        hits = self._search.search(inp.user_message, top_k=3, min_score=3.0)

        if not hits:
            output = SpecialistOutput(
                specialist=SpecialistName.FAQ,
                payload={
                    "answer_facts": [],
                    "confidence": 0.0,
                    "next_best_question": None,
                    "no_match": True,
                },
                cards_used=[],
                tools_called=[
                    {"name": "KBSearch.search", "args": {"query": inp.user_message}, "result": "0 hits"}
                ],
            )
            return output, {"model": "no_llm", "input_tokens": 0, "output_tokens": 0}

        cards_used = [h.card.card_id for h in hits]

        # ALWAYS include the full top-card content so Writer can give
        # procedural (how-to / recipe) answers, not just abstract facts.
        top = hits[0]
        top_card_content = {
            "card_id": top.card.card_id,
            "title": top.card.title,
            "core_answer": top.card.core_answer,
            "supporting_points": list(top.card.supporting_points[:6]),
            "next_best_question": top.card.next_best_question or None,
        }

        # If no LLM client provided, return the top hit's core_answer directly
        # as a single fact (useful for tests / offline mode).
        if self._client is None:
            payload = _offline_fallback_payload(hits)
            payload["top_card_content"] = top_card_content
            output = SpecialistOutput(
                specialist=SpecialistName.FAQ,
                payload=payload,
                cards_used=cards_used,
                tools_called=_tools_log(hits, inp.user_message),
            )
            return output, {"model": "no_llm", "input_tokens": 0, "output_tokens": 0}

        # LLM extract
        prompt = _build_extract_prompt(inp.user_message, hits)
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
            payload = _parse_extract(raw)
            payload["answer_facts"] = payload.get("answer_facts", [])[:MAX_FACTS]
            payload["no_match"] = bool(payload.get("no_match", False))
        except Exception as exc:  # noqa: BLE001
            logger.warning("faq JSON parse failed (%s); raw=%r", exc, raw)
            payload = _offline_fallback_payload(hits)
            payload["confidence"] = 0.3  # downgrade — we fell back

        # Always pass the top-card raw content so Writer can compose a
        # detailed how-to / recipe answer rather than terse facts.
        payload["top_card_content"] = top_card_content

        output = SpecialistOutput(
            specialist=SpecialistName.FAQ,
            payload=payload,
            cards_used=cards_used,
            tools_called=_tools_log(hits, inp.user_message),
        )

        usage = {
            "model": self._model,
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        }
        return output, usage

    def _pick_recipes_for_user(self, user: Any) -> list:
        """Pick recipes matching user's constitution (if known) else popular."""
        if user.constitution and user.constitution != Constitution.UNKNOWN:
            r = self._recipes.for_constitution(user.constitution.value, limit=4)
            if r:
                return r
        return self._recipes.popular(limit=4)


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------


# Phrases that signal user wants ACTUAL recipe list, not abstract knowledge.
_RECIPE_LIST_KEYWORDS = (
    "什么湯水", "什么汤水", "邊款湯", "邊款湯水", "邊款好", "哪些汤",
    "什麼食譜", "什么食谱", "邊款食譜", "邊款食谱", "what soup",
    "推介", "推薦", "推荐", "邊款好飲", "有咩湯", "有咩食譜",
    "邊個食譜", "點揀湯", "食譜咩", "推介食譜", "湯水有咩",
    "汤水有什么", "食譜有咩", "你都没有发我", "你都冇發我",
)


def _wants_recipes(text: str) -> bool:
    if not text:
        return False
    return any(kw in text for kw in _RECIPE_LIST_KEYWORDS)


def _build_extract_prompt(query: str, hits: list[SearchHit]) -> str:
    card_blocks = []
    for h in hits:
        c = h.card
        supporting = "\n".join(f"- {p}" for p in c.supporting_points[:4])
        card_blocks.append(
            f"=== card_id: {c.card_id} (domain: {c.domain}, score: {h.score:.1f}) ===\n"
            f"標題: {c.title}\n"
            f"概要: {c.objective[:200]}\n"
            f"核心答案: {c.core_answer[:800]}\n"
            f"重點：\n{supporting}\n"
            f"證據級別: {c.evidence_level}\n"
            f"建議跟進: {c.next_best_question or '(無)'}"
        )

    cards_text = "\n\n".join(card_blocks)

    return f"""用戶問題：「{query}」

相關 KB cards：

{cards_text}

從上面 cards 抽出 1-5 個直接答用戶問題嘅 fact，連 card_id。輸出 JSON。"""


def _offline_fallback_payload(hits: list[SearchHit]) -> dict[str, Any]:
    """Used when no LLM client is configured — returns top card's content as facts."""
    if not hits:
        return {
            "answer_facts": [],
            "confidence": 0.0,
            "next_best_question": None,
            "no_match": True,
        }
    top = hits[0]
    facts: list[dict[str, str]] = []
    facts.append({"fact": top.card.short_excerpt, "card_id": top.card.card_id})
    for p in top.card.supporting_points[:2]:
        facts.append({"fact": p, "card_id": top.card.card_id})

    confidence = min(1.0, top.score / 20.0)
    return {
        "answer_facts": facts,
        "confidence": confidence,
        "next_best_question": top.card.next_best_question or None,
        "no_match": False,
    }


def _tools_log(hits: list[SearchHit], query: str) -> list[dict[str, Any]]:
    return [
        {
            "name": "KBSearch.search",
            "args": {"query": query, "top_k": 3},
            "result": {
                "hits": [
                    {
                        "card_id": h.card.card_id,
                        "score": h.score,
                        "matched_phrases": list(h.matched_phrases[:5]),
                    }
                    for h in hits
                ]
            },
        }
    ]


def _parse_extract(text: str) -> dict[str, Any]:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"no JSON: {text[:200]!r}")
    return json.loads(text[start : end + 1])
