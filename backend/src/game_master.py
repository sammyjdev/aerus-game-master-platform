"""
game_master.py - Central orchestrator. The only module that calls OpenRouter.
Responsibilities: action batching, context assembly, LLM calls,
response parsing, delta application, and event broadcasting.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
import uuid
from typing import Any, AsyncIterator

import aiosqlite
from openai import AsyncOpenAI

from . import connection_manager as cm
from .debug_tools import clip_text, log_debug, log_flow, summarize_payload
from . import memory_manager
from . import local_llm
from . import state_manager, travel_manager, vector_store
from .application.billing.billing_router import select_billing_config
from .context_builder import build_context, build_gm_system_prompt
from .models import ActionBatch, GMResponse, PlayerAction, WSMessageType

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Action batching
# ---------------------------------------------------------------------------

_pending_actions: list[PlayerAction] = []
_batch_lock = asyncio.Lock()
_batch_task: asyncio.Task | None = None
_BATCH_WINDOW_SECONDS = 3.0


def get_runtime_metrics() -> dict[str, Any]:
    return {
        "pending_actions": len(_pending_actions),
        "batch_task_active": bool(_batch_task and not _batch_task.done()),
        "batch_window_seconds": _BATCH_WINDOW_SECONDS,
    }


async def submit_action(
    player_id: str,
    player_name: str,
    action_text: str,
) -> None:
    """
    Receives a player action and adds it to the batching window.
    It does not receive conn - the batch task opens its own connection.
    """
    global _batch_task

    action = PlayerAction(
        player_id=player_id,
        player_name=player_name,
        action_text=action_text,
        timestamp=time.time(),
    )

    async with _batch_lock:
        _pending_actions.append(action)
        logger.debug("Action added to batch: %s -> %s", player_name, action_text[:50])
        log_debug(
            logger,
            "batch_action_enqueued",
            player_id=player_id,
            player_name=player_name,
            pending_actions=len(_pending_actions),
            action_preview=clip_text(action_text, 140),
        )

        if _batch_task is None or _batch_task.done():
            _batch_task = asyncio.create_task(_process_batch_after_window())


async def _process_batch_after_window() -> None:
    """
    Waits for the batching window and processes all accumulated actions.
    Opens its own connection - the WebSocket connection may already be closed.
    """
    await asyncio.sleep(_BATCH_WINDOW_SECONDS)

    async with _batch_lock:
        if not _pending_actions:
            return
        actions = list(_pending_actions)
        _pending_actions.clear()

    log_flow(
        logger,
        "batch_window_closed",
        actions_count=len(actions),
        players=[action.player_name for action in actions],
    )

    async with state_manager.db_context() as conn:
        turn_number = await state_manager.get_current_turn_number(conn) + 1
        batch = ActionBatch(actions=actions, turn_number=turn_number)
        await process_batch(conn, batch)


# ---------------------------------------------------------------------------
# Batch processing
# ---------------------------------------------------------------------------

async def _resolve_billing(
    conn: aiosqlite.Connection, batch: ActionBatch
) -> Any:
    first_player_id = batch.actions[0].player_id if batch.actions else None
    byok_encrypted = None
    if first_player_id:
        byok_encrypted = await state_manager.get_byok_key(conn, first_player_id)
    tension_level = await _get_tension_level(conn)
    log_debug(
        logger,
        "billing_resolution_requested",
        tension_level=tension_level,
        has_byok=bool(byok_encrypted),
        player_id=first_player_id,
    )
    return select_billing_config(
        tension_level=tension_level,
        player_byok_encrypted=byok_encrypted,
        player_id=first_player_id,
    )


async def _build_messages(
    conn: aiosqlite.Connection,
    context: Any,
    user_message: str,
    batch: ActionBatch,
    party_size: int,
) -> list[dict[str, str]]:
    tension_level = await _get_tension_level(conn)
    encounter_scale, boss_scale_steps = _calculate_encounter_scaling(party_size)
    system_prompt = build_gm_system_prompt(
        num_players=party_size,
        tension_level=tension_level,
        turn_number=batch.turn_number,
        encounter_scale=encounter_scale,
        boss_scale_steps=boss_scale_steps,
    )
    messages: list[dict[str, str]] = [
        {"role": "system", "content": context.to_system_prompt() + "\n\n" + system_prompt},
    ]
    history = await state_manager.get_recent_history(conn, limit=10)
    for h in history:
        messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": user_message})
    log_debug(
        logger,
        "gm_messages_built",
        turn_number=batch.turn_number,
        party_size=party_size,
        encounter_scale=encounter_scale,
        boss_scale_steps=boss_scale_steps,
        message_count=len(messages),
        history_count=len(history),
        user_message=clip_text(user_message, 220),
    )
    return messages


def _calculate_encounter_scaling(party_size: int) -> tuple[float, int]:
    normalized_party = max(1, party_size)
    encounter_scale = round(1.0 + (normalized_party - 1) * 0.35, 2)
    boss_scale_steps = max(0, (normalized_party - 1) // 2)
    return encounter_scale, boss_scale_steps


def get_encounter_scaling_preview(party_size: int) -> dict[str, float | int]:
    encounter_scale, boss_scale_steps = _calculate_encounter_scaling(party_size)
    return {
        "party_size": max(1, party_size),
        "encounter_scale": encounter_scale,
        "boss_scale_steps": boss_scale_steps,
    }


async def _get_party_size(conn: aiosqlite.Connection, batch: ActionBatch) -> int:
    alive_players = await state_manager.get_all_alive_players(conn)
    alive_count = len([p for p in alive_players if p["name"]])
    return max(1, alive_count, len(batch.actions))


_GAME_STATE_MARKER = "<game_state>"


def _flush_buffer(buffer: str) -> tuple[str, str]:
    """
    Checks whether the buffer contains <game_state>.
    Returns (to_emit, new_buffer). If to_emit is None, it signals stop.
    """
    if _GAME_STATE_MARKER in buffer:
        return buffer[: buffer.index(_GAME_STATE_MARKER)], ""
    if len(buffer) > 50:
        return buffer[:-20], buffer[-20:]
    return "", buffer


async def _tokens_from_stream(
    stream: Any, collector: list[str]
) -> AsyncIterator[str]:
    """Itera sobre o stream OpenAI, coleta a resposta completa e filtra <game_state>."""
    buffer = ""
    async for chunk in stream:
        delta = chunk.choices[0].delta.content
        if not delta:
            continue
        collector.append(delta)
        buffer += delta
        to_emit, buffer = _flush_buffer(buffer)
        if _GAME_STATE_MARKER in (buffer + delta):
            if to_emit:
                yield to_emit
            return
        if to_emit:
            yield to_emit
    if buffer:
        yield buffer


async def _stream_llm(
    billing: Any, messages: list[dict[str, str]]
) -> tuple[str, str]:
    """Chama o LLM e faz streaming para os jogadores. Retorna (full_response, narrative)."""
    started_at = time.perf_counter()
    if local_llm.is_local_only():
        model = os.getenv("AERUS_OLLAMA_GM_MODEL", os.getenv("AERUS_OLLAMA_MODEL", "qwen2.5:14b-instruct"))
        log_flow(logger, "gm_llm_start", provider="ollama", model=model, message_count=len(messages))
        full_response = await local_llm.generate_chat(
            messages,
            max_tokens=2048,
            model_override=model,
        )
        narrative = await cm.manager.broadcast_stream(_tokens_from_text(full_response))
        log_flow(
            logger,
            "gm_llm_complete",
            provider="ollama",
            model=model,
            duration_ms=round((time.perf_counter() - started_at) * 1000, 2),
            response_chars=len(full_response),
            narrative_chars=len(narrative),
        )
        return full_response, narrative

    client = AsyncOpenAI(api_key=billing.api_key, base_url=billing.base_url)
    collector: list[str] = []

    log_flow(logger, "gm_llm_start", provider="openrouter", model=billing.model, message_count=len(messages))

    stream = await client.chat.completions.create(
        model=billing.model,
        messages=messages,
        stream=True,
        max_tokens=2048,
        extra_headers={
            "HTTP-Referer": "https://aerus-rpg.fly.dev",
            "X-Title": "Aerus Game Master Platform",
        },
    )
    narrative = await cm.manager.broadcast_stream(_tokens_from_stream(stream, collector))
    full_response = "".join(collector)
    log_flow(
        logger,
        "gm_llm_complete",
        provider="openrouter",
        model=billing.model,
        duration_ms=round((time.perf_counter() - started_at) * 1000, 2),
        response_chars=len(full_response),
        narrative_chars=len(narrative),
    )
    return full_response, narrative


async def _tokens_from_text(full_response: str) -> AsyncIterator[str]:
    buffer = ""
    chunk_size = 48
    for index in range(0, len(full_response), chunk_size):
        buffer += full_response[index:index + chunk_size]
        to_emit, buffer = _flush_buffer(buffer)
        if to_emit:
            yield to_emit
        if _GAME_STATE_MARKER in buffer:
            return
    if buffer and _GAME_STATE_MARKER not in buffer:
        yield buffer


async def process_batch(
    conn: aiosqlite.Connection,
    batch: ActionBatch,
) -> None:
    """
    Full pipeline:
    1. Build the 4-layer context
    2. Select model and billing
    3. Call the LLM (streaming)
    4. Parse the response
    5. Apply the state delta
    6. Broadcast events
    7. Save to history
    """
    logger.info("Processing batch #%d with %d actions", batch.turn_number, len(batch.actions))
    batch_started_at = time.perf_counter()
    log_flow(
        logger,
        "batch_processing_started",
        turn_number=batch.turn_number,
        actions_count=len(batch.actions),
        players=[action.player_name for action in batch.actions],
    )

    thinking_task = asyncio.create_task(_thinking_timeout(cm.manager))

    try:
        current_tension = await _get_tension_level(conn)
        context = await build_context(conn, batch, tension_level=current_tension)
        billing = None if local_llm.is_local_only() else await _resolve_billing(conn, batch)
        user_message = _format_batch_as_user_message(batch)
        party_size = await _get_party_size(conn, batch)
        messages = await _build_messages(conn, context, user_message, batch, party_size)

        thinking_task.cancel()

        full_response, _ = await _stream_llm(billing, messages)
        await cm.manager.broadcast({"type": WSMessageType.STREAM_END})
        gm_response = _parse_gm_response(full_response)

        # 6. Aplica deltas e emite eventos
        await _apply_deltas_and_events(conn, gm_response, batch)
        await _update_cooperative_mission_progress(conn, batch)
        await _advance_travel_if_active(conn)

        # 7. Save history
        await state_manager.append_history(
            conn,
            history_id=str(uuid.uuid4()),
            turn_number=batch.turn_number,
            role="user",
            content=user_message,
        )
        await state_manager.append_history(
            conn,
            history_id=str(uuid.uuid4()),
            turn_number=batch.turn_number,
            role="assistant",
            content=_extract_narrative_only(full_response),
        )
        await memory_manager.update_memory_after_turn(conn, batch, gm_response)
        log_flow(
            logger,
            "batch_processing_completed",
            turn_number=batch.turn_number,
            duration_ms=round((time.perf_counter() - batch_started_at) * 1000, 2),
            dice_rolls=len(gm_response.dice_rolls),
            state_delta_players=len(gm_response.state_delta),
            events=len(gm_response.game_events),
            tension_level=gm_response.tension_level,
        )

    except asyncio.CancelledError:
        raise
    except Exception as e:
        logger.exception("Error while processing batch: %s", e)
        await cm.manager.broadcast({
            "type": WSMessageType.ERROR,
            "message": "Internal GM error. Please try again.",
        })
    finally:
        thinking_task.cancel()


async def _thinking_timeout(manager: cm.ConnectionManager) -> None:
    """Send a GM thinking message after 15 seconds without a response."""
    await asyncio.sleep(15)
    await manager.broadcast_gm_thinking()


# ---------------------------------------------------------------------------
# Formatting and parsing
# ---------------------------------------------------------------------------

def _format_batch_as_user_message(batch: ActionBatch) -> str:
    """Convert an action batch into a user message for the LLM."""
    lines = [f"[Turn {batch.turn_number}]"]
    for action in batch.actions:
        lines.append(f"**{action.player_name}**: {action.action_text}")
    return "\n".join(lines)


def _parse_gm_response(full_response: str) -> GMResponse:
    """
    Parse the GM response by extracting JSON from the <game_state> tag.
    Defensive fallback - returns a default GMResponse if parsing fails.
    """
    narrative = _extract_narrative_only(full_response)

    # Try to extract JSON from the <game_state> tag
    match = re.search(
        r"<game_state>\s*([\s\S]*?)\s*</game_state>",
        full_response,
    )

    if not match:
        logger.warning("GM response missing structured <game_state>")
        return GMResponse(narrative=narrative)

    try:
        data: dict[str, Any] = json.loads(match.group(1))
        response = GMResponse(
            narrative=narrative,
            dice_rolls=data.get("dice_rolls", []),
            state_delta=data.get("state_delta", {}),
            game_events=data.get("game_events", []),
            tension_level=int(data.get("tension_level", 5)),
            audio_cue=data.get("audio_cue"),
            image_prompt=data.get("next_scene_query"),
        )
        log_debug(
            logger,
            "gm_response_parsed",
            narrative_chars=len(response.narrative),
            dice_rolls=len(response.dice_rolls),
            state_delta_players=len(response.state_delta),
            events=len(response.game_events),
            tension_level=response.tension_level,
        )
        return response
    except ValueError as e:
        logger.warning("Failed to parse <game_state>: %s", e)
        return GMResponse(narrative=narrative)


def _extract_narrative_only(full_response: str) -> str:
    """Remove the <game_state> tag from the response, leaving only the narrative."""
    return re.sub(
        r"\s*<game_state>.*?</game_state>\s*",
        "",
        full_response,
        flags=re.DOTALL,
    ).strip()


async def _get_tension_level(conn: aiosqlite.Connection) -> int:
    tension_str = await state_manager.get_world_state(conn, "tension_level") or "5"
    try:
        return int(tension_str)
    except ValueError:
        return 5


async def _apply_deltas_and_events(
    conn: aiosqlite.Connection,
    gm_response: GMResponse,
    batch: ActionBatch | None = None,
) -> None:
    """Apply state deltas and emit game events."""
    log_debug(
        logger,
        "batch_apply_start",
        dice_rolls=len(gm_response.dice_rolls),
        state_delta=summarize_payload(gm_response.state_delta),
        events=summarize_payload(gm_response.game_events),
    )
    # Dice roll data - enrich with is_critical and is_fumble
    for roll in gm_response.dice_rolls:
        die = int(roll.get("die", 20))
        result = int(roll.get("result", 0))
        enriched = {
            **roll,
            "is_critical": result == die,
            "is_fumble": result == 1,
        }
        await cm.manager.broadcast_dice_roll(enriched)
        await asyncio.sleep(0.1)  # brief pause for frontend animation
        log_debug(logger, "dice_roll_emitted", roll=summarize_payload(enriched))

    # Per-player state deltas - apply to the DB and notify the frontend
    if gm_response.state_delta:
        for player_id, delta in gm_response.state_delta.items():
            await state_manager.apply_state_delta(conn, player_id, delta)
            log_debug(
                logger,
                "state_delta_applied",
                player_id=player_id,
                delta=summarize_payload(delta),
            )
            await _maybe_emit_progression_events(conn, player_id)
            # Apply faction reputation deltas when present
            from .reputation_gates import check_reputation_gates
            for rep_delta in delta.get("reputation_delta", []):
                faction_id = rep_delta.get("faction_id")
                change = rep_delta.get("delta", 0)
                if faction_id and change:
                    current_rep = await state_manager.get_faction_reputation(conn, player_id)
                    old_score = current_rep.get(faction_id, 0)
                    new_score = await state_manager.update_faction_reputation(
                        conn, player_id, faction_id, change
                    )
                    await cm.manager.broadcast_game_event(
                        "REPUTATION_CHANGE",
                        {
                            "type": "REPUTATION_CHANGE",
                            "player_id": player_id,
                            "faction_id": faction_id,
                            "delta": change,
                            "new_score": new_score,
                        },
                    )
                    # Check and fire reputation gates
                    gate_events = await check_reputation_gates(
                        conn, player_id, faction_id, new_score, old_score
                    )
                    for gate_event in gate_events:
                        await cm.manager.broadcast_game_event(
                            "REPUTATION_GATE_UNLOCKED", gate_event
                        )
        await cm.manager.broadcast({
            "type": WSMessageType.STATE_UPDATE,
            "delta": gm_response.state_delta,
        })

    await state_manager.set_world_state(
        conn,
        "tension_level",
        str(gm_response.tension_level),
    )

    # Game events
    for event in gm_response.game_events:
        event_type = event.get("type", "")
        await cm.manager.broadcast_game_event(event_type, event)

    # Audio cue
    if gm_response.audio_cue:
        await cm.manager.broadcast({
            "type": WSMessageType.AUDIO_CUE,
            "cue": gm_response.audio_cue,
        })

    if batch:
        await _track_secret_objective_progress(conn, batch, gm_response)


async def _maybe_emit_progression_events(
    conn: aiosqlite.Connection,
    player_id: str,
) -> None:
    player = await state_manager.get_player_by_id(conn, player_id)
    if player is None:
        return

    level = int(player["level"] or 1)
    if level < 5 or level % 5 != 0:
        return

    player_name = player["name"] or "Player"
    inferred_class = (player["inferred_class"] or "Adventurer").strip()

    # Every 5 levels: emit ABILITY_UNLOCK as signal for GM to award organic power
    ability_lock_key = f"ability_unlock:{player_id}:{level}"
    already_unlocked = await state_manager.get_quest_flag(conn, ability_lock_key)
    if already_unlocked != "1":
        await state_manager.set_quest_flag(conn, ability_lock_key, "1")
        await cm.manager.broadcast_game_event(
            "ABILITY_UNLOCK",
            {
                "type": "ABILITY_UNLOCK",
                "player_id": player_id,
                "player_name": player_name,
                "level": level,
                "inferred_class": inferred_class,
            },
        )

    # Every 25 levels: formal class mutation
    if level % 25 != 0:
        return

    mutation_lock_key = f"class_mutation:{player_id}:{level}"
    already_mutated = await state_manager.get_quest_flag(conn, mutation_lock_key)
    if already_mutated == "1":
        return

    from .behavior_trajectory import get_mutation_name

    old_class = inferred_class
    new_class = await get_mutation_name(conn, player_id, old_class)
    if new_class == old_class:
        await state_manager.set_quest_flag(conn, mutation_lock_key, "1")
        return

    await state_manager.set_player_inferred_class(conn, player_id, new_class)
    await state_manager.set_quest_flag(conn, mutation_lock_key, "1")
    await cm.manager.broadcast_game_event(
        "CLASS_MUTATION",
        {
            "type": "CLASS_MUTATION",
            "player_id": player_id,
            "player_name": player_name,
            "old_class": old_class,
            "new_class": new_class,
            "level": level,
        },
    )


def _mutated_class_name(old_class: str) -> str:
    base = old_class.lower()
    mapping = {
        "mage": "Thread Archmage",
        "warrior": "Steel Warden",
        "rogue": "Vector Shade",
        "cleric": "Ash Hierophant",
        "ranger": "Ruin Hunter",
        "paladin": "Paladin of the Eternal Flame",
        "soldier": "Commander of Valdrek",
        "arcanist": "Ascendant Arcanist",
        "thread weaver": "Primordial Weaver",
        "adventurer": "Ascended Traveler",
    }
    return mapping.get(base, f"Ascended {old_class}")


async def _advance_travel_if_active(conn: aiosqlite.Connection) -> None:
    """Advance one travel day per GM turn and emit an event on arrival."""
    state = await travel_manager.get_travel_state(conn)
    if not state.get("active"):
        return

    result = await travel_manager.advance_travel_day(conn)
    if result.get("arrived"):
        await cm.manager.broadcast_game_event(
            "TRAVEL_ARRIVED",
            {
                "type": "TRAVEL_ARRIVED",
                "destination": result["destination"],
                "destination_name": result["destination_name"],
            },
        )
        log_flow(logger, "travel_arrived", destination=result["destination"])
    else:
        encounter = travel_manager.roll_encounter(
            result.get("terrain", "wilderness"),
            tension=int((await state_manager.get_world_state(conn, "tension_level")) or "5"),
        )
        if encounter["triggered"]:
            await cm.manager.broadcast_game_event(
                "TRAVEL_ENCOUNTER",
                {
                    "type": "TRAVEL_ENCOUNTER",
                    "day": result["day_current"],
                    "terrain": result["terrain"],
                    "roll": encounter["roll"],
                    "encounter": encounter["encounter"],
                },
            )
            log_flow(logger, "travel_encounter_triggered",
                     day=result["day_current"], roll=encounter["roll"])
        else:
            log_debug(logger, "travel_day_safe",
                      day=result["day_current"], roll=encounter["roll"])


async def _track_secret_objective_progress(
    conn: aiosqlite.Connection,
    batch: ActionBatch,
    gm_response: GMResponse,
) -> None:
    unique_player_ids = list(dict.fromkeys(action.player_id for action in batch.actions))
    for player_id in unique_player_ids:
        player = await state_manager.get_player_by_id(conn, player_id)
        if not _has_secret_objective(player):
            continue

        secret_objective = str(player["secret_objective"]).strip()
        progress_key = f"secret_objective_progress:{player_id}"
        stage_key = f"secret_objective_hint_stage:{player_id}"

        progress, stage = await _load_secret_progress_state(conn, progress_key, stage_key)
        progress = _compute_secret_progress(progress, gm_response, player_id)
        await state_manager.set_quest_flag(conn, progress_key, str(progress))
        stage = await _emit_due_secret_hints(player, secret_objective, progress, stage)
        await state_manager.set_quest_flag(conn, stage_key, str(stage))


def _has_secret_objective(player: aiosqlite.Row | None) -> bool:
    if player is None:
        return False
    return bool((player["secret_objective"] or "").strip())


async def _load_secret_progress_state(
    conn: aiosqlite.Connection,
    progress_key: str,
    stage_key: str,
) -> tuple[int, int]:
    progress_raw = await state_manager.get_quest_flag(conn, progress_key)
    stage_raw = await state_manager.get_quest_flag(conn, stage_key)
    progress = int(progress_raw) if progress_raw and progress_raw.isdigit() else 0
    stage = int(stage_raw) if stage_raw and stage_raw.isdigit() else 0
    return progress, stage


def _compute_secret_progress(progress: int, gm_response: GMResponse, player_id: str) -> int:
    delta = gm_response.state_delta.get(player_id, {}) if gm_response.state_delta else {}
    bonus = 5 if int(delta.get("experience_gain", 0)) > 0 else 0
    return min(100, progress + 10 + bonus)


async def _emit_due_secret_hints(
    player: aiosqlite.Row,
    secret_objective: str,
    progress: int,
    stage: int,
) -> int:
    for idx, threshold in enumerate([30, 60, 90], start=1):
        if progress < threshold or stage >= idx:
            continue
        hint = await _generate_secret_hint(player, secret_objective, idx)
        await cm.manager.broadcast_game_event(
            "FACTION_CONFLICT",
            {
                "type": "FACTION_CONFLICT",
                "faction": player["faction"],
                "hint": hint,
            },
        )
        stage = idx
    return stage


async def _update_cooperative_mission_progress(
    conn: aiosqlite.Connection,
    batch: ActionBatch,
) -> None:
    await state_manager.initialize_or_refresh_cooperative_mission(conn)
    unique_players = list(dict.fromkeys(action.player_id for action in batch.actions))
    mission_state: dict[str, str] = await state_manager.get_cooperative_mission_state(conn)
    for player_id in unique_players:
        mission_state = await state_manager.mark_cooperative_mission_participation(conn, player_id)

    required = int(mission_state.get("cooperative_mission_required_players", "0") or 0)
    completed = int(mission_state.get("cooperative_mission_completed_players", "0") or 0)
    progress_percent = round((completed / required) * 100, 2) if required > 0 else 100.0
    payload = {
        "type": "COOP_MISSION",
        "active": mission_state.get("cooperative_mission_active", "0") == "1",
        "completed": mission_state.get("cooperative_mission_completed", "0") == "1",
        "blocking": mission_state.get("cooperative_mission_blocking", "0") == "1",
        "required_players": required,
        "completed_players": completed,
        "progress_percent": progress_percent,
        "objective": mission_state.get(
            "cooperative_mission_objective",
            state_manager.COOP_MISSION_OBJECTIVE_DEFAULT,
        ),
    }
    await cm.manager.broadcast_game_event("COOP_MISSION", payload)


async def _generate_secret_hint(player: aiosqlite.Row, secret_objective: str, stage: int) -> str:
    system_prompt = (
        "You create gradual and indirect hints for a secret RPG objective. "
        "Respond in one short sentence without revealing the objective explicitly."
    )
    user_prompt = (
        f"Faction: {player['faction']}\n"
        f"Secret objective: {secret_objective}\n"
        f"Hint stage: {stage}/3\n"
        "Generate the hint now."
    )
    model = os.getenv("AERUS_OLLAMA_HINT_MODEL", "phi4:14b")
    try:
        text = await local_llm.generate_text(
            system_prompt,
            user_prompt,
            max_tokens=80,
            model_override=model,
        )
        hint = text.strip()
        if hint:
            return hint
    except Exception:
        pass

    fallback_hints = {
        1: "Subtle signs suggest that old alliances conceal an unpaid debt.",
        2: "The right pieces are beginning to move, but watchful eyes still track every step.",
        3: "The moment to act in silence is approaching; one mistake could expose everything.",
    }
    return fallback_hints.get(stage, fallback_hints[1])


# ---------------------------------------------------------------------------
# Isekai convocation
# ---------------------------------------------------------------------------

async def generate_isekai_convocation(
    _conn: aiosqlite.Connection,
    _player_id: str,
    player_name: str,
    race: str,
    faction: str,
    backstory: str,
) -> str:
    """
    Generate a personalized convocation narrative for Aerus.
    Called once during character creation.
    """
    faction_config = _get_faction_prompt(faction)

    system = (
        "You are the narrator of an Aerus RPG convocation. "
        "Create an epic and personalized convocation narrative in English (max 300 words). "
        "Tone: mysterious, heavy, inevitable. Mention the Dome of Factions and the Primordial Thread."
    )

    user = (
        f"Summoned character:\n"
        f"Name: {player_name}\n"
        f"Race: {race}\n"
        f"Faction: {faction_config}\n"
        f"Backstory: {backstory[:500]}\n\n"
        "Generate this character's convocation narrative into Aerus."
    )

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]

    if local_llm.is_local_only():
        model = os.getenv("AERUS_OLLAMA_CONVOCATION_MODEL", os.getenv("AERUS_OLLAMA_HINT_MODEL", "phi4:14b"))
        return await local_llm.generate_chat(messages, max_tokens=600, model_override=model)

    return await local_llm._generate_chat_with_openrouter(messages, max_tokens=600)


def _get_faction_prompt(faction_id: str) -> str:
    faction_names = {
        "church_pure_flame": "Church of the Pure Flame (Sanctum)",
        "empire_valdrek": "Empire of Valdrek (Auramveld)",
        "guild_of_threads": "Guild of Threads (Vel'Ossian)",
        "children_of_broken_thread": "Children of the Broken Thread",
    }
    return faction_names.get(faction_id, faction_id)




