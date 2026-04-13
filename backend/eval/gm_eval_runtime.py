from __future__ import annotations

import asyncio
import json
import re
import time
import uuid
from typing import Any

import aiosqlite

from eval.gm_eval_assertions import scenario_hard_fail_labels, score_dimensions
from eval.gm_eval_models import RuntimeContext, Scenario, ScenarioResult
from eval.gm_eval_reporting import FAIL, LINE, PASS, THIN
from src import state_manager
from src.context_builder import build_context, build_gm_system_prompt
from src.local_llm import generate_chat
from src.migration_runner import run_migrations
from src.models import ActionBatch, PlayerAction
from src.time_manager import initialize_calendar


async def init_eval_db(conn: aiosqlite.Connection) -> None:
    conn.row_factory = aiosqlite.Row
    await run_migrations(conn)
    await state_manager.ensure_default_world_state(conn)
    await initialize_calendar(conn)


async def seed_player(
    conn: aiosqlite.Connection,
    name: str,
    username: str,
    level: int,
    hp_fraction: float,
    inferred_class: str,
    faction: str,
    initial_inventory: list[dict[str, Any]] | None = None,
    active_conditions: list[dict[str, Any]] | None = None,
    languages: list[str] | None = None,
    currency: dict[str, int] | None = None,
    macros: list[dict[str, Any]] | None = None,
    spell_aliases: dict[str, str] | None = None,
) -> str:
    player_id = str(uuid.uuid4())
    await state_manager.create_player(conn, player_id, username, "hash")
    await state_manager.set_character(
        conn,
        player_id=player_id,
        name=name,
        race="human",
        faction=faction,
        backstory="An outworld traveler trying to survive in Aerus.",
        inferred_class=inferred_class,
        secret_objective="Discover what the Primordial Thread expects from them.",
        max_hp=100,
    )
    await state_manager.seed_starter_inventory(conn, player_id, "martial adventurer")
    current_hp = max(1, int(100 * hp_fraction))
    await conn.execute(
        """
        UPDATE players
        SET level = ?, experience = ?, current_hp = ?, faction = ?, inferred_class = ?,
            languages_json = ?, currency_json = ?, macros_json = ?, spell_aliases_json = ?
        WHERE player_id = ?
        """,
        (
            level,
            max(0, (level - 1) * 100),
            current_hp,
            faction,
            inferred_class,
            json.dumps(languages or ["common_tongue"]),
            json.dumps(currency or {"copper": 0, "silver": 5, "gold": 0, "platinum": 0}),
            json.dumps(macros or []),
            json.dumps(spell_aliases or {}),
            player_id,
        ),
    )
    await conn.commit()

    if initial_inventory:
        await seed_inventory_items(conn, player_id, initial_inventory)
    if active_conditions:
        await seed_conditions(conn, player_id, active_conditions)
    return player_id


async def seed_inventory_items(conn: aiosqlite.Connection, player_id: str, items: list[dict[str, Any]]) -> None:
    for item in items:
        item_id = str(item.get("item_id") or f"{player_id}-{uuid.uuid4()}")
        name = str(item.get("name") or "Item")
        description = str(item.get("description") or "")
        rarity = str(item.get("rarity") or "common")
        quantity = max(1, int(item.get("quantity", 1)))
        equipped = 1 if bool(item.get("equipped")) else 0
        await conn.execute(
            """
            INSERT INTO inventory
                (item_id, player_id, name, description, rarity, quantity, equipped, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(item_id) DO UPDATE SET
                quantity = excluded.quantity,
                equipped = excluded.equipped
            """,
            (item_id, player_id, name, description, rarity, quantity, equipped, "{}"),
        )
    await state_manager.recalculate_inventory_weight(conn, player_id)
    await conn.commit()


async def seed_conditions(conn: aiosqlite.Connection, player_id: str, conditions: list[dict[str, Any]]) -> None:
    await state_manager._apply_condition_changes(  # type: ignore[attr-defined]
        conn,
        player_id,
        {"conditions_add": conditions},
        turn_number=0,
    )
    await conn.commit()


async def set_location(conn: aiosqlite.Connection, location: str) -> None:
    await state_manager.set_world_state(conn, "current_location", location)


async def set_tension(conn: aiosqlite.Connection, tension: int) -> None:
    await state_manager.set_world_state(conn, "tension_level", str(tension))


