"""
context_builder.py - 4-layer context engineering.
Builds the full system prompt for the GM without touching the database directly.
Consumes data already loaded by state_manager and vector_store.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import aiosqlite

_TRUNCATED = "\n[truncated]"

from . import state_manager, travel_manager, vector_store
from .infrastructure.config.config_loader import load_campaign, load_world_kernel
from .models import ActionBatch, ContextLayers, LoreResult, MemoryLayers
from .time_manager import get_current_date

logger = logging.getLogger(__name__)

# Approximate token budget per layer (1 token ~= 4 chars in English)
_L0_CHAR_LIMIT = 1_000   # ~250 tokens (compact kernel)
_L1_CHAR_LIMIT = 800     # ~200 tokens
_L2_CHAR_LIMIT = 1_600   # ~400 tokens
_L3_CHAR_LIMIT = 6_000   # ~1500 tokens
_MEM_CHAR_LIMIT = 800    # ~200 tokens
_LORE_CHAR_LIMIT = 3_200 # ~800 tokens


async def build_context(
    conn: aiosqlite.Connection,
    batch: ActionBatch,
) -> ContextLayers:
    """
    Main entry point - builds all 4 layers.
    Called by game_master before each LLM request.
    """
    player_ids = [a.player_id for a in batch.actions]

    # Parallel data retrieval (all operations are independent)
    (
        players,
        history,
        memory,
        location_raw,
        cooperative_mission,
        current_date,
        travel_state,
    ) = await asyncio.gather(
        state_manager.get_all_alive_players(conn),
        state_manager.get_recent_history(conn, limit=10),
        state_manager.get_memory_layers(conn, player_ids),
        state_manager.get_world_state(conn, "current_location"),
        state_manager.get_cooperative_mission_state(conn),
        get_current_date(conn),
        travel_manager.get_travel_state(conn),
    )
    location = location_raw or "Isles of Myr"

    # Reputation + inventory for every player in parallel
    rep_results, inv_results = await asyncio.gather(
        asyncio.gather(*[state_manager.get_faction_reputation(conn, pid) for pid in player_ids]),
        asyncio.gather(*[state_manager.get_player_inventory(conn, pid) for pid in player_ids]),
    )
    reputations: dict[str, dict[str, int]] = dict(zip(player_ids, rep_results))
    inventories: dict[str, list] = dict(zip(player_ids, inv_results))

    # Enriched semantic retrieval: actions + location + factions
    action_text = " ".join(a.action_text for a in batch.actions)[:300]
    player_factions = " ".join({p["faction"] for p in players if p["faction"]})
    query = f"{action_text} {location} {player_factions}"
    lore = await vector_store.retrieve_lore(query, n_results=5)

    l0 = _build_l0_static()
    l1 = _build_l1_campaign()
    l2 = _build_l2_state(players, location, cooperative_mission, current_date, reputations, inventories, travel_state)
    l3 = _build_l3_history(history)
    mem = _build_memory_injection(memory)
    lore_text = _build_lore_text(lore)

    return ContextLayers(
        l0_static=l0,
        l1_campaign=l1,
        l2_state=l2,
        l3_history=l3,
        memory_injection=mem,
        lore_retrieval=lore_text,
    )


# ---------------------------------------------------------------------------
# Layer builders
# ---------------------------------------------------------------------------

def _build_l0_static() -> str:
    """L0: Compact world kernel. Details come from ChromaDB."""
    kernel = load_world_kernel()
    if len(kernel) > _L0_CHAR_LIMIT:
        kernel = kernel[:_L0_CHAR_LIMIT] + "\n[...truncated]"
    return kernel


def _build_l1_campaign() -> str:
    """L1: Current campaign configuration."""
    campaign = load_campaign()
    parts = [
        f"Campaign: {campaign.get('campaign', {}).get('name', 'Aerus')}",
        f"Tone: darkness level {campaign.get('tone', {}).get('darkness_level', 8)}/10",
        f"Difficulty: {campaign.get('difficulty', {}).get('base', 'brutal')}",
        f"Permadeath: {'yes' if campaign.get('difficulty', {}).get('permadeath', True) else 'no'}",
    ]
    return "\n".join(parts)


def _build_l2_state(
    players: list[aiosqlite.Row],
    location: str,
    cooperative_mission: dict[str, str],
    current_date: dict | None = None,
    reputations: dict[str, dict[str, int]] | None = None,
    inventories: dict[str, list] | None = None,
    travel_state: dict | None = None,
) -> str:
    """L2: Current player and world state."""
    date_str = current_date["description"] if current_date else "Unknown date"
    state_parts = [f"Current location: {location}", f"Date: {date_str}", "", "Players:"]

    for p in players:
        attrs = json.loads(p["attributes_json"] or "{}")
        magic_prof = json.loads(p["magic_prof_json"] or "{}")
        weapon_prof = json.loads(p["weapon_prof_json"] or "{}")
        magic_text = _format_proficiency(magic_prof)
        weapon_text = _format_proficiency(weapon_prof)
        inv_text = _format_inventory(inventories.get(p["player_id"], []) if inventories else [])
        state_parts.append(
            f"- {p['name']} ({p['race']}, {p['faction']}) | "
            f"Class: {p['inferred_class']} | "
            f"Level: {p['level']} | "
            f"HP: {p['current_hp']}/{p['max_hp']} | "
            f"STR:{attrs.get('strength',10)} DEX:{attrs.get('dexterity',10)} "
            f"INT:{attrs.get('intelligence',10)} VIT:{attrs.get('vitality',10)} "
            f"LUK:{attrs.get('luck',10)} CHA:{attrs.get('charisma',10)} | "
            f"Magic Prof.:{magic_text} | Weapon Prof.:{weapon_text} | "
            f"Inventory:[{inv_text}] | "
            f"SecretObjective:{(p['secret_objective'] or 'N/A')[:120]}"
        )

    mission_active = cooperative_mission.get("cooperative_mission_active", "0") == "1"
    mission_completed = cooperative_mission.get("cooperative_mission_completed", "0") == "1"
    mission_required = cooperative_mission.get("cooperative_mission_required_players", "0")
    mission_done = cooperative_mission.get("cooperative_mission_completed_players", "0")
    mission_objective = cooperative_mission.get(
        "cooperative_mission_objective",
        state_manager.COOP_MISSION_OBJECTIVE_DEFAULT,
    )
    state_parts.extend([
        "",
        f"Initial cooperative mission active: {'yes' if mission_active else 'no'}",
        f"Initial cooperative mission completed: {'yes' if mission_completed else 'no'}",
        f"Cooperative progress: {mission_done}/{mission_required}",
        f"Cooperative objective: {mission_objective}",
    ])

    rep_text = _format_reputations(reputations)
    if rep_text:
        state_parts.append(rep_text)

    if travel_state and travel_state.get("active"):
        state_parts.extend([
            "",
            f"[TRAVEL IN PROGRESS] {travel_state['origin_name']} -> {travel_state['destination_name']} | "
            f"Day {travel_state['day_current']}/{travel_state['day_total']} | "
            f"Terrain: {travel_state['terrain']} | "
            f"Days remaining: {travel_state['days_remaining']}",
        ])

    text = "\n".join(state_parts)
    if len(text) > _L2_CHAR_LIMIT:
        text = text[:_L2_CHAR_LIMIT] + _TRUNCATED
    return text


def _format_reputations(reputations: dict[str, dict[str, int]] | None) -> str:
    """Format all player reputations for the L2 context."""
    if not reputations:
        return ""
    lines = []
    for pid, faction_scores in reputations.items():
        non_neutral = {f: s for f, s in faction_scores.items() if s != 0}
        if non_neutral:
            summary = ", ".join(f"{f}:{s:+d}" for f, s in non_neutral.items())
            lines.append(f"  {pid[:8]}... -> {summary}")
    if not lines:
        return ""
    return "\nFaction reputation:\n" + "\n".join(lines)


def _format_inventory(items: list) -> str:
    """Format the player inventory as compact text for the L2 context."""
    if not items:
        return "empty"
    parts = []
    for item in items[:8]:  # cap at 8 items to keep context under control
        try:
            name = item["name"]
            qty = item["quantity"]
            parts.append(f"{name}x{qty}" if qty > 1 else name)
        except (KeyError, TypeError):
            continue
    if len(items) > 8:
        parts.append(f"+{len(items) - 8} others")
    return ", ".join(parts) if parts else "empty"


def _format_proficiency(values: dict[str, int]) -> str:
    if not values:
        return "-"
    ordered = sorted(values.items(), key=lambda item: item[0])
    return ",".join(f"{name}:{int(level)}" for name, level in ordered[:5])


def _build_l3_history(history: list[aiosqlite.Row]) -> str:
    """L3: Most recent history exchanges."""
    if not history:
        return "Start of the adventure."

    lines: list[str] = []
    for row in history:
        role = "Players" if row["role"] == "user" else "GM"
        lines.append(f"[{role}]: {row['content']}")

    text = "\n".join(lines)
    if len(text) > _L3_CHAR_LIMIT:
        text = text[-_L3_CHAR_LIMIT:]
    return text


def _build_memory_injection(memory: MemoryLayers) -> str:
    """Compressed memory layer."""
    parts: list[str] = []
    if memory.character:
        parts.append(f"Character memory:\n{memory.character}")
    if memory.world:
        parts.append(f"World changes:\n{memory.world}")
    if memory.arc:
        parts.append(f"Narrative arc:\n{memory.arc}")

    if not parts:
        return "No prior memory."

    text = "\n\n".join(parts)
    if len(text) > _MEM_CHAR_LIMIT:
        text = text[:_MEM_CHAR_LIMIT] + _TRUNCATED
    return text


def _build_lore_text(lore: LoreResult) -> str:
    """Format ChromaDB results for context injection."""
    if not lore.documents:
        return "No scene-specific lore found."

    parts: list[str] = []
    for doc, meta in zip(lore.documents, lore.metadatas):
        name = meta.get("name", "Unknown")
        doc_truncated = doc[:600] if len(doc) > 600 else doc
        parts.append(f"### {name}\n{doc_truncated}")

    text = "\n\n".join(parts)
    if len(text) > _LORE_CHAR_LIMIT:
        text = text[:_LORE_CHAR_LIMIT] + _TRUNCATED
    return text


# ---------------------------------------------------------------------------
# Full system prompt for the GM
# ---------------------------------------------------------------------------

GM_SYSTEM_PROMPT_TEMPLATE = """You are the Game Master (GM) of Aerus RPG - a dark fantasy RPG for {num_players} player(s).

