"""Tests for the per-phone blocklist.

Covers the two key behaviours:

1. A blocked phone short-circuits ``_process_turn`` before the pipeline
   is invoked.
2. Blocklist entries persist to ``data/blocklist.json`` and are read
   back correctly after a reload.

ChatDaddy send is patched with ``AsyncMock``s so no network calls happen.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from src.whatsapp import blocklist
from src.whatsapp import router as router_module


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def fresh_blocklist(tmp_path):
    """Point the blocklist at a fresh temp file for every test."""
    blocklist._set_path_for_tests(tmp_path / "blocklist.json")
    blocklist._reload_for_tests()
    yield
    blocklist._set_path_for_tests(tmp_path / "blocklist.json")
    blocklist._reload_for_tests()


@pytest.fixture
def stub_pipeline_router(monkeypatch):
    """Wire a stub pipeline + stub send into the router."""
    pipeline = AsyncMock()
    from types import SimpleNamespace

    async def _run_turn(**kwargs):
        return SimpleNamespace(
            turn_id="t1",
            writer_output=SimpleNamespace(bubbles=["pipeline ran"]),
        )
    pipeline.run_turn = AsyncMock(side_effect=_run_turn)
    router_module.set_pipeline(pipeline)

    send_message = AsyncMock(return_value=None)
    send_long_message = AsyncMock(return_value=None)
    monkeypatch.setattr(router_module.client, "send_message", send_message)
    monkeypatch.setattr(router_module.client, "send_long_message", send_long_message)
    monkeypatch.setattr(router_module.client, "_typing_delay", lambda t: 0.0)

    return {
        "pipeline": pipeline,
        "send_message": send_message,
        "send_long_message": send_long_message,
    }


# ---------------------------------------------------------------------------
# Persistence tests
# ---------------------------------------------------------------------------


def test_blocklist_empty_on_first_use():
    """A fresh blocklist file means nothing is blocked."""
    assert blocklist.list_blocked() == []
    assert not blocklist.is_blocked("85291234567")
    assert not blocklist.decide("85291234567").blocked


def test_add_and_persist_across_reload(tmp_path):
    """Adding a phone writes to disk; a reload sees it."""
    blocklist._set_path_for_tests(tmp_path / "blocklist.json")
    blocklist._reload_for_tests()

    assert blocklist.add("85291234567") is True
    assert blocklist.is_blocked("85291234567")

    # Adding a duplicate returns False (no change).
    assert blocklist.add("85291234567") is False

    # Simulate a process restart: force a re-read from disk.
    blocklist._reload_for_tests()
    assert blocklist.is_blocked("85291234567")
    assert "85291234567" in blocklist.list_blocked()


def test_remove_persists(tmp_path):
    """Removing a phone writes back to disk."""
    blocklist._set_path_for_tests(tmp_path / "blocklist.json")
    blocklist._reload_for_tests()

    blocklist.add("85291112222")
    assert blocklist.remove("85291112222") is True
    assert not blocklist.is_blocked("85291112222")

    blocklist._reload_for_tests()
    assert not blocklist.is_blocked("85291112222")
    # Removing a non-present phone returns False.
    assert blocklist.remove("85299999999") is False


def test_phone_normalisation_handles_plus_and_spaces():
    """Normalisation strips '+', spaces, JID suffixes — same canonical key."""
    blocklist.add("+852 9123 4567")
    assert blocklist.is_blocked("85291234567")
    assert blocklist.is_blocked("+852-9123-4567")
    assert blocklist.is_blocked("85291234567@s.whatsapp.net")


def test_canned_reply_persists():
    """Setting a canned reply writes it to disk and survives a reload."""
    blocklist.add("85291234567")
    blocklist.set_canned_reply("process canceled")
    decision = blocklist.decide("85291234567")
    assert decision.blocked
    assert decision.canned_reply == "process canceled"
    assert decision.should_send_reply

    blocklist._reload_for_tests()
    decision2 = blocklist.decide("85291234567")
    assert decision2.canned_reply == "process canceled"


# ---------------------------------------------------------------------------
# Short-circuit test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_blocked_phone_skips_pipeline_silently(stub_pipeline_router):
    """A blocked phone with no canned reply → pipeline never runs, no send."""
    phone = "85290000001"
    blocklist.add(phone)
    blocklist._reload_for_tests()

    await router_module._process_turn(
        phone=phone,
        merged_text="hello",
        chat_id=f"{phone}@s.whatsapp.net",
        account_id="acc_test",
        sender_name="Test User",
        attachments=[],
        fragment_ids=["wa_x"],
        primary_message_id="wa_x",
    )

    stub_pipeline_router["pipeline"].run_turn.assert_not_awaited()
    stub_pipeline_router["send_message"].assert_not_awaited()
    stub_pipeline_router["send_long_message"].assert_not_awaited()


@pytest.mark.asyncio
async def test_blocked_phone_with_canned_reply_sends_then_skips(stub_pipeline_router):
    """A blocked phone with a canned reply → canned reply sent, pipeline skipped."""
    phone = "85290000002"
    blocklist.add(phone)
    blocklist.set_canned_reply("process canceled")
    blocklist._reload_for_tests()

    await router_module._process_turn(
        phone=phone,
        merged_text="hello",
        chat_id=f"{phone}@s.whatsapp.net",
        account_id="acc_test",
        attachments=[],
        fragment_ids=["wa_y"],
        primary_message_id="wa_y",
    )

    stub_pipeline_router["pipeline"].run_turn.assert_not_awaited()
    stub_pipeline_router["send_message"].assert_awaited_once()
    # The canned reply should have been the body.
    awaited_args = stub_pipeline_router["send_message"].await_args
    assert "process canceled" in awaited_args.args[2]


@pytest.mark.asyncio
async def test_non_blocked_phone_runs_pipeline_and_sends(stub_pipeline_router):
    """An un-blocked phone → pipeline runs and bubbles are sent."""
    phone = "85290000003"

    await router_module._process_turn(
        phone=phone,
        merged_text="hello",
        chat_id=f"{phone}@s.whatsapp.net",
        account_id="acc_test",
        attachments=[],
        fragment_ids=["wa_z"],
        primary_message_id="wa_z",
    )

    stub_pipeline_router["pipeline"].run_turn.assert_awaited_once()
    stub_pipeline_router["send_long_message"].assert_awaited()
