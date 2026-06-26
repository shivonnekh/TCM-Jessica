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
from datetime import datetime
from collections import OrderedDict
from typing import Final

from src.channels import comment_rules, meta_client
from src.channels.meta_events import (
    IncomingComment,
    IncomingDM,
    Platform,
    parse_meta_webhook,
)
from src.crm.models import ConversationMessage
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


def _is_own_comment(comment: IncomingComment) -> bool:
    own_ids = {
        os.environ.get("IG_USER_ID", "").strip(),
        os.environ.get("IG_USER_ID_JACKIE", "").strip(),
        os.environ.get("FB_PAGE_ID", "").strip(),
        comment.recipient_id or "",
    }
    own_ids.discard("")
    return bool(comment.from_id and comment.from_id in own_ids)


def _comment_intent_key(comment: IncomingComment) -> str:
    text = " ".join((comment.text or "").casefold().split())[:160]
    return ":".join([
        comment.platform,
        comment.recipient_id or "unknown_account",
        comment.media_id or "unknown_media",
        comment.from_id or "unknown_user",
        text or "empty",
    ])


async def _claim_webhook_event(event_id: str, kind: str, pipeline: JessicaPipeline) -> bool:
    """Persistently claim a Meta event before causing outbound side effects.

    The in-memory LRU only protects one process. Meta may retry webhooks after
    a restart or while a deploy is rolling, so comments also need a DB-backed
    idempotency key before we public-reply or DM. Tests/fakes without a CRM
    keep the old in-memory-only behavior.
    """
    crm = getattr(pipeline, "_crm", None)
    claim = getattr(crm, "try_claim_webhook_event", None)
    if claim is None:
        return True
    key = f"meta:{kind}:{event_id}"
    try:
        return bool(await claim(key, kind))
    except Exception:  # noqa: BLE001
        logger.exception("[meta] webhook idempotency claim failed for %s", key)
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
            if event.is_reply_to_comment or _is_own_comment(event):
                continue
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


async def _should_send_canned_for_dm(dm: IncomingDM, pipeline: JessicaPipeline) -> bool:
    """Only use keyword canned guides to open a DM conversation.

    Once the user has CRM history, the social agent should continue naturally
    instead of looping back into the same protocol prompt whenever a keyword is
    mentioned again.
    """
    crm = getattr(pipeline, "_crm", None)
    if crm is None:
        return True
    try:
        user = await crm.get_user(dm.crm_key)
    except Exception:  # noqa: BLE001
        logger.exception("[meta] failed to check CRM history for %s", dm.crm_key)
        return False
    if user is None:
        return True
    history = list(getattr(user, "conversation_history", []) or [])
    state = dict(getattr(user, "temp_state", {}) or {})
    return not history and not state.get("meta_pending_guide_images")


async def _dispatch_dm(dm: IncomingDM, pipeline: JessicaPipeline) -> None:
    """Reply to a (possibly merged) DM. Routes to Chloe when registered;
    otherwise falls back to the Jessica pipeline. Text + images interleave."""
    if await _send_pending_guide_images(dm, pipeline):
        return

    # Keyword guide short-circuit — "gut" etc. in a DM sends the canned
    # guide (images) directly, skipping the LLM. Same rules as comments.
    rule = comment_rules.match(dm.text)
    if rule is not None and not rule.use_agent and await _should_send_canned_for_dm(dm, pipeline):
        await _persist_canned_interaction(
            pipeline,
            crm_key=dm.crm_key,
            inbound_text=dm.text,
            inbound_message_id=dm.message_id,
            outbound_text=rule.dm_text,
            image_urls=rule.all_images,
        )
        await _send_canned_to_user(
            dm.sender_id, rule, platform=dm.platform, account_id=dm.recipient_id
        )
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
    if comment.is_reply_to_comment or _is_own_comment(comment):
        logger.info("[meta] ignoring own/reply comment %s", comment.comment_id)
        return
    if not await _claim_webhook_event(comment.comment_id, "comment", pipeline):
        logger.info("[meta] duplicate comment %s — already handled", comment.comment_id)
        return
    intent_key = _comment_intent_key(comment)
    if not await _claim_webhook_event(intent_key, "comment_intent", pipeline):
        logger.info("[meta] duplicate comment intent %s — already handled", intent_key)
        return

    rule = comment_rules.match(comment.text)
    if rule is None:
        logger.info("[meta] comment %s: no rule match — skipping", comment.comment_id)
        return

    if rule.use_agent:
        sent = await _comment_via_agent(comment, pipeline)
    else:
        sent = await _comment_via_canned(comment, rule, pipeline)

    # Optional public acknowledgement on the thread (per-rule). Send it after
    # the private path succeeds so failures do not create public-only spam.
    if sent and rule.public_ack:
        await meta_client.reply_to_comment(
            comment.comment_id, rule.public_ack, platform=comment.platform,
            account_id=comment.recipient_id or None,
        )


async def _comment_via_canned(
    comment: IncomingComment, rule, pipeline: JessicaPipeline | None = None
) -> bool:
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
            return False
    if pipeline is not None:
        await _persist_canned_interaction(
            pipeline,
            crm_key=comment.crm_key,
            inbound_text=comment.text,
            inbound_message_id=comment.comment_id,
            outbound_text=rule.dm_text,
            image_urls=rule.all_images,
            pending_images=True,
        )
    return True


