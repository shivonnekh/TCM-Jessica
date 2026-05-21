"""Voice note transcription via OpenAI Whisper.

WhatsApp voice notes arrive as opus/ogg blobs. We decrypt them via
ChatDaddy's transcoder (handled in `src.whatsapp.media.download_media`)
then push the bytes through Whisper (gpt-4o-mini-transcribe by default
— cheaper than whisper-1, comparable quality for Cantonese / 廣東話).
"""

from __future__ import annotations

import io
import logging
import os

from openai import AsyncOpenAI

logger = logging.getLogger("llm_transcribe")

DEFAULT_TRANSCRIBE_MODEL = os.environ.get(
    "OPENAI_TRANSCRIBE_MODEL", "gpt-4o-mini-transcribe"
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
