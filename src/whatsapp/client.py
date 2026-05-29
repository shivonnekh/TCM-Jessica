"""ChatDaddy IM API client — send messages + token management.

Ported from AOS 2.0 chatdaddyService.ts to Python/httpx.
Only supports IM API variant (api.chatdaddy.tech/im/messages).

Supports two auth modes:
  1. API token (apit_*) — used directly as Bearer token, no refresh needed
  2. Refresh token — exchanged for short-lived access token every 50 min
"""

from __future__ import annotations

import asyncio
import logging
import os
import random
import time

import httpx

logger = logging.getLogger("whatsapp.client")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CHATDADDY_IM_API = "https://api.chatdaddy.tech/im/messages"
CHATDADDY_AUTH_URL = "https://api.chatdaddy.tech/auth/token"
WA_MESSAGE_LIMIT = 4096
TOKEN_REFRESH_INTERVAL_S = 3000  # 50 minutes (tokens last 60 min)
CHUNK_SEND_DELAY_S = 0.5        # Delay between multi-chunk messages (legacy)

# Bubble-style splitting for natural WhatsApp feel.
#
# Timing model — two components:
#   1. THINK_BASE — baseline "reading / composing" pause before typing starts
#   2. PER_CHAR   — typing time proportional to bubble length
# Plus random JITTER so the cadence doesn't look mechanical across 5 bubbles.
#
# Tunable live via env vars without a redeploy (useful for tuning perceived
# naturalness based on real user feedback).
BUBBLE_TARGET = 150              # Target chars per bubble
BUBBLE_MAX = 250                 # Hard max — never exceed
BUBBLE_DELAY_MIN = float(os.environ.get("WA_BUBBLE_DELAY_MIN", "2.5"))
BUBBLE_DELAY_MAX = float(os.environ.get("WA_BUBBLE_DELAY_MAX", "6.0"))
BUBBLE_DELAY_THINK_BASE = float(os.environ.get("WA_BUBBLE_DELAY_THINK_BASE", "1.8"))
BUBBLE_DELAY_PER_CHAR = float(os.environ.get("WA_BUBBLE_DELAY_PER_CHAR", "0.020"))
BUBBLE_DELAY_JITTER = float(os.environ.get("WA_BUBBLE_DELAY_JITTER", "0.6"))

# Hard cutoff on outbound sends — httpx's own timeout has been observed to
# hang past 30s when ChatDaddy /im/messages wedges. asyncio.wait_for at this
# value is the last line of defense.
#
# Bumped 2026-04-29 from 20s → 45s after observing ChatDaddy regularly
# accepting the message but taking 25-40s to return the 200. With the
# old 20s timeout we'd fire the apology AFTER ChatDaddy had already
# delivered the real reply — customer saw both messages back-to-back.
# 45s is a more honest deadline for "actually wedged vs just slow".
SEND_TIMEOUT_S = float(os.environ.get("CHATDADDY_SEND_TIMEOUT_S", "45.0"))


class SendProbablyDeliveredError(Exception):
    """Raised when our request to ChatDaddy timed out waiting for the 200 ACK
    but the message was almost certainly delivered (ChatDaddy commonly
    queues + delivers within ~5s but takes 25-40s to confirm). Callers
    should treat this as 'sent' for apology-suppression purposes — if we
    fire the generic 'system error' apology when the customer ACTUALLY
    got the real reply, they see both messages stacked."""

# ---------------------------------------------------------------------------
# Module-level token state (refreshed in background)
# ---------------------------------------------------------------------------

_access_token: str = ""
_token_expires_at: float = 0.0
_is_static_token: bool = False   # True if using apit_* token (no refresh needed)
_http: httpx.AsyncClient | None = None


def _get_http() -> httpx.AsyncClient:
    global _http
    if _http is None or _http.is_closed:
        _http = httpx.AsyncClient(timeout=30.0)
    return _http


# ---------------------------------------------------------------------------
# Token management
# ---------------------------------------------------------------------------

def _detect_token_type(token: str) -> bool:
    """Return True if this is a static API token (apit_*), False if refresh token."""
    return token.startswith("apit_")


