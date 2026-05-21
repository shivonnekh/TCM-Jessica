"""Tests for ProductCatalog — pure scoring + filtering, no LLM."""

from __future__ import annotations

import pytest

from src.tools.product_catalog import ProductCatalog


@pytest.fixture(scope="module")
def catalog() -> ProductCatalog:
    return ProductCatalog()


# -------------------------------------------------------------------
# Loading
# -------------------------------------------------------------------


def test_catalog_loads_all_products(catalog: ProductCatalog) -> None:
    # 10 soups + 3 ointments = 13
    assert len(catalog.all_products) == 13


def test_catalog_get_known_product(catalog: ProductCatalog) -> None:
    p = catalog.get("soup_chuanxiong_tianma")
    assert p is not None
    assert p.name == "川芎白芷天麻湯"
    assert p.product_type == "soup"


def test_catalog_get_unknown_returns_none(catalog: ProductCatalog) -> None:
    assert catalog.get("does_not_exist") is None


# -------------------------------------------------------------------
# Constitution boost
# -------------------------------------------------------------------


def test_constitution_match_boosts_score(catalog: ProductCatalog) -> None:
    # 陰虛 user with no pain points → should rank 陰虛-matching soups high
    matches = catalog.match_products(
        constitution="陰虛質",
        pain_points=[],
        max_results=5,
    )
    assert matches, "expected at least one match for 陰虛 user"
    top = matches[0]
    assert any(
        c == "陰虛" or "陰虛" in c
        for c in top.product.constitution_match
    )
    # Constitution match alone should produce ≥5 score
    assert top.score >= 5


def test_constitution_with_trailing_質_normalised(catalog: ProductCatalog) -> None:
    # "陰虛質" should match products whose constitution_match has "陰虛"
    matches = catalog.match_products(
        constitution="陰虛質",
        pain_points=[],
        max_results=3,
    )
    assert any(
        "陰虛" in c for m in matches for c in m.product.constitution_match
    )


# -------------------------------------------------------------------
# Pain-point match
# -------------------------------------------------------------------


def test_pain_point_keyword_boosts_score(catalog: ProductCatalog) -> None:
    # 頭痛 should boost 川芎白芷天麻湯 specifically
    matches = catalog.match_products(
        constitution="血瘀質",
        pain_points=["頭痛"],
        max_results=3,
    )
    ids = [m.product.product_id for m in matches]
    assert "soup_chuanxiong_tianma" in ids


def test_pain_point_substring_match(catalog: ProductCatalog) -> None:
    # User wrote "偏頭痛" — should still match soup whose keywords contain 頭痛
    matches = catalog.match_products(
        constitution=None,
        pain_points=["偏頭痛"],
        max_results=5,
    )
    ids = [m.product.product_id for m in matches]
    assert "soup_chuanxiong_tianma" in ids


# -------------------------------------------------------------------
# Already-pitched filter
# -------------------------------------------------------------------


def test_already_pitched_is_heavily_penalised(catalog: ProductCatalog) -> None:
    # Pitch the obvious-best product, then check it drops to bottom
    matches = catalog.match_products(
        constitution="血瘀質",
        pain_points=["頭痛"],
        already_pitched=["soup_chuanxiong_tianma"],
        max_results=10,
        min_score=-50,
    )
    ids = [m.product.product_id for m in matches]
    if "soup_chuanxiong_tianma" in ids:
        # Should not be at top anymore
        assert ids[0] != "soup_chuanxiong_tianma"


# -------------------------------------------------------------------
# Pregnancy contraindication filter
# -------------------------------------------------------------------


def test_pregnant_user_excludes_chuanxiong_tianma(catalog: ProductCatalog) -> None:
    # 川芎白芷天麻湯 has 「⚠️ 孕婦忌（活血藥）」
    matches = catalog.match_products(
        constitution="血瘀質",
        pain_points=["頭痛"],
        user_tags=["pregnant"],
        max_results=10,
    )
    ids = [m.product.product_id for m in matches]
    assert "soup_chuanxiong_tianma" not in ids


def test_pregnant_via_notes_excludes_chuanxiong(catalog: ProductCatalog) -> None:
    matches = catalog.match_products(
        constitution="血瘀質",
        pain_points=["頭痛"],
        user_notes="客戶提及自己 懷孕 中",
        max_results=10,
    )
    ids = [m.product.product_id for m in matches]
    assert "soup_chuanxiong_tianma" not in ids


# -------------------------------------------------------------------
# Product type filter
# -------------------------------------------------------------------


def test_product_type_filter_only_ointments(catalog: ProductCatalog) -> None:
    matches = catalog.match_products(
        constitution="濕熱質",
        pain_points=["皮膚痕"],
        product_type="ointment",
        max_results=5,
    )
    assert matches
    assert all(m.product.product_type == "ointment" for m in matches)


# -------------------------------------------------------------------
# No-input behaviour
# -------------------------------------------------------------------


def test_empty_input_returns_no_matches_above_threshold(
    catalog: ProductCatalog,
) -> None:
    # No constitution, no pain points → no signal → nothing above min_score=1
    matches = catalog.match_products(
        constitution=None,
        pain_points=[],
        max_results=5,
    )
    # "any"-constitution products get a weak +1 bump — they may surface but
    # the test only asserts we don't get junk above the soup_chuanxiong
    # (which needs real signal). Sanity check: no match score > 2.
    assert all(m.score <= 2 for m in matches)
