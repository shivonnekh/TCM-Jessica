"""QA harness — Sales + Product flow end-to-end.

Exercises 6 distinct sales paths in isolated SQLite DBs:

  1. 3-soup pitch (氣虛質 user asks「介紹下湯水」)
  2. wa.me order intake (「想訂【清心潤肺湯 HK$48】」)
  3. Delivery address collection (temp_state.order_awaiting_delivery=True)
  4. Ointment pitch (skin complaint)
  5. Pricing-only query (「邊款湯幾錢？」)
  6. Repeat ask with products already pitched

For each scenario, prints user input, planner decision, writer bubbles,
media_to_send URLs, and validates the new product-mention format:
   🍲 NAME — HK$XX
   功效：a、b、c

Run:
  python scripts/qa_sales_flow.py            # all 6 scenarios
  python scripts/qa_sales_flow.py --only 1   # just scenario 1

Cost: ~$1 OpenAI (6 short conversations, mostly LLM Planner + Writer).
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Quiet noisy libs — keep our QA output readable
logging.basicConfig(level=logging.WARNING)
for noisy in ("httpx", "openai", "urllib3"):
    logging.getLogger(noisy).setLevel(logging.ERROR)

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.agents.registry import build_specialist_registry  # noqa: E402
from src.crm.models import (  # noqa: E402
    Constitution,
    User,
    UserStatus,
)
from src.crm.repo import CRMRepo  # noqa: E402
from src.llm import LLMClient  # noqa: E402
from src.orchestrator.pipeline import JessicaPipeline  # noqa: E402
from src.tools.kb_index import KBIndex  # noqa: E402
from src.tools.kb_search import KBSearch  # noqa: E402
from src.trace.writer import TraceWriter  # noqa: E402

# Optional: load .env
try:
    from dotenv import load_dotenv  # type: ignore

    load_dotenv(REPO_ROOT / ".env")
except ImportError:
    pass


# -------------------------------------------------------------------
# Scenario configuration
# -------------------------------------------------------------------


@dataclass(frozen=True)
class Scenario:
    """One QA scenario — seeded user state + a sequence of turns."""

    idx: int
    name: str
    phone: str
    seed: dict[str, Any]  # fields to set on the seed user
    turns: tuple[tuple[str, str], ...]  # (label, message) — media not exercised here
    expectations: tuple[str, ...]  # human-readable expected behaviours


SCENARIOS: tuple[Scenario, ...] = (
    Scenario(
        idx=1,
        name="3-soup pitch (氣虛質 user asks for soups)",
        phone="+85291110001",
        seed={
            "status": UserStatus.CONSTITUTION_DONE,
            "constitution": Constitution.QIXU,
            "pain_points": ["失眠", "攰"],
        },
        turns=(
            ("Soup pitch ask", "介紹下湯水"),
        ),
        expectations=(
            "Sales specialist routed",
            "3 distinct paid soups pitched (each with name + price + 功效)",
            "media_to_send has 3 image URLs (one per soup)",
            "Writer announcement count == actual product bubble count",
        ),
    ),
    Scenario(
        idx=2,
        name="wa.me order intake (清心潤肺湯)",
        phone="+85291110002",
        seed={
            "status": UserStatus.QUALIFIED,
            "constitution": Constitution.YINXU,
        },
        turns=(
            ("wa.me order", "想訂【清心潤肺湯 HK$48】"),
        ),
        expectations=(
            "Sales routed",
            "intent=order_received in Sales payload",
            "Writer asks for delivery address",
            "user.status set to bought",
        ),
    ),
    Scenario(
        idx=3,
        name="Delivery address collection",
        phone="+85291110003",
        seed={
            "status": UserStatus.BOUGHT,
            "constitution": Constitution.YINXU,
            "products_purchased": ["soup_qingxin_runfei"],
            "temp_state": {
                "order_awaiting_delivery": True,
                "order_pending_product_id": "soup_qingxin_runfei",
                "order_pending_product_name": "清心潤肺湯",
            },
        },
        turns=(
            ("Address reply", "旺角彌敦道 123 號，陳大文，9876 5432"),
        ),
        expectations=(
            "Sales routed",
            "intent=delivery_address_received",
            "user.location saved, temp_state cleared",
            "district extracted as 旺角",
        ),
    ),
    Scenario(
        idx=4,
        name="Ointment pitch (skin complaint)",
        phone="+85291110004",
        seed={
            "status": UserStatus.QUALIFIED,
            "constitution": Constitution.SHIRE,
        },
        turns=(
            ("Skin complaint", "我皮膚痕"),
        ),
        expectations=(
            "Sales routed (ointment path)",
            "Products pitched are type=ointment, NOT soup",
            "Writer mentions 茶樹綠豆濕敏膏 / 蛋黃油乳液 / 止痕濕疹膏",
            "Each ointment has image attached",
        ),
    ),
    Scenario(
        idx=5,
        name="Pricing-only query",
        phone="+85291110005",
        seed={
            "status": UserStatus.QUALIFIED,
            "constitution": Constitution.QIXU,
        },
        turns=(
            ("Pricing ask", "邊款湯幾錢？"),
        ),
        expectations=(
            "Sales routed",
            "Multiple soups listed with prices",
            "Each item shows HK$XX",
        ),
    ),
    Scenario(
        idx=6,
        name="Repeat ask — DIFFERENT products this time",
        phone="+85291110006",
        seed={
            "status": UserStatus.CONSTITUTION_DONE,
            "constitution": Constitution.QIXU,
            "products_pitched": [
                "soup_qingxin_runfei",
                "soup_xinghua_an",
            ],
            "pain_points": ["失眠"],
        },
        turns=(
            ("Repeat ask", "仲有冇其他湯水？"),
        ),
        expectations=(
            "Sales routed",
            "New products surfaced — NOT the 2 already pitched",
            "No repeat of soup_qingxin_runfei or soup_xinghua_an",
        ),
    ),
)


# -------------------------------------------------------------------
# Format validation helpers
# -------------------------------------------------------------------


# 🍲 / 🌿 / 💊 emoji indicator for a product line. We accept any food/herb
# emoji at the start because the Writer chooses what feels natural.
_PRODUCT_EMOJIS = ("🍲", "🌿", "💊", "🧴", "🥣", "🍵")


def find_product_bubbles(bubbles: list[str]) -> list[str]:
    """Bubbles that look like a product mention.

    Heuristic: must contain a price tag (HK$XX or $XX). Pure intro bubbles
    with just a 🌿 emoji do NOT count as product mentions. This matches the
    real Writer template which always pairs product name + price.
    """
    out: list[str] = []
    for b in bubbles:
        has_price = bool(re.search(r"HK\$\d+|\$\d+", b))
        if has_price:
            out.append(b)
    return out


def validate_product_mention_format(bubble: str) -> dict[str, bool]:
    """Check a single product bubble against the new template:

       🍲 [name] — HK$XX
       功效：a、b、c
    """
    return {
        "has_emoji": any(e in bubble for e in _PRODUCT_EMOJIS),
        "has_price": bool(re.search(r"HK\$\d+|\$\d+", bubble)),
        "has_indications_label": "功效" in bubble or "適合" in bubble,
        "has_separator": "、" in bubble or "，" in bubble,
    }


_ANNOUNCE_COUNT_RE = re.compile(r"(\d+)\s*款")


def extract_announced_count(bubbles: list[str]) -> int | None:
    """If a bubble says 'N 款湯水', extract N. Returns None if no claim."""
    for b in bubbles:
        m = _ANNOUNCE_COUNT_RE.search(b)
        if m:
            n = int(m.group(1))
            # Filter out catalog facts like「10 款」or「3 款」(meta references)
            # by skipping if the bubble mentions「全部」/「我哋有」without
            # implying "今次/now pitching".
            if "今" in b or "我幫你揀" in b or "推薦" in b or "推介" in b:
                return n
            # Generic '今次揀' inference — N <= 5 most likely pitch claim
            if n <= 5:
                return n
    return None


# -------------------------------------------------------------------
# Scenario runner
# -------------------------------------------------------------------


async def seed_user(
    crm: CRMRepo, phone: str, seed: dict[str, Any]
) -> User:
    """Create the user, apply seed fields, save back, return snapshot."""
    user = await crm.get_or_create_user(phone)
    if seed:
        user = user.with_updates(**seed)
        await crm.save_user(user)
    return user


def print_scenario_header(s: Scenario) -> None:
    print()
    print("┏" + "━" * 78)
    print(f"┃  SCENARIO {s.idx}: {s.name}")
    print(f"┃  Phone: {s.phone}")
    if s.seed:
        seed_summary = ", ".join(
            f"{k}={v if not isinstance(v, dict) else '...'}" for k, v in s.seed.items()
        )
        print(f"┃  Seed:  {seed_summary[:120]}")
    print(f"┃  Expectations:")
    for exp in s.expectations:
        print(f"┃    - {exp}")
    print("┗" + "━" * 78)


def print_turn_result(label: str, msg: str, result: Any, bug_report: list[str]) -> None:
    trace = result.trace
    planner_out = trace.planner.output if trace.planner else {}
    specialists_used = planner_out.get("specialists", [])
    reasoning = planner_out.get("reasoning", "")[:80]

    print()
    print(f"┌─[{label}]" + "─" * (70 - len(label)))
    print(f"│ 👤 User: {msg}")
    print(f"│ 🧠 Plan: {specialists_used}  mode={planner_out.get('mode', '?')}")
    print(f"│        reason: {reasoning}")
    if planner_out.get("extracted_pain_points"):
        print(f"│ 🩺 Extracted: {planner_out['extracted_pain_points']}")

    bubbles = result.writer_output.bubbles
    for i, bubble in enumerate(bubbles, 1):
        prefix = "│ 💬 Bubble" if i == 1 else "│           "
        # Truncate to 200 chars per line so console stays readable
        b_display = bubble.replace("\n", " ⏎ ")
        if len(b_display) > 200:
            b_display = b_display[:200] + "..."
        print(f"{prefix} {i}: {b_display}")

    media = result.writer_output.media_to_send or []
    for m in media:
        url = (m.get("url") or "")[:90]
        idx = m.get("after_bubble_idx", "?")
        print(f"│ 📎 Media @bubble {idx}: {url}...")

    # ── Validation ───────────────────────────────────────────────────
    product_bubbles = find_product_bubbles(bubbles)
    announced = extract_announced_count(bubbles)

    # Specialist payload introspection — pull Sales output if present
    sales_payload: dict[str, Any] = {}
    for sp in trace.specialists:
        if sp.name == "sales":
            sales_payload = sp.output or {}
            break

    print(f"│ ✓ Sales bubbles found: {len(product_bubbles)} (of {len(bubbles)} total)")
    print(f"│ ✓ Announced count: {announced}")

    products_in_payload = (
        sales_payload.get("payload", {}).get("products_to_pitch", []) or []
    )
    print(f"│ ✓ Products in Sales payload: {len(products_in_payload)}")
    if products_in_payload:
        pids = [p.get("product_id") or "?" for p in products_in_payload]
        print(f"│   product_ids: {pids}")

    # Per-bubble format check
    for i, pb in enumerate(product_bubbles, 1):
        v = validate_product_mention_format(pb)
        ok = all(v.values())
        flag = "✓" if ok else "✗"
        if not ok:
            missing = [k for k, val in v.items() if not val]
            bug_report.append(
                f"  - Bubble #{i} missing: {missing}: {pb[:80]!r}"
            )
        print(f"│   {flag} bubble #{i} format: {v}")

    # Image presence check
    payload_image_urls = [
        p.get("image_url") for p in products_in_payload if p.get("image_url")
    ]
    media_urls = [m.get("url") for m in media if m.get("url")]
    missing_images: list[str] = []
    for url in payload_image_urls:
        if url not in media_urls:
            missing_images.append(url)
    if missing_images:
        bug_report.append(
            f"  - {len(missing_images)} product image(s) NOT in media_to_send"
        )
        for u in missing_images[:3]:
            print(f"│   ✗ Missing image: {u[:90]}")
    else:
        if payload_image_urls:
            print(f"│   ✓ All {len(payload_image_urls)} product images present")

    # Announce-vs-actual count check (the production bug)
    if announced is not None and len(product_bubbles) > 0:
        if announced > len(product_bubbles):
            bug_report.append(
                f"  - BUG: announced {announced} products, only {len(product_bubbles)} "
                f"product bubbles rendered"
            )
            print(
                f"│   ✗ COUNT MISMATCH: announced {announced}, rendered "
                f"{len(product_bubbles)}"
            )

    # Truncation heuristic — JSON parse on raw writer output failed AND
    # bubble count is suspiciously small. Pure punctuation-end checks were
    # too noisy (HK Canto bubbles often end in 啦/喇/㗎 which are valid).
    writer_out = trace.writer.output if trace.writer else {}
    raw_text = writer_out.get("raw_text") if isinstance(writer_out, dict) else None
    # Only flag if bubble ends mid-Chinese char or with an open bracket
    if bubbles:
        last = bubbles[-1].rstrip()
        if last.endswith(("，", ",", "(", "（", "「", "『", ":", "：")):
            bug_report.append(
                f"  - Final bubble ends mid-clause (possible truncation): {last[-40:]!r}"
            )
            print(f"│   ⚠ Final bubble cut mid-clause: ...{last[-40:]!r}")
    _ = raw_text  # quiet linter — placeholder for future raw inspection

    print(f"│ ⏱  {trace.total_latency_ms or 0}ms")
    print("└" + "─" * 70)


async def run_scenario(s: Scenario, pipeline: JessicaPipeline, crm: CRMRepo) -> list[str]:
    """Run one scenario. Returns list of bug-report lines."""
    bugs: list[str] = []
    print_scenario_header(s)

    # Seed
    await seed_user(crm, s.phone, s.seed)

    # Run turns
    for label, msg in s.turns:
        try:
            result = await pipeline.run_turn(
                phone=s.phone, user_message=msg, media_urls=[]
            )
        except Exception as exc:  # noqa: BLE001
            line = f"  - EXCEPTION during turn '{label}': {type(exc).__name__}: {exc}"
            bugs.append(line)
            print(f"│ ✗ {line}")
            continue
        print_turn_result(label, msg, result, bugs)

    # Final CRM check
    final = await crm.get_user(s.phone)
    if final is not None:
        print()
        print(f"   Final CRM: status={final.status.value}, "
              f"pitched={len(final.products_pitched)}, "
              f"purchased={len(final.products_purchased)}, "
              f"district={final.district or '-'}, "
              f"temp_state_keys={list(final.temp_state.keys())[:5]}")

    # Scenario-specific extra checks (CRM-level)
    if s.idx == 2:
        if final and final.status != UserStatus.BOUGHT:
            bugs.append(
                f"  - SCENARIO 2: expected status=bought after order, got "
                f"{final.status.value}"
            )
    if s.idx == 3:
        if final and not final.location:
            bugs.append("  - SCENARIO 3: location not saved after address reply")
        if final and final.temp_state.get("order_awaiting_delivery"):
            bugs.append(
                "  - SCENARIO 3: temp_state.order_awaiting_delivery still True "
                "after address reply"
            )
        if final and final.district != "旺角":
            bugs.append(
                f"  - SCENARIO 3: district expected 旺角, got {final.district!r}"
            )
    if s.idx == 4:
        # Skin pitch should include ointments. The 'skin' playbook category
        # legitimately includes soup_pengyu_jiedu (it's a 清熱解毒 soup that
        # helps skin internally), so we only flag if ZERO ointments appear.
        new_pitches = [
            pid
            for pid in (final.products_pitched if final else [])
            if pid not in (s.seed.get("products_pitched") or [])
        ]
        ointment_count = sum(1 for pid in new_pitches if pid.startswith("ointment_"))
        if ointment_count == 0:
            bugs.append(
                f"  - SCENARIO 4: expected at least one ointment in pitch, got {new_pitches}"
            )
    if s.idx == 6:
        already = set(s.seed.get("products_pitched") or [])
        new_pitches = [
            pid for pid in (final.products_pitched if final else []) if pid not in already
        ]
        repeats = [pid for pid in (final.products_pitched if final else []) if pid in already]
        if not new_pitches:
            bugs.append(
                "  - SCENARIO 6: no NEW products pitched after 仲有冇其他 — "
                "repeat ask did not surface alternatives"
            )
        # Sanity: pitched list shouldn't grow with dup ids (de-dup is enforced
        # by pipeline._apply_specialist_diffs)
        if final and len(final.products_pitched) != len(set(final.products_pitched)):
            bugs.append("  - SCENARIO 6: products_pitched has duplicates")
        print(f"   New pitches in S6: {new_pitches}")

    return bugs


# -------------------------------------------------------------------
# Main
# -------------------------------------------------------------------


async def main(only: int | None = None) -> None:
    client = LLMClient()
    kb_index = KBIndex.load()
    kb_search = KBSearch(kb_index, vector_store=None, embedder=None)
    trace_writer = TraceWriter(str(REPO_ROOT / "traces_qa"))
    specialists = build_specialist_registry(client, kb_search=kb_search)

    all_bugs: list[tuple[Scenario, list[str]]] = []

    print()
    print("=" * 80)
    print("🔎  QA HARNESS — SALES + PRODUCT FLOW")
    print(f"     Scenarios: {len(SCENARIOS) if only is None else 1}")
    print("=" * 80)

    for s in SCENARIOS:
        if only is not None and s.idx != only:
            continue

        # Fresh SQLite per scenario — total isolation
        db_path = Path(f"/tmp/qa_sales_{s.idx}.db")
        if db_path.exists():
            db_path.unlink()
        crm = await CRMRepo.connect(db_path)

        pipeline = JessicaPipeline(
            crm=crm,
            trace_writer=trace_writer,
            client=client,
            specialists=specialists,
        )

        bugs = await run_scenario(s, pipeline, crm)
        all_bugs.append((s, bugs))

        await crm.close()

    # ── Summary ──────────────────────────────────────────────────────
    print()
    print("=" * 80)
    print("📊  QA SUMMARY")
    print("=" * 80)
    total_bugs = sum(len(b) for _, b in all_bugs)
    for s, bugs in all_bugs:
        if bugs:
            print(f"\n  Scenario {s.idx} — {len(bugs)} issue(s):")
            for b in bugs:
                print(b)
        else:
            print(f"\n  Scenario {s.idx} — ✓ clean")
    print()
    print(f"Total issues found: {total_bugs}")
    print("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--only", type=int, default=None,
        help="Run only scenario N (1-6)",
    )
    args = parser.parse_args()
    asyncio.run(main(only=args.only))
