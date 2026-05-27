# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## 1. Project Identity

**TCM-Jessica** is a WhatsApp-native TCM (Traditional Chinese Medicine) wellness sales & care agent for **心宜中醫 (Care Plus)** clinic. Jessica is a warm, gentle, conversational character — *not* a doctor, but a knowledgeable guide who helps users understand their 體質 (constitution), recommends 湯水 (herbal soups) and 藥膏 (ointments), and books clinic appointments.

- Language: **HK Cantonese 口語** only — never 書面語, never Mandarin phrasing.
- Tone: gentle, warm, human, slightly playful. NOT clinical, NOT pushy.
- Customer: HK consumers using WhatsApp, mixed ages, mostly health-curious / lightly symptomatic.
- Sales channel: WhatsApp via ChatDaddy IM API. Order link: `wa.me/85252417448`.

### Why a Standalone Project (and not part of dr-baba-agent)

Jessica was previously embedded inside `dr-baba-agent` as one of 50 tenant configs. We split her out because:

1. **Observability** — inside dr-baba-agent, Jessica's traces are mixed with 47 cancer pipelines. We can't cleanly see: "for this user, which agent fired, which tool ran, which card was read, what the final reply was." This project's #1 architectural goal is **per-turn step-level traceability**.
2. **Different architecture** — Dr. Baba is a single card-driven retrieval pipeline. Jessica is a **multi-agent orchestration** (Planner → Specialists → Writer) with **parallel specialist calls**. Trying to retrofit that into Dr. Baba's pipeline was creating coupling debt.
3. **Independent deployment** — 心宜中醫 should be able to ship Jessica without coordinating with cancer education releases.

What we **share** with `dr-baba-agent` (ported, then evolved independently):
- ChatDaddy WhatsApp client + auth flow + bubble-split logic
- Message buffer / merge logic (combining rapid-fire user messages before responding)
- TCM knowledge base cards (~30 cards: soups, constitution, FAQ)
- Paid product catalog (10 soups + 3 ointments from 心宜中醫)

Reference legacy code in `src/sales_legacy/` and `docs/legacy/` — **do not import from these**, they are read-only references during the rewrite.

---

## 2. Architecture (Big Picture)

```
                          WhatsApp (ChatDaddy IM API)
                                    │
                                    ▼
                       ┌────────────────────────┐
                       │  Inbound Gateway       │  poller + webhook
                       │  - dedup               │
                       │  - blocklist           │
                       │  - media intake        │
                       └────────────┬───────────┘
                                    │
                                    ▼
                       ┌────────────────────────┐
                       │  Buffer & Merge        │  wait window for
                       │  (per-chat queue)      │  rapid-fire msgs
                       └────────────┬───────────┘
                                    │
                                    ▼
                       ┌────────────────────────┐
                       │  CRM Read              │  load user state
                       │  - status, age, loc    │  + conversation
                       │  - history, notes      │    history window
                       └────────────┬───────────┘
                                    │
                                    ▼
                       ┌────────────────────────┐
                       │  PLANNER AGENT         │  decides:
                       │  inputs: CRM + msg     │  which specialist(s)
                       │  output: routing plan  │  + can fan out 2 in
                       │                        │    parallel
                       └────┬───────────────────┘
                            │
                ┌───────────┼───────────┬──────────────┬───────────────┐
                ▼           ▼           ▼              ▼               ▼
        ┌─────────────┐ ┌────────┐ ┌─────────┐ ┌──────────────┐ ┌────────────┐
        │ Greeting/   │ │  FAQ   │ │  Sales  │ │ TCM Constit. │ │ Appointment│
        │ Others      │ │ Agent  │ │  Agent  │ │  Agent       │ │  Agent     │
        │             │ │        │ │         │ │ (9 體質)     │ │            │
        │ - no tools  │ │ - KB   │ │ - paid  │ │ - tongue img │ │ - clinic   │
        │ - chit-chat │ │   search│ │   prods │ │ - 4 MCQs     │ │   match    │
        │             │ │ - cards │ │ - pitch │ │ - 湯水推薦   │ │ - slots    │
        └─────────────┘ └────────┘ └─────────┘ └──────────────┘ └────────────┘
                │           │          │              │               │
                └───────────┴──────────┴──────────────┴───────────────┘
                                    │
                                    ▼
                       ┌────────────────────────┐
                       │  FINAL WRITER AGENT    │  composes 1 final
                       │  - merges all outputs  │  reply, splits into
                       │  - HK Canto polish     │  bubble messages
                       │  - bubble split        │
                       └────────────┬───────────┘
                                    │
                                    ▼
                       ┌────────────────────────┐
                       │  CRM Write + Trace     │  persist state +
                       │  Outbound Send         │  full step trace
                       └────────────┬───────────┘
                                    │
                                    ▼
                          User WhatsApp (bubbles)
```

