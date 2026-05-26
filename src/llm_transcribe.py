"""Voice note transcription via OpenAI Whisper-class models.

WhatsApp voice notes arrive as opus/ogg blobs. We decrypt them via
ChatDaddy's transcoder (handled in `src.whatsapp.media.download_media`)
then push the bytes through OpenAI audio transcription API.

Model history (this file):
  - whisper-1                  (legacy, ~$0.006/min)
  - gpt-4o-mini-transcribe     (cheap, but **retires 2026-06-01**)
  - gpt-4o-transcribe          (current default, replaces mini-transcribe)
                                — comparable quality for Cantonese / 廣東話,
                                  modest price increase, future-proof
"""

from __future__ import annotations

import io
import logging
import os

from openai import AsyncOpenAI

logger = logging.getLogger("llm_transcribe")

# Migration 2026-05-26: gpt-4o-mini-transcribe retires 2026-06-01.
# gpt-4o-transcribe is the recommended replacement (no mini-tier
# successor in the new generation). Override via env if needed.
DEFAULT_TRANSCRIBE_MODEL = os.environ.get(
    "OPENAI_TRANSCRIBE_MODEL", "gpt-4o-transcribe"
)

# Cantonese hint — Whisper supports ISO-639-1 codes. "yue" isn't on the
# list so we use "zh" with a prompt hint for HK 廣東話.
_LANGUAGE = os.environ.get("OPENAI_TRANSCRIBE_LANGUAGE", "zh")
_PROMPT_HINT = "以下係香港廣東話口語對話，混雜少量英文。"


async def transcribe_audio(
    audio_bytes: bytes,
    *,
    filename_hint: str = "voice.ogg",
    client: AsyncOpenAI | None = None,
) -> str:
    """Return the transcribed text, or empty string on failure (never raises)."""
    if not audio_bytes:
        return ""
    oai = client or AsyncOpenAI()
    buf = io.BytesIO(audio_bytes)
    buf.name = filename_hint  # OpenAI uses the extension for format detection
    try:
        resp = await oai.audio.transcriptions.create(
            model=DEFAULT_TRANSCRIBE_MODEL,
            file=buf,
            language=_LANGUAGE,
            prompt=_PROMPT_HINT,
        )
        text = (resp.text or "").strip()
        logger.info("transcribed %d bytes → %d chars", len(audio_bytes), len(text))
        return text
    except Exception as exc:  # noqa: BLE001
        logger.exception("whisper transcribe failed (%d bytes): %s", len(audio_bytes), exc)
        return ""
