"""WhatsApp inbound media handler — download + process via existing media.py.

Downloads media from ChatDaddy URLs (direct or transcoder fallback),
then routes through src/media.py for transcription/OCR/PDF extraction.
"""

from __future__ import annotations

import ipaddress
import logging
import os
import socket
import tempfile
from pathlib import Path
from urllib.parse import urlparse

import httpx

logger = logging.getLogger("whatsapp.media")

TRANSCODER_URL = "https://api-transcoder.chatdaddy.tech"

# SSRF defense — only allow media fetches against these host suffixes. Any
# URL from a webhook payload (attacker-controlled) MUST pass this check
# before we issue an HTTP request. See _is_url_safe().
_ALLOWED_HOST_SUFFIXES = (
    "chatdaddy.tech",         # api.chatdaddy.tech, api-transcoder.chatdaddy.tech
    "whatsapp.net",           # mmg.whatsapp.net (encrypted media direct URLs)
    "whatsapp.com",           # media.whatsapp.com (rare fallback)
)


def _is_url_safe(url: str) -> bool:
    """Refuse URLs that aren't on our host allowlist or that resolve to
    private / link-local IPs (SSRF defense).

    Returns False (refuses) for:
      - Non-http(s) schemes
      - Hosts not ending in an allowed suffix
      - Hosts that resolve to RFC 1918 / loopback / link-local addresses
    """
    if not url:
        return False
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    if parsed.scheme not in ("http", "https"):
        return False
    host = (parsed.hostname or "").lower()
    if not host:
        return False
    if not any(host == suf or host.endswith("." + suf) for suf in _ALLOWED_HOST_SUFFIXES):
        logger.warning("blocked media URL — host not on allowlist: %s", host)
        return False
    # Resolve and refuse any private / link-local addresses (defeats DNS
    # rebinding to internal services and 169.254.169.254 cloud metadata).
    try:
        for family, *_, sockaddr in socket.getaddrinfo(host, None):
            ip = ipaddress.ip_address(sockaddr[0])
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                logger.warning("blocked media URL — resolves to non-public IP %s (%s)", ip, host)
                return False
    except socket.gaierror:
        # DNS failure — we can't verify, refuse to be safe
        logger.warning("blocked media URL — DNS resolution failed for %s", host)
        return False
    return True

# Mime → extension mapping
_EXT_MAP = {
    "image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp",
    "audio/ogg": ".ogg", "audio/mpeg": ".mp3", "audio/mp4": ".m4a",
    "audio/wav": ".wav", "audio/amr": ".amr", "audio/aac": ".aac",
    "video/mp4": ".mp4", "application/pdf": ".pdf",
}


def _detect_media_type(
    attachment: dict,
) -> str:
    """Detect media category from ChatDaddy attachment dict."""
    att_type = (attachment.get("type") or "").lower()
    mime = (attachment.get("mimetype") or attachment.get("mimeType") or "").lower()

    if att_type in ("image",) or mime.startswith("image/"):
        return "image"
    if att_type in ("audio", "ptt") or mime.startswith("audio/"):
        return "audio"
    if att_type in ("video", "videomessage") or "video" in att_type or mime.startswith("video/"):
        return "video"
    if mime == "application/pdf":
        return "pdf"
    return "unknown"


_OGG_MAGIC = b"OggS"
_WEBM_MAGIC = b"\x1a\x45\xdf\xa3"
_MP3_MAGIC_ID3 = b"ID3"
_MP3_MAGIC_FRAME = b"\xff\xfb"
_FLAC_MAGIC = b"fLaC"
_M4A_FTYP = b"ftyp"  # appears at offset 4 in m4a/mp4

_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
_JPEG_MAGIC = b"\xff\xd8"
_GIF_MAGIC = b"GIF8"
_WEBP_RIFF = b"RIFF"  # RIFF....WEBP — check first 4 bytes


def _has_known_audio_container(data: bytes) -> bool:
    """Check first ~16 bytes for a recognised audio container magic.

    WhatsApp voice notes downloaded via direct URL are sometimes raw opus
    packets (no OGG container) — Whisper rejects them as "Invalid file
    format / 0 seconds". Properly-containered OGG/WebM/MP3/FLAC/M4A all
    have stable magic numbers in the first 16 bytes.
    """
    if not data or len(data) < 8:
        return False
    head = data[:16]
    if head.startswith(_OGG_MAGIC):
        return True
    if head.startswith(_WEBM_MAGIC):
        return True
    if head.startswith(_MP3_MAGIC_ID3) or head.startswith(_MP3_MAGIC_FRAME):
        return True
    if head.startswith(_FLAC_MAGIC):
        return True
    if _M4A_FTYP in head:
        return True
    return False


