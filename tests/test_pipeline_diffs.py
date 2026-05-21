"""Tests for orchestrator's _apply_specialist_diffs merge helper."""

from __future__ import annotations

from src.agents.base import SpecialistName, SpecialistOutput
from src.crm.models import Constitution, User, UserStatus
from src.orchestrator.pipeline import _apply_specialist_diffs


def _out(specialist: SpecialistName, diff: dict) -> SpecialistOutput:
    return SpecialistOutput(
        specialist=specialist,
        payload={},
        suggested_user_state_diff=diff,
    )


def test_replace_known_field() -> None:
    user = User(phone="+85291234567", status=UserStatus.NEW)
    outputs = [_out(SpecialistName.GREETING, {"status": "qualified"})]
    result = _apply_specialist_diffs(user, outputs)
    assert result.status == UserStatus.QUALIFIED


def test_unknown_field_dropped() -> None:
    user = User(phone="+85291234567")
    outputs = [_out(SpecialistName.SALES, {"fake_field": 123})]
    # Should not raise — just drop
    result = _apply_specialist_diffs(user, outputs)
    assert result.model_dump() == user.model_dump()


def test_append_extends_list_with_dedup() -> None:
    user = User(
        phone="+85291234567",
        products_pitched=["soup_a", "soup_b"],
    )
    outputs = [
        _out(
            SpecialistName.SALES,
            {"products_pitched_append": ["soup_c", "soup_a"]},  # dup
        )
    ]
    result = _apply_specialist_diffs(user, outputs)
    assert result.products_pitched == ["soup_a", "soup_b", "soup_c"]


def test_append_on_empty_list() -> None:
    user = User(phone="+85291234567")
    outputs = [
        _out(SpecialistName.SALES, {"products_pitched_append": ["soup_a"]})
    ]
    result = _apply_specialist_diffs(user, outputs)
    assert result.products_pitched == ["soup_a"]


def test_append_unknown_field_dropped() -> None:
    user = User(phone="+85291234567")
    outputs = [
        _out(SpecialistName.SALES, {"phantom_list_append": ["x"]})
    ]
    result = _apply_specialist_diffs(user, outputs)
    # No change, no crash
    assert result.products_pitched == []


def test_append_on_non_list_field_dropped() -> None:
    user = User(phone="+85291234567")
    outputs = [
        _out(SpecialistName.GREETING, {"name_append": "Foo"})  # name is str
    ]
    result = _apply_specialist_diffs(user, outputs)
    assert result.name is None


def test_multiple_specialists_merge_disjoint_keys() -> None:
    user = User(phone="+85291234567")
    outputs = [
        _out(SpecialistName.CONSTITUTION, {"constitution": Constitution.QIXU.value}),
        _out(SpecialistName.SALES, {"products_pitched_append": ["soup_a"]}),
    ]
    result = _apply_specialist_diffs(user, outputs)
    assert result.constitution == Constitution.QIXU
    assert result.products_pitched == ["soup_a"]


def test_replace_then_append_in_one_pass() -> None:
    """When both a replace and an _append on the same base field exist,
    the _append uses the just-replaced value as the base."""
    user = User(phone="+85291234567", products_pitched=["soup_old"])
    outputs = [
        _out(SpecialistName.SALES, {
            "products_pitched": ["soup_reset"],
            "products_pitched_append": ["soup_new"],
        })
    ]
    result = _apply_specialist_diffs(user, outputs)
    # Both ops applied; final has both, dedup preserved
    assert set(result.products_pitched) == {"soup_reset", "soup_new"}
