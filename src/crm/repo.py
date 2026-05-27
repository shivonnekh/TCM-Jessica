"""CRMRepo — SQLite persistence for users + messages + appointments.

Async via aiosqlite. All public methods are coroutines.

Threading: caller owns the connection lifecycle (open at app startup,
close at shutdown).
"""

from __future__ import annotations

import json
import zoneinfo
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

_HKT = zoneinfo.ZoneInfo("Asia/Hong_Kong")

import aiosqlite

from src.crm.models import (
    AppointmentRecord,
    Constitution,
    ConversationMessage,
    TongueRecord,
    User,
    UserStatus,
)

SCHEMA_PATH = Path(__file__).parent / "schema.sql"


class CRMRepo:
    """Repository pattern — hides SQL from the rest of the codebase."""

    def __init__(self, db: aiosqlite.Connection) -> None:
        self._db = db

    # ---------------------------------------------------------------
    # Lifecycle
    # ---------------------------------------------------------------

    @classmethod
    async def connect(cls, db_path: str | Path) -> "CRMRepo":
        db = await aiosqlite.connect(str(db_path))
        db.row_factory = aiosqlite.Row
        await db.executescript(SCHEMA_PATH.read_text())
        # Column migrations — SQLite doesn't support "ADD COLUMN IF NOT
        # EXISTS", so we add only when missing. Idempotent and safe to
        # re-run on every connect.
        await _migrate_add_user_columns(db)
        await db.commit()
        return cls(db)

    async def close(self) -> None:
        await self._db.close()

    # ---------------------------------------------------------------
    # Users
    # ---------------------------------------------------------------

    async def get_user(self, phone: str, *, history_window: int = 20) -> User | None:
        cur = await self._db.execute("SELECT * FROM users WHERE phone = ?", (phone,))
        row = await cur.fetchone()
        if row is None:
            return None

        history = await self._load_history(phone, limit=history_window)
        appointments = await self._load_appointments(phone)
        tongue_photos = await self._load_tongue_photos(phone)
        return _row_to_user(row, history, appointments, tongue_photos)

    async def get_or_create_user(self, phone: str) -> User:
        existing = await self.get_user(phone)
        if existing is not None:
            return existing
        new = User(phone=phone)
        await self.save_user(new)
        return new

    async def save_user(self, user: User) -> None:
        await self._db.execute(
            """
            INSERT INTO users (
                phone, name, status, age, location, district, constitution,
                pain_points, products_pitched, products_purchased,
                notes, tags, temp_state,
                last_period_start, cycle_length_days,
                observed_patterns,
                created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(phone) DO UPDATE SET
                name = excluded.name,
                status = excluded.status,
                age = excluded.age,
                location = excluded.location,
                district = excluded.district,
                constitution = excluded.constitution,
                pain_points = excluded.pain_points,
                products_pitched = excluded.products_pitched,
                products_purchased = excluded.products_purchased,
                notes = excluded.notes,
                tags = excluded.tags,
                temp_state = excluded.temp_state,
                last_period_start = excluded.last_period_start,
                cycle_length_days = excluded.cycle_length_days,
                observed_patterns = excluded.observed_patterns,
                updated_at = excluded.updated_at
            """,
            (
                user.phone,
                user.name,
                user.status.value,
                user.age,
                user.location,
                user.district,
                user.constitution.value,
                json.dumps(user.pain_points, ensure_ascii=False),
                json.dumps(user.products_pitched, ensure_ascii=False),
                json.dumps(user.products_purchased, ensure_ascii=False),
                user.notes,
                json.dumps(user.tags, ensure_ascii=False),
                json.dumps(user.temp_state, ensure_ascii=False),
                user.last_period_start.isoformat() if user.last_period_start else None,
                user.cycle_length_days,
                json.dumps(
                    [op.model_dump(mode="json") for op in user.observed_patterns],
                    ensure_ascii=False,
                ),
                user.created_at.isoformat(),
                user.updated_at.isoformat(),
            ),
        )
        await self._db.commit()

    # ---------------------------------------------------------------
    # Messages
    # ---------------------------------------------------------------

    async def append_message(self, phone: str, msg: ConversationMessage) -> None:
        await self._db.execute(
            """
            INSERT OR IGNORE INTO messages
                (phone, role, content, media_urls, wa_message_id, turn_id, at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                phone,
                msg.role,
                msg.content,
                json.dumps(msg.media_urls, ensure_ascii=False),
                msg.wa_message_id,
                msg.turn_id,
                msg.at.isoformat(),
            ),
        )
        await self._db.commit()

    async def _load_history(
        self, phone: str, *, limit: int
    ) -> list[ConversationMessage]:
        cur = await self._db.execute(
            """
            SELECT role, content, media_urls, wa_message_id, turn_id, at
            FROM messages
            WHERE phone = ?
            ORDER BY at DESC
            LIMIT ?
            """,
            (phone, limit),
        )
        rows = await cur.fetchall()
        # Reverse so oldest → newest
        return [
            ConversationMessage(
                role=r["role"],
                content=r["content"],
                media_urls=json.loads(r["media_urls"] or "[]"),
                wa_message_id=r["wa_message_id"],
                turn_id=r["turn_id"],
                at=datetime.fromisoformat(r["at"]),
            )
            for r in reversed(rows)
        ]

    # ---------------------------------------------------------------
    # Appointments
    # ---------------------------------------------------------------

    async def delete_all_for_phone(self, phone: str) -> dict[str, int]:
        """Wipe everything for one phone. Returns counts deleted."""
        async with self._db.execute(
            "SELECT COUNT(*) FROM messages WHERE phone = ?", (phone,)
        ) as cur:
            row = await cur.fetchone()
            msg_count = row[0] if row else 0
        async with self._db.execute(
            "SELECT COUNT(*) FROM appointments WHERE phone = ?", (phone,)
        ) as cur:
            row = await cur.fetchone()
            appt_count = row[0] if row else 0
        async with self._db.execute(
            "SELECT COUNT(*) FROM users WHERE phone = ?", (phone,)
        ) as cur:
            row = await cur.fetchone()
            user_count = row[0] if row else 0

        # FK ON DELETE CASCADE handles messages + appointments automatically.
        await self._db.execute("DELETE FROM users WHERE phone = ?", (phone,))
        # But ensure no orphans if FKs are off.
        await self._db.execute("DELETE FROM messages WHERE phone = ?", (phone,))
        await self._db.execute("DELETE FROM appointments WHERE phone = ?", (phone,))
        await self._db.execute("DELETE FROM tongue_photos WHERE phone = ?", (phone,))
        await self._db.commit()
        return {"users": user_count, "messages": msg_count, "appointments": appt_count}

    async def add_tongue_record(self, phone: str, record: TongueRecord) -> None:
        await self._db.execute(
            """
            INSERT INTO tongue_photos
                (phone, photo_url, captured_at, tongue_colour, coating_colour,
                 coating_thickness, coating_moisture, body_shape,
                 teeth_marks, cracks, raw_analysis, constitution_at_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                phone,
                record.photo_url,
                record.captured_at.isoformat(),
                record.tongue_colour,
                record.coating_colour,
                record.coating_thickness,
                record.coating_moisture,
                record.body_shape,
                int(record.teeth_marks),
                int(record.cracks),
                record.raw_analysis,
                record.constitution_at_time,
            ),
        )
        await self._db.commit()

    async def _load_tongue_photos(self, phone: str) -> list[TongueRecord]:
        cur = await self._db.execute(
            """
            SELECT photo_url, captured_at, tongue_colour, coating_colour,
                   coating_thickness, coating_moisture, body_shape,
                   teeth_marks, cracks, raw_analysis, constitution_at_time
            FROM tongue_photos
            WHERE phone = ?
            ORDER BY captured_at ASC
            """,
            (phone,),
        )
        rows = await cur.fetchall()
        return [
            TongueRecord(
                photo_url=r["photo_url"],
                captured_at=datetime.fromisoformat(r["captured_at"]),
                tongue_colour=r["tongue_colour"] or "",
                coating_colour=r["coating_colour"] or "",
                coating_thickness=r["coating_thickness"] or "",
                coating_moisture=r["coating_moisture"] or "",
                body_shape=r["body_shape"] or "",
                teeth_marks=bool(r["teeth_marks"]),
                cracks=bool(r["cracks"]),
                raw_analysis=r["raw_analysis"] or "",
                constitution_at_time=r["constitution_at_time"] or "unknown",
            )
            for r in rows
        ]

    async def add_appointment(self, phone: str, appt: AppointmentRecord) -> None:
        await self._db.execute(
            """
            INSERT INTO appointments
                (phone, clinic_id, date, time, mode, status, booked_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                phone,
                appt.clinic_id,
                appt.date,
                appt.time,
                appt.mode,
                appt.status,
                appt.booked_at.isoformat(),
            ),
        )
        await self._db.commit()

    # ---------------------------------------------------------------
    # Broadcast tracking (proactive weather care — per-user weekly cap)
    # ---------------------------------------------------------------

    async def list_active_phones(self, limit: int = 5000) -> list[str]:
        """Phones eligible to receive proactive broadcasts (not churned/opted-out)."""
        cur = await self._db.execute(
            """
            SELECT phone FROM users
            WHERE status NOT IN ('churned', 'opted_out')
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = await cur.fetchall()
        return [row["phone"] for row in rows]

    async def get_broadcast_count_this_week(self, phone: str, iso_week: str) -> int:
        """How many broadcasts this user has received in the given ISO week."""
        cur = await self._db.execute(
            "SELECT COUNT(*) AS cnt FROM user_broadcasts WHERE phone = ? AND iso_week = ?",
            (phone, iso_week),
        )
        row = await cur.fetchone()
        return int(row["cnt"]) if row else 0

    async def get_last_broadcast_at(self, phone: str) -> str | None:
        """ISO timestamp of the most recent broadcast sent to this user, or None."""
        cur = await self._db.execute(
            "SELECT MAX(sent_at) AS last FROM user_broadcasts WHERE phone = ?",
            (phone,),
        )
        row = await cur.fetchone()
        return row["last"] if row and row["last"] else None

    async def record_broadcast(
        self, phone: str, condition_code: str, iso_week: str, sent_at: str
    ) -> None:
        """Persist a sent broadcast for cap tracking."""
        await self._db.execute(
            """
            INSERT INTO user_broadcasts (phone, sent_at, condition_code, iso_week)
            VALUES (?, ?, ?, ?)
            """,
            (phone, sent_at, condition_code, iso_week),
        )
        await self._db.commit()

    async def list_phones_for_constitution_recheck(
        self,
        recheck_cutoff: str,
        activity_cutoff: str,
        limit: int = 5000,
    ) -> list[str]:
        """Phones with a known constitution that haven't been rechecked recently.

        Args:
            recheck_cutoff: ISO timestamp — no constitution_recheck broadcast after this
            activity_cutoff: ISO timestamp — no messages after this = "gone quiet"
            limit: max results
        """
        cur = await self._db.execute(
            """
            SELECT u.phone
            FROM users u
            WHERE u.status NOT IN ('churned', 'opted_out')
              AND u.constitution != 'unknown'
              AND u.phone NOT IN (
                  SELECT phone FROM user_broadcasts
                  WHERE condition_code = 'constitution_recheck'
                    AND sent_at > ?
              )
              AND NOT EXISTS (
                  SELECT 1 FROM messages m
                  WHERE m.phone = u.phone
                    AND m.at > ?
              )
            ORDER BY u.updated_at ASC
            LIMIT ?
            """,
            (recheck_cutoff, activity_cutoff, limit),
        )
        rows = await cur.fetchall()
        return [row["phone"] for row in rows]

    async def list_phones_for_tongue_nudge(
        self,
        tongue_cutoff: str,
        nudge_cutoff: str,
        limit: int = 5000,
    ) -> list[str]:
        """Phones eligible for a monthly 舌診進度 nudge.

        Criteria:
            - Active user (not churned/opted_out)
            - Constitution known (not UNKNOWN)
            - Has at least one prior tongue_photo
            - Most recent tongue_photo is older than ``tongue_cutoff``
            - No tongue_nudge broadcast since ``nudge_cutoff``

        Args:
            tongue_cutoff: ISO timestamp — any tongue photo newer than
                this means user already uploaded recently, skip them.
            nudge_cutoff: ISO timestamp — no tongue_nudge broadcast
                after this (one nudge per 30 days).
        """
        cur = await self._db.execute(
            """
            SELECT u.phone
            FROM users u
            WHERE u.status NOT IN ('churned', 'opted_out')
              AND u.constitution != 'unknown'
              AND EXISTS (
                  SELECT 1 FROM tongue_photos t
                  WHERE t.phone = u.phone
              )
              AND NOT EXISTS (
                  SELECT 1 FROM tongue_photos t
                  WHERE t.phone = u.phone
                    AND t.captured_at > ?
              )
              AND u.phone NOT IN (
                  SELECT phone FROM user_broadcasts
                  WHERE condition_code = 'tongue_nudge'
                    AND sent_at > ?
              )
            ORDER BY u.updated_at ASC
            LIMIT ?
            """,
            (tongue_cutoff, nudge_cutoff, limit),
        )
        rows = await cur.fetchall()
        return [row["phone"] for row in rows]

    async def list_phones_for_purchase_followup(
        self,
        activity_cutoff: str,
        followup_cutoff: str,
        limit: int = 5000,
    ) -> list[str]:
        """Phones that bought something, went quiet, and haven't had a follow-up recently.

        Args:
            activity_cutoff: ISO timestamp — no messages after this = "gone quiet"
            followup_cutoff: ISO timestamp — no purchase_followup broadcast after this
            limit: max results
        """
        cur = await self._db.execute(
            """
            SELECT u.phone
            FROM users u
            WHERE u.status NOT IN ('churned', 'opted_out')
              AND json_array_length(u.products_purchased) > 0
              AND u.phone NOT IN (
                  SELECT phone FROM user_broadcasts
                  WHERE condition_code = 'purchase_followup'
                    AND sent_at > ?
              )
              AND NOT EXISTS (
                  SELECT 1 FROM messages m
                  WHERE m.phone = u.phone
                    AND m.at > ?
              )
            ORDER BY u.updated_at ASC
            LIMIT ?
            """,
            (followup_cutoff, activity_cutoff, limit),
        )
        rows = await cur.fetchall()
        return [row["phone"] for row in rows]

    async def list_phones_for_upcoming_appointments(
        self,
        within_hours: int = 48,
        limit: int = 5000,
    ) -> list[str]:
        """Phones with a *confirmed* appointment in the next ``within_hours`` hours.

        Uses local HKT time for comparison because appointment date/time is
        stored in clinic-local (HKT) format without timezone offset.

        Args:
            within_hours: look-ahead window in hours (default 48).
            limit: safety cap on results.
        """
        now = datetime.now(_HKT)
        cutoff = now + timedelta(hours=within_hours)
        # Stored format: date='YYYY-MM-DD', time='HH:MM' → concat gives 'YYYY-MM-DD HH:MM'
        now_str = now.strftime("%Y-%m-%d %H:%M")
        cutoff_str = cutoff.strftime("%Y-%m-%d %H:%M")

        cur = await self._db.execute(
            """
            SELECT DISTINCT a.phone
            FROM appointments a
            JOIN users u ON a.phone = u.phone
            WHERE u.status NOT IN ('churned', 'opted_out')
              AND a.status = 'confirmed'
              AND (a.date || ' ' || a.time) >= ?
              AND (a.date || ' ' || a.time) <  ?
            ORDER BY (a.date || ' ' || a.time) ASC
            LIMIT ?
            """,
            (now_str, cutoff_str, limit),
        )
        rows = await cur.fetchall()
        return [row["phone"] for row in rows]

    async def get_message_count(self, phone: str) -> int:
        """Total number of stored messages for this user (all time)."""
        cur = await self._db.execute(
            "SELECT COUNT(*) AS cnt FROM messages WHERE phone = ?", (phone,)
        )
        row = await cur.fetchone()
        return int(row["cnt"]) if row else 0

    async def get_messages_since(
        self,
        phone: str,
        *,
        since: datetime | None = None,
        limit: int = 60,
    ) -> list[ConversationMessage]:
        """Load messages newer than ``since`` (all time if None), oldest-first."""
        if since is not None:
            cur = await self._db.execute(
                """
                SELECT role, content, media_urls, wa_message_id, turn_id, at
                FROM messages
                WHERE phone = ? AND at > ?
                ORDER BY at ASC
                LIMIT ?
                """,
                (phone, since.isoformat(), limit),
            )
        else:
            cur = await self._db.execute(
                """
                SELECT role, content, media_urls, wa_message_id, turn_id, at
                FROM messages
                WHERE phone = ?
                ORDER BY at ASC
                LIMIT ?
                """,
                (phone, limit),
            )
        rows = await cur.fetchall()
        return [
            ConversationMessage(
                role=r["role"],
                content=r["content"],
                media_urls=json.loads(r["media_urls"] or "[]"),
                wa_message_id=r["wa_message_id"],
                turn_id=r["turn_id"],
                at=datetime.fromisoformat(r["at"]),
            )
            for r in rows
        ]

    async def _load_appointments(self, phone: str) -> list[AppointmentRecord]:
        cur = await self._db.execute(
            """
            SELECT clinic_id, date, time, mode, status, booked_at
            FROM appointments
            WHERE phone = ?
            ORDER BY date DESC, time DESC
            """,
            (phone,),
        )
        rows = await cur.fetchall()
        return [
            AppointmentRecord(
                clinic_id=r["clinic_id"],
                date=r["date"],
                time=r["time"],
                mode=r["mode"],
                status=r["status"],
                booked_at=datetime.fromisoformat(r["booked_at"]),
            )
            for r in rows
        ]


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------


def _row_to_user(
    row: aiosqlite.Row,
    history: list[ConversationMessage],
    appointments: list[AppointmentRecord],
    tongue_photos: list[TongueRecord] | None = None,
) -> User:
    # Forward-compatible read: temp_state column may be missing in older
    # databases that haven't run the schema migration. Default to {}.
    try:
        temp_state = json.loads(row["temp_state"] or "{}")
    except (IndexError, KeyError):
        temp_state = {}

    # last_period_start may be absent in older DBs that haven't re-run schema.
    raw_period = None
    try:
        raw_period = row["last_period_start"]
    except (IndexError, KeyError):
        pass

    # observed_patterns also may be absent in legacy DBs
    raw_patterns: list[dict] = []
    try:
        raw = row["observed_patterns"]
        if raw:
            raw_patterns = json.loads(raw)
    except (IndexError, KeyError, TypeError):
        pass

    from datetime import date as _date

    from src.crm.models import ObservedPattern  # noqa: PLC0415

    parsed_patterns = [ObservedPattern.model_validate(p) for p in raw_patterns]

    return User(
        phone=row["phone"],
        name=row["name"],
        status=UserStatus(row["status"]),
        age=row["age"],
        location=row["location"],
        district=row["district"],
        constitution=Constitution(row["constitution"]),
        pain_points=json.loads(row["pain_points"] or "[]"),
        products_pitched=json.loads(row["products_pitched"] or "[]"),
        products_purchased=json.loads(row["products_purchased"] or "[]"),
        notes=row["notes"] or "",
        tags=json.loads(row["tags"] or "[]"),
        temp_state=temp_state,
        last_period_start=_date.fromisoformat(raw_period) if raw_period else None,
        cycle_length_days=_try_int(row, "cycle_length_days", 28),
        observed_patterns=parsed_patterns,
        conversation_history=history,
        appointments=appointments,
        tongue_photos=tongue_photos or [],
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
    )


def _user_snapshot_to_dict(user: User) -> dict[str, Any]:
    """For trace bundles — JSON-serializable snapshot."""
    return user.model_dump(mode="json")


def _try_int(row: Any, key: str, default: int) -> int:
    """Read an integer column that may be absent in older schema versions."""
    try:
        val = row[key]
        return int(val) if val is not None else default
    except (IndexError, KeyError, TypeError, ValueError):
        return default


# -------------------------------------------------------------------
# Column migrations — SQLite has no "ADD COLUMN IF NOT EXISTS", so we
# inspect PRAGMA table_info and ADD only when missing. Idempotent.
# -------------------------------------------------------------------


_USER_COLUMN_MIGRATIONS: tuple[tuple[str, str], ...] = (
    # (column_name, ddl_fragment for ADD COLUMN)
    ("last_period_start", "last_period_start TEXT"),
    ("cycle_length_days", "cycle_length_days INTEGER NOT NULL DEFAULT 28"),
    ("observed_patterns", "observed_patterns TEXT NOT NULL DEFAULT '[]'"),
)


async def _migrate_add_user_columns(db: aiosqlite.Connection) -> None:
    """Add new users-table columns if missing. Safe to run on every connect."""
    cur = await db.execute("PRAGMA table_info(users)")
    rows = await cur.fetchall()
    existing = {r[1] for r in rows}  # column names
    for col, ddl in _USER_COLUMN_MIGRATIONS:
        if col not in existing:
            await db.execute(f"ALTER TABLE users ADD COLUMN {ddl}")
