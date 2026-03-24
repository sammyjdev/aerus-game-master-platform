"""
time_manager.py - Aerus calendar tracking in the database.
Persists calendar state through the world_state table without depending on state_manager.

Ash Calendar:
  - 3 seasons of 90 days = 270 days per year
  - Kael-High (days 1-90): summer
  - Crossing (days 91-180): unstable weather
  - Syr-High (days 181-270): winter
  - Current campaign year: 4217 PC (post-Sealing)
  - Starting point: day 91 (first day of Crossing)
"""
from __future__ import annotations

import logging
import time

import aiosqlite

logger = logging.getLogger(__name__)

_KEY_DAY = "calendar_day"
_KEY_SEASON = "calendar_season"
_KEY_YEAR = "calendar_year"

_START_DAY = 91
_START_SEASON = "Crossing"
_START_YEAR = 4217

_DAYS_PER_YEAR = 270
_SEASONS = [
    (1, 90, "Kael-High"),
    (91, 180, "Crossing"),
    (181, 270, "Syr-High"),
]


def _day_to_season(day: int) -> str:
    """Return the season name for a given day of the year (1-270)."""
    for start, end, name in _SEASONS:
        if start <= day <= end:
            return name
    return "Crossing"


async def _get_world_value(conn: aiosqlite.Connection, key: str) -> str | None:
    async with conn.execute("SELECT value FROM world_state WHERE key = ?", (key,)) as cursor:
        row = await cursor.fetchone()
        return row[0] if row else None


async def _set_world_value(conn: aiosqlite.Connection, key: str, value: str) -> None:
    now = time.time()
    await conn.execute(
        "INSERT INTO world_state (key, value, updated_at) VALUES (?, ?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at",
        (key, value, now),
    )
    await conn.commit()


async def initialize_calendar(conn: aiosqlite.Connection) -> None:
    """
    Initialize the calendar with the campaign starting values if they do not
    already exist in the database. Called during init_db().
    """
    existing = await _get_world_value(conn, _KEY_DAY)
    if existing is not None:
        return

    await _set_world_value(conn, _KEY_DAY, str(_START_DAY))
    await _set_world_value(conn, _KEY_SEASON, _START_SEASON)
    await _set_world_value(conn, _KEY_YEAR, str(_START_YEAR))
    logger.info("Calendar initialized: Year %d, %s, day %d", _START_YEAR, _START_SEASON, _START_DAY)


async def get_current_date(conn: aiosqlite.Connection) -> dict:
    """
    Return the current calendar state.

    Returns:
        {
            "day": int,
            "season": str,
            "year": int,
            "description": str
        }
    """
    day = int(await _get_world_value(conn, _KEY_DAY) or _START_DAY)
    season = await _get_world_value(conn, _KEY_SEASON) or _START_SEASON
    year = int(await _get_world_value(conn, _KEY_YEAR) or _START_YEAR)

    description = f"Year {year} PC, {season}, day {day} of the year"
    return {"day": day, "season": season, "year": year, "description": description}


async def advance_days(conn: aiosqlite.Connection, days: int) -> dict:
    """
    Advance the calendar by N days, updating season and year as needed.

    Returns the new calendar state in the same format as get_current_date().
    """
    if days <= 0:
        return await get_current_date(conn)

    day = int(await _get_world_value(conn, _KEY_DAY) or _START_DAY)
    year = int(await _get_world_value(conn, _KEY_YEAR) or _START_YEAR)

    day += days
    while day > _DAYS_PER_YEAR:
        day -= _DAYS_PER_YEAR
        year += 1

    season = _day_to_season(day)

    await _set_world_value(conn, _KEY_DAY, str(day))
    await _set_world_value(conn, _KEY_SEASON, season)
    await _set_world_value(conn, _KEY_YEAR, str(year))

    logger.debug("Calendar advanced %d day(s): Year %d, %s, day %d", days, year, season, day)

    description = f"Year {year} PC, {season}, day {day} of the year"
    return {"day": day, "season": season, "year": year, "description": description}
