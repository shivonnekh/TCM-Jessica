"""Tests for the TongueProgress specialist + its planner routing + CRM persistence."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.agents.base import SpecialistInput, SpecialistName
from src.agents.planner import _rule_overrides
from src.agents.tongue_progress_agent import (
    TongueProgressAgent,
    _classify_direction,
    _diff_findings,
    _extract_json,
)
from src.crm.models import Constitution, TongueRecord, User, UserStatus
from src.crm.repo import CRMRepo


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def _record(**overrides) -> TongueRecord:
    defaults = {
        "photo_url": "https://example.com/t.jpg",
        "captured_at": datetime(2026, 5, 1, 10, 0),
        "tongue_colour": "淡紅",
        "coating_colour": "白",
        "coating_thickness": "厚",
        "coating_moisture": "膩",
        "body_shape": "正常",
        "teeth_marks": False,
        "cracks": False,
        "raw_analysis": "脷淡紅，苔白厚膩",
        "constitution_at_time": "陽虛質",
    }
    defaults.update(overrides)
    return TongueRecord(**defaults)


def test_diff_findings_detects_coating_change() -> None:
    prior = _record(coating_thickness="厚", coating_moisture="膩")
    current = _record(coating_thickness="薄", coating_moisture="潤")
    changes = _diff_findings(prior, current)

    aspects = {c["aspect"] for c in changes}
    assert "coating_thickness" in aspects
    assert "coating_moisture" in aspects


def test_diff_findings_returns_empty_for_identical_records() -> None:
    prior = _record()
    current = _record(photo_url="different.jpg")  # only URL differs
    assert _diff_findings(prior, current) == []


def test_diff_findings_detects_boolean_flag_change() -> None:
    prior = _record(teeth_marks=False, cracks=False)
    current = _record(teeth_marks=True, cracks=True)
    changes = _diff_findings(prior, current)

    aspects = {c["aspect"] for c in changes}
    assert "teeth_marks" in aspects
    assert "cracks" in aspects


def test_classify_direction_improving_from_narrative() -> None:
    changes = [{"aspect": "coating_thickness", "before": "厚", "after": "薄"}]
    narrative = "你嘅舌苔薄咗好多，濕熱明顯改善緊"
    assert _classify_direction(changes, narrative) == "improving"


def test_classify_direction_worsening_from_narrative() -> None:
    changes = [{"aspect": "coating_thickness", "before": "薄", "after": "厚"}]
    narrative = "舌苔加重咗，濕熱差咗"
    assert _classify_direction(changes, narrative) == "worsening"


def test_classify_direction_stable_when_no_changes() -> None:
    assert _classify_direction([], "冇變化") == "stable"


def test_extract_json_handles_leading_prose() -> None:
    text = '分析完成: {"tongue_colour": "紅", "coating_thickness": "薄"}'
    parsed = _extract_json(text)
    assert parsed["tongue_colour"] == "紅"


def test_extract_json_raises_on_no_json() -> None:
    with pytest.raises(ValueError):
        _extract_json("沒有 JSON 喺度")


# ---------------------------------------------------------------------------
# Planner routing
# ---------------------------------------------------------------------------


def test_tongue_photo_with_prior_history_routes_to_progress() -> None:
    """User has known constitution + ≥1 prior tongue photo → TONGUE_PROGRESS."""
    user = User(
        phone="+85291234567",
        status=UserStatus.CONSTITUTION_DONE,
        constitution=Constitution.YANGXU,
        tongue_photos=[_record(captured_at=datetime(2026, 4, 1, 10, 0))],
    )
    decision = _rule_overrides(user, "睇下我有冇好啲", ["https://m.jpg"])

    assert decision is not None
    assert decision.specialists == [SpecialistName.TONGUE_PROGRESS]
    assert "progress" in decision.reasoning.lower()


def test_first_tongue_photo_still_routes_to_constitution() -> None:
    """No prior tongue history → CONSTITUTION (existing flow)."""
    user = User(
        phone="+85291234567",
        status=UserStatus.NEW,
        tongue_photos=[],
    )
    decision = _rule_overrides(user, "影咗", ["https://m.jpg"])

    assert decision is not None
    assert decision.specialists == [SpecialistName.CONSTITUTION]


def test_unknown_constitution_routes_to_constitution_not_progress() -> None:
    """Even with prior photos, if constitution is UNKNOWN we re-diagnose."""
    user = User(
        phone="+85291234567",
        status=UserStatus.QUALIFIED,
        constitution=Constitution.UNKNOWN,
        tongue_photos=[_record()],
    )
    decision = _rule_overrides(user, "再睇下", ["https://m.jpg"])

    assert decision is not None
    assert decision.specialists == [SpecialistName.CONSTITUTION]


# ---------------------------------------------------------------------------
# TongueProgressAgent.run
# ---------------------------------------------------------------------------


def _mock_llm(vision_json: str, narrative_text: str = "你嘅舌苔薄咗好多") -> MagicMock:
    """Build an LLM mock that returns vision JSON on first call,
    narrative on second."""
    vision_resp = MagicMock()
    vision_resp.content = [MagicMock(text=vision_json)]
    vision_resp.usage = MagicMock(input_tokens=100, output_tokens=50)

    narrative_resp = MagicMock()
    narrative_resp.content = [MagicMock(text=narrative_text)]
    narrative_resp.usage = MagicMock(input_tokens=80, output_tokens=40)

    llm = MagicMock()
    llm.messages = MagicMock()
    llm.messages.create = AsyncMock(side_effect=[vision_resp, narrative_resp])
    return llm


@pytest.mark.asyncio
async def test_agent_returns_no_media_error_when_no_url() -> None:
    agent = TongueProgressAgent(MagicMock())
    user = User(phone="+85291234567")
    output, _usage = await agent.run(
        SpecialistInput(user=user, user_message="無圖", media_urls=[])
    )
    assert output.error == "no_media_urls"


@pytest.mark.asyncio
async def test_agent_first_photo_no_prior_history() -> None:
    """No prior records → phase=first_photo, no narrative, no comparison."""
    vision_json = (
        '{"tongue_colour":"淡紅","coating_colour":"白","coating_thickness":"厚",'
        '"coating_moisture":"膩","body_shape":"正常","teeth_marks":false,'
        '"cracks":false,"raw_analysis":"舌苔厚膩"}'
    )
    llm = _mock_llm(vision_json)
    agent = TongueProgressAgent(llm)

    user = User(phone="+85291234567", constitution=Constitution.YANGXU)
    output, _usage = await agent.run(
        SpecialistInput(user=user, user_message="影咗", media_urls=["https://x.jpg"])
    )

    assert output.error is None
    assert output.payload["phase"] == "first_photo"
    assert output.payload["previous_record"] is None
    assert output.payload["changes"] == []
    # Vision called exactly once (no narrative call)
    assert llm.messages.create.await_count == 1


@pytest.mark.asyncio
async def test_agent_compares_to_prior_record() -> None:
    """With prior record, narrative is generated + changes detected."""
    vision_json = (
        '{"tongue_colour":"淡紅","coating_colour":"白","coating_thickness":"薄",'
        '"coating_moisture":"潤","body_shape":"正常","teeth_marks":false,'
        '"cracks":false,"raw_analysis":"舌苔薄潤"}'
    )
    llm = _mock_llm(vision_json, narrative_text="你嘅舌苔薄咗好多，濕熱改善緊")
    agent = TongueProgressAgent(llm)

    prior = _record(
        coating_thickness="厚",
        coating_moisture="膩",
        captured_at=datetime(2026, 4, 1, 10, 0),
    )
    user = User(
        phone="+85291234567",
        constitution=Constitution.YANGXU,
        tongue_photos=[prior],
    )

    output, _usage = await agent.run(
        SpecialistInput(
            user=user,
            user_message="一個月後再影",
            media_urls=["https://new.jpg"],
        )
    )

    assert output.payload["phase"] == "compared"
    assert output.payload["previous_record"] is not None
    assert len(output.payload["changes"]) >= 1
    assert "薄咗" in output.payload["narrative_zh"]
    assert output.payload["overall_direction"] == "improving"
    # Vision + narrative = 2 LLM calls
    assert llm.messages.create.await_count == 2


@pytest.mark.asyncio
async def test_agent_emits_tongue_photo_append_diff() -> None:
    """suggested_user_state_diff has tongue_photos_append with the new record."""
    vision_json = (
        '{"tongue_colour":"紅","coating_colour":"黃","coating_thickness":"厚",'
        '"coating_moisture":"膩","body_shape":"正常","teeth_marks":false,'
        '"cracks":false,"raw_analysis":"舌紅苔黃厚"}'
    )
    llm = _mock_llm(vision_json)
    agent = TongueProgressAgent(llm)

    user = User(phone="+85291234567", constitution=Constitution.SHIRE)
    output, _usage = await agent.run(
        SpecialistInput(
            user=user, user_message="影", media_urls=["https://shire.jpg"]
        )
    )

    diff = output.suggested_user_state_diff
    assert "tongue_photos_append" in diff
    appended = diff["tongue_photos_append"]
    assert len(appended) == 1
    assert appended[0]["tongue_colour"] == "紅"
    assert appended[0]["constitution_at_time"] == "濕熱質"


@pytest.mark.asyncio
async def test_agent_handles_vision_llm_failure() -> None:
    """Vision call exception → still returns output with safe fallback."""
    llm = MagicMock()
    llm.messages = MagicMock()
    llm.messages.create = AsyncMock(side_effect=RuntimeError("vision API down"))
    agent = TongueProgressAgent(llm)

    user = User(phone="+85291234567", constitution=Constitution.QIXU)
    output, _usage = await agent.run(
        SpecialistInput(
            user=user, user_message="影", media_urls=["https://fail.jpg"]
        )
    )

    # No crash; output is valid; raw_analysis has fallback text
    assert output.error is None
    assert "未能完成" in output.payload["current_analysis"]["raw_analysis"]


# ---------------------------------------------------------------------------
# CRM round-trip (SQLite)
# ---------------------------------------------------------------------------


@pytest.fixture
async def repo(tmp_path: Path) -> CRMRepo:
    r = await CRMRepo.connect(tmp_path / "test.db")
    yield r
    await r.close()


@pytest.mark.asyncio
async def test_crm_persists_tongue_record(repo: CRMRepo) -> None:
    phone = "+85291234567"
    await repo.get_or_create_user(phone)

    record = _record(captured_at=datetime(2026, 5, 1, 10, 0))
    await repo.add_tongue_record(phone, record)

    user = await repo.get_user(phone)
    assert user is not None
    assert len(user.tongue_photos) == 1
    assert user.tongue_photos[0].tongue_colour == "淡紅"
    assert user.tongue_photos[0].coating_thickness == "厚"


@pytest.mark.asyncio
async def test_crm_multiple_tongue_records_ordered_oldest_first(
    repo: CRMRepo,
) -> None:
    phone = "+85291234567"
    await repo.get_or_create_user(phone)

    older = _record(
        photo_url="https://older.jpg",
        captured_at=datetime(2026, 4, 1, 10, 0),
        coating_thickness="厚",
    )
    newer = _record(
        photo_url="https://newer.jpg",
        captured_at=datetime(2026, 5, 1, 10, 0),
        coating_thickness="薄",
    )
    await repo.add_tongue_record(phone, older)
    await repo.add_tongue_record(phone, newer)

    user = await repo.get_user(phone)
    assert user is not None
    assert len(user.tongue_photos) == 2
    # Oldest first → user.tongue_photos[-1] is the latest (pattern used by agent)
    assert user.tongue_photos[0].photo_url == "https://older.jpg"
    assert user.tongue_photos[-1].photo_url == "https://newer.jpg"


@pytest.mark.asyncio
async def test_crm_delete_cascades_tongue_photos(repo: CRMRepo) -> None:
    phone = "+85291234567"
    await repo.get_or_create_user(phone)
    await repo.add_tongue_record(phone, _record())

    await repo.delete_all_for_phone(phone)
    user = await repo.get_user(phone)
    assert user is None
