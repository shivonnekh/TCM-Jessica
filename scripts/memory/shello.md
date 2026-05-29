# Shello Session Memory — TCM-Jessica

## Session — 2026-05-26

### What happened
Massive day. Started on production bug triage (CRM `list_phones_for_upcoming_appointments` missing), expanded into 15 commits across model migration, query understanding, sales payload enrichment, vision-based tongue progress tracking, full QA agent team sweep, and ended with an emergency prod-down fix for a Postgres column migration bug I caused.

### Major work shipped (15+ commits)
- **CRM**: `list_phones_for_upcoming_appointments` (Postgres + SQLite), idempotent column migrations
- **Memory consolidator**: auto-summary across sessions (gpt-5.4-mini, ~$0.0003/run)
- **Farewell summary** with CRM-aware closing (constitution + pain_points + appointments)
- **Returning user** proactive follow-up using prior pain_points
- **Tongue progress agent** — vision before/after comparison + image attach
- **Acupoint routing** — initially hardcoded map, then refactored to pure KB vector search (user pushed back on hardcoding)
- **Sales payload enrichment** — name + price + 功效 (indications) + image MANDATORY for every product mention
- **Phase 1 model migration** — gpt-4o-mini → gpt-5.4-mini (forced by deprecation deadline)
- **Phase 2 Planner query understanding** — rephrase + extracted_pain_points NER in single LLM call
- **QA agent team**: 3 parallel agents (Sales/Constitution/Conversation) — found + fixed 7 real bugs, added 17 tests, total 511 passing

### Critical bugs found + fixed today
1. `max_completion_tokens` API change for gpt-5.x — every LLM call was failing
2. Constitution agent persisting findings on rejected tongue → infinite loop trap
3. Mid-constitution rule had no escape — non-MCQ messages got force-routed
4. "OK 三點" misclassified as farewell, breaking appointment confirmation
5. Multi-clause farewell (>15 chars) missed by length gate
6. Writer `MAX_BUBBLES=5` silently dropping 3rd product (the screenshot bug)
7. Sales `writer_hint` saying `方向:` instead of new `功效:` template
8. ConstitutionAgent never persisted TongueRecord → tongue progress bootstrap impossible
9. Multi-symptom turns only extracting first match → CRM lost subsequent complaints
10. Skin complaints never persisted to pain_points (skin keywords intentionally excluded)
11. Complaint+Emotion mix → complaint rule won, lost 七情/臟腑 framing
12. **PROD-DOWN**: `UndefinedColumnError: last_period_start` — `CREATE TABLE IF NOT EXISTS` doesn't add new columns to existing tables. Added ALTER TABLE ADD COLUMN IF NOT EXISTS.

### Decisions made
- **Stay on OpenAI** despite running parallel research on 6 providers (Anthropic / Grok / Kimi / DeepSeek / Gemini). gpt-5.4-mini at $0.75/$4.50 is cost/quality sweet spot for HK Canto + budget.
- **Vision on gpt-5.4-mini** not Gemini Pro — keeps single-provider stack, negligible cost diff at ~4 calls/user lifetime
- **Writer on gpt-5.4-mini** not Sonnet — cost ceiling, prompt engineering matters more than model tier
- **Postgres on free tier** until launch — expires 2026-06-20, user wants to wait
- **Don't push back on user UX intuitions** — they were right twice: hardcoded acupoint map was wrong (should be KB), Sales bare-pitch was broken (needs 功效 + 圖)

### Architecture observations worth remembering
- Planner now does 3 jobs in 1 LLM call (route + rephrase + NER) — clean design, gpt-4o handles it
- Two-rail extraction (LLM NER + keyword fallback) catches what LLM omits (gpt-5.4-mini has inconsistent extraction)
- Rule-based fast paths must propagate to NER fallback — easy to miss
- Schema migrations need ALTER TABLE for additive changes; CREATE TABLE IF NOT EXISTS is a trap