### Load-Bearing Invariants (Do Not Break)

1. **Every turn must produce a complete trace** — Planner decision, specialist calls (inputs + outputs + tools used + KB cards read), Writer composition, final bubbles sent. Stored per `(user_id, turn_id)`. If a feature breaks tracing, the feature is wrong.
2. **Planner is the ONLY agent that decides routing** — Specialists do not call other specialists. They return structured output and stop.
3. **Final Writer is the ONLY agent that user-facing text passes through** — Specialists never write user-facing copy. They return structured intent/content; the Writer turns it into 廣東話口語 bubbles.
4. **Knowledge access is card-driven** — FAQ + Constitution + Sales agents read from JSON cards in `data/knowledge_base/` and `data/products/`. No hallucinated TCM content. If no card matches, the agent says so honestly to the Writer.
5. **CRM is the single source of user state truth** — Specialists do not maintain their own user memory. Read from CRM at turn start, write back at turn end.

---

## 3. Components

### 3.1 Inbound Gateway (`src/whatsapp/`)
Ported from `dr-baba-agent/src/whatsapp/`. Handles:
- ChatDaddy IM API auth (apit_ token OR refresh-token flow, refresh every 50 min)
- Webhook receiver + dedup
- Polling fallback (when ChatDaddy event service stalls)
- Media download (tongue photos, voice notes)
- Blocklist (per-phone opt-out)

### 3.2 Buffer & Merge (`src/whatsapp/buffer.py`)
Ported from `dr-baba-agent`. When a user fires 3 messages in 4 seconds, we wait ~3-5s after the last message before invoking the Planner — otherwise we'd respond to fragment 1 while fragments 2 and 3 are still arriving. See `dr-baba-agent/src/whatsapp/router.py::_enqueue_for_merge`.

### 3.3 CRM (`src/crm/`)
**This is new — Dr. Baba does not have a real CRM.** Required fields per user:

| Field | Type | Source |
|-------|------|--------|
| `phone` | string | WhatsApp |
| `name` | string | extracted or asked |
| `status` | enum | `new` / `qualified` / `constitution_done` / `bought` / `booked` / `churned` / `opted_out` |
| `age` | int | asked when relevant |
| `location` / `district` | string | asked at appointment stage |
| `constitution` | enum (9 體質) | set by Constitution Agent |
| `pain_points` | list | extracted from conversation |
| `products_pitched` | list | what Sales Agent has shown |
| `products_purchased` | list | confirmed orders |
| `appointments` | list | booked slots (separate table, joined on read) |
| `notes` | text | freeform — written by memory consolidator (§3.8) + agents |
| `conversation_history` | list[message] | rolling window (last 20 turns, full log in `messages` table) |
| `tags` | list[string] | custom labels |
| `temp_state` | dict | cross-turn flow state owned by specialists (e.g. `constitution_q_index`, `awaiting_delivery_address`, `last_consolidated_at`) |
| `last_period_start` | date \| None | menstrual cycle tracking (optional, female users) |
| `cycle_length_days` | int | default 28; drives 月事陪伴 broadcast |

