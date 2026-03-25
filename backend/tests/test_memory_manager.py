from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, patch

import pytest

from src import memory_manager, state_manager
from src.models import ActionBatch, GMResponse, PlayerAction


async def _seed_player(conn, username: str, name: str) -> str:
    player_id = str(uuid.uuid4())
    await state_manager.create_player(conn, player_id, username, "hash")
    await state_manager.set_character(
        conn,
        player_id=player_id,
        name=name,
        race="humano",
        faction="guild_of_threads",
        backstory="um passado sombrio",
        inferred_class="Guerreiro",
        secret_objective="sobreviver",
        max_hp=100,
    )
    return player_id


@pytest.mark.asyncio
async def test_update_memory_after_turn_persists_character_world_arc(db):
    p1 = await _seed_player(db, "player1", "Kael")
    p2 = await _seed_player(db, "player2", "Lyra")

    batch = ActionBatch(
        actions=[
            PlayerAction(player_id=p1, player_name="Kael", action_text="Ataco", timestamp=0.0),
            PlayerAction(player_id=p2, player_name="Lyra", action_text="LanÃ§o magia", timestamp=0.0),
        ],
        turn_number=3,
    )
    gm_response = GMResponse(narrative="A cena avanÃ§a", tension_level=7)

    extracted = {
        "character_facts": {
            "Kael": ["Sofreu dano ao proteger Lyra"],
            "Lyra": ["Selou a cripta com magia de fogo"],
        },
        "world_changes": ["CapitÃ£o cultista fugiu para a cripta"],
        "arc_progress": ["Conflito escalou apÃ³s fuga do antagonista"],
        "tension_hint": 8,
    }

    with patch("src.memory_manager.generate_text", new=AsyncMock(return_value=json.dumps(extracted))):
        with patch("src.memory_manager.summarize_recent_history", new=AsyncMock(return_value="Resumo do turno")):
            await memory_manager.update_memory_after_turn(db, batch, gm_response)

    memory = await state_manager.get_memory_layers(db, [p1, p2])
    assert "Sofreu dano ao proteger Lyra" in memory.character
    assert "Selou a cripta com magia de fogo" in memory.character
    assert "Resumo do turno" in memory.character
    assert "Turn 3" in memory.world
    assert "CapitÃ£o cultista fugiu para a cripta" in memory.world
    assert "Tension 8/10" in memory.arc


@pytest.mark.asyncio
async def test_update_memory_after_turn_uses_deterministic_fallback_when_extractor_invalid(db):
    p1 = await _seed_player(db, "player3", "Nox")
    batch = ActionBatch(
        actions=[PlayerAction(player_id=p1, player_name="Nox", action_text="Observo", timestamp=0.0)],
        turn_number=1,
    )
    gm_response = GMResponse(narrative="SilÃªncio", tension_level=5)

    with patch("src.memory_manager.generate_text", new=AsyncMock(return_value="NOT_JSON")):
        with patch("src.memory_manager.summarize_recent_history", new=AsyncMock(return_value="  ")):
            await memory_manager.update_memory_after_turn(db, batch, gm_response)

    memory = await state_manager.get_memory_layers(db, [p1])
    assert "Acted on turn 1" in memory.character
    assert "Observed consequence on turn 1" in memory.world
    assert "Tension 5/10" in memory.arc


def test_parse_extractor_json_strips_markdown_fences():
    batch = ActionBatch(
        actions=[PlayerAction(player_id="p1", player_name="Kael", action_text="Ataco", timestamp=0.0)],
        turn_number=2,
    )
    gm_response = GMResponse(narrative="Narrativa", tension_level=6)

    raw = """```json
    {
      "character_facts": {"Kael": ["Feriu o inimigo"]},
      "world_changes": ["PortÃ£o foi quebrado"],
      "arc_progress": ["Ato 1 avanÃ§ou"],
      "tension_hint": 9
    }
    ```"""
    parsed = memory_manager._parse_extractor_json(raw, batch=batch, gm_response=gm_response)

    assert parsed["character_facts"]["Kael"] == ["Feriu o inimigo"]
    assert parsed["world_changes"] == ["PortÃ£o foi quebrado"]
    assert parsed["arc_progress"] == ["Ato 1 avanÃ§ou"]
    assert parsed["tension_hint"] == 9


def test_merge_memory_deduplicates_and_limits_lines():
    existing = "linha 1\nlinha 2\nlinha 3"
    incoming = "linha 2\nlinha 4\nlinha 5"
    merged = memory_manager._merge_memory(existing, incoming, max_lines=4)
    assert merged.splitlines() == ["linha 2", "linha 3", "linha 4", "linha 5"]
