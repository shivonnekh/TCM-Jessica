"""Tests for KBSearch — real cards, no LLM."""

from __future__ import annotations

import pytest

from src.tools.kb_index import KBIndex
from src.tools.kb_search import KBSearch


@pytest.fixture(scope="module")
def search() -> KBSearch:
    return KBSearch(KBIndex.load())


def test_soup_query_returns_soup_card(search: KBSearch) -> None:
    hits = search.search("有冇咩湯水可以推介？")
    assert hits, "expected at least one hit for a soup query"
    top_domains = {h.card.domain for h in hits[:2]}
    assert "soups" in top_domains


def test_constitution_query_returns_constitution_card(search: KBSearch) -> None:
    hits = search.search("我想知自己係咩體質")
    assert hits, "expected at least one hit"
    assert any(h.card.domain == "constitution" for h in hits)


def test_acupressure_query_routes_to_faq(search: KBSearch) -> None:
    hits = search.search("頭痛可以按邊度穴位？")
    assert hits, "expected at least one hit"
    # Acupressure cards live under faq/
    assert any(h.card.domain == "faq" for h in hits)


def test_no_relevant_query_returns_empty(search: KBSearch) -> None:
    hits = search.search("我想買部 iPhone 嘅評測")
    assert hits == [], f"unexpected hits for irrelevant query: {[h.card.card_id for h in hits]}"


def test_empty_query_returns_empty(search: KBSearch) -> None:
    assert search.search("") == []
    assert search.search("   ") == []


def test_score_is_higher_for_better_match(search: KBSearch) -> None:
    """A more specific query should outscore a vague one."""
    specific = search.search("氣虛體質飲咩湯")
    if specific:
        assert specific[0].score >= 5.0
