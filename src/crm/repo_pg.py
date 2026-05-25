"""CRMRepoPG — Postgres-backed CRM repository.

Mirrors the public API of ``CRMRepo`` (the SQLite implementation) so the
caller doesn't care which driver is in use. Switch happens in
``CRMRepo.connect()`` based on the connection URL.
"""

from __future__ import annotations

import json
import logging
import zoneinfo
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

_HKT = zoneinfo.ZoneInfo("Asia/Hong_Kong")

import asyncpg

from src.crm.models import (
    AppointmentRecord,
    Constitution,
    ConversationMessage,
    User,
    UserStatus,
)

logger = logging.getLogger("crm.repo_pg")

SCHEMA_PATH = Path(__file__).parent / "schema_pg.sql"


class CRMRepoPG:
    """Postgres CRM repo (asyncpg)."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    # ---------------------------------------------------------------
    # Lifecycle
    # ---------------------------------------------------------------

    @classmethod
    async def connect(cls, dsn: str) -> "CRMRepoPG":
        # Normalize postgresql:// to a DSN asyncpg accepts.
        if dsn.startswith("postgres://"):
            dsn = "postgresql://" + dsn[len("postgres://") :]
        pool = await asyncpg.create_pool(
            dsn, min_size=1, max_size=5, command_timeout=30
        )
        # Apply schema (idempotent)
        async with pool.acquire() as conn:
            schema_sql = SCHEMA_PATH.read_text()
            for stmt in _split_sql(schema_sql):
                if stmt.strip():
                    await conn.execute(stmt)
        logger.info("CRMRepoPG connected, schema applied")
        return cls(pool)

    async def close(self) -> None:
        await self._pool.close()

    # ---------------------------------------------------------------
    # Users
    # ---------------------------------------------------------------

    async def get_user(self, phone: str, *, history_window: int = 20) -> User | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM users WHERE phone = $1", phone)
            if row is None:
                return None
            history = await _load_history(conn, phone, history_window)
            appointments = await _load_appointments(conn, phone)
        return _row_to_user(row, history, appointments)

    async def get_or_create_user(self, phone: str) -> User:
        existing = await self.get_user(phone)
        if existing is not None:
            return existing
        new = User(phone=phone)
        await self.save_user(new)
        return new

    async def save_user(self, user: User) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO users (
                    phone, name, status, age, location, district, constitution,
                    pain_points, products_pitched, products_purchased,
                    notes, tags, temp_state, created_at, updated_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
                ON CONFLICT (phone) DO UPDATE SET
                    name = EXCLUDED.name,
                    status = EXCLUDED.status,
                    age = EXCLUDED.age,
                    location = EXCLUDED.location,
                    district = EXCLUDED.district,
                    constitution = EXCLUDED.constitution,
                    pain_points = EXCLUDED.pain_points,
                    products_pitched = EXCLUDED.products_pitched,
                    products_purchased = EXCLUDED.products_purchased,
                    notes = EXCLUDED.notes,
                    tags = EXCLUDED.tags,
                    temp_state = EXCLUDED.temp_state,
                    updated_at = EXCLUDED.updated_at
                """,
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
                user.created_at.isoformat(),
                user.updated_at.isoformat(),
            )

    # ---------------------------------------------------------------
    # Messages
    # ---------------------------------------------------------------

    async def append_message(self, phone: str, msg: ConversationMessage) -> None:
        # Manual dedup: Postgres ON CONFLICT needs an exact index match,
        # but our unique index on wa_message_id is PARTIAL (WHERE NOT
        # NULL). Cleanest path is to check existence first when a
        # wa_message_id is provided.
        async with self._pool.acquire() as conn:
            if msg.wa_message_id:
                exists = await conn.fetchval(
                    "SELECT 1 FROM messages WHERE wa_message_id = $1 LIMIT 1",
                    msg.wa_message_id,
                )
                if exists:
                    return
            await conn.execute(
                """
                INSERT INTO messages
                    (phone, role, content, media_urls, wa_message_id, turn_id, at)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                phone,
                msg.role,
                msg.content,
                json.dumps(msg.media_urls, ensure_ascii=False),
                msg.wa_message_id,
                msg.turn_id,
                msg.at.isoformat(),
            )

    # ---------------------------------------------------------------
    # Appointments
    # ---------------------------------------------------------------

    async def delete_all_for_phone(self, phone: str) -> dict[str, int]:
        """Wipe everything for one phone. Returns counts deleted."""
        async with self._pool.acquire() as conn:
            msg_count = await conn.fetchval(
                "SELECT COUNT(*) FROM messages WHERE phone = $1", phone
            )
            appt_count = await conn.fetchval(
                "SELECT COUNT(*) FROM appointments WHERE phone = $1", phone
            )
            user_count = await conn.fetchval(
                "SELECT COUNT(*) FROM users WHERE phone = $1", phone
            )
            async with conn.transaction():
                await conn.execute("DELETE FROM users WHERE phone = $1", phone)
                await conn.execute("DELETE FROM messages WHERE phone = $1", phone)
                await conn.execute(
                    "DELETE FROM appointments WHERE phone = $1", phone
                )
        return {
            "users": user_count or 0,
            "messages": msg_count or 0,
            "appointments": appt_count or 0,
        }

    async def add_appointment(self, phone: str, appt: AppointmentRecord) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO appointments
                    (phone, clinic_id, date, time, mode, status, booked_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                phone,
                appt.clinic_id,
                appt.date,
                appt.time,
                appt.mode,
                appt.status,
                appt.booked_at.isoformat(),
            )

    # ---------------------------------------------------------------
    # Broadcast tracking (proactive weather care — per-user weekly cap)
    # ---------------------------------------------------------------

    async def list_active_phones(self, limit: int = 5000) -> list[str]:
        """Phones eligible to receive proactive broadcasts (not churned/opted-out)."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT phone FROM users
                WHERE status NOT IN ('churned', 'opted_out')
                ORDER BY updated_at DESC
                LIMIT $1
                """,
                limit,
            )
        return [row["phone"] for row in rows]

    async def get_broadcast_count_this_week(self, phone: str, iso_week: str) -> int:
        """How many broadcasts this user has received in the given ISO week."""
        async with self._pool.acquire() as conn:
            val = await conn.fetchval(
                "SELECT COUNT(*) FROM user_broadcasts WHERE phone = $1 AND iso_week = $2",
                phone,
                iso_week,
            )
        return int(val or 0)

    async def get_last_broadcast_at(self, phone: str) -> str | None:
        """ISO timestamp of the most recent broadcast sent to this user, or None."""
        async with self._pool.acquire() as conn:
            val = await conn.fetchval(
                "SELECT MAX(sent_at) FROM user_broadcasts WHERE phone = $1",
                phone,
            )
        return val

    async def record_broadcast(
        self, phone: str, condition_code: str, iso_week: str, sent_at: str
    ) -> None:
        """Persist a sent broadcast for cap tracking."""
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO user_broadcasts (phone, sent_at, condition_code, iso_week)
                VALUES ($1, $2, $3, $4)
                """,
                phone,
                sent_at,
                condition_code,
                iso_week,
            )

    async def list_phones_for_constitution_recheck(
        self,
        recheck_cutoff: str,
        activity_cutoff: str,
        limit: int = 5000,
    ) -> list[str]:
        """Phones with a known constitution that haven't been rechecked recently."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT u.phone
                FROM users u
                WHERE u.status NOT IN ('churned', 'opted_out')
                  AND u.constitution != 'unknown'
                  AND u.phone NOT IN (
                      SELECT phone FROM user_broadcasts
                      WHERE condition_code = 'constitution_recheck'
                        AND sent_at > $1
                  )
                  AND NOT EXISTS (
                      SELECT 1 FROM messages m
                      WHERE m.phone = u.phone
                        AND m.at > $2
                  )
                ORDER BY u.updated_at ASC
                LIMIT $3
                """,
                recheck_cutoff,
                activity_cutoff,
                limit,
            )
        return [row["phone"] for row in rows]

    async def list_phones_for_purchase_followup(
        self,
        activity_cutoff: str,
        followup_cutoff: str,
        limit: int = 5000,
    ) -> list[str]:
        """Phones that bought something, went quiet, and haven't had a follow-up recently."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT u.phone
                FROM users u
                WHERE u.status NOT IN ('churned', 'opted_out')
                  AND u.products_purchased NOT IN ('[]', '')
                  AND u.phone NOT IN (
                      SELECT phone FROM user_broadcasts
                      WHERE condition_code = 'purchase_followup'
                        AND sent_at > $1
                  )
                  AND NOT EXISTS (
                      SELECT 1 FROM messages m
                      WHERE m.phone = u.phone
                        AND m.at > $2
                  )
                ORDER BY u.updated_at ASC
                LIMIT $3
                """,
                followup_cutoff,
                activity_cutoff,
                limit,
            )
        return [row["phone"] for row in rows]


    async def list_phones_for_upcoming_appointments(
        self,
        within_hours: int = 48,
        limit: int = 5000,
    ) -> list[str]:
        """Phones with a *confirmed* appointment in the next ``within_hours`` hours.

        Uses local HKT time for comparison because appointment date/time is
        stored in clinic-local (HKT) format without timezone offset.
        """
        now = datetime.now(_HKT)
        cutoff = now + timedelta(hours=within_hours)
        now_str = now.strftime("%Y-%m-%d %H:%M")
        cutoff_str = cutoff.strftime("%Y-%m-%d %H:%M")

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT DISTINCT a.phone
                FROM appointments a
                JOIN users u ON a.phone = u.phone
                WHERE u.status NOT IN ('churned', 'opted_out')
                  AND a.status = 'confirmed'
                  AND (a.date || ' ' || a.time) >= $1
                  AND (a.date || ' ' || a.time) <  $2
                ORDER BY (a.date || ' ' || a.time) ASC
                LIMIT $3
                """,
                now_str,
                cutoff_str,
                limit,
            )
        return [row["phone"] for row in rows]


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------


async def _load_history(
    conn: asyncpg.Connection, phone: str, limit: int
) -> list[ConversationMessage]:
    rows = await conn.fetch(
        """
        SELECT role, content, media_urls, wa_message_id, turn_id, at
        FROM messages WHERE phone = $1 ORDER BY at DESC LIMIT $2
        """,
        phone,
        limit,
    )
    out: list[ConversationMessage] = []
    for r in reversed(list(rows)):
        out.append(
            ConversationMessage(
                role=r["role"],
                content=r["content"],
                media_urls=json.loads(r["media_urls"] or "[]"),
                wa_message_id=r["wa_message_id"],
                turn_id=r["turn_id"],
                at=datetime.fromisoformat(r["at"]),
            )
        )
    return out


async def _load_appointments(
    conn: asyncpg.Connection, phone: str
) -> list[AppointmentRecord]:
    rows = await conn.fetch(
        """
        SELECT clinic_id, date, time, mode, status, booked_at
        FROM appointments WHERE phone = $1
        ORDER BY date DESC, time DESC
        """,
        phone,
    )
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


def _row_to_user(
    row: Any,
    history: list[ConversationMessage],
    appointments: list[AppointmentRecord],
) -> User:
    try:
        temp_state = json.loads(row["temp_state"] or "{}")
    except (KeyError, TypeError):
        temp_state = {}
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
        conversation_history=history,
        appointments=appointments,
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
    )


def _split_sql(s: str) -> list[str]:
    """Split a SQL script on semicolons, preserving multi-line statements."""
    # Naive splitter — fine for our schema which has no embedded semicolons.
    return [stmt.strip() + ";" for stmt in s.split(";") if stmt.strip()]
