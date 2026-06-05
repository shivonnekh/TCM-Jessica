"""Outbound Meta Graph API client — send DMs (text + image) + reply to comments.

Mirrors ``src/whatsapp/client.py`` but for the Instagram / Facebook
Messenger Send API and the comment endpoints. One module serves both
platforms; the ``platform`` argument selects the right credentials.

Send primitives:

    send_dm(recipient_id, text, *, platform)
        Text DM to a user. Send API: ``POST /{sender_id}/messages`` with
        ``recipient: {id}``. Subject to Meta's 24h messaging window.

    send_dm_image(recipient_id, image_url, *, platform)
        Image DM (separate Send API call with an attachment payload).

    send_private_reply(comment_id, text, *, platform)
        Comment → DM. Single DM to the commenter, ``recipient: {comment_id}``.

    reply_to_comment(comment_id, text, *, platform)
        Public reply on the comment thread: ``POST /{comment_id}/replies``.

Credentials (per platform):
    instagram → IG_PAGE_ACCESS_TOKEN + IG_USER_ID
    facebook  → FB_PAGE_ACCESS_TOKEN + FB_PAGE_ID

    META_GRAPH_BASE     default ``https://graph.facebook.com``
    META_GRAPH_VERSION  default ``v25.0``
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Final

import httpx

from src.channels.meta_events import Platform

logger = logging.getLogger("channels.meta_client")

_DEFAULT_BASE: Final[str] = "https://graph.facebook.com"
_DEFAULT_VERSION: Final[str] = "v25.0"
_TIMEOUT_S: Final[float] = 15.0

# Per-platform env var names: (access-token var, sender-id var)
_CREDS_ENV: Final[dict[Platform, tuple[str, str]]] = {
    "instagram": ("IG_PAGE_ACCESS_TOKEN", "IG_USER_ID"),
    "facebook": ("FB_PAGE_ACCESS_TOKEN", "FB_PAGE_ID"),
}


@dataclass(frozen=True)
class SendResult:
    """Outcome of a single outbound call. ``ok`` is the only thing callers
    must branch on; ``detail`` is for logging / diagnostics."""

    ok: bool
    detail: str = ""


@dataclass(frozen=True)
class _Creds:
    token: str
    sender_id: str

    @property
    def complete(self) -> bool:
        return bool(self.token) and bool(self.sender_id)


def _creds(platform: Platform) -> _Creds:
    token_var, id_var = _CREDS_ENV[platform]
    return _Creds(
        token=os.environ.get(token_var, "").strip(),
        sender_id=os.environ.get(id_var, "").strip(),
    )


def _base() -> str:
    return os.environ.get("META_GRAPH_BASE", _DEFAULT_BASE).rstrip("/")


def _version() -> str:
    return os.environ.get("META_GRAPH_VERSION", _DEFAULT_VERSION).strip()


def _graph_url(path: str) -> str:
    return f"{_base()}/{_version()}/{path.lstrip('/')}"


# ---------------------------------------------------------------------------
# Public send primitives
# ---------------------------------------------------------------------------


async def send_dm(
    recipient_id: str, text: str, *, platform: Platform = "instagram"
) -> SendResult:
    """Send a text direct message to a user (recipient by id)."""
    if not text.strip():
        return SendResult(False, "empty text")
    return await _post_message(
        platform=platform,
        recipient={"id": recipient_id},
        message={"text": text},
        context=f"{platform}:dm→{recipient_id}",
    )


async def send_dm_image(
    recipient_id: str, image_url: str, *, platform: Platform = "instagram"
) -> SendResult:
    """Send an image direct message (Send API attachment payload)."""
    url = (image_url or "").strip()
    if not url.startswith(("http://", "https://")):
        return SendResult(False, "non-absolute url")
    return await _post_message(
        platform=platform,
        recipient={"id": recipient_id},
        message={
            "attachment": {
                "type": "image",
                "payload": {"url": url, "is_reusable": True},
            }
        },
        context=f"{platform}:dm_image→{recipient_id}",
    )


async def send_private_reply(
    comment_id: str, text: str, *, platform: Platform = "instagram"
) -> SendResult:
    """Comment → DM. Reply privately to the author of ``comment_id``."""
    if not text.strip():
        return SendResult(False, "empty text")
    return await _post_message(
        platform=platform,
        recipient={"comment_id": comment_id},
        message={"text": text},
        context=f"{platform}:private_reply→{comment_id}",
    )


async def reply_to_comment(
    comment_id: str, text: str, *, platform: Platform = "instagram"
) -> SendResult:
    """Public reply on the comment thread (visible to everyone)."""
    if not text.strip():
        return SendResult(False, "empty text")

    creds = _creds(platform)
    if not creds.token:
        logger.warning("[meta] %s token unset — cannot reply to comment", platform)
        return SendResult(False, "no token")

    url = _graph_url(comment_id + "/replies")
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_S) as client:
            resp = await client.post(
                url,
                params={"access_token": creds.token},
                json={"message": text},
            )
    except httpx.HTTPError as exc:
        logger.warning("[meta] comment reply transport error: %s", exc)
        return SendResult(False, f"transport: {exc}")

    return _interpret(resp, context=f"{platform}:comment_reply→{comment_id}")


# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------


async def _post_message(
    *, platform: Platform, recipient: dict, message: dict, context: str
) -> SendResult:
    """POST to the Send API: ``/{sender_id}/messages``."""
    creds = _creds(platform)
    if not creds.complete:
        logger.warning(
            "[meta] missing %s credentials — cannot send (%s)", platform, context
        )
        return SendResult(False, "missing credentials")

    url = _graph_url(f"{creds.sender_id}/messages")
    body = {
        "recipient": recipient,
        "message": message,
        "messaging_type": "RESPONSE",
    }
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_S) as client:
            resp = await client.post(
                url,
                params={"access_token": creds.token},
                json=body,
            )
    except httpx.HTTPError as exc:
        logger.warning("[meta] send transport error (%s): %s", context, exc)
        return SendResult(False, f"transport: {exc}")

    return _interpret(resp, context=context)


def _interpret(resp: httpx.Response, *, context: str) -> SendResult:
    """Map an HTTP response to a SendResult. Never logs the access token."""
    if resp.status_code == 200:
        logger.info("[meta] sent ok (%s)", context)
        return SendResult(True)

    # Graph API error bodies are JSON: {"error": {"message", "code", ...}}.
    # They do not echo the token, but keep the slice short regardless.
    detail = resp.text[:200]
    logger.warning("[meta] send failed HTTP %d (%s): %s", resp.status_code, context, detail)
    return SendResult(False, f"http {resp.status_code}")
