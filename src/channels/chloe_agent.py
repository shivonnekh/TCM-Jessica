"""Chloe — the Instagram / Facebook DM agent (separate route from Jessica).

Chloe (陳芷晴) is the content-creator persona for social channels. She is
intentionally *lighter* than the Jessica clinic pipeline:

    * Greeting-first — every NEW conversation opens with her intro.
    * Warm, educational, short replies (IG-DM cadence).
    * Soft CTA to WhatsApp for deep consultation (where Jessica converts).
    * No 体质 diagnosis / tongue photos / hard sell — those live on WhatsApp.

She reuses the shared CRM (namespaced ``ig_<id>`` / ``fb_<id>`` keys) so
conversation history persists, but does NOT run the Planner→Specialists→
Writer pipeline. One LLM call per turn.

Persona config: ``data/personas/chloe.json`` (env override CHLOE_PERSONA_PATH).
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Final

from src.crm.models import ConversationMessage

logger = logging.getLogger("channels.chloe")

# Base URL for consultation links (override via CONSULT_BASE_URL env var)
_DEFAULT_CONSULT_BASE: Final[str] = "https://tcm-jessica.onrender.com"

_DEFAULT_PERSONA_PATH: Final[str] = str(
    Path(__file__).resolve().parent.parent.parent / "data" / "personas" / "chloe.json"
)
_HISTORY_WINDOW: Final[int] = 16


@dataclass(frozen=True)
class ChloePersona:
    """Immutable Chloe persona profile loaded from JSON."""

    display_name: str
    whatsapp_cta: str
    greeting_bubbles: tuple[str, ...]
    greeting_media_url: str
    system_prompt: str
    model: str
    max_tokens: int
    max_bubbles: int
    cta_after_turns: int = 15
    cta_nudge: str = ""


@dataclass(frozen=True)
class ChloeReply:
    """Bubbles + optional media to send back on a DM."""

    bubbles: list[str] = field(default_factory=list)
    media: list[dict] = field(default_factory=list)  # [{url, after_bubble_idx}]


def _persona_path() -> Path:
    return Path(os.environ.get("CHLOE_PERSONA_PATH", _DEFAULT_PERSONA_PATH))


@lru_cache(maxsize=4)
def _load_persona(path_str: str, mtime: float) -> ChloePersona:
    data = json.loads(Path(path_str).read_text(encoding="utf-8"))
    return ChloePersona(
        display_name=str(data.get("display_name", "Chloe")),
        whatsapp_cta=str(data.get("whatsapp_cta", "")),
        greeting_bubbles=tuple(str(b) for b in data.get("greeting_bubbles", []) if str(b).strip()),
        greeting_media_url=str(data.get("greeting_media_url", "")).strip(),
        system_prompt=str(data.get("system_prompt", "")),
        model=str(data.get("model", "gpt-5.4-mini")),
        max_tokens=int(data.get("max_tokens", 400)),
        max_bubbles=int(data.get("max_bubbles", 3)),
        cta_after_turns=int(data.get("cta_after_turns", 15)),
        cta_nudge=str(data.get("cta_nudge", "")),
    )


def load_persona() -> ChloePersona:
    p = _persona_path()
    mtime = p.stat().st_mtime if p.exists() else 0.0
    return _load_persona(str(p), mtime)


class ChloeAgent:
    """Single-LLM-call social DM agent. Greeting-first, CRM-backed."""

    def __init__(self, client, crm, consultation_repo=None) -> None:
        # client: src.llm.LLMClient ; crm: CRM repo (same instance as pipeline)
        # consultation_repo: src.consultation.repo.ConsultationRepo (optional)
        self._client = client
        self._crm = crm
        self._consult = consultation_repo

    async def respond(
        self, *, crm_key: str, user_message: str, message_id: str | None = None
    ) -> ChloeReply:
        """Produce Chloe's reply for one inbound DM.

        Greeting-first: when the user has no prior conversation history,
        the persona greeting bubbles are sent first, then her answer.
        """
        persona = load_persona()

        # 1. Load user + decide if this is a first-touch conversation.
        # GREET ONCE PER USER: key the greeting off whether the user record
        # already exists — NOT off message history (which can read empty if
        # a persist hiccups, causing repeated greetings). get_or_create_user
        # always creates the row on the first turn, so an existing row means
        # we've met before.
        existing = await self._crm.get_user(crm_key)
        is_first_touch = existing is None
        user = existing if existing is not None else await self._crm.get_or_create_user(crm_key)
        history = list(getattr(user, "conversation_history", []) or [])
        logger.info(
            "[chloe] turn key=%s first_touch=%s history_len=%d existing=%s",
            crm_key, is_first_touch, len(history), existing is not None,
        )

        # 2. Decide whether we need the LLM. On a first-touch PURE greeting
        # (just "hi"/"你好"), the intro greeting IS the whole reply — no LLM
        # call, and no redundant second greeting. Otherwise generate an answer.
        # Booking intent short-circuits LLM — creates a video room immediately.
        need_llm = not (is_first_touch and _is_pure_greeting(user_message))
        answer_bubbles: list[str] = []
        if need_llm and _is_booking_intent(user_message) and self._consult is not None:
            try:
                answer_bubbles = await self._handle_booking(crm_key)
                need_llm = False
            except Exception:  # noqa: BLE001
                logger.exception("[chloe] booking flow failed for %s", crm_key)
                # Fall through to LLM so user still gets a reply
        if need_llm:
            try:
                turns = _count_user_turns(history)
                answer_bubbles = await self._generate(
                    persona, history, user_message, turns=turns
                )
            except Exception:  # noqa: BLE001
                logger.exception("[chloe] LLM generation failed for %s", crm_key)
                answer_bubbles = ["唔好意思，我而家有少少繁忙 🙏 你可以 WhatsApp 我 "
                                  f"{persona.whatsapp_cta}，我盡快覆你 🌿"]

        # 3. Greeting-first composition.
        bubbles: list[str] = []
        media: list[dict] = []
        if is_first_touch:
            bubbles.extend(persona.greeting_bubbles)
            if persona.greeting_media_url:
                media.append({"url": persona.greeting_media_url,
                              "after_bubble_idx": max(0, len(persona.greeting_bubbles) - 1)})
        bubbles.extend(answer_bubbles)
        cap = len(persona.greeting_bubbles) + persona.max_bubbles
        bubbles = [b for b in bubbles if b.strip()][: max(1, cap)]

        # 4. Persist both sides to CRM (best-effort).
        await self._persist(crm_key, user_message, bubbles, message_id)

        return ChloeReply(bubbles=bubbles, media=media)

    # ------------------------------------------------------------------

    async def _handle_booking(self, crm_key: str) -> list[str]:
        """Create a video consultation room and return the patient link bubbles."""
        consult = await self._consult.create(crm_key=crm_key)
        base = os.environ.get("CONSULT_BASE_URL", _DEFAULT_CONSULT_BASE).rstrip("/")
        patient_url = f"{base}{consult.patient_url}"
        logger.info("[chloe] booking room=%s crm=%s url=%s", consult.id, crm_key, patient_url)
        return [
            "好的！我幫你安排咗一個視頻診症房間 🌿",
            f"請點擊以下連結加入：\n{patient_url}",
            "醫師確認時間後會喺同一連結加入，記得開鏡頭同麥克風 📷 如有問題可以 WhatsApp 我哋 🙏",
        ]

    # Voice-call preamble — injected BEFORE the persona system prompt when
    # _generate() is called from a video consultation (voice_call=True).
    # It overrides the DM-specific rules (no-photo, IG cadence, etc.) and
    # establishes that Chloe is in a live video call and can see the patient.
    _VOICE_CALL_PREAMBLE = """\
