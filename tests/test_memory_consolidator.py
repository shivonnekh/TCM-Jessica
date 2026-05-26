"""Tests for memory_consolidator.py — auto-summary of conversation history."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.memory_consolidator import (
    MIN_NEW_MESSAGES,
    consolidate_memory,
    should_consolidate,
)
from src.crm.models import ConversationMessage, User
from src.crm.repo import CRMRepo


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def repo(tmp_path: Path) -> CRMRepo:
    r = await CRMRepo.connect(tmp_path / "test.db")
    yield r
    await r.close()


def _make_user(**kwargs) -> User:
    defaults = {"phone": "+85291000001"}
    defaults.update(kwargs)
    return User(**defaults)


def _make_messages(n: int, role: str = "user", base_offset_minutes: int = 0) -> list[ConversationMessage]:
    """Create N ConversationMessage objects with sequential timestamps."""
    return [
        ConversationMessage(
            role=role,
            content=f"message {i}",
            at=datetime(2026, 5, 20, 10, 0) + timedelta(minutes=base_offset_minutes + i),
        )
        for i in range(n)
    ]


def _mock_llm(reply: str = "更新後嘅筆記內容") -> MagicMock:
    """Return a mock LLM client that returns a fixed text."""
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=reply)]

    llm = MagicMock()
    llm.messages = MagicMock()
    llm.messages.create = AsyncMock(return_value=mock_response)
    return llm


# ---------------------------------------------------------------------------
# should_consolidate — no prior consolidation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_should_consolidate_false_when_few_messages(repo: CRMRepo) -> None:
    """User with ≤20 total messages: no consolidation needed."""
    phone = "+85291000001"
    await repo.get_or_create_user(phone)
    for msg in _make_messages(10):
        await repo.append_message(phone, msg)

    user = await repo.get_user(phone)
    assert not await should_consolidate(repo, user)


@pytest.mark.asyncio
async def test_should_consolidate_true_when_many_messages(repo: CRMRepo) -> None:
    """User with >20 total messages and no prior consolidation: should consolidate."""
    phone = "+85291000002"
    await repo.get_or_create_user(phone)
    for msg in _make_messages(25):
        await repo.append_message(phone, msg)

    user = await repo.get_user(phone)
    assert await should_consolidate(repo, user)


# ---------------------------------------------------------------------------
# should_consolidate — after previous consolidation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_should_consolidate_false_if_few_messages_since_last(repo: CRMRepo) -> None:
    """Fewer than MIN_NEW_MESSAGES since last consolidation: skip."""
    phone = "+85291000003"
    last_at = datetime(2026, 5, 20, 9, 0)
    await repo.get_or_create_user(phone)
    # Add 5 messages AFTER the last_consolidated_at
    for msg in _make_messages(5, base_offset_minutes=60):  # all after 10:00 > 9:00
        await repo.append_message(phone, msg)

    user = _make_user(
        phone=phone,
        temp_state={"last_consolidated_at": last_at.isoformat()},
    )
    assert not await should_consolidate(repo, user)


@pytest.mark.asyncio
async def test_should_consolidate_true_if_enough_messages_since_last(repo: CRMRepo) -> None:
    """At least MIN_NEW_MESSAGES since last consolidation: should consolidate."""
    phone = "+85291000004"
    last_at = datetime(2026, 5, 20, 9, 0)
    await repo.get_or_create_user(phone)
    for msg in _make_messages(MIN_NEW_MESSAGES, base_offset_minutes=60):
        await repo.append_message(phone, msg)

    user = _make_user(
        phone=phone,
        temp_state={"last_consolidated_at": last_at.isoformat()},
    )
    assert await should_consolidate(repo, user)


# ---------------------------------------------------------------------------
# consolidate_memory — core logic
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_consolidate_skips_when_too_few_messages(repo: CRMRepo) -> None:
    """Returns original user unchanged when there aren't enough messages."""
    phone = "+85291000005"
    await repo.get_or_create_user(phone)
    for msg in _make_messages(5):
        await repo.append_message(phone, msg)

    user = await repo.get_user(phone)
    llm = _mock_llm()
    result = await consolidate_memory(repo, llm, user)

    # No LLM call made
    llm.messages.create.assert_not_called()
    # User returned unchanged
    assert result.notes == user.notes
    assert result.temp_state.get("last_consolidated_at") is None


@pytest.mark.asyncio
async def test_consolidate_calls_llm_and_updates_notes(repo: CRMRepo) -> None:
    """With enough messages, calls LLM and updates user.notes."""
    phone = "+85291000006"
    await repo.get_or_create_user(phone)
    for msg in _make_messages(MIN_NEW_MESSAGES + 5):
        await repo.append_message(phone, msg)

    user = await repo.get_user(phone)
    llm = _mock_llm(reply="用戶有失眠同腰痛問題。對玫瑰花茶有興趣。")
    result = await consolidate_memory(repo, llm, user)

    llm.messages.create.assert_called_once()
    assert result.notes == "用戶有失眠同腰痛問題。對玫瑰花茶有興趣。"
    assert "last_consolidated_at" in result.temp_state


@pytest.mark.asyncio
async def test_consolidate_persists_to_crm(repo: CRMRepo) -> None:
    """Updated notes are saved to CRM so next load sees them."""
    phone = "+85291000007"
    await repo.get_or_create_user(phone)
    for msg in _make_messages(MIN_NEW_MESSAGES + 2):
        await repo.append_message(phone, msg)

    user = await repo.get_user(phone)
    await consolidate_memory(repo, _mock_llm("新筆記內容"), user)

    reloaded = await repo.get_user(phone)
    assert reloaded is not None
    assert reloaded.notes == "新筆記內容"
    assert "last_consolidated_at" in reloaded.temp_state