Storage: **PostgreSQL** in production (Render free tier, 1GB, persistent). SQLite for local dev. `CRMRepo` (aiosqlite) and `CRMRepoPG` (asyncpg) implement the same async surface — `repo_factory.py` picks the driver based on `DATABASE_URL`.

### 3.4 Planner Agent (`src/agents/planner.py`)

The Planner does **three jobs in one LLM call** (gpt-5.4-mini):

1. **Route** to 1-2 specialists. Two is the cap (more = too messy for Writer).
2. **Rephrase** the user message into clean HK 廣東話 (`rephrased_query`).
   Strips filler / mixed scripts / typos so downstream specialists work
   on a normalised input. Passed via `SpecialistInput.rephrased_query`;
   specialists pick it up via the `effective_query` property.
3. **Extract** health complaints (`extracted_pain_points: list[str]`) as
   NER tags. Multi-tag in single turn supported ("頭痛+失眠+腰痛" → 3 tags),
   plus catch-up sweep of last 5 turns for any complaints CRM missed.

Output: `PlannerDecision { specialists, mode, reasoning, notes_for_writer,
proactive_hint, rephrased_query, extracted_pain_points }`.

**Why one LLM call**: gpt-5.4-mini can handle routing + rephrase + NER
together; splitting into separate calls would double latency + cost for
no quality gain.

Rule fast-paths bypass the LLM entirely for deterministic cases
(tongue photo, wa.me order, farewell, MCQ answers, simple greetings,
health complaints, etc.). See §3.5 table.

### 3.5 Specialist Agents (`src/agents/`)

| Agent | Tools | Knowledge | Output Schema |
|-------|-------|-----------|---------------|
| `greeting_agent.py` | none | none | `{ tone: "warm", topic: str, suggested_followup: str? }` |
| `casual_agent.py` | none | none | Empathic chit-chat for returning users + non-medical topics. Driven by Planner's `notes_for_writer` for proactive follow-up. |
| `faq_agent.py` | `search_kb`, `read_card` | `data/knowledge_base/` (52 cards: soups, constitution, faq, acupressure) — vector + keyword hybrid via `tools/kb_search.py` | `{ answer_facts: list, cards_used: list[card_id], confidence: float }` |
| `sales_agent.py` | `recommend_product`, `share_product_image`, `share_order_link` | `data/products/` | `{ products_to_pitch: [{ name, price_display, indications, constitution_match, image_url }], pitch_angle, urgency }` — payload **MUST include 功效 (indications) + image** for every product mentioned (Writer enforces this) |
| `constitution_agent.py` | `analyze_tongue` (vision, gpt-5.4-mini), `ask_constitution_question`, `declare_constitution` | `data/knowledge_base/constitution/` | 4-phase state machine: asking_tongue → analyzing_tongue → asking_mcq (4 MCQs) → declaring. On declare, **persists a TongueRecord** to `user.tongue_photos` + clears `constitution_*` temp_state. |
| `appointment_agent.py` | `match_clinic_by_location`, `propose_slot`, `confirm_booking` | `data/clinics/clinics.json` | `{ phase: "asking_mode" \| "asking_location" \| "proposing_slot" \| "confirming", payload: ... }`. Auto-defaults to `in_person` after asking_mode once + user shows scheduling intent. |
| `tongue_progress_agent.py` | vision compare (gpt-5.4-mini), diff structured fields, narrative LLM call | uses prior `TongueRecord` from CRM | `{ phase: "compared" \| "first_photo", current_analysis, previous_record, changes, overall_direction, narrative_zh }`. Emits `tongue_photos_append` diff so pipeline persists the new record. |

**Planner-level rule fast-paths** (bypass LLM, deterministic):

