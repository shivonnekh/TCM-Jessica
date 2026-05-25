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


def test_wame_order_message_routes_to_sales() -> None:
    """wa.me pre-filled order text → Sales immediately, no LLM."""
    user = User(phone="+85291234567", status=UserStatus.QUALIFIED)
    decision = _rule_overrides(user, "想訂【彭魚鰓解毒湯 HK$120】", [])
    assert decision is not None
    assert decision.specialists == [SpecialistName.SALES]
    assert "order" in decision.reasoning.lower()


def test_wame_order_fires_before_other_rules() -> None:
    """Order message takes priority even if user has no prior pitch history."""
    user = User(phone="+85291234567", status=UserStatus.NEW, products_pitched=[])
    decision = _rule_overrides(user, "想訂【清心潤肺湯 HK$48】", [])
    assert decision is not None
    assert decision.specialists == [SpecialistName.SALES]


def test_awaiting_delivery_address_routes_to_sales() -> None:
    """User in mid-address-collection state → Sales (not anything else)."""
    from src.agents.sales_agent import _TS_AWAITING_ADDRESS

    user = User(
        phone="+85291234567",
        status=UserStatus.QUALIFIED,
        temp_state={_TS_AWAITING_ADDRESS: True},
    )
    decision = _rule_overrides(user, "旺角彌敦道123號，陳大文，9876 5432", [])
    assert decision is not None
    assert decision.specialists == [SpecialistName.SALES]
    assert "address" in decision.reasoning.lower()


def test_new_order_overrides_awaiting_address_state() -> None:
    """A new wa.me order message takes priority even when awaiting an address."""
    from src.agents.sales_agent import _TS_AWAITING_ADDRESS

    user = User(
        phone="+85291234567",
        temp_state={_TS_AWAITING_ADDRESS: True},
    )
    # A new order message → order rule fires first (before address rule)
    decision = _rule_overrides(user, "想訂【清心潤肺湯 HK$48】", [])
    assert decision is not None
    assert decision.specialists == [SpecialistName.SALES]
    assert "order" in decision.reasoning.lower()


def test_regular_message_is_not_order() -> None:
    """'我想訂湯' (no bracket format) does NOT trigger order rule → falls through."""
    user = User(phone="+85291234567", status=UserStatus.QUALIFIED)
    # No 【...HK$...】 → not an order message → falls through to LLM
    decision = _rule_overrides(user, "我想訂湯", [])
    assert decision is None
