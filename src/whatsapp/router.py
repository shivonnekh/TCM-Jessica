"""WhatsApp webhook router for Jessica via ChatDaddy.

Receives incoming messages, buffers rapid-fire fragments, dispatches a
merged turn through ``JessicaPipeline.run_turn``, then sends the bubble
list back via ChatDaddy.

Adapted from ``dr-baba-agent/src/whatsapp/router.py`` (3,676 lines →
~450 lines). The Dr. Baba version handled 50-disease tenant routing,
disease-menu deep-linking, sales-flow state machines, opt-out keywords,
proactive scheduling, and CRM mirroring — none of which Jessica needs.

What was preserved:
  * Buffer / merge logic (single-owner flusher per phone). Bursts of
    rapid-fire messages collapse into one pipeline call.
  * Dedup (shared ``_seen_ids`` set with the poller).
  * Echo suppression (``fromMe == True``).
  * Diagnostic capture of every raw webhook.
  * Group gate (drops all group messages — Jessica is 1-on-1 only).
  * Blocklist (per-phone opt-out, file-backed).
  * Bubble-aware send via ChatDaddy client (typing pauses between bubbles).

What was removed:
  * Per-phone disease routing / interactive disease menu.
  * RESTART keyword + multi-CRM wipe.
  * Proactive opt-in/opt-out keyword detection.
  * Sales-flow state-machine short-circuit.
  * LLM-based completeness check (replaced with a short-fragment
    heuristic — same effect, no extra LLM call).
"""

from __future__ import annotations

import asyncio
import hmac
import logging
import os
import sys
import time
from collections import OrderedDict
from dataclasses import dataclass, field as dc_field
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from src import llm_transcribe
from src.agents.acute_pain import detect_all_health_complaints
from src.crm.models import ConversationMessage
from src.orchestrator.pipeline import JessicaPipeline, PipelineResult
from src.whatsapp import (
    blocklist,
    client,
    diagnostic_capture,
    group_gate,
)
from src.whatsapp import media as whatsapp_media
from src.whatsapp.models import ChatDaddyMessage, parse_webhook

# Force stdout line-buffering — on Render (no TTY) Python defaults to
# full buffering which makes print() debug output invisible.
if not sys.stdout.line_buffering:
    sys.stdout.reconfigure(line_buffering=True)

logger = logging.getLogger("whatsapp.router")

router = APIRouter(tags=["whatsapp"])


# ---------------------------------------------------------------------------
# Config (env-tunable)
# ---------------------------------------------------------------------------

WEBHOOK_SECRET = os.environ.get("CHATDADDY_WEBHOOK_SECRET", "")
DEFAULT_ACCOUNT_ID = os.environ.get("CHATDADDY_ACCOUNT_ID", "")

# Group-chat identity — needed so Jessica knows when she's been @-mentioned.
#   JESSICA_BOT_JID   — the bot's own JID digits (e.g. "85212345678").
#                       Derive from the ChatDaddy number; leave blank in local
#                       dev if you don't have it — name-based detection still works.
#   JESSICA_BOT_NAMES — comma-separated display names (default: "Jessica,jessica").
BOT_JID: str = os.environ.get("JESSICA_BOT_JID", "").strip()
_raw_bot_names = os.environ.get("JESSICA_BOT_NAMES", "Jessica,jessica")
BOT_NAMES: list[str] = [n.strip() for n in _raw_bot_names.split(",") if n.strip()]

# Production guard — when APP_ENV=production, the webhook MUST have a secret
# configured. We refuse to start without one. In dev / test, an empty secret
# is permitted (smoke tests + unit tests rely on this).
APP_ENV = os.environ.get("APP_ENV", "development").lower()
if APP_ENV == "production" and not WEBHOOK_SECRET:
    raise RuntimeError(
        "CHATDADDY_WEBHOOK_SECRET is required when APP_ENV=production. "
        "Unauthenticated webhooks allow anyone to inject messages."
    )

# Merge windows — tuned for HK Chinese WhatsApp users (IME delay + burst
# typing). Override via env vars if needed.
WA_MERGE_COMPLETE = float(os.environ.get("WA_MERGE_COMPLETE", "5.0"))
WA_MERGE_INCOMPLETE = float(os.environ.get("WA_MERGE_INCOMPLETE", "8.0"))
WA_MERGE_FORCE = float(os.environ.get("WA_MERGE_FORCE", "15.0"))