| Rule | File | Effect |
|------|------|--------|
| wa.me order | `sales_agent._ORDER_RE` | "想訂【...HK$...】" → SALES (parse + collect address) |
| Awaiting delivery address | `_TS_AWAITING_ADDRESS` | mid-order-flow → SALES |
| Tongue photo + prior history | `planner.py` | media + `constitution!=UNKNOWN` + `len(tongue_photos)>=1` → TONGUE_PROGRESS (else CONSTITUTION) |
| Mid-constitution flow | `planner.py:_looks_like_mcq_answer` | findings present + UNKNOWN constitution + msg looks like A/B/C/D → CONSTITUTION (escape valve: non-MCQ msg falls through) |
| Farewell detection | `planner.py:_is_farewell` | tail-position match on 拜拜/bye/多謝/晚安/etc. → GREETING + CRM-aware closing summary |
| Returning user greeting | `planner.py:_build_returning_hint` | "hi" + CRM has context → CASUAL + proactive follow-up referencing prior pain_points |
| Health complaint shortcut | `agents/acute_pain.py:detect_health_complaint` | 頭痛/失眠/腰痛/etc. + returning user → FAQ + CASUAL (KB owns acupoint content, NO hardcoded mapping) |
| Emotion detection (七情) | `agents/emotion.py:detect_emotion` | Stress/anger/sadness → 七情 → 五臟 mapping → CASUAL + FAQ. Wins over health-complaint rule when both fire. |
| Symptom memory | `agents/symptom_memory.py` | Same symptom mentioned ≥3 times in history → CASUAL + FAQ with caring tone |

### 3.6 Final Writer Agent (`src/agents/writer.py`)
- Input: CRM context + user message + ALL specialist outputs
- Output: list of bubble messages (target ~150 chars, max 250, see `dr-baba-agent/src/whatsapp/client.py` `BUBBLE_TARGET`)
- Responsible for: tone consistency (Jessica voice), HK 口語 polish, removing redundancy when 2 specialists overlap, inserting media (images) at the right bubble boundaries.
- **NEVER** invents medical/product facts. Only re-narrates what specialists provided.

### 3.7 Orchestrator (`src/orchestrator/`)
The conductor — runs the full pipeline per turn:
1. CRM load
2. Planner call (route + rephrase + extract — see §3.4)
3. Fan-out specialist calls (sequential or parallel per Planner decision).
   Each receives `SpecialistInput.rephrased_query` for cleaner downstream
   LLM/KB work.
4. Writer call (gpt-5.4-mini composes 5-bubble reply; adaptive cap to 8
   bubbles when payload has ≥2 products)
5. CRM write + trace persist:
   - Apply specialist diffs (`_apply_specialist_diffs`)
   - **Two-rail pain_points extraction**: use `decision.extracted_pain_points`
     if present, else fall back to `detect_all_health_complaints(text)`
     keyword scan. Prevents CRM going empty when LLM omits the field OR
     when a rule fast-path bypassed the LLM entirely.
   - Persist new appointments + new tongue_photos via `_append` convention
6. **Background: fire memory consolidator if ≥15 new messages** (§3.8) —
   `asyncio.create_task`, zero latency to user
7. Send bubbles via WhatsApp client

Every step emits a structured trace event. See §5.

### 3.8 Memory Consolidator (`src/agents/memory_consolidator.py`)

Jessica's rolling history is 20 messages. Anything older is in the DB but invisible to agents. The consolidator solves this:

- **Trigger:** post-turn background task fires when `total_messages > 20` (first run) or `≥15 messages since last_consolidated_at` (subsequent)
- **Model:** gpt-4o-mini (cheap, ~\$0.0003 / call)
- **Output:** updated `user.notes` containing extracted insights (health issues, emotional state, product reactions, personal details)
- **Failure mode:** silent — never crashes the server. Logs warning + skips.
- **State:** `last_consolidated_at` lives in `user.temp_state` to avoid re-summarising the same messages.

Next time the user returns, `notes` is loaded with the rest of the User snapshot → Planner / Writer see the long-term memory.

