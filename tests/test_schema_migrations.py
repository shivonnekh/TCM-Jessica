"""Migration-path tests — verify "OLD DB schema + NEW code" doesn't crash.

Why this file exists
--------------------
2026-05-26 prod-down: a new code release expected ``users.last_period_start``
and ``users.cycle_length_days`` columns. Prod Postgres was created earlier
than the model change, so the columns were missing. ``CREATE TABLE IF NOT
EXISTS`` did not add them. Every ``save_user`` then crashed with
``UndefinedColumnError``.

The previous test suite never caught this because every test creates a
fresh DB with the *current* schema. There was no test that simulated
"existing DB with older schema → new code connects → migration must
apply ADD COLUMN".

These tests fill that gap. The pattern is:

  1. Create a DB with a deliberately *truncated* (older) schema
  2. Seed it with realistic legacy rows
  3. Open it via the production code path (``CRMRepo.connect``)
  4. Verify (a) the migration added the missing columns and (b) the
     legacy rows still readable + writable through the new model

When you add a new column to the User model, ALSO add it to
``_USER_COLUMN_MIGRATIONS`` in ``src/crm/repo.py`` (and
``_PG_USER_COLUMN_MIGRATIONS`` in ``src/crm/repo_pg.py``) AND extend
the ``EXPECTED_NEW_COLUMNS`` constant below.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import aiosqlite
import pytest

from src.crm.models import Constitution, User, UserStatus
from src.crm.repo import (
    _USER_COLUMN_MIGRATIONS,
    CRMRepo,
    _migrate_add_user_columns,
)
from src.crm.repo_pg import (
    _PG_USER_COLUMN_MIGRATIONS,
    _migrate_pg_user_columns,
)


# Columns added since the original schema. When the User model grows a
# new persisted column, this list (and the migration tables in repo.py /
# repo_pg.py) MUST grow together.
EXPECTED_NEW_COLUMNS: frozenset[str] = frozenset({
    "last_period_start",
    "cycle_length_days",
})


# Schema as of 2026-05-25 (the day BEFORE menstrual fields were added).
# Used to simulate an existing prod DB created before the model change.
_LEGACY_SCHEMA_SQL = """
CREATE TABLE users (
    phone           TEXT PRIMARY KEY,
    name            TEXT,
    status          TEXT NOT NULL DEFAULT 'new',
    age             INTEGER,
    location        TEXT,
    district        TEXT,
    constitution    TEXT NOT NULL DEFAULT 'unknown',
    pain_points     TEXT NOT NULL DEFAULT '[]',
    products_pitched   TEXT NOT NULL DEFAULT '[]',
    products_purchased TEXT NOT NULL DEFAULT '[]',
    notes           TEXT NOT NULL DEFAULT '',
    tags            TEXT NOT NULL DEFAULT '[]',
    temp_state      TEXT NOT NULL DEFAULT '{}',
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);

CREATE TABLE messages (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    phone           TEXT NOT NULL,
    role            TEXT NOT NULL,
    content         TEXT NOT NULL,
    media_urls      TEXT NOT NULL DEFAULT '[]',
    wa_message_id   TEXT,
    turn_id         TEXT,
    at              TEXT NOT NULL,
    FOREIGN KEY (phone) REFERENCES users(phone) ON DELETE CASCADE
);

CREATE TABLE appointments (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    phone           TEXT NOT NULL,
    clinic_id       TEXT NOT NULL,
    date            TEXT NOT NULL,
    time            TEXT NOT NULL,
    mode            TEXT NOT NULL,
    status          TEXT NOT NULL,
    booked_at       TEXT NOT NULL,
    FOREIGN KEY (phone) REFERENCES users(phone) ON DELETE CASCADE
);

