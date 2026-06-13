"""
game_master.py - Central orchestrator. The only module that calls OpenRouter.
Responsibilities: action batching, context assembly, LLM calls,
response parsing, delta application, and event broadcasting.
"""
from __future__ import annotations

import asyncio
import inspect
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
from . import hosted_narrator
from .application.billing.billing_router import select_billing_config
from .context_builder import build_context, build_gm_system_prompt, build_slm_system_prompt
from .infrastructure.config.config_loader import get_campaign_value as _get_campaign_value
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
        player_output_targets=[
            (action.player_id, action.player_name or f"Player {idx + 1}")
            for idx, action in enumerate(batch.actions)
        ],
        language=_get_campaign_value("campaign.language") or "en",
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


# ---------------------------------------------------------------------------
# B1 — SLM narrative path
# ---------------------------------------------------------------------------

def _build_slm_messages(
    context: Any,
    user_message: str,
    tension_level: int,
    language: str,
    history: list[dict],
) -> list[dict[str, str]]:
    """Build lean messages for the SLM (narrative only, no game_state rules)."""
    loc_match = re.match(r"Current location:\s*(.+)", context.l2_state or "")
    location = loc_match.group(1).strip() if loc_match else "Aerus"
    system = build_slm_system_prompt(location, tension_level, language)
    messages: list[dict[str, str]] = [{"role": "system", "content": system}]
    # Include last 4 history entries for narrative continuity
    for h in history[-4:]:
        messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": user_message})
    return messages


async def _stream_slm_narrative(
    billing: Any,
    messages: list[dict[str, str]],
) -> tuple[str, str]:
    """B1: stream narrative from SLM. Returns (full_text, streamed_text)."""
    started_at = time.perf_counter()
    client = AsyncOpenAI(api_key=billing.api_key, base_url=billing.base_url)
    collector: list[str] = []

    log_flow(logger, "slm_narrative_start", model=billing.model, message_count=len(messages))

    stream = await client.chat.completions.create(
        model=billing.model,
        messages=messages,
        stream=True,
        max_tokens=400,
    )

    async def _clean_tokens() -> AsyncIterator[str]:
        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if not delta:
                continue
            collector.append(delta)
            yield _sanitize_narrative_text(delta)

    narrative = await cm.manager.broadcast_stream(_clean_tokens())
    full_text = _sanitize_narrative_text("".join(collector))
    log_flow(
        logger,
        "slm_narrative_complete",
        model=billing.model,
        duration_ms=round((time.perf_counter() - started_at) * 1000, 2),
        narrative_chars=len(full_text),
    )
    return full_text, narrative


async def _extract_game_state_b1(
    conn: aiosqlite.Connection,
    narrative: str,
    batch: ActionBatch,
    context: Any,
    current_tension: int,
    valid_player_ids: list[str],
) -> "GMResponse":
    """B1: extract structured game_state from narrative via extractor model.

    Always uses AERUS_OLLAMA_EXTRACTOR_MODEL (Ollama) — never routes through
    billing_router / SLM, because the SLM is trained for prose, not JSON.
    """
    player_list = "\n".join(
        f"- {a.player_id} => {a.player_name}" for a in batch.actions
    )
    actions = "\n".join(f"**{a.player_name}**: {a.action_text}" for a in batch.actions)

    system_prompt = (
        "You are a game-state extractor for Aerus RPG.\n"
        "Given a narrative and player actions, output ONLY valid JSON — no markdown, no extra text.\n\n"
        "Schema:\n"
        "{\n"
        '  "dice_rolls": [],\n'
        '  "state_delta": {"<player_id>": {"hp_change": 0, "mp_change": 0, "stamina_change": 0,\n'
        '    "experience_gain": 0, "inventory_add": [], "inventory_remove": [],\n'
        '    "conditions_add": [], "conditions_remove": []}},\n'
        '  "game_events": [],\n'
        '  "tension_level": 5,\n'
        '  "audio_cue": "ambient_calm",\n'
        '  "next_scene_query": "max 12 words, no question mark"\n'
        "}\n\n"
        "Use exact player_id values as keys in state_delta:\n"
        f"{player_list}"
    )
    user_prompt = (
        f"PLAYER ACTIONS (Turn {batch.turn_number}):\n{actions}\n\n"
        f"NARRATIVE:\n{narrative}\n\n"
        f"CURRENT STATE:\n{(context.l2_state or '')[:1200]}"
    )

    extractor_model = os.getenv("AERUS_OLLAMA_EXTRACTOR_MODEL", "qwen2.5:14b-instruct")
    try:
        raw = await local_llm.generate_text(
            system_prompt,
            user_prompt,
            max_tokens=800,
            model_override=extractor_model,  # forces Ollama path, never SLM
        )
        json_match = re.search(r"\{[\s\S]*\}", raw)
        json_text = json_match.group(0) if json_match else raw
        repaired = _repair_json_candidate(json_text)
        data: dict[str, Any] = json.loads(repaired)

        next_scene_query = _normalize_next_scene_query(data.get("next_scene_query"), narrative)
        response = GMResponse(
            narrative=narrative,
            dice_rolls=data.get("dice_rolls", []),
            state_delta=data.get("state_delta", {}),
            game_events=_normalize_game_events(data.get("game_events", [])),
            tension_level=int(data.get("tension_level", current_tension)),
            audio_cue=data.get("audio_cue"),
            image_prompt=next_scene_query,
        )
        log_debug(
            logger,
            "b1_game_state_extracted",
            dice_rolls=len(response.dice_rolls),
            state_delta_players=len(response.state_delta) if isinstance(response.state_delta, dict) else 0,
            events=len(response.game_events),
            tension_level=response.tension_level,
        )
        response = _reconcile_response_player_ids(response, valid_player_ids)
        return _apply_response_guardrails(response)
    except Exception as exc:
        logger.warning("B1 game_state extraction failed: %s — returning narrative-only response", exc)
        return GMResponse(narrative=narrative, tension_level=current_tension)


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

# Some model responses omit the opening <game_state> tag and jump straight
# into the JSON payload. Use stable keys as a secondary stop condition.
_JSON_STOP_MARKERS = ('"dice_rolls"', '"state_delta"')


def _json_stop_position(buffer: str) -> int | None:
    for marker in _JSON_STOP_MARKERS:
        idx = buffer.find(marker)
        if idx != -1:
            brace = buffer.rfind("{", 0, idx)
            return brace if brace != -1 else idx
    return None


