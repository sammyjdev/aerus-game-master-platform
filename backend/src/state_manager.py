"""
state_manager.py - Only module with SQLite access.
Every database read and write goes through this layer.
All writes are atomic inside a transaction context.
"""
import logging
import os
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import aiosqlite

from .inventory_manager import (
    get_default_starter_inventory,
    get_default_weight_catalog,
    get_weight_capacity,
    sum_inventory_weight,
)
from .models import (
    MemoryLayers,
    PlayerStatus,
)

logger = logging.getLogger(__name__)

DB_PATH = os.getenv("DATABASE_PATH", "aerus.db")

DEFAULT_START_LOCATION = "Isles of Myr"
COOP_MISSION_ACTIVE_KEY = "cooperative_mission_active"
COOP_MISSION_COMPLETED_KEY = "cooperative_mission_completed"
COOP_MISSION_BLOCKING_KEY = "cooperative_mission_blocking"
COOP_MISSION_REQUIRED_PLAYERS_KEY = "cooperative_mission_required_players"
COOP_MISSION_OBJECTIVE_KEY = "cooperative_mission_objective"
COOP_MISSION_ID_KEY = "cooperative_mission_id"
COOP_MISSION_OBJECTIVE_DEFAULT = (
    "Regroup in the Isles of Myr and align on a joint plan before moving forward."
)


# ---------------------------------------------------------------------------
# Connection and initialization
# ---------------------------------------------------------------------------

