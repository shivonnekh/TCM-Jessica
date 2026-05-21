"""ProductCatalog — match user constitution / pain_points → paid products.

Loads the flat lookup at `data/products/product_catalog.json` (which mirrors
the per-card `products[]` arrays in `tcm_paid_soups.json` and
`tcm_paid_ointments.json`).

This is a *pure* tool — no LLM, no I/O after construction. The SalesAgent
calls `.match_products(...)` and gets back a ranked list of `(Product, score)`.

Scoring (deterministic):
  +5  if `constitution_match` includes the user's constitution
       (or the product matches "any" constitution)
  +3  per pain_point keyword that appears in
       `complaint_keywords` ∪ `indications`
  +1  small symmetric bump if the user's constitution keyword appears
       in the product's `indications` text (catches loose matches like
       「陰虛火旺」 vs 「陰虛」)
  -10 if `product_id` is already in `already_pitched`
       (heavily down-weighted to enforce "one new pitch per session")

Contraindication filtering happens BEFORE scoring:
  - If the user has any `pregnancy` signal (tag `pregnant`, or notes /
    pain_points mentioning 「孕婦」「懷孕」「pregnant」), products whose
    `contraindications` mention 孕婦忌 are excluded entirely.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger("tools.product_catalog")

DEFAULT_CATALOG_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "data"
    / "products"
    / "product_catalog.json"
)

# Phrases in `contraindications` that mean "absolutely no for pregnancy".
# We treat 慎用 / 慎 as "caution, ask doctor" — NOT a hard exclusion (the
# product card itself prompts the Writer to add a caveat). 忌 = exclude.
_PREGNANCY_HARD_BLOCK_MARKERS: tuple[str, ...] = (
    "孕婦忌",
    "孕婦不可",
    "活血藥",  # 川芎天麻湯 — labelled as such
)

# User-side signals that the user is pregnant.
_PREGNANCY_USER_SIGNALS: tuple[str, ...] = (
    "孕婦",
    "懷孕",
    "有 BB",
    "有BB",
    "pregnant",
    "pregnancy",
)


@dataclass(frozen=True)
class Product:
    """Immutable value object — one entry from product_catalog.json.

    We keep the raw dict accessible via `raw` for fields not formally
    typed here (e.g. `severity_match`, `english_name`, `key_benefit`).
    """

    product_id: str
    name: str
    product_type: str  # "soup" | "ointment"
    price_hkd: int
    image_url: str
    purchase_url: str
    indications: tuple[str, ...]
    constitution_match: tuple[str, ...]
    complaint_keywords: tuple[str, ...]
    contraindications: tuple[str, ...]
    key_benefit: str
    raw: dict[str, Any] = field(default_factory=dict, compare=False)

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> Product:
        return cls(
            product_id=str(raw["product_id"]),
            name=str(raw["name"]),
            product_type=str(raw.get("product_type", "soup")),
            price_hkd=int(raw.get("price_hkd", 0)),
            image_url=str(raw.get("image_url", "")),
            purchase_url=str(raw.get("purchase_url", "")),
            indications=tuple(raw.get("indications", [])),
            constitution_match=tuple(raw.get("constitution_match", [])),
            complaint_keywords=tuple(raw.get("complaint_keywords", [])),
            contraindications=tuple(raw.get("contraindications", [])),
            key_benefit=str(raw.get("key_benefit", "")),
            raw=raw,
        )


@dataclass(frozen=True)
class ProductMatch:
    """Result of scoring a product against a user."""

    product: Product
    score: float
    match_reasons: tuple[str, ...]


class ProductCatalog:
    """Pure-function product matcher backed by product_catalog.json."""

    def __init__(self, catalog_path: str | Path = DEFAULT_CATALOG_PATH) -> None:
        self._path = Path(catalog_path)
        self._products: list[Product] = []
        self.reload()

    # -----------------------------------------------------------------
    # Loading
    # -----------------------------------------------------------------

    def reload(self) -> None:
        data = json.loads(self._path.read_text(encoding="utf-8"))
        raw_products = data.get("products", [])
        self._products = [Product.from_raw(p) for p in raw_products]
        logger.debug("ProductCatalog loaded %d products", len(self._products))

    # -----------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------

    @property
    def all_products(self) -> list[Product]:
        return list(self._products)

    def get(self, product_id: str) -> Product | None:
        for p in self._products:
            if p.product_id == product_id:
                return p
        return None

    def match_products(
        self,
        *,
        constitution: str | None,
        pain_points: list[str] | tuple[str, ...] | None,
        already_pitched: list[str] | tuple[str, ...] | None = None,
        user_tags: list[str] | tuple[str, ...] | None = None,
        user_notes: str | None = None,
        product_type: str | None = None,
        max_results: int = 3,
        min_score: float = 1.0,
    ) -> list[ProductMatch]:
        """Score and rank products for this user.

        Args:
            constitution: TCM 體質 (e.g. "陰虛質", "濕熱質"). May include
                the trailing 質 character or not — we strip it.
            pain_points: List of user-mentioned complaints.
            already_pitched: Product IDs to heavily down-weight.
            user_tags: Free-form tags from CRM (used for pregnancy filter).
            user_notes: CRM notes (also scanned for pregnancy signal).
            product_type: Optional filter — "soup" or "ointment".
            max_results: Cap on returned matches (default 3).
            min_score: Minimum score required to be returned.

        Returns:
            List of ProductMatch, sorted by score descending. Already-pitched
            products are returned LAST (heavily penalised) but still present
            so the Sales Agent can see "I've already shown you all the
            relevant ones."
        """
        already = set(already_pitched or ())
        is_pregnant = _user_is_pregnant(
            tags=user_tags, notes=user_notes, pain_points=pain_points
        )

        norm_const = _normalise_constitution(constitution)
        pains = tuple(pain_points or ())

        matches: list[ProductMatch] = []
        for product in self._products:
            if product_type and product.product_type != product_type:
                continue
            if is_pregnant and _is_pregnancy_contraindicated(product):
                logger.debug(
                    "filtered pregnancy-contraindicated product %s",
                    product.product_id,
                )
                continue

            score, reasons = _score_product(
                product=product,
                constitution=norm_const,
                pain_points=pains,
                already_pitched=already,
            )
            if score < min_score:
                continue
            matches.append(
                ProductMatch(
                    product=product, score=score, match_reasons=tuple(reasons)
                )
            )

        matches.sort(key=lambda m: m.score, reverse=True)
        return matches[:max_results]


# ---------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------


def _normalise_constitution(raw: str | None) -> str:
    """Strip the trailing 質 character so '陰虛質' matches '陰虛'."""
    if not raw:
        return ""
    s = raw.strip()
    if s.endswith("質"):
        s = s[:-1]
    return s


def _user_is_pregnant(
    *,
    tags: list[str] | tuple[str, ...] | None,
    notes: str | None,
    pain_points: list[str] | tuple[str, ...] | None,
) -> bool:
    blob_parts: list[str] = []
    if tags:
        blob_parts.extend(tags)
    if notes:
        blob_parts.append(notes)
    if pain_points:
        blob_parts.extend(pain_points)
    blob = " ".join(blob_parts).lower()
    if not blob:
        return False
    if "pregnant" in blob or "pregnancy" in blob:
        return True
    return any(sig in blob for sig in ("孕婦", "懷孕", "有 bb", "有bb"))


def _is_pregnancy_contraindicated(product: Product) -> bool:
    text = " ".join(product.contraindications)
    return any(marker in text for marker in _PREGNANCY_HARD_BLOCK_MARKERS)


def _score_product(
    *,
    product: Product,
    constitution: str,
    pain_points: tuple[str, ...],
    already_pitched: set[str],
) -> tuple[float, list[str]]:
    score = 0.0
    reasons: list[str] = []

    # 1. Constitution match
    if constitution:
        for c in product.constitution_match:
            if c == "any":
                score += 1  # weak bump — universal product
                reasons.append("通用配方")
                break
            if constitution and (c == constitution or constitution in c or c in constitution):
                score += 5
                reasons.append(f"配合{constitution}體質")
                break

    # 2. Pain-point keyword match (complaint_keywords ∪ indications)
    haystack = set(product.complaint_keywords) | set(product.indications)
    matched_pains: list[str] = []
    for pain in pain_points:
        pain_lc = pain.strip()
        if not pain_lc:
            continue
        # bidirectional substring match — short pain like "頭痛" should
        # match keyword "偏頭痛" too
        for kw in haystack:
            if pain_lc == kw or pain_lc in kw or kw in pain_lc:
                score += 3
                matched_pains.append(pain_lc)
                break
    if matched_pains:
        # de-dup reason line
        unique = sorted(set(matched_pains))
        reasons.append(f"針對{'、'.join(unique[:3])}")

    # 3. Already-pitched penalty (NOT exclusion — keeps tie-break stable)
    if product.product_id in already_pitched:
        score -= 10
        reasons.append("已推介過")

    return score, reasons
