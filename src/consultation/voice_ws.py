"""Voice AI WebSocket handler — the AI practitioner side of a consultation.

Flow per turn:
  0. Browser sends JSON {type:'vision_frame', image_b64:'...'} (camera frame)
     → server starts GPT-4o Vision analysis as an asyncio.Task (concurrent)
  1. Browser sends binary audio blob (WebM/Opus or MP4 from MediaRecorder)
  2. Whisper transcribes → emit transcript back to client
     (while STT runs, vision analysis is completing in background)
  3. Collect vision_notes (await task with 3s timeout)
  4. ChloeAgent._generate() produces reply bubbles (vision_notes injected)
  5. MiniMax TTS converts reply to MP3 bytes
  6. Server sends JSON response: {type, text, audio_b64}
  7. Browser plays audio + shows subtitles

On disconnect: post-call summary generated + sent back to patient's platform.
In-memory conversation history scoped to the WebSocket connection — no CRM
persistence for voice calls in v1 (fast, no side effects on existing DM flow).
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os

from fastapi import WebSocket, WebSocketDisconnect

from src.channels.chloe_agent import ChloeAgent, load_persona
from src.consultation.tcm_vision import analyze_vision_frame
from src.crm.models import ConversationMessage
from src.llm_transcribe import transcribe_audio
from src.media.tts import force_synthesize, merge_bubbles_for_speech

logger = logging.getLogger("consultation.voice_ws")

# Chloe uses GentleLady for the IP persona; fallback to KindWoman if unset.
_CHLOE_VOICE = os.environ.get("CHLOE_VOICE", "Cantonese_GentleLady")


def _audio_filename(data: bytes) -> str:
    """Detect audio container from magic bytes → correct extension for Whisper."""
    if len(data) < 12:
        return "voice.webm"
    # WebM: 0x1A 0x45 0xDF 0xA3
    if data[:4] == b"\x1a\x45\xdf\xa3":
        return "voice.webm"
    # MP4 / M4A: bytes 4-8 = 'ftyp'
    if data[4:8] == b"ftyp":
        return "voice.mp4"
    # OGG: 'OggS'
    if data[:4] == b"OggS":
        return "voice.ogg"
    # Default — Whisper will try to parse anyway
    logger.debug("[voice] unknown audio magic=%s", data[:8].hex())
    return "voice.webm"


_WELCOME_TEXT = (
    "你好，歡迎嚟到陳芷晴中醫師嘅視像問診。"
    "我係 AI 問診助手，會先幫你了解今日嘅身體情況同唔舒服嘅地方。"
    "你可以簡單講低你今日想睇嘅問題。"
    "準備好，我哋而家開始。"
)

# Module-level cache — generated once at startup, reused for every connection.
_welcome_audio_cache: bytes | None = None


async def warmup_welcome_audio() -> None:
    """Pre-generate welcome TTS at server startup so first patient gets instant audio."""
    global _welcome_audio_cache
    try:
        _welcome_audio_cache = await force_synthesize(_WELCOME_TEXT, voice=_CHLOE_VOICE)
        logger.info(
            "[voice] welcome audio cached %d bytes", len(_welcome_audio_cache or b"")
        )
    except Exception:  # noqa: BLE001
        logger.exception("[voice] welcome audio warmup failed — will generate on demand")


async def handle_voice(
    websocket: WebSocket,
    room_id: str,
    chloe: ChloeAgent,
) -> None:
    """Drive the voice AI call for one browser connection."""
    await websocket.accept()
    persona = load_persona()
    history: list[ConversationMessage] = []
    vision_notes: str = ""               # latest TCM inspection notes
    vision_task: asyncio.Task | None = None  # concurrent vision analysis
    logger.info("[voice] connected room=%s", room_id)

    # ── Welcome message — Chloe speaks first ──────────────────────
    # Use pre-cached audio if available (generated at startup) — zero latency.
    # Fall back to live generation if warmup hasn't finished yet.
    welcome_audio: bytes | None = _welcome_audio_cache
    if welcome_audio:
        logger.info("[voice] using cached welcome audio room=%s", room_id)
    else:
        logger.info("[voice] cache miss — generating welcome TTS room=%s", room_id)
        try:
            welcome_audio = await force_synthesize(_WELCOME_TEXT, voice=_CHLOE_VOICE)
        except Exception:  # noqa: BLE001
            logger.exception("[voice] welcome TTS failed room=%s", room_id)

    # Send welcome response first (plays audio, shows subtitle)
    welcome_payload: dict = {"type": "response", "text": _WELCOME_TEXT}
    if welcome_audio:
        welcome_payload["audio_b64"] = base64.b64encode(welcome_audio).decode("ascii")
    await websocket.send_json(welcome_payload)

    # Now signal ready — browser starts VAD after welcome audio plays
    await websocket.send_json({"type": "ready", "text": "已連接 陳芷晴中醫師 🌿"})

    # Add welcome to history so Chloe remembers she already introduced herself
    from datetime import datetime, timezone
    _now = datetime.now(timezone.utc)
    history.append(ConversationMessage(role="chloe", content=_WELCOME_TEXT, at=_now))

    try:
        while True:
            msg = await websocket.receive()

            # Handle disconnect cleanly (raw receive returns dict, not exception)
            msg_type = msg.get("type", "")
            if msg_type == "websocket.disconnect":
                logger.info("[voice] browser disconnected room=%s", room_id)
                break

            # ── JSON text messages (vision frame, etc.) ────────────
            if text_data := msg.get("text"):
                try:
                    json_msg = json.loads(text_data)
                    if json_msg.get("type") == "vision_frame":
                        img_b64 = json_msg.get("image_b64", "")
                        if img_b64:
                            # Cancel any in-flight analysis before starting a new one
                            if vision_task and not vision_task.done():
                                vision_task.cancel()
                            vision_task = asyncio.create_task(
                                analyze_vision_frame(img_b64, chloe._client._openai)
                            )
                            logger.info(
                                "[voice] vision_frame received, analysis started room=%s "
                                "img_len=%d", room_id, len(img_b64),
                            )
                except Exception:  # noqa: BLE001
                    logger.debug("[voice] failed to parse text msg room=%s", room_id)
                continue

            # ── binary audio blob ──────────────────────────────────
            audio_bytes: bytes | None = msg.get("bytes")
            if not audio_bytes:
                logger.debug("[voice] non-binary message type=%s room=%s", msg_type, room_id)
                continue

            logger.info("[voice] received audio %d bytes room=%s", len(audio_bytes), room_id)
            await websocket.send_json({"type": "status", "text": "聽緊…"})

            # 1. STT
            filename = _audio_filename(audio_bytes)
            logger.info("[voice] starting STT room=%s format=%s", room_id, filename)
            user_text = await transcribe_audio(
                audio_bytes,
                filename_hint=filename,
                client=chloe._client._openai,  # reuse existing AsyncOpenAI client
            )
            if not user_text:
                logger.warning("[voice] STT returned empty room=%s", room_id)
                await websocket.send_json({
                    "type": "error",
                    "text": "唔聽到你講嘢，請再試一次 🙏",
                })
                continue

            logger.info("[voice] STT ok room=%s transcript=%r", room_id, user_text[:80])
            await websocket.send_json({"type": "transcript", "text": user_text})
            await websocket.send_json({"type": "status", "text": "諗緊…"})

            # 2. Collect vision analysis (started concurrently with STT) ──
            if vision_task is not None:
                if not vision_task.done():
                    try:
                        vision_notes = await asyncio.wait_for(
                            asyncio.shield(vision_task), timeout=3.0
                        )
                        logger.info("[voice] vision_task done room=%s notes_len=%d",
                                    room_id, len(vision_notes))
                    except asyncio.TimeoutError:
                        logger.warning("[voice] vision analysis timed out room=%s", room_id)
                    except Exception:  # noqa: BLE001
                        logger.exception("[voice] vision task error room=%s", room_id)
                else:
                    try:
                        vision_notes = vision_task.result() or ""
                    except Exception:  # noqa: BLE001
                        vision_notes = ""

            # 3. LLM — Chloe generates reply (reuse private _generate)
            logger.info("[voice] calling LLM room=%s vision=%s",
                        room_id, bool(vision_notes))
            try:
                bubbles = await chloe._generate(
                    persona, history, user_text,
                    turns=len([m for m in history if m.role == "user"]),
                    vision_notes=vision_notes,
                )
                logger.info("[voice] LLM ok room=%s bubbles=%d", room_id, len(bubbles))
            except Exception:  # noqa: BLE001
                logger.exception("[voice] LLM failed room=%s", room_id)
                bubbles = ["唔好意思，我而家有少少問題，請稍後再試 🙏"]

            reply_text = "\n".join(bubbles)
            await websocket.send_json({"type": "status", "text": "回緊…"})

            # 4. TTS — Cantonese_GentleLady voice
            logger.info("[voice] calling TTS room=%s", room_id)
            speech_text = merge_bubbles_for_speech(bubbles)
            audio_mp3: bytes | None = None
            try:
                audio_mp3 = await force_synthesize(speech_text, voice=_CHLOE_VOICE)
                logger.info("[voice] TTS ok room=%s bytes=%s",
                            room_id, len(audio_mp3) if audio_mp3 else "None")
            except Exception:  # noqa: BLE001
                logger.exception("[voice] TTS failed room=%s", room_id)

            # 5. Update in-memory history
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc)
            history.append(ConversationMessage(role="user", content=user_text, at=now))
            history.append(ConversationMessage(role="chloe", content=reply_text, at=now))
            # Keep last 20 turns in memory
            if len(history) > 20:
                history = history[-20:]

            # 6. Send response — text always, audio if TTS succeeded
            payload: dict = {"type": "response", "text": reply_text}
            if audio_mp3:
                payload["audio_b64"] = base64.b64encode(audio_mp3).decode("ascii")
            logger.info("[voice] sending response room=%s has_audio=%s", room_id, bool(audio_mp3))
            await websocket.send_json(payload)

    except WebSocketDisconnect:
        logger.info("[voice] disconnected (exception) room=%s", room_id)
    except Exception:  # noqa: BLE001
        logger.exception("[voice] unexpected error room=%s", room_id)
    finally:
        # Send post-call summary back to the patient's origin platform (IG / Messenger)
        repo = getattr(getattr(websocket, "app", None), "state", None)
        repo = getattr(repo, "consultation_repo", None) if repo else None
        if repo and history:
            try:
                from src.consultation.post_call import send_post_call_summary
                await send_post_call_summary(
                    room_id=room_id,
                    history=history,
                    repo=repo,
                    openai_client=chloe._client._openai,
                )
            except Exception:  # noqa: BLE001
                logger.exception("[post_call] failed room=%s", room_id)
