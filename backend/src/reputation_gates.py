"""
reputation_gates.py — Evaluates faction reputation thresholds and emits
unlock events when a player crosses a configured gate.

Each gate fires exactly once per player per faction (tracked via quest_flags).
Called by game_master after applying state deltas that include reputation changes.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from . import state_manager

logger = logging.getLogger(__name__)

_GATES_PATH = Path(__file__).parent.parent / "config" / "reputation_gates.yaml"
_gates_cache: list[dict] | None = None


def _load_gates() -> list[dict]:
    global _gates_cache
    if _gates_cache is None:
        data = yaml.safe_load(_gates_path().read_text(encoding="utf-8"))
        _gates_cache = data.get("gates", [])
    return _gates_cache


def _gates_path() -> Path:
    return _GATES_PATH


def _band(score: int) -> str:
    if score <= -50:
        return "hostile"
    if score <= -20:
        return "distrusted"
    if score <= 19:
        return "neutral"
    if score <= 49:
        return "friendly"
    return "allied"


async def check_reputation_gates(
    conn: Any,
    player_id: str,
    faction_id: str,
    new_score: int,
    old_score: int,
) -> list[dict]:
    """Check and fire any gates triggered by a reputation change.

    Returns a list of fired gate payloads (to be broadcast as game events).
    Each gate fires at most once per player (idempotent via quest_flags).
    """
    gates = _load_gates()
    fired: list[dict] = []

    for gate in gates:
        if gate["faction_id"] != faction_id:
            continue

        threshold = gate["threshold"]
        direction = gate["direction"]

        crossed = (
            (direction == "up" and old_score < threshold <= new_score)
            or (direction == "down" and old_score > threshold >= new_score)
        )
        if not crossed:
            continue

        flag_key = f"rep_gate:{gate['gate_id']}:{player_id}"
        already_fired = await state_manager.get_quest_flag(conn, flag_key)
        if already_fired == "1":
            continue

        await state_manager.set_quest_flag(conn, flag_key, "1")

        payload = {
            "type": "REPUTATION_GATE_UNLOCKED",
            "gate_id": gate["gate_id"],
            "player_id": player_id,
            "faction_id": faction_id,
            "unlock_type": gate["unlock_type"],
            "description": gate["description"],
            "gm_hint": gate["gm_hint"],
            "new_score": new_score,
            "reputation_band": _band(new_score),
        }
        fired.append(payload)
        logger.info(
            "Reputation gate fired: gate=%s player=%s faction=%s score=%d",
            gate["gate_id"],
            player_id,
            faction_id,
            new_score,
        )

    return fired
