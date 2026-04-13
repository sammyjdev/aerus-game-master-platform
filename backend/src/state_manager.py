"""
state_manager.py - Only module with SQLite access.
Every database read and write goes through this layer.
All writes are atomic inside a transaction context.
"""
import json
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

# ---------------------------------------------------------------------------
# Racial attribute tables & skill bonuses
# ---------------------------------------------------------------------------

_RACIAL_ATTRS: dict[str, dict[str, int]] = {
    "human_northerner":   {"strength": 11, "dexterity": 10, "intelligence": 12, "vitality": 11, "luck":  8, "charisma":  8},
    "human_trader":       {"strength":  8, "dexterity": 12, "intelligence": 10, "vitality":  9, "luck": 15, "charisma":  6},
    "human_khorathi":     {"strength": 10, "dexterity": 11, "intelligence":  9, "vitality": 15, "luck":  8, "charisma":  7},
    "human_dawnmere":     {"strength":  9, "dexterity": 11, "intelligence": 11, "vitality":  9, "luck": 10, "charisma": 10},
    "elf_twilight":       {"strength":  7, "dexterity": 12, "intelligence": 15, "vitality":  9, "luck":  8, "charisma":  9},
    "elf_corrupted_fae":  {"strength":  7, "dexterity": 12, "intelligence": 12, "vitality":  9, "luck": 11, "charisma":  9},
    "elf_mist":           {"strength":  7, "dexterity": 12, "intelligence": 11, "vitality":  9, "luck": 12, "charisma":  9},
    "elf_wandering_fae":  {"strength":  7, "dexterity": 15, "intelligence": 10, "vitality":  9, "luck": 10, "charisma":  9},
    "forger_stone_goliath": {"strength": 15, "dexterity": 7, "intelligence": 9, "vitality": 12, "luck": 8, "charisma": 9},
    "forger_deep_dwarf":  {"strength": 11, "dexterity":  9, "intelligence": 12, "vitality": 12, "luck":  8, "charisma":  8},
    "forger_stenvaard":   {"strength": 12, "dexterity":  8, "intelligence": 10, "vitality": 12, "luck":  9, "charisma":  9},
}

# Neutral fallback (all 10s) used when no subrace is specified
_DEFAULT_ATTRS: dict[str, int] = {k: 10 for k in ("strength", "dexterity", "intelligence", "vitality", "luck", "charisma")}

# Racial starting skills: {subrace: {skill_key: {rank, uses, impact}}}
_RACIAL_SKILLS: dict[str, dict[str, dict]] = {
    "human_northerner":   {"ash_memory": {"rank": 2, "uses": 8, "impact": 8.0}, "history": {"rank": 2, "uses": 8, "impact": 8.0}},
    "human_trader":       {"negotiation": {"rank": 2, "uses": 8, "impact": 8.0}, "influence_trade": {"rank": 2, "uses": 8, "impact": 8.0}},
    "human_khorathi":     {"camp_craft": {"rank": 2, "uses": 8, "impact": 8.0}},
    "human_dawnmere":     {"thread_sensing": {"rank": 2, "uses": 8, "impact": 8.0}},
    "elf_twilight":       {"detect_magic": {"rank": 2, "uses": 8, "impact": 8.0}, "corruption_reading": {"rank": 2, "uses": 8, "impact": 8.0}},
    "elf_corrupted_fae":  {"detect_magic": {"rank": 2, "uses": 8, "impact": 8.0}, "corruption_reading": {"rank": 2, "uses": 8, "impact": 8.0}},
    "elf_mist":           {"detect_magic": {"rank": 2, "uses": 8, "impact": 8.0}, "corruption_reading": {"rank": 2, "uses": 8, "impact": 8.0}},
    "elf_wandering_fae":  {"detect_magic": {"rank": 2, "uses": 8, "impact": 8.0}, "corruption_reading": {"rank": 2, "uses": 8, "impact": 8.0}},
    "forger_stone_goliath": {"smithing": {"rank": 3, "uses": 15, "impact": 18.0}},
    "forger_deep_dwarf":  {"appraise": {"rank": 2, "uses": 8, "impact": 8.0}, "ruin_reading": {"rank": 2, "uses": 8, "impact": 8.0}},
    "forger_stenvaard":   {"smithing": {"rank": 3, "uses": 15, "impact": 18.0}},
}