【重要情境】你現在係喺【視頻問診】，唔係 Instagram 私訊。

你同病人係面對面 video call。以下規則取代 IG DM 規則：

1. 你可以透過病人嘅鏡頭直接睇到佢——唔好叫佢拍照片或者發圖片。
   如需望診，直接請佢對住鏡頭：「可以請你伸一下舌頭嗎？」「請面向鏡頭，我睇一睇你嘅面色。」
2. 回答要係自然口語、適合聆聽，唔好用 bullet points、markdown 或者太多 emoji。
   每次回答 1-3 句自然說話，短而溫暖，似真人面對面傾偈咁。
3. 唔好提 WhatsApp——你哋已經係面對面，唔需要轉去其他平台。
4. 你係喺做正式問診，可以問有關症狀、病史、生活習慣嘅問題，比 IG 更深入。
5. 如果病人問嘅問題需要你睇佢，直接透過鏡頭睇，唔好推搪。

"""

    async def _generate(
        self,
        persona: ChloePersona,
        history: list[ConversationMessage],
        user_message: str,
        *,
        turns: int = 0,
        vision_notes: str = "",
        camera_available: bool = True,
        voice_call: bool = False,
    ) -> list[str]:
        messages: list[dict] = []
        for m in history[-_HISTORY_WINDOW:]:
            role = "user" if getattr(m, "role", "user") == "user" else "assistant"
            messages.append({"role": role, "content": getattr(m, "content", "")})
        messages.append({"role": "user", "content": user_message})

        # In voice calls, prepend the video-consultation preamble so Chloe
        # knows she's NOT in a DM — she can see the patient and should behave
        # like a real face-to-face consultation, not a messaging exchange.
        system = (self._VOICE_CALL_PREAMBLE + persona.system_prompt) if voice_call else persona.system_prompt

        # WhatsApp CTA is relationship-gated: the nudge instruction is only
        # appended once the conversation is ~cta_after_turns deep. Before
        # that, the base prompt tells Chloe NOT to push WhatsApp unsolicited.
        # (CTA nudge is suppressed entirely in voice calls — no need to push WA.)
        if not voice_call and persona.cta_nudge and turns >= persona.cta_after_turns:
            system = system + persona.cta_nudge

        # Inject TCM 望診 context from vision frame analysis (voice calls only).
        #
        # Three cases:
        #   1. Good vision notes → inject observations, ask targeted questions
        #   2. Camera on but analysis unclear (very short) → prompt to show face/tongue
        #   3. Camera off → proactively ask patient to turn it on
        if vision_notes and len(vision_notes) >= 20:
            # Case 1: meaningful observations available
            system = (
                system
                + "\n\n【即時望診記錄（AI望診助理提供）】\n"
                + vision_notes
                + "\n\n請在問診時適時參考以上望診觀察，問出更有針對性的中醫問題。"
                "（例如面色偏白 → 詢問是否怕冷；黑眼圈明顯 → 詢問睡眠質素）"
                "如病人提到某個症狀，可以結合望診觀察加以印證或深入詢問。"
            )
        elif camera_available and not vision_notes:
            # Case 2: camera on but nothing useful captured (bad angle / too dark)
            system = (
                system
                + "\n\n【望診提醒】鏡頭畫面不夠清晰，未能進行望診。"
                "請溫和地請病人調整鏡頭，讓你可以清楚睇到佢嘅面色。"
                "如需睇舌頭，請病人微微伸出舌頭。"
            )
        elif not camera_available:
            # Case 3: camera is off — must ask patient to enable it
            system = (
                system
                + "\n\n【望診提醒】病人現時未有開啟鏡頭。"
                "中醫望診（觀察面色、眼神、舌象）係重要嘅診症環節，必須透過鏡頭進行。"
                "請你溫和但清楚地提醒病人開啟鏡頭，例如：「方便嘅話，可以幫我打開鏡頭嗎？"
                "中醫睇診需要望診，睇一睇你嘅面色同舌苔，會幫助我了解你嘅身體狀況。」"
                "唔好接受病人靠口頭形容代替望診——請堅持叫佢開鏡頭。"
            )

        resp = await self._client.messages.create(
            model=persona.model,
            max_tokens=persona.max_tokens,
            system=system,
            messages=messages,
        )
        text = "".join(
            block.text for block in resp.content if getattr(block, "type", "") == "text"
        )
        return _split_bubbles(text, persona.max_bubbles)

    async def _persist(
        self, crm_key: str, user_message: str, bubbles: list[str], message_id: str | None
    ) -> None:
        now = datetime.utcnow()
        try:
            await self._crm.append_message(
                crm_key,
                ConversationMessage(role="user", content=user_message, at=now,
                                    wa_message_id=message_id),
            )
            reply_text = "\n\n".join(bubbles)
            await self._crm.append_message(
                crm_key,
                ConversationMessage(role="chloe", content=reply_text, at=now),
            )
        except Exception:  # noqa: BLE001
            logger.exception("[chloe] CRM persist failed for %s", crm_key)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


# Booking / consultation intent — triggers video room creation.
_BOOKING_INTENT_RE = re.compile(
    r"約診|預約|睇診|睇醫生|睇醫師|約醫生|約醫師|想睇醫|幫我約|book(?:ing)?|"
    r"consultation|視頻診症|video\s*call|診症|想約|可以約",
    re.IGNORECASE,
)


def _is_booking_intent(text: str) -> bool:
    """True when the message expresses intent to book a consultation."""
    return bool(_BOOKING_INTENT_RE.search((text or "").strip()))


# Whole-message greeting (no health content) → first-touch intro is enough.
_PURE_GREETING_RE = re.compile(
    r"^\s*(?:hi+|hey+|hello+|he+llo+|hihi|yo+|哈囉|哈罗|你好+|您好|早晨|早安|午安|晚安|"
    r"嗨+|喂+|hi 啊|hello 啊|在嗎|在吗|有人嗎|有人吗)\s*[!！~～.。、,，\s]*$",
    re.IGNORECASE,
)


def _is_pure_greeting(text: str) -> bool:
    """True when the whole message is just a greeting (no health content)."""
    return bool(_PURE_GREETING_RE.match((text or "").strip()))


def _count_user_turns(history: list[ConversationMessage]) -> int:
    """Number of user messages so far — the conversation 'depth'."""
    return sum(1 for m in history if getattr(m, "role", "") == "user")


def _split_bubbles(text: str, max_bubbles: int) -> list[str]:
    """Split Chloe's plain-text reply into bubbles on blank lines.

    Falls back to sentence-ish splitting if the model returned one blob.
    Always returns at least one bubble; caps at ``max_bubbles``.
    """
    text = (text or "").strip()
    if not text:
        return []
    parts = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if len(parts) <= 1:
        # single blob — split on newlines as a softer fallback
        parts = [p.strip() for p in text.split("\n") if p.strip()] or [text]
    return parts[:max_bubbles]
