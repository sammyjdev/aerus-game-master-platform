"""
migration_runner.py — Versioned SQLite schema migration system.

Migrations live in backend/migrations/ as numbered SQL files:
  001_initial_schema.sql
  002_player_resource_pools.sql
  ...

The runner tracks applied migrations in a `schema_migrations` table and applies
only the ones that have not been run yet, in numeric order.
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path

import aiosqlite

logger = logging.getLogger(__name__)

MIGRATIONS_DIR = Path(__file__).parent.parent / "migrations"

_MIGRATION_PATTERN = re.compile(r"^(\d{3})_.+\.sql$")


def _discover_migrations() -> list[tuple[int, Path]]:
    """Return sorted list of (version_number, path) for all migration files."""
    migrations: list[tuple[int, Path]] = []
    if not MIGRATIONS_DIR.is_dir():
        return migrations
    for entry in MIGRATIONS_DIR.iterdir():
        match = _MIGRATION_PATTERN.match(entry.name)
        if match:
            migrations.append((int(match.group(1)), entry))
    migrations.sort(key=lambda x: x[0])
    return migrations


async def _ensure_migrations_table(conn: aiosqlite.Connection) -> None:
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version     INTEGER PRIMARY KEY,
            filename    TEXT NOT NULL,
            applied_at  REAL NOT NULL
        )
    """)
    await conn.commit()


async def _applied_versions(conn: aiosqlite.Connection) -> set[int]:
    cursor = await conn.execute("SELECT version FROM schema_migrations")
    rows = await cursor.fetchall()
    return {row[0] for row in rows}


async def run_migrations(conn: aiosqlite.Connection) -> None:
    """Apply all pending migrations in version order. Safe to call on every startup."""
    import time

    await _ensure_migrations_table(conn)
    applied = await _applied_versions(conn)
    migrations = _discover_migrations()

    if not migrations:
        logger.warning("No migration files found in %s", MIGRATIONS_DIR)
        return

    pending = [(v, p) for v, p in migrations if v not in applied]
    if not pending:
        logger.debug("All %d migrations already applied.", len(migrations))
        return

    for version, path in pending:
        sql = path.read_text(encoding="utf-8")
        # Strip comment-only lines so executescript doesn't choke on them
        statements = [s.strip() for s in sql.split(";") if s.strip() and not s.strip().startswith("--")]
        for statement in statements:
            try:
                await conn.execute(statement)
            except Exception as exc:
                # Column-already-exists is expected when upgrading a pre-migration DB
                if "duplicate column" in str(exc).lower() or "already exists" in str(exc).lower():
                    logger.debug("Migration %03d: skipping already-present statement (%s)", version, exc)
                else:
                    logger.error("Migration %03d failed: %s\nSQL: %s", version, exc, statement)
                    raise
        await conn.execute(
            "INSERT INTO schema_migrations (version, filename, applied_at) VALUES (?, ?, ?)",
            (version, path.name, time.time()),
        )
        await conn.commit()
        logger.info("Migration %03d applied: %s", version, path.name)
