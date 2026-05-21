"""Tests for SalesAgent — offline mode (client=None)."""

from __future__ import annotations

import pytest

from src.agents.base import SpecialistInput, SpecialistName
from src.agents.sales_agent import SalesAgent
from src.crm.models import Constitution, User


@pytest.fixture(scope="module")
def sales() -> SalesAgent:
    # client=None → deterministic offline mode
    return SalesAgent(client=None)


@pytest.mark.asyncio
async def test_offline_pitches_top_match(sales: SalesAgent) -> None:
    user = User(
        phone="+85291234567",
        constitution=Constitution.XUEYU,  # 血瘀質
        pain_points=["頭痛"],
    )
    inp = SpecialistInput(user=user, user_message="頭好痛，有冇湯可以飲？")
    output, _usage = await sales.run(inp)

    assert output.specialist == SpecialistName.SALES
    payload = output.payload
    assert payload["intent"] == "pitch_products"
    ids = [p["product_id"] for p in payload["products_to_pitch"]]
    assert "soup_chuanxiong_tianma" in ids
    # ProductCatalog.match_products always logged as a tool call
    assert any(
        t["name"] == "ProductCatalog.match_products"
        for t in output.tools_called
    )


@pytest.mark.asyncio
async def test_already_pitched_filtered(sales: SalesAgent) -> None:
    user = User(
        phone="+85291234567",
        constitution=Constitution.XUEYU,
        pain_points=["頭痛"],
        products_pitched=["soup_chuanxiong_tianma"],
    )
    inp = SpecialistInput(user=user, user_message="仲有冇其他推介？")
    output, _usage = await sales.run(inp)

    ids = [p["product_id"] for p in output.payload["products_to_pitch"]]
    # The previously-pitched product must NOT be re-pitched
    assert "soup_chuanxiong_tianma" not in ids


@pytest.mark.asyncio
async def test_pregnant_user_excludes_blood_activating(sales: SalesAgent) -> None:
    user = User(
        phone="+85291234567",
        constitution=Constitution.XUEYU,
        pain_points=["頭痛"],
        tags=["pregnant"],
    )
    inp = SpecialistInput(user=user, user_message="頭痛得好辛苦")
    output, _usage = await sales.run(inp)

    ids = [p["product_id"] for p in output.payload["products_to_pitch"]]
    # 川芎白芷天麻湯 is 活血 → must be excluded for pregnant user
    assert "soup_chuanxiong_tianma" not in ids


@pytest.mark.asyncio
async def test_no_match_when_no_signal(sales: SalesAgent) -> None:
    user = User(phone="+85291234567")  # unknown constitution, no pain points
    inp = SpecialistInput(user=user, user_message="hi")
    output, _usage = await sales.run(inp)

    payload = output.payload
    assert payload["intent"] == "no_match"
    assert payload["products_to_pitch"] == []
    assert payload["no_match_reason"] is not None


@pytest.mark.asyncio
async def test_promotion_surfaces_at_closing_stage(sales: SalesAgent) -> None:
    # User has already been pitched once → stage should be follow_up or
    # closing, and the 95-折 promo (sales_close trigger) should surface.
    user = User(
        phone="+85291234567",
        constitution=Constitution.SHIRE,  # 濕熱質
        pain_points=["皮膚痕", "濕疹"],
        products_pitched=["soup_pengyu_jiedu"],
    )
    inp = SpecialistInput(user=user, user_message="呢個都岩，再睇下藥膏")
    output, _usage = await sales.run(inp)

    assert output.payload["intent"] == "pitch_products"
    offer_ids = [o["id"] for o in output.payload["active_offers"]]
    assert "package_5_pct_off_v1" in offer_ids


@pytest.mark.asyncio
async def test_suggested_state_diff_appends_pitched_ids(sales: SalesAgent) -> None:
    user = User(
        phone="+85291234567",
        constitution=Constitution.SHIRE,
        pain_points=["濕疹"],
    )
    inp = SpecialistInput(user=user, user_message="我有濕疹")
    output, _usage = await sales.run(inp)

    diff = output.suggested_user_state_diff
    assert "products_pitched_append" in diff
    assert diff["products_pitched_append"]  # non-empty
