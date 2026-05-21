"""Dispatch to the right CRM driver based on DATABASE_URL.

- postgres:// or postgresql://  → CRMRepoPG (asyncpg)
- anything else (file path, empty, or sqlite:...)  → CRMRepo (aiosqlite)

Both implement the same async surface; the caller doesn't care.
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger("crm.factory")


async def open_crm_repo(database_url_or_path: str) -> Any:
    """Return a repo (CRMRepoPG or CRMRepo) connected to the target DB."""
    is_pg = database_url_or_path.startswith(("postgres://", "postgresql://"))
    if is_pg:
        from src.crm.repo_pg import CRMRepoPG

        logger.info("CRM: using PostgreSQL backend")
        return await CRMRepoPG.connect(database_url_or_path)
    from src.crm.repo import CRMRepo

    logger.info("CRM: using SQLite backend at %s", database_url_or_path)
    return await CRMRepo.connect(database_url_or_path)


def resolve_database_url(default_sqlite_path: str) -> str:
    """Resolve the effective DB URL/path from env.

    Priority:
      1. DATABASE_URL env var (Render Postgres injects this)
      2. DATABASE_PATH env var (legacy SQLite path)
      3. default_sqlite_path argument
    """
    url = os.environ.get("DATABASE_URL", "").strip()
    if url:
        return url
    return os.environ.get("DATABASE_PATH", default_sqlite_path)
