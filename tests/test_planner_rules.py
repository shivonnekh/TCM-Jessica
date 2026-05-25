"""Tests for Planner rule overrides — no LLM call."""

from __future__ import annotations

from src.agents.base import SpecialistName
from src.agents.planner import _rule_overrides
from src.crm.models import User, UserStatus


def test_tongue_photo_routes_to_constitution() -> None:
    user = User(phone="+85291234567", status=UserStatus.NEW)
    decision = _rule_overrides(user, "我嚟睇下", ["https://media/tongue.jpg"])
    assert decision is not None
    assert decision.specialists == [SpecialistName.CONSTITUTION]


def test_first_touch_hi_routes_to_greeting() -> None:
    user = User(phone="+85291234567", status=UserStatus.NEW)
    decision = _rule_overrides(user, "hi", [])
    assert decision is not None
    assert decision.specialists == [SpecialistName.GREETING]


def test_substantive_message_falls_through_to_llm() -> None:
    user = User(phone="+85291234567", status=UserStatus.QUALIFIED)
    decision = _rule_overrides(user, "我想知有冇湯水可以調氣虛", [])
    assert decision is None  # signal: LLM should decide


def test_returning_user_says_hi_routes_to_casual() -> None:
    """A user with history saying 'hi' is NOT a first-touch — should
    route to CasualTalk Agent (not Greeting onboarding)."""
    from datetime import datetime

    from src.crm.models import ConversationMessage

    user = User(
        phone="+85291234567",
        status=UserStatus.QUALIFIED,
        conversation_history=[
            ConversationMessage(role="user", content="hi", at=datetime.utcnow())
        ],
    )
    decision = _rule_overrides(user, "hi", [])
    assert decision is not None
    assert decision.specialists == [SpecialistName.CASUAL]
    assert decision.mode == "solo"


def test_purchase_confirmation_routes_to_sales() -> None:
    """'我訂咗' from a user who has seen a pitch → Sales (not Greeting)."""
    user = User(
        phone="+85291234567",
        status=UserStatus.QUALIFIED,
        products_pitched=["soup_pengyu_jiedu"],
    )
    decision = _rule_overrides(user, "我訂咗喇！多謝！", [])
    assert decision is not None
    assert decision.specialists == [SpecialistName.SALES]


def test_purchase_confirmation_no_pitch_falls_through() -> None:
    """'訂咗' from a user who has never seen a pitch → falls through to LLM."""
    user = User(
        phone="+85291234567",
        status=UserStatus.NEW,
        products_pitched=[],  # never pitched
    )
    decision = _rule_overrides(user, "訂咗喇", [])
    # No pitch history → guard fails → falls through to LLM
    assert decision is None