# Skill categories and their sub-skill keys (14 categories)
SKILL_CATEGORIES: dict[str, list[str]] = {
    "combat":     ["grapple", "counterstrike", "dual_wield", "weapon_flow", "endurance_combat"],
    "stealth":    ["conceal", "pickpocket", "lockpick", "ambush", "disguise"],
    "social":     ["persuasion", "intimidation", "deception", "negotiation", "charm"],
    "politics":   ["court_etiquette", "faction_negotiation", "rhetoric", "law", "influence_trade"],
    "survival":   ["foraging", "tracking", "navigation", "first_aid", "camp_craft"],
    "medicine":   ["wound_treatment", "poison_lore", "disease_diagnosis", "herbalism", "surgery"],
    "lore":       ["arcane_lore", "history", "faction_lore", "creature_lore", "ruin_reading"],
    "crafting":   ["smithing", "alchemy", "artifice", "runework", "tailoring"],
    "ritual":     ["thread_sensing", "spirit_binding", "corruption_reading", "seal_work", "resonance"],
    "athletics":  ["climbing", "swimming", "sprinting", "acrobatics", "lifting"],
    "perception": ["detect_magic", "detect_lie", "search", "listen", "appraise"],
    "nature":     ["beast_handling", "herbalism_wild", "weather_reading", "terrain_lore", "poison_craft"],
    "tactics":    ["battle_tactics", "group_command", "ambush_planning", "retreat_coordination", "morale"],
    "mysticism":  ["dream_reading", "void_lore", "prophecy", "fragment_reading", "ash_memory"],
}

# Reverse map: skill_key → category
_SKILL_TO_CATEGORY: dict[str, str] = {
    sk: cat for cat, keys in SKILL_CATEGORIES.items() for sk in keys
}

# Class affinity: inferred_class → list of primary skill categories
_CLASS_AFFINITIES: dict[str, list[str]] = {
    "Blade":        ["combat", "athletics"],
    "Sorcerer":     ["lore", "ritual", "mysticism"],
    "Sharpshooter": ["stealth", "perception", "survival"],
    "Shadow":       ["stealth", "perception", "social"],
    "Herald":       ["social", "politics", "tactics"],
    "Sentinel":     ["combat", "athletics", "tactics"],
    "Channeler":    ["ritual", "mysticism", "lore"],
    "Wanderer":     ["survival", "nature", "medicine"],
}

# Campaign attribute caps (must match campaign.yaml)
ATTRIBUTE_PER_CAP = 250
ATTRIBUTE_AP_BUDGET = 500   # total AP available from levelling at level 100

# ---------------------------------------------------------------------------
# Skill progression helpers
# ---------------------------------------------------------------------------

def _skill_impact_threshold(target_rank: int) -> float:
    """Accumulated impact required to reach target_rank. Formula: target_rank² × 2."""
    return float(target_rank * target_rank * 2)


