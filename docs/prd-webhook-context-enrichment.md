# PRD: ChatDaddy Webhook Context Enrichment
**Status:** Draft  
**Version:** 1.0  
**Owner:** Shivonne  
**Reusability:** Cross-project — drop into any ChatDaddy-connected agent

---

## Problem

When a ChatDaddy webhook arrives, the pipeline only has the **single inbound message**. To make intelligent responses, an agent needs two things simultaneously:

1. **CRM profile** — user's status, constitution, history stored locally
2. **ChatDaddy chat history** — the source of truth from ChatDaddy's own DB

These are currently handled separately per project, or ChatDaddy history is skipped entirely. This means:
- Fresh deployments have no history (local CRM is empty)
- Server restarts / DB wipes lose prior context
- Cross-project duplication — every project re-solves the same problem differently

---

## Goals

- Pull CRM + ChatDaddy history **in parallel** on every webhook
- Merge + deduplicate both sources into one unified history
- **Never block** the webhook 200 response — enrichment runs with a hard timeout
- Graceful degradation when either source fails
- Drop-in module — configurable via env vars, no code changes per project

## Non-Goals

- Not a full CRM system
- Not a message archival/storage service  
- Not a ChatDaddy client replacement (assumes a ChatDaddy client already exists in the project)
- Does not handle outbound messages

---

## ChatDaddy History API

**Endpoint:** `GET https://api.chatdaddy.tech/im/messages/{accountId}/{chatId}`

**Key parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `count` | int | Number of messages to fetch (default: 20) |
| `beforeId` | string | Pagination — fetch messages before this ID |
| `fromMe` | bool | Filter: only user messages or only bot messages |
| `fetchFromPlatform` | bool | If true, fetch from WhatsApp source if not in ChatDaddy DB |

**Available from webhook payload:**  
- `accountId` → `msg.account_id`  
- `chatId` → `msg.chat_id` (e.g. `85291234567@s.whatsapp.net`)

Both are present in every webhook. No extra lookup needed.

---

## Interface Contract

### Input

```python
@dataclass(frozen=True)
class WebhookContext:
    account_id: str     # from webhook payload
    chat_id: str        # from webhook payload  
    message_id: str     # current inbound message ID (for dedup)
    timestamp: int      # current message timestamp
```

### Output

```python
@dataclass(frozen=True)
class EnrichedContext:
    crm_user: User | None                  # local CRM profile (None if not found or failed)
    chat_history: list[HistoryMessage]     # merged, deduplicated, sorted ASC by timestamp
    history_source: HistorySource          # "local" | "chatdaddy" | "merged" | "empty"
    crm_ok: bool                           # False if CRM fetch failed
    chatdaddy_ok: bool                     # False if ChatDaddy fetch failed
    enrichment_ms: int                     # total latency for observability

class HistorySource(str, Enum):
    LOCAL = "local"
    CHATDADDY = "chatdaddy"
    MERGED = "merged"
    EMPTY = "empty"

@dataclass(frozen=True)
class HistoryMessage:
    message_id: str
    chat_id: str
    text: str
    from_me: bool
    timestamp: int
    source: str         # "local" | "chatdaddy"
```

---

## Data Flow

```
Webhook arrives
     │
     ▼
extract (account_id, chat_id, message_id)
     │
     ├──────────────────────────────────┐
     │                                  │
     ▼                                  ▼
[Task A]                          [Task B]
CRM.get_user(chat_id)             ChatDaddy.get_messages(
                                    account_id, chat_id,
                                    count=HISTORY_COUNT
                                  )
     │                                  │
     └──────────────┬───────────────────┘
                    ▼
            asyncio.gather(return_exceptions=True)
            (hard timeout: HISTORY_TIMEOUT_MS)
                    │
                    ▼
            merge_histories(crm_history, cd_history)
            - deduplicate by message_id
            - fallback dedup: (timestamp, text[:50], from_me)
            - sort by timestamp ASC
            - take last HISTORY_WINDOW messages
            - exclude current inbound message_id
                    │
                    ▼
            EnrichedContext → pipeline
```

---

## Merge Strategy

**Source of truth priority:** ChatDaddy > local CRM

**Dedup key (in order of preference):**
1. `message_id` exact match
2. Composite: `(timestamp_rounded_to_sec, text[:50], from_me)` — for messages where ChatDaddy and local used different ID formats