async def refresh_token() -> str:
    """Get or exchange a token for the ChatDaddy API.

    Three modes (controlled by env vars):

    1. Static API token — CHATDADDY_REFRESH_TOKEN starts with 'apit_'.
       Used directly as Bearer token, never refreshed.
       Limitation: rejected by api-transcoder.chatdaddy.tech (jwt malformed).

    2. Refresh token + teamId — CHATDADDY_REFRESH_TOKEN is a UUID and
       CHATDADDY_TEAM_ID is set (also a UUID). We POST {refreshToken,
       teamId} to /auth/token and receive a JWT access_token. JWT works
       for BOTH the regular IM API AND the transcoder service. This is
       the path that unblocks WhatsApp voice transcription.

    3. Legacy refresh token — CHATDADDY_REFRESH_TOKEN is a UUID but
       CHATDADDY_TEAM_ID is unset. POST {refreshToken, grantType} —
       returns 400 from current ChatDaddy schema (validated 2026-04-30).
       Kept only for backwards compat; emits a clear error message.
    """
    global _access_token, _token_expires_at, _is_static_token

    raw_token = os.environ.get("CHATDADDY_REFRESH_TOKEN", "")
    if not raw_token:
        raise RuntimeError("CHATDADDY_REFRESH_TOKEN not set")

    # Mode 1: Static API token — use directly, never expires
    if _detect_token_type(raw_token):
        _access_token = raw_token
        _token_expires_at = time.time() + 86400 * 365  # "never"
        _is_static_token = True
        logger.info("Using static ChatDaddy API token (apit_*)")
        return _access_token

    # Modes 2 & 3: Refresh token exchange
    _is_static_token = False
    team_id = os.environ.get("CHATDADDY_TEAM_ID", "").strip()

    if team_id:
        # Mode 2: refresh token + teamId — current ChatDaddy schema. Returns
        # a real JWT that works for both api.chatdaddy.tech AND the
        # transcoder service.
        payload = {"refreshToken": raw_token, "teamId": team_id}
        auth_mode = "refresh_token + teamId (JWT)"
    else:
        # Mode 3: legacy. Will return 400 from current schema; kept so the
        # error is loud rather than silent.
        payload = {"refreshToken": raw_token, "grantType": "refresh_token"}
        auth_mode = "refresh_token (legacy, no teamId)"
        logger.warning(
            "CHATDADDY_REFRESH_TOKEN is a UUID but CHATDADDY_TEAM_ID is unset. "
            "Auth WILL fail under current ChatDaddy schema. Either set "
            "CHATDADDY_TEAM_ID (UUID), or revert CHATDADDY_REFRESH_TOKEN to "
            "an apit_* static API token."
        )

    http = _get_http()
    resp = await http.post(CHATDADDY_AUTH_URL, json=payload)

    if resp.status_code >= 400:
        body_preview = resp.text[:300]
        raise RuntimeError(
            f"ChatDaddy auth failed ({auth_mode}): "
            f"status={resp.status_code} body={body_preview!r}"
        )

    data = resp.json()
    # ChatDaddy returns either 'access_token' (snake_case, current) or
    # 'accessToken' (camelCase, legacy). Accept both.
    _access_token = data.get("access_token") or data.get("accessToken") or ""
    expires_in = int(
        data.get("expires_in") or data.get("expiresIn") or 3600
    )
    _token_expires_at = time.time() + expires_in - 60  # Refresh 1 min early

    if not _access_token:
        raise RuntimeError(f"ChatDaddy auth returned no token: {data}")

    logger.info(
        "ChatDaddy token refreshed via %s (expires in %ds)",
        auth_mode, expires_in,
    )
    return _access_token


async def get_token() -> str:
    """Return current access token, refreshing if expired."""
    if not _access_token or time.time() >= _token_expires_at:
        return await refresh_token()
    return _access_token


async def start_token_refresh_loop() -> None:
    """Background coroutine that keeps the token fresh.

    For static API tokens (apit_*), initializes once then sleeps forever.
    For refresh tokens, re-exchanges every 50 minutes.
    """
    # Initial token load
    try:
        await refresh_token()
    except Exception:
        logger.exception("ChatDaddy initial token load failed — retrying in 30s")
        await asyncio.sleep(30)
        await refresh_token()  # One retry, then let it crash

    # If static token, no refresh loop needed
    if _is_static_token:
        logger.info("Static API token — no refresh loop needed")
        # Keep coroutine alive so lifespan can cancel it cleanly
        while True:
            await asyncio.sleep(3600)
        return

    # Refresh loop for exchange-based tokens
    while True:
        await asyncio.sleep(TOKEN_REFRESH_INTERVAL_S)
        try:
            await refresh_token()
        except Exception:
            logger.exception("ChatDaddy token refresh failed — retrying in 30s")
            await asyncio.sleep(30)


# ---------------------------------------------------------------------------
# Send message
# ---------------------------------------------------------------------------

