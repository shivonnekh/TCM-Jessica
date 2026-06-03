"""Regression: the group LISTEN path must build a valid ConversationMessage.

2026-05-29 prod bug: `_listen_group_message` constructed
``ConversationMessage(role=, text=, timestamp=str)`` but the model fields
are ``content`` + ``at`` (datetime). Every un-mentioned group message
crashed with a pydantic ValidationError (2 missing fields). The LISTEN
path silently failed — no CRM absorption happened.

This test drives `_listen_group_message` with a fake pipeline/CRM and
asserts the message is absorbed (name + pain_points + history) with no
exception.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from src.crm.models import User
from src.whatsapp import router as wa_router
from src.whatsapp.models import ChatDaddyMessage


class _FakeCRM:
    def __init__(self, user: User) -> None:
        self._user = user
        self.saved: list[User] = []

    async def get_or_create_user(self, phone: str) -> User:
        return self._user

    async def save_user(self, user: User) -> None:
        self.saved.append(user)


class _FakePipeline:
    def __init__(self, crm: _FakeCRM) -> None:
        self._crm = crm


def _group_msg(text: str, timestamp: int = 1_900_000_000) -> ChatDaddyMessage:
    return ChatDaddyMessage(
        event="message-insert",
        message_id="m1",
        chat_id="120363000111222@g.us",      # group JID
        account_id="acc",
        text=text,
        from_me=False,
        timestamp=timestamp,
        sender_name="阿明",
        sender_contact_id="998877665544332@lid",  # group participant LID
    )


@pytest.fixture
def wire_pipeline(monkeypatch: pytest.MonkeyPatch):
    def _wire(user: User) -> _FakeCRM:
        crm = _FakeCRM(user)
        monkeypatch.setattr(wa_router, "_get_pipeline", lambda: _FakePipeline(crm))
        return crm
    return _wire


@pytest.mark.asyncio
async def test_listen_absorbs_message_without_crashing(wire_pipeline) -> None:
    user = User(phone="85291112222")
    crm = wire_pipeline(user)

    # Should NOT raise (the original bug raised ValidationError here).
    await wa_router._listen_group_message(
        _group_msg("我最近成日失眠，個頭好痛"), account_id="acc"
    )

    assert crm.saved, "LISTEN path should have persisted the user"
    saved = crm.saved[-1]
    # Name captured from sender_name
    assert saved.name == "阿明"
    # Pain points absorbed via keyword scan
    assert "失眠" in (saved.pain_points or [])
    # History got the message with the right field (content, not text)
    assert any(m.content == "我最近成日失眠，個頭好痛" for m in saved.conversation_history)


@pytest.mark.asyncio
async def test_listen_handles_bad_timestamp(wire_pipeline) -> None:
    user = User(phone="85291112222")
    crm = wire_pipeline(user)

    msg = _group_msg("頭痛", timestamp=99_999_999_999_999)  # absurd → fallback path

    # Must not crash — falls back to utcnow()
    await wa_router._listen_group_message(msg, account_id="acc")
    assert crm.saved


@pytest.mark.asyncio
async def test_listen_skips_when_pipeline_not_ready(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(wa_router, "_get_pipeline", lambda: None)
    # Should return quietly, no exception
    await wa_router._listen_group_message(_group_msg("hi"), account_id="acc")