async def set_cooperative_mission(
    conn: aiosqlite.Connection,
    *,
    active: bool,
    completed: bool,
    num_players: int,
) -> None:
    await state_manager.set_quest_flag(conn, state_manager.COOP_MISSION_ACTIVE_KEY, "1" if active else "0")
    await state_manager.set_quest_flag(conn, state_manager.COOP_MISSION_COMPLETED_KEY, "1" if completed else "0")
    await state_manager.set_quest_flag(
        conn,
        state_manager.COOP_MISSION_BLOCKING_KEY,
        "1" if active and not completed and num_players > 1 else "0",
    )
    await state_manager.set_quest_flag(conn, state_manager.COOP_MISSION_REQUIRED_PLAYERS_KEY, str(num_players))
    await state_manager.set_quest_flag(conn, state_manager.COOP_MISSION_OBJECTIVE_KEY, state_manager.COOP_MISSION_OBJECTIVE_DEFAULT)
    await state_manager.set_quest_flag(conn, state_manager.COOP_MISSION_ID_KEY, "mission_coop_intro_v1")
    await state_manager.set_quest_flag(
        conn,
        "cooperative_mission_completed_players",
        str(num_players if completed else 0),
    )


async def apply_extra_world_state(conn: aiosqlite.Connection, values: dict[str, str]) -> None:
    for key, value in values.items():
        await state_manager.set_world_state(conn, key, value)


def normalize_runtime_id(raw_value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(raw_value or "").lower())


def resolve_runtime_player_id(candidate: Any, valid_player_ids: list[str]) -> str | None:
    if not isinstance(candidate, str):
        return None
    cleaned = candidate.strip()
    if not cleaned:
        return None
    if cleaned in valid_player_ids:
        return cleaned

    normalized_candidate = normalize_runtime_id(cleaned)
    if not normalized_candidate:
        return None

    by_norm = {normalize_runtime_id(player_id): player_id for player_id in valid_player_ids}
    if normalized_candidate in by_norm:
        return by_norm[normalized_candidate]

    prefix_matches = [
        player_id
        for player_id in valid_player_ids
        if normalize_runtime_id(player_id).startswith(normalized_candidate)
        or normalized_candidate.startswith(normalize_runtime_id(player_id))
    ]
    if len(prefix_matches) == 1:
        return prefix_matches[0]

    if len(valid_player_ids) == 1 and len(normalized_candidate) >= 8:
        return valid_player_ids[0]
    return None


def reconcile_runtime_player_ids(game_state: dict[str, Any], valid_player_ids: list[str]) -> dict[str, Any]:
    if not valid_player_ids or not game_state:
        return game_state

    state_delta = game_state.get("state_delta", {})
    if isinstance(state_delta, dict):
        normalized_delta: dict[str, Any] = {}
        for raw_player_id, delta in state_delta.items():
            resolved = resolve_runtime_player_id(raw_player_id, valid_player_ids)
            if not resolved:
                normalized_delta[str(raw_player_id)] = delta
                continue
            current = normalized_delta.get(resolved)
            if isinstance(current, dict) and isinstance(delta, dict):
                merged = dict(current)
                merged.update(delta)
                normalized_delta[resolved] = merged
            else:
                normalized_delta[resolved] = delta
        game_state["state_delta"] = normalized_delta

    events = game_state.get("game_events", [])
    if isinstance(events, list):
        normalized_events: list[dict[str, Any]] = []
        for event in events:
            if not isinstance(event, dict):
                continue
            normalized_event = dict(event)
            resolved = resolve_runtime_player_id(normalized_event.get("player_id"), valid_player_ids)
            if resolved:
                normalized_event["player_id"] = resolved
            normalized_events.append(normalized_event)
        game_state["game_events"] = normalized_events
    return game_state


