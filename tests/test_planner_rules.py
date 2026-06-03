"""Tests for Planner rule overrides — no LLM call."""

from __future__ import annotations

from datetime import datetime

from src.agents.base import SpecialistName
from src.agents.planner import (
    _build_closing_notes,
    _build_returning_hint,
    _is_farewell,
    _rule_overrides,
    _wants_appointment,
)
from src.crm.models import Constitution, ConversationMessage, User, UserStatus


def _user_with_history(**kwargs) -> User:
    """Helper — user with at least one prior conversation message."""
    history = [ConversationMessage(role="user", content="上次嚟過", at=datetime.utcnow())]
    return User(phone="+85291234567", conversation_history=history, **kwargs)


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


# ---------------------------------------------------------------------------
# Farewell detection — _is_farewell()
# ---------------------------------------------------------------------------


def test_is_farewell_exact_tokens() -> None:
    for phrase in ("拜拜", "再見", "bye", "多謝", "thx", "好啦", "晚安"):
        assert _is_farewell(phrase), f"expected farewell: {phrase!r}"


def test_is_farewell_case_insensitive() -> None:
    assert _is_farewell("Bye")
    assert _is_farewell("BYE")
    assert _is_farewell("Thanks")


def test_is_farewell_in_short_message() -> None:
    assert _is_farewell("好啦多謝")
    assert _is_farewell("bye bye!")


def test_is_farewell_false_for_long_messages() -> None:
    # Long messages containing farewell words should NOT trigger
    long = "我唔係想再見你，我係想問下有咩好嘅湯水推介俾我試下啊"
    assert not _is_farewell(long)


def test_is_farewell_false_for_substantive_content() -> None:
    assert not _is_farewell("我想知道失眠嘅湯水")
    assert not _is_farewell("推介湯水俾我")
    assert not _is_farewell("你好啊我有問題")


# ---------------------------------------------------------------------------
# Farewell rule → closing summary (planner rule)
# ---------------------------------------------------------------------------


def test_farewell_routes_to_greeting_with_closing_notes() -> None:
    """Returning user says bye → GREETING + closing summary in notes_for_writer."""
    user = _user_with_history(status=UserStatus.QUALIFIED)
    decision = _rule_overrides(user, "拜拜", [])

    assert decision is not None
    assert decision.specialists == [SpecialistName.GREETING]
    assert "farewell" in decision.reasoning.lower()
    assert decision.notes_for_writer is not None
    assert "對話結束" in decision.notes_for_writer


def test_farewell_includes_crm_context_in_notes() -> None:
    """Closing notes reference the user's pain points and constitution."""
    user = _user_with_history(
        status=UserStatus.CONSTITUTION_DONE,
        constitution=Constitution.YANGXU,
        pain_points=["失眠", "腰痛"],
    )
    notes = _build_closing_notes(user)

    assert "陽虛質" in notes
    assert "失眠" in notes or "腰痛" in notes


def test_farewell_not_triggered_for_first_touch() -> None:
    """First-touch user saying 'bye' has no history — should NOT trigger farewell rule."""
    user = User(phone="+85291234567", status=UserStatus.NEW)
    decision = _rule_overrides(user, "bye", [])

    # No history → farewell rule skips; may fall through to LLM or first-touch
    assert decision is None or decision.specialists != [SpecialistName.GREETING] or \
        (decision.notes_for_writer is None or "對話結束" not in decision.notes_for_writer)


def test_farewell_fires_before_emotion_rule() -> None:
    """'唔緊要好啦' contains farewell + could be emotional — farewell wins."""
    user = _user_with_history(status=UserStatus.QUALIFIED)
    decision = _rule_overrides(user, "唔緊要好啦", [])

    assert decision is not None
    assert decision.specialists == [SpecialistName.GREETING]


# ---------------------------------------------------------------------------
# Returning user greeting → proactive follow-up
# ---------------------------------------------------------------------------


