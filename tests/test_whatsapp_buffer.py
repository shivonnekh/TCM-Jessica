"""Tests for the WhatsApp merge buffer + dedup.

Covers the three invariants of the buffer/merge layer:

1. Rapid-fire messages within the merge window combine into ONE
   pipeline call.
2. Messages outside the window stay as separate pipeline calls.
3. The dedup set prevents the same ``wa_message_id`` from processing
   twice (regardless of whether webhook or poller delivered it).

All tests stub out the pipeline with an ``AsyncMock`` and patch
ChatDaddy send so no network calls are made.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from src.whatsapp import router as router_module


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def stub_pipeline() -> AsyncMock:
    """Pipeline stub — records each `run_turn` call + returns a fake bubble list."""
    pipeline = AsyncMock()

    async def _run_turn(*, phone, user_message, media_urls=None,
                        merged_from_fragments=None, wa_message_id=None):
        # Mirror the shape of `PipelineResult`. Tests only inspect the
        # fields they care about, so a SimpleNamespace is enough.
        from types import SimpleNamespace
        writer_output = SimpleNamespace(bubbles=[f"echo: {user_message}"])
        return SimpleNamespace(
            turn_id=f"turn_{phone}_{len(user_message)}",
            writer_output=writer_output,
        )

    pipeline.run_turn = AsyncMock(side_effect=_run_turn)
    return pipeline


@pytest.fixture(autouse=True)
def reset_router_state(stub_pipeline, monkeypatch, tmp_path):
    """Reset all module-level state between tests.

    Required because router.py keeps process-global ``_seen_ids`` and
    ``_merge_buffers`` dicts that would leak across test cases.
    """
    router_module._merge_buffers.clear()
    router_module._seen_ids.clear()
    router_module._bg_task_refs.clear()
    router_module._phone_locks.clear()
    router_module.set_pipeline(stub_pipeline)

    # Tighten merge windows so tests don't waste real time.
    monkeypatch.setattr(router_module, "WA_MERGE_COMPLETE", 0.2)
    monkeypatch.setattr(router_module, "WA_MERGE_INCOMPLETE", 0.4)
    monkeypatch.setattr(router_module, "WA_MERGE_FORCE", 1.5)

    # Stub the ChatDaddy client send so we never touch the network.
    monkeypatch.setattr(
        router_module.client, "send_long_message",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        router_module.client, "send_message",
        AsyncMock(return_value=None),
    )
    # Bypass typing delays for fast tests.
    monkeypatch.setattr(router_module.client, "_typing_delay", lambda text: 0.0)

    # Point blocklist at a fresh tmp file so the prod data/blocklist.json
    # doesn't affect tests.
    from src.whatsapp import blocklist
    blocklist._set_path_for_tests(tmp_path / "blocklist.json")
    blocklist._reload_for_tests()

    yield

    router_module._merge_buffers.clear()
    router_module._seen_ids.clear()
    router_module._bg_task_refs.clear()
    router_module._phone_locks.clear()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _enqueue(phone: str, text: str, message_id: str) -> None:
    """Enqueue a single fragment into the merge buffer."""
    await router_module._enqueue_for_merge(
        phone=phone,
        text=text,
        chat_id=f"{phone}@s.whatsapp.net",
        account_id="acc_test",
        sender_name="Test User",
        message_id=message_id,
    )


async def _wait_for_flush(timeout: float = 3.0) -> None:
    """Wait until all background flusher tasks finish."""
    deadline = asyncio.get_event_loop().time() + timeout
    while router_module._bg_task_refs and asyncio.get_event_loop().time() < deadline:
        # Snapshot the set — tasks may add/remove themselves while we wait.
        pending = list(router_module._bg_task_refs)
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_three_rapid_fragments_merge_into_one_pipeline_call(stub_pipeline):
    """3 rapid-fire fragments within the merge window → ONE pipeline call."""
    phone = "85291234567"

    await _enqueue(phone, "我頭痛", "wa_msg_1")
    await asyncio.sleep(0.05)
    await _enqueue(phone, "瞓得唔好", "wa_msg_2")
    await asyncio.sleep(0.05)
    await _enqueue(phone, "食欲又差", "wa_msg_3")

    await _wait_for_flush()

    assert stub_pipeline.run_turn.await_count == 1, (
        f"expected 1 merged pipeline call, got {stub_pipeline.run_turn.await_count}"
    )
    call_kwargs = stub_pipeline.run_turn.await_args.kwargs
    assert call_kwargs["phone"] == phone
    # All three fragments must appear in the merged text.
    merged = call_kwargs["user_message"]
    assert "我頭痛" in merged
    assert "瞓得唔好" in merged
    assert "食欲又差" in merged
    # All three message_ids must appear in the fragment list.
    fragments = call_kwargs["merged_from_fragments"]
    assert set(fragments) == {"wa_msg_1", "wa_msg_2", "wa_msg_3"}


@pytest.mark.asyncio
async def test_messages_outside_merge_window_stay_separate(stub_pipeline):
    """Two fragments spaced beyond the merge window → TWO pipeline calls."""
    phone = "85291234567"

    await _enqueue(phone, "我頭痛", "wa_msg_a")
    await _wait_for_flush()
    assert stub_pipeline.run_turn.await_count == 1

    # Sleep well past WA_MERGE_FORCE so any zombie flusher is gone.
    await asyncio.sleep(0.05)

    await _enqueue(phone, "另一個問題", "wa_msg_b")
    await _wait_for_flush()

    assert stub_pipeline.run_turn.await_count == 2, (
        f"expected 2 separate pipeline calls, got "
        f"{stub_pipeline.run_turn.await_count}"
    )
    second_call = stub_pipeline.run_turn.await_args_list[1].kwargs
    assert "另一個問題" in second_call["user_message"]
    assert "我頭痛" not in second_call["user_message"]


@pytest.mark.asyncio
async def test_dedup_prevents_double_processing_of_same_message_id():
    """Recording the same ``wa_message_id`` twice → only the first wins."""
    assert not router_module._is_duplicate("wa_dup_1")
    router_module._record_seen_message_id("wa_dup_1")
    assert router_module._is_duplicate("wa_dup_1")

    # Empty id is never a duplicate (defensive).
    assert not router_module._is_duplicate("")
    router_module._record_seen_message_id("")
    assert not router_module._is_duplicate("")


@pytest.mark.asyncio
async def test_dedup_blocks_second_enqueue_via_webhook_path(stub_pipeline):
    """Simulate the webhook path's dedup gate: same id → second enqueue
    is skipped, pipeline runs only once."""
    phone = "85291234567"
    msg_id = "wa_msg_dup"

    # First arrival — record + enqueue
    if not router_module._is_duplicate(msg_id):
        router_module._record_seen_message_id(msg_id)
        await _enqueue(phone, "hello", msg_id)

    # Second arrival (webhook replay) — dedup catches it, skip
    if not router_module._is_duplicate(msg_id):
        router_module._record_seen_message_id(msg_id)
        await _enqueue(phone, "hello", msg_id)

    await _wait_for_flush()

    assert stub_pipeline.run_turn.await_count == 1


@pytest.mark.asyncio
async def test_dedup_lru_evicts_oldest_when_full(monkeypatch):
    """Dedup cap is enforced — oldest id is evicted when over capacity."""
    monkeypatch.setattr(router_module, "_DEDUP_MAX", 3)
    router_module._seen_ids.clear()

    for i in range(5):
        router_module._record_seen_message_id(f"id_{i}")

    # Only the last 3 should remain.
    assert not router_module._is_duplicate("id_0")
    assert not router_module._is_duplicate("id_1")
    assert router_module._is_duplicate("id_2")
    assert router_module._is_duplicate("id_3")
    assert router_module._is_duplicate("id_4")