### 3.9 Broadcaster (`src/broadcaster/`)

Proactive outreach — 10 channels, all sharing one 6h asyncio loop in `scheduler.py`. Per-user weekly cap enforced via `user_broadcasts` table (`get_broadcast_count_this_week`).

| Channel | Frequency | Trigger | Composer |
|---------|-----------|---------|----------|
| Weather care | event-driven | heatwave / cold front detected | `weather_service.py` + `composer.py` |
| Solar terms (節氣) | per 節氣 (24/yr) | calendar | `solar_terms.py` |
| Constitution recheck | quarterly | user went quiet 90 days | `composer.py` |
| Purchase follow-up | one-shot per purchase | 3 days post-buy | `composer.py` |
| Weekly tea (DIY 茶飲) | weekly | by constitution | `composer.py` |
| Weekly acupressure | weekly | by health-tag | `composer.py` |
| Appointment prep | 48h before appt | upcoming confirmed | `composer.py` |
| Monthly food therapy | monthly | by month + constitution | `composer.py` |
| Weekly sleep tip | weekly | by constitution | `composer.py` |
| 月事陪伴 (menstrual care) | weekly | `last_period_start` set | `menstrual_care.py` |

All gated by `_within_send_window()` (HKT 09:00-21:00) and `is_blocked(phone)`.

---

## 4. Data

```
data/
├── knowledge_base/        # Read-only TCM education content
│   ├── soups/             # 食療湯水 cards
│   ├── constitution/      # 九體質 + 氣虛/濕熱/etc.
│   ├── faq/               # acupressure, beauty, digestion, etc.
│   └── MANIFEST.md
├── products/              # Paid catalog (心宜中醫)
│   ├── soups/             # 10 paid soups
│   ├── ointments/         # 3 paid ointments
│   ├── product_catalog.json
│   └── PRODUCTS_INDEX.md
├── clinics/
│   └── clinics.json       # 心宜中醫 branches: name, address, district, hours, phone
└── media/
    ├── greetings/         # Greeting/intro media
    └── products/          # Product photos (referenced by product cards)
```

Card schema (knowledge_base + products) follows `dr-baba-agent` convention: `metadata`, `overview`, `core_content`, `execution_logic`, `references`. **Do not invent a new schema** — we want to keep card portability with Dr. Baba so content edits can flow between projects.

---

## 5. Observability (Critical — This Is Why The Project Exists)

Every turn produces a **trace bundle** stored at `traces/<date>/<user_id>/<turn_id>.json`:

```json
{
  "turn_id": "...",
  "user_id": "...",
  "received_at": "...",
  "user_message": "...",
  "merged_from_fragments": ["msg_id_1", "msg_id_2"],
  "crm_snapshot": { ... },
  "planner": {
    "input_tokens": N, "output_tokens": N, "latency_ms": N,
    "decision": { "specialists": [...], "reasoning": "..." }
  },
  "specialists": [
    {
      "name": "constitution_agent",
      "input": { ... },
      "tools_called": [{ "name": "...", "args": {...}, "result": {...} }],
      "cards_read": ["tcm_constitution_assessment", ...],
      "output": { ... },
      "tokens": {...}, "latency_ms": N
    }
  ],
  "writer": {
    "input": { ... },
    "output_bubbles": ["...", "...", "..."],
    "tokens": {...}, "latency_ms": N
  },
  "send_log": [{ "bubble_idx": 0, "sent_at": "...", "wa_message_id": "..." }],
  "crm_diff": { "before": {...}, "after": {...} }
}
```

Also expose a **live trace viewer** (simple FastAPI + HTML) at `/trace/<turn_id>` so we can debug a single conversation without grepping JSON.

**If a feature breaks the trace format, fix the feature, not the trace.**

---

## 6. Stack

