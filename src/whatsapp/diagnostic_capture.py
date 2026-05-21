"""Circular buffer of recent raw ChatDaddy webhook payloads for diagnostics.

In-memory only (survives a single process lifetime). Used to inspect what
ChatDaddy actually sends — especially for group-chat support discovery
(participantId, senderJid, mentionedJids, quoted-message metadata) which
are not currently parsed by ``ChatDaddyMessage``.

Exposed via the authenticated admin endpoint
``/api/whatsapp/debug/raw-webhooks``. Capture is unconditional (every
webhook), retention is bounded (``_BUFFER_SIZE``), so memory cost is fixed.

DESIGN NOTES
------------
- Diagnostic must never break the request path → all functions swallow
  exceptions.
- No PII redaction here — admin endpoint is auth-gated; this is the
  same data already flowing through the request handler. Treat as
  ops-internal data.
- Frozen dataclass so captured snapshots are immutable.
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass
from threading import Lock
from typing import Any

# Maximum number of webhooks retained in memory. Each ChatDaddy payload
# is typically <5 KB, so 20 × 5 KB = 100 KB upper bound — negligible.
_BUFFER_SIZE: int = 20


@dataclass(frozen=True)
class CapturedWebhook:
    """One observed ChatDaddy webhook payload (post-JSON-parse, pre-routing)."""

    received_at: int  # unix seconds
    is_group: bool    # ``chatId`` ends with ``@g.us``
    chat_id: str
    sender_contact_id: str  # ``senderContactId`` — distinct from chat_id in groups
    has_mentions: bool
    has_quoted: bool
    text_len: int
    raw: dict[str, Any]      # full payload, untouched


_buffer: deque[CapturedWebhook] = deque(maxlen=_BUFFER_SIZE)
_lock = Lock()


# ---------------------------------------------------------------------------
# Capture (called from router on every inbound webhook)
# ---------------------------------------------------------------------------


def capture(payload: dict[str, Any]) -> None:
    """Append a raw payload to the diagnostic buffer.

    Best-effort — never raises. If shape is unexpected we still attempt
    to record what we can so unrecognised events are visible too.
    """
    try:
        data_arr = payload.get("data") or []
        first: dict[str, Any] = (
            data_arr[0]
            if data_arr and isinstance(data_arr[0], dict)
            else {}
        )
        chat_id = str(first.get("chatId") or first.get("chat_id") or "")
        sender_contact_id = str(
            first.get("senderContactId") or first.get("sender_contact_id") or ""
        )
        mentions_field = (
            first.get("mentionedJids")
            or first.get("mentioned")
            or first.get("mentions")
            or []
        )
        with _lock:
            _buffer.append(
                CapturedWebhook(
                    received_at=int(time.time()),
                    is_group=chat_id.endswith("@g.us"),
                    chat_id=chat_id,
                    sender_contact_id=sender_contact_id,
                    has_mentions=bool(mentions_field),
                    has_quoted=bool(first.get("quoted")),
                    text_len=len(str(first.get("text") or "")),
                    raw=payload,
                )
            )
    except Exception:
        # Diagnostic must never break the request path. Silent on purpose.
        pass


# ---------------------------------------------------------------------------
# Read paths (called from admin endpoint)
# ---------------------------------------------------------------------------


def recent(limit: int = 20, group_only: bool = False) -> list[dict[str, Any]]:
    """Return recent captured webhooks, newest first.

    Each item is a JSON-serialisable dict.
    """
    with _lock:
        items = list(_buffer)
    items.reverse()  # newest first
    if group_only:
        items = [w for w in items if w.is_group]
    items = items[: max(0, min(limit, _BUFFER_SIZE))]
    return [
        {
            "received_at": w.received_at,
            "is_group": w.is_group,
            "chat_id": w.chat_id,
            "sender_contact_id": w.sender_contact_id,
            "has_mentions": w.has_mentions,
            "has_quoted": w.has_quoted,
            "text_len": w.text_len,
            "raw": w.raw,
        }
        for w in items
    ]


def field_shape() -> dict[str, Any]:
    """Summarise which fields appear in captured payloads.

    Useful for discovering ChatDaddy field names without reading every
    full payload. Returns frequency counts for each key seen in
    ``data[*]`` across the buffer.
    """
    with _lock:
        items = list(_buffer)

    field_counts: dict[str, int] = {}
    group_count = 0
    mention_count = 0
    quoted_count = 0
    sender_id_count = 0

    for w in items:
        if w.is_group:
            group_count += 1
        if w.has_mentions:
            mention_count += 1
        if w.has_quoted:
            quoted_count += 1
        if w.sender_contact_id:
            sender_id_count += 1

        data_arr = w.raw.get("data") or []
        for item in data_arr:
            if isinstance(item, dict):
                for key in item.keys():
                    field_counts[key] = field_counts.get(key, 0) + 1

    return {
        "total_captured": len(items),
        "group_payloads": group_count,
        "with_mentions": mention_count,
        "with_quoted": quoted_count,
        "with_sender_contact_id": sender_id_count,
        "field_frequencies": dict(
            sorted(field_counts.items(), key=lambda kv: -kv[1])
        ),
    }


def clear() -> int:
    """Clear the buffer (admin-only, used after capture session)."""
    with _lock:
        n = len(_buffer)
        _buffer.clear()
        return n
