"""Byte-identity regression test — Phase 0 PersonaProfile refactor.

CRITICAL: this repo is LIVE (real WhatsApp customers via Jessica). The
Writer's system prompt drives every outbound message. This test proves
the profile-driven refactor of ``src.agents.writer._build_system_prompt``
does not change ANY character of the prompt Jessica actually uses.

Method:
  1. BEFORE refactoring writer.py, we captured the exact output of
     ``_build_system_prompt()`` (git SHA c95fa04, pre-PersonaProfile) into
     ``tests/fixtures/golden_writer_system_prompt.txt`` (verbatim, UTF-8).
  2. AFTER refactoring, this test asserts:
       - ``_build_system_prompt()``               (no args — legacy call site,
         e.g. admin_views.py's prompt_renderer)               == golden
       - ``_build_system_prompt(None)``            (explicit no-profile)     == golden
       - ``_build_system_prompt(default_jessica_profile())``  == golden

This is an EXACT string equality check, not an approximate/semantic one.
"""

from __future__ import annotations

from pathlib import Path

from src.agents.writer import _build_system_prompt
from src.personas.profile import default_jessica_profile

_GOLDEN_PATH = Path(__file__).resolve().parent / "fixtures" / "golden_writer_system_prompt.txt"


def _golden() -> str:
    return _GOLDEN_PATH.read_text(encoding="utf-8")


def test_golden_fixture_exists_and_is_nonempty() -> None:
    golden = _golden()
    assert len(golden) > 1000


def test_no_args_call_is_byte_identical_to_golden() -> None:
    """Legacy call site (admin_views.py prompt_renderer) — zero args."""
    assert _build_system_prompt() == _golden()


def test_explicit_none_profile_is_byte_identical_to_golden() -> None:
    assert _build_system_prompt(None) == _golden()


def test_default_jessica_profile_is_byte_identical_to_golden() -> None:
    assert _build_system_prompt(default_jessica_profile()) == _golden()


def test_none_and_default_profile_produce_identical_output() -> None:
    """profile=None and profile=default_jessica_profile() must be
    indistinguishable to any caller."""
    assert _build_system_prompt(None) == _build_system_prompt(default_jessica_profile())
