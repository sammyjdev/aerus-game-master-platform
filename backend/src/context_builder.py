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

from . import rumor_manager, state_manager, travel_manager, vector_store
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

LANGUAGE_DISPLAY_NAMES: dict[str, str] = {
    "common_tongue": "Common Tongue",
    "valdrekian": "Valdrekian",
    "myr_pidgin": "Myr Pidgin",
    "old_aerus": "Old Aerus",
    "the_hum": "The Hum (instinct, non-verbal)",
    "glyph_script": "Glyph Script (written only)",
    "deep_tongue": "Deep Tongue",
    "ash_cant": "Ash Cant (slang/cipher)",
}

_ROOTING_STAGE_NAMES: dict[int, str] = {
    0: "Unrooted",
    1: "Anchored — 365+ days in Aerus",
    2: "Resonant — 730+ days in Aerus",
    3: "Merged — 1095+ days in Aerus",
    4: "Sovereign — 1825+ days in Aerus",
}


async def build_context(
    conn: aiosqlite.Connection,
    batch: ActionBatch,
    tension_level: int = 5,
) -> ContextLayers:
    """
    Main entry point - builds all 4 layers.
    Called by game_master before each LLM request.

    tension_level drives narrative tone (L1) and world state indicators (L2)
    beyond just LLM model selection.
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

    # Build faction map from already-fetched players (no extra DB call)
    player_factions_by_id = {p["player_id"]: p["faction"] for p in players}

    # Reputation, inventory, episodes, and rumors for every player in parallel
    rep_results, inv_results, ep_results, rumor_results = await asyncio.gather(
        asyncio.gather(*[state_manager.get_faction_reputation(conn, pid) for pid in player_ids]),
        asyncio.gather(*[state_manager.get_player_inventory(conn, pid) for pid in player_ids]),
        asyncio.gather(*[state_manager.get_player_episodes(conn, pid, limit=5, min_importance=2) for pid in player_ids]),
        asyncio.gather(*[
            rumor_manager.get_active_rumors_for_player(
                conn, pid, player_factions_by_id.get(pid), tension_level
            )
            for pid in player_ids
        ]),
    )
    reputations: dict[str, dict[str, int]] = dict(zip(player_ids, rep_results))
    inventories: dict[str, list] = dict(zip(player_ids, inv_results))
    episodes: dict[str, list] = dict(zip(player_ids, ep_results))
    player_rumors: dict[str, list[str]] = dict(zip(player_ids, rumor_results))

    # Enriched semantic retrieval: actions + location + factions
    action_text = " ".join(a.action_text for a in batch.actions)[:300]
    player_factions = " ".join({p["faction"] for p in players if p["faction"]})
    query = f"{action_text} {location} {player_factions}"
    lore = await vector_store.retrieve_lore(query, n_results=5)

    l0 = _build_l0_static()
    l1 = _build_l1_campaign(tension_level)
    l2 = _build_l2_state(players, location, cooperative_mission, current_date, reputations, inventories, travel_state, tension_level, episodes, player_rumors)
    l3 = _build_l3_history(history)
    mem = _build_memory_injection(memory)
    lore_text = _build_lore_text(lore)

    from .recipe_manager import get_recipes_context
    crafting_ctx = get_recipes_context()
    if crafting_ctx:
        lore_text = (lore_text + "\n\n" + crafting_ctx).strip()

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


_TENSION_DIRECTIVES: dict[tuple[int, int], str] = {
    (1, 3): (
        "Exploration mode. Focus on discovery, NPC bonds, and world-building. "
        "Faction aggression is low. Encounters are rare and mostly social or environmental. "
        "Let the world breathe."
    ),
    (4, 6): (
        "Rising conflict. Threats exist but are manageable. "
        "Factions are watchful; NPCs choose sides carefully. "
        "Encounters are meaningful and carry consequences."
    ),
    (7, 8): (
        "Active conflict. Violence is imminent. Faction lines are drawn; NPC trust is fragile. "
        "Every scene should carry the weight of what has already been lost. "
        "Danger is present even in safe locations."
    ),
    (9, 10): (
        "Crisis. The world is at a breaking point. Every faction is mobilizing. "
        "Death is a real possibility each turn. "
        "Horror should be present in routine things. Restraint costs more than action."
    ),
}


def _get_tension_directive(tension_level: int) -> str:
    for (low, high), directive in _TENSION_DIRECTIVES.items():
        if low <= tension_level <= high:
            return directive
    return _TENSION_DIRECTIVES[(4, 6)]


def _build_l1_campaign(tension_level: int = 5) -> str:
    """L1: Current campaign configuration with tension-driven narrative directive."""
    campaign = load_campaign()
    parts = [
        f"Campaign: {campaign.get('campaign', {}).get('name', 'Aerus')}",
        f"Tone: darkness level {campaign.get('tone', {}).get('darkness_level', 8)}/10",
        f"Difficulty: {campaign.get('difficulty', {}).get('base', 'brutal')}",
        f"Permadeath: {'yes' if campaign.get('difficulty', {}).get('permadeath', True) else 'no'}",
        f"Current tension: {tension_level}/10",
        f"Narrative directive: {_get_tension_directive(tension_level)}",
    ]
    return "\n".join(parts)


_TENSION_WORLD_STATE: dict[tuple[int, int], str] = {
    (1, 3): "Faction activity: dormant. Streets are calm. Institutional surveillance is routine.",
    (4, 6): "Faction activity: watchful. Patrols are increased. Rumors are circulating.",
    (7, 8): "Faction activity: mobilized. Public spaces are tense. Checkpoints and informants are active.",
    (9, 10): "Faction activity: crisis footing. Open conflict is possible. Civilians are withdrawing. Nothing is safe.",
}


def _get_tension_world_state(tension_level: int) -> str:
    for (low, high), state in _TENSION_WORLD_STATE.items():
        if low <= tension_level <= high:
            return state
    return _TENSION_WORLD_STATE[(4, 6)]


def _build_l2_state(
    players: list[aiosqlite.Row],
    location: str,
    cooperative_mission: dict[str, str],
    current_date: dict | None = None,
    reputations: dict[str, dict[str, int]] | None = None,
    inventories: dict[str, list] | None = None,
    travel_state: dict | None = None,
    tension_level: int = 5,
    episodes: dict[str, list] | None = None,
    player_rumors: dict[str, list[str]] | None = None,
) -> str:
    """L2: Current player and world state with tension-driven faction/world indicators."""
    date_str = current_date["description"] if current_date else "Unknown date"
    state_parts = [
        f"Current location: {location}",
        f"Date: {date_str}",
        f"World state: {_get_tension_world_state(tension_level)}",
        "",
        "Players:",
    ]

    for p in players:
        attrs = json.loads(p["attributes_json"] or "{}")
        magic_prof = json.loads(p["magic_prof_json"] or "{}")
        weapon_prof = json.loads(p["weapon_prof_json"] or "{}")
        skills_raw = json.loads(p["skills_json"] or "{}")
        magic_text = _format_proficiency(magic_prof)
        weapon_text = _format_proficiency(weapon_prof)
        skills_text = _format_skills(skills_raw)
        inv_text = _format_inventory(inventories.get(p["player_id"], []) if inventories else [])
        ep_text = _format_episodes(episodes.get(p["player_id"], []) if episodes else [])
        ep_suffix = f" | KeyMemory:[{ep_text}]" if ep_text else ""
        state_parts.append(
            f"- {p['name']} ({p['race']}, {p['faction']}) | "
            f"PlayerID:{p['player_id']} | "
            f"Class: {p['inferred_class']} | "
            f"Level: {p['level']} | "
            f"HP: {p['current_hp']}/{p['max_hp']} | "
            f"STR:{attrs.get('strength',10)} DEX:{attrs.get('dexterity',10)} "
            f"INT:{attrs.get('intelligence',10)} VIT:{attrs.get('vitality',10)} "
            f"LUK:{attrs.get('luck',10)} CHA:{attrs.get('charisma',10)} | "
            f"Languages:{_format_languages(p['languages_json'])} | "
            f"Wallet:{_format_currency_wallet(p['currency_json'])} | "
            f"Magic Prof.:{magic_text} | Weapon Prof.:{weapon_text} | "
            f"Skills:{skills_text} | "
            f"Inventory:[{inv_text}] | "
            f"SecretObjective:{(p['secret_objective'] or 'N/A')[:120]}"
            f"{ep_suffix}"
        )

        # Inject faction-biased rumors this player hasn't heard yet
        rumors = player_rumors.get(p["player_id"], []) if player_rumors else []
        if rumors:
            rumor_block = rumor_manager.format_rumors_for_context(rumors, p["name"] or "Player")
            state_parts.append(rumor_block)

        # Isekai rooting status
        race_lower = (p["race"] or "").lower()
        if "isekai" in race_lower or "summoned" in race_lower:
            try:
                rooting_stage = p["rooting_stage"]
                days_in_world = p["days_in_world"]
            except (IndexError, KeyError):
                rooting_stage = 0
                days_in_world = 0
            stage_label = _ROOTING_STAGE_NAMES.get(rooting_stage, f"Stage {rooting_stage}")
            state_parts.append(
                f"  [Isekai] Rooting stage: {rooting_stage} ({stage_label}, {days_in_world} days in Aerus)"
            )

        # Flame Seal status
        try:
            seal = p["flame_seal"]
        except (IndexError, KeyError):
            seal = None
        _SEAL_DISPLAY = {
            "common": "Common Seal (low-tier elemental use authorized)",
            "trade": "Trade Seal (professional licensed use)",
            "high_flame": "High Flame Seal (advanced magic authorized)",
            "null_seal": "NULL SEAL — magic is suppressed by Church authority",
            "conclave": "Conclave Authorization (unrestricted Guild-internal status)",
        }
        if seal:
            state_parts.append(f"  Flame Seal: {_SEAL_DISPLAY.get(seal, seal)}")
        else:
            state_parts.append("  Flame Seal: None (unlicensed magic user)")

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


def _format_languages(raw_languages: Any) -> str:
    if not raw_languages:
        return "Common Tongue"
    try:
        parsed = json.loads(raw_languages) if isinstance(raw_languages, str) else raw_languages
    except (TypeError, ValueError):
        parsed = []
    if not isinstance(parsed, list):
        return "Common Tongue"
    values = [
        LANGUAGE_DISPLAY_NAMES.get(str(item).strip(), str(item).strip())
        for item in parsed if str(item).strip()
    ]
    return ", ".join(values) if values else "Common Tongue"


def _format_currency_wallet(raw_wallet: Any) -> str:
    try:
        parsed = json.loads(raw_wallet) if isinstance(raw_wallet, str) else raw_wallet
    except (TypeError, ValueError):
        parsed = {}
    if not isinstance(parsed, dict):
        parsed = {}
    return (
        f"cp:{int(parsed.get('copper', 0) or 0)} "
        f"sp:{int(parsed.get('silver', 0) or 0)} "
        f"gp:{int(parsed.get('gold', 0) or 0)} "
        f"pp:{int(parsed.get('platinum', 0) or 0)}"
    )


def _format_episodes(episodes: list) -> str:
    """Format the top episodic memories as compact context for the GM."""
    if not episodes:
        return ""
    parts = []
    for ep in episodes[:4]:  # cap at 4 to stay within L2 budget
        desc = ep.get("description", "")[:80]
        parts.append(desc)
    return " | ".join(parts)


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


def _format_skills(skills: dict) -> str:
    """Format top-6 skills by rank for L2 injection. skills_json structure:
    {skill_key: {rank, uses, impact}} or {skill_key: int} (legacy rank-only)."""
    if not skills:
        return "-"
    ranked = []
    for key, val in skills.items():
        rank = val.get("rank", val) if isinstance(val, dict) else int(val)
        if rank > 0:
            ranked.append((key, int(rank)))
    ranked.sort(key=lambda x: -x[1])
    return ",".join(f"{k}:{r}" for k, r in ranked[:6]) or "-"


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
1. Always respond in {language_name}, using the specified literary tone.
2. Be cinematic, visceral, and consequential. Death carries real weight.
3. Never ignore player actions - every action must have a consequence.
4. Return structured JSON after the narrative.
5. Current tension: {tension_level}/10 - scale danger and epic weight accordingly.
6. ALL players begin together in the Islands of Myr. Maintain geographic consistency for that shared starting point.
7. While the initial cooperative mission is active, progression is BLOCKED: all living players must cooperate and participate. If any player tries to leave the Islands of Myr before completing it, stop the departure narratively with a concrete obstacle such as a harbor refusal, checkpoint, storm wall, sealed route, or mission pressure.
8. Balance EVERY encounter around the number of players present (current party size: {num_players}).
9. Suggested non-boss encounter scale: multiplier {encounter_scale}.
10. Boss exception: base difficulty plus one phase step for every 2 additional players (current boss step bonus: +{boss_scale_steps}).
11. POWER PROGRESSION: At every multiple of 5 levels, ALWAYS emit `ABILITY_UNLOCK`. At every 25 levels, emit BOTH `ABILITY_UNLOCK` and `CLASS_MUTATION`, in that order.
12. FACTION REPUTATION: Use only valid IDs: `church_pure_flame`, `empire_valdrek`, `guild_of_threads`, `children_of_broken_thread`, `myr_council`. If an action helps one faction and harms another, include both deltas.
13. ITEMS AND INVENTORY: Never grant the effect of an item that is not present in the contextual inventory. If an absent item is used, the narrative must explicitly state that the character searched and failed to find it.
14. OUTCOME DISPUTES: Never retroactively change dice results or already narrated damage.
15. PER-PLAYER DELTA: In multiplayer sessions, each player must have an individual `state_delta` entry.
16. PLAYER IDS: Use the exact runtime player IDs listed below. Never use placeholders such as `player_id`, `id`, `uuid`, `name`, or invented IDs.
17. OUTPUT DISCIPLINE: Keep the narrative compact. Never use markdown headings, numbered lists, bullet lists, or code fences.
18. LENGTH PRIORITY: If space is tight, shorten the narrative first. Never omit or truncate the `game_state` block.
19. NARRATIVE CAP: Use at most two short paragraphs and no more than 130 words unless the scene absolutely requires more.
20. EVENT DISCIPLINE: Only emit `LOOT`, `LEVELUP`, `ABILITY_UNLOCK`, `CLASS_MUTATION`, or `DEATH` when the scene directly earns them. Social aid, aftermath, celebration, travel, and lore scenes should not invent combat loot or progression spikes.
21. REPUTATION CAUSALITY: If the player visibly protects, aids, or publicly supports a faction member or institution, include an explicit `reputation_delta` with the correct faction ID inside that player's `state_delta`.
22. CELEBRATION AND AFTERMATH: If the scene is post-objective relief or celebration, keep tension between 2 and 4 and give the narrative emotional payoff with explicit relief, earned quiet, shared victory, gratitude, rest, or sober togetherness. Name that payoff directly instead of only implying it.
23. DESPERATE ESCAPE: If the scene begins near death, under pursuit, or in a desperate retreat, tension must stay at 7 or higher until clear safety is reached. Use urgency words like desperate, blood, panic, crushing, breathless, or terror.
24. COMBAT CAUSALITY: If a hostile strike lands, a dangerous creature connects, or a heavy action backfires, at least one affected player should usually have negative `hp_change` unless the narrative clearly explains a miss, block, or harmless glancing blow.
25. HEALING VISIBILITY: If any player has positive `hp_change`, the narrative must explicitly describe visible healing, relief, warmth, closed wounds, restored breath, or pain easing.
26. PROGRESSION SIGNALING: When `ABILITY_UNLOCK`, `LEVELUP`, or `CLASS_MUTATION` is emitted, the narrative should also mention awakening, growth, a new technique, or transformation in natural language.
27. LOOT SIGNALING: When meaningful loot is earned, name the reward in the narrative and emit a `LOOT` event with at least one concrete item. Rare victories should not default to common loot.
28. CREATIVE SPECIFICITY: Avoid generic fantasy phrasing. Use at least one concrete sensory detail and one Aerus-specific proper noun when the scene depends on lore, place, faction, or aftermath.
29. ONBOARDING GROUNDING: In Isles of Myr onboarding or dockside scenes, explicitly name Port Myr, the harbor, the docks, or the quay so the player is clearly grounded in place.
30. EXPLICIT DENIAL WORDING: For blocked departures or missing items, use unmistakable wording such as `halt`, `no departures without clearance`, `refused passage`, `cannot find`, `finds no potion`, or `it is not there`.
31. HEALING WORDING: When healing succeeds, explicitly mention wounds knitting closed, warmth flooding the body, pain receding, breath steadying, or strength returning.
32. BREAKTHROUGH PAYOFF: If the action clearly describes a breakthrough, boss finish, limit break, or claimed reward, emit the earned progression or loot signal instead of only narrating mood.
33. ACTIVE COMBAT COST: In an unresolved combat exchange against a living threat, include immediate pressure on the player side as well, usually through negative `hp_change` or at minimum clear stamina loss plus explicit danger of the next hit.
34. CONSUMABLE ACCOUNTING: If a potion, antidote, salve, bomb, or similar consumable is used, it must appear in `inventory_remove` for the user.
35. ITEM TRANSFER ACCOUNTING: In multiplayer item sharing, the giver loses the item in `inventory_remove`, and the receiver either gains it in `inventory_add` or immediately benefits from it in their own `state_delta`.
36. FATAL BLOWS: If a nearly dead player is struck by a final blow or clearly dies in the scene, emit a `DEATH` event or an unmistakably fatal state.
37. LEVEL THRESHOLD DISCIPLINE: On level 5/10/15/20/... awakening scenes, always emit `ABILITY_UNLOCK`. On level 25/50/... scenes, emit both `ABILITY_UNLOCK` and `CLASS_MUTATION`.
38. LEVELUP MILESTONES: If the player is one level below a milestone and the action clearly claims a breakthrough, victory, or crossing a limit, emit `LEVELUP` with `new_level` equal to the next level reached.
39. CONDITION ACCOUNTING: If poison, rot, corruption, burning, bleeding, or another harmful status is inflicted, include it in `conditions_add` with a positive `duration_turns`. If an antidote, cleanse, cure, or relief effect removes an active status, include the removed status in `conditions_remove`.
40. LORE ANSWERS: When asked about the Pact of Myr, Vor'Athek, the Primordial Thread, the Guild of Threads, or the Sealing, name the asked canon term directly and connect it to at least one other canon term or institution.
41. BACKLASH WORDING: When corrupted magic rebounds on the caster, say that the corruption backfires, lashes back, bites back, or rebounds into the caster instead of only implying generic pain.
42. SKILL TRACKING: When a player's action clearly invokes a named skill category (combat, stealth, social, politics, survival, medicine, lore, crafting, ritual, athletics, perception, nature, tactics, mysticism), emit `skill_use: {"skill_key": "<sub_skill>", "impact": <float>}` inside that player's `state_delta`. Impact values: 0.5=trivial/failed, 1.0=normal success, 2.0=significant (changed the scene), 3.0=exceptional (pivoted the session), 5.0=legendary (campaign-defining). Skill rank-ups are automatic — do not emit `skill_delta` unless you need to override a rank directly (rare). Omit `skill_use` for trivial environmental actions that do not reflect practiced competency.

PLAYER OUTPUT TARGETS:
{player_output_targets}

FINAL CHECKLIST:
- The JSON inside `<game_state>` is valid and parseable.
- If the level is a multiple of 25, `game_events` includes both `ABILITY_UNLOCK` and `CLASS_MUTATION`.
- If a missing item is used, the narrative explicitly states the item was not found and `hp_change` is not positive.
- If combat harm is narrated, at least one affected player usually has negative `hp_change`.
- If healing is applied with positive `hp_change`, the prose names the healing visibly.
- If one faction benefits and another is harmed, `reputation_delta` includes both entries.
- If a public rescue helps the Church, include a positive `church_pure_flame` delta.
- If the scene is celebration or aftermath, do not inject random combat rewards.
- If a player used a named skill that meaningfully shaped the outcome, include `skill_use` with an appropriate impact score in their `state_delta`.
- If departure is blocked during the cooperative mission, name the obstacle directly.
- If progression events are present, mention the growth in prose as well.
- In Port Myr onboarding, name Port Myr, the harbor, or the docks directly.
- For absent items or blocked departures, use explicit denial language rather than implication alone.
- For successful healing, use visible bodily recovery language rather than subtle implication alone.
- In unresolved combat, prefer showing immediate player-side cost instead of consequence-free dominance.
- If a consumable is drunk or applied, include it in `inventory_remove`.
- If one player gives an item to another, account for both sides of the transfer.
- If the player is nearly dead and the blow is final, emit `DEATH` or a fatal state.
- On level-multiple awakening scenes, do not omit `ABILITY_UNLOCK`.
- If the player crosses a level milestone after a breakthrough or claimed victory, emit `LEVELUP` with the new level.
- If poison, rot, or corruption is inflicted, include a harmful entry in `conditions_add` with a positive duration.
- If an antidote or cleanse works, include the removed effect in `conditions_remove`.
- If the scene is about the Pact of Myr or related canon, name at least two canon terms directly.
- If corrupted magic hurts the caster, describe it as backlash or corruption biting back.
- `state_delta` keys are exact runtime player IDs from PLAYER OUTPUT TARGETS.
- Every `game_events[].player_id` value is an exact runtime player ID from PLAYER OUTPUT TARGETS.
- `next_scene_query` is a short retrieval fragment only: max 12 words, no question mark, no full sentence.
- Narrative target: 70-130 words and two short paragraphs max.
- Do not wrap JSON in markdown fences. Use only plain `<game_state> ... </game_state>`.

RESPONSE FORMAT:
Free-form prose narrative, followed by:

<game_state>
{{
  "dice_rolls": [
    {{"player": "{example_player_name}", "die": 20, "purpose": "sword attack", "result": 18}}
  ],
  "state_delta": {{
    "{example_player_id}": {{
      "hp_change": -15,
      "mp_change": -10,
      "stamina_change": -20,
      "experience_gain": 50,
      "reputation_delta": [
        {{"faction_id": "church_pure_flame", "delta": 10, "reason": "Protected a wounded sentinel in public"}}
      ],
      "inventory_add": [
        {{"item_id": "generated-item-id", "name": "Item Name", "description": "Item description.", "rarity": "rare", "quantity": 1, "equipped": false}}
      ],
      "inventory_remove": [],
      "conditions_add": [
        {{"condition_id": "generated-condition-id", "name": "Poisoned", "description": "Loses 5 HP per turn.", "duration_turns": 3, "applied_at_turn": {turn_number}, "is_buff": false}}
      ],
      "conditions_remove": []
    }}
  }},
  "game_events": [
    {{"type": "LOOT", "player_id": "{example_player_id}", "player_name": "{example_player_name}", "items": [
      {{"item_id": "generated-loot-id", "name": "Ash Sword", "description": "Forged in the ruins.", "rarity": "epic", "quantity": 1, "equipped": false}}
    ]}},
    {{"type": "LEVELUP", "player_id": "{example_player_id}", "player_name": "{example_player_name}", "new_level": 5}},
    {{"type": "ABILITY_UNLOCK", "player_id": "{example_player_id}", "player_name": "{example_player_name}", "ability_name": "Ability Name", "ability_description": "Organic description."}},
    {{"type": "CLASS_MUTATION", "player_id": "{example_player_id}", "player_name": "{example_player_name}", "new_class": "Ash Warden", "old_class": "Warrior"}},
    {{"type": "DEATH", "player_id": "{example_player_id}", "player_name": "{example_player_name}", "cause": "fatal blow from the Golem"}}
  ],
  "tension_level": 6,
  "audio_cue": "combat_intense",
  "next_scene_query": "harbor rumor about Traveler mark"
}}
</game_state>"""


def build_gm_system_prompt(
    num_players: int,
    tension_level: int,
    turn_number: int = 0,
    encounter_scale: float = 1.0,
    boss_scale_steps: int = 0,
    player_output_targets: list[tuple[str, str]] | None = None,
    language: str = "en",
) -> str:
    player_output_targets = player_output_targets or []
    example_player_id = player_output_targets[0][0] if player_output_targets else "runtime-player-id"
    example_player_name = player_output_targets[0][1] if player_output_targets else "Player"
    rendered_targets = "\n".join(
        f"- {player_id} => {player_name}"
        for player_id, player_name in player_output_targets
    ) or "- runtime-player-id => Player"
    language_name = "Brazilian Portuguese" if language == "pt" else "English"
    return GM_SYSTEM_PROMPT_TEMPLATE.format(
        num_players=num_players,
        tension_level=tension_level,
        turn_number=turn_number,
        encounter_scale=encounter_scale,
        boss_scale_steps=boss_scale_steps,
        player_output_targets=rendered_targets,
        example_player_id=example_player_id,
        example_player_name=example_player_name,
        language_name=language_name,
    )
