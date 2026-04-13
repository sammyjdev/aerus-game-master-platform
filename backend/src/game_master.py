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
    async for chunk in stream:
        delta = chunk.choices[0].delta.content
        if not delta:
            continue
        collector.append(delta)
        buffer += delta
        to_emit, buffer, should_stop = _flush_buffer(buffer)
        if to_emit:
            yield to_emit
        if should_stop:
            return
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
        to_emit, buffer, should_stop = _flush_buffer(buffer)
        if to_emit:
            yield to_emit
        if should_stop:
            return
    if buffer and _GAME_STATE_MARKER not in buffer and _json_stop_position(buffer) is None:
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
        gm_response = _parse_gm_response(
            full_response,
            current_tension=current_tension,
            valid_player_ids=[action.player_id for action in batch.actions],
        )

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
    return stripped.strip()


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
        "heal", "healing", "mend", "mending", "warmth", "relief", "pain eases",
        "pain eased", "wound closes", "wounds close", "wound knits", "knit shut",
        "restored", "restoration", "breath returns", "strength returns",
        "stitches itself", "closed flesh", "closing flesh",
    )
    return any(term in text for term in healing_terms)


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

        if hp_change_int > 0 and not healing_visible:
            updated["hp_change"] = 0
            adjusted = True
            logger.info(
                "GM guardrail removed positive hp_change without healing signal: player=%s original=%s",
                player_id,
                hp_change,
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