def _sanitize_narrative_text(text: str) -> str:
    # Hard ban of em dash in output and persisted narrative.
    return (text or "").replace("\u2014", "-")


def _flush_buffer(buffer: str) -> tuple[str, str, bool]:
    """
    Checks whether the buffer contains a structured game_state block.
    Returns (to_emit, new_buffer, should_stop).
    """
    if _GAME_STATE_MARKER in buffer:
        return buffer[: buffer.index(_GAME_STATE_MARKER)], "", True
    stop_pos = _json_stop_position(buffer)
    if stop_pos is not None:
        return buffer[:stop_pos].rstrip(), "", True
    if len(buffer) > 50:
        return buffer[:-20], buffer[-20:], False
    return "", buffer, False


async def _tokens_from_stream(
    stream: Any, collector: list[str]
) -> AsyncIterator[str]:
    """Itera sobre o stream OpenAI, coleta a resposta completa e filtra <game_state>."""
    buffer = ""
    suppress_output = False
    async for chunk in stream:
        delta = chunk.choices[0].delta.content
        if not delta:
            continue
        collector.append(delta)
        if suppress_output:
            continue
        buffer += delta
        to_emit, buffer, should_stop = _flush_buffer(buffer)
        if to_emit:
            yield _sanitize_narrative_text(to_emit)
        if should_stop:
            suppress_output = True
            buffer = ""
    if buffer and not suppress_output:
        yield _sanitize_narrative_text(buffer)


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
        to_emit, buffer, should_stop = _flush_buffer(buffer)
        if to_emit:
            yield _sanitize_narrative_text(to_emit)
        if should_stop:
            return
    if buffer and _GAME_STATE_MARKER not in buffer and _json_stop_position(buffer) is None:
        yield _sanitize_narrative_text(buffer)


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
        valid_player_ids = [action.player_id for action in batch.actions]
        language = _get_campaign_value("campaign.language") or "en"

        if billing and billing.is_slm:
            # ── B1: SLM generates narrative, extractor builds game_state ──────
            history = await state_manager.get_recent_history(conn, limit=4)
            slm_messages = _build_slm_messages(
                context, user_message, current_tension, language, list(history)
            )
            thinking_task.cancel()
            full_response, _ = await _stream_slm_narrative(billing, slm_messages)
            await cm.manager.broadcast({"type": WSMessageType.STREAM_END})
            gm_response = await _extract_game_state_b1(
                conn, full_response, batch, context, current_tension, valid_player_ids
            )
        elif billing and billing.is_hosted_narrator:
            # ── Hosted frontier narrator + RAG + guardrail (see docs/GAP_ANALYSIS_NARRATOR.md) ──
            # Frontier model narrates (DeepSeek/Haiku); curated 794 examples are RAG;
            # a guardrail validates each output; the Ollama extractor builds game_state.
            thinking_task.cancel()
            loc_match = re.match(r"Current location:\s*(.+)", context.l2_state or "")
            location = loc_match.group(1).strip() if loc_match else "Aerus"
            player_name = batch.actions[0].player_name if batch.actions else "Jogador"
            player_names = [a.player_name for a in batch.actions]
            rag_examples = await vector_store.retrieve_narration_examples(user_message, n_results=3)
            result = await hosted_narrator.narrate(
                api_key=billing.api_key,
                base_url=billing.base_url,
                model=billing.model,
                user_message=user_message,
                rag_examples=rag_examples,
                location=location,
                tension=current_tension,
                language=language,
                player_name=player_name,
                player_names=player_names,
            )
            full_response = result["text"]

            async def _stream_once() -> AsyncIterator[str]:
                yield full_response

            await cm.manager.broadcast_stream(_stream_once())
            await cm.manager.broadcast({"type": WSMessageType.STREAM_END})
            gm_response = await _extract_game_state_b1(
                conn, full_response, batch, context, current_tension, valid_player_ids
            )
        else:
            # ── Standard path: full-context prompt → GM response with game_state
            messages = await _build_messages(conn, context, user_message, batch, party_size)
            thinking_task.cancel()
            full_response, _ = await _stream_llm(billing, messages)
            await cm.manager.broadcast({"type": WSMessageType.STREAM_END})
            gm_response = _parse_gm_response(
                full_response,
                current_tension=current_tension,
                valid_player_ids=valid_player_ids,
            )

        fallback_state, fallback_events = await _build_minimum_mechanics_fallback(
            conn,
            batch,
            gm_response.narrative,
        )
        gm_response.state_delta, merged_players = _merge_missing_fallback_state(
            gm_response.state_delta,
            fallback_state,
        )
        gm_response.game_events, merged_events = _merge_fallback_events(
            gm_response.game_events,
            fallback_events,
        )
        if merged_players or merged_events:
            log_flow(
                logger,
                "fallback_mechanics_merged",
                turn_number=batch.turn_number,
                players=merged_players,
                generated_events=merged_events,
            )

        await _inject_narrative_loot_if_missing(conn, batch, gm_response)

        # 6. Aplica deltas e emite eventos
        await _apply_deltas_and_events(conn, gm_response, batch)
        await _update_cooperative_mission_progress(conn, batch)
        await _advance_travel_if_active(conn)
        condition_results = await state_manager.process_condition_turn(conn, batch.turn_number)
        if condition_results:
            log_flow(
                logger,
                "condition_turn_processed",
                turn_number=batch.turn_number,
                affected_players=list(condition_results.keys()),
            )

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


def _normalize_runtime_id(raw_value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(raw_value or "").lower())


def _resolve_runtime_player_id(candidate: Any, valid_player_ids: list[str]) -> str | None:
    if not isinstance(candidate, str):
        return None
    cleaned = candidate.strip()
    if not cleaned:
        return None
    if cleaned in valid_player_ids:
        return cleaned

    normalized_candidate = _normalize_runtime_id(cleaned)
    if not normalized_candidate:
        return None

    by_norm = {_normalize_runtime_id(player_id): player_id for player_id in valid_player_ids}
    if normalized_candidate in by_norm:
        return by_norm[normalized_candidate]

    prefix_matches = [
        player_id
        for player_id in valid_player_ids
        if _normalize_runtime_id(player_id).startswith(normalized_candidate)
        or normalized_candidate.startswith(_normalize_runtime_id(player_id))
    ]
    if len(prefix_matches) == 1:
        return prefix_matches[0]

    if len(valid_player_ids) == 1 and len(normalized_candidate) >= 8:
        return valid_player_ids[0]
    return None