**Merge rules:**
- If same message in both sources → keep ChatDaddy version, mark `source="chatdaddy"`
- ChatDaddy-only → include, `source="chatdaddy"`
- Local-only → include, `source="local"`
- Sort merged list by `timestamp` ascending
- Take last `HISTORY_WINDOW` (default: 20)
- Always exclude the current inbound message (it's handled by the pipeline directly)

---

## Error Handling

| Failure | Behavior | `history_source` |
|---------|----------|-----------------|
| CRM unavailable / timeout | `crm_user=None`, `crm_ok=False`, proceed with ChatDaddy only | `"chatdaddy"` |
| ChatDaddy 4xx (e.g. 401, 404) | Log warning, `chatdaddy_ok=False`, use local CRM only | `"local"` |
| ChatDaddy timeout | Log warning, `chatdaddy_ok=False`, use local CRM only | `"local"` |
| ChatDaddy returns empty list | Use local CRM history | `"local"` |
| Both fail | `EnrichedContext` with empty history, pipeline continues | `"empty"` |
| Overall enrichment timeout | Return whatever was collected so far, pipeline continues | varies |

**Critical rule: enrichment MUST NOT block the webhook 200 response.**  
The enrichment module wraps both fetches in `asyncio.timeout(HISTORY_TIMEOUT_MS / 1000)`. If the timeout fires, return partial results and proceed.

---

## Configuration

All tunable via environment variables:

```bash
# Feature toggle
CHATDADDY_HISTORY_ENABLED=true          # default: true

# Fetch settings
CHATDADDY_HISTORY_COUNT=20              # messages to fetch from ChatDaddy
CHATDADDY_HISTORY_WINDOW=20            # final merged window size
CHATDADDY_HISTORY_TIMEOUT_MS=2500      # hard timeout for both fetches combined

# Behaviour flags
CHATDADDY_HISTORY_ON_FIRST_TOUCH=true  # pull even for brand-new users (status=NEW)
CHATDADDY_HISTORY_FETCH_FROM_PLATFORM=false  # pass fetchFromPlatform=true to ChatDaddy API
```

---

## Implementation Reference

### Python (asyncio)

```python
# src/context/enrichment.py

import asyncio
import time
import logging
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("context.enrichment")

HISTORY_ENABLED = os.environ.get("CHATDADDY_HISTORY_ENABLED", "true") == "true"
HISTORY_COUNT = int(os.environ.get("CHATDADDY_HISTORY_COUNT", "20"))
HISTORY_WINDOW = int(os.environ.get("CHATDADDY_HISTORY_WINDOW", "20"))
HISTORY_TIMEOUT_S = float(os.environ.get("CHATDADDY_HISTORY_TIMEOUT_MS", "2500")) / 1000


async def enrich_webhook(
    ctx: WebhookContext,
    crm: CRMRepo,
    cd_client: ChatDaddyClient,
) -> EnrichedContext:
    if not HISTORY_ENABLED:
        crm_user = await crm.get_user(ctx.chat_id)
        return EnrichedContext(
            crm_user=crm_user,
            chat_history=[],
            history_source=HistorySource.LOCAL,
            crm_ok=True,
            chatdaddy_ok=False,
            enrichment_ms=0,
        )

    start = time.monotonic()
    try:
        async with asyncio.timeout(HISTORY_TIMEOUT_S):
            crm_task = asyncio.create_task(crm.get_user(ctx.chat_id))
            cd_task = asyncio.create_task(
                cd_client.get_messages(ctx.account_id, ctx.chat_id, count=HISTORY_COUNT)
            )
            results = await asyncio.gather(crm_task, cd_task, return_exceptions=True)
    except asyncio.TimeoutError:
        logger.warning("Enrichment timed out after %.1fs", HISTORY_TIMEOUT_S)
        results = [crm_task.result() if crm_task.done() else None,
                   cd_task.result() if cd_task.done() else None]

    crm_user = results[0] if not isinstance(results[0], Exception) else None
    cd_history = results[1] if not isinstance(results[1], Exception) else []
    crm_ok = not isinstance(results[0], Exception)
    cd_ok = not isinstance(results[1], Exception)

    merged = _merge(
        local=crm_user.conversation_history if crm_user else [],
        remote=cd_history or [],
        exclude_id=ctx.message_id,
        window=HISTORY_WINDOW,
    )

    source = _determine_source(crm_ok, cd_ok, bool(merged))
    elapsed_ms = int((time.monotonic() - start) * 1000)

    logger.info(
        "Enrichment complete: source=%s crm_ok=%s cd_ok=%s history=%d elapsed=%dms",
        source, crm_ok, cd_ok, len(merged), elapsed_ms,
    )

    return EnrichedContext(
        crm_user=crm_user,
        chat_history=merged,
        history_source=source,
        crm_ok=crm_ok,
        chatdaddy_ok=cd_ok,
        enrichment_ms=elapsed_ms,
    )


def _merge(
    local: list,
    remote: list,
    exclude_id: str,
    window: int,
) -> list[HistoryMessage]:
    seen: dict[str, HistoryMessage] = {}

    # Index local messages first (lower priority)
    for msg in local:
        key = _dedup_key(msg)
        if key and msg.message_id != exclude_id:
            seen[key] = HistoryMessage(
                message_id=getattr(msg, "message_id", ""),
                chat_id=getattr(msg, "chat_id", ""),
                text=getattr(msg, "text", "") or getattr(msg, "content", ""),
                from_me=getattr(msg, "from_me", False),
                timestamp=getattr(msg, "timestamp", 0),
                source="local",
            )

    # Overwrite with ChatDaddy (higher priority)
    for msg in remote:
        key = _dedup_key(msg)
        if key and msg.get("id") != exclude_id:
            seen[key] = HistoryMessage(
                message_id=msg.get("id", ""),
                chat_id=msg.get("chatId", ""),
                text=msg.get("text", ""),
                from_me=bool(msg.get("fromMe", False)),
                timestamp=int(msg.get("timestamp", 0)),
                source="chatdaddy",
            )

    sorted_msgs = sorted(seen.values(), key=lambda m: m.timestamp)
    return sorted_msgs[-window:]


def _dedup_key(msg) -> str | None:
    """Primary: message_id. Fallback: composite key."""
    mid = getattr(msg, "message_id", None) or (msg.get("id") if isinstance(msg, dict) else None)
    if mid:
        return f"id:{mid}"
    # Composite fallback
    ts = getattr(msg, "timestamp", None) or (msg.get("timestamp") if isinstance(msg, dict) else None)
    text = getattr(msg, "text", None) or getattr(msg, "content", None) or (msg.get("text") if isinstance(msg, dict) else None) or ""
    from_me = getattr(msg, "from_me", None) or (msg.get("fromMe") if isinstance(msg, dict) else None)
    if ts and text:
        return f"composite:{int(ts)}:{str(from_me)}:{text[:50]}"
    return None


def _determine_source(crm_ok: bool, cd_ok: bool, has_history: bool) -> HistorySource:
    if not has_history:
        return HistorySource.EMPTY
    if crm_ok and cd_ok:
        return HistorySource.MERGED
    if cd_ok:
        return HistorySource.CHATDADDY
    return HistorySource.LOCAL
```

### TypeScript (Promise.allSettled)

```typescript
// src/context/enrichment.ts

export async function enrichWebhook(
  ctx: WebhookContext,
  crm: CRMRepo,
  cdClient: ChatDaddyClient,
): Promise<EnrichedContext> {
  const timeout = parseInt(process.env.CHATDADDY_HISTORY_TIMEOUT_MS ?? '2500')
  const count = parseInt(process.env.CHATDADDY_HISTORY_COUNT ?? '20')
  const window = parseInt(process.env.CHATDADDY_HISTORY_WINDOW ?? '20')
  const start = Date.now()

  const [crmResult, cdResult] = await Promise.allSettled([
    withTimeout(crm.getUser(ctx.chatId), timeout),
    withTimeout(cdClient.getMessages(ctx.accountId, ctx.chatId, { count }), timeout),
  ])

  const crmUser = crmResult.status === 'fulfilled' ? crmResult.value : null
  const cdHistory = cdResult.status === 'fulfilled' ? cdResult.value : []
  const crmOk = crmResult.status === 'fulfilled'
  const cdOk = cdResult.status === 'fulfilled'

  const merged = mergeHistories({
    local: crmUser?.conversationHistory ?? [],
    remote: cdHistory ?? [],
    excludeId: ctx.messageId,
    window,
  })

  return {
    crmUser,
    chatHistory: merged,
    historySource: determineSource(crmOk, cdOk, merged.length > 0),
    crmOk,
    chatdaddyOk: cdOk,
    enrichmentMs: Date.now() - start,
  }
}

function withTimeout<T>(promise: Promise<T>, ms: number): Promise<T> {
  return Promise.race([
    promise,
    new Promise<T>((_, reject) =>
      setTimeout(() => reject(new Error(`Timeout after ${ms}ms`)), ms)
    ),
  ])
}
```

---

## Integration Points

### TCM-Jessica (Python)
**Hook point:** `src/whatsapp/router.py`, after `parse_webhook()` and before `pipeline.run()`
```python
# Replace:
user = await crm.get_user(msg.phone)

# With:
ctx = WebhookContext(account_id=msg.account_id, chat_id=msg.chat_id, ...)
enriched = await enrich_webhook(ctx, crm, cd_client)
user = enriched.crm_user
```

### AOS 2.0 (TypeScript)
**Hook point:** Journey Engine `handleInbound()` — wrap existing CRM lookup with `enrichWebhook()`

### New projects
1. Copy `src/context/enrichment.py` (or `.ts`)
2. Set env vars
3. Call `enrich_webhook()` in webhook handler before routing to pipeline

---

## Acceptance Criteria

- [ ] Both fetches run in parallel (not sequential)
- [ ] Total enrichment completes in < 3s p95 under normal conditions
- [ ] Webhook 200 response is never delayed — enrichment times out gracefully
- [ ] Histories merged correctly — no duplicate messages
- [ ] ChatDaddy version wins on conflict
- [ ] Graceful degradation: CRM-only when ChatDaddy fails
- [ ] Graceful degradation: ChatDaddy-only when CRM fails
- [ ] Both fail → empty history, pipeline still runs
- [ ] `enrichment_ms` logged for every request
- [ ] Configurable via env vars, no code changes needed per project
- [ ] Unit tests: merge logic (dedup, sort, window)
- [ ] Integration tests: CRM fail, ChatDaddy fail, both fail, both succeed

---

## Write-Back: Persist ChatDaddy History to Local CRM

**Decision (Q1): Yes — write back on first pull.**

When ChatDaddy returns history and local CRM has none (or fewer messages), persist the ChatDaddy messages into the local CRM. This means:
- Subsequent webhook turns use local CRM directly (no extra ChatDaddy call needed)
- Resilient to ChatDaddy API downtime after first contact
- Keeps local CRM as the running source of truth going forward

### Write-Back Logic

```python
async def _write_back_if_needed(
    crm: CRMRepo,
    crm_user: User | None,
    cd_history: list[dict],
    chat_id: str,
) -> None:
    """Persist ChatDaddy history into local CRM if local is empty or sparse."""
    if not cd_history:
        return

    local_count = len(crm_user.conversation_history) if crm_user else 0
    cd_count = len(cd_history)

    # Only write back if ChatDaddy has meaningfully more history
    if cd_count <= local_count:
        return

    logger.info(
        "Write-back: ChatDaddy has %d messages, local has %d — persisting delta",
        cd_count, local_count,
    )

    # Convert ChatDaddy messages to CRM format
    crm_messages = [
        ConversationMessage(
            role="user" if not msg.get("fromMe") else "assistant",
            content=msg.get("text", ""),
            timestamp=int(msg.get("timestamp", 0)),
            message_id=msg.get("id", ""),
        )
        for msg in cd_history
        if msg.get("text")  # skip media-only messages
    ]

    if crm_user:
        # Merge into existing user
        await crm.append_history(chat_id, crm_messages)
    else:
        # Bootstrap new user from ChatDaddy history
        await crm.create_user_with_history(chat_id, crm_messages)

    logger.info("Write-back complete: %d messages persisted", len(crm_messages))
```

### Updated `enrich_webhook` with Write-Back

```python
async def enrich_webhook(
    ctx: WebhookContext,
    crm: CRMRepo,
    cd_client: ChatDaddyClient,
    *,
    write_back: bool = True,    # toggle via CHATDADDY_HISTORY_WRITE_BACK env var
) -> EnrichedContext:
    ...
    # After gather():
    if write_back and cd_ok and cd_history:
        asyncio.create_task(
            _write_back_if_needed(crm, crm_user, cd_history, ctx.chat_id)
        )
        # Fire-and-forget: don't await — write-back runs in background,
        # doesn't block the current turn's pipeline

    merged = _merge(...)
    return EnrichedContext(...)
```

**Key design choices:**
- Write-back is **fire-and-forget** (`create_task`, not awaited) — never adds latency to the current turn
- Only writes back when ChatDaddy has more than local — no redundant writes
- Skips media-only messages (no text = nothing useful to persist)
- Controlled by `CHATDADDY_HISTORY_WRITE_BACK=true` (default: true)

### Additional Config

```bash
CHATDADDY_HISTORY_WRITE_BACK=true       # default: true — persist ChatDaddy history to CRM
```

---

## Open Questions

| # | Question | Decision |
|---|----------|----------|
| Q1 | Should we write ChatDaddy history back to local CRM on first pull? | ✅ Yes — fire-and-forget write-back, see section above |
| Q2 | What's the right `count` for history? 20 or more for long-running chats? | Default 20, config |
| Q3 | Should we cache ChatDaddy history per chat_id to avoid repeated calls? | Out of scope v1 |
| Q4 | For group chats, `chat_id` is the group JID — does ChatDaddy return full group history? | Need to verify |
