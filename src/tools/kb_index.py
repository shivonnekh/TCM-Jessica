"""KB Index — loads all knowledge cards at startup, builds search index.

Per CLAUDE.md §3, knowledge access is card-driven. Each card has a
manually-curated `overview.trigger_conditions` array (typically 30-80
phrases per card) — these are the primary retrieval signal.

Card schema (consistent across all 52 cards):
    {
        "knowledge_card": {  # OR top-level
            "metadata": { "card_id", "domain", "category", ... },
            "overview": {
                "title": str,
                "objective": str,
                "trigger_conditions": [str, ...],   # PRIMARY signal
                "patient_profile": [str, ...]
            },
            "core_content": {
                "core_answer": str,
                "supporting_points": [str, ...],
                "evidence_level": str,
                "next_best_question": str
            },
            ...
        }
    }
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

logger = logging.getLogger("tools.kb_index")

DEFAULT_KB_ROOT = (
    Path(__file__).resolve().parent.parent.parent / "data" / "knowledge_base"
)

# Subdirectories that contain cards
_DOMAIN_SUBDIRS = ("soups", "constitution", "faq")


class KBCard(BaseModel):
    """In-memory representation of one knowledge card."""

    model_config = ConfigDict(frozen=True)

    card_id: str
    domain: str  # "soups" | "constitution" | "faq" (folder-based)
    category: str  # from metadata
    title: str
    objective: str
    trigger_conditions: tuple[str, ...]
    patient_profile: tuple[str, ...]
    core_answer: str
    supporting_points: tuple[str, ...]
    evidence_level: str
    next_best_question: str
    source_path: str  # relative to KB root, for debug

    @property
    def short_excerpt(self) -> str:
        """First ~300 chars of core_answer — for retrieval-result preview."""
        return self.core_answer[:300]


class KBIndex:
    """All cards loaded into memory + a normalized trigger-phrase index."""

    def __init__(self, cards: list[KBCard]) -> None:
        self._cards: dict[str, KBCard] = {c.card_id: c for c in cards}

        # Inverted index: lowercased trigger phrase → set of card_ids
        # Card titles also indexed.
        self._phrase_to_cards: dict[str, set[str]] = {}
        for card in cards:
            for phrase in card.trigger_conditions:
                key = _normalize(phrase)
                if not key:
                    continue
                self._phrase_to_cards.setdefault(key, set()).add(card.card_id)
            # Title words too
            for word in _tokenize_zh(card.title):
                self._phrase_to_cards.setdefault(word, set()).add(card.card_id)

        logger.info(
            "KBIndex loaded: %d cards, %d unique trigger phrases",
            len(self._cards),
            len(self._phrase_to_cards),
        )

    def __len__(self) -> int:
        return len(self._cards)

    def get_card(self, card_id: str) -> KBCard | None:
        return self._cards.get(card_id)

    def all_cards(self) -> list[KBCard]:
        return list(self._cards.values())

    def all_phrases(self) -> dict[str, set[str]]:
        """Read-only view of the inverted index — useful for tests/debug."""
        return self._phrase_to_cards

    # -----------------------------------------------------------------
    # Factory
    # -----------------------------------------------------------------

    @classmethod
    def load(cls, kb_root: str | Path = DEFAULT_KB_ROOT) -> "KBIndex":
        root = Path(kb_root)
        cards: list[KBCard] = []

        for subdir in _DOMAIN_SUBDIRS:
            domain_dir = root / subdir
            if not domain_dir.is_dir():
                logger.warning("KB subdir missing: %s", domain_dir)
                continue
            for json_path in sorted(domain_dir.glob("*.json")):
                try:
                    card = _load_card(json_path, domain=subdir, kb_root=root)
                except Exception as exc:  # noqa: BLE001
                    logger.error("failed to load card %s: %s", json_path, exc)
                    continue
                cards.append(card)

        return cls(cards)


# -------------------------------------------------------------------
# Loading + normalization helpers
# -------------------------------------------------------------------


def _load_card(path: Path, *, domain: str, kb_root: Path) -> KBCard:
    raw = json.loads(path.read_text(encoding="utf-8"))
    # Some cards wrap in "knowledge_card", others are top-level
    card_data = raw.get("knowledge_card", raw)

    metadata = card_data.get("metadata", {})
    overview = card_data.get("overview", {})
    core = card_data.get("core_content", {})

    return KBCard(
        card_id=metadata.get("card_id") or path.stem,
        domain=domain,
        category=str(metadata.get("category", "")),
        title=str(overview.get("title", "")),
        objective=str(overview.get("objective", "")),
        trigger_conditions=tuple(overview.get("trigger_conditions", []) or []),
        patient_profile=tuple(overview.get("patient_profile", []) or []),
        core_answer=str(core.get("core_answer", "")),
        supporting_points=tuple(
            str(p) for p in (core.get("supporting_points") or [])
        ),
        evidence_level=str(core.get("evidence_level", "")),
        next_best_question=str(core.get("next_best_question", "")),
        source_path=str(path.relative_to(kb_root)),
    )


def _normalize(s: str) -> str:
    """Lowercase + strip — used for matching keys."""
    return s.strip().lower()


def _tokenize_zh(text: str) -> list[str]:
    """Extract significant tokens from Chinese title text.

    Naive char-level n-gram windowing for Chinese (no jieba dependency).
    For ASCII words just lowercase-split.
    Returns 2- and 3-char Chinese substrings + ASCII words.
    """
    out: list[str] = []
    n = len(text)
    for size in (2, 3):
        for i in range(n - size + 1):
            chunk = text[i : i + size]
            if _is_zh_chunk(chunk):
                out.append(chunk)

    # ASCII fallback
    import re

    for w in re.findall(r"[A-Za-z]{3,}", text):
        out.append(w.lower())

    return out


def _is_zh_chunk(s: str) -> bool:
    return all("一" <= ch <= "鿿" for ch in s)
