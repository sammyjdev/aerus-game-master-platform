"""
travel_manager.py - Travel progression and daily encounter system.

Responsibilities:
- Read routes and locations from travel.yaml
- Roll daily encounters (d20), modified by terrain and tension
- Read and write travel state through world_state (state_manager)

Flow:
  1. The GM or a player declares travel -> start_travel()
  2. Each travel step advances the day -> advance_travel_day() + roll_encounter()
  3. Arrival -> complete_travel() updates current_location
  4. context_builder calls get_travel_state() for L2 context injection
"""
from __future__ import annotations

import logging
import os
import random
from functools import lru_cache
from pathlib import Path
from typing import Any

import aiosqlite
import yaml

logger = logging.getLogger(__name__)

# Config path (mirrors config_loader.py)
_CONFIG_DIR = Path(os.getenv("CONFIG_DIR", Path(__file__).parent.parent.parent / "config"))
_TRAVEL_YAML = _CONFIG_DIR / "travel.yaml"

# world_state keys
_KEY_ACTIVE = "travel_active"
_KEY_ORIGIN = "travel_origin"
_KEY_DESTINATION = "travel_destination"
_KEY_DAY_CURRENT = "travel_day_current"
_KEY_DAY_TOTAL = "travel_day_total"
_KEY_SEGMENT = "travel_current_segment"


