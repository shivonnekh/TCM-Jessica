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
    """Instagram-side secret. Instagram API with Instagram Login signs IG
    webhooks with the *Instagram app secret*, stored in ``META_APP_SECRET``."""
    return os.environ.get("META_APP_SECRET", "").strip()


def _fb_app_secret() -> str:
    """Facebook/Messenger secret. Facebook Pages sign webhooks with the
    *Meta app secret* (distinct from the Instagram app secret). Falls back to
    ``META_APP_SECRET`` only if ``FB_APP_SECRET`` is unset (single-app setups)."""
    return os.environ.get("FB_APP_SECRET", "").strip() or _app_secret()


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


def verify_signature(raw: bytes, header: str, *, secret: str | None = None) -> bool:
    """Validate ``X-Hub-Signature-256: sha256=<hex>`` against the app secret.

    ``secret`` lets the caller pick the platform-specific secret (Instagram vs
    Meta app secret). When omitted it defaults to the Instagram secret.
    Production requires a secret (fails closed). Dev with no secret skips
    verification so curl smoke tests work.
    """
    secret = secret if secret is not None else _app_secret()
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

# Per-account agent registry — keyed by business IG/FB account id.
# When a DM/comment arrives on a known account, its agent handles the reply.
# Falls back to _chloe_agent (default) when no per-account entry exists.
_account_agents: dict[str, object] = {}
_chloe_agent = None  # type: ignore[var-annotated]  # default agent


def set_chloe_agent(agent) -> None:
    """Register the default Chloe agent for IG/FB DMs. Called from web.lifespan."""
    global _chloe_agent
    _chloe_agent = agent


def set_account_agent(account_id: str, agent) -> None:
    """Register a per-account agent (e.g. Jackie for jackiechan.tcm)."""
    _account_agents[account_id] = agent


def _get_agent(account_id: str | None):
    """Return the agent for this account, falling back to the default."""
    if account_id and account_id in _account_agents:
        return _account_agents[account_id]
    return _chloe_agent


# Merge buffer — debounces rapid-fire DM fragments into one turn (lazy init).
_merge_buffer = None  # type: ignore[var-annotated]


def _get_merge_buffer(pipeline: JessicaPipeline):
    """Lazily build the per-process merge buffer bound to the dispatcher."""
    global _merge_buffer
    if _merge_buffer is None:
        from src.channels.merge_buffer import MergeBuffer

        async def _on_flush(dm: IncomingDM) -> None:
            await _dispatch_dm(dm, pipeline)

        _merge_buffer = MergeBuffer(
            window_s=float(os.environ.get("CHLOE_MERGE_WINDOW_S", "5.0")),
            max_s=float(os.environ.get("CHLOE_MERGE_MAX_S", "20.0")),
            on_flush=_on_flush,
        )
    return _merge_buffer


def reset_merge_buffer() -> None:
    """Test hook — drop the buffer so a fresh window/on_flush is built."""
    global _merge_buffer
    _merge_buffer = None


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
    app_secret: str | None = None,
) -> tuple[dict, int]:
    """Verify + parse + dispatch. Returns ``(json_body, status_code)``.

    ``app_secret`` selects the platform secret for signature verification
    (Facebook passes the Meta app secret; Instagram leaves it ``None`` to use
    the Instagram secret). The router just wraps the return value in a
    ``JSONResponse``. We always prefer a 200 once the payload is authentic so
    Meta doesn't disable the subscription on transient downstream issues.
    """
    if not enabled:
        return {"status": "disabled"}, 200

    if not verify_signature(raw, signature_header, secret=app_secret):
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
    """Entry point for an inbound DM — pushes it into the merge buffer.

    Rapid-fire fragments from one user are debounced and combined into a
    single turn (see ``merge_buffer``). When buffering is off the fragment
    dispatches immediately. The actual reply logic is ``_dispatch_dm``.
    """
    await _get_merge_buffer(pipeline).submit(dm)


