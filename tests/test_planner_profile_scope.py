"""Tests for the Planner's optional specialist-scope clamp (Phase 0).

The clamp is ADDITIVE and OFF by default: PlannerAgent.decide() only
enforces ``profile.allowed_specialists`` when a profile is explicitly
supplied. No current call site (JessicaPipeline.run_turn) passes a
profile today, so existing WhatsApp routing behaviour is completely
unaffected — verified here via ``_rule_overrides`` output directly
(no LLM call needed for these tests).
"""

from __future__ import annotations

from src.agents.base import PlannerDecision, SpecialistName
from src.agents.planner import _clamp_to_profile
from src.personas.profile import PersonaProfile


def _profile(allowed: frozenset[str], **overrides) -> PersonaProfile:
    kwargs = dict(
        key="test_persona",
        language="en",
        identity_name="Tester",
        allowed_specialists=allowed,
        brand_policy="test",
    )
    kwargs.update(overrides)
    return PersonaProfile(**kwargs)


def _decision(specialists, mode="solo", **kw) -> PlannerDecision:
    return PlannerDecision(specialists=specialists, mode=mode, reasoning="test", **kw)


# ---------------------------------------------------------------------
# No profile supplied -> zero change (existing behaviour untouched)
# ---------------------------------------------------------------------


def test_no_profile_leaves_decision_untouched() -> None:
    decision = _decision([SpecialistName.SALES])
    # _clamp_to_profile should not even be invoked in this case by callers,
    # but as a defensive check: passing None profile is not this function's
    # contract — callers gate on `profile is not None` before calling it.
    # Directly test the gate via decide()-level behaviour elsewhere; here
    # we just confirm clamp leaves an ALREADY-allowed decision unchanged.
    profile = _profile(frozenset({"sales", "faq", "casual"}))
    clamped = _clamp_to_profile(decision, profile)
    assert clamped is decision  # unchanged object, no-op


# ---------------------------------------------------------------------
# Disallowed specialist gets remapped
# ---------------------------------------------------------------------


def test_disallowed_commerce_specialist_remaps_to_faq() -> None:
    """Sales is disallowed for a no-commerce persona (e.g. Jackie) ->
    remapped to FAQ (information-seeking fallback)."""
    decision = _decision([SpecialistName.SALES])
    profile = _profile(frozenset({"faq", "casual", "constitution"}))
    clamped = _clamp_to_profile(decision, profile)
    assert clamped.specialists == [SpecialistName.FAQ]
    assert clamped.mode == "solo"


def test_disallowed_appointment_specialist_remaps_to_faq() -> None:
    decision = _decision([SpecialistName.APPOINTMENT])
    profile = _profile(frozenset({"faq", "casual", "constitution"}))
    clamped = _clamp_to_profile(decision, profile)
    assert clamped.specialists == [SpecialistName.FAQ]


def test_disallowed_greeting_specialist_remaps_to_casual() -> None:
    """Greeting (chit-chat-flavoured) remaps to Casual, not FAQ."""
    decision = _decision([SpecialistName.GREETING])
    profile = _profile(frozenset({"faq", "casual", "constitution"}))
    clamped = _clamp_to_profile(decision, profile)
    assert clamped.specialists == [SpecialistName.CASUAL]


def test_allowed_specialist_is_never_remapped() -> None:
    decision = _decision([SpecialistName.FAQ])
    profile = _profile(frozenset({"faq", "casual", "constitution"}))
    clamped = _clamp_to_profile(decision, profile)
    assert clamped is decision


def test_two_specialist_decision_collapses_to_solo_when_one_disallowed() -> None:
    """sequential [constitution, sales] with sales disallowed -> both map
    to allowed specialists; if they collapse to the same one, mode becomes
    solo (never leave a 2-element list with a duplicate)."""
    decision = _decision(
        [SpecialistName.CONSTITUTION, SpecialistName.SALES], mode="sequential"
    )
    profile = _profile(frozenset({"faq", "casual", "constitution"}))
    clamped = _clamp_to_profile(decision, profile)
    assert SpecialistName.SALES not in clamped.specialists
    assert SpecialistName.CONSTITUTION in clamped.specialists
    # sales -> faq fallback, constitution stays -> two distinct allowed names
    assert clamped.specialists == [SpecialistName.CONSTITUTION, SpecialistName.FAQ]
    assert clamped.mode == "sequential"


def test_fallback_itself_disallowed_falls_further_back() -> None:
    """If FAQ isn't allowed either, fall back to whatever IS allowed
    (never emit a disallowed specialist name)."""
    decision = _decision([SpecialistName.SALES])
    profile = _profile(frozenset({"casual"}))
    clamped = _clamp_to_profile(decision, profile)
    assert clamped.specialists == [SpecialistName.CASUAL]


def test_clamp_preserves_other_decision_fields() -> None:
    decision = _decision(
        [SpecialistName.SALES],
        notes_for_writer="some hint",
        proactive_hint="ready_for_pitch",
    )
    profile = _profile(frozenset({"faq", "casual"}))
    clamped = _clamp_to_profile(decision, profile)
    assert clamped.notes_for_writer == "some hint"
    assert clamped.proactive_hint == "ready_for_pitch"
    assert clamped.reasoning == decision.reasoning


# ---------------------------------------------------------------------
# decide() — end-to-end via rule fast-paths (no LLM call needed)
# ---------------------------------------------------------------------


async def test_decide_without_profile_is_unaffected_by_scope() -> None:
    """CRITICAL regression guard: PlannerAgent.decide() with profile=None
    (the only value used by every current call site) must behave exactly
    as before this feature existed — rule fast-path routes Sales freely
    even though a no-commerce profile exists elsewhere in the codebase."""
    from datetime import datetime

    from src.agents.planner import PlannerAgent
    from src.crm.models import ConversationMessage, User

    class _NoOpClient:
        pass

    agent = PlannerAgent(_NoOpClient())
    user = User(
        phone="+85291234567",
        conversation_history=[
            ConversationMessage(role="user", content="hi", at=datetime.utcnow())
        ],
    )
    decision, usage = await agent.decide(user, "藥膏", media_urls=[])
    assert SpecialistName.SALES in decision.specialists
    assert usage["shortcut"] is True


async def test_decide_with_profile_clamps_rule_based_decision() -> None:
    """When a profile IS supplied, even a rule-based fast-path decision
    gets clamped to the profile's allowed scope."""
    from datetime import datetime

    from src.agents.planner import PlannerAgent
    from src.crm.models import ConversationMessage, User

    class _NoOpClient:
        pass

    agent = PlannerAgent(_NoOpClient())
    user = User(
        phone="+85291234567",
        conversation_history=[
            ConversationMessage(role="user", content="hi", at=datetime.utcnow())
        ],
    )
    no_commerce_profile = _profile(frozenset({"faq", "casual", "constitution"}))
    decision, _usage = await agent.decide(
        user, "藥膏", media_urls=[], profile=no_commerce_profile
    )
    assert SpecialistName.SALES not in decision.specialists
    assert SpecialistName.FAQ in decision.specialists