# Burst-mode heuristic: if accumulated fragments are all short, the user
# is clearly mid-burst, so use the longer window regardless of how the
# first fragment looks.
WA_BURST_AVG_CHARS = int(os.environ.get("WA_BURST_AVG_CHARS", "10"))
WA_BURST_MAX_FRAGMENTS = int(os.environ.get("WA_BURST_MAX_FRAGMENTS", "3"))

WA_USE_MERGE_BUFFER = os.environ.get("WA_USE_MERGE_BUFFER", "true").lower() == "true"


# ---------------------------------------------------------------------------
# Dedup: LRU of recent message IDs
# ---------------------------------------------------------------------------

_DEDUP_MAX = 2000
_seen_ids: OrderedDict[str, float] = OrderedDict()


def _is_duplicate(message_id: str) -> bool:
    """Pure check: True iff we've recorded this message ID. Does NOT insert."""
    if not message_id:
        return False
    return message_id in _seen_ids


def _record_seen_message_id(message_id: str) -> None:
    """Mark a message id as processed. Bounded by ``_DEDUP_MAX`` (FIFO evict)."""
    if not message_id:
        return
    _seen_ids[message_id] = time.time()
    while len(_seen_ids) > _DEDUP_MAX:
        _seen_ids.popitem(last=False)


# ---------------------------------------------------------------------------
# Merge buffer — collect rapid-fire messages before one pipeline call
# ---------------------------------------------------------------------------
#
# Design: ONE owner coroutine per phone buffer.
#
# Prior Dr. Baba designs used two timer tasks (window + force deadline) that
# raced each other, got cancelled and replaced on every inbound, and left
# orphaned asyncio tasks under FastAPI BackgroundTasks. That pattern lost
# messages in production. This design:
#   1. ``_enqueue_for_merge`` appends to the buffer (pure mutation, no tasks)
#   2. First inbound on an empty buffer spawns ONE flusher coroutine
#   3. The flusher owns the buffer lifetime: sleeps → checks activity → loops
#      or flushes. No cross-task cancellation, no timer replacement.
#   4. Hard deadline enforced by capping sleep time inside the flusher.
#   5. On crash, flusher pops the buffer so the next inbound starts fresh.


@dataclass
class _PendingBuffer:
    """Buffered messages waiting to be merged and processed."""

    texts: list[str] = dc_field(default_factory=list)
    attachments: list[dict] = dc_field(default_factory=list)
    fragment_ids: list[str] = dc_field(default_factory=list)
    chat_id: str = ""
    account_id: str = ""
    sender_name: str = ""
    first_arrival: float = 0.0  # monotonic — enforces hard deadline
    last_activity: float = 0.0  # monotonic — updated on each enqueue
    flusher_running: bool = False
    message_id: str = ""  # latest fragment id (for media download URL)


_merge_buffers: dict[str, _PendingBuffer] = {}

# Strong refs for fire-and-forget asyncio tasks so they don't get GC'd
# before they run.
_bg_task_refs: set[asyncio.Task] = set()


def _spawn_bg(coro) -> asyncio.Task:
    """Schedule a coroutine as a retained asyncio task (GC-safe)."""
    task = asyncio.create_task(coro)
    _bg_task_refs.add(task)
    task.add_done_callback(_bg_task_refs.discard)
    return task


def _looks_complete(text: str) -> bool:
    """Heuristic: is this fragment a complete thought?

    Returns False for very short fragments (likely mid-burst) — caller
    will use the longer merge window. True otherwise, falling through to
    the burst-mode override which catches the all-short-fragments case.

    Dr. Baba uses an LLM call for this (``src.queue.check_message_completeness``);
    we deliberately skip the extra LLM round-trip and rely on length +
    burst-mode override, which together cover the same observed cases.
    """
    stripped = (text or "").strip()
    if len(stripped) < 8:
        return False
    # Trailing punctuation — '。', '!', '?', '。', etc. — signals end of thought
    if stripped[-1] in "。！？!?":
        return True
    # Otherwise we don't know — assume incomplete so the longer merge window
    # applies. The burst-mode override catches the "all-short-fragments" case.
    return False