def parse_response(raw: str, *, default_tension: int = 5, valid_player_ids: list[str] | None = None) -> tuple[str, dict[str, Any]]:
    narrative = raw.strip()
    game_state: dict[str, Any] = {}
    match = re.search(r"<game_state>\s*(.*?)\s*</game_state>", raw, re.DOTALL)
    if not match:
        match = re.search(r"```game_state\s*(.*?)\s*```", raw, re.DOTALL | re.IGNORECASE)
    if not match:
        open_tag = re.search(r"<game_state>\s*", raw, re.IGNORECASE)
        if open_tag:
            match_text = raw[open_tag.end():]
            match = True
        else:
            fence_tag = re.search(r"```game_state\s*", raw, re.IGNORECASE)
            if fence_tag:
                match_text = raw[fence_tag.end():]
                match = True
            else:
                match_text = ""
    if not match:
        return narrative, game_state

    if hasattr(match, "start"):
        narrative = raw[: match.start()].strip()
        json_text = match.group(1).strip()
    else:
        narrative = raw.split("<game_state>", 1)[0].split("```game_state", 1)[0].strip()
        json_text = match_text.strip()

    candidates = [
        json_text,
        re.sub(r"//[^\n]*", "", json_text),
        repair_json_candidate(json_text),
    ]
    for candidate in candidates:
        candidate = re.sub(r",\s*([}\]])", r"\1", candidate)
        candidate = re.sub(r"([:\[,]\s*)\+(\d)", r"\1\2", candidate)
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            game_state = parsed
            break
    if not game_state:
        game_state = salvage_partial_game_state(json_text)
    if game_state:
        game_state["game_events"] = normalize_game_events(game_state.get("game_events"))
        game_state.setdefault("tension_level", default_tension)
        next_scene = normalize_next_scene_query(game_state.get("next_scene_query"), narrative)
        if next_scene:
            game_state["next_scene_query"] = next_scene
        if valid_player_ids:
            game_state = reconcile_runtime_player_ids(game_state, valid_player_ids)
    return narrative, game_state


def repair_json_candidate(raw_json: str) -> str:
    text = raw_json.strip()
    if not text:
        return text
    start = text.find("{")
    if start >= 0:
        text = text[start:]
    text = re.sub(r"\s*```.*$", "", text, flags=re.DOTALL)
    chars: list[str] = []
    stack: list[str] = []
    in_string = False
    escape = False
    for ch in text:
        chars.append(ch)
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch in "{[":
            stack.append("}" if ch == "{" else "]")
        elif ch in "}]":
            if stack and stack[-1] == ch:
                stack.pop()
            else:
                break
    if in_string:
        chars.append('"')
    while stack:
        chars.append(stack.pop())
    repaired = "".join(chars)
    return re.sub(r"([:\[,]\s*)\+(\d)", r"\1\2", repaired)


def salvage_partial_game_state(raw_json: str) -> dict[str, Any]:
    text = raw_json.strip()
    if not text:
        return {}
    salvaged: dict[str, Any] = {}
    for key, opener in (("dice_rolls", "["), ("state_delta", "{"), ("game_events", "[")):
        match = re.search(rf'"{key}"\s*:\s*', text)
        if not match:
            continue
        start = text.find(opener, match.end())
        if start < 0:
            continue
        block = extract_balanced_json_block(text, start)
        if not block:
            continue
        candidate = repair_json_candidate(block)
        candidate = re.sub(r",\s*([}\]])", r"\1", candidate)
        try:
            salvaged[key] = json.loads(candidate)
        except json.JSONDecodeError:
            continue

    tension_match = re.search(r'"tension_level"\s*:\s*(-?\d+)', text)
    if tension_match:
        salvaged["tension_level"] = int(tension_match.group(1))
    for key in ("audio_cue", "next_scene_query"):
        match = re.search(rf'"{key}"\s*:\s*"([^"]*)"', text)
        if match:
            salvaged[key] = match.group(1)
    return salvaged


def extract_balanced_json_block(text: str, start: int) -> str:
    if start < 0 or start >= len(text) or text[start] not in "{[":
        return ""
    closing = "}" if text[start] == "{" else "]"
    stack = [closing]
    chars: list[str] = []
    in_string = False
    escape = False
    for ch in text[start:]:
        chars.append(ch)
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch in "{[":
            stack.append("}" if ch == "{" else "]")
        elif ch in "}]":
            if stack and ch == stack[-1]:
                stack.pop()
                if not stack:
                    return "".join(chars)
            else:
                break
    return "".join(chars + stack[::-1])


def normalize_next_scene_query(raw_query: Any, narrative: str) -> str | None:
    if isinstance(raw_query, str) and raw_query.strip():
        cleaned = re.sub(r"[?!.]+", "", raw_query).strip()
        cleaned = " ".join(cleaned.split()[:12])
        return cleaned or None
    fallback = derive_next_scene_query(narrative)
    return fallback or None