async def _dispatch_dm(dm: IncomingDM, pipeline: JessicaPipeline) -> None:
    """Reply to a (possibly merged) DM. Routes to Chloe when registered;
    otherwise falls back to the Jessica pipeline. Text + images interleave."""
    # Keyword guide short-circuit — "gut" etc. in a DM sends the canned
    # guide (images) directly, skipping the LLM. Same rules as comments.
    rule = comment_rules.match(dm.text)
    if rule is not None and not rule.use_agent:
        await _send_canned_to_user(dm.sender_id, rule, platform=dm.platform)
        return

    _agent = _get_agent(dm.recipient_id)
    if _agent is not None:
        try:
            reply = await _agent.respond(
                crm_key=dm.crm_key, user_message=dm.text, message_id=dm.message_id
            )
            bubbles = [b for b in reply.bubbles if b.strip()]
            media_by_idx = _group_media(reply.media)
        except Exception:  # noqa: BLE001
            logger.exception("[meta] agent failed for %s", dm.crm_key)
            return
    else:
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
        send = await meta_client.send_dm(
            dm.sender_id, bubble, platform=dm.platform, account_id=dm.recipient_id
        )
        if not send.ok:
            logger.warning("[meta] DM bubble send failed: %s", send.detail)
            break
        for url in media_by_idx.get(i, []):
            await asyncio.sleep(_MEDIA_PAUSE_S)
            img = await meta_client.send_dm_image(
                dm.sender_id, url, platform=dm.platform, account_id=dm.recipient_id
            )
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
        # Catch-all: if this account has a registered agent (e.g. Jackie),
        # post a public ack on the thread and open a DM conversation.
        _agent = _get_agent(comment.recipient_id or None)
        if _agent is not None and hasattr(_agent, "comment_ack"):
            ack = _agent.comment_ack
            if ack:
                await meta_client.reply_to_comment(
                    comment.comment_id, ack, platform=comment.platform,
                    account_id=comment.recipient_id or None,
                )
            await _comment_via_account_agent(comment)
        else:
            logger.info("[meta] comment %s: no rule match — skipping", comment.comment_id)
        return

    # Optional public acknowledgement on the thread (per-rule).
    if rule.public_ack:
        await meta_client.reply_to_comment(
            comment.comment_id, rule.public_ack, platform=comment.platform,
            account_id=comment.recipient_id or None,
        )

    if rule.use_agent:
        await _comment_via_agent(comment, pipeline)
    else:
        await _comment_via_canned(comment, rule)


async def _comment_via_canned(comment: IncomingComment, rule) -> None:
    """Send the predefined DM for this keyword — no LLM call.

    The first message is a private reply (comment→DM). Any images then
    follow as normal DMs to the commenter (recipient by id).
    """
    if rule.dm_text:
        send = await meta_client.send_private_reply(
            comment.comment_id, rule.dm_text, platform=comment.platform,
            account_id=comment.recipient_id or None,
        )
        if not send.ok:
            logger.warning("[meta] canned private reply failed: %s", send.detail)
            return
    if comment.from_id:
        for url in rule.all_images:
            await asyncio.sleep(_MEDIA_PAUSE_S)
            img = await meta_client.send_dm_image(
                comment.from_id, url, platform=comment.platform,
                account_id=comment.recipient_id or None,
            )
            if not img.ok:
                logger.warning("[meta] canned image failed: %s", img.detail)


async def _send_canned_to_user(recipient_id: str, rule, *, platform) -> None:
    """Send a canned keyword reply (text + images) straight to a DM user."""
    if rule.dm_text:
        await meta_client.send_dm(recipient_id, rule.dm_text, platform=platform)
    for url in rule.all_images:
        await asyncio.sleep(_MEDIA_PAUSE_S)
        img = await meta_client.send_dm_image(recipient_id, url, platform=platform)
        if not img.ok:
            logger.warning("[meta] canned DM image failed: %s", img.detail)


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
        comment.comment_id, joined, platform=comment.platform,
        account_id=comment.recipient_id or None,
    )
    if not send.ok:
        logger.warning("[meta] agent private reply failed: %s", send.detail)


async def _comment_via_account_agent(comment: IncomingComment) -> None:
    """Catch-all DM for accounts with a registered ChloeAgent (e.g. Jackie).

    Uses the commenter's IG id as the CRM key so each unique commenter gets
    their own conversation thread. Sends greeting + first response as a
    private reply (comment→DM) linked to the original comment.
    """
    _agent = _get_agent(comment.recipient_id or None)
    if _agent is None:
        return
    try:
        reply = await _agent.respond(
            crm_key=comment.crm_key,
            user_message=comment.text,
            message_id=comment.comment_id,
        )
        bubbles = [b for b in reply.bubbles if b.strip()]
    except Exception:  # noqa: BLE001
        logger.exception("[meta] account agent failed for comment %s", comment.comment_id)
        return

    if not bubbles:
        return

    # Send greeting + reply as a private reply (appears as DM linked to comment).
    for i, bubble in enumerate(bubbles):
        if i == 0:
            send = await meta_client.send_private_reply(
                comment.comment_id, bubble, platform=comment.platform,
                account_id=comment.recipient_id or None,
            )
        else:
            # Subsequent bubbles go as regular DMs to the commenter.
            if not comment.from_id:
                break
            send = await meta_client.send_dm(
                comment.from_id, bubble, platform=comment.platform,
                account_id=comment.recipient_id or None,
            )
        if not send.ok:
            logger.warning("[meta] account agent DM bubble %d failed: %s", i, send.detail)
            break
        if i < len(bubbles) - 1:
            await asyncio.sleep(_BUBBLE_PAUSE_S)


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