def _reconcile_response_player_ids(response: GMResponse, valid_player_ids: list[str] | None) -> GMResponse:
    if not valid_player_ids:
        return response

    state_delta = response.state_delta if isinstance(response.state_delta, dict) else {}
    normalized_delta: dict[str, Any] = {}
    for raw_player_id, delta in state_delta.items():
        resolved = _resolve_runtime_player_id(raw_player_id, valid_player_ids)
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
    response.state_delta = normalized_delta

    normalized_events: list[dict[str, Any]] = []
    for event in response.game_events:
        if not isinstance(event, dict):
            continue
        normalized_event = dict(event)
        resolved = _resolve_runtime_player_id(normalized_event.get("player_id"), valid_player_ids)
        if resolved:
            normalized_event["player_id"] = resolved
        normalized_events.append(normalized_event)
    response.game_events = normalized_events
    return response


def _parse_gm_response(full_response: str, current_tension: int = 5, valid_player_ids: list[str] | None = None) -> GMResponse:
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
        match = re.search(
            r"```game_state\s*([\s\S]*?)\s*```",
            full_response,
            re.IGNORECASE,
        )
    if not match:
        open_tag = re.search(r"<game_state>\s*", full_response, re.IGNORECASE)
        if open_tag:
            json_candidate = full_response[open_tag.end():]
            match = True
        else:
            fence_tag = re.search(r"```game_state\s*", full_response, re.IGNORECASE)
            if fence_tag:
                json_candidate = full_response[fence_tag.end():]
                match = True
            else:
                close_tag = re.search(r"</game_state>", full_response, re.IGNORECASE)
                if close_tag:
                    text_before = full_response[: close_tag.start()]
                    brace_idx = text_before.rfind("{")
                    if brace_idx != -1:
                        json_candidate = text_before[brace_idx:]
                        match = True
                        logger.warning(
                            "GM response missing <game_state> opening tag; recovered JSON from closing tag"
                        )
                    else:
                        json_candidate = ""
                else:
                    json_candidate = ""

    if not match:
        logger.warning("GM response missing structured <game_state>")
        return GMResponse(narrative=narrative)

    try:
        json_text = match.group(1) if hasattr(match, "group") else json_candidate
        repaired = _repair_json_candidate(json_text)
        repaired = re.sub(r"([:\[,]\s*)\+(\d)", r"\1\2", repaired)
        try:
            data: dict[str, Any] = json.loads(repaired)
        except json.JSONDecodeError:
            data = _salvage_partial_game_state(json_text)
            if not data:
                raise
        next_scene_query = _normalize_next_scene_query(data.get("next_scene_query"), narrative)
        response = GMResponse(
            narrative=narrative,
            dice_rolls=data.get("dice_rolls", []),
            state_delta=data.get("state_delta", {}),
            game_events=_normalize_game_events(data.get("game_events", [])),
            tension_level=int(data.get("tension_level", current_tension)),
            audio_cue=data.get("audio_cue"),
            image_prompt=next_scene_query,
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
        response = _reconcile_response_player_ids(response, valid_player_ids)
        return _apply_response_guardrails(response)
    except ValueError as e:
        logger.warning("Failed to parse <game_state>: %s", e)

        # Fallback: salvage structured keys from the full raw response,
        # not only the extracted <game_state> section.
        salvaged = _salvage_partial_game_state(full_response)
        if salvaged:
            try:
                next_scene_query = _normalize_next_scene_query(
                    salvaged.get("next_scene_query"), narrative
                )
                response = GMResponse(
                    narrative=narrative,
                    dice_rolls=salvaged.get("dice_rolls", []),
                    state_delta=salvaged.get("state_delta", {}),
                    game_events=_normalize_game_events(salvaged.get("game_events", [])),
                    tension_level=int(salvaged.get("tension_level", current_tension)),
                    audio_cue=salvaged.get("audio_cue"),
                    image_prompt=next_scene_query,
                )
                logger.warning(
                    "Recovered partial game_state from full response: dice_rolls=%s state_delta_players=%s events=%s",
                    len(response.dice_rolls),
                    len(response.state_delta) if isinstance(response.state_delta, dict) else 0,
                    len(response.game_events),
                )
                response = _reconcile_response_player_ids(response, valid_player_ids)
                return _apply_response_guardrails(response)
            except Exception as salvage_exc:
                logger.warning("Full-response salvage failed: %s", salvage_exc)

        return GMResponse(narrative=narrative)


def _extract_narrative_only(full_response: str) -> str:
    """Remove the <game_state> tag from the response, leaving only the narrative."""
    stripped = re.sub(
        r"\s*<game_state>.*?</game_state>\s*",
        "",
        full_response,
        flags=re.DOTALL,
    )
    stripped = re.sub(
        r"\s*```game_state.*?```\s*",
        "",
        stripped,
        flags=re.DOTALL | re.IGNORECASE,
    )
    stripped = re.sub(
        r"\s*<game_state>.*$",
        "",
        stripped,
        flags=re.DOTALL | re.IGNORECASE,
    )
    stripped = re.sub(
        r"\s*```game_state.*$",
        "",
        stripped,
        flags=re.DOTALL | re.IGNORECASE,
    )
    close_idx = stripped.find("</game_state>")
    if close_idx != -1:
        brace_idx = stripped.rfind("{", 0, close_idx)
        end_idx = close_idx + len("</game_state>")
        if brace_idx != -1:
            stripped = (stripped[:brace_idx] + stripped[end_idx:]).strip()
        else:
            stripped = stripped[:close_idx].strip()
    return _sanitize_narrative_text(stripped.strip())


def _merge_missing_fallback_state(
    current_state: dict[str, Any] | Any,
    fallback_state: dict[str, Any],
) -> tuple[dict[str, Any], int]:
    state = current_state if isinstance(current_state, dict) else {}
    merged_players = 0

    for player_id, fallback_delta in fallback_state.items():
        if not isinstance(fallback_delta, dict):
            continue

        current_delta = state.get(player_id)
        if not isinstance(current_delta, dict):
            state[player_id] = dict(fallback_delta)
            merged_players += 1
            continue

        changed = False

        if "skill_use" in fallback_delta and "skill_use" not in current_delta and "skill_delta" not in current_delta:
            current_delta["skill_use"] = fallback_delta["skill_use"]
            changed = True

        for key in ("hp_change", "mp_change", "stamina_change", "experience_gain"):
            if key in fallback_delta and key not in current_delta:
                current_delta[key] = fallback_delta[key]
                changed = True

        if isinstance(fallback_delta.get("magic_proficiency_delta"), dict):
            current_magic = current_delta.get("magic_proficiency_delta")
            if not isinstance(current_magic, dict):
                current_magic = {}
            before = len(current_magic)
            for mk, mv in fallback_delta["magic_proficiency_delta"].items():
                if mk not in current_magic:
                    current_magic[mk] = mv
            if len(current_magic) > before:
                current_delta["magic_proficiency_delta"] = current_magic
                changed = True

        if isinstance(fallback_delta.get("inventory_add"), list):
            current_add = current_delta.get("inventory_add")
            if not isinstance(current_add, list):
                current_add = []
            existing_names = {
                str(item.get("name", "")).lower()
                for item in current_add
                if isinstance(item, dict)
            }
            before_len = len(current_add)
            for item in fallback_delta["inventory_add"]:
                if not isinstance(item, dict):
                    continue
                name = str(item.get("name", "")).lower()
                if name and name not in existing_names:
                    current_add.append(item)
                    existing_names.add(name)
            if len(current_add) > before_len:
                current_delta["inventory_add"] = current_add
                changed = True

        if changed:
            state[player_id] = current_delta
            merged_players += 1

    return state, merged_players


def _merge_fallback_events(
    current_events: list[dict[str, Any]] | Any,
    fallback_events: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], int]:
    events = current_events if isinstance(current_events, list) else []
    merged = 0

    existing_loot_signatures: set[tuple[str, tuple[str, ...]]] = set()
    for event in events:
        if not isinstance(event, dict) or event.get("type") != "LOOT":
            continue
        pid = str(event.get("player_id", ""))
        names = tuple(
            sorted(
                str(item.get("name", ""))
                for item in event.get("items", [])
                if isinstance(item, dict)
            )
        )
        existing_loot_signatures.add((pid, names))

    for event in fallback_events:
        if not isinstance(event, dict):
            continue
        if event.get("type") == "LOOT":
            pid = str(event.get("player_id", ""))
            names = tuple(
                sorted(
                    str(item.get("name", ""))
                    for item in event.get("items", [])
                    if isinstance(item, dict)
                )
            )
            signature = (pid, names)
            if signature in existing_loot_signatures:
                continue
            existing_loot_signatures.add(signature)
        events.append(event)
        merged += 1

    return events, merged


