"""Text-to-Speech via MiniMax T2A — native HK Cantonese voice for Jessica.

Ported (simplified) from dr-baba-agent/src/media_output/tts.py. We keep only
the MiniMax provider because:
  1. Native Cantonese voices (`Cantonese_KindWoman` matches Jessica's brand)
  2. Single provider = simpler ops surface
  3. dr-baba already battle-tested this path in production

Trigger model is **match modality** — voice-reply only when the inbound turn
included a voice note. The decision lives in the WhatsApp router, not here;
this module just exposes ``synthesize`` and the cache file path.

Cache strategy: SHA-256(text + voice) → MP3 in ``data/media/tts/<hash>.mp3``.
The ``/media/tts/<hash>.mp3`` URL is automatically served by the FastAPI
StaticFiles mount in ``src/web.py``.

Env vars:
    TTS_ENABLED              "true" to enable (default "false" — opt-in)
    MINIMAX_API_KEY          MiniMax T2A API key (secret)
    MINIMAX_GROUP_ID         MiniMax group id (optional, appended as query param)
    MINIMAX_TTS_VOICE        Default Jessica voice (default Cantonese_KindWoman)
    MINIMAX_TTS_LANGUAGE     Language hint (default "Chinese,Yue")
    MINIMAX_BASE_URL         Override for the MiniMax API host
    JESSICA_BASE_URL         Absolute base URL so ChatDaddy can fetch the audio
                             (e.g. https://tcm-jessica.onrender.com). If unset
                             we fall back to a relative path which only works
                             for in-process clients (dev sandbox), not WA send.
"""

from __future__ import annotations

import hashlib
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import httpx

logger = logging.getLogger("media.tts")

# ── Config ────────────────────────────────────────────────────────

_DEFAULT_VOICE: Final[str] = "Cantonese_KindWoman"
_DEFAULT_LANGUAGE: Final[str] = "Chinese,Yue"
_DEFAULT_BASE_URL: Final[str] = "https://api.minimax.io"
_DEFAULT_MODEL: Final[str] = "speech-2.8-hd"
_REQUEST_TIMEOUT_S: Final[float] = 30.0


def _is_enabled() -> bool:
    return os.environ.get("TTS_ENABLED", "false").lower() == "true"


def _cache_dir() -> Path:
    """Cache root — under ``data/media/tts/`` so the FastAPI mount serves it.

    Resolved each call so tests can monkey-patch via env vars without
    re-importing the module.
    """
    root = Path(
        os.environ.get(
            "TTS_CACHE_DIR",
            str(Path(__file__).resolve().parent.parent.parent / "data" / "media" / "tts"),
        )
    )
    root.mkdir(parents=True, exist_ok=True)
    return root


# ── Public types ──────────────────────────────────────────────────


@dataclass(frozen=True)
class TTSResult:
    """A successfully synthesised audio clip.

    ``path`` is the on-disk cached file.
    ``url`` is the public URL the WhatsApp client should send.
    ``mime_type`` is always ``audio/mpeg`` for MiniMax MP3 output.
    """

    path: Path
    url: str
    mime_type: str = "audio/mpeg"
    byte_count: int = 0


# ── Public API ────────────────────────────────────────────────────


async def force_synthesize(text: str, *, voice: str | None = None) -> bytes | None:
    """Like ``synthesize`` but bypasses TTS_ENABLED — always calls MiniMax.

    Used by the voice consultation feature which needs TTS regardless of the
    WhatsApp TTS toggle. Returns raw MP3 bytes or None on failure.
    """
    cleaned = _clean_for_speech(text)
    if not cleaned.strip():
        return None
    voice_id = (voice or os.environ.get("MINIMAX_TTS_VOICE") or _DEFAULT_VOICE).strip()
    return await _call_minimax(cleaned, voice_id)


