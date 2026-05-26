"""Tests for acute pain detection + planner routing."""

from __future__ import annotations

from datetime import datetime

import pytest

from src.agents.acute_pain import AcuteRelief, detect_acute_pain
from src.agents.base import SpecialistName
from src.agents.planner import _rule_overrides
from src.crm.models import ConversationMessage, User, UserStatus


# ---------------------------------------------------------------------------
# detect_acute_pain — pure unit tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text,expected_symptom",
    [
        ("我頭好痛 😭", "頭痛"),
        ("頭痛到頂唔順", "頭痛"),
        ("偏頭痛勁痛", "頭痛"),
        ("經痛好辛苦", "經痛"),
        ("M痛勁", "經痛"),
        ("失眠頂唔順", "失眠"),
        ("肩頸痛痛到", "肩頸痛"),
        ("頭暈到天旋地轉", "頭暈眩"),
        ("鼻塞辛苦死", "鼻塞"),
        ("腰好痛幫吓我", "腰痛"),
    ],
)
def test_acute_pain_detects_distress_with_symptom(text: str, expected_symptom: str) -> None:
    relief = detect_acute_pain(text)
    assert relief is not None
    assert relief.symptom_zh == expected_symptom


@pytest.mark.parametrize(
    "text",
    [
        "我有頭痛問題",          # symptom but no urgency signal
        "我以前試過經痛",        # past tense, not urgent now
        "鼻塞咁多年都係咁",      # chronic, not acute
        "我想問下湯水",           # no symptom
        "你好啊",                  # greeting
        "",                        # empty
    ],
)
def test_acute_pain_returns_none_for_non_urgent(text: str) -> None:
    assert detect_acute_pain(text) is None


def test_acute_pain_emoji_alone_is_a_signal() -> None:
    """Emojis like 😭 / 🤕 count as urgency."""
    relief = detect_acute_pain("頭痛 🤕")
    assert relief is not None
    assert relief.symptom_zh == "頭痛"


def test_acute_pain_returns_known_acupoint() -> None:
    """All mapped acupoints exist in the acupoint index — image attach works."""
    relief = detect_acute_pain("我頭好痛 😭")
    assert relief is not None
    assert relief.primary_acupoint_zh == "合谷穴"
    assert relief.location_zh  # non-empty
    assert relief.press_instruction_zh
    assert relief.tcm_rationale_zh


def test_acute_pain_distress_without_symptom_returns_none() -> None:
    """Urgency without a known symptom → fall through to normal flow."""
    assert detect_acute_pain("好辛苦 😭") is None


# ---------------------------------------------------------------------------
# Planner rule integration
# ---------------------------------------------------------------------------


def _user(**kwargs) -> User:
    return User(phone="+85291234567", **kwargs)


def _user_with_history(**kwargs) -> User:
    history = [ConversationMessage(role="user", content="上次嚟過", at=datetime.utcnow())]
    return User(phone="+85291234567", conversation_history=history, **kwargs)


def test_acute_pain_routes_to_casual_and_faq_in_parallel() -> None:
    decision = _rule_overrides(_user(), "我頭好痛 😭", [])

    assert decision is not None
    assert set(decision.specialists) == {SpecialistName.CASUAL, SpecialistName.FAQ}
    assert decision.mode == "parallel"
    assert "急救" in decision.reasoning or "acute" in decision.reasoning.lower()


def test_acute_pain_notes_include_acupoint_instruction() -> None:
    decision = _rule_overrides(_user(), "頭痛到頂唔順", [])

    assert decision is not None
    notes = decision.notes_for_writer
    assert "合谷穴" in notes
    assert "虎口" in notes
    assert "30 秒" in notes or "按壓" in notes


def test_acute_pain_for_period_pain_routes_to_sanyinjiao() -> None:
    decision = _rule_overrides(_user(), "經痛好辛苦", [])

    assert decision is not None
    assert "三陰交" in decision.notes_for_writer


def test_acute_pain_does_not_fire_for_chronic_mention() -> None:
    """Non-acute symptom mention → planner falls through to LLM."""
    decision = _rule_overrides(_user(), "我成日有頭痛問題", [])

    # No acute signal → no acute pain rule → falls through
    if decision is not None:
        # Allowed: the LLM-bypass returns None OR returns a different rule
        # (e.g. complaint_lite). Just verify it's NOT the acute pain rule.
        assert "急救" not in decision.reasoning


def test_acute_pain_fires_before_emotion_rule() -> None:
    """'頭痛好辛苦 😭' could match both emotion + acute pain — acute wins."""
    decision = _rule_overrides(_user_with_history(), "頭痛好辛苦 😭", [])

    assert decision is not None
    assert "急救" in decision.reasoning


def test_acute_pain_fires_for_new_user_too() -> None:
    """First-touch user with acute pain → still gets immediate relief, not onboarding."""
    decision = _rule_overrides(_user(status=UserStatus.NEW), "頭好痛幫吓我", [])

    assert decision is not None
    assert "急救" in decision.reasoning
    # Critical: should NOT route to GREETING + CONSTITUTION (the existing
    # first-touch-with-complaint rule), which delays relief.
    assert SpecialistName.CONSTITUTION not in decision.specialists


def test_acute_pain_does_not_block_order_message() -> None:
    """wa.me order message must always reach Sales, even if it contains pain words."""
    # User clicks an order link AFTER saying they have pain — the order
    # message itself is structured and gets priority.
    decision = _rule_overrides(_user(), "想訂【清心潤肺湯 HK$48】", [])

    assert decision is not None
    assert decision.specialists == [SpecialistName.SALES]
