"""Tests for KBIndex — loads real cards from data/knowledge_base/."""

from __future__ import annotations

import pytest

from src.tools.kb_index import KBIndex


@pytest.fixture(scope="module")
def index() -> KBIndex:
    return KBIndex.load()


def test_index_loads_expected_card_count(index: KBIndex) -> None:
    # MANIFEST.md says 52 base cards. Two 2026-05-27 KB enhancement
    # pushes:
    #   First push (16 cards):
    #     - 8 constitution deep-dives (平和/陽虛/陰虛/痰濕/濕熱/血瘀/氣鬱/特稟)
    #     - 3 三高 cards (diabetes/hypertension/cholesterol)
    #     - 1 七情五臟 card
    #     - 2 men's health cards (kidney + prostate)
    #     - 1 中藥目錄 (40 herbs)
    #     - 1 24 節氣 養生
    #   Second push (3 cards, 辨證 layer addition):
    #     - tcm_anxiety_emotional (4 patterns: 肝鬱/心脾兩虛/痰火擾心/心腎不交)
    #     - tcm_nose_allergy (4 patterns: 肺氣虛/脾氣虛/腎陽虛/肺經鬱熱)
    #     - tcm_skin_itch (5 patterns: 風熱/風寒/血虛風燥/濕熱/血熱)
    # 52 + 16 + 3 = 71
    # Plus 6 existing cards enriched with 證型 enumeration (sleep, headache,
    # digestion bloating + stool, women's menstrual, cold/flu) — same count.
    assert len(index) == 71


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