async def synthesize(
    text: str,
    *,
    voice: str | None = None,
    cache: bool = True,
) -> TTSResult | None:
    """Convert ``text`` to a Cantonese audio file via MiniMax T2A.

    Returns ``None`` when:
      - ``TTS_ENABLED`` is not true
      - ``text`` is empty after cleaning
      - the MiniMax API errors out (caller-side never raises; we log)

    Audio files are cached by ``SHA-256(voice + cleaned_text)``. Repeat
    phrases (greetings, common Jessica replies) skip the API call.
    """
    if not _is_enabled():
        return None

    cleaned = _clean_for_speech(text)
    if not cleaned.strip():
        return None

    voice_id = (voice or os.environ.get("MINIMAX_TTS_VOICE") or _DEFAULT_VOICE).strip()

    cache_key = _cache_key(voice_id, cleaned)
    filename = f"{cache_key}.mp3"
    cached_path = _cache_dir() / filename

    if cache and cached_path.exists():
        logger.info("[tts] cache hit voice=%s len=%d", voice_id, len(cleaned))
        return TTSResult(
            path=cached_path,
            url=_public_url(filename),
            byte_count=cached_path.stat().st_size,
        )

    try:
        audio_bytes = await _call_minimax(cleaned, voice_id)
    except Exception:  # noqa: BLE001
        logger.exception("[tts] MiniMax synthesis failed for %d chars", len(cleaned))
        return None

    if not audio_bytes:
        logger.warning("[tts] MiniMax returned no audio for %d chars", len(cleaned))
        return None

    _atomic_write_bytes(cached_path, audio_bytes)
    logger.info(
        "[tts] saved %d bytes voice=%s text=%r",
        len(audio_bytes),
        voice_id,
        cleaned[:40],
    )
    return TTSResult(
        path=cached_path,
        url=_public_url(filename),
        byte_count=len(audio_bytes),
    )


# ── MiniMax HTTP call ─────────────────────────────────────────────


async def _call_minimax(text: str, voice_id: str) -> bytes | None:
    """POST to MiniMax T2A v2; return audio bytes or ``None`` on protocol error.

    MiniMax response shape:
      { "data": {"audio": "<hex>"}, "base_resp": {"status_code": 0, ...} }
    """
    api_key = os.environ.get("MINIMAX_API_KEY", "").strip()
    if not api_key:
        logger.warning("[tts] MINIMAX_API_KEY not set — cannot synthesise")
        return None

    group_id = os.environ.get("MINIMAX_GROUP_ID", "").strip()
    base_url = os.environ.get("MINIMAX_BASE_URL", _DEFAULT_BASE_URL).rstrip("/")
    language = os.environ.get("MINIMAX_TTS_LANGUAGE", _DEFAULT_LANGUAGE)

    url = f"{base_url}/v1/t2a_v2"
    if group_id:
        url += f"?GroupId={group_id}"

    payload = {
        "model": _DEFAULT_MODEL,
        "text": text,
        "voice_setting": {
            "voice_id": voice_id,
            "pitch": 1,      # +1 semitone — Chloe IP voice spec
            "speed": 1.0,
            "vol": 1.0,
        },
        "language_boost": language,
        "audio_setting": {
            "format": "mp3",
            "sample_rate": 32000,
            "bitrate": 128000,
        },
    }

    async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT_S) as client:
        resp = await client.post(
            url,
            json=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )

    if resp.status_code != 200:
        # MiniMax sometimes echoes the bearer token prefix / masked key
        # substring in 401/403 error bodies — never log those bodies.
        if resp.status_code in (401, 403):
            logger.warning("[tts] MiniMax auth error HTTP %d", resp.status_code)
        else:
            logger.warning(
                "[tts] MiniMax HTTP %d body=%s",
                resp.status_code, resp.text[:120],
            )
        return None

    try:
        data = resp.json()
    except ValueError:
        logger.warning("[tts] MiniMax non-JSON response: %s", resp.text[:200])
        return None

    base_resp = data.get("base_resp") or {}
    if base_resp.get("status_code") != 0:
        logger.warning("[tts] MiniMax error: %s", base_resp)
        return None

    audio_hex = (data.get("data") or {}).get("audio") or ""
    if not audio_hex:
        logger.warning("[tts] MiniMax returned no audio keys=%s", list(data.keys()))
        return None

    try:
        return bytes.fromhex(audio_hex)
    except ValueError:
        logger.warning("[tts] MiniMax audio hex decode failed")
        return None