async def send_message(
    account_id: str,
    chat_id: str,
    text: str,
    attachments: list[dict] | None = None,
    buttons: list[dict] | None = None,
) -> None:
    """Send a WhatsApp message via ChatDaddy IM API.

    URL: POST https://api.chatdaddy.tech/im/messages/{accountId}/{chatId}
    Body: { text, miscOptions: { withTyping: true }, attachments?, buttons? }

    buttons format: [{"id": "btn-id", "text": "Button Label"}, ...]
    Note: buttons are only supported on the last bubble of a multi-bubble reply.
    """
    from urllib.parse import quote

    token = await get_token()
    url = f"{CHATDADDY_IM_API}/{quote(account_id, safe='')}/{quote(chat_id, safe='')}"
    payload: dict = {
        "text": text,
        "miscOptions": {"withTyping": True},
    }
    if attachments:
        payload["attachments"] = attachments
    if buttons:
        payload["buttons"] = buttons

    http = _get_http()
    print(f"[SEND-DEBUG] Calling ChatDaddy: url={url[:100]} text_len={len(text)}")

    # Belt-and-suspenders: asyncio.wait_for wraps the httpx call so a wedged
    # connection pool can't block forever. httpx's own timeout has been
    # observed to hang past 30s in production — this is the hard cutoff.
    try:
        resp = await asyncio.wait_for(
            http.post(
                url,
                json=payload,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                    "accept": "application/json",
                },
            ),
            timeout=SEND_TIMEOUT_S,
        )
    except asyncio.TimeoutError:
        # ChatDaddy frequently accepts the message and starts processing
        # but the response takes longer than SEND_TIMEOUT_S. The message
        # has typically ALREADY been delivered to WhatsApp by the time
        # our timeout fires — we just didn't get the 200 ACK in time.
        # Wrap the error so the caller can distinguish "definitely
        # failed" from "probably delivered, just slow ack".
        print(f"[SEND-DEBUG] TIMEOUT after {SEND_TIMEOUT_S}s — ChatDaddy /im/messages slow ack (msg likely delivered)")
        logger.error(
            "ChatDaddy send timed out after %ss — treating as probably-delivered "
            "(chat_id=%s, text_len=%d)",
            SEND_TIMEOUT_S, chat_id, len(text),
        )
        raise SendProbablyDeliveredError(
            f"ChatDaddy ack timed out after {SEND_TIMEOUT_S}s — "
            f"message probably delivered, just slow response"
        )
    except httpx.HTTPError as exc:
        print(f"[SEND-DEBUG] HTTP ERROR: {type(exc).__name__}: {exc}")
        logger.error("ChatDaddy send HTTP error: %s", exc)
        raise

    print(f"[SEND-DEBUG] ChatDaddy response: status={resp.status_code}")
    if not resp.is_success:
        print(f"[SEND-DEBUG] FAILED: {resp.status_code} — {resp.text[:300]}")
        logger.error("ChatDaddy send failed (%d): %s", resp.status_code, resp.text)
        resp.raise_for_status()

    print(f"[SEND-DEBUG] OK: sent to {chat_id} ({len(text)} chars)")


async def send_long_message(
    account_id: str,
    chat_id: str,
    text: str,
) -> None:
    """Send a message as natural WhatsApp bubbles with typing delays.

    Each bubble after the first is preceded by a human-like pause
    (see `_typing_delay`) so a 5-bubble reply doesn't arrive all at once.
    """
    bubbles = split_into_bubbles(text)
    for i, bubble in enumerate(bubbles):
        if i > 0:
            delay = _typing_delay(bubble)
            logger.debug(
                "[WA] Bubble %d/%d delay=%.2fs len=%d",
                i + 1, len(bubbles), delay, len(bubble),
            )
            await asyncio.sleep(delay)
        await send_message(account_id, chat_id, bubble)


def _typing_delay(text: str, rng: random.Random | None = None) -> float:
    """Natural typing delay for a bubble of text.

    Model: think_base + (per_char * length) + jitter, clamped to [MIN, MAX].

    A short bubble gets roughly MIN (feels like a quick "hm, yes"),
    a long bubble gets closer to MAX (feels like composing a thought).
    Jitter breaks the mechanical cadence that 5 identical delays would have.

    `rng` is injectable for deterministic tests; defaults to the module random.
    """
    typing_time = max(0, len(text)) * BUBBLE_DELAY_PER_CHAR
    jitter_source = rng if rng is not None else random
    jitter = jitter_source.uniform(-BUBBLE_DELAY_JITTER, BUBBLE_DELAY_JITTER)
    raw = BUBBLE_DELAY_THINK_BASE + typing_time + jitter
    return max(BUBBLE_DELAY_MIN, min(BUBBLE_DELAY_MAX, raw))


# ---------------------------------------------------------------------------
# Bubble-style response splitting
# ---------------------------------------------------------------------------

import re

# Patterns that should stay together (not split mid-item)
_BULLET_RE = re.compile(r"^[\s]*[-•·]\s", re.MULTILINE)
_NUMBERED_RE = re.compile(r"^[\s]*\d+[.️⃣)]\s", re.MULTILINE)
_EMOJI_NUMBERED_RE = re.compile(r"^[\s]*[0-9]️⃣\s", re.MULTILINE)