async def _enqueue_for_merge(
    *,
    phone: str,
    text: str,
    chat_id: str,
    account_id: str,
    sender_name: str = "",
    attachments: list[dict] | None = None,
    message_id: str = "",
) -> None:
    """Append a message to the per-phone buffer; spawn flusher if first in."""
    print(f"[WA-ENQUEUE] phone={phone} text={text[:40]}")
    try:
        now = time.monotonic()
        buf = _merge_buffers.get(phone)
        new_buffer = buf is None
        if new_buffer:
            buf = _PendingBuffer(
                chat_id=chat_id,
                account_id=account_id,
                sender_name=sender_name,
                first_arrival=now,
                message_id=message_id or "",
            )
            _merge_buffers[phone] = buf

        if text and text.strip():
            buf.texts.append(text.strip())
        if attachments:
            buf.attachments.extend(attachments)
        if message_id:
            buf.message_id = message_id
            buf.fragment_ids.append(message_id)
        buf.last_activity = now

        if new_buffer and not buf.flusher_running:
            buf.flusher_running = True
            _spawn_bg(_wait_and_flush(phone))
            print(f"[WA-ENQUEUE] Flusher spawned for phone={phone}")
        else:
            print(
                f"[WA-ENQUEUE] Appended to existing buffer: "
                f"phone={phone} msgs={len(buf.texts)}"
            )
    except Exception as exc:
        logger.exception("[WA-ENQUEUE] crashed for %s: %s", phone, exc)
        # Fallback: skip merge buffer, process immediately
        try:
            await _process_turn(
                phone=phone,
                merged_text=text,
                chat_id=chat_id,
                account_id=account_id,
                sender_name=sender_name,
                attachments=attachments or [],
                fragment_ids=[message_id] if message_id else [],
                primary_message_id=message_id,
            )
        except Exception:
            logger.exception("[WA-ENQUEUE] direct processing also failed for %s", phone)


async def _wait_and_flush(phone: str) -> None:
    """Owner coroutine — waits for buffer to settle, then flushes once."""
    try:
        while True:
            buf = _merge_buffers.get(phone)
            if buf is None:
                return

            age = time.monotonic() - buf.first_arrival
            if age >= WA_MERGE_FORCE:
                break

            combined = "\n".join(buf.texts)
            is_complete = _looks_complete(combined)

            # Burst-mode override — short fragments get the longer window.
            if is_complete and buf.texts:
                avg_len = sum(len(t) for t in buf.texts) / len(buf.texts)
                if (
                    avg_len < WA_BURST_AVG_CHARS
                    and len(buf.texts) <= WA_BURST_MAX_FRAGMENTS
                ):
                    is_complete = False

            window = WA_MERGE_COMPLETE if is_complete else WA_MERGE_INCOMPLETE
            remaining_to_force = max(0.1, WA_MERGE_FORCE - age)
            sleep_for = min(window, remaining_to_force)

            activity_before_sleep = buf.last_activity
            print(
                f"[WA-FLUSH] phone={phone} complete={is_complete} "
                f"window={window}s sleep={sleep_for:.2f}s msgs={len(buf.texts)}"
            )
            await asyncio.sleep(sleep_for)

            buf = _merge_buffers.get(phone)
            if buf is None:
                return
            if buf.last_activity > activity_before_sleep:
                continue
            break

        buf = _merge_buffers.pop(phone, None)
        if buf is None or (not buf.texts and not buf.attachments):
            return

        merged_text = "\n".join(buf.texts)
        print(
            f"[WA-FLUSH] FLUSH phone={phone} msgs={len(buf.texts)} "
            f"text={merged_text[:60]}"
        )

        await _process_turn(
            phone=phone,
            merged_text=merged_text,
            chat_id=buf.chat_id,
            account_id=buf.account_id,
            sender_name=buf.sender_name,
            attachments=buf.attachments,
            fragment_ids=buf.fragment_ids,
            primary_message_id=buf.message_id,
        )
    except asyncio.CancelledError:
        _merge_buffers.pop(phone, None)
        raise
    except Exception as exc:
        logger.exception("[WA-FLUSH] flusher crashed for %s: %s", phone, exc)
        _merge_buffers.pop(phone, None)


# ---------------------------------------------------------------------------
# Per-phone lock — serialise pipeline runs for the same customer
# ---------------------------------------------------------------------------

_phone_locks: dict[str, asyncio.Lock] = {}


def _lock_for(phone: str) -> asyncio.Lock:
    lock = _phone_locks.get(phone)
    if lock is None:
        lock = asyncio.Lock()
        _phone_locks[phone] = lock
    return lock


# ---------------------------------------------------------------------------
# Group-chat silent listener
# ---------------------------------------------------------------------------