- **Language:** Python 3.11+ (3.14 in production via Render)
- **Web/API:** FastAPI (webhook + trace viewer + admin views)
- **LLM:** **gpt-5.4-mini** via OpenAI for all roles (Planner / Writer /
  Specialists / Vision). Migrated from gpt-4o-mini on 2026-05-26 (forced
  by deprecation deadline; gpt-5.4-mini is ~60% cheaper too). `src/llm.py`
  is an Anthropic-shaped facade — `LLMClient` wraps `AsyncOpenAI` so agents
  use `client.messages.create(...)` unchanged. `_uses_max_completion_tokens()`
  routes gpt-5.x / o-series to the new `max_completion_tokens` parameter
  (gpt-5 family rejects `max_tokens`).
- **Voice transcribe:** `gpt-4o-transcribe` (migrated from `gpt-4o-mini-transcribe`
  which retired 2026-06-01).
- **DB:** PostgreSQL in production (Render free, 1GB, persistent — **free
  tier expires 90 days after creation; current expiry 2026-06-20**).
  SQLite for local dev. Dispatched by `repo_factory.py` based on `DATABASE_URL`.
- **Vector search:** pgvector (Postgres extension) — indexed on startup if
  `DATABASE_URL` is Postgres. Hybrid KB search via `tools/vector_store.py`.
- **Schema migrations:** `CREATE TABLE IF NOT EXISTS` only creates new
  tables — does NOT add new columns to existing ones. To add a column:
  (1) extend the `User` model, (2) add to `_USER_COLUMN_MIGRATIONS` in
  `src/crm/repo.py`, (3) add to `_PG_USER_COLUMN_MIGRATIONS` in
  `src/crm/repo_pg.py`, (4) add to `EXPECTED_NEW_COLUMNS` in
  `tests/test_schema_migrations.py`. Step (4) is a forcing function that
  goes red if any of (1)-(3) is missed. **For Postgres, do NOT use
  `ALTER TABLE ADD COLUMN IF NOT EXISTS` — asyncpg 0.31 + Python 3.14
  hits a protocol bug. Use `information_schema` lookup + conditional ADD
  (see `_migrate_pg_user_columns`).**
- **Deployment:** Render (Singapore region, web Starter + Postgres free).
  **Auto-deploy webhook is currently broken** — push to main does not
  trigger deploy. Workaround: `POST /v1/services/{id}/deploys` via Render
  API. See `docs/DEPLOYMENT.md`.
- **Test:** pytest (523 passing as of 2026-05-26).

---

## 7. Commands

```bash
# Install
pip install -e .

# Run dev server
uvicorn src.web:app --reload --port 8000

# Run tests
pytest -q                                          # all (523 tests)
pytest tests/test_planner_rules.py -v              # one file
pytest tests/test_schema_migrations.py -v          # migration-path tests

# Run end-to-end persona dry-run (20-turn dialogue, ~$0.50 OpenAI cost)
python3 scripts/persona_dry_run.py                 # full 20 turns
python3 scripts/persona_dry_run.py --short         # first 5 turns only

# Targeted QA harnesses (each ~$1 OpenAI)
python3 scripts/qa_sales_flow.py                   # 6 sales scenarios
python3 scripts/qa_constitution_flow.py            # 5 constitution scenarios
python3 scripts/qa_conversation_flow.py            # 8 conversation scenarios

# Manually trigger Render deploy (workaround for broken webhook)
curl -s -X POST -H "Authorization: Bearer $RENDER_API_KEY" \
  "https://api.render.com/v1/services/srv-d879lsmq1p3s73av6f80/deploys" -d '{}'

# Reset a test user (wipes all CRM data for one phone)
python -c "import asyncio; from src.crm.repo import CRMRepo; \
  asyncio.run((lambda r: r.delete_all_for_phone('+85291234567'))(await CRMRepo.connect('data/jessica.db')))"
```

---

## 8. Agent-First Policy

Same hard triggers as `~/.claude/rules/common/agents.md`. Additionally for this project:

