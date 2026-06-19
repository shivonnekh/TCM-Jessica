"""Post-consultation summary — generate a Cantonese summary and send it
back to the patient on the platform they came from.

Platform detection from crm_key:
    ig_<igsid>   → Instagram DM
    fb_<psid>    → Messenger DM
    <phone>      → WhatsApp (handled separately via WA client)
    unknown/test → skip (no platform to send to)

Called from voice_ws.handle_voice() on WebSocket disconnect when the
conversation history has at least 2 patient turns.
"""

from __future__ import annotations

import logging

from openai import AsyncOpenAI

from src.crm.models import ConversationMessage

logger = logging.getLogger("consultation.post_call")

_SUMMARY_PROMPT = """\
你係一位香港中醫師（陳芷晴中醫師）的AI助理。
以下係剛完成的視像問診對話記錄。請用繁體中文（廣東話書寫），生成一份簡潔的問診總結。

格式如下（直接輸出，不要多餘說明）：

【問診總結】

📋 主訴：（病人今日主要嘅不適或問題，1-2句）
💡 討論要點：（醫師分析或解釋咗咩，1-3句）
📝 建議：（醫師嘅建議，例如生活習慣、食療、需要面診等，1-3句）

如需預約面診或查詢，歡迎隨時回覆。

—— 陳芷晴中醫師 AI 問診助理"""


def _detect_platform(crm_key: str) -> tuple[str, str] | None:
    """Return (platform, recipient_id) or None if we can't route."""
    if crm_key.startswith("ig_"):
        return ("instagram", crm_key[3:])
    if crm_key.startswith("fb_"):
        return ("facebook", crm_key[3:])
    return None  # WhatsApp / unknown — handled separately or skipped


def _history_to_text(history: list[ConversationMessage]) -> str:
    lines: list[str] = []
    for msg in history:
        speaker = "病人" if msg.role == "user" else "醫師"
        lines.append(f"{speaker}：{msg.content}")
    return "\n".join(lines)


async def generate_summary(
    history: list[ConversationMessage],
    openai_client: AsyncOpenAI,
) -> str:
    """Call LLM to produce a structured post-call summary. Returns empty on failure."""
    if not history:
        return ""
    try:
        resp = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": _SUMMARY_PROMPT},
                {"role": "user", "content": _history_to_text(history)},
            ],
            max_tokens=400,
            temperature=0.4,
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception:  # noqa: BLE001
        logger.exception("[post_call] summary generation failed")
        return ""


async def send_post_call_summary(
    room_id: str,
    history: list[ConversationMessage],
    repo,          # ConsultationRepo
    openai_client: AsyncOpenAI,
) -> None:
    """Generate summary and send it to the patient on their origin platform."""
    # Need at least 1 patient turn to have anything to summarise
    patient_turns = [m for m in history if m.role == "user"]
    if len(patient_turns) < 1:
        logger.info("[post_call] no patient turns — skipping summary room=%s", room_id)
        return

    # Look up which platform the patient came from
    consult = await repo.get(room_id)
    if not consult:
        logger.warning("[post_call] room not found room=%s", room_id)
        return

    crm_key = consult.crm_key
    route = _detect_platform(crm_key)

    if route is None:
        logger.info(
            "[post_call] crm_key=%r — not an IG/FB key, skipping DM summary", crm_key
        )
        return

    platform, recipient_id = route
    logger.info(
        "[post_call] generating summary room=%s platform=%s recipient=%s",
        room_id, platform, recipient_id,
    )

    summary = await generate_summary(history, openai_client)
    if not summary:
        logger.warning("[post_call] empty summary — nothing to send room=%s", room_id)
        return

    from src.channels.meta_client import send_dm
    result = await send_dm(recipient_id, summary, platform=platform)  # type: ignore[arg-type]

    if result.ok:
        logger.info(
            "[post_call] summary sent ok platform=%s recipient=%s", platform, recipient_id
        )
    else:
        logger.warning(
            "[post_call] summary send failed platform=%s recipient=%s detail=%s",
            platform, recipient_id, result.detail,
        )
