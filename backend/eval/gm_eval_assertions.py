from __future__ import annotations

import re
from typing import Any, Callable

from eval.gm_eval_models import Assertion, DIMENSIONS, RuntimeContext, Scenario, ScenarioSetup, ScenarioTurn

HARD_FAIL_LABELS = {
    "Returns parseable game_state JSON",
    "Uses real player IDs in state_delta",
    "Avoids placeholder IDs in structured output",
    "Narrative denies use of the missing item",
    "Narrative blocks or discourages departure",
}


def assertion_category(assertion: Assertion) -> str:
    if assertion.category in {"contract", "narrative"}:
        return assertion.category
    return "contract"


def assertion_dimension(assertion: Assertion) -> str:
    return assertion.dimension if assertion.dimension in DIMENSIONS else "contract"


def scenario_hard_fail_labels(scenario: Scenario) -> set[str]:
    return set(HARD_FAIL_LABELS) | set(scenario.hard_fail_labels)


def score_dimensions(scenario: Scenario, passed_labels: list[str]) -> dict[str, dict[str, int]]:
    labels = set(passed_labels)
    scores: dict[str, dict[str, int]] = {dimension: {"passed": 0, "total": 0} for dimension in DIMENSIONS}
    for assertion in scenario.assertions:
        dimension = assertion_dimension(assertion)
        scores[dimension]["total"] += 1
        if assertion.label in labels:
            scores[dimension]["passed"] += 1
    return scores


def get_player_entries(gs: dict[str, Any]) -> list[dict[str, Any]]:
    state_delta = gs.get("state_delta", {})
    return [value for value in state_delta.values() if isinstance(value, dict)] if isinstance(state_delta, dict) else []


def extract_all_reputation_deltas(gs: dict[str, Any]) -> list[dict[str, Any]]:
    deltas: list[dict[str, Any]] = []
    for player_data in get_player_entries(gs):
        rep_delta = player_data.get("reputation_delta", [])
        if isinstance(rep_delta, list):
            deltas.extend(item for item in rep_delta if isinstance(item, dict))
    return deltas


def base_contract_assertions(require_followup: bool = True) -> list[Assertion]:
    checks = [
        Assertion("Returns parseable game_state JSON", has_parseable_json, category="contract", dimension="contract"),
        Assertion("Uses real player IDs in state_delta", valid_state_delta_targets, category="contract", dimension="contract"),
        Assertion("Avoids placeholder IDs in structured output", no_placeholder_player_ids, category="contract", dimension="contract"),
        Assertion("Narrative stays in-world", gm_stays_in_character, category="contract", dimension="narrative"),
    ]
    if require_followup:
        checks.append(Assertion("Provides a next-scene hook", has_scene_followup, category="contract", dimension="world"))
        checks.append(Assertion("Keeps next_scene_query retrieval-friendly", concise_next_scene_query, category="contract", dimension="contract"))
    return checks


def has_parseable_json(_: str, gs: dict[str, Any], __: RuntimeContext) -> bool:
    return bool(gs)


def has_nonempty_narrative(narrative: str, _: dict[str, Any], __: RuntimeContext) -> bool:
    return len(narrative.strip()) >= 80


def narrative_is_creative_enough(narrative: str, _: dict[str, Any], __: RuntimeContext) -> bool:
    text = narrative.lower()
    vivid = [
        "salt", "ash", "thread", "harbor", "dock", "flare", "glass", "rope", "lantern",
        "blood", "bone", "wind", "prayer", "seal", "fissure", "corruption", "mark",
    ]
    return len(narrative.strip()) >= 140 and sum(token in text for token in vivid) >= 3


def lore_is_specific_not_generic(narrative: str, _: dict[str, Any], __: RuntimeContext) -> bool:
    text = narrative.lower()
    canonical = [
        "pact of myr",
        "port myr",
        "guild of threads",
        "church of the pure flame",
        "myr council",
        "primordial thread",
        "vor'athek",
        "travelers",
        "dome",
    ]
    return sum(term in text for term in canonical) >= 2


def mentions_english_world_terms(narrative: str, _: dict[str, Any], __: RuntimeContext) -> bool:
    text = narrative.lower()
    terms = ["aerus", "myr", "thread", "flame", "empire", "guild", "isles"]
    return sum(term in text for term in terms) >= 2


def mentions_combat(narrative: str, _: dict[str, Any], __: RuntimeContext) -> bool:
    text = narrative.lower()
    terms = ["strike", "blade", "blood", "attack", "combat", "slash", "clash", "wound"]
    return any(term in text for term in terms)


