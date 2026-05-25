"""Tests for SalesAgent — offline mode (client=None)."""

from __future__ import annotations

import pytest

from src.agents.base import SpecialistInput, SpecialistName
from src.agents.sales_agent import (
    SalesAgent,
    _TS_AWAITING_ADDRESS,
    _TS_PENDING_ORDER_NAME,
    _is_address_content,
    _is_purchase_confirmation,
    _parse_order_message,
)
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


# ---------------------------------------------------------------------------
# wa.me order message detection + parsing
# ---------------------------------------------------------------------------


def test_parse_order_message_valid(sales: SalesAgent) -> None:
    """Standard wa.me pre-filled order message is parsed correctly."""
    catalog = sales._catalog
    result = _parse_order_message("想訂【彭魚鰓解毒湯 HK$120】", catalog)
    assert result is not None
    assert result.product_name == "彭魚鰓解毒湯"
    assert result.price_hkd == 120
    assert result.product_id is not None  # should match catalog


def test_parse_order_message_unknown_product(sales: SalesAgent) -> None:
    """Order message with unknown product name — still parses, product_id is None."""
    catalog = sales._catalog
    result = _parse_order_message("想訂【神秘靚湯 HK$999】", catalog)
    assert result is not None
    assert result.product_name == "神秘靚湯"
    assert result.price_hkd == 999
    assert result.product_id is None  # not in catalog


def test_parse_order_message_invalid(sales: SalesAgent) -> None:
    """Regular messages do NOT match order format."""
    catalog = sales._catalog
    for text in ["我想訂湯", "幾錢？", "我訂咗", "", "hello"]:
        assert _parse_order_message(text, catalog) is None, f"False positive for: {text!r}"


@pytest.mark.asyncio
async def test_order_received_sets_status_bought(sales: SalesAgent) -> None:
    """wa.me order message → status=bought + products_purchased recorded."""
    user = User(phone="+85291234567", constitution=Constitution.SHIRE)
    inp = SpecialistInput(user=user, user_message="想訂【彭魚鰓解毒湯 HK$120】")
    output, _usage = await sales.run(inp)

    assert output.payload["intent"] == "order_received"
    assert output.payload["ordered_product_name"] == "彭魚鰓解毒湯"
    diff = output.suggested_user_state_diff
    assert diff.get("status") == "bought"
    assert diff.get("products_purchased_append")


@pytest.mark.asyncio
async def test_order_received_asks_address_when_unknown(sales: SalesAgent) -> None:
    """User with no location → payload flags needs_delivery_address=True."""
    user = User(phone="+85291234567")  # no location/district
    inp = SpecialistInput(user=user, user_message="想訂【清心潤肺湯 HK$48】")
    output, _usage = await sales.run(inp)

    assert output.payload["intent"] == "order_received"
    assert output.payload["needs_delivery_address"] is True
    assert "address" in output.payload["writer_hint"].lower() or "地址" in output.payload["writer_hint"]


@pytest.mark.asyncio
async def test_order_received_skips_address_when_known(sales: SalesAgent) -> None:
    """User with known district → payload flags needs_delivery_address=False."""
    user = User(phone="+85291234567", district="旺角")
    inp = SpecialistInput(user=user, user_message="想訂【清肝明目湯 HK$68】")
    output, _usage = await sales.run(inp)

    assert output.payload["needs_delivery_address"] is False


# ---------------------------------------------------------------------------
# Delivery address state machine
# ---------------------------------------------------------------------------


def test_is_address_content_true() -> None:
    valid = [
        "九龍旺角彌敦道123號",
        "陳大文，旺角，9876 5432",
        "荃灣青山公路450號",
        "我係沙田住",
    ]
    for text in valid:
        assert _is_address_content(text) is True, f"Should be address: {text!r}"


def test_is_address_content_false() -> None:
    invalid = [
        "幾時到？",
        "係咪要埋電話？",
        "好",
        "ok",
        "",
        "送到哪裡？",
    ]
    for text in invalid:
        assert _is_address_content(text) is False, f"Should NOT be address: {text!r}"


@pytest.mark.asyncio
async def test_order_received_sets_awaiting_address_temp_state(
    sales: SalesAgent,
) -> None:
    """After order received, temp_state marks awaiting_delivery=True."""
    user = User(phone="+85291234567")  # no location
    inp = SpecialistInput(user=user, user_message="想訂【彭魚鰓解毒湯 HK$120】")
    output, _ = await sales.run(inp)

    diff = output.suggested_user_state_diff
    ts = diff.get("temp_state", {})
    assert ts.get(_TS_AWAITING_ADDRESS) is True
    assert ts.get(_TS_PENDING_ORDER_NAME) == "彭魚鰓解毒湯"


@pytest.mark.asyncio
async def test_order_received_no_awaiting_when_address_known(
    sales: SalesAgent,
) -> None:
    """If user already has district, awaiting_delivery should be False."""
    user = User(phone="+85291234567", district="旺角")
    inp = SpecialistInput(user=user, user_message="想訂【清心潤肺湯 HK$48】")
    output, _ = await sales.run(inp)

    ts = output.suggested_user_state_diff.get("temp_state", {})
    assert ts.get(_TS_AWAITING_ADDRESS) is False


@pytest.mark.asyncio
async def test_address_reply_saves_location_and_clears_state(
    sales: SalesAgent,
) -> None:
    """User sends address → location saved, temp_state cleared."""
    user = User(
        phone="+85291234567",
        temp_state={
            _TS_AWAITING_ADDRESS: True,
            _TS_PENDING_ORDER_NAME: "彭魚鰓解毒湯",
        },
    )
    address = "陳大文，旺角彌敦道123號，9876 5432"
    inp = SpecialistInput(user=user, user_message=address)
    output, _ = await sales.run(inp)

    assert output.payload["intent"] == "delivery_address_received"
    diff = output.suggested_user_state_diff
    assert diff.get("location") == address
    # temp_state must be cleared of the awaiting flag
    remaining_ts = diff.get("temp_state", {})
    assert _TS_AWAITING_ADDRESS not in remaining_ts


@pytest.mark.asyncio
async def test_address_reply_extracts_district(sales: SalesAgent) -> None:
    """District extracted from address text and saved to user.district."""
    user = User(
        phone="+85291234567",
        temp_state={_TS_AWAITING_ADDRESS: True, _TS_PENDING_ORDER_NAME: "湯"},
    )
    inp = SpecialistInput(user=user, user_message="我係旺角，彌敦道999號，陳小姐")
    output, _ = await sales.run(inp)

    diff = output.suggested_user_state_diff
    assert diff.get("district") == "旺角"


@pytest.mark.asyncio
async def test_question_during_address_keeps_state(sales: SalesAgent) -> None:
    """User asks a question while awaiting address → state preserved, re-ask in hint."""
    user = User(
        phone="+85291234567",
        temp_state={_TS_AWAITING_ADDRESS: True, _TS_PENDING_ORDER_NAME: "彭魚鰓解毒湯"},
    )
    inp = SpecialistInput(user=user, user_message="係咪要埋電話號碼？")
    output, _ = await sales.run(inp)

    assert output.payload["intent"] == "address_pending_question"
    # temp_state untouched — still awaiting
    assert output.suggested_user_state_diff == {}


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
