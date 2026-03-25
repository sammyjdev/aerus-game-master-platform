"""
behavior_trajectory.py — Derives a player's dominant behavioral pattern
from their episodic memory and uses it to select class mutation paths.

Called at level 25/50/75/100 milestones to make mutations feel earned
rather than predetermined. Two Blades who play differently reach different
mutations at the same level.
"""
from __future__ import annotations

import logging

import aiosqlite

from . import state_manager

logger = logging.getLogger(__name__)

# Action categories tracked in player_episodes
_ACTION_CATEGORIES = ("combat_action", "stealth_action", "social_action", "explore_action")

# Mutation table: base_class_keyword → {dominant_behavior → mutation_name}
# Keys are lowercased substrings of the inferred_class.
# "default" is used when behavior is mixed or below threshold.
_TRAJECTORY_MUTATIONS: dict[str, dict[str, str]] = {
    "blade": {
        "combat_action": "Iron Requiem",
        "stealth_action": "Ghostblade",
        "social_action": "Warleader",
        "explore_action": "Ruin Walker",
        "default": "Ascended Blade",
    },
    "sorcerer": {
        "combat_action": "Spellblade",
        "stealth_action": "Shadow Weaver",
        "social_action": "Silver Tongue",
        "explore_action": "Lore Seeker",
        "default": "Thread Archmage",
    },
    "sharpshooter": {
        "combat_action": "Death Caller",
        "stealth_action": "Phantom Arrow",
        "social_action": "Hunter of Men",
        "explore_action": "Horizon Warden",
        "default": "Ascended Sharpshooter",
    },
    "shadow": {
        "combat_action": "Knife of the Sealing",
        "stealth_action": "Living Void",
        "social_action": "Web Spinner",
        "explore_action": "Null Walker",
        "default": "Ascended Shadow",
    },
    "herald": {
        "combat_action": "Voice of War",
        "stealth_action": "Whisper Agent",
        "social_action": "Iron Herald",
        "explore_action": "Faction Prophet",
        "default": "Ascended Herald",
    },
    "sentinel": {
        "combat_action": "Last Wall",
        "stealth_action": "Hollow Fortress",
        "social_action": "Shield of the People",
        "explore_action": "Wandering Bastion",
        "default": "Ascended Sentinel",
    },
    "channeler": {
        "combat_action": "Conduit of Ruin",
        "stealth_action": "Silent Channel",
        "social_action": "Living Resonance",
        "explore_action": "Thread Drifter",
        "default": "Primordial Weaver",
    },
    "wanderer": {
        "combat_action": "Scarbringer",
        "stealth_action": "Ghost Road",
        "social_action": "Connector",
        "explore_action": "World Memory",
        "default": "Ascended Wanderer",
    },
    # Legacy / inferred class names from existing mapping
    "mage": {
        "combat_action": "Spellblade",
        "stealth_action": "Shadow Weaver",
        "social_action": "Silver Tongue",
        "explore_action": "Lore Seeker",
        "default": "Thread Archmage",
    },
    "warrior": {
        "combat_action": "Iron Requiem",
        "stealth_action": "Ghostblade",
        "social_action": "Warleader",
        "explore_action": "Ruin Walker",
        "default": "Steel Warden",
    },
    "rogue": {
        "combat_action": "Knife of the Sealing",
        "stealth_action": "Living Void",
        "social_action": "Web Spinner",
        "explore_action": "Null Walker",
        "default": "Vector Shade",
    },
    "ranger": {
        "combat_action": "Death Caller",
        "stealth_action": "Phantom Arrow",
        "social_action": "Hunter of Men",
        "explore_action": "Horizon Warden",
        "default": "Ruin Hunter",
    },
}

_DOMINANCE_THRESHOLD = 0.40  # behavior must represent ≥40% of total episodes to be "dominant"


async def get_mutation_name(
    conn: aiosqlite.Connection,
    player_id: str,
    old_class: str,
) -> str:
    """Return the mutation name for a player based on their behavioral trajectory.

    Falls back to generic "Ascended <class>" if no strong pattern is found.
    """
    counts = await state_manager.get_player_episode_counts_by_type(conn, player_id)
    dominant = _derive_dominant_behavior(counts)

    class_key = _match_class_key(old_class)
    if not class_key:
        logger.debug(
            "No mutation table for class '%s' (player %s) — using Ascended fallback",
            old_class,
            player_id,
        )
        return f"Ascended {old_class}"

    table = _TRAJECTORY_MUTATIONS[class_key]
    mutation_name = table.get(dominant, table["default"]) if dominant else table["default"]

    logger.info(
        "Mutation selected: player=%s class=%s dominant=%s -> %s",
        player_id,
        old_class,
        dominant,
        mutation_name,
    )
    return mutation_name


def _derive_dominant_behavior(counts: dict[str, int]) -> str | None:
    """Return the dominant action category, or None if no single category dominates."""
    total = sum(counts.get(cat, 0) for cat in _ACTION_CATEGORIES)
    if total == 0:
        return None

    best_cat = max(_ACTION_CATEGORIES, key=lambda c: counts.get(c, 0))
    best_share = counts.get(best_cat, 0) / total

    if best_share >= _DOMINANCE_THRESHOLD:
        return best_cat
    return None


def _match_class_key(inferred_class: str) -> str | None:
    """Match the player's inferred class to a key in _TRAJECTORY_MUTATIONS."""
    lowered = inferred_class.lower()
    for key in _TRAJECTORY_MUTATIONS:
        if key in lowered:
            return key
    return None
