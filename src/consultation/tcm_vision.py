"""TCM 望診 — Vision-based inspection for video consultations.

When a patient is on a voice call, the browser captures a JPEG frame
from the patient's camera and sends it as a JSON WebSocket message
(type='vision_frame').  This module calls GPT-4o Vision with a TCM
inspection prompt and returns concise observation notes.

Observations cover:
  • 面色 (complexion)
  • 眼神 (eyes / dark circles / eye bags)
  • 脣色 (lip colour)
  • 舌象 (tongue colour & coating, if visible)
  • 整體神態 (overall vitality)

The caller (voice_ws) starts this as an asyncio.Task concurrently with
STT so the latency cost is hidden behind Whisper's ~1-2 s transcription.
"""

from __future__ import annotations

import logging

from openai import AsyncOpenAI

logger = logging.getLogger("consultation.tcm_vision")

# -------------------------------------------------------------------
# Prompt
# -------------------------------------------------------------------
_VISION_PROMPT = """\
你係一位受過專業訓練的中醫望診助理。請根據提供的視頻截圖，進行簡短的中醫望診觀察。

請用繁體中文，以條列方式輸出你觀察到的資訊（僅描述清晰可見的特徵）：
• 面色：例如紅潤/蒼白/萎黃/晦暗/青紫
• 眼神：精神飽滿/疲倦；黑眼圈深淺；眼袋
• 脣色：例如紅潤/淡白/紫暗/乾裂
• 舌象：如舌頭可見，描述舌色及舌苔
• 整體神態：精神狀態、面部表情

如看不清楚某項特徵，請略去，不需強行猜測。
輸出應簡短（每項不超過20字），供中醫師問診參考。"""


# -------------------------------------------------------------------
# Public API
# -------------------------------------------------------------------
async def analyze_vision_frame(
    image_b64: str,
    openai_client: AsyncOpenAI,
) -> str:
    """Call GPT-4o Vision with the TCM inspection prompt.

    Returns a concise observation string, or empty string on failure.
    The image_b64 should be a raw JPEG base64 string (no data-URI prefix).
    """
    if not image_b64:
        return ""
    try:
        resp = await openai_client.chat.completions.create(
            model="gpt-4o",
            max_tokens=300,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": _VISION_PROMPT,
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_b64}",
                                "detail": "low",  # faster + cheaper; sufficient for face inspection
                            },
                        },
                    ],
                }
            ],
        )
        result = (resp.choices[0].message.content or "").strip()
        logger.info("[tcm_vision] analysis ok chars=%d", len(result))
        return result
    except Exception:  # noqa: BLE001
        logger.exception("[tcm_vision] vision analysis failed")
        return ""
