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

    list_recent_media(*, platform, account_id) / list_comments(media_id, *, platform, account_id)
        Read-only GET helpers used for one-off backfills (e.g. replaying
        comments that arrived before a keyword rule existed — see
        ``scripts/backfill_comments.py``). Not used by the live webhook path.

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

_DEFAULT_VERSION: Final[str] = "v25.0"
_TIMEOUT_S: Final[float] = 15.0

# Per-platform env var names: (access-token var, sender-id var)
_CREDS_ENV: Final[dict[Platform, tuple[str, str]]] = {
    "instagram": ("IG_PAGE_ACCESS_TOKEN", "IG_USER_ID"),
    "facebook": ("FB_PAGE_ACCESS_TOKEN", "FB_PAGE_ID"),
}

# Per-account overrides keyed by business IG/FB account id.
# When a webhook event's recipient_id matches one of these, the override
# token + sender_id is used instead of the global platform defaults.
# Add a new account by adding its id → (token_env_var, id_env_var) here.
_ACCOUNT_CREDS_ENV: Final[dict[str, tuple[str, str]]] = {
    "17841417304649448": ("IG_PAGE_ACCESS_TOKEN_JACKIE", "IG_USER_ID_JACKIE"),  # jackiechan.tcm
}

# Graph host is PER-PLATFORM and cannot be shared:
#   * Instagram API with Instagram Login (IGAA tokens) → graph.instagram.com
#   * Facebook Pages / Messenger                       → graph.facebook.com
# Each platform reads its override vars in order, else falls back to the
# correct default host. ``META_GRAPH_BASE`` is kept as a legacy alias for
# Instagram so existing deployments keep working.
_BASE_ENV: Final[dict[Platform, tuple[str, ...]]] = {
    "instagram": ("IG_GRAPH_BASE", "META_GRAPH_BASE"),
    "facebook": ("FB_GRAPH_BASE",),
}
_DEFAULT_BASE_BY_PLATFORM: Final[dict[Platform, str]] = {
    "instagram": "https://graph.instagram.com",
    "facebook": "https://graph.facebook.com",
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


def _creds(platform: Platform, account_id: str | None = None) -> _Creds:
    """Return credentials for the given platform, optionally scoped to a
    specific business account id (``recipient_id`` on inbound events).
    Falls back to the global platform token when no per-account override exists."""
    if account_id and account_id in _ACCOUNT_CREDS_ENV:
        token_var, id_var = _ACCOUNT_CREDS_ENV[account_id]
    else:
        token_var, id_var = _CREDS_ENV[platform]
    return _Creds(
        token=os.environ.get(token_var, "").strip(),
        sender_id=os.environ.get(id_var, "").strip(),
    )


def _base(platform: Platform) -> str:
    for var in _BASE_ENV[platform]:
        value = os.environ.get(var, "").strip()
        if value:
            return value.rstrip("/")
    return _DEFAULT_BASE_BY_PLATFORM[platform]


def _version() -> str:
    return os.environ.get("META_GRAPH_VERSION", _DEFAULT_VERSION).strip()


def _graph_url(platform: Platform, path: str) -> str:
    return f"{_base(platform)}/{_version()}/{path.lstrip('/')}"


# ---------------------------------------------------------------------------
# Public send primitives
# ---------------------------------------------------------------------------


async def send_dm(
    recipient_id: str, text: str, *, platform: Platform = "instagram",
    account_id: str | None = None,
) -> SendResult:
    """Send a text direct message to a user (recipient by id).
    Pass ``account_id`` (the business/page account that received the event)
    to use per-account credentials instead of the global platform token."""
    if not text.strip():
        return SendResult(False, "empty text")
    return await _post_message(
        platform=platform,
        account_id=account_id,
        recipient={"id": recipient_id},
        message={"text": text},
        context=f"{platform}:dm→{recipient_id}",
    )


async def send_dm_image(
    recipient_id: str, image_url: str, *, platform: Platform = "instagram",
    account_id: str | None = None,
) -> SendResult:
    """Send an image direct message (Send API attachment payload)."""
    url = (image_url or "").strip()
    if not url.startswith(("http://", "https://")):
        return SendResult(False, "non-absolute url")
    return await _post_message(
        platform=platform,
        account_id=account_id,
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
    comment_id: str, text: str, *, platform: Platform = "instagram",
    account_id: str | None = None,
) -> SendResult:
    """Comment → DM. Reply privately to the author of ``comment_id``."""
    if not text.strip():
        return SendResult(False, "empty text")
    return await _post_message(
        platform=platform,
        account_id=account_id,
        recipient={"comment_id": comment_id},
        message={"text": text},
        context=f"{platform}:private_reply→{comment_id}",
    )


async def reply_to_comment(
    comment_id: str, text: str, *, platform: Platform = "instagram",
    account_id: str | None = None,
) -> SendResult:
    """Public reply on the comment thread (visible to everyone)."""
    if not text.strip():
        return SendResult(False, "empty text")

    creds = _creds(platform, account_id)
    if not creds.token:
        logger.warning("[meta] %s token unset — cannot reply to comment", platform)
        return SendResult(False, "no token")

    url = _graph_url(platform, comment_id + "/replies")
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


async def list_recent_media(
    *, platform: Platform = "instagram", account_id: str | None = None, limit: int = 25,
) -> list[dict]:
    """GET /{business_id}/media — recent posts/reels for this account.

    Read-only diagnostic/backfill helper: lets us resolve a post's media id
    from its caption instead of asking Meta to "resend" history (webhooks
    never replay past events).
    """
    creds = _creds(platform, account_id)
    if not creds.complete:
        logger.warning("[meta] missing %s credentials — cannot list media", platform)
        return []
    url = _graph_url(platform, f"{creds.sender_id}/media")
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_S) as client:
            resp = await client.get(
                url,
                params={
                    "fields": "id,caption,permalink,timestamp",
                    "limit": str(limit),
                    "access_token": creds.token,
                },
            )
    except httpx.HTTPError as exc:
        logger.warning("[meta] list media transport error: %s", exc)
        return []
    if resp.status_code != 200:
        logger.warning("[meta] list media failed HTTP %d: %s", resp.status_code, resp.text[:200])
        return []
    return resp.json().get("data", [])