def _normalize_next_scene_query(raw_query: Any, narrative: str) -> str | None:
    if isinstance(raw_query, str) and raw_query.strip():
        cleaned = re.sub(r"[?!.]+", "", raw_query).strip()
        cleaned = " ".join(cleaned.split()[:12])
        return cleaned or None
    fallback = _derive_next_scene_query(narrative)
    return fallback or None


def _narrative_has_healing_signal(narrative: str) -> bool:
    text = narrative.lower()
    healing_terms = (
        "heal", "healing", "mend", "mending", "wound closes", "wounds close",
        "wound knits", "knit shut", "stitches itself", "closed flesh",
        "closing flesh", "tratar feridas", "cura", "curativo", "bandage",
        "bandagem", "restaura feridas", "luz curativa", "magia curativa",
    )
    return any(term in text for term in healing_terms)


def _narrative_has_rest_signal(narrative: str) -> bool:
    text = narrative.lower()
    rest_terms = (
        "rest", "resting", "sleep", "sleeping", "nap", "bed", "inn", "room",
        "descans", "dorm", "cama", "quarto", "taverna", "estalagem", "fôlego", "folego",
    )
    return any(term in text for term in rest_terms)


def _narrative_has_combat_pressure(narrative: str) -> bool:
    text = narrative.lower()
    combat_terms = (
        "counterattack", "counter-attack", "claw", "strike", "slashes", "slash",
        "grazes", "wound", "blow", "impact", "hits", "hit", "retaliation",
        "retaliate", "snarl", "battle", "combat", "enemy",
    )
    return any(term in text for term in combat_terms)


def _apply_response_guardrails(response: GMResponse) -> GMResponse:
    if not response.state_delta:
        return response

    healing_visible = _narrative_has_healing_signal(response.narrative)
    rest_visible = _narrative_has_rest_signal(response.narrative)
    adjusted = False
    normalized_state: dict[str, Any] = {}
    has_negative_hp = False
    has_negative_stamina = False

    for player_id, delta in response.state_delta.items():
        if not isinstance(delta, dict):
            normalized_state[player_id] = delta
            continue

        updated = dict(delta)
        hp_change = updated.get("hp_change", 0)
        try:
            hp_change_int = int(hp_change)
        except (TypeError, ValueError):
            hp_change_int = 0

        stamina_change = updated.get("stamina_change", 0)
        try:
            stamina_change_int = int(stamina_change)
        except (TypeError, ValueError):
            stamina_change_int = 0

        if hp_change_int < 0:
            has_negative_hp = True
        if stamina_change_int < 0:
            has_negative_stamina = True

        if hp_change_int > 0 and not healing_visible and not (rest_visible and response.tension_level <= 5):
            updated["hp_change"] = 0
            adjusted = True
            logger.info(
                "GM guardrail removed positive hp_change without healing or safe-rest signal: player=%s original=%s",
                player_id,
                hp_change,
            )

        if rest_visible and response.tension_level >= 6:
            for recovery_key in ("hp_change", "mp_change", "stamina_change"):
                try:
                    recovery_val = int(updated.get(recovery_key, 0) or 0)
                except (TypeError, ValueError):
                    recovery_val = 0
                if recovery_val > 0:
                    updated[recovery_key] = 0
                    adjusted = True
                    logger.info(
                        "GM guardrail removed recovery during unsafe rest: player=%s key=%s original=%s tension=%s",
                        player_id,
                        recovery_key,
                        recovery_val,
                        response.tension_level,
                    )

        normalized_state[player_id] = updated

    if (
        not has_negative_hp
        and has_negative_stamina
        and not healing_visible
        and response.tension_level >= 5
        and bool(response.dice_rolls)
        and _narrative_has_combat_pressure(response.narrative)
    ):
        for pid, pdelta in normalized_state.items():
            if not isinstance(pdelta, dict):
                continue
            inferred_delta = dict(pdelta)
            inferred_delta["hp_change"] = min(int(inferred_delta.get("hp_change", 0) or 0), -5)
            normalized_state[pid] = inferred_delta
            adjusted = True
            logger.info(
                "GM guardrail inferred combat chip damage for active exchange: player=%s hp_change=%s",
                pid,
                inferred_delta["hp_change"],
            )

    if adjusted:
        response.state_delta = normalized_state
    return response


