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

## Session — 2026-06-03
What happened: Built group chat support for Jessica. She now listens silently in groups and only replies when @-mentioned or her name is used.

Decisions:
- **Group CRM key**: `g_<sender_lid>` (per-person, not per-group) — each member gets own record
- **Mention detection**: mentionedJids JID match → quote-reply → @<digits> → @<name> → bare name (word boundary for ASCII, substring for CJK)
- **Bare name added** (linter update): ChatDaddy confirmed non-WABA accounts don't deliver mentionedJids — so "jessica你好" with no @ must also trigger REPLY. Already updated in group_gate.py.
- **Bot JID = 85252417448** — same number as ORDER_WHATSAPP (clinic uses one WA number for both). Wired into render.yaml as JESSICA_BOT_JID.
- **JESSICA_BOT_NAMES** defaulted to "Jessica,jessica,Jessica姐" in render.yaml
- Silent listen path: keyword-scan pain_points + capture sender_name + append to conversation_history. Zero LLM cost.

Still open:
- Group CRM records (g_<lid>) and DM records (phone) won't auto-link if same person uses both. Acceptable for now.
- Haven't tested in a real group yet — user should add Jessica to a test group and @-mention her
- Auto-deploy still broken — manual deploy via Render API as workaround
- Postgres free expires 2026-06-20 — upgrade before launch

## Session — 2026-06-03

### What happened
Heavy ship day across voice, conversation quality, group chat, infra, and a prod routing bug. Started from "MiniMax TTS still there?" → shipped voice-out; pivoted to convo/UX hardening via real dry-runs; debugged group chat end-to-end with raw webhook capture; user upgraded web service to Starter; closed with a prod 鬼打墙 routing fix found from a live trace.

### Shipped (11 commits, all live on prod)
- **Voice-out (MiniMax)** `e7c46f0` — `src/media/tts.py`, match-modality (only voice-reply when inbound was voice), `Cantonese_KindWoman`, atomic cache write, task-cancel guard. 30 tests.
- **Planner JSON escape fix** `e136625` — bd09d9f's inferred_patterns example had unescaped `{}` → str.format KeyError → apology on EVERY turn for ~2 days. Added test_prompt_template_render.py forcing function.
- **4 convo/UX fixes** `f71ad49` — found via live persona dry-run:
  - One-question rule (was stacking 3 questions/turn)
  - Bubble restraint (was maxing 5 bubbles every turn)
  - Acupoint media gating (faq_agent only attaches images when USER asks 穴位/按摩 — was scanning card body, pushing 6 images unprompted)
  - Forward motion (concrete next step on "點幫我", not fluff)
  - Before/after dry-run proved all 4 +辨證 surfaces naturally + converts to pitch
- **Group chat** `a456b41`+`f149e2d`+`9adfa93` — reply when name-addressed, listen+absorb CRM otherwise.
  - Fixed LISTEN crash (ConversationMessage built with text=/timestamp= but model is content=/at=datetime)
  - Set JESSICA_BOT_JID=85252417448 + names on live service
  - **KEY FINDING via /admin/webhooks/recent raw capture**: ChatDaddy sends NO mentionedJids on non-WABA — native @-tags arrive as plain text. So matcher now accepts bare name ("hi jessica" not just "@jessica"). ASCII word-boundary, CJK substring.
- **鬼打墙 routing fix** `adeaf9b` — prod trace showed "今天有什么汤水介绍" → appointment (pushed 視診), looped. Root: `_APPOINTMENT_INTENT_KEYWORDS` had bare time words 今日/今天/聽日/明天/幾點/幾時可以. Removed all. Tightened 地址→診所地址 (delivery address ≠ clinic q). 6 regression tests.
- **version-update-showcase.html** — stakeholder summary (voice/convo/group/reliability + DB deadline note)

### Infra
- **Web service: free → Starter ($7)** — user paid. No more spin-down → webhooks reliable. render.yaml updated for parity (`d192294`).
- Tests: 511 → 620 passing.

### Still open / next
- ⚠️ **Postgres STILL FREE — deletes itself 2026-06-20 (17 days)**. The $7 was web service ONLY. DB is separate paid item. HARD DEADLINE — data loss if not upgraded. User aware, handling separately (or wants me to pull upgrade options).
- Group trade-off shipped: name-about-her ("jessica好靚") also triggers reply. Acceptable for consult group; switch to always-reply-whitelisted-groups if noisy.
- Render auto-deploy webhook still broken — manual deploy via API (render CLI key in ~/.render/cli.yaml, SVC=srv-d879lsmq1p3s73av6f80, owner tea-cumb3f5umphs73ehbo30).
- TTS_ENABLED=true on prod, MINIMAX_* shared with dr-baba quota — watch usage.
- Advisory self-critique guard (medical prescriptive red-line) — still not built, flagged earlier.

### Method notes (what worked)
- **persona_dry_run.py is gold** — found 4 convo issues zero unit tests caught; ~$0.25/run. User trusts real replies > tests.
- **/admin/webhooks/recent raw capture** decisively solved the group mystery — read ground truth, don't theorize.
- **Live trace fetch** (`/trace/<id>` on prod) showed exact planner routing for the 鬼打墙 bug. Traces list at `/trace`.
- Render deploy poll pattern: trigger via API, until-loop on status==live, then /health.

### Tonal
- User is decisive + action-oriented ("push", "do all in parallel", "b"). Ships fast, tests on real WhatsApp, sends screenshots of failures with sharp diagnosis ("鬼打墙", "unknown contact").
