"""Tests for the enriched Sales product dict (functions + image, mandatory).

Post-launch fix 2026-05-26: previously Writer received only name + price,
so pitches looked like "抗病毒湯 $88" with no detail. Now all detail
fields surface so the Writer can render rich pitches.
"""

from __future__ import annotations

from src.agents.sales_agent import _product_dict, _product_dict_simple
from src.tools.product_catalog import Product, ProductMatch


def _sample_product() -> Product:
    return Product(
        product_id="soup_pengyu_jiedu",
        name="彭魚鰓解毒湯",
        product_type="soup",
        price_hkd=120,
        indications=("痘疹未清", "手腳濕疹", "暗瘡", "手足口病", "清熱解毒"),
        constitution_match=("濕熱", "陰虛火旺"),
        complaint_keywords=("痘", "暗瘡", "濕疹"),
        contraindications=("孕婦慎用", "脾胃虛寒者少飲"),
        key_benefit="清熱解毒，皮膚問題首選",
        image_url="data/media/products/soups/soup_pengyu_jiedu.png",
        purchase_url="https://wa.me/85252417448?text=test",
    )


# ---------------------------------------------------------------------------
# _product_dict_simple — used in re-shows + list views
# ---------------------------------------------------------------------------


def test_simple_dict_includes_indications() -> None:
    d = _product_dict_simple(_sample_product())
    assert d["indications"] == [
        "痘疹未清", "手腳濕疹", "暗瘡", "手足口病", "清熱解毒"
    ]


def test_simple_dict_includes_constitution_match() -> None:
    d = _product_dict_simple(_sample_product())
    assert d["constitution_match"] == ["濕熱", "陰虛火旺"]


def test_simple_dict_includes_key_benefit() -> None:
    d = _product_dict_simple(_sample_product())
    assert d["key_benefit"] == "清熱解毒，皮膚問題首選"


def test_simple_dict_includes_contraindications() -> None:
    d = _product_dict_simple(_sample_product())
    assert d["contraindications"] == ["孕婦慎用", "脾胃虛寒者少飲"]


def test_simple_dict_includes_price_display() -> None:
    """price_display falls back to f'HK${price_hkd}' when not on the Product."""
    d = _product_dict_simple(_sample_product())
    assert d["price_display"] == "HK$120"


def test_simple_dict_image_url_is_absolute() -> None:
    """Relative paths like data/media/... must be converted to absolute URLs
    so WhatsApp can fetch them."""
    d = _product_dict_simple(_sample_product())
    assert d["image_url"].startswith("http")
    assert "soup_pengyu_jiedu.png" in d["image_url"]


# ---------------------------------------------------------------------------
# _product_dict — used in active pitch flow
# ---------------------------------------------------------------------------


def test_full_dict_includes_indications() -> None:
    match = ProductMatch(
        product=_sample_product(),
        score=10.0,
        match_reasons=("symptom: 暗瘡",),
    )
    d = _product_dict(match, pitch_angles={})
    assert d["indications"] == [
        "痘疹未清", "手腳濕疹", "暗瘡", "手足口病", "清熱解毒"
    ]


def test_full_dict_includes_key_benefit() -> None:
    match = ProductMatch(
        product=_sample_product(),
        score=10.0,
        match_reasons=(),
    )
    d = _product_dict(match, pitch_angles={})
    assert d["key_benefit"] == "清熱解毒，皮膚問題首選"


def test_full_dict_image_url_absolute() -> None:
    match = ProductMatch(
        product=_sample_product(),
        score=10.0,
        match_reasons=(),
    )
    d = _product_dict(match, pitch_angles={})
    assert d["image_url"].startswith("http")


def test_full_dict_preserves_pitch_angle_hint() -> None:
    match = ProductMatch(
        product=_sample_product(),
        score=10.0,
        match_reasons=("symptom: 暗瘡",),
    )
    d = _product_dict(match, pitch_angles={"soup_pengyu_jiedu": "皮膚問題首選"})
    assert d["pitch_angle_hint"] == "皮膚問題首選"


def test_full_dict_match_reasons_preserved() -> None:
    match = ProductMatch(
        product=_sample_product(),
        score=10.0,
        match_reasons=("symptom: 暗瘡", "constitution: 濕熱"),
    )
    d = _product_dict(match, pitch_angles={})
    assert d["match_reasons"] == ["symptom: 暗瘡", "constitution: 濕熱"]


# ---------------------------------------------------------------------------
# Acceptance test — the full payload has everything Writer needs
# ---------------------------------------------------------------------------


def test_payload_has_all_required_fields_for_writer() -> None:
    """The Writer needs: name, price_display, indications, image_url at minimum.
    All other detail fields are bonus."""
    d = _product_dict_simple(_sample_product())
    for required in ("name", "price_display", "indications", "image_url"):
        assert d.get(required), f"missing required field: {required}"
    assert isinstance(d["indications"], list)
    assert len(d["indications"]) >= 1