### Still open
- **Auto-deploy webhook broken** on Render since 2026-05-22 — needs dashboard intervention (manual deploy works via API as workaround)
- **Postgres free expires 2026-06-20** — upgrade to Starter ($7/mo) before launch or data lost
- **Testing gap**: no migration-path test for existing DBs (caused today's prod crash). Should add.
- **KB content gaps**: 三高 / 9 體質 deep dive / 情志 / 男性 / 中藥目錄 / 24 節氣 cards
- **Tongue progress monthly nudge** broadcast not built
- **Appointment district fallback** when user evasive (only `online_video` happy path tested)
- **Real-LLM end-to-end test for constitution** — happy path with valid tongue still untested in prod
- **Sales product cards** lack ingredients/材料 field — clinic team needs to fill

### Files touched (rough)
- `src/llm.py` (model split, max_completion_tokens fix)
- `src/llm_transcribe.py` (gpt-4o-transcribe migration)
- `src/agents/planner.py` (query understanding, multiple rule fixes)
- `src/agents/writer.py` (MAX_BUBBLES adaptive cap, 功效 template)
- `src/agents/sales_agent.py` (writer_hint + payload enrichment)
- `src/agents/constitution_agent.py` (persist TongueRecord, reset state)
- `src/agents/acute_pain.py` (rip hardcoded map, multi-symptom helper)
- `src/agents/memory_consolidator.py` (new)
- `src/agents/tongue_progress_agent.py` (new)
- `src/crm/repo.py` + `repo_pg.py` + `schema.sql` + `schema_pg.sql` (5 schema changes)
- `src/orchestrator/pipeline.py` (Phase 2 wiring, two-rail extraction)
- `scripts/persona_dry_run.py` + `qa_sales_flow.py` + `qa_constitution_flow.py` + `qa_conversation_flow.py` (new test harnesses)
- `docs/today-improvements-showcase.html` (client-facing showcase)
- `CLAUDE.md` (architecture update)

### Service URLs
- Prod: https://tcm-jessica.onrender.com
- Render service ID: `srv-d879lsmq1p3s73av6f80`
- Postgres ID: `dpg-d87ai33eo5us73duobj0-a` (free, expires 2026-06-20)

### Tonal notes for next session
- User trusts dry runs more than tests — they ask for "real run see real replies"
- User flags UX issues fast and accurately — listen carefully
- User runs the company; cost ceiling matters; quality not at all costs
- Auto-deploy issue not yet resolved — user has the dashboard, I don't

### Post-save addendum — 2026-05-26 late evening

- Prod-down fix `f234fc3` actually failed to deploy too (asyncpg + ALTER TABLE IF NOT EXISTS bug in Python 3.14 runtime — `AttributeError: NoneType has no attribute decode`)
- Wrote second fix `115805e`: moved PG column migration out of SQL into Python via `information_schema` lookup + conditional ADD COLUMN. Avoids the asyncpg protocol path entirely.
- Deploy `dep-d8arutjbc2fs73e50rc0` LIVE confirmed working.
- Lesson: asyncpg 0.31 + Python 3.14 has issues with DDL `IF NOT EXISTS` extensions. Use information_schema lookup instead.

## Session — 2026-05-29
What happened: Full day building WhatsApp poll button UX for MCQ constitution questions. Lots of back-and-forth on whether ChatDaddy poll votes can be read.
Decisions:
- Buttons infrastructure: fully wired (WriterOutput.buttons, _extract_buttons in pipeline, buttons on last bubble in router, send_message accepts buttons param)
- MCQ gets poll buttons (4 options = WhatsApp poll widget, not quick-reply buttons)
- Poll vote selection: CANNOT be read via webhook payload (pollReplyOptions always []) or REST API (poll.options has no vote counts). This is likely a WhatsApp E2E encryption limitation.
- Added /admin/webhooks/recent endpoint to read live webhook payloads
- Added WEBHOOK-RAW logger to capture raw POST body of poll vote events
- Updated webhook subscription to include message-update + message-insert
- fetch_poll_selection() implemented but consistently returns "" (no votes > 0 in REST API)
Still open:
- WEBHOOK-RAW log has NOT been captured yet with a vote on the new server (user hasn't voted since deploy at 06:51 HKT). Once they vote, check `render logs -r srv-d879lsmq1p3s73av6f80 | grep WEBHOOK-RAW` immediately.
- If WEBHOOK-RAW shows pollReplyOptions populated → update _extract_poll_selection() to read it
- If WEBHOOK-RAW shows empty → accept limitation, revert MCQ to plain ABCD text
- Appointment mode buttons (診所/電話) and post-pitch CTA buttons are ready to add (≤3 options = real quick-reply buttons, not polls)
