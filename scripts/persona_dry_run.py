"""20-turn persona dry-run — exercise the full Jessica pipeline end-to-end.

Runs against a fresh local SQLite at /tmp/persona_test.db. Uses real
LLM calls (OPENAI_API_KEY required). Prints every user turn + Jessica's
bubbles, plus per-turn metadata (planner decision, specialists, latency).

Cost: ~$0.30-0.80 in OpenAI tokens depending on model selection.

Usage:
    python scripts/persona_dry_run.py            # full 20-turn dialogue
    python scripts/persona_dry_run.py --short    # first 5 turns only
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

# Suppress noisy library logs — keep our turn-by-turn output readable
logging.basicConfig(level=logging.WARNING)
for noisy in ("httpx", "openai", "urllib3"):
    logging.getLogger(noisy).setLevel(logging.ERROR)

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.agents.registry import build_specialist_registry  # noqa: E402
from src.crm.repo import CRMRepo  # noqa: E402
from src.llm import LLMClient  # noqa: E402
from src.orchestrator.pipeline import JessicaPipeline  # noqa: E402
from src.tools.embedder import Embedder  # noqa: E402
from src.tools.kb_index import KBIndex  # noqa: E402
from src.tools.kb_search import KBSearch  # noqa: E402
from src.trace.writer import TraceWriter  # noqa: E402

# Optional: load .env so OPENAI_API_KEY is available
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv(REPO_ROOT / ".env")
except ImportError:
    pass


PERSONA_PHONE = "+85299999001"

# 20-turn dialogue script. Each item is (description, user_message, optional_media_url).
DIALOGUE: list[tuple[str, str, list[str]]] = [
    ("First touch", "Hello", []),
    ("Symptom intro", "我最近成日失眠，又有點頭痛", []),
    ("Stress context", "我做 IT 嘅，成日做到夜晚 1-2 點先瞓", []),
    ("Asks why", "係咪同我嘅生活有關？中醫角度點睇？", []),
    ("Wants help", "你可以點幫我？", []),
    # Tongue photo (simulated URL — vision will be called)
    ("Tongue photo upload", "我影咗張脷俾你睇下",
        ["https://upload.wikimedia.org/wikipedia/commons/thumb/0/0c/Healthy_human_tongue.jpg/640px-Healthy_human_tongue.jpg"]),
    ("MCQ answer 1", "C", []),
    ("MCQ answer 2", "B", []),
    ("MCQ answer 3", "C", []),
    ("MCQ answer 4", "B", []),
    ("Asks about soups", "有咩湯水推介？", []),
    ("Wants details", "邊一款最啱我？", []),
    ("Pricing", "幾錢呀？", []),
    ("Order intent", "我想試下清心潤肺湯", []),
    ("Asks delivery", "點訂？要等幾耐？", []),
    ("Want appointment", "我都想預約覆診", []),
    ("Picks slot", "下星期三下午得唔得？", []),
    ("Confirms", "OK 三點", []),
    ("Thanks", "多謝你 Jessica", []),
    ("Farewell", "好啦拜拜", []),
]


async def main(short: bool = False) -> None:
    # 0. Fresh CRM
    db_path = Path("/tmp/persona_test.db")
    if db_path.exists():
        db_path.unlink()
    crm = await CRMRepo.connect(db_path)

    # 1. LLM + KB + trace
    client = LLMClient()
    kb_index = KBIndex.load()
    embedder = None  # local SQLite has no pgvector; keyword search only
    kb_search = KBSearch(kb_index, vector_store=None, embedder=embedder)
    trace_writer = TraceWriter(str(REPO_ROOT / "traces_dev"))

    # 2. Specialists + pipeline
    specialists = build_specialist_registry(client, kb_search=kb_search)
    pipeline = JessicaPipeline(
        crm=crm,
        trace_writer=trace_writer,
        client=client,
        specialists=specialists,
    )

    turns = DIALOGUE[:5] if short else DIALOGUE

    print()
    print("=" * 72)
    print(f"📱 PERSONA DRY-RUN — {len(turns)} turns")
    print(f"   User: 28-yr-old HK IT worker, insomnia + headaches")
    print(f"   Phone: {PERSONA_PHONE}")
    print(f"   DB: {db_path} (fresh)")
    print("=" * 72)

    for idx, (label, msg, media) in enumerate(turns, start=1):
        media_note = f" + 📷 ({len(media)} img)" if media else ""
        print()
        print(f"┌─[Turn {idx:2d}: {label}]{media_note} " + "─" * (50 - len(label)))
        print(f"│ 👤 User: {msg}")
        try:
            result = await pipeline.run_turn(
                phone=PERSONA_PHONE,
                user_message=msg,
                media_urls=media,
            )
            trace = result.trace
            planner_out = trace.planner.output if trace.planner else {}
            specialists_used = planner_out.get("specialists", [])
            reasoning = planner_out.get("reasoning", "")[:60]
            latency = trace.total_latency_ms or 0

            print(f"│ 🧠 Plan: {specialists_used} mode={planner_out.get('mode', '?')}")
            print(f"│        {reasoning}")
            if planner_out.get("extracted_pain_points"):
                print(f"│ 🩺 Extracted: {planner_out['extracted_pain_points']}")
            if planner_out.get("rephrased_query") and planner_out["rephrased_query"] != msg:
                print(f"│ 🔄 Rephrased: {planner_out['rephrased_query']}")

            for i, bubble in enumerate(result.writer_output.bubbles, 1):
                # Use markers so Jessica's bubbles stand out
                first = "│ 💬 Jessica:" if i == 1 else "│           "
                print(f"{first} {bubble}")

            media_to_send = result.writer_output.media_to_send or []
            for m in media_to_send:
                url = m.get("url", "")[:60]
                print(f"│ 📎 Media: {url}...")

            print(f"│ ⏱️  {latency}ms")
        except Exception as exc:  # noqa: BLE001
            print(f"│ ❌ ERROR: {type(exc).__name__}: {exc}")
        print("└" + "─" * 70)

    # 3. Final CRM snapshot
    final_user = await crm.get_user(PERSONA_PHONE)
    print()
    print("=" * 72)
    print("📊 FINAL CRM SNAPSHOT")
    print("=" * 72)
    if final_user:
        print(f"  status:              {final_user.status.value}")
        print(f"  constitution:        {final_user.constitution.value}")
        print(f"  pain_points:         {final_user.pain_points}")
        print(f"  products_pitched:    {final_user.products_pitched}")
        print(f"  products_purchased:  {final_user.products_purchased}")
        print(f"  appointments:        {len(final_user.appointments)} booked")
        print(f"  tongue_photos:       {len(final_user.tongue_photos)} recorded")
        print(f"  notes (first 200):   {final_user.notes[:200]!r}")
        print(f"  conv history:        {len(final_user.conversation_history)} msgs")
    print("=" * 72)
    print()

    await crm.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--short", action="store_true", help="Only first 5 turns")
    args = parser.parse_args()
    asyncio.run(main(short=args.short))
