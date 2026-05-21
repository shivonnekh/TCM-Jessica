"""Tests for the SpecialistCatalog + Planner DRY menu."""

from __future__ import annotations

from src.agents.base import (
    SPECIALIST_CATALOG,
    SpecialistName,
    render_specialist_menu_zh,
)


def test_catalog_contains_every_specialist() -> None:
    """If you add a SpecialistName enum value, you MUST add a catalog entry."""
    for name in SpecialistName:
        assert name in SPECIALIST_CATALOG, f"missing catalog entry for {name.value}"


def test_each_meta_has_required_fields() -> None:
    for meta in SPECIALIST_CATALOG.values():
        assert meta.one_liner_zh.strip()
        assert len(meta.triggers_zh) >= 1
        assert meta.output_summary.strip()


def test_render_menu_lists_all() -> None:
    rendered = render_specialist_menu_zh()
    for name in SpecialistName:
        assert name.value in rendered