async def list_comments(
    media_id: str, *, platform: Platform = "instagram", account_id: str | None = None,
) -> list[dict]:
    """GET /{media_id}/comments — every top-level comment on a post/reel.

    Read-only backfill helper (see ``list_recent_media``). Paginates through
    all results. Does not fetch nested replies (``is_reply_to_comment``
    filtering happens on the ``parent_id`` field the webhook payload would
    have set, which this endpoint does not return — replies are excluded by
    only reading top-level comments here).
    """
    creds = _creds(platform, account_id)
    if not creds.complete:
        logger.warning("[meta] missing %s credentials — cannot list comments", platform)
        return []
    url = _graph_url(platform, f"{media_id}/comments")
    params = {
        "fields": "id,text,username,from,timestamp",
        "access_token": creds.token,
    }
    out: list[dict] = []
    async with httpx.AsyncClient(timeout=_TIMEOUT_S) as client:
        while url:
            try:
                resp = await client.get(url, params=params)
            except httpx.HTTPError as exc:
                logger.warning("[meta] list comments transport error: %s", exc)
                break
            if resp.status_code != 200:
                logger.warning(
                    "[meta] list comments failed HTTP %d: %s", resp.status_code, resp.text[:200]
                )
                break
            body = resp.json()
            out.extend(body.get("data", []))
            url = body.get("paging", {}).get("next")
            params = {}  # ``next`` already carries all query params
    return out


# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------


async def _post_message(
    *, platform: Platform, recipient: dict, message: dict, context: str,
    account_id: str | None = None,
) -> SendResult:
    """POST to the Send API: ``/{sender_id}/messages``."""
    creds = _creds(platform, account_id)
    if not creds.complete:
        logger.warning(
            "[meta] missing %s credentials — cannot send (%s)", platform, context
        )
        return SendResult(False, "missing credentials")

    url = _graph_url(platform, f"{creds.sender_id}/messages")
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