def mentions_port_myr(narrative: str, _: dict[str, Any], __: RuntimeContext) -> bool:
    text = narrative.lower()
    return "port myr" in text or ("myr" in text and "harbor" in text)


def blocks_or_discourages_departure(narrative: str, _: dict[str, Any], __: RuntimeContext) -> bool:
    text = narrative.lower()
    return any(
        token in text
        for token in [
            "cannot leave",
            "can't leave",
            "blocked",
            "checkpoint",
            "refused passage",
            "stopped at the docks",
            "the harbor closes",
            "the route is shut",
        ]
    )


def location_not_changed(narrative: str, gs: dict[str, Any], __: RuntimeContext) -> bool:
    location = str(gs.get("location") or gs.get("current_location") or "").lower()
    if location and location not in {"port_myr", "isles_of_myr"}:
        return False
    text = narrative.lower()
    return not any(
        token in text
        for token in [
            "you set sail",
            "you leave the isles",
            "the ship departs",
            "you successfully depart",
        ]
    )


def is_visceral(narrative: str, _: dict[str, Any], __: RuntimeContext) -> bool:
    text = narrative.lower()
    return any(token in text for token in ["blood", "panic", "desperate", "terror", "crushing", "gasp", "agony"])


def has_dice_rolls(_: str, gs: dict[str, Any], __: RuntimeContext) -> bool:
    return isinstance(gs.get("dice_rolls"), list) and len(gs["dice_rolls"]) > 0


def has_negative_hp_change(_: str, gs: dict[str, Any], __: RuntimeContext) -> bool:
    for player_data in get_player_entries(gs):
        if int(player_data.get("hp_change", 0)) < 0:
            return True
    return False


def has_positive_hp_change(_: str, gs: dict[str, Any], __: RuntimeContext) -> bool:
    for player_data in get_player_entries(gs):
        if int(player_data.get("hp_change", 0)) > 0:
            return True
    return False


def has_reputation_delta(_: str, gs: dict[str, Any], __: RuntimeContext) -> bool:
    for player_data in get_player_entries(gs):
        rep_delta = player_data.get("reputation_delta", [])
        if isinstance(rep_delta, list) and rep_delta:
            return True
    return False


def has_named_reputation_delta(_: str, gs: dict[str, Any], __: RuntimeContext, faction_id: str) -> bool:
    return any(delta.get("faction_id") == faction_id for delta in extract_all_reputation_deltas(gs))


def has_positive_reputation_delta(_: str, gs: dict[str, Any], __: RuntimeContext, faction_id: str) -> bool:
    for delta in extract_all_reputation_deltas(gs):
        change = delta.get("delta", delta.get("change_value", 0))
        if delta.get("faction_id") == faction_id and isinstance(change, (int, float)) and change > 0:
            return True
    return False


def has_inventory_change(_: str, gs: dict[str, Any], __: RuntimeContext) -> bool:
    for player_data in get_player_entries(gs):
        if player_data.get("inventory_add") or player_data.get("inventory_remove"):
            return True
    return False


def has_experience_gain(_: str, gs: dict[str, Any], __: RuntimeContext) -> bool:
    return any(int(player_data.get("experience_gain", 0)) > 0 for player_data in get_player_entries(gs))


def mentions_progression(narrative: str, _: dict[str, Any], __: RuntimeContext) -> bool:
    text = narrative.lower()
    return any(token in text for token in ["power", "growth", "awakens", "surges", "new technique", "transformation", "level"])


def has_event_type(_: str, gs: dict[str, Any], __: RuntimeContext, event_type: str) -> bool:
    events = gs.get("game_events", [])
    return isinstance(events, list) and any(isinstance(event, dict) and event.get("type") == event_type for event in events)


def has_levelup_event(_: str, gs: dict[str, Any], __: RuntimeContext) -> bool:
    events = gs.get("game_events", [])
    if not isinstance(events, list):
        return False
    return any(
        isinstance(event, dict)
        and event.get("type") == "LEVELUP"
        and ("new_level" in event or "level" in event)
        for event in events
    )


def has_loot_event_with_items(_: str, gs: dict[str, Any], __: RuntimeContext) -> bool:
    events = gs.get("game_events", [])
    if not isinstance(events, list):
        return False
    for event in events:
        if isinstance(event, dict) and event.get("type") == "LOOT":
            items = event.get("items", [])
            if isinstance(items, list) and any(isinstance(item, dict) and item.get("name") for item in items):
                return True
    return False


