"""Tests for KBIndex — loads real cards from data/knowledge_base/."""

from __future__ import annotations

import pytest

from src.tools.kb_index import KBIndex


@pytest.fixture(scope="module")
def index() -> KBIndex:
    return KBIndex.load()


def test_index_loads_expected_card_count(index: KBIndex) -> None:
    # MANIFEST.md says 52 base cards across 3 domains;
    # +8 constitution deep-dive cards added 2026-05-27 (pinghe/yangxu/yinxu/
    # tanshi/shire/xueyu/qiyu/tebing — 氣虛 already existed) → 60.
    assert len(index) == 60


def test_known_soup_card_present(index: KBIndex) -> None:
    card = index.get_card("tcm_food_therapy_soups")
    assert card is not None
    assert card.domain == "soups"
    assert "湯水" in card.title or "湯" in card.title
    assert len(card.trigger_conditions) > 10


def test_constitution_card_present(index: KBIndex) -> None:
    card = index.get_card("tcm_constitution_assessment")
    assert card is not None
    assert card.domain == "constitution"


def test_every_card_has_core_answer(index: KBIndex) -> None:
    missing = [c.card_id for c in index.all_cards() if not c.core_answer]
    assert missing == [], f"cards missing core_answer: {missing}"


def test_phrase_index_built(index: KBIndex) -> None:
    phrases = index.all_phrases()
    # Should be far more phrases than cards (each card has 30-80)
    assert len(phrases) > len(index) * 10


def test_domains_balanced(index: KBIndex) -> None:
    by_domain: dict[str, int] = {}
    for c in index.all_cards():
        by_domain[c.domain] = by_domain.get(c.domain, 0) + 1
    # Should have all three domains populated
    assert set(by_domain.keys()) == {"soups", "constitution", "faq"}
