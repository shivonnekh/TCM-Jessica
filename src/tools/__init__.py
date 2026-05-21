"""Specialist tools — pure functions / classes that specialists call.

A tool is NOT a specialist. A tool is a deterministic capability the
specialist can invoke. Examples:

- ClinicMatcher  — district → best clinic (used by Appointment Agent)
- KBSearch       — query → ranked card list (used by FAQ + Constitution)
- ProductRecommender — constitution / pain_points → product list

Tools own no LLM logic. They are testable as pure functions.
"""

from src.tools.clinic_matcher import ClinicMatch, ClinicMatcher
from src.tools.kb_index import KBCard, KBIndex
from src.tools.kb_search import KBSearch, SearchHit
from src.tools.product_catalog import Product, ProductCatalog, ProductMatch
from src.tools.promotions import PromotionsLoader

__all__ = [
    "ClinicMatch",
    "ClinicMatcher",
    "KBCard",
    "KBIndex",
    "KBSearch",
    "Product",
    "ProductCatalog",
    "ProductMatch",
    "PromotionsLoader",
    "SearchHit",
]