async def _listen_group_message(msg: ChatDaddyMessage, account_id: str) -> None:  # noqa: ARG001
    """Absorb a group message that didn't @-mention Jessica.

    No reply is sent. We update the sender's CRM record so that when they
    eventually do @-mention Jessica she already has context: their display
    name and any health complaints mentioned in passing.

    The account_id argument is accepted for API symmetry / future use
    (e.g. read-receipt acknowledgement) but is currently unused.
    """
    user_phone = msg.effective_user_phone
    pipeline = _get_pipeline()
    if pipeline is None:
        logger.debug("[group_listen] pipeline not ready — skipping %s", user_phone)
        return

    try:
        async with _lock_for(user_phone):
            # Load (or create) the per-sender CRM record.
            user = await pipeline._crm.get_or_create_user(user_phone)  # noqa: SLF001

            updates: dict[str, Any] = {}

            # Store the sender's WhatsApp display name the first time we see them.
            if msg.sender_name and not user.name:
                updates["name"] = msg.sender_name
                logger.debug(
                    "[group_listen] captured name=%r for %s", msg.sender_name, user_phone
                )

            # Extract health complaints mentioned in passing (keyword scan —
            # no LLM call, so this is free and fast).
            if msg.text.strip():
                complaints = detect_all_health_complaints(msg.text)
                if complaints:
                    existing = set(user.pain_points or [])
                    new_complaints = [c for c in complaints if c not in existing]
                    if new_complaints:
                        updates["pain_points"] = list(existing | set(new_complaints))
                        logger.info(
                            "[group_listen] added pain_points=%s for %s",
                            new_complaints, user_phone,
                        )

            # Append message to rolling history window so Planner has context
            # when the user eventually @-mentions Jessica.
            if msg.text.strip():
                conv_msg = ConversationMessage(
                    role="user",
                    text=msg.text,
                    timestamp=str(msg.timestamp),
                )
                user = user.append_message(conv_msg)
                updates["conversation_history"] = [
                    m.model_dump() for m in user.conversation_history
                ]

            if updates:
                updated_user = user.with_updates(**{
                    k: v for k, v in updates.items()
                    if k not in ("conversation_history",)  # already applied via append_message
                })
                await pipeline._crm.save_user(updated_user)  # noqa: SLF001
            elif msg.text.strip():
                # Still persist the updated conversation_history even if no
                # other fields changed.
                await pipeline._crm.save_user(user)  # noqa: SLF001

    except Exception as exc:
        logger.exception("[group_listen] failed for %s: %s", user_phone, exc)


# ---------------------------------------------------------------------------
# Pipeline dispatch
# ---------------------------------------------------------------------------


async def _process_turn(
    *,
    phone: str,
    merged_text: str,
    chat_id: str,
    account_id: str,
    sender_name: str = "",
    attachments: list[dict] | None = None,
    fragment_ids: list[str] | None = None,
    primary_message_id: str = "",
) -> None:
    """Run one merged turn through the pipeline + send bubbles.

    Pure orchestration — assumes upstream has done dedup, group-gate,
    blocklist, and echo suppression.
    """
    fragment_ids = fragment_ids or []
    attachments = attachments or []

    # ---- RESTART keyword (wipes all CRM for this phone) ---------------
    if _is_restart_command(merged_text):
        pipeline = _get_pipeline()
        if pipeline is not None:
            try:
                counts = await pipeline._crm.delete_all_for_phone(phone)  # noqa: SLF001
                logger.info("[RESTART] wiped phone=%s counts=%s", phone, counts)
            except Exception:
                logger.exception("[RESTART] wipe failed for %s", phone)
        try:
            await client.send_long_message(
                account_id, chat_id,
                "已清除你嘅資料 🌿 我哋重新開始啦，發 hi 我幫你 onboard 返。",
            )
        except Exception:
            logger.exception("[RESTART] confirmation send failed for %s", phone)
        return

    # ---- Blocklist (last gate before pipeline) -----------------------
    decision = blocklist.decide(phone)
    if decision.blocked:
        if decision.should_send_reply:
            try:
                await client.send_message(account_id, chat_id, decision.canned_reply)
                logger.info("[blocklist] sent canned reply to %s", phone)
            except Exception:
                logger.exception("[blocklist] canned-reply send failed for %s", phone)
        else:
            logger.info("[blocklist] dropped inbound from %s (silent)", phone)
        return

    pipeline = _get_pipeline()
    if pipeline is None:
        logger.error(
            "[WA] pipeline not initialised — dropping turn for %s (state.pipeline missing)",
            phone,
        )
        return

    # Download + decrypt media via ChatDaddy transcoder. Audio → Whisper
    # transcript (merged into user_message). Image → local /tmp path
    # passed to Constitution Agent's vision flow.
    image_paths, transcript = await _download_and_process_media(
        attachments=attachments,
        account_id=account_id,
        chat_id=chat_id,
        message_id=primary_message_id,
    )

    effective_message = merged_text
    if transcript:
        # Voice note is the user's "message". If they typed text in the
        # same burst, append both (typed first, then voice).
        effective_message = (
            f"{merged_text} {transcript}".strip() if merged_text else transcript
        )
        logger.info("[WA] voice transcript: %r", transcript[:120])

    async with _lock_for(phone):
        try:
            result: PipelineResult = await pipeline.run_turn(
                phone=phone,
                user_message=effective_message,
                media_urls=image_paths,
                merged_from_fragments=fragment_ids,
                wa_message_id=primary_message_id or None,
            )
        except Exception:
            logger.exception("[WA] pipeline.run_turn failed for %s", phone)
            return

        bubbles = list(result.writer_output.bubbles or [])
        logger.info(
            "[WA] turn=%s phone=%s bubbles=%d",
            result.turn_id, phone, len(bubbles),
        )

        # media_to_send entries: {"url": str, "after_bubble_idx": str|int}
        raw_media = getattr(result.writer_output, "media_to_send", None) or []
        media_to_send: list[dict] = []
        try:
            for m in raw_media:
                media_to_send.append({
                    "url": m.get("url", ""),
                    "after_bubble_idx": int(m.get("after_bubble_idx", 0)),
                })
        except Exception:  # noqa: BLE001
            logger.exception("malformed media_to_send: %s", raw_media)

        await _send_bubbles(
            account_id=account_id,
            chat_id=chat_id,
            bubbles=bubbles,
            media_to_send=media_to_send,
            inbound_was_voice=bool(transcript),
        )