@lru_cache(maxsize=1)
def _load_travel() -> dict[str, Any]:
    """Load travel.yaml. Cached - it is not reloaded during runtime."""
    with open(_TRAVEL_YAML, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    logger.info("Loaded travel.yaml from %s", _TRAVEL_YAML)
    return data


def get_location(location_id: str) -> dict[str, Any] | None:
    """Return location metadata or None if the id does not exist."""
    return _load_travel().get("locations", {}).get(location_id)


def get_all_locations() -> dict[str, dict[str, Any]]:
    """Return the full location dictionary."""
    return _load_travel().get("locations", {})


def get_route(origin: str, destination: str) -> dict[str, Any] | None:
    """
    Look up a route between origin and destination (bidirectional).
    Tries the keys 'A->B' and 'B->A'.
    """
    routes = _load_travel().get("routes", {})
    key_fwd = f"{origin}->{destination}"
    key_rev = f"{destination}->{origin}"
    return routes.get(key_fwd) or routes.get(key_rev)


def calculate_travel_days(origin: str, destination: str) -> int | None:
    """Return route total_days, or None if the route is not found."""
    route = get_route(origin, destination)
    return route["total_days"] if route else None


def get_current_segment_terrain(origin: str, destination: str, day: int) -> str:
    """
    Return the terrain of the segment for the current travel day.
    If the day exceeds all segments, return the last segment terrain.
    """
    route = get_route(origin, destination)
    if not route:
        return "wilderness"

    segments = route.get("segments", [])
    if not segments:
        return "wilderness"

    elapsed = 0
    for seg in segments:
        elapsed += seg.get("days", 1)
        if day <= elapsed:
            return seg.get("terrain", "wilderness")

    return segments[-1].get("terrain", "wilderness")


def roll_encounter(terrain: str, tension: int = 5) -> dict[str, Any]:
    """
    Roll a d20 and determine whether an encounter happens.

    Tension modifier: base chance + 3% for each tension point above 5.
    Returns a dict with: triggered, roll, threshold, terrain, chance_percent.
    """
    config = _load_travel()
    base_chance: float = config.get("encounter_chance", {}).get(terrain, 0.30)

    tension_bonus = max(0, tension - 5) * 0.03
    final_chance = min(0.95, base_chance + tension_bonus)

    roll = random.randint(1, 20)
    threshold = round(final_chance * 20)
    triggered = roll <= threshold

    encounter_entry = None
    if triggered:
        table = config.get("encounter_tables", {}).get(terrain, [])
        for entry in table:
            if entry["roll_min"] <= roll <= entry["roll_max"]:
                encounter_entry = entry
                break

    return {
        "triggered": triggered,
        "roll": roll,
        "threshold": threshold,
        "terrain": terrain,
        "chance_percent": round(final_chance * 100),
        "encounter": encounter_entry,
    }


async def start_travel(
    conn: aiosqlite.Connection,
    origin: str,
    destination: str,
) -> dict[str, Any]:
    """
    Start a trip and persist all travel-state keys.
    Returns the initial state or raises ValueError if the route does not exist.
    """
    from . import state_manager  # local import to avoid a circular dependency

    total = calculate_travel_days(origin, destination)
    if total is None:
        raise ValueError(f"Route not found: {origin} -> {destination}")

    terrain = get_current_segment_terrain(origin, destination, 1)

    await state_manager.set_world_state(conn, _KEY_ACTIVE, "1")
    await state_manager.set_world_state(conn, _KEY_ORIGIN, origin)
    await state_manager.set_world_state(conn, _KEY_DESTINATION, destination)
    await state_manager.set_world_state(conn, _KEY_DAY_CURRENT, "1")
    await state_manager.set_world_state(conn, _KEY_DAY_TOTAL, str(total))
    await state_manager.set_world_state(conn, _KEY_SEGMENT, terrain)

    logger.info("Travel started: %s -> %s (%d days)", origin, destination, total)
    return await get_travel_state(conn)


async def advance_travel_day(conn: aiosqlite.Connection) -> dict[str, Any]:
    """
    Advance travel by one day. If the destination was reached, call complete_travel().
    Returns the updated state.
    """
    from . import state_manager

    state = await get_travel_state(conn)
    if not state["active"]:
        return state

    origin = state["origin"]
    destination = state["destination"]
    day_current = state["day_current"] + 1
    day_total = state["day_total"]

    if day_current > day_total:
        return await complete_travel(conn, destination)

    terrain = get_current_segment_terrain(origin, destination, day_current)
    await state_manager.set_world_state(conn, _KEY_DAY_CURRENT, str(day_current))
    await state_manager.set_world_state(conn, _KEY_SEGMENT, terrain)

    return await get_travel_state(conn)


async def complete_travel(conn: aiosqlite.Connection, destination: str) -> dict[str, Any]:
    """
    Finish the trip: update current_location and clear the travel state.
    """
    from . import state_manager

    await state_manager.set_world_state(conn, "current_location", destination)

    for key in (
        _KEY_ACTIVE,
        _KEY_ORIGIN,
        _KEY_DESTINATION,
        _KEY_DAY_CURRENT,
        _KEY_DAY_TOTAL,
        _KEY_SEGMENT,
    ):
        await state_manager.set_world_state(conn, key, "")

    loc = get_location(destination)
    loc_name = loc["name"] if loc else destination
    logger.info("Travel completed. Current location: %s", loc_name)

    return {
        "active": False,
        "arrived": True,
        "destination": destination,
        "destination_name": loc_name,
    }


async def get_travel_state(conn: aiosqlite.Connection) -> dict[str, Any]:
    """
    Return the full travel state for L2 context injection.
    """
    from . import state_manager

    active_raw = await state_manager.get_world_state(conn, _KEY_ACTIVE)
    active = active_raw == "1"

    if not active:
        return {"active": False}

    origin = await state_manager.get_world_state(conn, _KEY_ORIGIN) or ""
    destination = await state_manager.get_world_state(conn, _KEY_DESTINATION) or ""
    day_current = int((await state_manager.get_world_state(conn, _KEY_DAY_CURRENT)) or "1")
    day_total = int((await state_manager.get_world_state(conn, _KEY_DAY_TOTAL)) or "1")
    terrain = await state_manager.get_world_state(conn, _KEY_SEGMENT) or "wilderness"

    origin_loc = get_location(origin)
    destination_loc = get_location(destination)

    return {
        "active": active,
        "origin": origin,
        "origin_name": origin_loc["name"] if origin_loc else origin,
        "destination": destination,
        "destination_name": destination_loc["name"] if destination_loc else destination,
        "day_current": day_current,
        "day_total": day_total,
        "terrain": terrain,
        "days_remaining": max(0, day_total - day_current),
    }

