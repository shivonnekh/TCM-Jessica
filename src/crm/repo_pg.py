"""CRMRepoPG — Postgres-backed CRM repository.

Mirrors the public API of ``CRMRepo`` (the SQLite implementation) so the
caller doesn't care which driver is in use. Switch happens in
``CRMRepo.connect()`` based on the connection URL.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

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
        async with self._pool.acquire() as conn:
            # ON CONFLICT on the partial unique index `idx_messages_wa_id`
            # so duplicate wa_message_id is ignored.
            await conn.execute(
                """
                INSERT INTO messages
                    (phone, role, content, media_urls, wa_message_id, turn_id, at)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (wa_message_id) DO NOTHING
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