# Tokens that trigger a full CRM wipe for the sender (case-insensitive).
_RESTART_TOKENS = {
    "restart", "reset",
    "重新開始", "重新开始", "重置", "重新嚟過", "重新嚟过",
    "/reset", "/restart",
}


def _is_restart_command(text: str) -> bool:
    if not text:
        return False
    t = text.strip()
    if t.lower() in _RESTART_TOKENS:
        return True
    # Tolerate punctuation / surrounding whitespace
    return t.lower() in _RESTART_TOKENS


def _extract_media_urls(attachments: list[dict]) -> list[str]:
    """Pull direct URLs off the ChatDaddy attachment dicts. (Legacy.)"""
    urls: list[str] = []
    for att in attachments:
        url = att.get("url") or att.get("directPath") or ""
        if url:
            urls.append(url)
    return urls


_MEDIA_TMP_DIR = Path(os.environ.get("MEDIA_TMP_DIR", "/tmp/jessica_media"))
_MEDIA_TMP_DIR.mkdir(parents=True, exist_ok=True)


def _classify_attachment(att: dict) -> str:
    """Returns 'audio' | 'image' | 'video' | 'document' | 'other'."""
    t = (att.get("type") or "").lower()
    mime = (att.get("mimetype") or att.get("mimeType") or "").lower()
    if "audio" in t or mime.startswith("audio/") or "ptt" in t:
        return "audio"
    if "image" in t or mime.startswith("image/"):
        return "image"
    if "video" in t or mime.startswith("video/"):
        return "video"
    if "document" in t or mime in ("application/pdf",):
        return "document"
    return "other"


def _ext_for(kind: str, att: dict) -> str:
    mime = (att.get("mimetype") or att.get("mimeType") or "").lower()
    return {
        "audio/ogg": "ogg", "audio/mpeg": "mp3", "audio/mp4": "m4a",
        "image/jpeg": "jpg", "image/png": "png", "image/webp": "webp",
        "video/mp4": "mp4",
    }.get(mime, {"audio": "ogg", "image": "jpg"}.get(kind, "bin"))