def test_returning_greeting_includes_proactive_notes() -> None:
    """Returning user with pain_points says hi → notes_for_writer includes context."""
    user = _user_with_history(
        status=UserStatus.QUALIFIED,
        pain_points=["失眠"],
    )
    decision = _rule_overrides(user, "你好", [])

    assert decision is not None
    assert decision.specialists == [SpecialistName.CASUAL]
    assert decision.notes_for_writer is not None
    assert "回頭用戶" in decision.notes_for_writer
    assert "失眠" in decision.notes_for_writer


def test_returning_greeting_references_purchased_product() -> None:
    """Returning user who bought something → hint mentions the product."""
    user = _user_with_history(
        status=UserStatus.BOUGHT,
        products_purchased=["彭魚鰓解毒湯"],
    )
    hint = _build_returning_hint(user)
    assert "彭魚鰓解毒湯" in hint


def test_returning_greeting_references_constitution() -> None:
    """Returning user with known constitution → hint includes it."""
    user = _user_with_history(constitution=Constitution.QIXU)
    hint = _build_returning_hint(user)
    assert "氣虛質" in hint


def test_returning_greeting_no_context_is_gentle() -> None:
    """Returning user with no CRM context → generic warm greeting, no crash."""
    user = _user_with_history()  # no pain_points, no constitution, no notes
    hint = _build_returning_hint(user)
    assert isinstance(hint, str)
    assert len(hint) > 0


def test_returning_greeting_hi_variations() -> None:
    """Multiple greeting forms all trigger the returning-user rule."""
    user = _user_with_history(pain_points=["頭痛"])
    for greeting in ("hi", "你好", "喂", "早晨", "hello"):
        decision = _rule_overrides(user, greeting, [])
        assert decision is not None, f"no decision for greeting {greeting!r}"
        assert decision.specialists == [SpecialistName.CASUAL], \
            f"wrong specialist for {greeting!r}: {decision.specialists}"


# ---------------------------------------------------------------------------
# Appointment-intent rule — must NOT fire on generic time words
# (regression: 2026-06-03 prod 鬼打墙 — "今天有什么汤水介绍啊？" was forced to
#  appointment because "今天" was an appointment keyword → pushed 視診 promo,
#  never answered the soup question).
# ---------------------------------------------------------------------------

def test_today_soup_question_is_not_appointment() -> None:
    """The exact prod bug: a soup question containing 今天 must NOT route to appt."""
    assert _wants_appointment("今天有什么汤水介绍啊？") is False
    assert _wants_appointment("今日有咩湯水介紹啊？") is False


def test_generic_time_words_are_not_appointment() -> None:
    for msg in (
        "今天好攰",
        "聽日想試下煲湯",
        "明天可以飲呢個湯嗎？",
        "幾時可以飲呢個湯？",
        "呢個湯幾點飲最好？",
    ):
        assert _wants_appointment(msg) is False, f"false positive on {msg!r}"


def test_genuine_appointment_still_detected() -> None:
    for msg in (
        "我想預約睇醫師",
        "可唔可以網上視診？",
        "想到診睇中醫",
        "聽日想預約",            # time word + real booking signal → still True
        "診所喺邊呀？",
    ):
        assert _wants_appointment(msg) is True, f"missed appointment intent in {msg!r}"


def test_delivery_address_not_mistaken_for_clinic_address() -> None:
    """Bare '地址' (delivery address in a sales order) must NOT trigger appointment."""
    assert _wants_appointment("我嘅地址係沙田...") is False


def test_today_soup_question_falls_through_to_llm() -> None:
    """End-to-end at the rule layer: soup question yields no rule override
    (so it reaches the LLM Planner, which routes to FAQ/Sales)."""
    user = User(phone="+85291234567", status=UserStatus.QUALIFIED)
    decision = _rule_overrides(user, "今天有什么汤水介绍啊？", [])
    if decision is not None:
        assert SpecialistName.APPOINTMENT not in decision.specialists