ABSOLUTE RULES:
1. Always respond in English, using the specified literary tone.
2. Be cinematic, visceral, and consequential. Death carries real weight.
3. Never ignore player actions - every action must have a consequence.
4. Return structured JSON after the narrative.
5. Current tension: {tension_level}/10 - scale danger and epic weight accordingly.
6. ALL players begin together in the Islands of Myr. Maintain geographic consistency for that shared starting point.
7. While the initial cooperative mission is active, progression is BLOCKED: all living players must cooperate and participate. If any player tries to leave the Islands of Myr before completing it, stop the departure narratively with a concrete obstacle.
8. Balance EVERY encounter around the number of players present (current party size: {num_players}).
9. Suggested non-boss encounter scale: multiplier {encounter_scale}.
10. Boss exception: base difficulty plus one phase step for every 2 additional players (current boss step bonus: +{boss_scale_steps}).
11. POWER PROGRESSION: At every multiple of 5 levels, ALWAYS emit `ABILITY_UNLOCK`. At every 25 levels, emit BOTH `ABILITY_UNLOCK` and `CLASS_MUTATION`, in that order.
12. FACTION REPUTATION: Use only valid IDs: `church_pure_flame`, `empire_valdrek`, `guild_of_threads`, `children_of_broken_thread`, `myr_council`. If an action helps one faction and harms another, include both deltas.
13. ITEMS AND INVENTORY: Never grant the effect of an item that is not present in the contextual inventory. If an absent item is used, the narrative must explicitly state that the character searched and failed to find it.
14. OUTCOME DISPUTES: Never retroactively change dice results or already narrated damage.
15. PER-PLAYER DELTA: In multiplayer sessions, each player must have an individual `state_delta` entry.