# ── Helpers ───────────────────────────────────────────────────────


def _cache_key(voice_id: str, cleaned_text: str) -> str:
    """16-char SHA-256 hash — enough entropy for our cache size."""
    return hashlib.sha256(f"{voice_id}:{cleaned_text}".encode("utf-8")).hexdigest()[:16]


def _atomic_write_bytes(target: Path, payload: bytes) -> None:
    """Write to a temp file in the same directory, then rename atomically.

    ``Path.write_bytes`` is not atomic — two concurrent turns that hash to
    the same cache key would race and could leave a torn file visible to a
    third reader. ``os.replace`` after ``NamedTemporaryFile`` in the same
    directory is atomic on POSIX (and equivalent on Windows for files on
    the same filesystem), so a reader either sees the full file or nothing.
    """
    import os
    import tempfile

    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        dir=str(target.parent), prefix=".tts-", suffix=".mp3.tmp"
    )
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(payload)
        os.replace(tmp_name, target)
    except Exception:
        # Best-effort cleanup if rename never happened.
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def _public_url(filename: str) -> str:
    """Absolute URL so WhatsApp gateways (ChatDaddy) can fetch the audio.

    Falls back to a relative ``/media/tts/<file>`` for local dev — won't be
    fetchable by ChatDaddy but works for in-process tests.
    """
    base = os.environ.get("JESSICA_BASE_URL", "").rstrip("/")
    if base:
        return f"{base}/media/tts/{filename}"
    return f"/media/tts/{filename}"


# Markdown / emoji / URLs sound terrible when spoken — strip them.
_EMOJI_RANGES = (
    "\U0001F600-\U0001F64F"
    "\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF"
    "\U0001F900-\U0001F9FF"
    "\U00002702-\U000027B0"
    "\U0001FA00-\U0001FA6F"
    "\U0001FA70-\U0001FAFF"
    "\U00002600-\U000026FF"
    "✀-➿"
)


def _clean_for_speech(text: str) -> str:
    """Strip markdown, emoji, and URLs so the speech sounds natural."""
    import re

    # Remove URLs (don't want "h t t p s colon slash slash...")
    text = re.sub(r"https?://\S+", "", text)
    # Remove markdown headers
    text = re.sub(r"#{1,6}\s*", "", text)
    # Remove bold/italic markers
    text = re.sub(r"\*{1,3}([^*]+)\*{1,3}", r"\1", text)
    # Remove bullet markers
    text = re.sub(r"^[\-•·]\s*", "", text, flags=re.MULTILINE)
    # Remove emoji
    text = re.sub(rf"[{_EMOJI_RANGES}⚠️❌✅🔍💊🌿😊✨]+", "", text)
    # Collapse whitespace (multi-bubble joins create runs of newlines)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def merge_bubbles_for_speech(bubbles: list[str]) -> str:
    """Join Jessica's bubble list into ONE coherent script for a single audio file.

    Strategy:
      - Drop empty bubbles
      - Join with a sentence-ending pause (full stop + space) so MiniMax
        inserts a natural breath between thoughts
      - Then run through ``_clean_for_speech`` which collapses whitespace
    """
    parts = [b.strip() for b in bubbles if b and b.strip()]
    if not parts:
        return ""
    joined = "。 ".join(parts)
    # Avoid double full-stops when a bubble already ends in 。 ！ ？
    joined = (
        joined.replace("。。 ", "。 ")
        .replace("！。 ", "！ ")
        .replace("？。 ", "？ ")
        .replace(".。 ", ". ")
    )
    return joined