CREATE TABLE user_broadcasts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    phone           TEXT NOT NULL,
    sent_at         TEXT NOT NULL,
    condition_code  TEXT NOT NULL,
    iso_week        TEXT NOT NULL,
    FOREIGN KEY (phone) REFERENCES users(phone) ON DELETE CASCADE
);
"""


# ---------------------------------------------------------------------------
# Migration table self-checks
# ---------------------------------------------------------------------------


def test_sqlite_and_pg_migration_tables_agree() -> None:
    """The two migration tables MUST add the same columns — otherwise
    Postgres and SQLite users will silently diverge."""
    sqlite_cols = {col for col, _ddl in _USER_COLUMN_MIGRATIONS}
    pg_cols = {col for col, _ddl in _PG_USER_COLUMN_MIGRATIONS}
    assert sqlite_cols == pg_cols, (
        f"SQLite and PG migrations disagree: sqlite-only={sqlite_cols - pg_cols} "
        f"pg-only={pg_cols - sqlite_cols}"
    )


def test_migration_tables_cover_all_expected_columns() -> None:
    """Every column that the User model grew since the original schema
    MUST be in both migration tables. Forgetting an entry here is what
    caused the 2026-05-26 prod-down."""
    sqlite_cols = {col for col, _ddl in _USER_COLUMN_MIGRATIONS}
    missing = EXPECTED_NEW_COLUMNS - sqlite_cols
    assert not missing, (
        f"Migration table is missing columns: {missing}. "
        f"Add them to _USER_COLUMN_MIGRATIONS in src/crm/repo.py "
        f"AND _PG_USER_COLUMN_MIGRATIONS in src/crm/repo_pg.py."
    )


# ---------------------------------------------------------------------------
# SQLite migration-path tests
# ---------------------------------------------------------------------------


async def _seed_legacy_sqlite(db_path: Path) -> None:
    """Create a SQLite DB with the pre-2026-05-26 schema + one legacy row."""
    db = await aiosqlite.connect(str(db_path))
    try:
        await db.executescript(_LEGACY_SCHEMA_SQL)
        await db.execute(
            """
            INSERT INTO users
                (phone, name, status, constitution, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "+85291000001",
                "Legacy Apple",
                UserStatus.QUALIFIED.value,
                Constitution.YANGXU.value,
                "2026-05-21T10:00:00",
                "2026-05-21T10:00:00",
            ),
        )
        await db.commit()
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_legacy_sqlite_db_migrates_on_connect(tmp_path: Path) -> None:
    """Opening a legacy DB via CRMRepo.connect must add the new columns
    without losing existing rows. This is the exact scenario that broke
    prod on 2026-05-26."""
    db_path = tmp_path / "legacy.db"
    await _seed_legacy_sqlite(db_path)

    # Sanity: the legacy DB really is missing the new columns.
    raw = await aiosqlite.connect(str(db_path))
    cur = await raw.execute("PRAGMA table_info(users)")
    rows = await cur.fetchall()
    columns_before = {r[1] for r in rows}
    await raw.close()
    assert not (EXPECTED_NEW_COLUMNS & columns_before), (
        "Legacy schema fixture is contaminated — should not have new columns"
    )

    # Now open via the production code path.
    repo = await CRMRepo.connect(db_path)
    try:
        # Re-inspect after migration
        cur = await repo._db.execute("PRAGMA table_info(users)")  # noqa: SLF001
        rows = await cur.fetchall()
        columns_after = {r[1] for r in rows}

        for col in EXPECTED_NEW_COLUMNS:
            assert col in columns_after, (
                f"Migration did not add column {col!r} — "
                f"prod will crash on save_user"
            )

        # The legacy row must still be readable through the new model
        user = await repo.get_user("+85291000001")
        assert user is not None
        assert user.name == "Legacy Apple"
        assert user.constitution == Constitution.YANGXU
        # New fields take their model defaults
        assert user.last_period_start is None
        assert user.cycle_length_days == 28
    finally:
        await repo.close()


@pytest.mark.asyncio
async def test_legacy_db_supports_save_user_with_new_fields(tmp_path: Path) -> None:
    """After migration, save_user with the new fields populated must
    persist and round-trip cleanly."""
    from datetime import date

    db_path = tmp_path / "legacy.db"
    await _seed_legacy_sqlite(db_path)

    repo = await CRMRepo.connect(db_path)
    try:
        user = await repo.get_user("+85291000001")
        assert user is not None
        updated = user.with_updates(
            last_period_start=date(2026, 5, 20),
            cycle_length_days=30,
        )
        await repo.save_user(updated)

        round_tripped = await repo.get_user("+85291000001")
        assert round_tripped is not None
        assert round_tripped.last_period_start == date(2026, 5, 20)
        assert round_tripped.cycle_length_days == 30
        # Legacy fields preserved
        assert round_tripped.name == "Legacy Apple"
        assert round_tripped.constitution == Constitution.YANGXU
    finally:
        await repo.close()


@pytest.mark.asyncio
async def test_migration_is_idempotent(tmp_path: Path) -> None:
    """Connecting to an already-migrated DB must be a no-op, not a crash.
    Render restarts the service many times — every restart re-runs connect()."""
    db_path = tmp_path / "legacy.db"
    await _seed_legacy_sqlite(db_path)

    # First connect: applies migration
    repo1 = await CRMRepo.connect(db_path)
    await repo1.close()

    # Second connect: must not raise (column already added)
    repo2 = await CRMRepo.connect(db_path)
    try:
        cur = await repo2._db.execute("PRAGMA table_info(users)")  # noqa: SLF001
        rows = await cur.fetchall()
        # Each added column appears exactly once (no duplicates from re-running)
        col_counts: dict[str, int] = {}
        for r in rows:
            col_counts[r[1]] = col_counts.get(r[1], 0) + 1
        for col in EXPECTED_NEW_COLUMNS:
            assert col_counts.get(col, 0) == 1, (
                f"Column {col!r} appeared {col_counts.get(col, 0)} times — "
                f"migration is not idempotent"
            )
    finally:
        await repo2.close()


@pytest.mark.asyncio
async def test_fresh_db_already_has_new_columns(tmp_path: Path) -> None:
    """A brand-new DB built from the current schema.sql must include the
    new columns directly — the migration step exists for upgrading old
    DBs, but fresh installs should never need it to take effect."""
    db_path = tmp_path / "fresh.db"
    repo = await CRMRepo.connect(db_path)
    try:
        cur = await repo._db.execute("PRAGMA table_info(users)")  # noqa: SLF001
        rows = await cur.fetchall()
        columns = {r[1] for r in rows}
        for col in EXPECTED_NEW_COLUMNS:
            assert col in columns, (
                f"Fresh schema is missing {col!r} — schema.sql is out of "
                f"sync with the User model"
            )
    finally:
        await repo.close()