async def get_db() -> AsyncGenerator[aiosqlite.Connection, None]:
    """FastAPI Depends() helper that provides a connection with WAL mode enabled."""
    async with aiosqlite.connect(DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA journal_mode=WAL")
        await conn.execute("PRAGMA foreign_keys=ON")
        yield conn


@asynccontextmanager
async def db_context() -> AsyncGenerator[aiosqlite.Connection, None]:
    """Manual context manager for use outside FastAPI dependency injection."""
    async with aiosqlite.connect(DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA journal_mode=WAL")
        await conn.execute("PRAGMA foreign_keys=ON")
        yield conn


async def init_db() -> None:
    """Run all pending schema migrations and seed default state. Called at startup."""
    from .migration_runner import run_migrations

    async with db_context() as conn:
        await run_migrations(conn)
        await ensure_default_world_state(conn)

        # Initialize the calendar if it has not been set up yet
        from .time_manager import initialize_calendar
        await initialize_calendar(conn)

    logger.info("Database initialized at %s", DB_PATH)


# ---------------------------------------------------------------------------
# Invites
# ---------------------------------------------------------------------------

async def create_invite(conn: aiosqlite.Connection, code: str, created_by: str) -> None:
    await conn.execute(
        "INSERT INTO invites (code, created_by, created_at) VALUES (?, ?, ?)",
        (code, created_by, time.time()),
    )
    await conn.commit()


async def redeem_invite(
    conn: aiosqlite.Connection, code: str, player_id: str
) -> bool:
    """Mark an invite as used. Returns False if it does not exist or was already used."""
    async with conn.execute(
        "SELECT used FROM invites WHERE code = ?", (code,)
    ) as cursor:
        row = await cursor.fetchone()

    if row is None or row["used"]:
        return False

    await conn.execute(
        "UPDATE invites SET used = 1, used_by = ? WHERE code = ?",
        (player_id, code),
    )
    await conn.commit()
    return True


# ---------------------------------------------------------------------------
# Players
# ---------------------------------------------------------------------------

async def create_player(
    conn: aiosqlite.Connection,
    player_id: str,
    username: str,
    password_hash: str,
) -> None:
    await conn.execute(
        """INSERT INTO players
           (player_id, username, password_hash, created_at, attributes_json)
           VALUES (?, ?, ?, ?, ?)""",
        (player_id, username, password_hash, time.time(), json.dumps({})),
    )
    await conn.commit()


async def get_player_by_username(
    conn: aiosqlite.Connection, username: str
) -> aiosqlite.Row | None:
    async with conn.execute(
        "SELECT * FROM players WHERE username = ?", (username,)
    ) as cursor:
        return await cursor.fetchone()


async def get_player_by_id(
    conn: aiosqlite.Connection, player_id: str
) -> aiosqlite.Row | None:
    async with conn.execute(
        "SELECT * FROM players WHERE player_id = ?", (player_id,)
    ) as cursor:
        return await cursor.fetchone()


async def get_all_alive_players(conn: aiosqlite.Connection) -> list[aiosqlite.Row]:
    async with conn.execute(
        "SELECT * FROM players WHERE status = 'alive' AND name IS NOT NULL"
    ) as cursor:
        return await cursor.fetchall()


async def set_character(
    conn: aiosqlite.Connection,
    player_id: str,
    name: str,
    race: str,
    faction: str,
    backstory: str,
    inferred_class: str,
    secret_objective: str,
    max_hp: int,
) -> None:
    default_attrs = {
        "strength": 10,
        "dexterity": 10,
        "intelligence": 10,
        "vitality": 10,
        "luck": 10,
        "charisma": 10,
    }
    weight_capacity = get_weight_capacity(default_attrs["strength"], default_attrs["vitality"])
    currency = {
        "copper": 0,
        "silver": 5,
        "gold": 0,
        "platinum": 0,
    }
    await conn.execute(
        """UPDATE players SET
           name = ?, race = ?, faction = ?, backstory = ?,
           inferred_class = ?, secret_objective = ?, max_hp = ?,
           current_hp = ?, attributes_json = ?,
           currency_json = ?, inventory_weight = ?, weight_capacity = ?,
           macros_json = ?, spell_aliases_json = ?, backstory_changed_recently = 0
           WHERE player_id = ?""",
        (
            name, race, faction, backstory,
            inferred_class, secret_objective, max_hp,
            max_hp, json.dumps(default_attrs),
            json.dumps(currency), 0.0, weight_capacity, json.dumps([]), json.dumps({}),
            player_id,
        ),
    )
    await conn.commit()


async def get_character_macros(conn: aiosqlite.Connection, player_id: str) -> list[dict]:
    async with conn.execute(
        "SELECT macros_json FROM players WHERE player_id = ?",
        (player_id,),
    ) as cursor:
        row = await cursor.fetchone()
    if row is None:
        return []
    return json.loads(row["macros_json"] or "[]")


async def set_character_macros(
    conn: aiosqlite.Connection,
    player_id: str,
    macros: list[dict],
) -> bool:
    row = await get_player_by_id(conn, player_id)
    if row is None:
        return False
    await conn.execute(
        "UPDATE players SET macros_json = ? WHERE player_id = ?",
        (json.dumps(macros), player_id),
    )
    await conn.commit()
    return True


async def update_backstory(
    conn: aiosqlite.Connection,
    player_id: str,
    backstory: str,
) -> bool:
    row = await get_player_by_id(conn, player_id)
    if row is None:
        return False
    await conn.execute(
        "UPDATE players SET backstory = ?, backstory_changed_recently = 1 WHERE player_id = ?",
        (backstory, player_id),
    )
    await conn.commit()
    return True


async def get_spell_aliases(conn: aiosqlite.Connection, player_id: str) -> dict[str, str]:
    async with conn.execute(
        "SELECT spell_aliases_json FROM players WHERE player_id = ?",
        (player_id,),
    ) as cursor:
        row = await cursor.fetchone()
    if row is None:
        return {}
    return json.loads(row["spell_aliases_json"] or "{}")


async def set_spell_aliases(
    conn: aiosqlite.Connection,
    player_id: str,
    aliases: dict[str, str],
) -> bool:
    row = await get_player_by_id(conn, player_id)
    if row is None:
        return False
    await conn.execute(
        "UPDATE players SET spell_aliases_json = ? WHERE player_id = ?",
        (json.dumps(aliases), player_id),
    )
    await conn.commit()
    return True


async def recalculate_inventory_weight(conn: aiosqlite.Connection, player_id: str) -> float:
    rows = await get_player_inventory(conn, player_id)
    inventory = [{"name": row["name"], "quantity": row["quantity"]} for row in rows]
    total = sum_inventory_weight(inventory, get_default_weight_catalog())
    await conn.execute(
        "UPDATE players SET inventory_weight = ? WHERE player_id = ?",
        (total, player_id),
    )
    return total


async def seed_starter_inventory(conn: aiosqlite.Connection, player_id: str, backstory: str = "") -> None:
    base_items = get_default_starter_inventory()
    weapon_description = "A simple weapon adjusted to the character's style."
    lower = (backstory or "").lower()
    if any(term in lower for term in ["arco", "bow", "archer", "ranged"]):
        weapon_description = "A basic ranged weapon tailored to the character's background."
    elif any(term in lower for term in ["magia", "magic", "arcano", "arcane"]):
        weapon_description = "A basic channeling weapon suited for early combat focus."

    await conn.execute("DELETE FROM inventory WHERE player_id = ?", (player_id,))
    for item in base_items:
        description = item["description"]
        if item["item_id"] == "starter-weapon":
            description = weapon_description
        await conn.execute(
            """INSERT INTO inventory
               (item_id, player_id, name, description, rarity, quantity, equipped)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                f"{player_id}-{item['item_id']}",
                player_id,
                item["name"],
                description,
                item.get("rarity", "common"),
                int(item.get("quantity", 1)),
                1 if item.get("equipped") else 0,
            ),
        )
    await recalculate_inventory_weight(conn, player_id)
    await conn.commit()


async def apply_state_delta(
    conn: aiosqlite.Connection, player_id: str, delta: dict
) -> None:
    """
    Apply the state delta returned by the GM atomically.
    delta may include: hp_change, attribute_changes, status, experience_gain
    """
    async with conn.execute(
        """SELECT current_hp, max_hp, current_mp, max_mp,
                  current_stamina, max_stamina,
                  experience, level, status, attributes_json
           FROM players WHERE player_id = ?""",
        (player_id,),
    ) as cursor:
        row = await cursor.fetchone()

    if row is None:
        logger.warning("apply_state_delta: player %s not found", player_id)
        return

    attributes = json.loads(row["attributes_json"] or "{}")
    current_hp, current_mp, current_stamina, status = _apply_resource_changes(row, delta)
    experience, level = _apply_xp_and_attrs(row, delta, attributes)

    await conn.execute(
        """UPDATE players SET
           current_hp = ?, current_mp = ?, current_stamina = ?,
           experience = ?, level = ?, status = ?, attributes_json = ?
           WHERE player_id = ?""",
        (current_hp, current_mp, current_stamina,
         experience, level, status, json.dumps(attributes), player_id),
    )
    await _apply_inventory_changes(conn, player_id, delta)
    await _apply_condition_changes(conn, player_id, delta)
    await conn.commit()


def _xp_threshold(level: int) -> int:
    """XP required to advance from level `level` to `level+1`."""
    return level * 100


def _apply_resource_changes(row: aiosqlite.Row, delta: dict) -> tuple[int, int, int, str]:
    """Calculate new HP, MP, stamina, and status values from the delta."""
    current_hp = max(0, min(row["max_hp"], row["current_hp"] + int(delta.get("hp_change", 0))))
    current_mp = max(0, min(row["max_mp"], row["current_mp"] + int(delta.get("mp_change", 0))))
    current_stamina = max(0, min(row["max_stamina"], row["current_stamina"] + int(delta.get("stamina_change", 0))))
    status = PlayerStatus.DEAD.value if current_hp == 0 else delta.get("status", row["status"])
    return current_hp, current_mp, current_stamina, status


def _apply_xp_and_attrs(row: aiosqlite.Row, delta: dict, attributes: dict) -> tuple[int, int]:
    """Calculate new XP and level values, and apply attribute changes in place."""
    experience = row["experience"] + int(delta.get("experience_gain", 0))
    level = row["level"]
    if experience >= _xp_threshold(level):
        experience -= _xp_threshold(level)
        level += 1
    for attr, val in delta.get("attribute_changes", {}).items():
        if attr in attributes:
            attributes[attr] = max(10, attributes[attr] + int(val))
    return experience, level


async def get_player_inventory(
    conn: aiosqlite.Connection, player_id: str
) -> list[aiosqlite.Row]:
    """Return every item in a player inventory."""
    async with conn.execute(
        "SELECT * FROM inventory WHERE player_id = ? ORDER BY rowid",
        (player_id,),
    ) as cursor:
        return await cursor.fetchall()


async def get_player_conditions(
    conn: aiosqlite.Connection, player_id: str
) -> list[aiosqlite.Row]:
    """Return every active condition on a player."""
    async with conn.execute(
        "SELECT * FROM conditions WHERE player_id = ? ORDER BY rowid",
        (player_id,),
    ) as cursor:
        return await cursor.fetchall()


async def _apply_inventory_changes(
    conn: aiosqlite.Connection, player_id: str, delta: dict
) -> None:
    """Apply inventory additions and removals atomically."""
    for item in delta.get("inventory_add", []):
        await conn.execute(
            """INSERT INTO inventory
               (item_id, player_id, name, description, rarity, quantity, equipped)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(item_id) DO UPDATE SET
                 quantity = excluded.quantity,
                 equipped = excluded.equipped""",
            (
                item.get("item_id", ""),
                player_id,
                item.get("name", ""),
                item.get("description", ""),
                item.get("rarity", "common"),
                int(item.get("quantity", 1)),
                1 if item.get("equipped") else 0,
            ),
        )
    for item_id in delta.get("inventory_remove", []):
        await conn.execute(
            "DELETE FROM inventory WHERE item_id = ? AND player_id = ?",
            (item_id, player_id),
        )
    if delta.get("inventory_add") or delta.get("inventory_remove"):
        await recalculate_inventory_weight(conn, player_id)


async def _apply_condition_changes(
    conn: aiosqlite.Connection, player_id: str, delta: dict, turn_number: int = 0
) -> None:
    """Apply condition additions and removals atomically."""
    for cond in delta.get("conditions_add", []):
        await conn.execute(
            """INSERT INTO conditions
               (condition_id, player_id, name, description,
                duration_turns, applied_at_turn, is_buff)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(condition_id) DO UPDATE SET
                 duration_turns = excluded.duration_turns,
                 is_buff        = excluded.is_buff""",
            (
                cond.get("condition_id", ""),
                player_id,
                cond.get("name", ""),
                cond.get("description", ""),
                cond.get("duration_turns"),
                int(cond.get("applied_at_turn", turn_number)),
                1 if cond.get("is_buff") else 0,
            ),
        )
    for cond_id in delta.get("conditions_remove", []):
        await conn.execute(
            "DELETE FROM conditions WHERE condition_id = ? AND player_id = ?",
            (cond_id, player_id),
        )


async def mark_convocation_sent(conn: aiosqlite.Connection, player_id: str) -> None:
    await conn.execute(
        "UPDATE players SET convocation_sent = 1 WHERE player_id = ?", (player_id,)
    )
    await conn.commit()


async def create_dice_roll_request(
    conn: aiosqlite.Connection,
    roll_id: str,
    player_id: str,
    roll_type: str,
    dc: int,
    description: str,
) -> None:
    await conn.execute(
        """INSERT INTO dice_roll_arguments
           (roll_id, player_id, roll_type, dc, description, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (roll_id, player_id, roll_type, int(dc), description, time.time()),
    )
    await conn.commit()


async def get_dice_roll_request(
    conn: aiosqlite.Connection, roll_id: str
) -> aiosqlite.Row | None:
    async with conn.execute(
        "SELECT * FROM dice_roll_arguments WHERE roll_id = ?",
        (roll_id,),
    ) as cursor:
        return await cursor.fetchone()


async def submit_dice_roll_result(
    conn: aiosqlite.Connection,
    roll_id: str,
    player_id: str,
    initial_roll: int,
    initial_result: int,
    argument: str,
) -> bool:
    row = await get_dice_roll_request(conn, roll_id)
    if row is None or row["player_id"] != player_id:
        return False
    if row["argument_submitted"]:
        return False

    await conn.execute(
        """UPDATE dice_roll_arguments SET
           initial_roll = ?,
           initial_result = ?,
           argument = ?,
           argument_submitted = 1
           WHERE roll_id = ?""",
        (int(initial_roll), int(initial_result), argument.strip(), roll_id),
    )
    await conn.commit()
    return True


async def resolve_dice_roll(
    conn: aiosqlite.Connection,
    roll_id: str,
    verdict: str,
    circumstance_bonus: int,
    explanation: str,
) -> aiosqlite.Row | None:
    row = await get_dice_roll_request(conn, roll_id)
    if row is None:
        return None

    initial_result = int(row["initial_result"] or 0)
    bonus = int(circumstance_bonus)
    final_result = initial_result
    if verdict == "accept_with_bonus":
        final_result = initial_result + bonus
    elif verdict in {"accept_no_bonus", "reject"}:
        final_result = initial_result
        bonus = 0
    elif verdict == "reroll_requested":
        final_result = None
        bonus = 0

    await conn.execute(
        """UPDATE dice_roll_arguments SET
           verdict = ?,
           circumstance_bonus = ?,
           final_result = ?,
           explanation = ?,
           resolved_at = ?
           WHERE roll_id = ?""",
        (verdict, bonus, final_result, explanation.strip(), time.time(), roll_id),
    )
    await conn.commit()
    return await get_dice_roll_request(conn, roll_id)


async def set_byok_key(
    conn: aiosqlite.Connection, player_id: str, encrypted_key: str
) -> None:
    await conn.execute(
        "UPDATE players SET byok_key_encrypted = ? WHERE player_id = ?",
        (encrypted_key, player_id),
    )
    await conn.commit()


async def get_byok_key(
    conn: aiosqlite.Connection, player_id: str
) -> str | None:
    async with conn.execute(
        "SELECT byok_key_encrypted FROM players WHERE player_id = ?", (player_id,)
    ) as cursor:
        row = await cursor.fetchone()
    return row["byok_key_encrypted"] if row else None


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------

async def append_history(
    conn: aiosqlite.Connection,
    history_id: str,
    turn_number: int,
    role: str,
    content: str,
) -> None:
    await conn.execute(
        "INSERT INTO history (history_id, turn_number, role, content, created_at) VALUES (?, ?, ?, ?, ?)",
        (history_id, turn_number, role, content, time.time()),
    )
    await conn.commit()


async def get_recent_history(
    conn: aiosqlite.Connection, limit: int = 10
) -> list[aiosqlite.Row]:
    async with conn.execute(
        "SELECT role, content FROM history ORDER BY turn_number DESC, created_at DESC LIMIT ?",
        (limit,),
    ) as cursor:
        rows = await cursor.fetchall()
    return list(reversed(rows))


async def get_current_turn_number(conn: aiosqlite.Connection) -> int:
    async with conn.execute(
        "SELECT COALESCE(MAX(turn_number), 0) as max_turn FROM history"
    ) as cursor:
        row = await cursor.fetchone()
    return int(row["max_turn"]) if row else 0


# ---------------------------------------------------------------------------
# World state & Quest flags
# ---------------------------------------------------------------------------

async def set_world_state(
    conn: aiosqlite.Connection, key: str, value: str
) -> None:
    await conn.execute(
        "INSERT INTO world_state (key, value, updated_at) VALUES (?, ?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at",
        (key, value, time.time()),
    )
    await conn.commit()


async def get_world_state(
    conn: aiosqlite.Connection, key: str
) -> str | None:
    async with conn.execute(
        "SELECT value FROM world_state WHERE key = ?", (key,)
    ) as cursor:
        row = await cursor.fetchone()
    return row["value"] if row else None


async def ensure_default_world_state(conn: aiosqlite.Connection) -> None:
    defaults = {
        "current_location": DEFAULT_START_LOCATION,
        "tension_level": "5",
        "campaign_paused": "0",
        # Travel system keys (empty = sem viagem ativa)
        "travel_active": "0",
        "travel_origin": "",
        "travel_destination": "",
        "travel_day_current": "0",
        "travel_day_total": "0",
        "travel_current_segment": "",
    }
    for key, value in defaults.items():
        existing = await get_world_state(conn, key)
        if existing is None:
            await set_world_state(conn, key, value)


async def set_quest_flag(
    conn: aiosqlite.Connection, key: str, value: str
) -> None:
    await conn.execute(
        "INSERT INTO quest_flags (flag_key, flag_value, updated_at) VALUES (?, ?, ?) "
        "ON CONFLICT(flag_key) DO UPDATE SET flag_value = excluded.flag_value, updated_at = excluded.updated_at",
        (key, value, time.time()),
    )
    await conn.commit()


async def get_quest_flag(
    conn: aiosqlite.Connection, key: str
) -> str | None:
    async with conn.execute(
        "SELECT flag_value FROM quest_flags WHERE flag_key = ?", (key,)
    ) as cursor:
        row = await cursor.fetchone()
    return row["flag_value"] if row else None


async def initialize_or_refresh_cooperative_mission(conn: aiosqlite.Connection) -> dict[str, str]:
    await ensure_default_world_state(conn)
    players = await get_all_alive_players(conn)
    alive_ids = [p["player_id"] for p in players if p["name"]]
    alive_count = len(alive_ids)

    await set_quest_flag(conn, COOP_MISSION_ID_KEY, "mission_coop_intro_v1")
    await set_quest_flag(conn, COOP_MISSION_OBJECTIVE_KEY, COOP_MISSION_OBJECTIVE_DEFAULT)
    await set_quest_flag(conn, COOP_MISSION_REQUIRED_PLAYERS_KEY, str(alive_count))

    if alive_count <= 1:
        await set_quest_flag(conn, COOP_MISSION_ACTIVE_KEY, "0")
        await set_quest_flag(conn, COOP_MISSION_BLOCKING_KEY, "0")
        await set_quest_flag(conn, COOP_MISSION_COMPLETED_KEY, "1")
        return await get_cooperative_mission_state(conn)

    completed_flag = await get_quest_flag(conn, COOP_MISSION_COMPLETED_KEY)
    if completed_flag == "1":
        await set_quest_flag(conn, COOP_MISSION_ACTIVE_KEY, "0")
        await set_quest_flag(conn, COOP_MISSION_BLOCKING_KEY, "0")
        return await get_cooperative_mission_state(conn)

    await set_quest_flag(conn, COOP_MISSION_ACTIVE_KEY, "1")
    await set_quest_flag(conn, COOP_MISSION_BLOCKING_KEY, "1")
    await set_quest_flag(conn, COOP_MISSION_COMPLETED_KEY, "0")

    for player_id in alive_ids:
        key = f"cooperative_mission_player_done:{player_id}"
        if await get_quest_flag(conn, key) is None:
            await set_quest_flag(conn, key, "0")

    return await refresh_cooperative_mission_completion(conn)


async def mark_cooperative_mission_participation(
    conn: aiosqlite.Connection,
    player_id: str,
) -> dict[str, str]:
    active = await get_quest_flag(conn, COOP_MISSION_ACTIVE_KEY)
    if active != "1":
        return await get_cooperative_mission_state(conn)

    await set_quest_flag(conn, f"cooperative_mission_player_done:{player_id}", "1")
    return await refresh_cooperative_mission_completion(conn)


async def refresh_cooperative_mission_completion(conn: aiosqlite.Connection) -> dict[str, str]:
    players = await get_all_alive_players(conn)
    alive_ids = [p["player_id"] for p in players if p["name"]]
    alive_count = len(alive_ids)

    done_count = 0
    for player_id in alive_ids:
        key = f"cooperative_mission_player_done:{player_id}"
        if await get_quest_flag(conn, key) == "1":
            done_count += 1

    await set_quest_flag(conn, COOP_MISSION_REQUIRED_PLAYERS_KEY, str(alive_count))
    await set_quest_flag(conn, "cooperative_mission_completed_players", str(done_count))

    if alive_count > 1 and done_count >= alive_count:
        await set_quest_flag(conn, COOP_MISSION_COMPLETED_KEY, "1")
        await set_quest_flag(conn, COOP_MISSION_ACTIVE_KEY, "0")
        await set_quest_flag(conn, COOP_MISSION_BLOCKING_KEY, "0")
        await set_quest_flag(conn, "cooperative_mission_completed_turn", str(await get_current_turn_number(conn)))

    return await get_cooperative_mission_state(conn)


async def get_cooperative_mission_state(conn: aiosqlite.Connection) -> dict[str, str]:
    keys = [
        COOP_MISSION_ID_KEY,
        COOP_MISSION_OBJECTIVE_KEY,
        COOP_MISSION_ACTIVE_KEY,
        COOP_MISSION_COMPLETED_KEY,
        COOP_MISSION_BLOCKING_KEY,
        COOP_MISSION_REQUIRED_PLAYERS_KEY,
        "cooperative_mission_completed_players",
        "cooperative_mission_completed_turn",
    ]
    result: dict[str, str] = {}
    for key in keys:
        value = await get_quest_flag(conn, key)
        if value is not None:
            result[key] = value
    return result


async def set_player_inferred_class(
    conn: aiosqlite.Connection,
    player_id: str,
    inferred_class: str,
) -> None:
    await conn.execute(
        "UPDATE players SET inferred_class = ? WHERE player_id = ?",
        (inferred_class, player_id),
    )
    await conn.commit()


# ---------------------------------------------------------------------------
# Memory layers
# ---------------------------------------------------------------------------

async def get_memory_layers(
    conn: aiosqlite.Connection, player_ids: list[str]
) -> MemoryLayers:
    char_parts: list[str] = []
    for pid in player_ids:
        async with conn.execute(
            "SELECT content FROM character_memory WHERE player_id = ?", (pid,)
        ) as cursor:
            row = await cursor.fetchone()
        if row and row["content"]:
            char_parts.append(row["content"])

    async with conn.execute(
        "SELECT content FROM world_memory ORDER BY updated_at DESC LIMIT 1"
    ) as cursor:
        world_row = await cursor.fetchone()

    async with conn.execute(
        "SELECT content FROM arc_memory ORDER BY updated_at DESC LIMIT 1"
    ) as cursor:
        arc_row = await cursor.fetchone()

    return MemoryLayers(
        character="\n".join(char_parts),
        world=world_row["content"] if world_row else "",
        arc=arc_row["content"] if arc_row else "",
    )


async def upsert_character_memory(
    conn: aiosqlite.Connection, player_id: str, content: str
) -> None:
    await conn.execute(
        "INSERT INTO character_memory (player_id, content, updated_at) VALUES (?, ?, ?) "
        "ON CONFLICT(player_id) DO UPDATE SET content = excluded.content, updated_at = excluded.updated_at",
        (player_id, content, time.time()),
    )
    await conn.commit()


async def upsert_world_memory(
    conn: aiosqlite.Connection, content: str
) -> None:
    await conn.execute(
        "INSERT INTO world_memory (content, updated_at) VALUES (?, ?)",
        (content, time.time()),
    )
    await conn.commit()


async def upsert_arc_memory(
    conn: aiosqlite.Connection, content: str
) -> None:
    await conn.execute(
        "INSERT INTO arc_memory (content, updated_at) VALUES (?, ?)",
        (content, time.time()),
    )
    await conn.commit()


# ---------------------------------------------------------------------------
# Player episodic memory
# ---------------------------------------------------------------------------


async def save_player_episode(
    conn: aiosqlite.Connection,
    episode_id: str,
    player_id: str,
    turn_number: int,
    event_type: str,
    description: str,
    importance: int = 1,
) -> None:
    """Persist a single episodic memory for a player.

    importance scale: 1 = minor, 2 = notable, 3 = defining
    event_type examples: 'combat_action', 'social_action', 'stealth_action',
                         'moral_choice', 'faction_event', 'level_up', 'death_avoided'
    """
    await conn.execute(
        """
        INSERT INTO player_episodes
            (episode_id, player_id, turn_number, event_type, description, importance, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (episode_id, player_id, turn_number, event_type, description, importance, time.time()),
    )
    await conn.commit()


async def get_player_episodes(
    conn: aiosqlite.Connection,
    player_id: str,
    limit: int = 10,
    min_importance: int = 1,
) -> list[dict]:
    """Return the most important recent episodes for a player."""
    cursor = await conn.execute(
        """
        SELECT episode_id, turn_number, event_type, description, importance
        FROM player_episodes
        WHERE player_id = ? AND importance >= ?
        ORDER BY importance DESC, turn_number DESC
        LIMIT ?
        """,
        (player_id, min_importance, limit),
    )
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def get_player_episode_counts_by_type(
    conn: aiosqlite.Connection,
    player_id: str,
) -> dict[str, int]:
    """Return count of episodes per event_type for behavioral pattern analysis (B5)."""
    cursor = await conn.execute(
        """
        SELECT event_type, COUNT(*) as cnt
        FROM player_episodes
        WHERE player_id = ?
        GROUP BY event_type
        """,
        (player_id,),
    )
    rows = await cursor.fetchall()
    return {row["event_type"]: row["cnt"] for row in rows}


# ---------------------------------------------------------------------------
# Faction reputation
# ---------------------------------------------------------------------------

_FACTION_IDS = [
    "church_pure_flame",
    "empire_valdrek",
    "guild_of_threads",
    "children_of_broken_thread",
    "myr_council",
]
_REPUTATION_MIN = -100
_REPUTATION_MAX = 100


async def get_faction_reputation(
    conn: aiosqlite.Connection, player_id: str
) -> dict[str, int]:
    """Return a dict {faction_id: score} for the player. Missing factions default to 0."""
    async with conn.execute(
        "SELECT faction_id, score FROM faction_reputation WHERE player_id = ?",
        (player_id,),
    ) as cursor:
        rows = await cursor.fetchall()
    result = dict.fromkeys(_FACTION_IDS, 0)
    for row in rows:
        result[row["faction_id"]] = row["score"]
    return result


async def update_faction_reputation(
    conn: aiosqlite.Connection,
    player_id: str,
    faction_id: str,
    delta: int,
) -> int:
    """
    Apply a delta to the player's reputation with a faction. Clamped to [-100, +100].
    Returns the new score.
    """
    current = await get_faction_reputation(conn, player_id)
    old_score = current.get(faction_id, 0)
    new_score = max(_REPUTATION_MIN, min(_REPUTATION_MAX, old_score + delta))

    await conn.execute(
        "INSERT INTO faction_reputation (player_id, faction_id, score, updated_at) "
        "VALUES (?, ?, ?, ?) "
        "ON CONFLICT(player_id, faction_id) DO UPDATE SET "
        "score = excluded.score, updated_at = excluded.updated_at",
        (player_id, faction_id, new_score, time.time()),
    )
    await conn.commit()
    logger.debug(
        "Reputation %s/%s: %+d -> %d", player_id[:8], faction_id, delta, new_score
    )
    return new_score