@pytest.mark.asyncio
async def test_consolidate_bumps_timestamp_even_if_notes_unchanged(repo: CRMRepo) -> None:
    """Even if LLM returns same notes, last_consolidated_at is updated."""
    phone = "+85291000008"
    original_notes = "原有筆記"
    await repo.get_or_create_user(phone)
    # Save user with existing notes
    u = await repo.get_or_create_user(phone)
    await repo.save_user(u.with_updates(notes=original_notes))

    for msg in _make_messages(MIN_NEW_MESSAGES + 1):
        await repo.append_message(phone, msg)

    user = await repo.get_user(phone)
    # LLM returns same notes (no new info)
    llm = _mock_llm(reply=original_notes)
    result = await consolidate_memory(repo, llm, user)

    assert "last_consolidated_at" in result.temp_state


@pytest.mark.asyncio
async def test_consolidate_handles_llm_failure_gracefully(repo: CRMRepo) -> None:
    """LLM error → original user returned, no crash, notes unchanged."""
    phone = "+85291000009"
    await repo.get_or_create_user(phone)
    for msg in _make_messages(MIN_NEW_MESSAGES + 1):
        await repo.append_message(phone, msg)

    user = await repo.get_user(phone)
    llm = MagicMock()
    llm.messages = MagicMock()
    llm.messages.create = AsyncMock(side_effect=RuntimeError("LLM down"))

    result = await consolidate_memory(repo, llm, user)
    assert result.notes == user.notes  # unchanged
    assert result.temp_state.get("last_consolidated_at") is None  # not bumped


@pytest.mark.asyncio
async def test_consolidate_only_reads_messages_since_last_run(repo: CRMRepo) -> None:
    """Second consolidation only reads messages since last_consolidated_at."""
    phone = "+85291000010"
    await repo.get_or_create_user(phone)

    # Add 20 old messages
    cutoff = datetime(2026, 5, 20, 10, 0)
    for i in range(20):
        await repo.append_message(
            phone,
            ConversationMessage(
                role="user",
                content=f"old message {i}",
                at=cutoff - timedelta(minutes=20 - i),
            ),
        )

    # Add MIN_NEW_MESSAGES new messages after cutoff
    for i in range(MIN_NEW_MESSAGES):
        await repo.append_message(
            phone,
            ConversationMessage(
                role="user",
                content=f"new message {i}",
                at=cutoff + timedelta(minutes=i + 1),
            ),
        )

    user = _make_user(
        phone=phone,
        temp_state={"last_consolidated_at": cutoff.isoformat()},
    )

    call_args_captured: list = []

    async def capture_create(**kwargs):
        call_args_captured.append(kwargs)
        mock_resp = MagicMock()
        mock_resp.content = [MagicMock(text="new summary")]
        return mock_resp

    llm = MagicMock()
    llm.messages = MagicMock()
    llm.messages.create = capture_create

    await consolidate_memory(repo, llm, user)

    # The prompt should only contain "new message" content, not "old message"
    assert call_args_captured, "LLM should have been called"
    user_prompt = call_args_captured[0]["messages"][0]["content"]
    assert "new message" in user_prompt
    assert "old message" not in user_prompt


# ---------------------------------------------------------------------------
# Pipeline integration — _maybe_consolidate helper
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_maybe_consolidate_calls_consolidate_when_should(repo: CRMRepo) -> None:
    """_maybe_consolidate invokes consolidate_memory when should_consolidate is True."""
    from src.orchestrator.pipeline import _maybe_consolidate

    phone = "+85291000011"
    await repo.get_or_create_user(phone)
    for msg in _make_messages(MIN_NEW_MESSAGES + 10):  # 25 > 20 threshold
        await repo.append_message(phone, msg)

    user = await repo.get_user(phone)
    llm = _mock_llm("記憶摘要：用戶有頭痛問題。")
    await _maybe_consolidate(repo, llm, user)

    # Notes should have been updated
    reloaded = await repo.get_user(phone)
    assert reloaded is not None
    assert reloaded.notes == "記憶摘要：用戶有頭痛問題。"


@pytest.mark.asyncio
async def test_maybe_consolidate_skips_when_should_not(repo: CRMRepo) -> None:
    """_maybe_consolidate is a no-op when there aren't enough new messages."""
    from src.orchestrator.pipeline import _maybe_consolidate

    phone = "+85291000012"
    await repo.get_or_create_user(phone)
    # Only 5 messages — below threshold
    for msg in _make_messages(5):
        await repo.append_message(phone, msg)

    user = await repo.get_user(phone)
    llm = _mock_llm()
    await _maybe_consolidate(repo, llm, user)

    llm.messages.create.assert_not_called()


@pytest.mark.asyncio
async def test_maybe_consolidate_survives_exception(repo: CRMRepo) -> None:
    """_maybe_consolidate swallows errors — never raises."""
    from src.orchestrator.pipeline import _maybe_consolidate

    user = _make_user()
    broken_crm = MagicMock()
    broken_crm.get_message_count = AsyncMock(side_effect=RuntimeError("DB gone"))

    # Should not raise
    await _maybe_consolidate(broken_crm, MagicMock(), user)