def normalize_rarity(rarity: str) -> str:
    return rarity.strip().lower().replace("-", "_")


def has_non_common_loot_rarity(_: str, gs: dict[str, Any], __: RuntimeContext) -> bool:
    events = gs.get("game_events", [])
    if not isinstance(events, list):
        return False
    allowed = {"uncommon", "rare", "epic", "legendary", "mythic"}
    for event in events:
        if not isinstance(event, dict) or event.get("type") != "LOOT":
            continue
        for item in event.get("items", []):
            if isinstance(item, dict) and normalize_rarity(str(item.get("rarity", ""))) in allowed:
                return True
    return False


def has_conditions_add(_: str, gs: dict[str, Any], __: RuntimeContext) -> bool:
    return any(bool(player_data.get("conditions_add")) for player_data in get_player_entries(gs))


def has_condition_duration(_: str, gs: dict[str, Any], __: RuntimeContext) -> bool:
    for player_data in get_player_entries(gs):
        for cond in player_data.get("conditions_add", []):
            if isinstance(cond, dict) and int(cond.get("duration_turns", 0) or 0) > 0:
                return True
    return False


def has_inventory_remove(_: str, gs: dict[str, Any], __: RuntimeContext) -> bool:
    return any(bool(player_data.get("inventory_remove")) for player_data in get_player_entries(gs))


def narrative_shows_healing(narrative: str, _: dict[str, Any], __: RuntimeContext) -> bool:
    text = narrative.lower()
    return any(token in text for token in ["wound closes", "pain recedes", "restored", "healing warmth", "mended", "bandage"])


def has_scene_followup(_: str, gs: dict[str, Any], __: RuntimeContext) -> bool:
    next_scene = gs.get("next_scene_query")
    audio_cue = gs.get("audio_cue")
    return isinstance(next_scene, str) and bool(next_scene.strip()) or isinstance(audio_cue, str) and bool(audio_cue.strip())


def valid_state_delta_targets(_: str, gs: dict[str, Any], runtime: RuntimeContext) -> bool:
    state_delta = gs.get("state_delta", {})
    if not isinstance(state_delta, dict) or not state_delta:
        return False
    return set(state_delta.keys()).issubset(set(runtime.player_ids))


def no_placeholder_player_ids(_: str, gs: dict[str, Any], runtime: RuntimeContext) -> bool:
    valid_ids = set(runtime.player_ids)
    placeholder_values = {"id", "player_id", "pid", "unknown", "uuid", "name"}
    state_delta = gs.get("state_delta", {})
    if isinstance(state_delta, dict):
        if any(str(key).strip().lower() in placeholder_values for key in state_delta.keys()):
            return False
    for event in gs.get("game_events", []):
        if not isinstance(event, dict):
            continue
        player_id = event.get("player_id")
        if player_id is None:
            continue
        if str(player_id).strip().lower() in placeholder_values:
            return False
        if player_id not in valid_ids:
            return False
    return True


def concise_next_scene_query(_: str, gs: dict[str, Any], __: RuntimeContext) -> bool:
    query = gs.get("next_scene_query")
    if query is None:
        return True
    if not isinstance(query, str) or not query.strip():
        return False
    cleaned = query.strip()
    return len(cleaned) <= 140 and "?" not in cleaned


def has_mp_change_negative(_: str, gs: dict[str, Any], __: RuntimeContext) -> bool:
    return any(int(player_data.get("mp_change", 0)) < 0 for player_data in get_player_entries(gs))


def has_stamina_change_negative(_: str, gs: dict[str, Any], __: RuntimeContext) -> bool:
    return any(int(player_data.get("stamina_change", 0)) < 0 for player_data in get_player_entries(gs))


def has_per_player_delta(_: str, gs: dict[str, Any], runtime: RuntimeContext) -> bool:
    state_delta = gs.get("state_delta", {})
    return isinstance(state_delta, dict) and len(state_delta) >= len(runtime.player_ids) >= 2


def gm_stays_in_character(narrative: str, _: dict[str, Any], __: RuntimeContext) -> bool:
    text = narrative.lower()
    forbidden = [
        "as an ai",
        "out of character",
        "ooc",
        "mechanically",
        "game master note",
        "according to the rules above",
    ]
    return not any(token in text for token in forbidden)