async def _download_and_process_media(
    *,
    attachments: list[dict],
    account_id: str,
    chat_id: str,
    message_id: str,
) -> tuple[list[str], str]:
    """Download attachments via ChatDaddy transcoder; transcribe audio.

    Returns:
        (image_paths, transcribed_text)
        - image_paths: local /tmp paths (Constitution Agent → vision)
        - transcribed_text: concatenated Whisper output for any audio,
          empty string if no audio (or if transcription failed).
    """
    if not attachments:
        return [], ""

    try:
        api_token = await client.get_token()
    except Exception as exc:  # noqa: BLE001
        logger.exception("media download skipped — ChatDaddy auth failed: %s", exc)
        return [], ""

    image_paths: list[str] = []
    transcript_parts: list[str] = []

    for idx, att in enumerate(attachments):
        kind = _classify_attachment(att)
        if kind not in ("audio", "image"):
            logger.info("skipping attachment kind=%s (not yet supported)", kind)
            continue

        try:
            audio_or_image_bytes = await whatsapp_media.download_media(
                att,
                account_id=account_id,
                chat_id=chat_id,
                message_id=message_id,
                api_token=api_token,
                media_kind=kind,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("download_media failed (kind=%s): %s", kind, exc)
            continue

        if not audio_or_image_bytes:
            logger.warning("download_media returned empty (kind=%s)", kind)
            continue

        if kind == "audio":
            # Transcribe → text
            text = await llm_transcribe.transcribe_audio(
                audio_or_image_bytes,
                filename_hint=f"{message_id or 'voice'}_{idx}.ogg",
            )
            if text:
                transcript_parts.append(text)
            else:
                logger.warning("voice note arrived but Whisper returned empty text")

        elif kind == "image":
            # Save to /tmp; Constitution Agent base64-encodes from path.
            ext = _ext_for(kind, att)
            path = _MEDIA_TMP_DIR / f"{message_id or 'img'}_{idx}.{ext}"
            try:
                path.write_bytes(audio_or_image_bytes)
                image_paths.append(str(path))
                logger.info(
                    "saved image (%d bytes) → %s", len(audio_or_image_bytes), path,
                )
            except Exception:  # noqa: BLE001
                logger.exception("could not save image to %s", path)

    transcript = " ".join(transcript_parts).strip()
    return image_paths, transcript


async def _send_bubbles(
    *,
    account_id: str,
    chat_id: str,
    bubbles: list[str],
    media_to_send: list[dict] | None = None,
    inbound_was_voice: bool = False,
) -> None:
    """Send the Writer's bubble list with the client's typing-delay model.

    Inline media: after sending bubble index N, also send any media whose
    ``after_bubble_idx`` equals N (image as a separate WhatsApp message).

    Voice reply (match-modality): when ``inbound_was_voice`` is True, we
    kick off MiniMax TTS in the background while the text bubbles stream,
    then send the audio file as a final attachment so the voice-replying
    user gets an audible reply without perceiving the synthesis latency.
    """
    if not bubbles:
        return
    media_to_send = media_to_send or []

    # Kick off TTS synthesis BEFORE the text-bubble loop so the audio is
    # (hopefully) ready by the time the final bubble has been sent. Synth
    # typically takes 1-3s; bubble delays add up to 10-20s — so the voice
    # almost always lands at the end with zero perceived wait.
    voice_task: asyncio.Task[Any] | None = None
    if inbound_was_voice:
        from src.media.tts import merge_bubbles_for_speech, synthesize

        voice_script = merge_bubbles_for_speech(list(bubbles))
        if voice_script:
            voice_task = asyncio.create_task(synthesize(voice_script))

    try:
        await _send_bubbles_impl(
            account_id=account_id,
            chat_id=chat_id,
            bubbles=bubbles,
            media_to_send=media_to_send,
            voice_task=voice_task,
        )
    finally:
        # Defensive: if we crashed before awaiting voice_task, cancel it so
        # Python doesn't emit "Task was destroyed but it is pending" warnings
        # and so we don't keep the MiniMax HTTP call running uselessly.
        if voice_task is not None and not voice_task.done():
            voice_task.cancel()


async def _send_bubbles_impl(
    *,
    account_id: str,
    chat_id: str,
    bubbles: list[str],
    media_to_send: list[dict],
    voice_task: asyncio.Task[Any] | None,
) -> None:
    """Inner body of ``_send_bubbles`` — see that function's docstring."""
    # Group media by the bubble index they should appear after.
    # Defensive: only accept absolute http(s) URLs — relative paths
    # (e.g. 'data/media/...') would be unfetchable by ChatDaddy.
    media_by_idx: dict[int, list[str]] = {}
    for m in media_to_send:
        url = (m.get("url") or "").strip()
        if not url or not url.startswith(("http://", "https://")):
            logger.info("[WA] skip non-absolute media URL: %r", url[:80])
            continue
        try:
            idx = int(m.get("after_bubble_idx") or 0)
        except (TypeError, ValueError):
            idx = 0
        media_by_idx.setdefault(idx, []).append(url)

    for i, bubble in enumerate(bubbles):
        text = (bubble or "").strip()
        if not text:
            continue
        if i > 0:
            delay = client._typing_delay(text)  # noqa: SLF001 — intentional reuse
            await asyncio.sleep(delay)
        try:
            await client.send_long_message(account_id, chat_id, text)
        except client.SendProbablyDeliveredError:
            logger.warning(
                "[WA] send timed out but probably delivered (chat=%s, bubble=%d/%d)",
                chat_id, i + 1, len(bubbles),
            )
        except Exception:
            logger.exception(
                "[WA] send failed (chat=%s, bubble=%d/%d) — abandoning rest of bubbles",
                chat_id, i + 1, len(bubbles),
            )
            # Don't return — still try to deliver any pending voice file so
            # the voice-user at least gets the audio version of the reply.
            break

        # Send any media that should follow this bubble.
        for url in media_by_idx.get(i, []):
            try:
                await asyncio.sleep(0.8)  # gentle pause before the image
                mimetype = _guess_mimetype(url)
                await client.send_message(
                    account_id,
                    chat_id,
                    text="",
                    attachments=[
                        {"url": url, "type": "image", "mimetype": mimetype}
                    ],
                )
            except Exception:
                logger.exception("[WA] media send failed (url=%s)", url[:80])

    # ── Final voice-reply send (match-modality) ──────────────────────
    if voice_task is not None:
        try:
            await asyncio.sleep(0.6)  # small breath before the audio bubble
            voice_result = await voice_task
        except Exception:
            logger.exception("[WA] tts synthesis task crashed")
            voice_result = None

        if voice_result is None:
            logger.info("[WA] tts skipped or failed — sending text only")
        else:
            voice_url = voice_result.url
            if not voice_url.startswith(("http://", "https://")):
                logger.warning(
                    "[WA] tts url is relative (%s) — JESSICA_BASE_URL not set; skipping audio send",
                    voice_url,
                )
            else:
                try:
                    await client.send_message(
                        account_id,
                        chat_id,
                        text="",
                        attachments=[
                            {
                                "url": voice_url,
                                "type": "audio",
                                "mimetype": voice_result.mime_type,
                            }
                        ],
                    )
                    logger.info(
                        "[WA] sent voice reply (%d bytes, %s)",
                        voice_result.byte_count, voice_url[:60],
                    )
                except Exception:
                    logger.exception("[WA] voice attachment send failed")


def _guess_mimetype(url: str) -> str:
    """Map a URL/path's extension to the mimetype ChatDaddy expects."""
    lower = (url or "").lower().split("?")[0]
    if lower.endswith((".jpg", ".jpeg")):
        return "image/jpeg"
    if lower.endswith(".png"):
        return "image/png"
    if lower.endswith(".webp"):
        return "image/webp"
    if lower.endswith(".gif"):
        return "image/gif"
    if lower.endswith(".mp4"):
        return "video/mp4"
    return "image/jpeg"  # safe default for unknown image extensions


# ---------------------------------------------------------------------------
# Pipeline reference (lazy — populated by web.py during lifespan startup)
# ---------------------------------------------------------------------------

_pipeline_ref: JessicaPipeline | None = None


def set_pipeline(pipeline: JessicaPipeline) -> None:
    """Register the active pipeline. Called from ``web.lifespan`` at startup."""
    global _pipeline_ref
    _pipeline_ref = pipeline


def _get_pipeline() -> JessicaPipeline | None:
    return _pipeline_ref


# ---------------------------------------------------------------------------
# Webhook endpoint
# ---------------------------------------------------------------------------


@router.post("/webhook/chatdaddy")
async def chatdaddy_webhook(request: Request) -> JSONResponse:
    """Receive ChatDaddy webhook, return 200 immediately, process in background."""

    # 1. Validate webhook secret. In prod APP_ENV the secret MUST be set
    # (enforced at import time). In dev, an empty secret skips the check
    # so curl smoke tests work locally.
    if WEBHOOK_SECRET:
        incoming = request.headers.get("X-Webhook-Secret", "")
        # Constant-time comparison — defeats timing-attack probing of the secret.
        if not hmac.compare_digest(incoming.encode(), WEBHOOK_SECRET.encode()):
            return JSONResponse({"error": "unauthorized"}, status_code=401)

    # 2. Parse payload
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse({"error": "invalid json"}, status_code=400)

    # 2a. Diagnostic capture — bounded in-memory buffer, never raises.
    try:
        diagnostic_capture.capture(payload)
    except Exception:
        pass

    # 2b. Smoke-test shape — accept the dev-mode {"phone","text"} body so
    # `curl /webhook/chatdaddy -d '{"phone":...}'` keeps working. ChatDaddy
    # webhooks have an "event" + "data" shape; everything else falls
    # through to the smoke-test branch.
    #
    # SECURITY: smoke-test bypasses dedup / blocklist / group-gate and
    # accepts an attacker-controlled phone + media_urls. Gated to non-prod.
    msg = parse_webhook(payload)
    if msg is None:
        if APP_ENV == "production":
            return JSONResponse({"error": "invalid webhook payload"}, status_code=400)
        return await _handle_smoke_test_payload(payload)

    # 3. Skip bot's own messages
    if msg.from_me:
        return JSONResponse({"status": "echo_suppressed"})

    # 4. Dedup
    if _is_duplicate(msg.message_id):
        logger.debug("Duplicate message %s — skipping", msg.message_id)
        return JSONResponse({"status": "duplicate"})

    # 5. Must have text or attachments
    has_text = bool(msg.text.strip())
    has_media = len(msg.attachments) > 0
    if not has_text and not has_media:
        logger.info("Empty message from %s — skipping", msg.phone)
        return JSONResponse({"status": "empty"})

    # 6. Group gate — listen silently or reply when @-mentioned.
    if msg.is_group:
        group_action = group_gate.decide_group(msg, BOT_JID, BOT_NAMES)
        if group_action == group_gate.GroupAction.LISTEN:
            # Not mentioned — absorb context into CRM, no reply.
            account_id = msg.account_id or DEFAULT_ACCOUNT_ID
            _record_seen_message_id(msg.message_id)
            _spawn_bg(_listen_group_message(msg, account_id))
            return JSONResponse({"status": "group_listen"})
        # GroupAction.REPLY — fall through to normal pipeline dispatch below.
        logger.info(
            "[group_gate] REPLY — %s mentioned in group %s",
            BOT_JID or BOT_NAMES, msg.chat_id,
        )

    # 7. Record for dedup + dispatch.
    # Use effective_user_phone (per-sender CRM key) so group members each
    # get their own CRM record instead of being bucketed under the group JID.
    _record_seen_message_id(msg.message_id)
    account_id = msg.account_id or DEFAULT_ACCOUNT_ID
    user_phone = msg.effective_user_phone

    if WA_USE_MERGE_BUFFER:
        _spawn_bg(_enqueue_for_merge(
            phone=user_phone,
            text=msg.text,
            chat_id=msg.chat_id,
            account_id=account_id,
            sender_name=msg.sender_name,
            attachments=list(msg.attachments),
            message_id=msg.message_id,
        ))
    else:
        _spawn_bg(_process_turn(
            phone=user_phone,
            merged_text=msg.text,
            chat_id=msg.chat_id,
            account_id=account_id,
            sender_name=msg.sender_name,
            attachments=list(msg.attachments),
            fragment_ids=[msg.message_id] if msg.message_id else [],
            primary_message_id=msg.message_id,
        ))

    return JSONResponse({"status": "queued"})


# ---------------------------------------------------------------------------
# Smoke-test path (dev-only POST {"phone","text"})
# ---------------------------------------------------------------------------


async def _handle_smoke_test_payload(payload: dict[str, Any]) -> JSONResponse:
    """Dev-mode webhook body: ``{"phone": "...", "text": "...", ...}``.

    Runs the pipeline inline (no merge buffer, no ChatDaddy send) and
    returns the bubbles in the JSON response. Useful for ``curl`` and
    integration tests where we don't have a real ChatDaddy webhook.
    """
    phone = payload.get("phone") or payload.get("from")
    text = payload.get("text") or payload.get("message") or ""
    media_urls = payload.get("media_urls") or []

    if not phone or not text:
        return JSONResponse(
            {"error": "missing phone or text"},
            status_code=400,
        )

    pipeline = _get_pipeline()
    if pipeline is None:
        return JSONResponse({"error": "pipeline not initialised"}, status_code=503)

    try:
        result = await pipeline.run_turn(
            phone=str(phone),
            user_message=str(text),
            media_urls=list(media_urls),
        )
    except Exception as exc:
        logger.exception("[smoke-test] pipeline failed: %s", exc)
        return JSONResponse({"error": str(exc)}, status_code=500)

    return JSONResponse({
        "turn_id": result.turn_id,
        "bubbles": list(result.writer_output.bubbles or []),
        "trace_url": f"/trace/{result.turn_id}",
    })