| Task | Required Agent |
|------|----------------|
| Designing the Planner routing logic | **architect** before code |
| Writing a new specialist agent | **planner** → **tdd-guide** (tests first) → **code-reviewer** |
| Touching the trace schema | **architect** (load-bearing — affects every turn) |
| Card schema changes in `data/` | **planner** + **code-reviewer** |
| WhatsApp send/auth changes | **security-reviewer** |
| Constitution Agent vision prompts | **architect** (model behavior is fragile) |
| Build / type errors | **build-error-resolver** immediately |

**Exception:** single content edit in one knowledge card JSON — direct edit is correct.

---

## 9. Migration Notes (from dr-baba-agent)

| Component | Status | Notes |
|-----------|--------|-------|
| ChatDaddy WhatsApp client | **Port as-is** | Already battle-tested. Keep bubble timing, auth refresh, polling fallback. |
| Buffer / merge | **Port as-is** | Already proven. |
| TCM knowledge cards | **Copy and freeze** | Card content is good. Re-index/restructure only if FAQ retrieval underperforms. |
| Paid product cards | **Copy and freeze** | 10 soups + 3 ointments from 心宜中醫. |
| Old sales state machine (`src/sales/flow_engine.py`, `pitch_router.py`, etc.) | **Reference only** | New Planner+Specialist architecture replaces the state machine. Keep in `src/sales_legacy/` to mine for prompt language, pitch angles, intent detection rules. |
| `sales_prompt.py` (Jessica voice) | **Mine for tone** | Excellent HK Canto voice work — port lines into `writer_agent.py` and `greeting_agent.py` prompts. |
| Dr. Baba retrieval pipeline | **Do not port** | Built for a 3,800-card medical KB with high accuracy needs. Jessica's ~30 cards don't need vector search at MVP. |
| CRM | **Build fresh** | Dr. Baba uses ad-hoc patient memory. Jessica needs structured CRM (see §3.3). |
| Observability/trace | **Build fresh** | Dr. Baba's logging is line-based and tenant-mixed. Jessica needs per-turn structured bundles. |

---

## 10. What Not To Do

- Do not import `from dr-baba-agent.*` — projects are independent.
- Do not let a Specialist write user-facing text. Specialists return structured data; Writer composes.
- Do not let the Planner skip the Writer. Even for a one-word "ok" the Writer normalizes the bubble.
- Do not hardcode product names, soup names, clinic addresses, or 體質 logic in Python — they live in `data/`.
- Do not hardcode KB content in Python (e.g. acupoint → symptom mappings).
  KB cards + `AcupointImageMap` own that. We tried and ripped it out on
  2026-05-26 — Python copies of KB drift out of sync with clinic edits.
- Do not bloat the Planner prompt with specialist-specific instructions. Specialists own their own prompts.
- Do not add a 6th specialist without explicit approval. The orchestration cost grows non-linearly.
- Do not add a new column to `User` model without updating
  `_USER_COLUMN_MIGRATIONS` (SQLite) + `_PG_USER_COLUMN_MIGRATIONS` (PG)
  + `EXPECTED_NEW_COLUMNS` (test). `CREATE TABLE IF NOT EXISTS` is a
  trap — existing tables are NOT modified. Caused a prod-down on 2026-05-26.
- Do not use `ALTER TABLE ADD COLUMN IF NOT EXISTS` on Postgres via
  asyncpg 0.31 + Python 3.14 — protocol bug. Use information_schema
  lookup + conditional ADD instead.
- Do not pass `max_tokens` to gpt-5.x / o-series — they require
  `max_completion_tokens`. `_uses_max_completion_tokens()` in `src/llm.py`
  handles this; new direct OpenAI calls should use the facade.
- Do not skip running `scripts/persona_dry_run.py` after any change to
  the Planner, Writer, or a Specialist prompt. The dry-run found 4
  bugs in the same day that unit tests had passed — it tests against
  real LLM, with realistic conversation state.