def _normalize_game_events(raw_events: Any) -> list[dict[str, Any]]:
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


def _derive_next_scene_query(narrative: str) -> str:
    text = re.sub(r"\s+", " ", narrative).strip()
    if not text:
        return ""
    sentences = [segment.strip(" .,!?:;\"'") for segment in re.split(r"[.!?]+", text) if segment.strip()]
    seed = sentences[-1] if sentences else text
    words = [word for word in re.findall(r"[A-Za-z0-9'_-]+", seed) if len(word) > 2]
    return " ".join(words[:12])


def _infer_skill_key_from_action(action_text: str) -> str:
    text = (action_text or "").lower()
    matchers: list[tuple[tuple[str, ...], str]] = [
        (("armadilha", "trap", "embosc", "rota de fuga"), "ambush"),
        (("escond", "sombra", "furtiv", "stealth", "ocult"), "conceal"),
        (("descans", "dorm", "medit", "concentr", "respirar", "fôlego", "folego"), "thread_sensing"),
        (("runa", "runic", "runework"), "runework"),
        (("selo", "seal", "selamento"), "seal_work"),
        (("ritual", "invoca", "invocar"), "thread_sensing"),
        (("magia", "feiti", "arcano", "thread", "vento", "fogo", "gelo", "raio"), "detect_magic"),
        (("vasculh", "buscar", "procur", "inspec", "exam", "search", "observar", "investig"), "search"),
        (("convencer", "persuad", "negoci", "interrog", "convers"), "persuasion"),
        (("combate", "atacar", "golpe", "duelo", "fight", "battle"), "weapon_flow"),
    ]
    for terms, skill_key in matchers:
        if any(term in text for term in terms):
            return skill_key
    return "search"


def _infer_skill_use_from_action(action_text: str) -> dict[str, float | str]:
    text = (action_text or "").lower()
    skill_key = _infer_skill_key_from_action(action_text)
    impact = 1.0 if text.strip() else 0.5

    precision_terms = (
        "concentr", "medit", "observar", "investig", "interrog", "negoci",
        "armadilha", "trap", "embosc", "planej", "rota de fuga", "prepar",
    )
    risk_terms = (
        "perigo", "risco", "a qualquer custo", "sombras", "inimig", "fuga",
        "persegui", "combate", "alerta", "ameaça",
    )

    if any(term in text for term in precision_terms):
        impact += 0.5
    if any(term in text for term in risk_terms):
        impact += 0.5

    if skill_key in {"ambush", "conceal", "thread_sensing"} and impact < 1.5:
        impact = 1.5

    return {"skill_key": skill_key, "impact": min(3.0, max(0.5, impact))}


def _infer_story_experience_gain(action_text: str, narrative: str, tension_level: int) -> int:
    text = (action_text or "").lower().strip()
    scene = (narrative or "").lower()
    combined = f"{text} {scene}"

    if not text:
        return 0

    story_terms = (
        "salv", "resgat", "descobr", "revel", "convenc", "negoci", "interrog",
        "investig", "infiltr", "proteg", "defeat", "ritual", "selo", "seal",
        "quest", "missão", "missao", "pista", "verdade", "truth", "libert",
    )
    danger_terms = (
        "inimig", "ameaça", "perigo", "combate", "duelo", "fight", "battle",
        "cult", "capit", "boss", "guarda", "prisone", "prisione",
    )
    progress_terms = (
        "muda o rumo", "próxima etapa", "proxima etapa", "next step", "avança",
        "advance", "objective", "objetivo", "progresso", "clue", "pista",
    )
    completion_terms = (
        "derrot", "vence", "triunf", "conquista", "fecha o ritual", "sela",
        "recupera o artefato", "salva", "liberta",
    )
    trivial_terms = (
        "ajeit", "casaco", "observo a chuva", "chuva", "respiro", "espero",
        "silêncio", "silencio", "fico parado", "olho em volta sem agir",
    )

    impact_score = 0
    if any(term in text for term in story_terms):
        impact_score += 2
    if any(term in combined for term in progress_terms):
        impact_score += 2
    if tension_level >= 6 or any(term in combined for term in danger_terms):
        impact_score += 1
    if any(term in combined for term in completion_terms):
        impact_score += 1

    if impact_score <= 0:
        if any(term in combined for term in trivial_terms):
            return 0
        purposeful_verbs = (
            "ataco", "confront", "vasculh", "explor", "persuad", "negoci", "investig",
            "proteg", "escapo", "fujo", "interrogo", "rastreio",
        )
        if any(term in text for term in purposeful_verbs):
            impact_score = 1
        else:
            return 0

    xp = 6 + (impact_score * 4)
    return max(0, min(24, xp))


def _condition_ids_matching(active_conditions: list[Any] | None, keywords: tuple[str, ...]) -> list[str]:
    matched: list[str] = []
    for cond in active_conditions or []:
        try:
            if isinstance(cond, dict):
                cond_id = str(cond.get("condition_id", ""))
                name = str(cond.get("name", "") or "").lower()
                desc = str(cond.get("description", "") or "").lower()
            else:
                cond_id = str(cond["condition_id"])
                name = str(cond["name"] or "").lower()
                desc = str(cond["description"] or "").lower()
        except Exception:
            continue
        if cond_id and any(keyword in name or keyword in desc for keyword in keywords):
            matched.append(cond_id)
    return matched