async def _send_canned_to_user(
    recipient_id: str, rule, *, platform, account_id: str | None = None
) -> None:
    """Send a canned keyword reply (text + images) straight to a DM user."""
    if rule.dm_text:
        await meta_client.send_dm(
            recipient_id, rule.dm_text, platform=platform, account_id=account_id
        )
    for url in rule.all_images:
        await asyncio.sleep(_MEDIA_PAUSE_S)
        img = await meta_client.send_dm_image(
            recipient_id, url, platform=platform, account_id=account_id
        )
        if not img.ok:
            logger.warning("[meta] canned DM image failed: %s", img.detail)


async def _comment_via_agent(comment: IncomingComment, pipeline: JessicaPipeline) -> bool:
    """Run the pipeline on the comment text; send the joined reply as one DM."""
    try:
        result = await pipeline.run_turn(
            phone=comment.crm_key,
            user_message=comment.text,
            wa_message_id=comment.comment_id,
        )
    except Exception:  # noqa: BLE001
        logger.exception("[meta] pipeline failed for comment %s", comment.comment_id)
        return False

    bubbles = [b for b in (result.writer_output.bubbles or []) if b.strip()]
    if not bubbles:
        return False

    joined = "\n\n".join(bubbles)
    send = await meta_client.send_private_reply(
        comment.comment_id, joined, platform=comment.platform,
        account_id=comment.recipient_id or None,
    )
    if not send.ok:
        logger.warning("[meta] agent private reply failed: %s", send.detail)
        return False
    return True


async def _comment_via_account_agent(comment: IncomingComment) -> bool:
    """Catch-all DM for accounts with a registered ChloeAgent (e.g. Jackie).

    Uses the commenter's IG id as the CRM key so each unique commenter gets
    their own conversation thread. Sends greeting + first response as a
    private reply (comment→DM) linked to the original comment.
    """
    _agent = _get_agent(comment.recipient_id or None)
    if _agent is None:
        return False
    try:
        reply = await _agent.respond(
            crm_key=comment.crm_key,
            user_message=comment.text,
            message_id=comment.comment_id,
        )
        bubbles = [b for b in reply.bubbles if b.strip()]
    except Exception:  # noqa: BLE001
        logger.exception("[meta] account agent failed for comment %s", comment.comment_id)
        return False

    if not bubbles:
        return False

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
            return False
        if i < len(bubbles) - 1:
            await asyncio.sleep(_BUBBLE_PAUSE_S)
    return True


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _send_pending_guide_images(dm: IncomingDM, pipeline: JessicaPipeline) -> bool:
    """Send queued guide images, then let the agent continue the conversation.

    Instagram may allow the first comment→DM text but reject immediate follow-up
    media while the thread is still in a message-request state. Once the user
    replies in DM, they have opened the conversation, so we send queued protocol
    images first, clear the pending state, and then still allow the LLM to reply
    naturally on the same turn.
    """
    crm = getattr(pipeline, "_crm", None)
    if crm is None:
        return False
    try:
        user = await crm.get_user(dm.crm_key)
    except Exception:  # noqa: BLE001
        logger.exception("[meta] failed to load pending guide state for %s", dm.crm_key)
        return False
    state = dict(getattr(user, "temp_state", {}) or {}) if user is not None else {}
    urls = [u for u in state.get("meta_pending_guide_images", []) if isinstance(u, str)]
    if not urls:
        return False

    await _persist_canned_interaction(
        pipeline,
        crm_key=dm.crm_key,
        inbound_text=dm.text,
        inbound_message_id=dm.message_id,
        outbound_text="[sent pending guide images]",
        image_urls=urls,
    )
    for url in urls:
        await asyncio.sleep(_MEDIA_PAUSE_S)
        img = await meta_client.send_dm_image(
            dm.sender_id, url, platform=dm.platform, account_id=dm.recipient_id
        )
        if not img.ok:
            logger.warning("[meta] pending guide image failed url=%s: %s", url, img.detail)

    if user is not None:
        state.pop("meta_pending_guide_images", None)
        state.pop("meta_pending_guide_text", None)
        try:
            await crm.save_user(user.with_updates(temp_state=state))
        except Exception:  # noqa: BLE001
            logger.exception("[meta] failed to clear pending guide state for %s", dm.crm_key)
    return False


async def _persist_canned_interaction(
    pipeline: JessicaPipeline,
    *,
    crm_key: str,
    inbound_text: str,
    inbound_message_id: str | None,
    outbound_text: str,
    image_urls: list[str],
    pending_images: bool = False,
) -> None:
    """Store canned guide exchanges so later agent replies have context."""
    crm = getattr(pipeline, "_crm", None)
    if crm is None:
        return
    try:
        user = await crm.get_or_create_user(crm_key)
        if pending_images and image_urls:
            state = dict(getattr(user, "temp_state", {}) or {})
            state["meta_pending_guide_images"] = list(image_urls)
            state["meta_pending_guide_text"] = outbound_text
            await crm.save_user(user.with_updates(temp_state=state))
        now = datetime.utcnow()
        await crm.append_message(
            crm_key,
            ConversationMessage(
                role="user",
                content=inbound_text,
                at=now,
                wa_message_id=inbound_message_id,
            ),
        )
        if outbound_text or image_urls:
            await crm.append_message(
                crm_key,
                ConversationMessage(
                    role="chloe",
                    content=outbound_text or "[sent guide images]",
                    media_urls=list(image_urls),
                    at=now,
                ),
            )
    except Exception:  # noqa: BLE001
        logger.exception("[meta] failed to persist canned interaction for %s", crm_key)


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
