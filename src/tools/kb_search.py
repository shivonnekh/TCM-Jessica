"""KBSearch — query → ranked list of relevant cards.

Algorithm (no vector search at MVP):
  1. For each card, score it against the query:
     - Trigger-phrase match: +5 per phrase that appears in the query (or vice versa)
     - Title char-bigram match: +2 per shared bigram
     - Domain hint match: +3 if user query mentions the card's domain keyword
       (e.g. "湯水" → soups domain cards get a bump)
  2. Return top-K cards with score > threshold.

Scoring is deterministic — no LLM call. The LLM step happens in the
FAQ Agent AFTER retrieval, to extract structured facts from the top
cards.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from src.tools.kb_index import KBCard, KBIndex, _tokenize_zh

logger = logging.getLogger("tools.kb_search")

# Domain hint words → bump cards in that domain
_DOMAIN_HINTS: dict[str, tuple[str, ...]] = {
    "soups": ("湯水", "湯", "煲湯", "食譜", "茶飲", "食療"),
    "constitution": ("體質", "氣虛", "陽虛", "陰虛", "濕熱", "痰濕", "血瘀", "氣鬱", "脷"),
    "faq": (),  # generic — no specific keywords
}


@dataclass(frozen=True)
class SearchHit:
    card: KBCard
    score: float
    matched_phrases: tuple[str, ...]
    domain_bonus: float


class KBSearch:
    def __init__(self, index: KBIndex) -> None:
        self._index = index

    def search(
        self,
        query: str,
        *,
        top_k: int = 3,
        min_score: float = 3.0,
    ) -> list[SearchHit]:
        if not query or not query.strip():
            return []

        query_lc = query.strip().lower()
        query_bigrams = set(_tokenize_zh(query))

        hits: list[SearchHit] = []
        for card in self._index.all_cards():
            score, matched, dom_bonus = _score_card(card, query_lc, query_bigrams)
            if score >= min_score:
                hits.append(
                    SearchHit(
                        card=card,
                        score=score,
                        matched_phrases=matched,
                        domain_bonus=dom_bonus,
                    )
                )

        hits.sort(key=lambda h: h.score, reverse=True)
        return hits[:top_k]


def _score_card(
    card: KBCard, query_lc: str, query_bigrams: set[str]
) -> tuple[float, tuple[str, ...], float]:
    score = 0.0
    matched: list[str] = []

    # 1. Trigger phrase match — bidirectional substring
    for phrase in card.trigger_conditions:
        p = phrase.strip().lower()
        if not p:
            continue
        if p in query_lc or (len(p) >= 2 and p in query_lc):
            score += 5
            matched.append(phrase)
        elif len(p) >= 4 and query_lc in p:
            # query is contained inside a trigger phrase — weaker match
            score += 2
            matched.append(phrase)

    # 2. Title bigram match
    title_bigrams = set(_tokenize_zh(card.title))
    overlap = title_bigrams & query_bigrams
    score += 2 * len(overlap)

    # 3. Domain hint bump
    dom_bonus = 0.0
    for hint in _DOMAIN_HINTS.get(card.domain, ()):
        if hint in query_lc:
            dom_bonus += 3
    score += dom_bonus

    return score, tuple(matched), dom_bonus
