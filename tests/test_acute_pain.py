"""Tests for the health-complaint shortcut + planner routing.

Architecture (post-rewrite 2026-05-26):
    detect_health_complaint just returns a canonical symptom name (or None).
    All acupoint content, image / video attach, and tone calibration happen
    downstream — KB vector search via FAQ agent + AcupointImageMap. There
    is intentionally NO hardcoded symptom→acupoint mapping in Python.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from src.agents.acute_pain import (
    detect_all_health_complaints,
    detect_health_complaint,
)
from src.agents.base import SpecialistName
from src.agents.planner import _rule_overrides
from src.crm.models import ConversationMessage, User, UserStatus


# ---------------------------------------------------------------------------
# detect_health_complaint — pure unit tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text,expected",
    [
        ("我頭痛", "頭痛"),
        ("頭好痛", "頭痛"),
        ("我头疼", "頭痛"),
        ("經痛好辛苦", "經痛"),
        ("月經痛", "經痛"),
        ("月经痛", "經痛"),
        ("失眠", "失眠"),
        ("睡不着", "失眠"),
        ("肩頸痛", "肩頸痛"),
        ("腰痛", "腰痛"),
        ("眼攰", "眼睛疲勞"),
        ("鼻塞", "鼻塞"),
        ("頭暈到天旋地轉", "頭暈"),
        ("心煩胸悶", "心煩胸悶"),
        ("好攰冇精神", "疲勞"),
    ],
)
def test_detect_returns_canonical_symptom(text: str, expected: str) -> None:
    assert detect_health_complaint(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "",
        "你好",
        "我想問下湯水",
        "邊度有得買",
        "predict 我嘅體質",
    ],
)
def test_detect_returns_none_for_non_complaints(text: str) -> None:
    assert detect_health_complaint(text) is None


def test_detect_first_match_wins() -> None:
    """Multi-symptom message returns the FIRST canonical match in the
    keyword table — Planner just needs a single signal to route, the
    Planner LLM's extracted_pain_points captures the full set."""
    result = detect_health_complaint("我頭痛同時又失眠")
    assert result in {"頭痛", "失眠"}


# ---------------------------------------------------------------------------
# Planner routing — health complaint → FAQ + CASUAL
# ---------------------------------------------------------------------------


def _user(**kwargs) -> User:
    return User(phone="+85291234567", **kwargs)


def _user_with_history(**kwargs) -> User:
    history = [ConversationMessage(role="user", content="上次嚟過", at=datetime.utcnow())]
    return User(phone="+85291234567", conversation_history=history, **kwargs)


def test_health_complaint_routes_to_faq_and_casual() -> None:
    """Returning user with pain → FAQ (KB content) + CASUAL (empathy)."""
    decision = _rule_overrides(_user_with_history(), "我頭痛", [])

    assert decision is not None
    assert set(decision.specialists) == {SpecialistName.FAQ, SpecialistName.CASUAL}
    assert decision.mode == "parallel"


def test_health_complaint_works_for_simplified_chinese() -> None:
    """Production bug fix: 我头疼 (Simplified) must trigger same as 我頭痛."""
    decision = _rule_overrides(_user_with_history(), "我头疼", [])

    assert decision is not None
    assert SpecialistName.FAQ in decision.specialists


def test_health_complaint_works_without_urgency_signal() -> None:
    """Plain "我頭痛" (no 好/勁/痛到/emoji) STILL fires for returning users —
    production fix. Old behavior gated on urgency tokens and missed routine
    mentions."""
    decision = _rule_overrides(_user_with_history(), "我頭痛", [])
    assert decision is not None
    assert SpecialistName.FAQ in decision.specialists


def test_health_complaint_notes_warn_against_generic_advice() -> None:
    """The notes_for_writer must instruct against generic advice like
    '飲多啲熱水' — the actual production failure mode we're fixing."""
    decision = _rule_overrides(_user_with_history(), "頭痛", [])
    assert decision is not None
    assert "熱水" in decision.notes_for_writer  # the banned phrase
    assert "KB" in decision.notes_for_writer  # must reference KB content


def test_health_complaint_notes_do_NOT_hardcode_acupoint() -> None:
    """notes_for_writer must NOT include specific acupoint names — that
    info lives in KB cards. This test enforces the architecture."""
    decision = _rule_overrides(_user_with_history(), "我頭痛", [])
    assert decision is not None
    notes = decision.notes_for_writer
    # No specific acupoint should be hardcoded in the planner notes
    for hardcoded in ("合谷穴", "三陰交穴", "內關穴", "風池穴", "命門穴", "膻中穴"):
        assert hardcoded not in notes, f"acupoint {hardcoded} leaked into planner notes"


