"""TongueProgress Agent — compares new tongue photo to prior records.

When a user uploads a new tongue photo AND already has at least one
prior TongueRecord in CRM, this agent:

1. Calls the vision LLM to extract structured findings from the new photo.
2. Reads the most recent prior record's structured findings from CRM.
3. Diffs the two algorithmically (no second LLM call).
4. Asks the LLM to produce a HK Cantonese narrative summarising the change.
5. Emits `suggested_user_state_diff = {"tongue_photos_append": [new_record_dict]}`
   so the pipeline persists the new record to the dedicated table.

The Planner routes here only when:
  - media_urls contains an image AND
  - user.constitution != UNKNOWN (already diagnosed) AND
  - user.tongue_photos is non-empty

For first-time tongue uploads, ConstitutionAgent still handles diagnosis.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from src.agents.base import (
    SpecialistInput,
    SpecialistName,
    SpecialistOutput,
)
from src.crm.models import TongueRecord
from src.llm import DEFAULT_MODEL

logger = logging.getLogger("agents.tongue_progress")


_VISION_SYSTEM_PROMPT = """\
你係心宜中醫嘅 AI 助手，專做舌診結構化分析同進度追蹤。

任務：分析用戶嘅最新脷相，extract 結構化嘅中醫舌診數據。

輸出嚴格 JSON，鍵名係英文，值係中文：
{
  "tongue_colour": "淡紅" | "紅" | "絳" | "淡白" | "紫",
  "coating_colour": "白" | "黃" | "灰" | "黑",
  "coating_thickness": "薄" | "厚" | "無苔",
  "coating_moisture": "潤" | "燥" | "膩",
  "body_shape": "正常" | "胖" | "瘦",
  "teeth_marks": true | false,
  "cracks": true | false,
  "raw_analysis": "（用一兩句廣東話描述呢張脷相嘅整體觀察）"
}

只輸出 JSON，唔好加 markdown / code fence / 任何解釋。
"""


_NARRATIVE_SYSTEM_PROMPT = """\
你係心宜中醫嘅 AI 助手 Jessica。
任務：對比用戶今次同上次嘅脷相數據，用廣東話口語講出變化、改善方向。

風格規則：
- 用第二人稱「你」，口語自然，唔好教科書口吻
- 提到變化要具體（薄咗 / 厚咗 / 紅啲 / 淡啲）
- 講中醫詮釋（例：「濕熱改善緊」、「脾虛仍然存在」）
- 唔好突然 pitch 產品
- 唔好用 markdown
- 控制喺 2-4 句話以內