def _infer_healing_delta(
    action_text: str,
    narrative: str,
    tension_level: int,
    current_location: str = "",
    active_conditions: list[Any] | None = None,
) -> dict[str, Any]:
    text = (action_text or "").lower()
    scene = (narrative or "").lower()
    location = (current_location or "").lower()
    combined = f"{text} {scene} {location}"

    healing_terms = (
        "cura", "curar", "heal", "healing", "primeiros socorros", "first aid",
        "enfaixar", "bandage", "curativo", "tratar ferida", "tratamento",
        "poção", "pocao", "potion", "elixir", "antídoto", "antidoto", "salve",
        "purificar", "cleanse", "restoration", "restauração", "restauracao",
    )
    if not any(term in combined for term in healing_terms):
        return {}

    under_pressure = (
        tension_level >= 6
        or _narrative_has_combat_pressure(narrative)
        or any(term in combined for term in ("inimig", "ameaça", "passos", "persegui", "alarme"))
    )
    safe_place = any(
        term in combined
        for term in ("quarto", "cama", "estalagem", "taverna", "inn", "room", "bed", "camp", "abrigo", "santu", "temple")
    )
    quality_bonus = 2 if safe_place else 0
    pressure_penalty = 2 if under_pressure else 0

    delta: dict[str, Any] = {}

    if any(term in text for term in ("primeiros socorros", "first aid", "enfaixar", "bandage", "curativo", "tratar")):
        delta["hp_change"] = max(1, 4 + quality_bonus - pressure_penalty)
        delta["stamina_change"] = max(0, 1 + quality_bonus - pressure_penalty)
        remove_ids = _condition_ids_matching(active_conditions, ("bleed", "sangr", "burn", "queim", "fatigue", "exaust"))
        if remove_ids and not under_pressure:
            delta["conditions_remove"] = remove_ids

    if any(term in text for term in ("poção", "pocao", "potion", "elixir", "salve")):
        delta["hp_change"] = max(int(delta.get("hp_change", 0)), 6 + quality_bonus)
        if "antídoto" in text or "antidoto" in text:
            remove_ids = _condition_ids_matching(active_conditions, ("poison", "veneno", "toxic", "tox"))
            if remove_ids:
                current_remove = list(delta.get("conditions_remove", []))
                for cid in remove_ids:
                    if cid not in current_remove:
                        current_remove.append(cid)
                delta["conditions_remove"] = current_remove

    if _is_magic_intent(action_text) and any(term in text for term in ("cura", "heal", "divina", "restauração", "restauracao", "purificar", "cleanse")):
        delta["hp_change"] = max(int(delta.get("hp_change", 0)), 5 + quality_bonus)
        delta["mp_change"] = int(delta.get("mp_change", 0)) - 4
        remove_ids = _condition_ids_matching(active_conditions, ("bleed", "sangr", "burn", "queim", "poison", "veneno"))
        if remove_ids and not under_pressure:
            current_remove = list(delta.get("conditions_remove", []))
            for cid in remove_ids:
                if cid not in current_remove:
                    current_remove.append(cid)
            delta["conditions_remove"] = current_remove

    return delta


def _infer_rest_recovery(
    action_text: str,
    narrative: str,
    tension_level: int,
    current_location: str = "",
) -> dict[str, Any]:
    text = (action_text or "").lower()
    scene = (narrative or "").lower()
    location = (current_location or "").lower()
    combined = f"{text} {scene} {location}"

    if not any(term in text for term in ("descans", "dorm", "deitar", "sleep", "rest", "medit")):
        return {}

    premium_shelter = any(
        term in combined
        for term in ("cama", "quarto", "taverna", "estalagem", "inn", "room", "bed", "sanctuary", "temple", "port myr")
    )
    basic_shelter = premium_shelter or any(
        term in combined for term in ("camp", "fogueira", "tent", "abrigo", "shelter")
    )
    calm_scene = any(
        term in combined
        for term in ("quieto", "silêncio", "silencio", "porta fecha", "ninguém interrompe", "alone", "calmo", "seguro", "safe", "sem interrupções")
    )
    danger_present = (
        tension_level >= 6
        or _narrative_has_combat_pressure(narrative)
        or any(term in combined for term in ("persegui", "inimig", "ameaça", "grito", "passos", "alerta"))
    )

    if danger_present:
        return {}

    if not basic_shelter and not calm_scene and tension_level > 4:
        return {}

    meditative_focus = _is_magic_sensory_intent(action_text) or any(
        term in text for term in ("concentr", "medit", "vento", "thread", "mana", "foco")
    )
    full_sleep = any(term in text for term in ("dormir", "passar a noite", "pernoitar", "sleep through", "sono"))
    deep_rest = full_sleep or any(term in text for term in ("recuperar completamente", "restaurar completamente", "descansar mais"))

    quality = 2 if premium_shelter else 1 if basic_shelter or calm_scene else 0
    hp_gain = 2 + quality + (1 if deep_rest else 0)
    mp_gain = 2 + quality + (2 if meditative_focus else 0) + (1 if deep_rest else 0)
    stamina_gain = 4 + (quality * 2) + (2 if deep_rest else 0)

    if not premium_shelter:
        hp_gain = min(hp_gain, 3)
        mp_gain = min(mp_gain, 4)
        stamina_gain = min(stamina_gain, 6)

    return {
        "hp_change": max(1, hp_gain),
        "mp_change": max(1, mp_gain),
        "stamina_change": max(2, stamina_gain),
    }


def _is_magic_intent(action_text: str) -> bool:
    text = (action_text or "").lower()
    return bool(re.search(r"\b(magia|feiti|spell|arcano|vento|fogo|gelo|raio|ritual|thread|mana)\b", text))


def _is_magic_sensory_intent(action_text: str) -> bool:
    text = (action_text or "").lower()
    return bool(
        re.search(
            r"\b(sentir|detectar|perceber|rastrear|mapear|scan|sense|feel|presence|presenca|presença)\b",
            text,
        )
        and re.search(r"\b(vento|ar|wind|air|thread|magia|arcano|ritual)\b", text)
    )


def _has_magic_capability(row: aiosqlite.Row) -> bool:
    allowed_magic_seals = {"common", "trade", "high_flame", "conclave"}
    seal = str(row["flame_seal"] or "").lower()
    if seal in allowed_magic_seals:
        return True

    magic_prof = json.loads(row["magic_prof_json"] or "{}")
    if any(int(v or 0) > 0 for v in magic_prof.values()):
        return True

    skills = json.loads(row["skills_json"] or "{}")
    for key in ("detect_magic", "thread_sensing", "corruption_reading", "seal_work", "runework"):
        entry = skills.get(key)
        if isinstance(entry, dict) and int(entry.get("rank", 0) or 0) > 0:
            return True
    return False


def _infer_magic_element(action_text: str, narrative: str) -> str:
    text = f"{action_text} {narrative}".lower()
    if any(token in text for token in ("vento", "air", "wind")):
        return "air"
    if any(token in text for token in ("fogo", "fire", "flame")):
        return "fire"
    if any(token in text for token in ("agua", "água", "water", "ice", "gelo")):
        return "water"
    if any(token in text for token in ("terra", "earth", "stone", "rocha")):
        return "earth"
    if any(token in text for token in ("espirito", "espírito", "spirit", "alma")):
        return "spirit"
    return "energy"