def _pp_cost(current_rank: int) -> int:
    """PP cost to upgrade weapon/magic proficiency from current_rank to current_rank+1."""
    return (current_rank // 4) + 1

# Isekai rooting: days thresholds per stage (index == stage number)
ROOTING_THRESHOLDS = [0, 365, 730, 1095, 1825]

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
    subrace: str | None = None,
) -> None:
    # Use racial attribute distribution if a valid subrace is provided
    starting_attrs = dict(_RACIAL_ATTRS.get(subrace or "", _DEFAULT_ATTRS))
    weight_capacity = get_weight_capacity(starting_attrs["strength"], starting_attrs["vitality"])
    currency = {
        "copper": 0,
        "silver": 5,
        "gold": 0,
        "platinum": 0,
    }
    # Seed racial skill bonuses
    racial_skills = dict(_RACIAL_SKILLS.get(subrace or "", {}))
    await conn.execute(
        """UPDATE players SET
           name = ?, race = ?, faction = ?, backstory = ?,
           inferred_class = ?, secret_objective = ?, max_hp = ?,
           current_hp = ?, attributes_json = ?,
           currency_json = ?, inventory_weight = ?, weight_capacity = ?,
           macros_json = ?, spell_aliases_json = ?, backstory_changed_recently = 0,
           subrace = ?,
           skills_json = ?,
           attribute_points_available = 0,
           proficiency_points_available = 0
           WHERE player_id = ?""",
        (
            name, race, faction, backstory,
            inferred_class, secret_objective, max_hp,
            max_hp, json.dumps(starting_attrs),
            json.dumps(currency), 0.0, weight_capacity, json.dumps([]), json.dumps({}),
            subrace,
            json.dumps(racial_skills),
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


async def maybe_advance_rooting(
    conn: aiosqlite.Connection, player_id: str, days_in_world: int
) -> int | None:
    """Advance rooting stage if the player has passed a threshold. Returns new stage or None."""
    new_stage: int | None = None
    for stage, threshold in reversed(list(enumerate(ROOTING_THRESHOLDS))):
        if days_in_world >= threshold:
            new_stage = stage
            break

    if new_stage is None:
        return None

    async with conn.execute(
        "SELECT rooting_stage FROM players WHERE player_id = ?", (player_id,)
    ) as cur:
        row = await cur.fetchone()

    if row is None or row["rooting_stage"] >= new_stage:
        return None

    await conn.execute(
        "UPDATE players SET rooting_stage = ? WHERE player_id = ?",
        (new_stage, player_id),
    )
    await conn.commit()
    return new_stage


async def apply_state_delta(
    conn: aiosqlite.Connection, player_id: str, delta: dict
) -> dict:
    """
    Apply the state delta returned by the GM atomically.
    delta may include: hp_change, attribute_changes, status, experience_gain,
                       learn_language, days_passed
    Returns a dict with event metadata (e.g. learned_language, rooting_advanced).
    """
    result: dict = {}

    async with conn.execute(
        """SELECT current_hp, max_hp, current_mp, max_mp,
                  current_stamina, max_stamina,
                  experience, level, status, attributes_json, milestones_json,
                  magic_prof_json, weapon_prof_json,
                  skills_json, attribute_points_available, proficiency_points_available,
                  inferred_class
           FROM players WHERE player_id = ?""",
        (player_id,),
    ) as cursor:
        row = await cursor.fetchone()

    if row is None:
        logger.warning("apply_state_delta: player %s not found", player_id)
        return {"milestones_unlocked": []}

    attributes = json.loads(row["attributes_json"] or "{}")
    milestones = json.loads(row["milestones_json"] or "[]")
    current_hp, current_mp, current_stamina, status = _apply_resource_changes(row, delta)
    experience, level, new_ap, new_pp = _apply_xp_and_attrs(row, delta, attributes)

    new_milestones = _check_passive_milestones(attributes, level, milestones)
    updated_milestones = milestones + new_milestones
    result["milestones_unlocked"] = new_milestones

    new_attr_pts = row["attribute_points_available"] + new_ap + int(delta.get("grant_attribute_points", 0))
    new_prof_pts = row["proficiency_points_available"] + new_pp + int(delta.get("grant_proficiency_points", 0))

    await conn.execute(
        """UPDATE players SET
           current_hp = ?, current_mp = ?, current_stamina = ?,
           experience = ?, level = ?, status = ?, attributes_json = ?,
           milestones_json = ?,
           attribute_points_available = ?,
           proficiency_points_available = ?
           WHERE player_id = ?""",
        (current_hp, current_mp, current_stamina,
         experience, level, status, json.dumps(attributes),
         json.dumps(updated_milestones),
         new_attr_pts, new_prof_pts,
         player_id),
    )
    await _apply_inventory_changes(conn, player_id, delta)
    await _apply_condition_changes(conn, player_id, delta)

    # Weapon / magic proficiency deltas (override: GM sets target rank directly)
    if "weapon_proficiency_delta" in delta:
        wpd = delta["weapon_proficiency_delta"]
        if isinstance(wpd, dict):
            async with conn.execute(
                "SELECT weapon_prof_json FROM players WHERE player_id = ?", (player_id,)
            ) as cur:
                prof_row = await cur.fetchone()
            if prof_row:
                wp = json.loads(prof_row["weapon_prof_json"] or "{}")
                for key, lvl in wpd.items():
                    wp[key] = max(1, min(20, int(lvl)))
                await conn.execute(
                    "UPDATE players SET weapon_prof_json = ? WHERE player_id = ?",
                    (json.dumps(wp), player_id),
                )
                result["weapon_prof_updated"] = list(wpd.keys())

    if "magic_proficiency_delta" in delta:
        mpd = delta["magic_proficiency_delta"]
        if isinstance(mpd, dict):
            async with conn.execute(
                "SELECT magic_prof_json FROM players WHERE player_id = ?", (player_id,)
            ) as cur:
                prof_row = await cur.fetchone()
            if prof_row:
                mp = json.loads(prof_row["magic_prof_json"] or "{}")
                for key, lvl in mpd.items():
                    mp[key] = max(1, min(20, int(lvl)))
                await conn.execute(
                    "UPDATE players SET magic_prof_json = ? WHERE player_id = ?",
                    (json.dumps(mp), player_id),
                )
                result["magic_prof_updated"] = list(mpd.keys())

    # Skill direct override (GM sets rank directly — rare/exceptional use)
    if "skill_delta" in delta:
        sd = delta["skill_delta"]
        if isinstance(sd, dict):
            ranked_up = await _apply_skill_delta(conn, player_id, sd)
            if ranked_up:
                result["skills_updated"] = ranked_up

    # Organic skill use recording (normal progression path)
    if "skill_use" in delta:
        su = delta["skill_use"]
        if isinstance(su, dict) and "skill_key" in su:
            inferred_class = row["inferred_class"] or ""
            ranked_up = await _apply_skill_use(
                conn, player_id, su["skill_key"], float(su.get("impact", 1.0)), inferred_class
            )
            if ranked_up:
                result["skill_rank_up"] = {"skill": su["skill_key"], "new_rank": ranked_up}

    if "craft_outcome" in delta:
        outcome = delta["craft_outcome"]
        if outcome.get("success") and outcome.get("item_id"):
            unique_item_id = f"{player_id}-crafted-{outcome['item_id']}-{int(time.time())}"
            await conn.execute(
                """INSERT INTO inventory
                   (item_id, player_id, name, description, rarity, quantity, equipped)
                   VALUES (?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(item_id) DO UPDATE SET
                     quantity = quantity + excluded.quantity""",
                (
                    unique_item_id,
                    player_id,
                    outcome.get("item_name", outcome["item_id"]),
                    outcome.get("description", "Crafted item"),
                    outcome.get("rarity", "common"),
                    int(outcome.get("quantity", 1)),
                    0,
                ),
            )
            result["crafted_item"] = outcome.get("item_name", outcome["item_id"])

    if "learn_language" in delta:
        lang = str(delta["learn_language"])
        async with conn.execute(
            "SELECT languages_json FROM players WHERE player_id = ?", (player_id,)
        ) as cur:
            lang_row = await cur.fetchone()
        if lang_row:
            languages = json.loads(lang_row["languages_json"] or '["common_tongue"]')
            if lang not in languages:
                languages.append(lang)
                await conn.execute(
                    "UPDATE players SET languages_json = ? WHERE player_id = ?",
                    (json.dumps(languages), player_id),
                )
            result["learned_language"] = lang

    if "days_passed" in delta:
        days = int(delta["days_passed"])
        await conn.execute(
            "UPDATE players SET days_in_world = days_in_world + ? WHERE player_id = ?",
            (days, player_id),
        )
        async with conn.execute(
            "SELECT days_in_world FROM players WHERE player_id = ?", (player_id,)
        ) as cur:
            days_row = await cur.fetchone()
        if days_row:
            new_stage = await maybe_advance_rooting(conn, player_id, days_row["days_in_world"])
            if new_stage is not None:
                result["rooting_advanced"] = new_stage

    _VALID_SEALS = frozenset({"common", "trade", "high_flame", "null_seal", "conclave"})

    if "grant_seal" in delta:
        seal = str(delta["grant_seal"])
        if seal in _VALID_SEALS:
            await conn.execute(
                "UPDATE players SET flame_seal = ? WHERE player_id = ?",
                (seal, player_id),
            )
            result["seal_granted"] = seal
        else:
            logger.warning("grant_seal: invalid seal type '%s'", seal)

    if "revoke_seal" in delta:
        await conn.execute(
            "UPDATE players SET flame_seal = NULL WHERE player_id = ?",
            (player_id,),
        )
        result["seal_revoked"] = True

    await conn.commit()
    return result


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


def _apply_xp_and_attrs(
    row: aiosqlite.Row, delta: dict, attributes: dict
) -> tuple[int, int, int, int]:
    """Calculate new XP/level, apply attribute changes in place.
    Returns (experience, new_level, ap_earned, pp_earned).
    AP: 5 per level-up. PP: 1 per level that is a multiple of 3.
    """
    experience = row["experience"] + int(delta.get("experience_gain", 0))
    old_level = row["level"]
    level = old_level
    while experience >= _xp_threshold(level):
        experience -= _xp_threshold(level)
        level += 1
    levels_gained = level - old_level
    ap_earned = levels_gained * 5
    pp_earned = sum(1 for lv in range(old_level + 1, level + 1) if lv % 3 == 0)
    for attr, val in delta.get("attribute_changes", {}).items():
        if attr in attributes:
            attributes[attr] = max(10, min(ATTRIBUTE_PER_CAP, attributes[attr] + int(val)))
    return experience, level, ap_earned, pp_earned


def _check_passive_milestones(
    attributes: dict, level: int, existing_milestones: list[str]
) -> list[str]:
    """Return newly unlocked passive milestone IDs based on attribute/level thresholds."""
    existing = set(existing_milestones)
    attr_thresholds = [
        ("strength",     20, "iron_physique"),
        ("intelligence", 20, "arcane_clarity"),
        ("vitality",     20, "unwavering_endurance"),
        ("dexterity",    20, "shadow_step"),
        ("charisma",     20, "voice_of_the_realm"),
        ("luck",         20, "fortune_favored"),
    ]
    new_milestones: list[str] = []
    for attr, threshold, milestone_id in attr_thresholds:
        if milestone_id not in existing and attributes.get(attr, 0) >= threshold:
            new_milestones.append(milestone_id)
    if "veteran" not in existing and level >= 10:
        new_milestones.append("veteran")
    if "legend" not in existing and level >= 25:
        new_milestones.append("legend")
    return new_milestones


async def _apply_skill_delta(
    conn: aiosqlite.Connection, player_id: str, skill_delta: dict[str, int]
) -> list[str]:
    """Direct GM override: set skill rank(s) for a player. Returns list of updated keys."""
    async with conn.execute(
        "SELECT skills_json FROM players WHERE player_id = ?", (player_id,)
    ) as cur:
        row = await cur.fetchone()
    if row is None:
        return []
    skills = json.loads(row["skills_json"] or "{}")
    updated = []
    for key, rank in skill_delta.items():
        rank = max(1, min(20, int(rank)))
        entry = skills.get(key, {"rank": 0, "uses": 0, "impact": 0.0})
        entry["rank"] = rank
        # Ensure impact is at least the threshold for the current rank
        entry["impact"] = max(float(entry.get("impact", 0.0)), _skill_impact_threshold(rank))
        skills[key] = entry
        updated.append(key)
    await conn.execute(
        "UPDATE players SET skills_json = ? WHERE player_id = ?",
        (json.dumps(skills), player_id),
    )
    return updated


async def _apply_skill_use(
    conn: aiosqlite.Connection,
    player_id: str,
    skill_key: str,
    impact: float,
    inferred_class: str,
) -> int | None:
    """Record a skill use and accumulate impact. Returns new rank if a rank-up occurred, else None."""
    async with conn.execute(
        "SELECT skills_json FROM players WHERE player_id = ?", (player_id,)
    ) as cur:
        row = await cur.fetchone()
    if row is None:
        return None
    skills = json.loads(row["skills_json"] or "{}")
    entry = skills.get(skill_key, {"rank": 0, "uses": 0, "impact": 0.0})

    # Apply class affinity multiplier
    category = _SKILL_TO_CATEGORY.get(skill_key)
    affinities = _CLASS_AFFINITIES.get(inferred_class, [])
    if category and category in affinities:
        impact *= 1.5

    entry["uses"] = int(entry.get("uses", 0)) + 1
    entry["impact"] = float(entry.get("impact", 0.0)) + impact

    # Auto rank-up loop
    old_rank = int(entry.get("rank", 0))
    current_rank = old_rank
    while current_rank < 20 and entry["impact"] >= _skill_impact_threshold(current_rank + 1):
        current_rank += 1
    entry["rank"] = current_rank
    skills[skill_key] = entry

    await conn.execute(
        "UPDATE players SET skills_json = ? WHERE player_id = ?",
        (json.dumps(skills), player_id),
    )
    return current_rank if current_rank > old_rank else None


async def spend_attribute_points(
    conn: aiosqlite.Connection, player_id: str, attribute: str, target_value: int
) -> dict:
    """Spend AP to raise an attribute to target_value. Returns {ok, spent, new_value} or error."""
    _VALID_ATTRS = frozenset({"strength", "dexterity", "intelligence", "vitality", "luck", "charisma"})
    if attribute not in _VALID_ATTRS:
        return {"ok": False, "reason": f"Unknown attribute '{attribute}'"}
    if target_value > ATTRIBUTE_PER_CAP:
        return {"ok": False, "reason": f"Target exceeds per-attribute cap of {ATTRIBUTE_PER_CAP}"}

    async with conn.execute(
        "SELECT attributes_json, attribute_points_available, milestones_json FROM players WHERE player_id = ?",
        (player_id,),
    ) as cur:
        row = await cur.fetchone()
    if row is None:
        return {"ok": False, "reason": "Player not found"}

    attrs = json.loads(row["attributes_json"] or "{}")
    current = int(attrs.get(attribute, 10))
    if target_value <= current:
        return {"ok": False, "reason": "Target must be greater than current value"}

    cost = target_value - current  # linear: 1 AP = +1
    available = int(row["attribute_points_available"])
    if available < cost:
        return {"ok": False, "reason": f"Not enough AP (need {cost}, have {available})"}

    attrs[attribute] = target_value
    new_available = available - cost
    milestones = json.loads(row["milestones_json"] or "[]")
    new_milestones = _check_passive_milestones(attrs, -1, milestones)  # -1: level not changing
    updated_milestones = milestones + new_milestones

    await conn.execute(
        """UPDATE players SET attributes_json = ?, attribute_points_available = ?,
           milestones_json = ? WHERE player_id = ?""",
        (json.dumps(attrs), new_available, json.dumps(updated_milestones), player_id),
    )
    await conn.commit()
    return {"ok": True, "spent": cost, "new_value": target_value, "ap_remaining": new_available,
            "milestones_unlocked": new_milestones}


async def spend_proficiency_points(
    conn: aiosqlite.Connection, player_id: str, prof_type: str, key: str, target_rank: int
) -> dict:
    """Spend PP to raise a weapon or magic proficiency to target_rank."""
    if prof_type not in ("weapon", "magic"):
        return {"ok": False, "reason": "prof_type must be 'weapon' or 'magic'"}
    if not 1 <= target_rank <= 20:
        return {"ok": False, "reason": "target_rank must be between 1 and 20"}

    col = "weapon_prof_json" if prof_type == "weapon" else "magic_prof_json"
    async with conn.execute(
        f"SELECT {col}, proficiency_points_available FROM players WHERE player_id = ?",
        (player_id,),
    ) as cur:
        row = await cur.fetchone()
    if row is None:
        return {"ok": False, "reason": "Player not found"}

    prof = json.loads(row[col] or "{}")
    current_rank = int(prof.get(key, 0))
    if target_rank <= current_rank:
        return {"ok": False, "reason": "Target rank must be greater than current rank"}

    cost = sum(_pp_cost(r) for r in range(current_rank, target_rank))
    available = int(row["proficiency_points_available"])
    if available < cost:
        return {"ok": False, "reason": f"Not enough PP (need {cost}, have {available})"}

    prof[key] = target_rank
    new_available = available - cost
    await conn.execute(
        f"UPDATE players SET {col} = ?, proficiency_points_available = ? WHERE player_id = ?",
        (json.dumps(prof), new_available, player_id),
    )
    await conn.commit()
    return {"ok": True, "spent": cost, "new_rank": target_rank, "pp_remaining": new_available}


async def apply_backstory_skills(
    conn: aiosqlite.Connection, player_id: str, skill_seeds: dict[str, int]
) -> None:
    """Apply backstory-derived skill seeds (rank 1-2 only, max 5 skills, max 8 impact total).
    These are pre-populating the skill map — they do not consume SP."""
    MAX_RANK = 2
    async with conn.execute(
        "SELECT skills_json FROM players WHERE player_id = ?", (player_id,)
    ) as cur:
        row = await cur.fetchone()
    if row is None:
        return
    skills = json.loads(row["skills_json"] or "{}")
    for key, rank in list(skill_seeds.items())[:5]:
        rank = max(1, min(MAX_RANK, int(rank)))
        entry = skills.get(key, {"rank": 0, "uses": 0, "impact": 0.0})
        # Only set if not already at a higher rank (don't overwrite racial bonuses)
        if entry.get("rank", 0) < rank:
            entry["rank"] = rank
            entry["uses"] = max(int(entry.get("uses", 0)), 8)
            entry["impact"] = max(float(entry.get("impact", 0.0)), _skill_impact_threshold(rank))
        skills[key] = entry
    await conn.execute(
        "UPDATE players SET skills_json = ? WHERE player_id = ?",
        (json.dumps(skills), player_id),
    )
    await conn.commit()


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
        "SELECT role, content, turn_number FROM history ORDER BY turn_number DESC, created_at DESC LIMIT ?",
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


# ---------------------------------------------------------------------------
# Admin helpers for Tier 1 routes
# ---------------------------------------------------------------------------

async def get_all_players(conn: aiosqlite.Connection) -> list[aiosqlite.Row]:
    """Retrieve all players with core profile fields."""
    async with conn.execute(
        "SELECT player_id, username, status, name, level, faction, created_at FROM players"
    ) as cursor:
        return await cursor.fetchall()


async def delete_byok_key(conn: aiosqlite.Connection, player_id: str) -> None:
    """Clear the BYOK API key for a player."""
    await conn.execute(
        "UPDATE players SET byok_key_encrypted = NULL WHERE player_id = ?",
        (player_id,),
    )
    await conn.commit()


async def get_all_invites(conn: aiosqlite.Connection) -> list[aiosqlite.Row]:
    """Retrieve all invite codes with metadata."""
    async with conn.execute(
        "SELECT code, created_by, created_at, used, used_by FROM invites"
    ) as cursor:
        return await cursor.fetchall()


# ---------------------------------------------------------------------------
# Session helpers for S-03: server-side token invalidation
# ---------------------------------------------------------------------------

async def create_session(
    conn: aiosqlite.Connection, player_id: str, token: str, expires_at: float | None = None
) -> None:
    """Create a session record when a player logs in."""
    import uuid
    import hashlib

    session_id = str(uuid.uuid4())
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    if expires_at is None:
        expires_at = time.time() + 60 * 60 * 24 * 180  # 6 months default
    await conn.execute(
        "INSERT INTO sessions (session_id, player_id, token_hash, expires_at, created_at) VALUES (?,?,?,?,?)",
        (session_id, player_id, token_hash, expires_at, time.time()),
    )
    await conn.commit()


async def get_session(conn: aiosqlite.Connection, player_id: str) -> aiosqlite.Row | None:
    """Get latest session for a player (any status)."""
    async with conn.execute(
        "SELECT * FROM sessions WHERE player_id = ? ORDER BY created_at DESC LIMIT 1",
        (player_id,),
    ) as c:
        return await c.fetchone()


async def get_active_session(conn: aiosqlite.Connection, player_id: str) -> aiosqlite.Row | None:
    """Get active (non-expired) session for a player."""
    async with conn.execute(
        "SELECT * FROM sessions WHERE player_id = ? AND expires_at > ? ORDER BY created_at DESC LIMIT 1",
        (player_id, time.time()),
    ) as c:
        return await c.fetchone()


async def revoke_sessions(conn: aiosqlite.Connection, player_id: str) -> None:
    """Revoke all sessions for a player by setting expires_at to now."""
    await conn.execute(
        "UPDATE sessions SET expires_at = ? WHERE player_id = ?",
        (time.time() - 1, player_id),
    )
    await conn.commit()


async def is_session_valid(conn: aiosqlite.Connection, player_id: str) -> bool:
    """Returns True if player has at least one active session."""
    row = await get_active_session(conn, player_id)
    return row is not None