只返回一段廣東話文字。
"""


_IMPROVING_KEYWORDS = ("改善", "薄咗", "退咗", "返正常", "好咗", "減少", "淡咗")
_WORSENING_KEYWORDS = ("加重", "厚咗", "深咗", "差咗", "更紅", "更厚")


class TongueProgressAgent:
    """Specialist that compares tongue photos over time."""

    def __init__(self, client: Any) -> None:
        self._client = client

    async def run(
        self, inp: SpecialistInput
    ) -> tuple[SpecialistOutput, dict[str, Any]]:
        if not inp.media_urls:
            logger.warning("tongue_progress: invoked without media_urls")
            return (
                SpecialistOutput(
                    specialist=SpecialistName.TONGUE_PROGRESS,
                    payload={"phase": "no_photo"},
                    error="no_media_urls",
                ),
                {"model": "no_llm", "input_tokens": 0, "output_tokens": 0},
            )

        new_photo_url = inp.media_urls[0]

        # 1. Vision analysis — extract structured findings from the new photo.
        new_findings, vision_usage = await self._analyze_new_photo(new_photo_url)

        prior_records = inp.user.tongue_photos
        prior = prior_records[-1] if prior_records else None

        # 2. Build the new record (persists via pipeline diff).
        new_record = TongueRecord(
            photo_url=new_photo_url,
            captured_at=datetime.utcnow(),
            tongue_colour=new_findings.get("tongue_colour", ""),
            coating_colour=new_findings.get("coating_colour", ""),
            coating_thickness=new_findings.get("coating_thickness", ""),
            coating_moisture=new_findings.get("coating_moisture", ""),
            body_shape=new_findings.get("body_shape", ""),
            teeth_marks=bool(new_findings.get("teeth_marks", False)),
            cracks=bool(new_findings.get("cracks", False)),
            raw_analysis=new_findings.get("raw_analysis", ""),
            constitution_at_time=inp.user.constitution.value,
        )

        # 3. Diff against prior + narrative.
        changes: list[dict[str, str]] = []
        overall = "first_photo"
        narrative = ""
        narrative_usage: dict[str, Any] = {
            "input_tokens": 0,
            "output_tokens": 0,
        }

        if prior is not None:
            changes = _diff_findings(prior, new_record)
            narrative, narrative_usage = await self._narrative(
                prior=prior, current=new_record, changes=changes
            )
            overall = _classify_direction(changes, narrative)

        payload: dict[str, Any] = {
            "phase": "compared" if prior is not None else "first_photo",
            "current_analysis": _record_to_dict(new_record),
            "previous_record": _record_to_dict(prior) if prior is not None else None,
            "changes": changes,
            "overall_direction": overall,
            "narrative_zh": narrative or new_record.raw_analysis,
        }

        diff = {"tongue_photos_append": [new_record.model_dump(mode="json")]}

        total_in = (vision_usage.get("input_tokens", 0)
                    + narrative_usage.get("input_tokens", 0))
        total_out = (vision_usage.get("output_tokens", 0)
                     + narrative_usage.get("output_tokens", 0))

        return (
            SpecialistOutput(
                specialist=SpecialistName.TONGUE_PROGRESS,
                payload=payload,
                suggested_user_state_diff=diff,
                tools_called=[
                    {
                        "name": "vision_analyze_tongue",
                        "args": {"url": new_photo_url[:120]},
                        "result": {"findings": new_findings},
                    }
                ],
            ),
            {
                "model": DEFAULT_MODEL,
                "input_tokens": total_in,
                "output_tokens": total_out,
            },
        )

    # ---------------------------------------------------------------
    # Internal LLM calls
    # ---------------------------------------------------------------

    async def _analyze_new_photo(
        self, photo_url: str
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Call vision LLM, parse JSON. Return (findings_dict, usage)."""
        try:
            response = await self._client.messages.create(
                model=DEFAULT_MODEL,
                max_tokens=400,
                system=_VISION_SYSTEM_PROMPT,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {"type": "url", "url": photo_url},
                            },
                            {"type": "text", "text": "請分析呢張脷相。"},
                        ],
                    }
                ],
            )
            text = response.content[0].text
            findings = _extract_json(text)
            usage = {
                "input_tokens": getattr(response.usage, "input_tokens", 0),
                "output_tokens": getattr(response.usage, "output_tokens", 0),
            }
            return findings, usage
        except Exception as exc:  # noqa: BLE001
            logger.warning("tongue_progress vision failed: %s", exc)
            return {"raw_analysis": "脷相分析未能完成"}, {
                "input_tokens": 0,
                "output_tokens": 0,
            }

    async def _narrative(
        self,
        *,
        prior: TongueRecord,
        current: TongueRecord,
        changes: list[dict[str, str]],
    ) -> tuple[str, dict[str, Any]]:
        """Generate a HK Cantonese before/after narrative."""
        days_ago = max(1, (current.captured_at - prior.captured_at).days)
        change_lines = "\n".join(
            f"- {c['aspect_zh']}：{c['before']} → {c['after']}"
            for c in changes
        ) or "（兩次數據相若，冇明顯變化）"

        user_prompt = f"""\
【上次（{days_ago} 日前）】
脷色：{prior.tongue_colour or "未記錄"}
苔色：{prior.coating_colour or "未記錄"}
苔厚：{prior.coating_thickness or "未記錄"}
潤燥：{prior.coating_moisture or "未記錄"}

【今次】
脷色：{current.tongue_colour}
苔色：{current.coating_colour}
苔厚：{current.coating_thickness}
潤燥：{current.coating_moisture}

【變化】
{change_lines}

請用 2-4 句廣東話講出進度同中醫詮釋。
"""
        try:
            response = await self._client.messages.create(
                model=DEFAULT_MODEL,
                max_tokens=300,
                system=_NARRATIVE_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            )
            text = response.content[0].text.strip()
            usage = {
                "input_tokens": getattr(response.usage, "input_tokens", 0),
                "output_tokens": getattr(response.usage, "output_tokens", 0),
            }
            return text, usage
        except Exception as exc:  # noqa: BLE001
            logger.warning("tongue_progress narrative failed: %s", exc)
            return "", {"input_tokens": 0, "output_tokens": 0}


# -----------------------------------------------------------------------------
# Pure helpers
# -----------------------------------------------------------------------------


_DIFF_ASPECTS = (
    ("tongue_colour", "脷色"),
    ("coating_colour", "苔色"),
    ("coating_thickness", "苔厚"),
    ("coating_moisture", "苔潤燥"),
    ("body_shape", "脷形"),
)


def _diff_findings(
    prior: TongueRecord, current: TongueRecord
) -> list[dict[str, str]]:
    """Return a list of structured field-by-field differences."""
    changes: list[dict[str, str]] = []
    for field, label_zh in _DIFF_ASPECTS:
        before = getattr(prior, field) or ""
        after = getattr(current, field) or ""
        if before and after and before != after:
            changes.append(
                {
                    "aspect": field,
                    "aspect_zh": label_zh,
                    "before": before,
                    "after": after,
                }
            )
    # Boolean flags
    if prior.teeth_marks != current.teeth_marks:
        changes.append(
            {
                "aspect": "teeth_marks",
                "aspect_zh": "齒痕",
                "before": "有" if prior.teeth_marks else "無",
                "after": "有" if current.teeth_marks else "無",
            }
        )
    if prior.cracks != current.cracks:
        changes.append(
            {
                "aspect": "cracks",
                "aspect_zh": "裂紋",
                "before": "有" if prior.cracks else "無",
                "after": "有" if current.cracks else "無",
            }
        )
    return changes


def _classify_direction(
    changes: list[dict[str, str]], narrative: str
) -> str:
    """Classify overall direction from narrative keywords."""
    if not changes:
        return "stable"
    text = narrative or ""
    improving = sum(1 for kw in _IMPROVING_KEYWORDS if kw in text)
    worsening = sum(1 for kw in _WORSENING_KEYWORDS if kw in text)
    if improving > worsening:
        return "improving"
    if worsening > improving:
        return "worsening"
    return "unclear"


def _record_to_dict(record: TongueRecord) -> dict[str, Any]:
    return record.model_dump(mode="json")


def _extract_json(text: str) -> dict[str, Any]:
    """Pull the first JSON object out of `text`, tolerating leading prose."""
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"no JSON in vision output: {text[:200]!r}")
    return json.loads(text[start : end + 1])
