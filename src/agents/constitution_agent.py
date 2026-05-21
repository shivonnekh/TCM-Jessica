"""TCM Constitution Agent — 九體質 assessment.

4-phase state machine, phase inferred from CRM (no separate state store).

  Phase 1 "asking_tongue":   no tongue analysis yet, no media this turn.
                             Tell Writer to ask for a tongue photo.

  Phase 2 "analyzing_tongue": media this turn → run Claude vision to
                              extract tongue_findings (colour, coating,
                              shape) → save to temp_state →
                              fall through to asking_mcq for question 0.

  Phase 3 "asking_mcq":      MCQ progress 0..3 → ask next question;
                             record previous answer to temp_state.

  Phase 4 "declaring":       4 MCQs answered → score 9 體質 candidates
                             from tongue + MCQ → declare → recommend
                             products → set user.constitution.

Vision: accepts media_urls. If URL is http(s), Claude vision fetches
directly. If local path, we base64-encode and embed. In offline / no-LLM
mode the agent skips the vision call and uses neutral findings (tests).

Output payload schemas per phase — see _build_payload_*.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import re
from pathlib import Path
from typing import Any

from src.llm import LLMClient

from src.agents.base import (
    SpecialistInput,
    SpecialistName,
    SpecialistOutput,
)
from src.crm.models import Constitution, UserStatus
from src.tools.kb_index import KBIndex
from src.tools.kb_search import KBSearch
from src.tools.product_catalog import ProductCatalog

logger = logging.getLogger("agents.constitution")

DEFAULT_MODEL = "gpt-4o-mini"  # vision quality matters
MAX_MCQ = 4

# temp_state namespacing — all keys live under "constitution_*" so other
# specialists can't accidentally collide.
_TS_FINDINGS = "constitution_tongue_findings"
_TS_MCQ_IDX = "constitution_mcq_index"
_TS_MCQ_ANS = "constitution_mcq_answers"


# ──────────────────────────────────────────────────────────────────
# The 4 MCQs — quick-screen subset of the 2009 中華中醫藥學會 standard.
# Each option maps to a multiset of 體質 it points toward (used for
# scoring in _score_constitution).
# ──────────────────────────────────────────────────────────────────


MCQS: list[dict[str, Any]] = [
    {
        "key": "energy",
        "question": "你最近嘅體力 + 精神狀態？",
        "options": [
            {"id": "A", "label": "精神奕奕、好少攰", "points": {Constitution.PINGHE: 2}},
            {"id": "B", "label": "正常，偶爾攰", "points": {Constitution.PINGHE: 1}},
            {"id": "C", "label": "成日攰、講嘢冇力", "points": {Constitution.QIXU: 3}},
            {"id": "D", "label": "心煩躁、易發脾氣", "points": {Constitution.QIYU: 2, Constitution.SHIRE: 1}},
        ],
    },
    {
        "key": "temperature",
        "question": "你嘅手腳同身體體溫感覺？",
        "options": [
            {"id": "A", "label": "成日凍 — 手腳冰冷", "points": {Constitution.YANGXU: 3}},
            {"id": "B", "label": "正常", "points": {Constitution.PINGHE: 1}},
            {"id": "C", "label": "熱、易出汗、口乾", "points": {Constitution.YINXU: 2, Constitution.SHIRE: 1}},
            {"id": "D", "label": "好怕焗、易紅面", "points": {Constitution.SHIRE: 3}},
        ],
    },
    {
        "key": "digestion",
        "question": "你嘅大便 + 消化系統？",
        "options": [
            {"id": "A", "label": "順、定時、正常成形", "points": {Constitution.PINGHE: 2}},
            {"id": "B", "label": "乾硬、難排", "points": {Constitution.YINXU: 2, Constitution.SHIRE: 1}},
            {"id": "C", "label": "稀、唔成形、易屙", "points": {Constitution.YANGXU: 2, Constitution.QIXU: 1}},
            {"id": "D", "label": "黏、馬桶黐底、味重", "points": {Constitution.TANSHI: 2, Constitution.SHIRE: 2}},
        ],
    },
    {
        "key": "mood_sleep",
        "question": "你嘅情緒同睡眠?",
        "options": [
            {"id": "A", "label": "平和、瞓得好", "points": {Constitution.PINGHE: 2}},
            {"id": "B", "label": "成日想多、心緒不寧、易醒", "points": {Constitution.QIYU: 2, Constitution.YINXU: 1}},
            {"id": "C", "label": "悶悶不樂、提唔起勁", "points": {Constitution.QIYU: 2, Constitution.QIXU: 1}},
            {"id": "D", "label": "瞓唔到、發夢多、易紅眼", "points": {Constitution.XUEYU: 2, Constitution.YINXU: 1}},
        ],
    },
]


# ──────────────────────────────────────────────────────────────────
# Tongue vision prompt
# ──────────────────────────────────────────────────────────────────


_VISION_SYSTEM = """你係中醫脷診助手。睇用戶 send 嘅脷相，輸出客觀觀察。

