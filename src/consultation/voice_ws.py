"""Voice AI WebSocket handler — the AI practitioner side of a consultation.

Flow per turn:
  1. Browser sends binary audio blob (WebM/Opus from MediaRecorder)
  2. Whisper transcribes → emit transcript back to client
  3. ChloeAgent._generate() produces reply bubbles
  4. MiniMax TTS converts reply to MP3 bytes
  5. Server sends JSON response: {type, text, audio_b64}
  6. Browser plays audio + shows text

In-memory conversation history scoped to the WebSocket connection — no CRM
persistence for voice calls in v1 (fast, no side effects on existing DM flow).
"""

from __future__ import annotations

import base64
import logging
import os

from fastapi import WebSocket, WebSocketDisconnect

from src.channels.chloe_agent import ChloeAgent, load_persona
from src.crm.models import ConversationMessage
from src.llm_transcribe import transcribe_audio
from src.media.tts import force_synthesize, merge_bubbles_for_speech

logger = logging.getLogger("consultation.voice_ws")

# Chloe uses GentleLady for the IP persona; fallback to KindWoman if unset.
_CHLOE_VOICE = os.environ.get("CHLOE_VOICE", "Cantonese_GentleLady")


async def handle_voice(
    websocket: WebSocket,
    room_id: str,
    chloe: ChloeAgent,
) -> None:
    """Drive the voice AI call for one browser connection."""
    await websocket.accept()
    persona = load_persona()
    history: list[ConversationMessage] = []

    await websocket.send_json({"type": "ready", "text": "已連接 Chloe 🌿"})
    logger.info("[voice] connected room=%s", room_id)

    try:
        while True:
            msg = await websocket.receive()

            # ── binary audio blob ──────────────────────────────────
            audio_bytes: bytes | None = msg.get("bytes")
            if not audio_bytes:
                continue

            await websocket.send_json({"type": "status", "text": "聽緊…"})

            # 1. STT
            user_text = await transcribe_audio(
                audio_bytes,
                filename_hint="voice.webm",
                client=chloe._client._openai,  # reuse existing AsyncOpenAI client
            )
            if not user_text:
                await websocket.send_json({
                    "type": "error",
                    "text": "唔聽到你講嘢，請再試一次 🙏",
                })
                continue

            logger.info("[voice] room=%s transcript=%r", room_id, user_text[:60])
            await websocket.send_json({"type": "transcript", "text": user_text})
            await websocket.send_json({"type": "status", "text": "諗緊…"})

            # 2. LLM — Chloe generates reply (reuse private _generate)
            try:
                bubbles = await chloe._generate(
                    persona, history, user_text,
                    turns=len([m for m in history if m.role == "user"]),
                )
            except Exception:  # noqa: BLE001
                logger.exception("[voice] LLM failed room=%s", room_id)
                bubbles = ["唔好意思，我而家有少少問題，請稍後再試 🙏"]

            reply_text = "\n".join(bubbles)
            await websocket.send_json({"type": "status", "text": "回緊…"})

            # 3. TTS — Cantonese_GentleLady voice
            speech_text = merge_bubbles_for_speech(bubbles)
            audio_mp3: bytes | None = None
            try:
                audio_mp3 = await force_synthesize(speech_text, voice=_CHLOE_VOICE)
            except Exception:  # noqa: BLE001
                logger.exception("[voice] TTS failed room=%s", room_id)

            # 4. Update in-memory history
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc)
            history.append(ConversationMessage(role="user", content=user_text, at=now))
            history.append(ConversationMessage(role="chloe", content=reply_text, at=now))
            # Keep last 20 turns in memory
            if len(history) > 20:
                history = history[-20:]

            # 5. Send response — text always, audio if TTS succeeded
            payload: dict = {"type": "response", "text": reply_text}
            if audio_mp3:
                payload["audio_b64"] = base64.b64encode(audio_mp3).decode("ascii")
            await websocket.send_json(payload)

    except WebSocketDisconnect:
        logger.info("[voice] disconnected room=%s", room_id)
    except Exception:  # noqa: BLE001
        logger.exception("[voice] unexpected error room=%s", room_id)
