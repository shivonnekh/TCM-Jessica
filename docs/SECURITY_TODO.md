# Security & Code Quality Follow-Ups

Fixed in commit (security pass 1): webhook auth + SSRF allowlist + smoke-test gating + `_looks_complete` regression.

Remaining items from the 2026-05-21 security + code review pass.
Tracked here so they don't slip; not blocking dev / smoke tests, but
**must be addressed before live customer traffic.**

---

## HIGH — fix before production

### 1. Token leakage in `client.py` print statements
**Where:** `src/whatsapp/client.py:247, 272, 283, 287, 289, 293`
**Risk:** `print(resp.text[:300])` in `refresh_token()` may echo back the
submitted `refreshToken` if ChatDaddy's error body includes it. Same for
send_message error paths.
**Fix:** Replace all `print()` in `client.py` with `logger.debug(...)` and
strip any credential-shaped fields from error body previews before
logging (regex on `refreshToken|access_token|Bearer`).

### 2. `_PendingBuffer` direct mutation
**Where:** `src/whatsapp/router.py:200-207`
**Risk:** Latent — works under asyncio single-thread guarantee, breaks if
ever moved to thread-pool executor or refactored.
**Fix:** Convert `texts` / `attachments` to tuples; rebuild buffer
on each enqueue. Or document explicitly + add lock if model changes.

### 3. `_bg_task_refs` unbounded growth under adversarial load
**Where:** `src/whatsapp/router.py:143-151`
**Risk:** Attacker hammers webhook with unique phone numbers, each
spawning a flusher that lives up to 15s. At 100 req/s → ~1500 live
tasks holding `_PendingBuffer` instances.
**Fix:** Add `MAX_CONCURRENT_BUFFERS = 500` cap on `_merge_buffers`; on
overflow, reject with 429 or drop-oldest. Add `len(_bg_task_refs)` log
on each webhook receipt for ops visibility.

### 4. Dedup state in-memory only
**Where:** `src/whatsapp/router.py:86-102`
**Risk:** Process restart loses the dedup window. Poller records IDs
*before* awaiting `_process_turn` — if processing throws, message is
permanently dropped.
**Fix:** Move `_seen_ids` to a persistent store (SQLite write-through or
Redis SET with TTL). Move poller dedup-record AFTER successful
`_process_turn`.

---

## MEDIUM

### 5. Phone numbers logged in plaintext (PII / PDPO)
**Where:** `router.py:185, 212, 266, 284`; `poller.py:60, 144`;
`blocklist.py:195, 210, 138`
**Fix:** Wrap with `_redact(phone)` helper → returns `phone[-4:]`. Apply
to ALL log lines + diagnostic_capture output.

### 6. `diagnostic_capture.py` stores raw payloads with full PII
**Where:** `src/whatsapp/diagnostic_capture.py:46-47, 117-120`
**Risk:** If `/api/whatsapp/debug/raw-webhooks` endpoint is exposed
without auth, full PII dump of last 20 messages.
**Fix:** Either (a) only enable in dev `APP_ENV != production`, or (b)
redact `text` field from `raw` (keep `text_len` for debugging).

### 7. `BLOCKLIST_PATH` env not validated
**Where:** `src/whatsapp/blocklist.py:56`
**Risk:** Attacker controlling env vars can point at any file → silent
empty blocklist (fail-open, no one blocked).
**Fix:** Validate resolved path is under project root; reject otherwise.

### 8. `threading.Lock` mixed with asyncio
**Where:** `src/whatsapp/blocklist.py:58`
**Risk:** Blocks event loop during file I/O; deadlocks if ever called
from `run_in_executor`.
**Fix:** Replace with `asyncio.Lock` + `await`, move file writes to
`asyncio.to_thread`.

### 9. Smoke-test error response leaks exception
**Where:** `src/whatsapp/router.py:572-574`
**Fix:** Return generic `{"error": "pipeline error"}`, full exception to
logs only.

### 10. Flusher condition redundancy
**Where:** `src/whatsapp/router.py:209`
**Issue:** `if new_buffer and not buf.flusher_running` — when `new_buffer`
is True, `flusher_running` is always False. The reverse case (flusher
crashed without cleanup) is never handled.
**Fix:** Change to `if not buf.flusher_running:` alone.

---

## LOW

### 11. 25+ `print()` statements in production code paths
**Where:** `router.py:186/212/215/265/286`, `poller.py:60/70/144/163`, etc.
**Fix:** Convert to `logger.debug(...)` / `logger.info(...)`.

### 12. Magic numbers
**Where:** `router.py:167` — hardcoded `8` (min chars for "complete")
**Fix:** `WA_COMPLETE_MIN_CHARS = int(os.environ.get(..., "8"))`.

### 13. Test fragility (`_wait_for_flush`)
**Where:** `tests/test_whatsapp_buffer.py:111-118`
**Fix:** Add `await asyncio.sleep(0)` at end of poll loop.

---

## Tracking

When fixing an item, move it from this file to the commit message of the
fix, with a `Closes #<n>` style note.