輸出純 JSON：
{
  "is_tongue_photo": true | false,
  "colour": "pale" | "pink" | "red" | "dark_red" | "purple" | "unknown",
  "shape": "thin" | "normal" | "swollen" | "tooth_marks" | "unknown",
  "coating": "none" | "thin_white" | "thick_white" | "yellow" | "greasy" | "peeled" | "unknown",
  "moisture": "dry" | "normal" | "wet" | "unknown",
  "notes": "1 句中文觀察，例如 「舌淡紅、苔薄白」"
}

如果張相唔係脷 → is_tongue_photo=false，其他欄填 "unknown"。
唔好做診斷、唔好建議。淨係客觀描述。"""


# ──────────────────────────────────────────────────────────────────


class ConstitutionAgent:
    def __init__(
        self,
        *,
        client: LLMClient | None = None,
        catalog: ProductCatalog | None = None,
        kb_index: KBIndex | None = None,
        vision_model: str = DEFAULT_MODEL,
        max_vision_tokens: int = 400,
    ) -> None:
        self._client = client
        self._catalog = catalog or ProductCatalog()
        self._kb = kb_index or KBIndex.load()
        self._kb_search = KBSearch(self._kb)
        self._vision_model = vision_model
        self._max_vision_tokens = max_vision_tokens

    async def run(
        self, inp: SpecialistInput
    ) -> tuple[SpecialistOutput, dict[str, Any]]:
        ts = dict(inp.user.temp_state)  # copy — never mutate input
        usage_total = {"model": "stub", "input_tokens": 0, "output_tokens": 0}
        tools_called: list[dict[str, Any]] = []
        cards_used: list[str] = []
        suggested_diff: dict[str, Any] = {}

        findings = ts.get(_TS_FINDINGS)
        mcq_idx = int(ts.get(_TS_MCQ_IDX, 0))
        mcq_answers: list[dict[str, Any]] = list(ts.get(_TS_MCQ_ANS, []))

        # ── PHASE 1: no tongue analysis yet, no media this turn ─────
        if not findings and not inp.media_urls:
            payload = _build_payload_ask_tongue()
            return _wrap(payload, suggested_diff, cards_used, tools_called), usage_total

        # ── PHASE 2: media present, run vision (if not done) ────────
        just_analyzed = False
        if not findings and inp.media_urls:
            findings, vision_usage = await self._analyze_tongue(inp.media_urls)
            tools_called.append(
                {
                    "name": "claude_vision.analyze_tongue",
                    "args": {"n_media": len(inp.media_urls)},
                    "result": findings,
                }
            )
            usage_total = vision_usage

            # Persist tongue findings
            ts[_TS_FINDINGS] = findings
            suggested_diff["temp_state"] = ts

            # Not a tongue photo? Ask again politely.
            if not findings.get("is_tongue_photo"):
                payload = _build_payload_ask_tongue(retry=True)
                return _wrap(payload, suggested_diff, cards_used, tools_called), usage_total

            just_analyzed = True
            # Fall through to PHASE 3 — ask first MCQ same turn, but
            # share the preliminary tongue read along with it.

        # User just answered the previous MCQ (if any).
        # We expect user_message to be an option label (A/B/C/D) or
        # natural text we can map. Look back at the last MCQ asked and
        # record the user's answer.
        if mcq_idx > 0 and mcq_idx <= MAX_MCQ:
            recorded = _record_previous_answer(
                inp.user_message,
                MCQS[mcq_idx - 1],
                mcq_answers,
            )
            if recorded is not None:
                mcq_answers = recorded
                ts[_TS_MCQ_ANS] = mcq_answers
                suggested_diff["temp_state"] = ts

        # ── PHASE 4: all MCQs answered → declare (FREE-FIRST) ───────
        if len(mcq_answers) >= MAX_MCQ:
            constitution = _score_constitution(findings or {}, mcq_answers)
            cards_used.append("tcm_constitution_assessment")

            # Primary: free KB recipes matching constitution. Paid pitch
            # waits for an explicit interest signal on a future turn —
            # Planner routes to Sales then.
            free_recipes = self._search_free_recipes(constitution)
            for hit in free_recipes:
                if hit["card_id"] not in cards_used:
                    cards_used.append(hit["card_id"])
            tools_called.append(
                {
                    "name": "KBSearch.free_recipes",
                    "args": {"constitution": constitution.value},
                    "result": {
                        "count": len(free_recipes),
                        "cards": [r["card_id"] for r in free_recipes],
                    },
                }
            )

            payload = _build_payload_declare(
                constitution, findings or {}, free_recipes=free_recipes
            )

            suggested_diff["constitution"] = constitution.value
            suggested_diff["status"] = UserStatus.CONSTITUTION_DONE.value
            ts[_TS_MCQ_IDX] = MAX_MCQ
            suggested_diff["temp_state"] = ts

            return _wrap(payload, suggested_diff, cards_used, tools_called), usage_total

        # ── PHASE 3: ask next MCQ ───────────────────────────────────
        next_q_idx = len(mcq_answers)  # advance based on recorded count
        ts[_TS_MCQ_IDX] = next_q_idx + 1
        suggested_diff["temp_state"] = ts
        payload = _build_payload_ask_mcq(
            next_q_idx,
            share_tongue_findings=just_analyzed,
            tongue_findings=findings,
        )
        return _wrap(payload, suggested_diff, cards_used, tools_called), usage_total

    # -----------------------------------------------------------------
    # KB lookup for free recipes
    # -----------------------------------------------------------------

    def _search_free_recipes(
        self, constitution: Constitution
    ) -> list[dict[str, Any]]:
        """Find 2-3 free home-cooking recipes from KB matching constitution."""
        queries = [
            f"{constitution.value} 湯水",
            f"{constitution.value} 食療",
        ]
        seen: set[str] = set()
        out: list[dict[str, Any]] = []
        for q in queries:
            for hit in self._kb_search.search(q, top_k=3, min_score=3.0):
                if hit.card.card_id in seen:
                    continue
                seen.add(hit.card.card_id)
                out.append(
                    {
                        "card_id": hit.card.card_id,
                        "title": hit.card.title,
                        "excerpt": hit.card.short_excerpt,
                        "next_best_question": hit.card.next_best_question or "",
                    }
                )
                if len(out) >= 3:
                    return out
        return out

    # ─────────────────────────────────────────────────────────────
    # Tongue vision
    # ─────────────────────────────────────────────────────────────

    async def _analyze_tongue(
        self, media_urls: list[str]
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Run Claude vision on the first media. Returns findings + usage."""
        if self._client is None:
            return _neutral_findings("offline_mode"), {
                "model": "no_llm",
                "input_tokens": 0,
                "output_tokens": 0,
            }

        url_or_path = media_urls[0]
        content_block = _build_vision_content(url_or_path)
        if content_block is None:
            return _neutral_findings("invalid_media"), {
                "model": "no_llm",
                "input_tokens": 0,
                "output_tokens": 0,
            }

        try:
            response = await self._client.messages.create(
                model=self._vision_model,
                max_tokens=self._max_vision_tokens,
                system=_VISION_SYSTEM,
                messages=[{"role": "user", "content": [content_block]}],
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("vision call failed: %s", exc)
            return _neutral_findings(f"vision_error:{type(exc).__name__}"), {
                "model": self._vision_model,
                "input_tokens": 0,
                "output_tokens": 0,
            }

        raw = "".join(b.text for b in response.content if b.type == "text").strip()
        try:
            findings = _extract_json(raw)
        except Exception as exc:  # noqa: BLE001
            logger.warning("vision JSON parse failed (%s); raw=%r", exc, raw)
            findings = _neutral_findings("parse_error")

        usage = {
            "model": self._vision_model,
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        }
        return findings, usage


# ──────────────────────────────────────────────────────────────────
# Vision content builder
# ──────────────────────────────────────────────────────────────────


def _build_vision_content(url_or_path: str) -> dict[str, Any] | None:
    """Translate a media reference into a Claude `image` content block."""
    if url_or_path.startswith(("http://", "https://")):
        return {"type": "image", "source": {"type": "url", "url": url_or_path}}
    p = Path(url_or_path)
    if not p.exists():
        logger.warning("media file not found: %s", url_or_path)
        return None
    ext = p.suffix.lower().lstrip(".")
    media_type = {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "gif": "image/gif",
        "webp": "image/webp",
    }.get(ext, "image/jpeg")
    data = base64.standard_b64encode(p.read_bytes()).decode("ascii")
    return {
        "type": "image",
        "source": {"type": "base64", "media_type": media_type, "data": data},
    }


# ──────────────────────────────────────────────────────────────────
# Scoring — 體質 selection from tongue + MCQs
# ──────────────────────────────────────────────────────────────────


def _score_constitution(
    findings: dict[str, Any], answers: list[dict[str, Any]]
) -> Constitution:
    scores: dict[Constitution, int] = {c: 0 for c in Constitution if c != Constitution.UNKNOWN}

    # Tongue-derived priors (small but directional)
    colour = findings.get("colour")
    coating = findings.get("coating")
    shape = findings.get("shape")
    moisture = findings.get("moisture")

    if colour == "pale":
        scores[Constitution.YANGXU] += 2
        scores[Constitution.QIXU] += 1
    elif colour in ("red", "dark_red"):
        scores[Constitution.YINXU] += 2
        scores[Constitution.SHIRE] += 1
    elif colour == "purple":
        scores[Constitution.XUEYU] += 3

    if coating in ("thick_white", "greasy"):
        scores[Constitution.TANSHI] += 3
    elif coating == "yellow":
        scores[Constitution.SHIRE] += 2
    elif coating == "peeled":
        scores[Constitution.YINXU] += 2

    if shape == "tooth_marks":
        scores[Constitution.QIXU] += 2
        scores[Constitution.TANSHI] += 1
    elif shape == "swollen":
        scores[Constitution.TANSHI] += 2

    if moisture == "dry":
        scores[Constitution.YINXU] += 1
    elif moisture == "wet":
        scores[Constitution.YANGXU] += 1

    # MCQ-derived signals (the main weight)
    for ans in answers:
        for cz_value, pts in ans.get("points", {}).items():
            try:
                cz = Constitution(cz_value) if isinstance(cz_value, str) else cz_value
            except ValueError:
                continue
            scores[cz] = scores.get(cz, 0) + int(pts)

    # Pick the max; tie → prefer PINGHE (least intervention).
    best = max(scores.items(), key=lambda kv: (kv[1], kv[0] == Constitution.PINGHE))
    return best[0] if best[1] > 0 else Constitution.PINGHE


# ──────────────────────────────────────────────────────────────────
# Recording previous-turn MCQ answer
# ──────────────────────────────────────────────────────────────────


_OPTION_RE = re.compile(r"^\s*([A-Da-d])\b")


def _record_previous_answer(
    user_text: str,
    last_question: dict[str, Any],
    answers_so_far: list[dict[str, Any]],
) -> list[dict[str, Any]] | None:
    """If the user text picks an option for `last_question`, append it.

    Recognises "A" / "a" / "A." prefixes and label substring matches.
    Returns updated answers list, or None if we couldn't recognise.
    """
    text = (user_text or "").strip()

    # Match leading letter A-D
    chosen_id: str | None = None
    m = _OPTION_RE.match(text)
    if m:
        chosen_id = m.group(1).upper()

    # Fallback: label substring
    if chosen_id is None:
        for opt in last_question["options"]:
            if opt["label"] in text:
                chosen_id = opt["id"]
                break

    if chosen_id is None:
        return None

    for opt in last_question["options"]:
        if opt["id"] == chosen_id:
            return [
                *answers_so_far,
                {
                    "question_key": last_question["key"],
                    "chosen_id": chosen_id,
                    "label": opt["label"],
                    # Pydantic JSON-serialises StrEnum keys to strings; store
                    # them as strings so temp_state round-trips cleanly.
                    "points": {k.value if isinstance(k, Constitution) else k: v
                               for k, v in opt["points"].items()},
                },
            ]
    return None


# ──────────────────────────────────────────────────────────────────
# Output payload builders — schemas the Writer consumes
# ──────────────────────────────────────────────────────────────────


def _build_payload_ask_tongue(retry: bool = False) -> dict[str, Any]:
    return {
        "phase": "asking_tongue",
        "retry": retry,
        "writer_hint": (
            "請用戶 send 一張清晰嘅脷相（伸出脷、自然光、唔好剛刷牙）。"
            if not retry
            else "張相唔似脷相，溫和咁問用戶重新 send 一張。"
        ),
    }


def _build_payload_ask_mcq(
    q_idx: int,
    *,
    share_tongue_findings: bool = False,
    tongue_findings: dict[str, Any] | None = None,
) -> dict[str, Any]:
    q = MCQS[q_idx]
    options = [{"id": o["id"], "label": o["label"]} for o in q["options"]]
    # Render the options as a single pre-formatted string the Writer MUST
    # use verbatim — prevents LLM from dropping option D / reordering.
    rendered_options = "\n".join(f"{o['id']}. {o['label']}" for o in options)
    payload = {
        "phase": "asking_mcq",
        "q_index": q_idx,
        "q_total": MAX_MCQ,
        "question": q["question"],
        "options": options,
        "options_rendered": rendered_options,
        "writer_hint": (
            f"問第 {q_idx + 1} / {MAX_MCQ} 條題。\n"
            f"Bubble 1: 「{q['question']}」(可以加 emoji)\n"
            f"Bubble 2: 必須 verbatim 用呢段（全部 4 個選項 A B C D 一個都唔少）:\n"
            f"{rendered_options}\n"
            f"絕對唔可以剩低任何選項、唔可以改字、唔可以分開做幾個 bubble。"
        ),
    }
    # On the first MCQ right after vision analysis, share a preliminary
    # tongue reading first, THEN ask the first question.
    if share_tongue_findings and tongue_findings:
        payload["share_tongue_first"] = True
        payload["tongue_findings"] = tongue_findings
        payload["writer_hint"] = (
            "Bubble 1-2: 用 1-2 句講脷相觀察 (顏色、苔、形態) + 1 句初步方向 "
            "(例 「初步睇起來氣虛偏向」)。\n"
            f"Bubble 3: 「{q['question']}」\n"
            "Bubble 4: 必須 verbatim 用呢段（全部 4 個選項一個都唔少）:\n"
            f"{rendered_options}"
        )
    return payload


def _absolutize(url: str, base: str) -> str:
    """Turn a relative product image path into an absolute URL.

    - Already http(s) → unchanged.
    - Starts with '/' → prefixed with base.
    - 'data/media/...' or 'media/...' → routed to '/media/...' on base.
    """
    if not url:
        return ""
    if url.startswith(("http://", "https://")):
        return url
    if url.startswith("data/media/"):
        return f"{base}/media/{url[len('data/media/'):]}"
    if url.startswith("/"):
        return f"{base}{url}"
    if url.startswith("media/"):
        return f"{base}/{url}"
    return f"{base}/{url}"


def _build_payload_declare(
    constitution: Constitution,
    findings: dict[str, Any],
    *,
    free_recipes: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    recipes = free_recipes or []
    recipe_titles = [r.get("title", "")[:30] for r in recipes]
    return {
        "phase": "declaring",
        "constitution": constitution.value,
        "tongue_findings": findings,
        "free_recipes": recipes,
        # NO paid soup_recommendations here. We do FREE-first, paid is
        # a follow-up only if user shows interest. Soft hook only.
        "writer_hint": (
            f"宣告體質「{constitution.value}」 (1-2 句講特徵)。"
            f"然後推介呢幾款免費家用食譜：{recipe_titles or '(KB hit 唔到 — 留空 free_recipes 唔好作)'}。"
            "風格：教育、非銷售；列 2-3 款湯水名 + 一句總體飲法 / 注意事項。"
            "最後一個 bubble 可以好輕咁提一句:「如果想試方便啲嘅，我哋都有預製"
            "湯水送上門」— 但唔好 push、唔好講價錢、唔好叫佢買。等用戶有興趣"
            "再問先 pitch。"
        ),
    }


def _neutral_findings(reason: str) -> dict[str, Any]:
    return {
        "is_tongue_photo": False,
        "colour": "unknown",
        "shape": "unknown",
        "coating": "unknown",
        "moisture": "unknown",
        "notes": "(無觀察)",
        "_reason": reason,
    }


def _wrap(
    payload: dict[str, Any],
    suggested_diff: dict[str, Any],
    cards_used: list[str],
    tools_called: list[dict[str, Any]],
) -> SpecialistOutput:
    return SpecialistOutput(
        specialist=SpecialistName.CONSTITUTION,
        payload=payload,
        suggested_user_state_diff=suggested_diff,
        cards_used=cards_used,
        tools_called=tools_called,
    )


def _extract_json(text: str) -> dict[str, Any]:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"no JSON in vision output: {text[:200]!r}")
    return json.loads(text[start : end + 1])
