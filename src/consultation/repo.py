"""Consultation repository — Postgres (asyncpg) with SQLite fallback.

Table: consultations
  id TEXT PRIMARY KEY
  crm_key TEXT NOT NULL
  preferred_time TEXT NOT NULL DEFAULT ''
  status TEXT NOT NULL DEFAULT 'pending'
  patient_joined_at TIMESTAMPTZ
  practitioner_joined_at TIMESTAMPTZ
  created_at TIMESTAMPTZ NOT NULL
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from src.consultation.models import Consultation, ConsultationStatus

logger = logging.getLogger("consultation.repo")

_CREATE_TABLE_PG = """
CREATE TABLE IF NOT EXISTS consultations (
    id                     TEXT        PRIMARY KEY,
    crm_key                TEXT        NOT NULL,
    preferred_time         TEXT        NOT NULL DEFAULT '',
    status                 TEXT        NOT NULL DEFAULT 'pending',
    patient_joined_at      TIMESTAMPTZ,
    practitioner_joined_at TIMESTAMPTZ,
    created_at             TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

_CREATE_TABLE_SQLITE = """
CREATE TABLE IF NOT EXISTS consultations (
    id                     TEXT PRIMARY KEY,
    crm_key                TEXT NOT NULL,
    preferred_time         TEXT NOT NULL DEFAULT '',
    status                 TEXT NOT NULL DEFAULT 'pending',
    patient_joined_at      TEXT,
    practitioner_joined_at TEXT,
    created_at             TEXT NOT NULL
);
"""


def _short_id() -> str:
    return uuid.uuid4().hex[:12]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_dt(value: str | datetime | None) -> datetime | None:
    """Coerce SQLite ISO strings to aware datetime; pass through native datetimes."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    # SQLite stores as string — parse and attach UTC
    try:
        dt = datetime.fromisoformat(str(value))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _row_to_consultation(row: dict | object) -> Consultation:
    """Accept both asyncpg Record (attr access) and sqlite3 Row (dict-like)."""
    def _get(key: str):
        try:
            return row[key]  # type: ignore[index]
        except TypeError:
            return getattr(row, key)

    return Consultation(
        id=_get("id"),
        crm_key=_get("crm_key"),
        preferred_time=_get("preferred_time") or "",
        status=_get("status"),
        created_at=_parse_dt(_get("created_at")) or _now(),
        patient_joined_at=_parse_dt(_get("patient_joined_at")),
        practitioner_joined_at=_parse_dt(_get("practitioner_joined_at")),
    )


class ConsultationRepo:
    """Abstract repo — switch at construction time based on DSN type."""

    def __init__(self, pool_or_path) -> None:  # asyncpg.Pool | str (sqlite path)
        self._backend = pool_or_path
        self._is_pg = not isinstance(pool_or_path, str)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    @classmethod
    async def connect(cls, db_url: str) -> "ConsultationRepo":
        if db_url.startswith(("postgres://", "postgresql://")):
            import asyncpg  # type: ignore[import]
            dsn = db_url.replace("postgres://", "postgresql://", 1)
            pool = await asyncpg.create_pool(dsn, min_size=1, max_size=3,
                                             command_timeout=30)
            async with pool.acquire() as conn:
                await conn.execute(_CREATE_TABLE_PG)
            logger.info("consultation repo: postgres ready")
            return cls(pool)
        else:
            # SQLite — db_url is a file path
            import aiosqlite  # type: ignore[import]
            async with aiosqlite.connect(db_url) as db:
                await db.execute(_CREATE_TABLE_SQLITE)
                await db.commit()
            logger.info("consultation repo: sqlite ready at %s", db_url)
            return cls(db_url)

    async def close(self) -> None:
        if self._is_pg:
            await self._backend.close()

    # ------------------------------------------------------------------
    # Writes
    # ------------------------------------------------------------------

    async def create(
        self,
        crm_key: str,
        preferred_time: str = "",
    ) -> Consultation:
        room_id = _short_id()
        now = _now()
        if self._is_pg:
            async with self._backend.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO consultations (id, crm_key, preferred_time, status, created_at)
                    VALUES ($1, $2, $3, 'pending', $4)
                    """,
                    room_id, crm_key, preferred_time, now,
                )
        else:
            import aiosqlite
            async with aiosqlite.connect(self._backend) as db:
                await db.execute(
                    """
                    INSERT INTO consultations (id, crm_key, preferred_time, status, created_at)
                    VALUES (?, ?, ?, 'pending', ?)
                    """,
                    (room_id, crm_key, preferred_time, now.isoformat()),
                )
                await db.commit()

        return Consultation(
            id=room_id,
            crm_key=crm_key,
            preferred_time=preferred_time,
            status="pending",
            created_at=now,
        )

    async def update_status(self, room_id: str, status: ConsultationStatus) -> None:
        if self._is_pg:
            async with self._backend.acquire() as conn:
                await conn.execute(
                    "UPDATE consultations SET status=$1 WHERE id=$2", status, room_id
                )
        else:
            import aiosqlite
            async with aiosqlite.connect(self._backend) as db:
                await db.execute(
                    "UPDATE consultations SET status=? WHERE id=?", (status, room_id)
                )
                await db.commit()

    async def mark_joined(self, room_id: str, role: str) -> None:
        now = _now()
        col = "patient_joined_at" if role == "patient" else "practitioner_joined_at"
        if self._is_pg:
            async with self._backend.acquire() as conn:
                await conn.execute(
                    f"UPDATE consultations SET {col}=$1 WHERE id=$2",  # noqa: S608
                    now, room_id,
                )
        else:
            import aiosqlite
            async with aiosqlite.connect(self._backend) as db:
                await db.execute(
                    f"UPDATE consultations SET {col}=? WHERE id=?",  # noqa: S608
                    (now.isoformat(), room_id),
                )
                await db.commit()

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    async def list_recent(self, limit: int = 30) -> list[Consultation]:
        if self._is_pg:
            async with self._backend.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT * FROM consultations
                    ORDER BY created_at DESC LIMIT $1
                    """,
                    limit,
                )
            return [_row_to_consultation(r) for r in rows]
        else:
            import aiosqlite
            async with aiosqlite.connect(self._backend) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    "SELECT * FROM consultations ORDER BY created_at DESC LIMIT ?",
                    (limit,),
                ) as cur:
                    rows = await cur.fetchall()
            return [_row_to_consultation(r) for r in rows]

    async def get(self, room_id: str) -> Consultation | None:
        if self._is_pg:
            async with self._backend.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT * FROM consultations WHERE id=$1", room_id
                )
        else:
            import aiosqlite
            async with aiosqlite.connect(self._backend) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    "SELECT * FROM consultations WHERE id=?", (room_id,)
                ) as cur:
                    row = await cur.fetchone()
        return _row_to_consultation(row) if row else None
