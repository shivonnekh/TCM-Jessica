"""Shared Meta (Instagram + Facebook) webhook core.

Both the Instagram and Facebook routers are thin wrappers over this
module — they differ only in URL path, enable-flag, and which product
they were registered for. All the real work lives here:

    * ``verify_subscription``  — GET hub.challenge handshake
    * ``verify_signature``     — X-Hub-Signature-256 validation (fails
                                 closed in production)
    * ``is_duplicate``         — bounded LRU dedup over message/comment ids
    * ``process_post``         — verify → parse → dedup → background dispatch
    * ``handle_dm`` / ``handle_comment`` — pipeline dispatch + reply

DM replies interleave text bubbles with images exactly like the WhatsApp
sender: each ``media_to_send`` entry is grouped by ``after_bubble_idx``
and the image DM is sent right after that bubble.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import os
from collections import OrderedDict
from typing import Final

from src.channels import comment_rules, meta_client
from src.channels.meta_events import (
    IncomingComment,
    IncomingDM,
    Platform,
    parse_meta_webhook,
)
from src.orchestrator.pipeline import JessicaPipeline

logger = logging.getLogger("channels.meta_webhook")

APP_ENV: Final[str] = os.environ.get("APP_ENV", "development").lower()
_BUBBLE_PAUSE_S: Final[float] = 0.6
_MEDIA_PAUSE_S: Final[float] = 0.8
_DEDUP_MAX: Final[int] = 2048


# ---------------------------------------------------------------------------
# Config accessors (read at call time so tests can monkeypatch env)
# ---------------------------------------------------------------------------


def _app_secret() -> str:
    return os.environ.get("META_APP_SECRET", "").strip()


def _verify_token() -> str:
    return os.environ.get("META_VERIFY_TOKEN", "").strip()


# ---------------------------------------------------------------------------
# GET handshake
# ---------------------------------------------------------------------------


def verify_subscription(mode: str, token: str, challenge: str) -> str | None:
    """Return ``challenge`` when the verify token matches, else ``None``."""
    expected = _verify_token()
    if mode == "subscribe" and expected and hmac.compare_digest(token, expected):
        logger.info("[meta] webhook verified")
        return challenge
    logger.warning("[meta] webhook verification failed (mode=%s)", mode)
    return None


# ---------------------------------------------------------------------------
# Signature verification
# ---------------------------------------------------------------------------


def verify_signature(raw: bytes, header: str) -> bool:
    """Validate ``X-Hub-Signature-256: sha256=<hex>`` against the app secret.

    Production requires the secret (fails closed). Dev with no secret
    skips verification so curl smoke tests work.
    """
    secret = _app_secret()
    if not secret:
        if APP_ENV == "production":
            logger.error("[meta] META_APP_SECRET unset in production — rejecting")
            return False
        return True
    if not header.startswith("sha256="):
        return False
    sent = header.split("=", 1)[1].strip()
    expected = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    return hmac.compare_digest(sent, expected)


# ---------------------------------------------------------------------------
# Dedup
# ---------------------------------------------------------------------------

_seen_ids: "OrderedDict[str, None]" = OrderedDict()


def is_duplicate(event_id: str) -> bool:
    if not event_id:
        return False
    if event_id in _seen_ids:
        return True
    _seen_ids[event_id] = None
    if len(_seen_ids) > _DEDUP_MAX:
        _seen_ids.popitem(last=False)
    return False


# ---------------------------------------------------------------------------
# POST processing
# ---------------------------------------------------------------------------


async def process_post(
    *,
    raw: bytes,
    signature_header: str,
    pipeline: JessicaPipeline | None,
    enabled: bool,
) -> tuple[dict, int]:
    """Verify + parse + dispatch. Returns ``(json_body, status_code)``.

    The router just wraps the return value in a ``JSONResponse``. We always
    prefer a 200 once the payload is authentic so Meta doesn't disable the
    subscription on transient downstream issues.
    """
    if not enabled:
        return {"status": "disabled"}, 200

    if not verify_signature(raw, signature_header):
        return {"error": "bad signature"}, 401

    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {"error": "invalid json"}, 400

    events = parse_meta_webhook(payload)
    if not events:
        return {"status": "ignored"}, 200

    if pipeline is None:
        logger.error("[meta] pipeline not initialised — dropping %d event(s)", len(events))
        return {"status": "no_pipeline"}, 503

    queued = 0
    for event in events:
        if isinstance(event, IncomingDM):
            if event.is_echo or is_duplicate(event.message_id) or not event.text.strip():
                continue
            _spawn(handle_dm(event, pipeline))
            queued += 1
        elif isinstance(event, IncomingComment):
            if is_duplicate(event.comment_id):
                continue
            _spawn(handle_comment(event, pipeline))
            queued += 1

    return {"status": "queued", "count": queued}, 200


# ---------------------------------------------------------------------------
# Dispatch handlers
# ---------------------------------------------------------------------------


async def handle_dm(dm: IncomingDM, pipeline: JessicaPipeline) -> None:
    """Run a DM through the pipeline; reply with interleaved text + images."""
    try:
        result = await pipeline.run_turn(
            phone=dm.crm_key,
            user_message=dm.text,
            wa_message_id=dm.message_id,
        )
    except Exception:  # noqa: BLE001
        logger.exception("[meta] pipeline failed for %s", dm.crm_key)
        return

    bubbles = [b for b in (result.writer_output.bubbles or []) if b.strip()]
    media_by_idx = _group_media(result.writer_output.media_to_send or [])

    for i, bubble in enumerate(bubbles):
        send = await meta_client.send_dm(dm.sender_id, bubble, platform=dm.platform)
        if not send.ok:
            logger.warning("[meta] DM bubble send failed: %s", send.detail)
            break
        for url in media_by_idx.get(i, []):
            await asyncio.sleep(_MEDIA_PAUSE_S)
            img = await meta_client.send_dm_image(dm.sender_id, url, platform=dm.platform)
            if not img.ok:
                logger.warning("[meta] DM image send failed: %s", img.detail)
        if i < len(bubbles) - 1:
            await asyncio.sleep(_BUBBLE_PAUSE_S)


async def handle_comment(comment: IncomingComment, pipeline: JessicaPipeline) -> None:
    """Comment → DM, driven by ``comment_rules`` (canned-first).

    A keyword match resolves to a rule. By default the rule sends a FIXED
    DM (text + optional image) — no agent, because for a CTA we already
    know what the lead wants. Only ``use_agent: true`` rules run the
    pipeline. No matching rule ⇒ we stay silent (don't auto-DM strangers).
    """
    rule = comment_rules.match(comment.text)
    if rule is None:
        logger.info("[meta] comment %s: no rule match — skipping", comment.comment_id)
        return

    # Optional public acknowledgement on the thread (per-rule).
    if rule.public_ack:
        await meta_client.reply_to_comment(
            comment.comment_id, rule.public_ack, platform=comment.platform
        )

    if rule.use_agent:
        await _comment_via_agent(comment, pipeline)
    else:
        await _comment_via_canned(comment, rule)


async def _comment_via_canned(comment: IncomingComment, rule) -> None:
    """Send the predefined DM for this keyword — no LLM call."""
    if not rule.dm_text:
        logger.warning("[meta] rule %r has no dm_text — nothing to send", rule.keyword)
        return
    send = await meta_client.send_private_reply(
        comment.comment_id, rule.dm_text, platform=comment.platform
    )
    if not send.ok:
        logger.warning("[meta] canned private reply failed: %s", send.detail)
        return
    # Image, if any, follows the text as a normal DM (recipient by id).
    if rule.image_url and comment.from_id:
        await asyncio.sleep(_MEDIA_PAUSE_S)
        await meta_client.send_dm_image(
            comment.from_id, rule.image_url, platform=comment.platform
        )


async def _comment_via_agent(comment: IncomingComment, pipeline: JessicaPipeline) -> None:
    """Run the pipeline on the comment text; send the joined reply as one DM."""
    try:
        result = await pipeline.run_turn(
            phone=comment.crm_key,
            user_message=comment.text,
            wa_message_id=comment.comment_id,
        )
    except Exception:  # noqa: BLE001
        logger.exception("[meta] pipeline failed for comment %s", comment.comment_id)
        return

    bubbles = [b for b in (result.writer_output.bubbles or []) if b.strip()]
    if not bubbles:
        return

    joined = "\n\n".join(bubbles)
    send = await meta_client.send_private_reply(
        comment.comment_id, joined, platform=comment.platform
    )
    if not send.ok:
        logger.warning("[meta] agent private reply failed: %s", send.detail)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _group_media(media_to_send: list[dict]) -> dict[int, list[str]]:
    """Group absolute image URLs by the bubble index they follow."""
    by_idx: dict[int, list[str]] = {}
    for m in media_to_send:
        url = (m.get("url") or "").strip()
        if not url.startswith(("http://", "https://")):
            continue
        try:
            idx = int(m.get("after_bubble_idx") or 0)
        except (TypeError, ValueError):
            idx = 0
        by_idx.setdefault(idx, []).append(url)
    return by_idx


# Background task helper — keep refs so tasks aren't GC'd mid-flight.
_bg_tasks: set[asyncio.Task] = set()


def _spawn(coro) -> None:
    task = asyncio.create_task(coro)
    _bg_tasks.add(task)
    task.add_done_callback(_bg_tasks.discard)
