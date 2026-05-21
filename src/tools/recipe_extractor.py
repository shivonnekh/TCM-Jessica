"""RecipeExtractor — pull NAMED free recipes from KB cards.

Bug surfaced 2026-05-21: Constitution Agent declared 平和質 then
recommended "中醫湯水指南" — that's a KB CARD TITLE, not a recipe.
FAQ Agent same issue: returned abstract '128 款食譜' instead of
actual recipe names.

Both fixed by extracting structured recipe entries from
`supporting_points` of two soup cards:
  - tcm_food_therapy_soups.json (28 doctor recipes)
  - tcm_food_therapy_soups_top100.json (100 healthy-food.hk recipes)

Each entry already has {title, url, image_url, constitutions} —
we just need to index by constitution and serve.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger("tools.recipe_extractor")

DEFAULT_KB_SOUP_DIR = (
    Path(__file__).resolve().parent.parent.parent
    / "data" / "knowledge_base" / "soups"
)

# Cards we extract recipes from. Skip food_therapy_products (it's OTC
# product analysis like 枇杷膏, not recipes) + teas/seasonal (specialty).
_RECIPE_CARD_FILES = (
    "tcm_food_therapy_soups.json",            # 28 HK doctor recipes
    "tcm_food_therapy_soups_top100.json",     # 100 healthy-food.hk
)


@dataclass(frozen=True)
class Recipe:
    title: str
    url: str
    image_url: str
    constitutions: tuple[str, ...]   # e.g. ('氣虛質', '平和質')
    source_card: str
    rank: int = 0


class RecipeExtractor:
    def __init__(self, kb_soup_dir: str | Path = DEFAULT_KB_SOUP_DIR) -> None:
        self._recipes: list[Recipe] = []
        # index: constitution_value → list[Recipe]
        self._by_constitution: dict[str, list[Recipe]] = {}
        self._load(Path(kb_soup_dir))

    def _load(self, dir_: Path) -> None:
        total = 0
        for fname in _RECIPE_CARD_FILES:
            path = dir_ / fname
            if not path.is_file():
                logger.warning("recipe card missing: %s", path)
                continue
            data = json.loads(path.read_text(encoding="utf-8"))
            card = data.get("knowledge_card", data)
            sp = card.get("core_content", {}).get("supporting_points", []) or []
            for entry in sp:
                if not isinstance(entry, dict):
                    continue
                title = (entry.get("title") or "").strip()
                if not title:
                    continue
                # Skip pure section headers (no url + no image typically)
                if not entry.get("url") and not entry.get("image_url"):
                    continue
                cons_raw = entry.get("constitutions") or []
                cons = tuple(c for c in cons_raw if isinstance(c, str))
                recipe = Recipe(
                    title=title,
                    url=entry.get("url", ""),
                    image_url=entry.get("image_url", ""),
                    constitutions=cons,
                    source_card=card.get("metadata", {}).get("card_id", fname),
                    rank=int(entry.get("rank", 0)),
                )
                self._recipes.append(recipe)
                total += 1
                for c in cons:
                    self._by_constitution.setdefault(c, []).append(recipe)

        # Sort each constitution's recipes by rank (lower = more popular)
        for c, lst in self._by_constitution.items():
            lst.sort(key=lambda r: (r.rank or 999, r.title))
        logger.info(
            "RecipeExtractor: %d recipes indexed across %d constitutions",
            total, len(self._by_constitution),
        )

    # ─────────────────────────────────────────────────────────────

    def for_constitution(
        self, constitution_value: str, *, limit: int = 3
    ) -> list[Recipe]:
        """Return recipes matching the given constitution (e.g. '氣虛質')."""
        return list(self._by_constitution.get(constitution_value, []))[:limit]

    def popular(self, *, limit: int = 4) -> list[Recipe]:
        """Top recipes regardless of constitution (for vague queries)."""
        ranked = sorted(self._recipes, key=lambda r: r.rank or 999)
        return ranked[:limit]

    def all_count(self) -> int:
        return len(self._recipes)


def recipe_to_dict(r: Recipe) -> dict[str, Any]:
    """Serialise a Recipe into payload-friendly dict."""
    return {
        "title": r.title,
        "url": r.url,
        "image_url": r.image_url,
        "constitutions": list(r.constitutions),
        "source_card": r.source_card,
    }