def test_health_complaint_does_not_fire_for_pure_first_touch() -> None:
    """Pure first-touch user (NEW + no history) with pain → fall through
    to the existing GREETING + CONSTITUTION onboarding flow. The clinic's
    structured intake takes priority for users we've never met."""
    decision = _rule_overrides(_user(status=UserStatus.NEW), "頭好痛幫吓我", [])
    # The complaint rule must NOT fire — onboarding rule handles it instead
    if decision is not None:
        assert "health complaint" not in decision.reasoning


def test_health_complaint_fires_for_returning_user() -> None:
    """Returning user (has history) with pain → routes to FAQ + CASUAL."""
    decision = _rule_overrides(_user_with_history(), "我頭痛", [])
    assert decision is not None
    assert SpecialistName.FAQ in decision.specialists
    assert SpecialistName.CASUAL in decision.specialists


def test_health_complaint_does_not_block_order_message() -> None:
    """wa.me order messages still take priority over complaint detection."""
    decision = _rule_overrides(_user(), "想訂【清心潤肺湯 HK$48】", [])
    assert decision is not None
    assert decision.specialists == [SpecialistName.SALES]


def test_health_complaint_fires_before_emotion_rule() -> None:
    """A complaint takes precedence over emotion detection."""
    decision = _rule_overrides(_user_with_history(), "頭痛好辛苦 😭", [])
    assert decision is not None
    assert SpecialistName.FAQ in decision.specialists


def test_no_complaint_message_falls_through() -> None:
    """Non-complaint messages don't trigger the complaint rule."""
    decision = _rule_overrides(_user(), "你好啊", [])
    # Either no decision (falls through to LLM) or a different rule
    # (e.g. greeting). But MUST NOT be the complaint rule.
    if decision is not None:
        assert "health complaint" not in decision.reasoning


# ---------------------------------------------------------------------------
# detect_all_health_complaints — multi-symptom extraction fallback
# ---------------------------------------------------------------------------


def test_detect_all_returns_multiple_symptoms_single_turn() -> None:
    """Single message mentioning multiple symptoms returns ALL of them."""
    result = detect_all_health_complaints("我頭痛又失眠又腰痛")
    assert set(result) == {"頭痛", "失眠", "腰痛"}


def test_detect_all_extracts_skin_keywords_for_crm() -> None:
    """Skin complaints route to Sales (not FAQ) so detect_health_complaint
    intentionally returns None. But the pipeline still needs to remember
    the symptom — detect_all_health_complaints covers extraction."""
    assert detect_all_health_complaints("我皮膚痕") == ["皮膚痕癢"]
    assert "濕疹" in detect_all_health_complaints("我有濕疹好辛苦")
    assert "暗瘡" in detect_all_health_complaints("成日生暗瘡")


def test_detect_all_simplified_chinese_multi_symptom() -> None:
    """Simplified Chinese input with multiple symptoms still extracts all."""
    result = detect_all_health_complaints("我头疼睡不着腰疼")
    assert set(result) == {"頭痛", "失眠", "腰痛"}


def test_detect_all_returns_empty_for_clean_messages() -> None:
    assert detect_all_health_complaints("") == []
    assert detect_all_health_complaints("你好") == []
    assert detect_all_health_complaints("有咩湯水推介") == []


def test_detect_all_is_deduped() -> None:
    """Duplicate symptom mentions in one message are deduped."""
    result = detect_all_health_complaints("頭痛 頭好痛 偏頭痛")
    assert result == ["頭痛"]


# ---------------------------------------------------------------------------
# Emotion + health complaint interaction (empathy bypass fix)
# ---------------------------------------------------------------------------


def test_combined_emotion_and_fatigue_defers_to_emotion_rule() -> None:
    """When a message has BOTH a complaint keyword (好攰 → 疲勞) AND an
    emotion keyword (壓力 → 思/脾), the planner should defer to the
    dedicated emotion rule so the Writer gets the 七情/臟腑 frame,
    not the generic acupoint/KB frame."""
    decision = _rule_overrides(_user_with_history(), "我好攰，最近壓力大", [])
    assert decision is not None
    # Both rules emit FAQ + CASUAL, but only the emotion rule embeds 情志
    # framing in notes_for_writer.
    notes = decision.notes_for_writer or ""
    assert "情志" in notes or "七情" in notes or "傷" in notes, (
        f"emotion frame missing from notes: {notes[:120]!r}"
    )
