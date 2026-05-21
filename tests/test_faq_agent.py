"""Tests for FAQAgent — uses offline (no-LLM) mode."""

from __future__ import annotations

import pytest

from src.agents.base import SpecialistInput, SpecialistName
from src.agents.faq_agent import FAQAgent
from src.crm.models import User


@pytest.fixture(scope="module")
def faq() -> FAQAgent:
    # client=None → offline fallback (uses top card's content directly)
    return FAQAgent(client=None)


@pytest.mark.asyncio
async def test_faq_offline_returns_facts_for_known_topic(faq: FAQAgent) -> None:
    user = User(phone="+85291234567")
    inp = SpecialistInput(user=user, user_message="有冇咩湯水可以調氣虛？")
    output, _usage = await faq.run(inp)

    assert output.specialist == SpecialistName.FAQ
    payload = output.payload
    assert payload["no_match"] is False
    assert len(payload["answer_facts"]) > 0
    assert all("card_id" in f for f in payload["answer_facts"])
    assert output.cards_used  # should record which cards were read


@pytest.mark.asyncio
async def test_faq_offline_no_match_for_irrelevant_query(faq: FAQAgent) -> None:
    user = User(phone="+85291234567")
    inp = SpecialistInput(user=user, user_message="我想買部 iPhone")
    output, _usage = await faq.run(inp)

    assert output.payload["no_match"] is True
    assert output.payload["answer_facts"] == []
    assert output.cards_used == []


@pytest.mark.asyncio
async def test_faq_records_tools_called(faq: FAQAgent) -> None:
    user = User(phone="+85291234567")
    inp = SpecialistInput(user=user, user_message="穴位按摩")
    output, _usage = await faq.run(inp)

    assert output.tools_called
    assert output.tools_called[0]["name"] == "KBSearch.search"