def normalize_game_events(raw_events: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_events, list):
        return []
    normalized: list[dict[str, Any]] = []
    for event in raw_events:
        if not isinstance(event, dict):
            continue
        if not event.get("type"):
            continue
        player_id = event.get("player_id")
        if player_id is not None:
            if not isinstance(player_id, str):
                continue
            candidate = player_id.strip()
            if len(candidate) < 30 or candidate.count("-") < 4:
                continue
        normalized.append(event)
    return normalized


async def load_turn_history(conn: aiosqlite.Connection, limit: int = 6) -> list[dict[str, str]]:
    history = await state_manager.get_recent_history(conn, limit=max(2, limit))
    return [{"role": row["role"], "content": row["content"]} for row in history][-limit:]


async def apply_eval_game_state(conn: aiosqlite.Connection, gs: dict[str, Any]) -> None:
    if not gs:
        return
    if "tension_level" in gs:
        await state_manager.set_world_state(conn, "tension_level", str(gs.get("tension_level")))
    location = gs.get("location") or gs.get("current_location")
    if isinstance(location, str) and location.strip():
        await state_manager.set_world_state(conn, "current_location", location.strip())
    state_delta = gs.get("state_delta", {})
    if isinstance(state_delta, dict):
        for player_id, delta in state_delta.items():
            if isinstance(player_id, str) and isinstance(delta, dict):
                await state_manager.apply_state_delta(conn, player_id, normalize_eval_delta(delta))