def _extract_loot_from_narrative(
    action_text: str,
    narrative: str,
    player_id: str,
    existing_item_names: set[str] | None = None,
) -> list[dict[str, Any]]:
    action = (action_text or "").lower()
    text = (narrative or "").lower()
    existing = {name.lower() for name in (existing_item_names or set())}

    is_search_context = bool(
        re.search(r"(vasculh|saque|loot|search|revira|examina|inspec|buscar corpos)", action)
    )
    asks_for_weapon = bool(re.search(r"\b(arma|weapon|espada|sword)\b", action))

    def missing(name: str) -> bool:
        return name.lower() not in existing

    items: list[dict[str, Any]] = []

    # Weapon granted/requested in narrative context.
    if asks_for_weapon and any(token in text for token in ("espada curta", "short sword", "espada")) and missing("Short Sword"):
        items.append({
            "item_id": f"{player_id}-short-sword-{uuid.uuid4().hex[:8]}",
            "name": "Short Sword",
            "description": "A reliable short blade for close combat.",
            "rarity": "common",
            "quantity": 1,
            "equipped": False,
        })

    # Search/recovery context: documents and marked artifacts.
    if is_search_context:
        if any(token in text for token in ("anel", "ring")) and missing("Traveler Mark Ring"):
            items.append({
                "item_id": f"{player_id}-traveler-ring-{uuid.uuid4().hex[:8]}",
                "name": "Traveler Mark Ring",
                "description": "Recovered during field search.",
                "rarity": "rare",
                "quantity": 1,
                "equipped": False,
            })
        if any(token in text for token in ("pergaminho", "scroll")) and missing("Sealed Scroll"):
            items.append({
                "item_id": f"{player_id}-sealed-scroll-{uuid.uuid4().hex[:8]}",
                "name": "Sealed Scroll",
                "description": "Recovered during field search.",
                "rarity": "rare",
                "quantity": 1,
                "equipped": False,
            })
        if any(token in text for token in ("medalh", "medallion", "medalhao", "medalhão")) and missing("Traveler Mark Medallion"):
            items.append({
                "item_id": f"{player_id}-traveler-medallion-{uuid.uuid4().hex[:8]}",
                "name": "Traveler Mark Medallion",
                "description": "Recovered during field search.",
                "rarity": "rare",
                "quantity": 1,
                "equipped": False,
            })
        if any(token in text for token in ("mapa", "map", "carta", "document")) and missing("Investigative Documents"):
            items.append({
                "item_id": f"{player_id}-investigative-docs-{uuid.uuid4().hex[:8]}",
                "name": "Investigative Documents",
                "description": "Notes, fragments, and routes tied to the Traveler Mark.",
                "rarity": "common",
                "quantity": 1,
                "equipped": False,
            })

    return items[:3]


async def _inject_narrative_loot_if_missing(
    conn: aiosqlite.Connection,
    batch: ActionBatch,
    gm_response: GMResponse,
) -> None:
    if not batch.actions:
        return

    if not isinstance(gm_response.state_delta, dict):
        gm_response.state_delta = {}
    if not isinstance(gm_response.game_events, list):
        gm_response.game_events = []

    for action in batch.actions:
        player_id = action.player_id
        player_row = await state_manager.get_player_by_id(conn, player_id)
        if player_row is None:
            continue

        inventory_rows = await state_manager.get_player_inventory(conn, player_id)
        existing_names = {str(item["name"] or "") for item in inventory_rows}

        inferred_items = _extract_loot_from_narrative(
            action.action_text,
            gm_response.narrative,
            player_id,
            existing_item_names=existing_names,
        )
        if not inferred_items:
            continue

        player_delta = gm_response.state_delta.get(player_id)
        if not isinstance(player_delta, dict):
            player_delta = {}

        current_add = player_delta.get("inventory_add", [])
        if not isinstance(current_add, list):
            current_add = []
        current_names = {
            str(item.get("name", "")).lower()
            for item in current_add
            if isinstance(item, dict)
        }
        for item in inferred_items:
            if item["name"].lower() not in current_names:
                current_add.append(item)

        if not current_add:
            continue

        player_delta["inventory_add"] = current_add
        gm_response.state_delta[player_id] = player_delta

        gm_response.game_events.append(
            {
                "type": "LOOT",
                "player_id": player_id,
                "player_name": action.player_name,
                "items": inferred_items,
            }
        )

        log_flow(
            logger,
            "narrative_loot_injected",
            player_id=player_id,
            player_name=action.player_name,
            items=[item["name"] for item in inferred_items],
        )


def _merge_delta_resources(target: dict[str, Any], patch: dict[str, Any]) -> None:
    for key, value in patch.items():
        if key in {"hp_change", "mp_change", "stamina_change", "experience_gain"}:
            target[key] = int(target.get(key, 0) or 0) + int(value or 0)
        elif key in {"conditions_remove", "inventory_remove"}:
            current = list(target.get(key, []))
            for item in value or []:
                if item not in current:
                    current.append(item)
            target[key] = current
        elif key in {"conditions_add", "inventory_add"}:
            current = list(target.get(key, []))
            current.extend(value or [])
            target[key] = current
        else:
            target[key] = value


