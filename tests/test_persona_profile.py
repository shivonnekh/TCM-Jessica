"""Tests for the PersonaProfile abstraction (Phase 0 scaffolding).

These tests exercise pure data-modelling — no LLM calls. The critical
assertion (per the migration plan) is that ``default_jessica_profile()``
captures TODAY'S hardcoded WhatsApp pipeline constants exactly, so that
threading ``profile=None`` (or the default Jessica profile) through the
pipeline is provably a no-op.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from src.agents.base import SpecialistName
from src.agents.writer import MAX_BUBBLES
from src.personas.profile import (
    PersonaProfile,
    default_jessica_profile,
    load_chloe_profile,
    load_jackie_profile,
)

# ---------------------------------------------------------------------
# PersonaProfile — construction / validation
# ---------------------------------------------------------------------


def _minimal_kwargs(**overrides):
    base = dict(
        key="test",
        language="yue",
        identity_name="Tester",
        allowed_specialists=frozenset({"faq"}),
        brand_policy="test policy",
    )
    base.update(overrides)
    return base


def test_persona_profile_is_frozen() -> None:
    profile = PersonaProfile(**_minimal_kwargs())
    with pytest.raises(FrozenInstanceError):
        profile.key = "changed"  # type: ignore[misc]


def test_persona_profile_rejects_empty_key() -> None:
    with pytest.raises(ValueError):
        PersonaProfile(**_minimal_kwargs(key=""))


def test_persona_profile_rejects_invalid_language() -> None:
    with pytest.raises(ValueError):
        PersonaProfile(**_minimal_kwargs(language="fr"))


def test_persona_profile_rejects_empty_identity_name() -> None:
    with pytest.raises(ValueError):
        PersonaProfile(**_minimal_kwargs(identity_name=""))


def test_persona_profile_rejects_empty_allowed_specialists() -> None:
    with pytest.raises(ValueError):
        PersonaProfile(**_minimal_kwargs(allowed_specialists=frozenset()))


def test_persona_profile_rejects_zero_max_bubbles() -> None:
    with pytest.raises(ValueError):
        PersonaProfile(**_minimal_kwargs(max_bubbles=0))


def test_persona_profile_defaults() -> None:
    profile = PersonaProfile(**_minimal_kwargs())
    assert profile.greeting_bubbles == ()
    assert profile.greeting_media_url == ""
    assert profile.max_bubbles == 5
    assert profile.tongue_read_only is False


# ---------------------------------------------------------------------
# default_jessica_profile() — MUST match today's hardcoded constants.
# ---------------------------------------------------------------------


def test_jessica_profile_key_and_language() -> None:
    profile = default_jessica_profile()
    assert profile.key == "jessica"
    assert profile.language == "yue"
    assert profile.identity_name == "Jessica"


def test_jessica_profile_max_bubbles_matches_writer_constant() -> None:
    """Pull the ACTUAL current constant from writer.py — don't invent a new one."""
    profile = default_jessica_profile()
    assert profile.max_bubbles == MAX_BUBBLES


def test_jessica_profile_allows_every_specialist() -> None:
    """Jessica's WhatsApp pipeline routes to the full specialist registry
    today — no commerce restriction, no tongue_read_only gating."""
    profile = default_jessica_profile()
    all_names = {name.value for name in SpecialistName}
    assert profile.allowed_specialists == all_names


def test_jessica_profile_is_not_tongue_read_only() -> None:
    assert default_jessica_profile().tongue_read_only is False


def test_jessica_profile_greeting_matches_greetings_json() -> None:
    """Greeting content should reflect the SAME source GreetingAgent uses
    (data/greetings.json first_touch_clean), not a re-typed duplicate."""
    from src.agents.greeting_agent import _load_greetings

    profile = default_jessica_profile()
    expected_bubbles = tuple(
        str(b) for b in _load_greetings().get("first_touch_clean", {}).get("bubbles", [])
    )
    assert profile.greeting_bubbles == expected_bubbles
    assert profile.greeting_media_url  # non-empty — greetings.json has a portrait


def test_jessica_profile_is_frozen_and_reusable() -> None:
    p1 = default_jessica_profile()
    p2 = default_jessica_profile()
    assert p1 == p2


# ---------------------------------------------------------------------
# Jackie / Chloe loaders — read the 3 new JSON fields, don't break
# existing fields ChloeAgent still consumes.
# ---------------------------------------------------------------------


def test_jackie_profile_language_and_scope() -> None:
    profile = load_jackie_profile()
    assert profile.key == "jackie"
    assert profile.language == "en"
    assert profile.tongue_read_only is True
    assert "sales" not in profile.allowed_specialists
    assert "appointment" not in profile.allowed_specialists
    assert "faq" in profile.allowed_specialists
    assert "casual" in profile.allowed_specialists
    assert "constitution" in profile.allowed_specialists


def test_jackie_profile_has_brand_policy() -> None:
    profile = load_jackie_profile()
    assert profile.brand_policy.strip()


def test_chloe_profile_language_and_scope() -> None:
    profile = load_chloe_profile()
    assert profile.key == "chloe"
    assert profile.language == "yue"
    assert profile.tongue_read_only is True
    assert "sales" not in profile.allowed_specialists
    assert "appointment" not in profile.allowed_specialists


def test_chloe_profile_has_brand_policy() -> None:
    profile = load_chloe_profile()
    assert profile.brand_policy.strip()


def test_jackie_json_still_has_fields_chloe_agent_reads() -> None:
    """Existing fields ChloeAgent depends on must survive untouched."""
    import json

    data = json.loads(Path("data/personas/jackie.json").read_text(encoding="utf-8"))
    for field in (
        "display_name",
        "greeting_bubbles",
        "greeting_media_url",
        "system_prompt",
        "model",
        "max_tokens",
        "max_bubbles",
    ):
        assert field in data, f"jackie.json missing existing field {field!r}"


def test_chloe_json_still_has_fields_chloe_agent_reads() -> None:
    import json

    data = json.loads(Path("data/personas/chloe.json").read_text(encoding="utf-8"))
    for field in (
        "display_name",
        "greeting_bubbles",
        "greeting_media_url",
        "system_prompt",
        "model",
        "max_tokens",
        "max_bubbles",
    ):
        assert field in data, f"chloe.json missing existing field {field!r}"


def test_load_jackie_profile_raises_on_missing_language(tmp_path) -> None:
    import json

    bad = tmp_path / "jackie_bad.json"
    bad.write_text(json.dumps({"allowed_specialists": ["faq"], "brand_policy": "x"}))
    with pytest.raises(ValueError):
        load_jackie_profile(bad)