def _looks_like_image(data: bytes) -> bool:
    """Check first bytes for a recognised image container magic.

    WhatsApp images arrive at mmg.whatsapp.net/*.enc — direct URL returns
    AES-encrypted bytes that do NOT match any image magic. The transcoder
    decrypts them so the result must match a known image header.

    Supports: JPEG, PNG, WebP, GIF, HEIC/HEIF (iPhone default format).
    Ported HEIC support from MIA/src/wa_media.py (2026-05-09).
    """
    if not data or len(data) < 12:
        return False
    head = data[:12]
    if head[:2] == _JPEG_MAGIC:
        return True
    if head[:8] == _PNG_MAGIC:
        return True
    if head[:4] == _GIF_MAGIC:
        return True
    # WebP: "RIFF" at 0-3, then 4 bytes length, then "WEBP" at 8-11
    if head[:4] == _WEBP_RIFF and head[8:12] == b"WEBP":
        return True
    # HEIC/HEIF (iPhone default) — ftyp box size at offset 0
    if head[:4] in (b"\x00\x00\x00\x18", b"\x00\x00\x00\x1c"):
        return True
    if b"ftypheic" in data[:24] or b"ftypheix" in data[:24] or b"ftypmif1" in data[:24]:
        return True
    return False


async def download_media(
    attachment: dict,
    *,
    account_id: str = "",
    chat_id: str = "",
    message_id: str = "",
    api_token: str = "",
    media_kind: str = "",
) -> bytes | None:
    """Download media bytes from a ChatDaddy attachment.

    For audio: prefer transcoder (produces a valid OGG/Opus container),
    fall back to direct URL. The direct URL for WhatsApp voice notes
    sometimes returns raw opus packets without a container, which OpenAI
    Whisper rejects as "Invalid file format / 0 seconds duration"
    (verified live 2026-04-30 06:37:50 — wa_60164245634).

    For images: ALSO prefer transcoder first (2026-05-08).
    WhatsApp images arrive at mmg.whatsapp.net/*.enc — the direct URL
    returns AES-encrypted bytes. The transcoder decrypts them to valid
    JPEG/PNG. Without this fix, all three vision providers (Anthropic,
    Groq, OpenAI) fail because they receive an encrypted blob.
    Validated result via _looks_like_image() before accepting.

    For other media (PDF, video): direct URL first, transcoder as fallback.

    Tries (audio or image):
      1. ChatDaddy transcoder (decrypts + re-encodes)
      2. Direct URL fetch (validate with magic bytes check)
    Tries (other):
      1. Direct URL fetch
      2. ChatDaddy transcoder fallback
    """
    url = attachment.get("url") or attachment.get("directPath") or ""
    if not url:
        logger.warning("No media URL in attachment: %s", attachment)
        return None

    # SSRF defense — webhook-supplied URL must pass allowlist + IP check.
    if not _is_url_safe(url):
        return None

    headers = {}
    if api_token:
        headers["Authorization"] = f"Bearer {api_token}"

    transcoder_url = ""
    if account_id and message_id:
        att_index = 0
        transcoder_url = (
            f"{TRANSCODER_URL}/stream-message-attachment"
            f"/{account_id}/{chat_id}/{message_id}/{att_index}"
        )
    # transcoder_url is built from our constant TRANSCODER_URL so it's
    # always safe, but we still defense-in-depth check it (TRANSCODER_URL
    # is env-configurable in some deployments).
    if transcoder_url and not _is_url_safe(transcoder_url):
        transcoder_url = ""

    async with httpx.AsyncClient(timeout=30.0) as http:
        # ── Audio + Image + Video: prefer transcoder ────────────────────
        # WhatsApp media at *.enc URLs is AES-encrypted — direct fetch
        # returns encrypted bytes that Whisper / vision models reject.
        # The transcoder decrypts all three media types.
        if media_kind in ("audio", "image", "video") and transcoder_url:
            try:
                resp = await http.get(transcoder_url, headers=headers)
                if resp.is_success and resp.content:
                    if media_kind == "audio" and _has_known_audio_container(resp.content):
                        logger.info(
                            "Downloaded audio (%d bytes) via transcoder [valid container, first16=%s]",
                            len(resp.content), resp.content[:16].hex(),
                        )
                        return resp.content
                    elif media_kind == "image" and _looks_like_image(resp.content):
                        logger.info(
                            "Downloaded image (%d bytes) via transcoder [valid header, first8=%s]",
                            len(resp.content), resp.content[:8].hex(),
                        )
                        return resp.content
                    elif media_kind == "video":
                        # No magic-bytes check for video — accept any non-empty response
                        logger.info(
                            "Downloaded video (%d bytes) via transcoder [first16=%s]",
                            len(resp.content), resp.content[:16].hex(),
                        )
                        return resp.content
                    else:
                        logger.warning(
                            "Transcoder returned %s bytes (%d) without recognised magic — "
                            "first16=%s — falling through to direct URL",
                            media_kind, len(resp.content), resp.content[:16].hex(),
                        )
                        # fall through to direct URL
                else:
                    logger.warning(
                        "Transcoder %s fetch failed: status=%d, "
                        "body_preview=%r, url=%s, has_token=%s",
                        media_kind, resp.status_code, resp.text[:200],
                        transcoder_url, bool(api_token),
                    )
            except Exception as e:
                logger.warning(
                    "Transcoder %s download exception: %s: %s",
                    media_kind, type(e).__name__, e,
                )

        # ── Direct URL ──────────────────────────────────────────────
        try:
            resp = await http.get(url, headers=headers)
            if resp.is_success and resp.content:
                if media_kind == "audio" and not _has_known_audio_container(resp.content):
                    logger.warning(
                        "Direct URL audio bytes (%d) missing container header — "
                        "first16=%s — Whisper will likely reject. Trying transcoder.",
                        len(resp.content), resp.content[:16].hex(),
                    )
                    # fall through to transcoder retry below
                elif media_kind == "image" and not _looks_like_image(resp.content):
                    logger.warning(
                        "Direct URL image bytes (%d) missing image magic — "
                        "first16=%s — likely encrypted. Trying transcoder.",
                        len(resp.content), resp.content[:16].hex(),
                    )
                    # fall through to transcoder retry below
                else:
                    logger.info(
                        "Downloaded media (%d bytes) via direct URL [first8=%s]",
                        len(resp.content), resp.content[:8].hex(),
                    )
                    return resp.content
            else:
                logger.warning(
                    "Direct URL fetch failed: status=%d, body_preview=%r",
                    resp.status_code, resp.text[:200],
                )
        except Exception as e:
            logger.warning(
                "Direct URL download exception: %s: %s",
                type(e).__name__, e,
            )

        # ── Transcoder (final fallback) ─────────────────────────────
        if transcoder_url:
            try:
                resp = await http.get(transcoder_url, headers=headers)
                if resp.is_success and resp.content:
                    first16 = resp.content[:16].hex() if resp.content else ""
                    logger.info(
                        "Downloaded media (%d bytes) via transcoder [fallback, first16=%s]",
                        len(resp.content), first16,
                    )
                    return resp.content
                else:
                    logger.warning(
                        "Transcoder fallback failed: status=%d, "
                        "body_preview=%r, url=%s, has_token=%s",
                        resp.status_code, resp.text[:200],
                        transcoder_url, bool(api_token),
                    )
            except Exception as e:
                logger.warning(
                    "Transcoder fallback exception: %s: %s",
                    type(e).__name__, e,
                )

        # ── 3rd fallback: refetch via ChatDaddy /im/messages REST API ─
        # When both direct URL and transcoder fail on a `.enc` payload,
        # ask ChatDaddy to give us the freshest message — the decrypted
        # attachment URL may have appeared after the webhook fired.
        if media_kind == "audio" and account_id and chat_id and message_id and api_token:
            try:
                # Try bare phone first (WABA), then @s.whatsapp.net (regular WA)
                bare_chat = chat_id.split("@")[0]
                for chat_variant in (bare_chat, f"{bare_chat}@s.whatsapp.net"):
                    fetch_url = (
                        f"https://api.chatdaddy.tech/im/messages/"
                        f"{account_id}/{chat_variant}?count=10"
                    )
                    msg_resp = await http.get(fetch_url, headers=headers)
                    if msg_resp.status_code != 200:
                        continue
                    messages = msg_resp.json().get("messages", [])
                    target = next(
                        (m for m in messages if m.get("id") == message_id),
                        None,
                    )
                    if not target:
                        continue
                    fresh_atts = target.get("attachments") or []
                    if not fresh_atts:
                        continue
                    fresh_url = fresh_atts[0].get("url", "")
                    if not fresh_url or fresh_url == url:
                        # Same encrypted URL — no fresh decryption available
                        continue
                    # SSRF — fresh_url originates from upstream API response;
                    # treat it as untrusted and re-check the allowlist.
                    if not _is_url_safe(fresh_url):
                        continue
                    logger.info(
                        "[3rd fallback] Refetched fresh attachment URL via "
                        "ChatDaddy REST: %s", fresh_url[:80],
                    )
                    fresh_resp = await http.get(fresh_url, headers=headers)
                    if fresh_resp.is_success and fresh_resp.content:
                        first16 = fresh_resp.content[:16].hex()
                        logger.info(
                            "Downloaded audio (%d bytes) via REST refetch "
                            "[first16=%s]",
                            len(fresh_resp.content), first16,
                        )
                        return fresh_resp.content
                    break  # found the message but the new URL also failed
            except Exception as e:
                logger.warning(
                    "REST refetch fallback exception: %s: %s",
                    type(e).__name__, e,
                )

    logger.error("All media download attempts failed for %s", url[:100])
    return None


def detect_media_type(attachment: dict) -> str:
    """Public alias for :func:`_detect_media_type`. Used by the orchestrator
    to decide which specialist (if any) should receive the media."""
    return _detect_media_type(attachment)


# NOTE: The Dr. Baba layer also has a `process_attachment` function that
# transcribes audio / describes images / extracts PDF text via `src.media`
# (Whisper + GPT-4o-vision + pypdf). Jessica handles media differently —
# tongue photos go to the Constitution Agent's `analyze_tongue` tool with
# the raw URL or downloaded bytes — so we do NOT port that wrapper. If
# Jessica ever needs general-purpose audio transcription, build a Jessica-
# side media module and import it from the orchestrator, not from here.

