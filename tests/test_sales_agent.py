"""Tests for SalesAgent — offline mode (client=None)."""

from __future__ import annotations

import pytest

from src.agents.base import SpecialistInput, SpecialistName
from src.agents.sales_agent import SalesAgent, _is_purchase_confirmation
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
async def test_promotion_surfaces_consultation_offers_on_pitch(
    sales: SalesAgent,
) -> None:
    """Per the 2026-05-22 playbook update: 95-折 is reserved for
    post-consultation users (not first-pitch). On a normal pitch we
    surface the 免診金 / 視診包郵 hooks (consultation-first funnel)."""
    user = User(
        phone="+85291234567",
        constitution=Constitution.SHIRE,
        pain_points=["皮膚痕", "濕疹"],
        products_pitched=["soup_pengyu_jiedu"],
    )
    inp = SpecialistInput(user=user, user_message="呢個都岩，再睇下藥膏")
    output, _usage = await sales.run(inp)

    assert output.payload["intent"] == "pitch_products"
    offer_ids = [o["id"] for o in output.payload["active_offers"]]
    # At least one offer surfaces on any product pitch.
    assert offer_ids, "expected at least one offer to surface on a pitch"


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


# ---------------------------------------------------------------------------
# Purchase confirmation detection (keyword function)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "我訂咗",
        "訂咗喇",
        "落單咗",
        "落咗單",
        "買咗",
        "已經訂",
        "訂好咗",
        "搞掂",
        "done 喇",
        "付咗款",
        "已下單",
    ],
)
def test_is_purchase_confirmation_true(text: str) -> None:
    assert _is_purchase_confirmation(text) is True


@pytest.mark.parametrize(
    "text",
    [
        "我想訂",
        "點落單",
        "邊度買",
        "落單",        # present-tense, not past
        "想要",
        "幾錢",
        "",
        "你好",
    ],
)
def test_is_purchase_confirmation_false(text: str) -> None:
    assert _is_purchase_confirmation(text) is False


# ---------------------------------------------------------------------------
# Purchase confirmation routing + CRM diff
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_purchase_confirmation_sets_status_bought(sales: SalesAgent) -> None:
    """When user says '我訂咗' and has products_pitched, status becomes 'bought'."""
    user = User(
        phone="+85291234567",
        constitution=Constitution.SHIRE,
        products_pitched=["soup_pengyu_jiedu", "soup_sijun"],
    )
    inp = SpecialistInput(user=user, user_message="我訂咗喇，多謝！")
    output, _usage = await sales.run(inp)

    assert output.payload["intent"] == "purchase_confirmed"
    diff = output.suggested_user_state_diff
    assert diff.get("status") == "bought"
    assert "products_purchased_append" in diff
    # Should reference the last-pitched products
    assert diff["products_purchased_append"]  # non-empty


@pytest.mark.asyncio
async def test_purchase_confirmation_records_last_pitched(sales: SalesAgent) -> None:
    """products_purchased_append should contain the last ≤3 pitched products."""
    pitched = ["soup_a", "soup_b", "soup_c", "soup_d"]
    user = User(
        phone="+85291234567",
        products_pitched=pitched,
    )
    inp = SpecialistInput(user=user, user_message="落單咗！")
    output, _usage = await sales.run(inp)

    diff = output.suggested_user_state_diff
    # Should be last 3 of the pitched list
    assert diff["products_purchased_append"] == ["soup_b", "soup_c", "soup_d"]


@pytest.mark.asyncio
async def test_purchase_confirmation_skipped_when_no_pitched(
    sales: SalesAgent,
) -> None:
    """If user says '訂咗' but has never seen a pitch, treat as normal message."""
    user = User(
        phone="+85291234567",
        constitution=Constitution.SHIRE,
        products_pitched=[],  # ← never pitched anything
    )
    inp = SpecialistInput(user=user, user_message="訂咗喇")
    output, _usage = await sales.run(inp)

    # No pitch + no products → no_match (not purchase_confirmed)
    assert output.payload["intent"] != "purchase_confirmed"


@pytest.mark.asyncio
async def test_purchase_confirmed_writer_hint_present(sales: SalesAgent) -> None:
    """Purchase confirmed payload includes a writer_hint for the response."""
    user = User(
        phone="+85291234567",
        products_pitched=["soup_pengyu_jiedu"],
    )
    inp = SpecialistInput(user=user, user_message="買咗啦！")
    output, _usage = await sales.run(inp)

    assert output.payload["intent"] == "purchase_confirmed"
    assert "writer_hint" in output.payload
    assert "purchase_confirmed" in output.tools_called[0]["name"]
