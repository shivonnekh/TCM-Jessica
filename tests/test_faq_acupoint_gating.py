"""Tests for acupoint-image GATING in FAQAgent.

The bug: acupoint images were attached whenever the matched KB *card body*
mentioned an acupoint, even when the user only described symptoms. This
spammed 穴位 images the user never asked for (UX + cost bug).

The fix: attach images only when the USER's message expresses acupressure
intent (`_wants_acupressure`). Card content still drives WHICH points.

These tests run the FULL LLM path via a fake client (so the acupoint scan
executes) and assert on the gate. They also unit-test the helper directly.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from src.agents.base import SpecialistInput, SpecialistName
from src.agents.faq_agent import FAQAgent, _wants_acupressure
from src.crm.models import User


# -------------------------------------------------------------------
# Fake LLM client — returns valid FAQ JSON so the LLM path runs and the
# acupoint scan (which only lives in the LLM path) executes.
# -------------------------------------------------------------------


class _FakeMessages:
    async def create(self, **_kwargs: object) -> SimpleNamespace:
        body = json.dumps(
            {
                "answer_facts": [{"fact": "測試 fact", "card_id": "x"}],
                "confidence": 0.8,
                "next_best_question": None,
                "no_match": False,
            }
        )
        return SimpleNamespace(
            content=[SimpleNamespace(type="text", text=body)],
            usage=SimpleNamespace(input_tokens=1, output_tokens=1),
        )


class _FakeClient:
    def __init__(self) -> None:
        self.messages = _FakeMessages()


@pytest.fixture(scope="module")
def faq_llm() -> FAQAgent:
    return FAQAgent(client=_FakeClient())


# -------------------------------------------------------------------
# Helper unit tests — positive / negative table.
# -------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "邊個穴位可以按",
        "點按舒緩失眠",
        "可唔可以教我穴位按摩",
        "推拿手法",
        "which acupoint helps",
        "give me a massage point",
    ],
)
def test_wants_acupressure_positive(text: str) -> None:
    assert _wants_acupressure(text) is True


@pytest.mark.parametrize(
    "text",
    [
        "我最近成日失眠，又有點頭痛",
        "有冇咩湯水可以調氣虛",
        "我想知我係咩體質",
        "",
        "你好啊 Jessica",
    ],
)
def test_wants_acupressure_negative(text: str) -> None:
    assert _wants_acupressure(text) is False


# -------------------------------------------------------------------
# Integration: symptom-only message must NOT attach acupoint images,
# even though the matched card body lists acupoints.
# -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_symptom_only_no_acupoint_images(faq_llm: FAQAgent) -> None:
    user = User(phone="+85291234567")
    inp = SpecialistInput(user=user, user_message="我最近成日失眠，又有點頭痛")
    output, _usage = await faq_llm.run(inp)

    # Card body for this query DOES contain acupoints (風池/合谷/三陰交/
    # 足三里) — the gate must still suppress them because the user did
    # not ask about acupressure.
    assert output.payload["acupoint_images"] == []


@pytest.mark.asyncio
async def test_acupressure_request_attaches_images(faq_llm: FAQAgent) -> None:
    user = User(phone="+85291234567")
    inp = SpecialistInput(user=user, user_message="邊個穴位可以按舒緩失眠")
    output, _usage = await faq_llm.run(inp)

    images = output.payload["acupoint_images"]
    assert len(images) > 0
    assert all("name" in img and "image_url" in img for img in images)


@pytest.mark.asyncio
async def test_intent_uses_rephrased_query(faq_llm: FAQAgent) -> None:
    """Even if raw message is messy 簡體, the Planner-rephrased query
    drives the gate (effective_query)."""
    user = User(phone="+85291234567")
    inp = SpecialistInput(
        user=user,
        user_message="失眠头痛",  # 簡體, no acupressure word
        rephrased_query="有咩穴位可以按舒緩失眠",  # normalised, with intent
    )
    output, _usage = await faq_llm.run(inp)
    assert len(output.payload["acupoint_images"]) > 0
