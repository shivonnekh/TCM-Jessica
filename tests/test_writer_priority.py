"""Tests for the Writer's conflict-resolution priority ordering.

Doesn't run the LLM — exercises the pure helper `_priority_rank` +
verifies SPECIALIST_PRIORITY is internally consistent.
"""

from __future__ import annotations

from src.agents.base import SpecialistName
from src.agents.writer import SPECIALIST_PRIORITY, _priority_rank


def test_priority_order_covers_all_specialists() -> None:
    """No specialist should fall into the unknown/lowest bucket."""
    for name in SpecialistName:
        rank = _priority_rank(name)
        assert rank < len(SPECIALIST_PRIORITY), f"{name.value} not in priority list"


def test_priority_order_constitution_highest() -> None:
    assert _priority_rank(SpecialistName.CONSTITUTION) == 0


def test_priority_order_greeting_lowest() -> None:
    assert _priority_rank(SpecialistName.GREETING) == len(SPECIALIST_PRIORITY) - 1


def test_priority_order_sales_above_faq() -> None:
    """Sales (revenue) beats FAQ (info) on conflicts."""
    assert _priority_rank(SpecialistName.SALES) < _priority_rank(SpecialistName.FAQ)


def test_priority_order_appointment_above_sales() -> None:
    """Concrete action (booking) beats sales pitch."""
    assert _priority_rank(SpecialistName.APPOINTMENT) < _priority_rank(SpecialistName.SALES)
