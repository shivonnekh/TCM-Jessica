"""Tests for CRMRepo — uses a temp SQLite DB."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from src.crm.models import (
    AppointmentRecord,
    Constitution,
    ConversationMessage,
    UserStatus,
)
from src.crm.repo import CRMRepo


@pytest.fixture
async def repo(tmp_path: Path) -> CRMRepo:
    db_path = tmp_path / "test.db"
    r = await CRMRepo.connect(db_path)
    yield r
    await r.close()


@pytest.mark.asyncio
async def test_get_or_create_creates_new_user(repo: CRMRepo) -> None:
    user = await repo.get_or_create_user("+85291234567")
    assert user.phone == "+85291234567"
    assert user.status == UserStatus.NEW
    assert user.constitution == Constitution.UNKNOWN


@pytest.mark.asyncio
async def test_save_user_persists_updates(repo: CRMRepo) -> None:
    u = await repo.get_or_create_user("+85291234567")
    u2 = u.with_updates(
        name="Apple",
        age=32,
        district="沙田",
        constitution=Constitution.QIXU,
        status=UserStatus.QUALIFIED,
    )
    await repo.save_user(u2)

    reloaded = await repo.get_user("+85291234567")
    assert reloaded is not None
    assert reloaded.name == "Apple"
    assert reloaded.age == 32
    assert reloaded.district == "沙田"
    assert reloaded.constitution == Constitution.QIXU
    assert reloaded.status == UserStatus.QUALIFIED


@pytest.mark.asyncio
async def test_messages_round_trip(repo: CRMRepo) -> None:
    await repo.get_or_create_user("+85291234567")
    msg = ConversationMessage(
        role="user",
        content="hi",
        at=datetime(2026, 5, 21, 10, 0),
        turn_id="turn-1",
    )
    await repo.append_message("+85291234567", msg)

    user = await repo.get_user("+85291234567")
    assert user is not None
    assert len(user.conversation_history) == 1
    assert user.conversation_history[0].content == "hi"
    assert user.conversation_history[0].turn_id == "turn-1"


@pytest.mark.asyncio
async def test_appointments_round_trip(repo: CRMRepo) -> None:
    await repo.get_or_create_user("+85291234567")
    appt = AppointmentRecord(
        clinic_id="careplus_shatin",
        date="2026-06-01",
        time="10:00",
        mode="in_person",
        status="confirmed",
        booked_at=datetime(2026, 5, 21, 11, 0),
    )
    await repo.add_appointment("+85291234567", appt)

    user = await repo.get_user("+85291234567")
    assert user is not None
    assert len(user.appointments) == 1
    assert user.appointments[0].clinic_id == "careplus_shatin"
    assert user.appointments[0].mode == "in_person"


@pytest.mark.asyncio
async def test_messages_dedup_by_wa_id(repo: CRMRepo) -> None:
    await repo.get_or_create_user("+85291234567")
    msg = ConversationMessage(
        role="user",
        content="dup",
        at=datetime(2026, 5, 21, 10, 0),
        wa_message_id="wa-1",
    )
    await repo.append_message("+85291234567", msg)
    await repo.append_message("+85291234567", msg)  # same wa-id → ignored

    user = await repo.get_user("+85291234567")
    assert user is not None
    assert len(user.conversation_history) == 1


# ---------------------------------------------------------------------------
# list_phones_for_upcoming_appointments
# ---------------------------------------------------------------------------


def _future_appt(hours_ahead: float) -> AppointmentRecord:
    """Helper — creates a confirmed appointment N hours from now (HKT)."""
    import zoneinfo

    hkt = zoneinfo.ZoneInfo("Asia/Hong_Kong")
    dt = datetime.now(hkt) + timedelta(hours=hours_ahead)
    return AppointmentRecord(
        clinic_id="careplus_shatin",
        date=dt.strftime("%Y-%m-%d"),
        time=dt.strftime("%H:%M"),
        mode="in_person",
        status="confirmed",
        booked_at=datetime.now(hkt),
    )


def _past_appt() -> AppointmentRecord:
    """Confirmed appointment from yesterday — should NOT appear."""
    import zoneinfo

    hkt = zoneinfo.ZoneInfo("Asia/Hong_Kong")
    dt = datetime.now(hkt) - timedelta(hours=24)
    return AppointmentRecord(
        clinic_id="careplus_shatin",
        date=dt.strftime("%Y-%m-%d"),
        time=dt.strftime("%H:%M"),
        mode="in_person",
        status="confirmed",
        booked_at=datetime.now(hkt),
    )


@pytest.mark.asyncio
async def test_upcoming_appointments_returns_phone_in_window(repo: CRMRepo) -> None:
    """User with a confirmed appointment 24h from now is returned."""
    phone = "+85291000001"
    await repo.get_or_create_user(phone)
    await repo.add_appointment(phone, _future_appt(hours_ahead=24))

    phones = await repo.list_phones_for_upcoming_appointments(within_hours=48)
    assert phone in phones


@pytest.mark.asyncio
async def test_upcoming_appointments_excludes_past(repo: CRMRepo) -> None:
    """Past appointments are NOT returned."""
    phone = "+85291000002"
    await repo.get_or_create_user(phone)
    await repo.add_appointment(phone, _past_appt())

    phones = await repo.list_phones_for_upcoming_appointments(within_hours=48)
    assert phone not in phones


@pytest.mark.asyncio
async def test_upcoming_appointments_excludes_beyond_window(repo: CRMRepo) -> None:
    """Appointment 72h away is outside a 48h window."""
    phone = "+85291000003"
    await repo.get_or_create_user(phone)
    await repo.add_appointment(phone, _future_appt(hours_ahead=72))

    phones = await repo.list_phones_for_upcoming_appointments(within_hours=48)
    assert phone not in phones


@pytest.mark.asyncio
async def test_upcoming_appointments_excludes_non_confirmed(repo: CRMRepo) -> None:
    """Proposed and cancelled appointments are ignored."""
    import zoneinfo

    hkt = zoneinfo.ZoneInfo("Asia/Hong_Kong")
    dt = datetime.now(hkt) + timedelta(hours=12)
    phone_proposed = "+85291000004"
    phone_cancelled = "+85291000005"
    for phone in (phone_proposed, phone_cancelled):
        await repo.get_or_create_user(phone)

    status_map = {phone_proposed: "proposed", phone_cancelled: "cancelled"}
    for phone, status in status_map.items():
        appt = AppointmentRecord(
            clinic_id="careplus_shatin",
            date=dt.strftime("%Y-%m-%d"),
            time=dt.strftime("%H:%M"),
            mode="in_person",
            status=status,
            booked_at=datetime.now(hkt),
        )
        await repo.add_appointment(phone, appt)

    phones = await repo.list_phones_for_upcoming_appointments(within_hours=48)
    assert phone_proposed not in phones
    assert phone_cancelled not in phones


@pytest.mark.asyncio
async def test_upcoming_appointments_excludes_churned(repo: CRMRepo) -> None:
    """Churned and opted-out users are skipped even if they have upcoming appointments."""
    import zoneinfo

    from src.crm.models import UserStatus

    hkt = zoneinfo.ZoneInfo("Asia/Hong_Kong")
    phone_churned = "+85291000006"
    phone_opted = "+85291000007"

    for phone, status in (
        (phone_churned, UserStatus.CHURNED),
        (phone_opted, UserStatus.OPTED_OUT),
    ):
        u = await repo.get_or_create_user(phone)
        await repo.save_user(u.with_updates(status=status))
        await repo.add_appointment(phone, _future_appt(hours_ahead=12))

    phones = await repo.list_phones_for_upcoming_appointments(within_hours=48)
    assert phone_churned not in phones
    assert phone_opted not in phones


@pytest.mark.asyncio
async def test_upcoming_appointments_deduplicates_phone(repo: CRMRepo) -> None:
    """User with two confirmed appointments in window only appears once."""
    phone = "+85291000008"
    await repo.get_or_create_user(phone)
    await repo.add_appointment(phone, _future_appt(hours_ahead=10))
    await repo.add_appointment(phone, _future_appt(hours_ahead=20))

    phones = await repo.list_phones_for_upcoming_appointments(within_hours=48)
    assert phones.count(phone) == 1


@pytest.mark.asyncio
async def test_upcoming_appointments_empty_when_no_appts(repo: CRMRepo) -> None:
    """Returns empty list when no confirmed upcoming appointments exist."""
    await repo.get_or_create_user("+85291000009")

    phones = await repo.list_phones_for_upcoming_appointments(within_hours=48)
    assert phones == []


@pytest.mark.asyncio
async def test_upcoming_appointments_custom_window(repo: CRMRepo) -> None:
    """Custom within_hours parameter is respected."""
    phone_near = "+85291000010"
    phone_far = "+85291000011"
    await repo.get_or_create_user(phone_near)
    await repo.get_or_create_user(phone_far)
    await repo.add_appointment(phone_near, _future_appt(hours_ahead=6))
    await repo.add_appointment(phone_far, _future_appt(hours_ahead=24))

    # 12h window — only near appt qualifies
    phones_12h = await repo.list_phones_for_upcoming_appointments(within_hours=12)
    assert phone_near in phones_12h
    assert phone_far not in phones_12h

    # 48h window — both qualify
    phones_48h = await repo.list_phones_for_upcoming_appointments(within_hours=48)
    assert phone_near in phones_48h
    assert phone_far in phones_48h
