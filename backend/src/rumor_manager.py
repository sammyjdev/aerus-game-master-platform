"""
rumor_manager.py — Asymmetric rumor injection for the GM context.

Each player hears a faction-biased version of the same underlying event,
creating information asymmetry within the party and forcing social negotiation.

Rumors are injected into L2 context once per rumor_id per player (idempotent).
New rumors surface as world tension rises above the rumor's tension_min threshold.
"""
from __future__ import annotations

import logging
import random
from pathlib import Path

import yaml

from . import state_manager

logger = logging.getLogger(__name__)

_RUMORS_PATH = Path(__file__).parent.parent / "config" / "rumors.yaml"
_rumors_cache: list[dict] | None = None

# Faction → rumor variant key mapping
# Players without a known faction fall back to "neutral"
_FACTION_VARIANT_MAP: dict[str, str] = {
    "church_pure_flame": "church_pure_flame",
    "empire_valdrek": "empire_valdrek",
    "guild_of_threads": "guild_of_threads",
    "children_of_broken_thread": "children_of_broken_thread",
    "myr_council": "myr_council",
}


def _load_rumors() -> list[dict]:
    global _rumors_cache
    if _rumors_cache is None:
        data = yaml.safe_load(_RUMORS_PATH.read_text(encoding="utf-8"))
        _rumors_cache = data.get("rumors", [])
    return _rumors_cache


def _variant_key(faction: str | None) -> str:
    if not faction:
        return "neutral"
    return _FACTION_VARIANT_MAP.get(faction.lower().replace(" ", "_"), "neutral")


def get_rumor_text(rumor_id: str, faction: str | None) -> str | None:
    """Return the faction-biased variant of a rumor, or None if not found."""
    rumors = _load_rumors()
    key = _variant_key(faction)
    for rumor in rumors:
        if rumor["rumor_id"] == rumor_id:
            variants = rumor.get("variants", {})
            return variants.get(key) or variants.get("neutral")
    return None


async def get_active_rumors_for_player(
    conn,
    player_id: str,
    faction: str | None,
    tension_level: int,
    limit: int = 2,
) -> list[str]:
    """Return faction-biased rumor texts that the player hasn't heard yet.

    Eligibility: rumor.tension_min <= tension_level AND not yet seen by player.
    Marks seen rumors via quest_flags to avoid repetition.
    """
    rumors = _load_rumors()
    eligible = [
        r for r in rumors
        if r.get("tension_min", 0) <= tension_level
    ]

    # Shuffle for variety across sessions
    random.shuffle(eligible)

    result: list[str] = []
    for rumor in eligible:
        if len(result) >= limit:
            break

        rumor_id = rumor["rumor_id"]
        flag_key = f"rumor_heard:{rumor_id}:{player_id}"
        already_heard = await state_manager.get_quest_flag(conn, flag_key)
        if already_heard == "1":
            continue

        variant_text = get_rumor_text(rumor_id, faction)
        if not variant_text:
            continue

        await state_manager.set_quest_flag(conn, flag_key, "1")
        result.append(variant_text.strip())
        logger.debug("Rumor %s delivered to player %s (faction=%s)", rumor_id, player_id, faction)

    return result


def format_rumors_for_context(rumors: list[str], player_name: str) -> str:
    """Format rumors as a compact context block for the GM prompt."""
    if not rumors:
        return ""
    lines = [f"[Rumors heard by {player_name}]"]
    for i, rumor in enumerate(rumors, 1):
        # Truncate each rumor for context budget
        truncated = rumor[:300] if len(rumor) > 300 else rumor
        lines.append(f"{i}. {truncated}")
    return "\n".join(lines)
