"""Tests for first-touch flow when user opens with a health complaint."""

from __future__ import annotations

import pytest

from src.agents.base import SpecialistInput, SpecialistName
from src.agents.greeting_agent import GreetingAgent, _user_has_complaint
from src.agents.planner import _rule_overrides
from src.crm.models import User, UserStatus


# ── Greeting Agent: template branching ───────────────────────────────


@pytest.fixture
def agent() -> GreetingAgent:
    # client unused on first-touch fast path
    return GreetingAgent(client=None)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_first_touch_no_complaint_uses_full_intro(agent: GreetingAgent) -> None:
    user = User(phone="+85291234567", status=UserStatus.NEW)
    inp = SpecialistInput(user=user, user_message="hi")
    out, _ = await agent.run(inp)

    payload = out.payload
    assert payload["official_intro"] is True
    # Full template has 4 bubbles
    assert len(payload["intro_bubbles"]) == 4
    assert "intent_flags" in payload
    assert "complaint_in_first_msg" not in payload["intent_flags"]


@pytest.mark.asyncio
async def test_first_touch_with_complaint_uses_compact_intro(
    agent: GreetingAgent,
) -> None:
    user = User(phone="+85291234567", status=UserStatus.NEW)
    inp = SpecialistInput(user=user, user_message="我皮膚痕癢")
    out, _ = await agent.run(inp)

    payload = out.payload
    assert payload["official_intro"] is True
    # Compact template has 2 bubbles
    assert len(payload["intro_bubbles"]) == 2
    assert "complaint_in_first_msg" in payload["intent_flags"]


# ── _user_has_complaint ──────────────────────────────────────────────


@pytest.mark.parametrize(
    "text",
    ["我皮膚痕癢", "頭痛", "失眠", "我覺得好攰", "想睇下體質", "皮膚問題", "經痛"],
)
def test_user_has_complaint_detects_health_terms(text: str) -> None:
    assert _user_has_complaint(text)


@pytest.mark.parametrize(
    "text", ["hi", "hello", "你好", "請問", "", "謝謝"]
)
def test_user_has_complaint_ignores_pure_greetings(text: str) -> None:
    assert not _user_has_complaint(text)


# ── Planner rule: first-touch + symptom routes to [greeting, constitution] ──


def test_planner_first_touch_with_symptom_routes_to_pair() -> None:
    user = User(phone="+85291234567", status=UserStatus.NEW)
    decision = _rule_overrides(user, "我皮膚痕癢", [])
    assert decision is not None
    assert decision.specialists == [
        SpecialistName.GREETING,
        SpecialistName.CONSTITUTION,
    ]
    assert decision.mode == "sequential"


def test_planner_first_touch_pure_hi_routes_to_greeting_only() -> None:
    user = User(phone="+85291234567", status=UserStatus.NEW)
    decision = _rule_overrides(user, "hi", [])
    assert decision is not None
    assert decision.specialists == [SpecialistName.GREETING]
    assert decision.mode == "solo"


def test_planner_returning_user_with_symptom_skips_rule() -> None:
    """For returning users we let the LLM Planner decide — they're past intro."""
    from datetime import datetime

    from src.crm.models import ConversationMessage

    user = User(
        phone="+85291234567",
        status=UserStatus.QUALIFIED,
        conversation_history=[
            ConversationMessage(role="user", content="hi", at=datetime.utcnow())
        ],
    )
    decision = _rule_overrides(user, "我皮膚痕癢", [])
    assert decision is None