def gm_handles_absurd_with_consequence(narrative: str, gs: dict[str, Any], __: RuntimeContext) -> bool:
    text = narrative.lower()
    consequence = any(token in text for token in ["fails", "recoils", "lashes", "slams", "breaks", "cost", "consequence"])
    return consequence and (bool(gs.get("state_delta")) or bool(gs.get("game_events")) or bool(gs.get("tension_level")))


def gm_refuses_nonexistent_item(narrative: str, _: dict[str, Any], __: RuntimeContext) -> bool:
    text = narrative.lower()
    return any(token in text for token in ["cannot find", "does not have", "searches in vain", "isn't there", "no potion"])


def gm_maintains_roll_result(narrative: str, _: dict[str, Any], __: RuntimeContext) -> bool:
    text = narrative.lower()
    return not any(token in text for token in ["retroactively", "actually the roll becomes", "the roll is changed"])


def gm_acknowledges_dispute(narrative: str, _: dict[str, Any], __: RuntimeContext) -> bool:
    text = narrative.lower()
    return any(token in text for token in ["protest", "frustration", "anger", "objection", "argue", "contest"])


def has_class_mutation_event(_: str, gs: dict[str, Any], __: RuntimeContext) -> bool:
    events = gs.get("game_events", [])
    if not isinstance(events, list):
        return False
    return any(isinstance(event, dict) and event.get("type") == "CLASS_MUTATION" and event.get("new_class") for event in events)


def has_dual_faction_rep(_: str, gs: dict[str, Any], __: RuntimeContext) -> bool:
    factions = {delta.get("faction_id") for delta in extract_all_reputation_deltas(gs) if delta.get("faction_id")}
    return len(factions) >= 2


def has_opposing_rep_deltas(_: str, gs: dict[str, Any], __: RuntimeContext) -> bool:
    positive = False
    negative = False
    for delta in extract_all_reputation_deltas(gs):
        change = delta.get("delta", delta.get("change_value", 0))
        if isinstance(change, (int, float)):
            positive = positive or change > 0
            negative = negative or change < 0
    return positive and negative


def has_social_consequence_event(_: str, gs: dict[str, Any], __: RuntimeContext) -> bool:
    events = gs.get("game_events", [])
    if not isinstance(events, list):
        return False
    return any(
        isinstance(event, dict) and event.get("type") in {"REPUTATION_CHANGE", "FACTION_CONFLICT", "DIPLOMACY_SUCCESS", "COOP_MISSION"}
        for event in events
    )


def narrative_shows_crime_consequence(narrative: str, _: dict[str, Any], __: RuntimeContext) -> bool:
    text = narrative.lower()
    return any(token in text for token in ["horror", "witnesses", "blood on your hands", "panic", "scream", "repercussion"])


def narrative_acknowledges_moral_weight(narrative: str, _: dict[str, Any], __: RuntimeContext) -> bool:
    text = narrative.lower()
    return any(token in text for token in ["guilt", "weight", "moral", "innocent", "sin", "hesitation", "consequence"])


def has_currency_gain(_: str, gs: dict[str, Any], __: RuntimeContext) -> bool:
    for player_data in get_player_entries(gs):
        curr = player_data.get("currency_add", {})
        if isinstance(curr, dict) and any(isinstance(v, (int, float)) and v > 0 for v in curr.values()):
            return True
        for item in player_data.get("inventory_add", []):
            if isinstance(item, dict):
                name = str(item.get("name", "")).lower()
                if any(token in name for token in ["coin", "gold", "silver", "reward", "payment"]):
                    return True
    return False


def has_buff_condition(_: str, gs: dict[str, Any], __: RuntimeContext) -> bool:
    for player_data in get_player_entries(gs):
        for cond in player_data.get("conditions_add", []):
            if isinstance(cond, dict) and bool(cond.get("is_buff")):
                return True
    return False


def has_multiple_conditions(_: str, gs: dict[str, Any], __: RuntimeContext) -> bool:
    return any(len(player_data.get("conditions_add", [])) >= 2 for player_data in get_player_entries(gs))


def has_inventory_add(_: str, gs: dict[str, Any], __: RuntimeContext) -> bool:
    return any(bool(player_data.get("inventory_add")) for player_data in get_player_entries(gs))


def has_conditions_remove(_: str, gs: dict[str, Any], __: RuntimeContext) -> bool:
    return any(bool(player_data.get("conditions_remove")) for player_data in get_player_entries(gs))


