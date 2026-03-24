from __future__ import annotations

import json
import os
import re

import aiosqlite

from . import state_manager
from .local_llm import generate_text
from .models import ActionBatch, GMResponse
from .summarizer import summarize_recent_history


async def update_memory_after_turn(
    conn: aiosqlite.Connection,
    batch: ActionBatch,
    gm_response: GMResponse,
) -> None:
    extracted = await _extract_structured_memory(conn, batch, gm_response)
    summary = (await summarize_recent_history(conn, limit=12)).strip()

    unique_player_ids = list(dict.fromkeys(action.player_id for action in batch.actions))
    player_name_by_id = {
        action.player_id: action.player_name or "Player" for action in batch.actions
    }

    for player_id in unique_player_ids:
        player = await state_manager.get_player_by_id(conn, player_id)
        if player is None:
            continue

        player_name = player["name"] or player_name_by_id.get(player_id, "Player")
        existing = (await state_manager.get_memory_layers(conn, [player_id])).character
        facts = extracted["character_facts"].get(player_name, [])
        fact_lines = [f"- {line}" for line in facts if line]

        candidate_parts: list[str] = [f"{player_name}:"]
        if fact_lines:
            candidate_parts.extend(fact_lines)
        if summary:
            candidate_parts.append(f"Summary: {summary}")
        candidate = "\n".join(candidate_parts)

        char_memory = _merge_memory(existing, candidate)
        await state_manager.upsert_character_memory(conn, player_id, char_memory)

    existing_world = (await state_manager.get_memory_layers(conn, [])).world
    existing_arc = (await state_manager.get_memory_layers(conn, [])).arc

    world_lines = [f"Turn {batch.turn_number}:"]
    world_lines.extend(f"- {line}" for line in extracted["world_changes"] if line)
    if summary:
        world_lines.append(f"Summary: {summary}")
    world_memory = _merge_memory(existing_world, "\n".join(world_lines))

    arc_lines = [
        f"Tension {int(extracted['tension_hint'])}/10.",
        *[f"- {line}" for line in extracted["arc_progress"] if line],
    ]
    if summary:
        arc_lines.append(f"Summary: {summary}")
    arc_memory = _merge_memory(existing_arc, "\n".join(arc_lines))

    await state_manager.upsert_world_memory(conn, world_memory)
    await state_manager.upsert_arc_memory(conn, arc_memory)


async def _extract_structured_memory(
    conn: aiosqlite.Connection,
    batch: ActionBatch,
    gm_response: GMResponse,
) -> dict:
    transcript = await _build_memory_transcript(conn, batch, gm_response)
    model = os.getenv("AERUS_OLLAMA_EXTRACTOR_MODEL", "qwen2.5:14b-instruct")

    system_prompt = (
        "You extract structured memory for an RPG. "
        "Respond ONLY with valid JSON and no markdown or comments."
    )
    user_prompt = (
        "Extract memory using this exact schema:\n"
        "{\n"
        '  "character_facts": {"Player Name": ["fact 1", "fact 2"]},\n'
        '  "world_changes": ["permanent world change 1"],\n'
        '  "arc_progress": ["narrative progress 1"],\n'
        '  "tension_hint": 0\n'
        "}\n"
        "Rules: keep facts short, do not invent anything, max 3 items per list.\n\n"
        f"TRANSCRIPT:\n{transcript}"
    )

    try:
        raw = await generate_text(
            system_prompt,
            user_prompt,
            max_tokens=320,
            model_override=model,
        )
        parsed = _parse_extractor_json(raw, batch=batch, gm_response=gm_response)
        return parsed
    except Exception:
        return _deterministic_memory_fallback(batch, gm_response)