def normalize_eval_delta(delta: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(delta)
    normalized["inventory_add"] = normalize_object_list(delta.get("inventory_add"), object_id_key="item_id")
    normalized["conditions_add"] = normalize_object_list(delta.get("conditions_add"), object_id_key="condition_id")
    normalized["inventory_remove"] = normalize_id_list(delta.get("inventory_remove"), fallback_keys=("item_id", "name"))
    normalized["conditions_remove"] = normalize_id_list(delta.get("conditions_remove"), fallback_keys=("condition_id", "name"))
    return normalized


def normalize_object_list(value: Any, *, object_id_key: str) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    normalized: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        obj = dict(item)
        if not obj.get(object_id_key):
            fallback = obj.get("name") or f"generated-{object_id_key}-{uuid.uuid4()}"
            obj[object_id_key] = str(fallback).strip().lower().replace(" ", "-")
        normalized.append(obj)
    return normalized


def normalize_id_list(value: Any, *, fallback_keys: tuple[str, ...]) -> list[str]:
    if not isinstance(value, list):
        return []
    normalized: list[str] = []
    for item in value:
        if isinstance(item, str) and item.strip():
            normalized.append(item.strip())
            continue
        if isinstance(item, dict):
            for key in fallback_keys:
                raw = item.get(key)
                if isinstance(raw, str) and raw.strip():
                    normalized.append(raw.strip())
                    break
    return normalized


def derive_followup_action(previous_narrative: str, previous_gs: dict[str, Any]) -> str:
    query = previous_gs.get("next_scene_query")
    if isinstance(query, str) and query.strip():
        cleaned = re.sub(r"[?!.]+", "", query).strip()
        cleaned = " ".join(cleaned.split()[:12])
        return f"I act immediately on this pressure: {cleaned or 'the newest complication'}."
    if previous_narrative.strip():
        snippet = " ".join(previous_narrative.strip().split()[:18])
        return f"I react to the newest complication and push the scene forward from this moment: {snippet}"
    return "I respond to the newest complication and press the scene forward."


def derive_next_scene_query(narrative: str) -> str:
    text = re.sub(r"\s+", " ", narrative).strip()
    if not text:
        return ""
    sentences = [segment.strip(" .,!?:;\"'") for segment in re.split(r"[.!?]+", text) if segment.strip()]
    seed = sentences[-1] if sentences else text
    words = [word for word in re.findall(r"[A-Za-z0-9'_-]+", seed) if len(word) > 2]
    return " ".join(words[:12])


async def run_scenario(
    index: int,
    total: int,
    scenario: Scenario,
    *,
    eval_max_tokens: int,
    scenario_timeout_seconds: float,
) -> ScenarioResult:
    setup = scenario.setup
    raw_response = ""
    error: str | None = None
    final_narrative = ""
    final_game_state: dict[str, Any] = {}
    turn_results: list[dict[str, Any]] = []

    async with aiosqlite.connect(":memory:") as conn:
        await init_eval_db(conn)
        await set_location(conn, setup.location)
        await set_tension(conn, setup.tension)
        if setup.world_state:
            await apply_extra_world_state(conn, setup.world_state)

        player_ids: list[str] = []
        player_name_to_id: dict[str, str] = {}
        kael_id = await seed_player(
            conn,
            name="Kael",
            username=f"kael_eval_{index}",
            level=setup.level,
            hp_fraction=setup.hp_fraction,
            inferred_class=setup.inferred_class,
            faction=setup.faction,
            initial_inventory=setup.initial_inventory,
            active_conditions=setup.active_conditions,
            languages=setup.languages,
            currency=setup.currency,
            macros=setup.macros,
            spell_aliases=setup.spell_aliases,
        )
        player_ids.append(kael_id)
        player_name_to_id["Kael"] = kael_id

        if setup.num_players >= 2:
            lyra_id = await seed_player(
                conn,
                name="Lyra",
                username=f"lyra_eval_{index}",
                level=setup.extra_level or setup.level,
                hp_fraction=setup.extra_hp_fraction if setup.extra_hp_fraction is not None else setup.hp_fraction,
                inferred_class=setup.extra_inferred_class,
                faction=setup.extra_faction,
                initial_inventory=setup.extra_initial_inventory,
                active_conditions=setup.extra_active_conditions,
                languages=setup.extra_languages,
                currency=setup.extra_currency,
                macros=setup.extra_macros,
                spell_aliases=setup.extra_spell_aliases,
            )
            player_ids.append(lyra_id)
            player_name_to_id["Lyra"] = lyra_id

        await set_cooperative_mission(
            conn,
            active=setup.coop_mission_active,
            completed=setup.coop_mission_completed,
            num_players=setup.num_players,
        )

        runtime = RuntimeContext(
            player_ids=player_ids,
            player_names=["Kael"] if len(player_ids) == 1 else ["Kael", "Lyra"],
            player_name_to_id=player_name_to_id,
        )

        for seed_idx, message in enumerate(scenario.history_messages, start=1):
            await state_manager.append_history(conn, str(uuid.uuid4()), seed_idx, message["role"], message["content"])

        prior_narrative = ""
        prior_game_state: dict[str, Any] = {}
        for turn_idx, turn in enumerate(scenario.turns, start=1):
            runtime.current_turn = turn_idx
            for message in turn.history_messages:
                await state_manager.append_history(conn, str(uuid.uuid4()), turn_idx, message["role"], message["content"])

            action_text = derive_followup_action(prior_narrative, prior_game_state) if turn.dynamic_followup else turn.action_text

            actions = [
                PlayerAction(
                    player_id=pid,
                    player_name="Kael" if idx == 0 else "Lyra",
                    action_text=action_text,
                    timestamp=time.time(),
                )
                for idx, pid in enumerate(player_ids)
            ]
            batch = ActionBatch(actions=actions, turn_number=turn_idx)
            tension_level = int(await state_manager.get_world_state(conn, "tension_level") or setup.tension)
            context = await build_context(conn, batch, tension_level=tension_level)
            system_prompt = build_gm_system_prompt(
                num_players=setup.num_players,
                tension_level=tension_level,
                turn_number=turn_idx,
                player_output_targets=[(pid, "Kael" if idx == 0 else "Lyra") for idx, pid in enumerate(player_ids)],
            )
            messages: list[dict[str, str]] = [
                {"role": "system", "content": context.to_system_prompt() + "\n\n" + system_prompt},
                *await load_turn_history(conn, limit=6),
                {"role": "user", "content": action_text},
            ]

            try:
                raw_response = await asyncio.wait_for(
                    generate_chat(messages, max_tokens=eval_max_tokens),
                    timeout=scenario_timeout_seconds,
                )
            except Exception as exc:  # pragma: no cover
                error = str(exc)
                break

            narrative, game_state = parse_response(raw_response, default_tension=tension_level, valid_player_ids=player_ids)
            await state_manager.append_history(conn, str(uuid.uuid4()), turn_idx, "user", action_text)
            await state_manager.append_history(conn, str(uuid.uuid4()), turn_idx, "assistant", narrative)
            await apply_eval_game_state(conn, game_state)

            final_narrative = narrative
            final_game_state = game_state
            prior_narrative = narrative
            prior_game_state = game_state
            turn_results.append(
                {
                    "turn": turn_idx,
                    "action_text": action_text,
                    "narrative_chars": len(narrative),
                    "json_present": bool(game_state),
                    "next_scene_query": game_state.get("next_scene_query"),
                }
            )

    passed: list[str] = []
    failed: list[str] = []
    for assertion in scenario.assertions:
        try:
            ok = assertion.fn(final_narrative, final_game_state, runtime)
        except Exception:
            ok = False
        if ok:
            passed.append(assertion.label)
        else:
            failed.append(assertion.label)

    return ScenarioResult(
        scenario=scenario,
        narrative=final_narrative,
        game_state=final_game_state,
        raw_response=raw_response,
        passed=passed,
        failed=failed,
        error=error,
        dimension_scores=score_dimensions(scenario, passed),
        hard_failures=[label for label in failed if label in scenario_hard_fail_labels(scenario)],
        turn_results=turn_results,
    )


async def run_selected_scenarios(
    scenarios: list[Scenario],
    *,
    eval_max_tokens: int,
    scenario_timeout_seconds: float,
    concurrency: int,
) -> list[ScenarioResult]:
    total = len(scenarios)
    semaphore = asyncio.Semaphore(concurrency)

    async def _run(index: int, scenario: Scenario) -> tuple[int, ScenarioResult]:
        async with semaphore:
            print(f"\n{LINE}")
            print(f"Running [{index}/{total}] {scenario.name}")
            print(f"Description: {scenario.description}")
            print(f"Concurrency slot: {concurrency}")
            print(LINE)
            started = time.time()
            result = await run_scenario(
                index,
                total,
                scenario,
                eval_max_tokens=eval_max_tokens,
                scenario_timeout_seconds=scenario_timeout_seconds,
            )
            result.elapsed_seconds = time.time() - started
            return index, result

    indexed_results = await asyncio.gather(*[_run(index, scenario) for index, scenario in enumerate(scenarios, start=1)])
    ordered = sorted(indexed_results, key=lambda item: item[0])
    results = [result for _, result in ordered]
    for idx, result in ordered:
        print_scenario_result(idx, total, result)
    return results


def print_scenario_result(idx: int, total: int, result: ScenarioResult) -> None:
    setup = result.scenario.setup
    print(f"\n[{idx}/{total}] {result.scenario.name}")
    print(
        f"Setup: level={setup.level}, hp={int(setup.hp_fraction * 100)}/100, "
        f"tension={setup.tension}, location={setup.location}, players={setup.num_players}, tier={result.scenario.tier}"
    )
    print(f"Suites: {', '.join(sorted(result.scenario.suites))}")
    print(f"Action: {(result.scenario.turns[0].action_text if result.scenario.turns else result.scenario.action_text)}")

    if result.error:
        print(f"\nModel call failed: {result.error}")
        return

    print(f"\n{THIN}")
    print("Narrative")
    print(THIN)
    print(result.narrative or "[empty narrative]")

    print(f"\n{THIN}")
    print("Game State")
    print(THIN)
    if result.game_state:
        print(json.dumps(result.game_state, ensure_ascii=False, indent=2))
    else:
        print("[missing or invalid <game_state> JSON]")
        if result.raw_response:
            print(result.raw_response[-600:])

    print(f"\n{THIN}")
    print("Checks")
    print(THIN)
    for label in result.passed:
        print(f"{PASS} {label}")
    for label in result.failed:
        print(f"{FAIL} {label}")
    if result.hard_failures:
        print(f"Hard fails: {', '.join(result.hard_failures)}")
    if result.turn_results:
        print("Turn trace:")
        for turn in result.turn_results:
            print(
                f"- turn {turn['turn']}: chars={turn['narrative_chars']} "
                f"json={'yes' if turn['json_present'] else 'no'} "
                f"next_scene={repr(turn['next_scene_query'])}"
            )
    score_pct = int(100 * result.score / result.total) if result.total else 0
    print(f"Score: {result.score}/{result.total} ({score_pct}%)")