def narrative_mentions_lore(narrative: str, _: dict[str, Any], __: RuntimeContext) -> bool:
    text = narrative.lower()
    terms = [
        "pact of myr",
        "isles of myr",
        "church of the pure flame",
        "guild of threads",
        "children of the broken thread",
        "primordial thread",
        "vor'athek",
        "valdrek",
        "bloom",
        "corruption",
    ]
    return sum(term in text for term in terms) >= 2


def mentions_reward_or_payment(narrative: str, _: dict[str, Any], __: RuntimeContext) -> bool:
    text = narrative.lower()
    return any(token in text for token in ["reward", "payment", "coins", "gold", "paid", "bounty"])


def mentions_travel_pressure(narrative: str, _: dict[str, Any], __: RuntimeContext) -> bool:
    text = narrative.lower()
    return any(token in text for token in ["road", "sea", "storm", "checkpoint", "days", "route", "passage", "crossing"])


def mentions_crafting_process(narrative: str, _: dict[str, Any], __: RuntimeContext) -> bool:
    text = narrative.lower()
    return any(token in text for token in ["forge", "craft", "hammer", "mix", "distill", "loom", "recipe", "kit"])


def mentions_language_constraint(narrative: str, _: dict[str, Any], __: RuntimeContext) -> bool:
    text = narrative.lower()
    return any(token in text for token in ["cannot read", "translator", "script", "archaic", "language", "scholar"])


def mentions_blessing_or_divine_protection(narrative: str, _: dict[str, Any], __: RuntimeContext) -> bool:
    text = narrative.lower()
    return any(token in text for token in ["blessing", "divine", "holy", "sanctified", "sacred protection"])


def no_levelup_event(_: str, gs: dict[str, Any], runtime: RuntimeContext) -> bool:
    return not has_levelup_event("", gs, runtime)


def mentions_extreme_effort(narrative: str, _: dict[str, Any], __: RuntimeContext) -> bool:
    text = narrative.lower()
    return any(token in text for token in ["strain", "burning lungs", "every muscle", "heavy blow", "exhaustion", "spent"])


def mentions_corruption_backfire(narrative: str, _: dict[str, Any], __: RuntimeContext) -> bool:
    text = narrative.lower()
    return any(token in text for token in ["backfire", "corruption", "lashes into you", "thread bites back", "reverses"])


def mentions_fall_consequence(narrative: str, _: dict[str, Any], __: RuntimeContext) -> bool:
    text = narrative.lower()
    return any(token in text for token in ["falls", "crashes", "slams into", "hits the ground", "drops hard"])


def mentions_vorathek(narrative: str, _: dict[str, Any], __: RuntimeContext) -> bool:
    return "vor'athek" in narrative.lower()


def mentions_primordial_thread_or_corruption(narrative: str, _: dict[str, Any], __: RuntimeContext) -> bool:
    text = narrative.lower()
    return "primordial thread" in text or "corruption" in text or "corrupted thread" in text


def tension_at_most(maximum: int) -> Callable[[str, dict[str, Any], RuntimeContext], bool]:
    def _check(_: str, gs: dict[str, Any], __: RuntimeContext) -> bool:
        try:
            return int(gs.get("tension_level", 10)) <= maximum
        except (TypeError, ValueError):
            return False

    return _check


def has_death_event_or_fatal_state(narrative: str, gs: dict[str, Any], runtime: RuntimeContext) -> bool:
    if has_event_type(narrative, gs, runtime, "DEATH"):
        return True
    return any(int(player_data.get("hp_change", 0)) <= -90 for player_data in get_player_entries(gs))


def mentions_both_players(narrative: str, _: dict[str, Any], runtime: RuntimeContext) -> bool:
    text = narrative.lower()
    return all(name.lower() in text for name in runtime.player_names[:2])


def kael_loses_item(_: str, gs: dict[str, Any], runtime: RuntimeContext) -> bool:
    kael_id = runtime.player_name_to_id.get("Kael")
    if not kael_id:
        return False
    delta = gs.get("state_delta", {}).get(kael_id, {})
    return isinstance(delta, dict) and bool(delta.get("inventory_remove"))


def lyra_receives_help(_: str, gs: dict[str, Any], runtime: RuntimeContext) -> bool:
    lyra_id = runtime.player_name_to_id.get("Lyra")
    if not lyra_id:
        return False
    delta = gs.get("state_delta", {}).get(lyra_id, {})
    return isinstance(delta, dict) and (int(delta.get("hp_change", 0)) > 0 or bool(delta.get("inventory_add")))