@pytest.mark.asyncio
async def test_migrate_helper_safe_on_already_migrated_db(tmp_path: Path) -> None:
    """Direct call to _migrate_add_user_columns must skip columns that
    already exist. Pure unit test, no full connect() needed."""
    db_path = tmp_path / "already.db"
    db = await aiosqlite.connect(str(db_path))
    try:
        await db.executescript(_LEGACY_SCHEMA_SQL)
        # Pre-add the columns manually so the helper sees them as existing
        for _col, ddl in _USER_COLUMN_MIGRATIONS:
            await db.execute(f"ALTER TABLE users ADD COLUMN {ddl}")
        await db.commit()
        # Calling the helper again must not raise
        await _migrate_add_user_columns(db)  # idempotent
    finally:
        await db.close()


# ---------------------------------------------------------------------------
# Postgres migration helper — unit test with mocked asyncpg connection
# ---------------------------------------------------------------------------
# We can't spin up a real Postgres in CI cheaply, but the migration helper
# is small and pure: it queries information_schema, then conditionally
# runs ALTER TABLE. Mock the connection's fetchval + execute and verify
# the right calls happen.


@pytest.mark.asyncio
async def test_pg_migration_adds_only_missing_columns() -> None:
    """When information_schema reports a column missing, helper must
    run ALTER TABLE for that column. When present, must skip."""
    conn = MagicMock()

    # First column: missing → fetchval returns None
    # Second column: present → fetchval returns 1
    fetchval_responses = [None, 1]
    conn.fetchval = AsyncMock(side_effect=fetchval_responses)
    conn.execute = AsyncMock()

    await _migrate_pg_user_columns(conn)

    # Should have checked both columns
    assert conn.fetchval.await_count == len(_PG_USER_COLUMN_MIGRATIONS)
    # Should have only ALTER'd the missing one
    assert conn.execute.await_count == 1
    altered_sql = conn.execute.await_args_list[0][0][0]
    expected_col = _PG_USER_COLUMN_MIGRATIONS[0][0]
    assert expected_col in altered_sql
    assert "ALTER TABLE users ADD COLUMN" in altered_sql


@pytest.mark.asyncio
async def test_pg_migration_skips_all_when_already_migrated() -> None:
    """All columns present → zero ALTER TABLE calls."""
    conn = MagicMock()
    conn.fetchval = AsyncMock(return_value=1)  # every column exists
    conn.execute = AsyncMock()

    await _migrate_pg_user_columns(conn)

    assert conn.fetchval.await_count == len(_PG_USER_COLUMN_MIGRATIONS)
    assert conn.execute.await_count == 0  # nothing to ALTER


@pytest.mark.asyncio
async def test_pg_migration_adds_all_when_db_is_pristine_legacy() -> None:
    """Cold prod scenario: all new columns missing → ALTER TABLE for each."""
    conn = MagicMock()
    conn.fetchval = AsyncMock(return_value=None)  # nothing exists
    conn.execute = AsyncMock()

    await _migrate_pg_user_columns(conn)

    assert conn.execute.await_count == len(_PG_USER_COLUMN_MIGRATIONS)
    # Each ALTER references the corresponding column name
    for i, (col_name, _ddl) in enumerate(_PG_USER_COLUMN_MIGRATIONS):
        sql = conn.execute.await_args_list[i][0][0]
        assert col_name in sql
        assert "ALTER TABLE users ADD COLUMN" in sql


@pytest.mark.asyncio
async def test_pg_migration_queries_correct_table() -> None:
    """The information_schema lookup must reference 'users' table —
    a typo here would silently no-op every migration."""
    conn = MagicMock()
    conn.fetchval = AsyncMock(return_value=1)
    conn.execute = AsyncMock()

    await _migrate_pg_user_columns(conn)

    for call in conn.fetchval.await_args_list:
        sql = call[0][0]
        assert "information_schema.columns" in sql
        assert "users" in sql


# ---------------------------------------------------------------------------
# Reference-grade legacy seed (older schema versions)
# ---------------------------------------------------------------------------
# When the schema gains MORE columns later, add a new _LEGACY_SCHEMA_*
# constant + matching test that ensures upgrades from THAT version also
# work. This way every historical schema has a regression test.


def test_legacy_schema_sql_is_self_contained() -> None:
    """Quick safety: the legacy SQL fixture compiles + has no stray
    references. If you edit it, this catches dumb typos before running
    a full async test."""
    import sqlite3

    conn = sqlite3.connect(":memory:")
    try:
        conn.executescript(_LEGACY_SCHEMA_SQL)
        # Verify each expected table got created
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = {row[0] for row in cur.fetchall()}
        for required in ("users", "messages", "appointments", "user_broadcasts"):
            assert required in tables, f"legacy schema missing {required!r}"
    finally:
        conn.close()