async def _build_memory_transcript(
    conn: aiosqlite.Connection,
    batch: ActionBatch,
    gm_response: GMResponse,
) -> str:
    history = await state_manager.get_recent_history(conn, limit=8)
    history_lines = [
        f"{('Players' if row['role'] == 'user' else 'GM')}: {row['content']}"
        for row in history
    ]

    current_actions = "\n".join(f"- {a.player_name}: {a.action_text}" for a in batch.actions)
    events = ", ".join(event.get("type", "UNKNOWN") for event in gm_response.game_events) or "none"

    return (
        f"Current turn: {batch.turn_number}\n"
        f"Current actions:\n{current_actions}\n\n"
        f"Current narrative:\n{gm_response.narrative}\n\n"
        f"Current events: {events}\n"
        f"Current tension: {gm_response.tension_level}\n\n"
        "Recent history:\n"
        + "\n".join(history_lines)
    )


def _parse_extractor_json(raw: str, batch: ActionBatch, gm_response: GMResponse) -> dict:
    normalized = _extract_json_body(raw)
    parsed = json.loads(normalized)
    if not isinstance(parsed, dict):
        raise ValueError("Memory JSON is not an object")

    character_facts_raw = parsed.get("character_facts", {})
    world_changes_raw = parsed.get("world_changes", [])
    arc_progress_raw = parsed.get("arc_progress", [])
    tension_hint_raw = parsed.get("tension_hint", gm_response.tension_level)

    if not isinstance(character_facts_raw, dict):
        raise ValueError("Invalid character_facts")
    if not isinstance(world_changes_raw, list) or not isinstance(arc_progress_raw, list):
        raise ValueError("Invalid memory lists")

    valid_names = {action.player_name for action in batch.actions if action.player_name}
    character_facts = _coerce_character_facts(character_facts_raw, valid_names)

    for action in batch.actions:
        if action.player_name not in character_facts:
            character_facts[action.player_name] = []

    world_changes = _coerce_text_list(world_changes_raw)
    arc_progress = _coerce_text_list(arc_progress_raw)

    try:
        tension_hint = int(tension_hint_raw)
    except (TypeError, ValueError):
        tension_hint = gm_response.tension_level

    tension_hint = max(0, min(10, tension_hint))
    return {
        "character_facts": character_facts,
        "world_changes": world_changes,
        "arc_progress": arc_progress,
        "tension_hint": tension_hint,
    }


def _coerce_character_facts(
    character_facts_raw: dict,
    valid_names: set[str],
) -> dict[str, list[str]]:
    character_facts: dict[str, list[str]] = {}
    for name, facts in character_facts_raw.items():
        if isinstance(name, str) and isinstance(facts, list) and name in valid_names:
            cleaned = _coerce_text_list(facts)
            if cleaned:
                character_facts[name] = cleaned
    return character_facts


def _coerce_text_list(values: list) -> list[str]:
    return [str(item).strip() for item in values if str(item).strip()][:3]


def _extract_json_body(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    match = re.search(r"\{[\s\S]*\}", text)
    return match.group(0) if match else text


def _deterministic_memory_fallback(batch: ActionBatch, gm_response: GMResponse) -> dict:
    character_facts = {
        action.player_name: [f"Acted on turn {batch.turn_number}: {action.action_text[:120]}"]
        for action in batch.actions
        if action.player_name
    }
    world_changes = [
        f"Observed consequence on turn {batch.turn_number}: {gm_response.narrative[:180]}"
        if gm_response.narrative
        else f"Turn {batch.turn_number} processed without detailed narrative"
    ]
    arc_progress = [
        f"Turn {batch.turn_number} completed with {len(gm_response.game_events)} event(s)"
    ]
    return {
        "character_facts": character_facts,
        "world_changes": world_changes,
        "arc_progress": arc_progress,
        "tension_hint": max(0, min(10, int(gm_response.tension_level))),
    }


def _merge_memory(existing: str, incoming: str, max_lines: int = 12) -> str:
    existing_lines = [line.strip() for line in (existing or "").splitlines() if line.strip()]
    incoming_lines = [line.strip() for line in (incoming or "").splitlines() if line.strip()]

    merged: list[str] = []
    for line in existing_lines + incoming_lines:
        if line not in merged:
            merged.append(line)

    if len(merged) > max_lines:
        merged = merged[-max_lines:]
    return "\n".join(merged)