def tension_at_least(minimum: int) -> Callable[[str, dict[str, Any], RuntimeContext], bool]:
    def _check(_: str, gs: dict[str, Any], __: RuntimeContext) -> bool:
        try:
            return int(gs.get("tension_level", 0)) >= minimum
        except (TypeError, ValueError):
            return False

    return _check


def build_topic_registry() -> dict[str, Any]:
    return {
        "Scenario": Scenario,
        "ScenarioSetup": ScenarioSetup,
        "ScenarioTurn": ScenarioTurn,
        "Assertion": Assertion,
        "base_contract": base_contract_assertions,
        "has_nonempty_narrative": has_nonempty_narrative,
        "narrative_is_creative_enough": narrative_is_creative_enough,
        "lore_is_specific_not_generic": lore_is_specific_not_generic,
        "mentions_english_world_terms": mentions_english_world_terms,
        "mentions_port_myr": mentions_port_myr,
        "mentions_combat": mentions_combat,
        "mentions_progression": mentions_progression,
        "mentions_reward_or_payment": mentions_reward_or_payment,
        "mentions_blessing_or_divine_protection": mentions_blessing_or_divine_protection,
        "mentions_travel_pressure": mentions_travel_pressure,
        "mentions_crafting_process": mentions_crafting_process,
        "mentions_language_constraint": mentions_language_constraint,
        "mentions_extreme_effort": mentions_extreme_effort,
        "mentions_corruption_backfire": mentions_corruption_backfire,
        "mentions_fall_consequence": mentions_fall_consequence,
        "mentions_vorathek": mentions_vorathek,
        "mentions_primordial_thread_or_corruption": mentions_primordial_thread_or_corruption,
        "has_inventory_add": has_inventory_add,
        "has_dice_rolls": has_dice_rolls,
        "has_negative_hp_change": has_negative_hp_change,
        "has_positive_hp_change": has_positive_hp_change,
        "has_experience_gain": has_experience_gain,
        "has_event_type": has_event_type,
        "has_named_reputation_delta": has_named_reputation_delta,
        "has_positive_reputation_delta": has_positive_reputation_delta,
        "has_levelup_event": has_levelup_event,
        "has_loot_event_with_items": has_loot_event_with_items,
        "has_non_common_loot_rarity": has_non_common_loot_rarity,
        "has_death_event_or_fatal_state": has_death_event_or_fatal_state,
        "has_conditions_add": has_conditions_add,
        "has_condition_duration": has_condition_duration,
        "has_inventory_remove": has_inventory_remove,
        "narrative_shows_healing": narrative_shows_healing,
        "narrative_mentions_lore": narrative_mentions_lore,
        "valid_state_delta_targets": valid_state_delta_targets,
        "has_scene_followup": has_scene_followup,
        "concise_next_scene_query": concise_next_scene_query,
        "has_mp_change_negative": has_mp_change_negative,
        "has_stamina_change_negative": has_stamina_change_negative,
        "has_per_player_delta": has_per_player_delta,
        "blocks_or_discourages_departure": blocks_or_discourages_departure,
        "location_not_changed": location_not_changed,
        "is_visceral": is_visceral,
        "has_reputation_delta": has_reputation_delta,
        "has_inventory_change": has_inventory_change,
        "gm_stays_in_character": gm_stays_in_character,
        "gm_handles_absurd_with_consequence": gm_handles_absurd_with_consequence,
        "gm_refuses_nonexistent_item": gm_refuses_nonexistent_item,
        "gm_maintains_roll_result": gm_maintains_roll_result,
        "gm_acknowledges_dispute": gm_acknowledges_dispute,
        "has_class_mutation_event": has_class_mutation_event,
        "has_dual_faction_rep": has_dual_faction_rep,
        "has_opposing_rep_deltas": has_opposing_rep_deltas,
        "has_social_consequence_event": has_social_consequence_event,
        "narrative_shows_crime_consequence": narrative_shows_crime_consequence,
        "narrative_acknowledges_moral_weight": narrative_acknowledges_moral_weight,
        "has_currency_gain": has_currency_gain,
        "has_buff_condition": has_buff_condition,
        "has_multiple_conditions": has_multiple_conditions,
        "has_conditions_remove": has_conditions_remove,
        "mentions_both_players": mentions_both_players,
        "kael_loses_item": kael_loses_item,
        "lyra_receives_help": lyra_receives_help,
        "no_levelup_event": no_levelup_event,
        "tension_at_least": tension_at_least,
        "tension_at_most": tension_at_most,
    }