def split_into_bubbles(
    text: str,
    target: int = BUBBLE_TARGET,
    hard_max: int = BUBBLE_MAX,
) -> list[str]:
    """Split text into small WhatsApp-friendly bubbles.

    Strategy:
      1. Split on paragraph breaks (\\n\\n) first — natural thought boundaries
      2. Within paragraphs, split on bullet/numbered list items
      3. Within items, split on sentence boundaries if still over target
      4. Merge tiny fragments (< 30 chars) with adjacent bubble
    """
    if not text or not text.strip():
        return [text] if text else []

    # Phase 1: split on PARAGRAPH boundaries (\n\n) ONLY.
    # 2026-05-21: reverted from "split on every \n" because the LLM was
    # producing structured KB content (headers + bullets + numbered
    # steps) as one block with \n separators, and the splitter was
    # blasting it into 15+ bubbles. Now: \n\n is the bubble boundary;
    # single \n lines stay together in one bubble (capped at BUBBLE_MAX
    # in phase 2/3).
    #
    # Effect on prompt design: bot wanting empathy + question in separate
    # bubbles must write them with \n\n between (already the prompt rule).
    # Structured lists with \n\n between SECTIONS still split correctly.
    paragraphs: list[str] = []
    for block in text.split("\n\n"):
        stripped = block.strip()
        if stripped:
            paragraphs.append(stripped)

    # Phase 2: break large paragraphs into list items or sentences
    raw_chunks: list[str] = []
    for para in paragraphs:
        if len(para) <= hard_max:
            raw_chunks.append(para)
            continue

        # Try splitting on list items (bullets or numbered)
        lines = para.split("\n")
        if len(lines) > 1 and any(
            _BULLET_RE.match(ln) or _NUMBERED_RE.match(ln) or _EMOJI_NUMBERED_RE.match(ln)
            for ln in lines
        ):
            # Group: non-list header + each list item
            current_group: list[str] = []
            for ln in lines:
                is_item = bool(
                    _BULLET_RE.match(ln) or _NUMBERED_RE.match(ln) or _EMOJI_NUMBERED_RE.match(ln)
                )
                if is_item and current_group:
                    raw_chunks.append("\n".join(current_group))
                    current_group = [ln]
                else:
                    current_group.append(ln)
            if current_group:
                raw_chunks.append("\n".join(current_group))
        else:
            # No list structure — split on sentences
            raw_chunks.extend(_split_sentences(para, hard_max))

    # Phase 3: split any remaining oversized chunks on sentences
    sized_chunks: list[str] = []
    for chunk in raw_chunks:
        if len(chunk) <= hard_max:
            sized_chunks.append(chunk)
        else:
            sized_chunks.extend(_split_sentences(chunk, hard_max))

    # Phase 4: merge tiny fragments with neighbours
    # min_size=10 — only merge truly trivial scraps (single emoji, 1-2 chars).
    # Kept low so short but meaningful empathy sentences (15-25 chars) stay
    # as their own bubble rather than getting swallowed into the next question.
    merged = _merge_tiny(sized_chunks, min_size=10, target=target)

    return [c for c in merged if c.strip()]


def _split_sentences(text: str, limit: int) -> list[str]:
    """Split text on sentence boundaries (CJK and Western)."""
    # Split on sentence-ending punctuation followed by space or end
    parts = re.split(r"(?<=[。！？!?])\s*", text)
    result: list[str] = []
    current = ""

    for part in parts:
        if not part.strip():
            continue
        if current and len(current) + len(part) + 1 > limit:
            result.append(current.strip())
            current = part
        else:
            current = (current + " " + part).strip() if current else part

    if current.strip():
        result.append(current.strip())

    # Last resort: if any chunk is still over limit, hard-cut
    final: list[str] = []
    for chunk in result:
        if len(chunk) <= limit:
            final.append(chunk)
        else:
            while chunk:
                final.append(chunk[:limit])
                chunk = chunk[limit:]

    return final


def _merge_tiny(
    chunks: list[str],
    min_size: int = 30,
    target: int = BUBBLE_TARGET,
) -> list[str]:
    """Merge very short chunks with the next chunk to avoid spam-bubbles."""
    if len(chunks) <= 1:
        return chunks

    merged: list[str] = []
    i = 0
    while i < len(chunks):
        current = chunks[i]
        # If tiny and there's a next chunk, merge forward
        if len(current) < min_size and i + 1 < len(chunks):
            combined = current + "\n\n" + chunks[i + 1]
            if len(combined) <= target:
                merged.append(combined)
                i += 2
                continue
        merged.append(current)
        i += 1

    return merged


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------

async def close() -> None:
    """Close the httpx client."""
    global _http
    if _http and not _http.is_closed:
        await _http.aclose()
        _http = None