async def _build_minimum_mechanics_fallback(
    conn: aiosqlite.Connection,
    batch: ActionBatch,
    narrative: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    state_delta: dict[str, Any] = {}
    fallback_events: list[dict[str, Any]] = []
    current_tension = await _get_tension_level(conn)
    current_location = (
        await state_manager.get_world_state(conn, "current_location")
        or state_manager.DEFAULT_START_LOCATION
    )

    for action in batch.actions:
        row = await state_manager.get_player_by_id(conn, action.player_id)
        if row is None:
            continue

        delta: dict[str, Any] = {}
        action_text = action.action_text or ""
        active_conditions = await state_manager.get_player_conditions(conn, action.player_id)

        delta["skill_use"] = _infer_skill_use_from_action(action_text)

        story_xp = _infer_story_experience_gain(action_text, narrative, current_tension)
        if story_xp > 0:
            delta["experience_gain"] = int(delta.get("experience_gain", 0) or 0) + story_xp
            log_flow(
                logger,
                "story_xp_inferred",
                player_id=action.player_id,
                player_name=action.player_name,
                experience_gain=story_xp,
            )

        rest_delta = _infer_rest_recovery(
            action_text,
            narrative,
            current_tension,
            current_location=current_location,
        )
        if rest_delta:
            _merge_delta_resources(delta, rest_delta)
            log_flow(
                logger,
                "rest_recovery_inferred",
                player_id=action.player_id,
                player_name=action.player_name,
                recovery=rest_delta,
                tension=current_tension,
                location=current_location,
            )

        healing_delta = _infer_healing_delta(
            action_text,
            narrative,
            current_tension,
            current_location=current_location,
            active_conditions=active_conditions,
        )
        if healing_delta:
            _merge_delta_resources(delta, healing_delta)
            log_flow(
                logger,
                "healing_delta_inferred",
                player_id=action.player_id,
                player_name=action.player_name,
                recovery=healing_delta,
                tension=current_tension,
                location=current_location,
            )

        if _is_magic_intent(action_text):
            seal = str(row["flame_seal"] or "").lower()
            magic_prof = json.loads(row["magic_prof_json"] or "{}")
            can_cast = _has_magic_capability(row)
            sensory_intent = _is_magic_sensory_intent(action_text)

            if can_cast:
                # Sensory/channeling actions cost less than offensive casting.
                if sensory_intent:
                    delta["mp_change"] = int(delta.get("mp_change", 0) or 0) - 2
                    delta["skill_use"] = {
                        "skill_key": "thread_sensing",
                        "impact": 1.0,
                    }
                else:
                    delta["mp_change"] = int(delta.get("mp_change", 0) or 0) - 6
                    element = _infer_magic_element(action_text, narrative)
                    if int(magic_prof.get(element, 0)) < 1:
                        delta["magic_proficiency_delta"] = {element: 1}
            else:
                # Explicit backlash when action attempts magic without explicit capability.
                if sensory_intent:
                    # Non-offensive sensing without capability: fatigue, but no direct self-harm.
                    delta["stamina_change"] = int(delta.get("stamina_change", 0) or 0) - 3
                    delta["mp_change"] = int(delta.get("mp_change", 0) or 0) - 1
                    delta["skill_use"] = {"skill_key": "thread_sensing", "impact": 0.5}
                    log_flow(
                        logger,
                        "magic_gate_soft_fail",
                        player_id=action.player_id,
                        player_name=action.player_name,
                        seal=seal or "none",
                    )
                else:
                    delta["hp_change"] = int(delta.get("hp_change", 0) or 0) - 4
                    delta["stamina_change"] = int(delta.get("stamina_change", 0) or 0) - 8
                    delta["mp_change"] = int(delta.get("mp_change", 0) or 0) - 3
                    delta["skill_use"] = {"skill_key": "thread_sensing", "impact": 0.5}
                    log_flow(
                        logger,
                        "magic_gate_backlash_applied",
                        player_id=action.player_id,
                        player_name=action.player_name,
                        seal=seal or "none",
                    )
        elif re.search(r"(atacar|combate|duelo|fight|battle|confront)", action_text.lower()):
            delta["stamina_change"] = int(delta.get("stamina_change", 0) or 0) - 3

        fallback_items = _extract_loot_from_narrative(action_text, narrative, action.player_id)
        if fallback_items:
            delta["inventory_add"] = fallback_items
            fallback_events.append(
                {
                    "type": "LOOT",
                    "player_id": action.player_id,
                    "player_name": action.player_name,
                    "items": fallback_items,
                }
            )

        if delta:
            state_delta[action.player_id] = delta

    return state_delta, fallback_events


def _repair_json_candidate(raw_json: str) -> str:
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


def _salvage_partial_game_state(raw_json: str) -> dict[str, Any]:
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
        block = _extract_balanced_json_block(text, start)
        if not block:
            continue
        candidate = _repair_json_candidate(block)
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


def _extract_balanced_json_block(text: str, start: int) -> str:
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
        purpose = str(roll.get("purpose", "action check")).strip() or "action check"
        player_name = str(roll.get("player", "Player")).strip() or "Player"

        # Telegraph the roll clearly before publishing the result.
        broadcast_gm_thinking = getattr(cm.manager, "broadcast_gm_thinking", None)
        if callable(broadcast_gm_thinking):
            maybe_result = broadcast_gm_thinking(
                f"Dice check incoming: {player_name} will roll d{die} for {purpose}."
            )
            if inspect.isawaitable(maybe_result):
                await maybe_result
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
            delta_result = await state_manager.apply_state_delta(conn, player_id, delta)
            log_debug(
                logger,
                "state_delta_applied",
                player_id=player_id,
                delta=summarize_payload(delta),
            )
            await _maybe_emit_progression_events(conn, player_id)
            if delta_result.get("milestones_unlocked"):
                await cm.manager.broadcast({
                    "type": "milestone",
                    "player_id": player_id,
                    "milestones": delta_result["milestones_unlocked"],
                })
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
            # Faction credibility changes
            for faction_name, change in delta.get("faction_cred_change", {}).items():
                await cm.manager.broadcast({
                    "type": "faction_objective_update",
                    "faction": faction_name,
                    "objective": "credibility_change",
                    "status": "in_progress",
                    "cred_change": float(change),
                })
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

    # Boss music event (W-04)
    if gm_response.tension_level >= 5 and gm_response.audio_cue == "boss_music":
        await cm.manager.broadcast({
            "type": WSMessageType.BOSS_MUSIC,
            "tension_level": gm_response.tension_level,
            "intensity": "high" if gm_response.tension_level >= 7 else "medium",
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
    lang = _get_campaign_value("campaign.language") or "en"
    if lang == "pt":
        lang_instruction = "Escreva em português do Brasil."
        user_label = "Personagem convocado"
        user_instruction = "Escreva a narrativa de convocação deste personagem para Aerus."
    else:
        lang_instruction = "Write in English."
        user_label = "Summoned character"
        user_instruction = "Write this character's convocation narrative into Aerus."

    system = (
        "You are the narrator of an Aerus RPG session. "
        f"{lang_instruction} "
        "Write a convocation scene for a character just pulled into Aerus — 200 to 300 words. "
        "The tone is heavy and inevitable, not triumphant. "
        "The world does not welcome them; it claims them. "
        "Mention the Dome of Factions and the Primordial Thread naturally, without announcing them. "
        "Write in second person. No em dashes. No flowery adjectives. No rule of three."
    )

    user = (
        f"{user_label}:\n"
        f"Name: {player_name}\n"
        f"Race: {race}\n"
        f"Faction: {faction_config}\n"
        f"Backstory: {backstory[:500]}\n\n"
        f"{user_instruction}"
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