FINAL CHECKLIST:
- The JSON inside `<game_state>` is valid and parseable.
- If the level is a multiple of 25, `game_events` includes both `ABILITY_UNLOCK` and `CLASS_MUTATION`.
- If a missing item is used, the narrative explicitly states the item was not found and `hp_change` is not positive.
- If one faction benefits and another is harmed, `reputation_delta` includes both entries.

RESPONSE FORMAT:
Free-form prose narrative, followed by:

<game_state>
{{
  "dice_rolls": [
    {{"player": "name", "die": 20, "purpose": "sword attack", "result": 18}}
  ],
  "state_delta": {{
    "player_id": {{
      "hp_change": -15,
      "mp_change": -10,
      "stamina_change": -20,
      "experience_gain": 50,
      "inventory_add": [
        {{"item_id": "uuid", "name": "Item Name", "description": "Item description.", "rarity": "rare", "quantity": 1, "equipped": false}}
      ],
      "inventory_remove": [],
      "conditions_add": [
        {{"condition_id": "uuid", "name": "Poisoned", "description": "Loses 5 HP per turn.", "duration_turns": 3, "applied_at_turn": {turn_number}, "is_buff": false}}
      ],
      "conditions_remove": []
    }}
  }},
  "game_events": [
    {{"type": "LOOT", "player_id": "id", "player_name": "name", "items": [
      {{"item_id": "uuid", "name": "Ash Sword", "description": "Forged in the ruins.", "rarity": "epic", "quantity": 1, "equipped": false}}
    ]}},
    {{"type": "LEVELUP", "player_id": "id", "player_name": "name", "new_level": 5}},
    {{"type": "ABILITY_UNLOCK", "player_id": "id", "player_name": "name", "ability_name": "Ability Name", "ability_description": "Organic description."}},
    {{"type": "CLASS_MUTATION", "player_id": "id", "player_name": "name", "new_class": "Ash Warden", "old_class": "Warrior"}},
    {{"type": "DEATH", "player_id": "id", "player_name": "name", "cause": "fatal blow from the Golem"}}
  ],
  "tension_level": 6,
  "audio_cue": "combat_intense",
  "next_scene_query": "short description for lore retrieval"
}}
</game_state>"""


def build_gm_system_prompt(
    num_players: int,
    tension_level: int,
    turn_number: int = 0,
    encounter_scale: float = 1.0,
    boss_scale_steps: int = 0,
) -> str:
    return GM_SYSTEM_PROMPT_TEMPLATE.format(
        num_players=num_players,
        tension_level=tension_level,
        turn_number=turn_number,
        encounter_scale=encounter_scale,
        boss_scale_steps=boss_scale_steps,
    )
