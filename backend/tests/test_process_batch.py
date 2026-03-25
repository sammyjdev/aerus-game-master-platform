"""
test_process_batch.py â€” Teste de integraÃ§Ã£o do pipeline completo do game loop.

Testa process_batch com LLM mockado: verifica que parse, aplicaÃ§Ã£o de delta,
histÃ³rico e broadcasts ocorrem corretamente sem chamadas de rede reais.
"""
from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from src import state_manager
from src.game_master import _apply_deltas_and_events, _build_messages, _parse_gm_response, process_batch
from src.models import ActionBatch, GMResponse, PlayerAction


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _seed_player(conn) -> str:
    player_id = str(uuid.uuid4())
    await state_manager.create_player(conn, player_id, "heroi", "hash")
    await state_manager.set_character(
        conn,
        player_id=player_id,
        name="Kael",
        race="humano",
        faction="guild_of_threads",
        backstory="Um arqueiro errante.",
        inferred_class="Arqueiro",
        secret_objective="Sobreviver.",
        max_hp=100,
    )
    return player_id


def _make_batch(player_id: str, text: str = "Ataco o goblin.") -> ActionBatch:
    return ActionBatch(
        actions=[PlayerAction(player_id=player_id, player_name="Kael", action_text=text, timestamp=0.0)],
        turn_number=1,
    )


# Resposta simulada de LLM com estrutura completa
def _make_llm_response(player_id: str) -> str:
    delta = json.dumps({player_id: {"hp_change": -20, "experience_gain": 30}})
    return (
        "O goblin recua ferido, uivando de dor.\n\n"
        "<game_state>\n"
        "{\n"
        f'  "dice_rolls": [{{"player": "Kael", "die": 20, "purpose": "ataque", "result": 15}}],\n'
        f'  "state_delta": {delta},\n'
        '  "game_events": [],\n'
        '  "tension_level": 4,\n'
        '  "audio_cue": "sword_hit"\n'
        "}\n"
        "</game_state>"
    )


# ---------------------------------------------------------------------------
# Testes de _apply_deltas_and_events
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_apply_deltas_updates_hp_in_db(db):
    player_id = await _seed_player(db)

    gm_response = GMResponse(
        narrative="Kael sofre 20 de dano.",
        state_delta={player_id: {"hp_change": -20, "experience_gain": 10}},
    )

    broadcast_calls: list[dict] = []

    with patch("src.game_master.cm.manager") as mock_manager:
        mock_manager.broadcast = AsyncMock(side_effect=lambda m: broadcast_calls.append(m) or None)
        mock_manager.broadcast_dice_roll = AsyncMock()
        mock_manager.broadcast_game_event = AsyncMock()

        await _apply_deltas_and_events(db, gm_response)

    # Verifica que HP foi reduzido no banco
    row = await state_manager.get_player_by_id(db, player_id)
    assert row["current_hp"] == 80

    # Verifica que state_update foi broadcast
    state_updates = [c for c in broadcast_calls if c.get("type") == "state_update"]
    assert len(state_updates) == 1


@pytest.mark.asyncio
async def test_apply_deltas_broadcasts_dice_roll(db):
    await _seed_player(db)

    gm_response = GMResponse(
        narrative="Kael rola o dado.",
        dice_rolls=[{"player": "Kael", "die": 20, "purpose": "ataque", "result": 20}],
    )

    with patch("src.game_master.cm.manager") as mock_manager:
        mock_manager.broadcast = AsyncMock()
        mock_manager.broadcast_dice_roll = AsyncMock()
        mock_manager.broadcast_game_event = AsyncMock()

        await _apply_deltas_and_events(db, gm_response)

    # dice_roll broadcast foi chamado uma vez
    mock_manager.broadcast_dice_roll.assert_called_once()
    call_arg = mock_manager.broadcast_dice_roll.call_args[0][0]
    assert call_arg["is_critical"] is True   # result == die
    assert call_arg["is_fumble"] is False


@pytest.mark.asyncio
async def test_apply_deltas_broadcasts_audio_cue(db):
    await _seed_player(db)

    gm_response = GMResponse(
        narrative="Impacto!",
        audio_cue="sword_hit",
    )

    broadcast_calls: list[dict] = []

    with patch("src.game_master.cm.manager") as mock_manager:
        mock_manager.broadcast = AsyncMock(side_effect=lambda m: broadcast_calls.append(m) or None)
        mock_manager.broadcast_dice_roll = AsyncMock()
        mock_manager.broadcast_game_event = AsyncMock()

        await _apply_deltas_and_events(db, gm_response)

    audio_broadcasts = [c for c in broadcast_calls if c.get("type") == "audio_cue"]
    assert len(audio_broadcasts) == 1
    assert audio_broadcasts[0]["cue"] == "sword_hit"


@pytest.mark.asyncio
async def test_apply_deltas_broadcasts_game_event(db):
    player_id = await _seed_player(db)

    gm_response = GMResponse(
        narrative="Kael subiu de nÃ­vel!",
        game_events=[{"type": "LEVELUP", "player_id": player_id, "player_name": "Kael", "new_level": 2}],
    )

    with patch("src.game_master.cm.manager") as mock_manager:
        mock_manager.broadcast = AsyncMock()
        mock_manager.broadcast_dice_roll = AsyncMock()
        mock_manager.broadcast_game_event = AsyncMock()

        await _apply_deltas_and_events(db, gm_response)

    mock_manager.broadcast_game_event.assert_called_once_with(
        "LEVELUP",
        {"type": "LEVELUP", "player_id": player_id, "player_name": "Kael", "new_level": 2},
    )


@pytest.mark.asyncio
async def test_apply_deltas_persists_tension_level(db):
    await _seed_player(db)

    gm_response = GMResponse(
        narrative="A pressÃ£o aumenta.",
        tension_level=8,
    )

    with patch("src.game_master.cm.manager") as mock_manager:
        mock_manager.broadcast = AsyncMock()
        mock_manager.broadcast_dice_roll = AsyncMock()
        mock_manager.broadcast_game_event = AsyncMock()

        await _apply_deltas_and_events(db, gm_response)

    tension = await state_manager.get_world_state(db, "tension_level")
    assert tension == "8"


@pytest.mark.asyncio
async def test_build_messages_uses_dynamic_tension_level(db):
    player_id = await _seed_player(db)
    batch = _make_batch(player_id)

    await state_manager.set_world_state(db, "tension_level", "9")

    mock_context = MagicMock()
    mock_context.to_system_prompt.return_value = "# Contexto base"
    messages = await _build_messages(
        conn=db,
        context=mock_context,
        user_message="AÃ§Ã£o do turno",
        batch=batch,
        party_size=1,
    )

    assert "Current tension: 9/10" in messages[0]["content"]


# ---------------------------------------------------------------------------
# Teste de integraÃ§Ã£o: process_batch completo com LLM mockado
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_process_batch_full_pipeline(db):
    """
    Verifica que process_batch:
    - chama o LLM (mockado)
    - faz streaming dos tokens narrativos
    - aplica o delta de estado no banco
    - salva histÃ³rico no banco
    - nÃ£o lanÃ§a exceÃ§Ãµes
    """
    player_id = await _seed_player(db)
    batch = _make_batch(player_id)
    broadcast_calls: list[dict] = []

    async def fake_broadcast_stream(stream):
        narrative = ""
        async for token in stream:
            narrative += token
        return narrative

    # Monta um chunk stream simulado
    def _make_chunk(text: str):
        chunk = MagicMock()
        chunk.choices = [MagicMock()]
        chunk.choices[0].delta.content = text
        return chunk

    # _tokens_from_stream para de consumir o stream ao ver <game_state>,
    # entÃ£o o bloco inteiro deve estar em um Ãºnico chunk para ir ao collector.
    game_state_json = (
        '{"dice_rolls": [{"player": "Kael", "die": 20, "purpose": "ataque", "result": 15}],'
        f'"state_delta": {{"{player_id}": {{"hp_change": -20, "experience_gain": 30}}}},'
        '"game_events": [], "tension_level": 4, "audio_cue": "sword_hit"}'
    )
    chunks = [
        _make_chunk("O goblin recua ferido, uivando de dor.\n\n"),
        _make_chunk(f"<game_state>\n{game_state_json}\n</game_state>"),
    ]

    class FakeStream:
        """Async iterable que simula o stream de chunks do OpenAI."""
        def __aiter__(self):
            return self._gen()

        async def _gen(self):
            for chunk in chunks:
                yield chunk

    mock_stream = FakeStream()

    with (
        patch("src.game_master.cm.manager") as mock_manager,
        patch("src.game_master.AsyncOpenAI") as mock_openai_cls,
        patch("src.game_master.build_context") as mock_ctx,
        patch("src.game_master.select_billing_config") as mock_billing,
    ):
        # Setup manager
        mock_manager.broadcast_stream = AsyncMock(side_effect=fake_broadcast_stream)
        mock_manager.broadcast = AsyncMock(side_effect=lambda m: broadcast_calls.append(m) or None)
        mock_manager.broadcast_dice_roll = AsyncMock()
        mock_manager.broadcast_game_event = AsyncMock()
        mock_manager.broadcast_gm_thinking = AsyncMock()

        # Setup LLM
        mock_client = AsyncMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create = AsyncMock(return_value=mock_stream)

        # Setup context
        mock_ctx_obj = MagicMock()
        mock_ctx_obj.to_system_prompt.return_value = "# MUNDO: AERUS"
        mock_ctx.return_value = mock_ctx_obj

        # Setup billing
        mock_billing_obj = MagicMock()
        mock_billing_obj.api_key = "sk-test"
        mock_billing_obj.base_url = "https://openrouter.ai/api/v1"
        mock_billing_obj.model = "google/gemini-flash-1.5"
        mock_billing.return_value = mock_billing_obj

        await process_batch(db, batch)

    # HistÃ³rico deve ter sido gravado (user + assistant)
    history = await state_manager.get_recent_history(db, limit=10)
    roles = [h["role"] for h in history]
    assert "user" in roles
    assert "assistant" in roles

    # HP deve ter sido reduzido
    row = await state_manager.get_player_by_id(db, player_id)
    assert row["current_hp"] == 80

    # XP deve ter aumentado
    assert row["experience"] == 30

    # stream_end foi broadcast
    stream_ends = [c for c in broadcast_calls if c.get("type") == "stream_end"]
    assert len(stream_ends) >= 1


@pytest.mark.asyncio
async def test_process_batch_full_pipeline_local_only(db, monkeypatch):
    player_id = await _seed_player(db)
    batch = _make_batch(player_id)
    broadcast_calls: list[dict] = []

    monkeypatch.setenv("AERUS_LOCAL_ONLY", "true")

    async def fake_broadcast_stream(stream):
        narrative = ""
        async for token in stream:
            narrative += token
        return narrative

    full_response = _make_llm_response(player_id)

    with (
        patch("src.game_master.cm.manager") as mock_manager,
        patch("src.game_master.build_context") as mock_ctx,
        patch("src.game_master.local_llm.generate_chat", new=AsyncMock(return_value=full_response)),
    ):
        mock_manager.broadcast_stream = AsyncMock(side_effect=fake_broadcast_stream)
        mock_manager.broadcast = AsyncMock(side_effect=lambda m: broadcast_calls.append(m) or None)
        mock_manager.broadcast_dice_roll = AsyncMock()
        mock_manager.broadcast_game_event = AsyncMock()
        mock_manager.broadcast_gm_thinking = AsyncMock()

        mock_ctx_obj = MagicMock()
        mock_ctx_obj.to_system_prompt.return_value = "# MUNDO: AERUS"
        mock_ctx.return_value = mock_ctx_obj

        await process_batch(db, batch)

    row = await state_manager.get_player_by_id(db, player_id)
    assert row["current_hp"] == 80
    assert row["experience"] == 30
    stream_ends = [c for c in broadcast_calls if c.get("type") == "stream_end"]
    assert len(stream_ends) >= 1


@pytest.mark.asyncio
async def test_apply_deltas_triggers_ability_unlock_on_level_multiple_of_five(db):
    """NÃ­vel 5: emite ABILITY_UNLOCK (sinal para GM), sem CLASS_MUTATION ainda."""
    player_id = await _seed_player(db)
    await db.execute(
        "UPDATE players SET inferred_class = ?, level = ?, experience = ? WHERE player_id = ?",
        ("Guerreiro", 4, 399, player_id),
    )
    await db.commit()

    gm_response = GMResponse(
        narrative="Kael evolui em combate.",
        state_delta={player_id: {"experience_gain": 1}},
    )

    with patch("src.game_master.cm.manager") as mock_manager:
        mock_manager.broadcast = AsyncMock()
        mock_manager.broadcast_dice_roll = AsyncMock()
        mock_manager.broadcast_game_event = AsyncMock()

        await _apply_deltas_and_events(db, gm_response)

    row = await state_manager.get_player_by_id(db, player_id)
    assert row["level"] == 5
    # NÃ­vel 5 â†’ apenas ABILITY_UNLOCK, sem mutaÃ§Ã£o de classe ainda (ocorre no 25)
    assert row["inferred_class"] == "Guerreiro"
    mock_manager.broadcast_game_event.assert_any_call(
        "ABILITY_UNLOCK",
        {
            "type": "ABILITY_UNLOCK",
            "player_id": player_id,
            "player_name": "Kael",
            "level": 5,
            "inferred_class": "Guerreiro",
        },
    )


@pytest.mark.asyncio
async def test_apply_deltas_triggers_class_mutation_on_level_25(db):
    """NÃ­vel 25: emite CLASS_MUTATION (mutaÃ§Ã£o formal) alÃ©m do ABILITY_UNLOCK."""
    player_id = await _seed_player(db)
    await db.execute(
        "UPDATE players SET inferred_class = ?, level = ?, experience = ? WHERE player_id = ?",
        ("Warrior", 24, 9999, player_id),
    )
    await db.commit()

    gm_response = GMResponse(
        narrative="Kael atinge a mutaÃ§Ã£o formal.",
        state_delta={player_id: {"experience_gain": 1}},
    )

    with patch("src.game_master.cm.manager") as mock_manager:
        mock_manager.broadcast = AsyncMock()
        mock_manager.broadcast_dice_roll = AsyncMock()
        mock_manager.broadcast_game_event = AsyncMock()

        await _apply_deltas_and_events(db, gm_response)

    row = await state_manager.get_player_by_id(db, player_id)
    assert row["level"] == 25
    assert row["inferred_class"] == "Steel Warden"
    mock_manager.broadcast_game_event.assert_any_call(
        "CLASS_MUTATION",
        {
            "type": "CLASS_MUTATION",
            "player_id": player_id,
            "player_name": "Kael",
            "old_class": "Warrior",
            "new_class": "Steel Warden",
            "level": 25,
        },
    )


@pytest.mark.asyncio
async def test_apply_deltas_emits_secret_objective_hint_when_progress_crosses_threshold(db):
    player_id = await _seed_player(db)
    await state_manager.set_quest_flag(db, f"secret_objective_progress:{player_id}", "25")
    await state_manager.set_quest_flag(db, f"secret_objective_hint_stage:{player_id}", "0")

    batch = _make_batch(player_id, text="Investigo os sinais do culto.")
    gm_response = GMResponse(narrative="O culto deixa pistas no mercado.")

    with patch("src.game_master.cm.manager") as mock_manager:
        mock_manager.broadcast = AsyncMock()
        mock_manager.broadcast_dice_roll = AsyncMock()
        mock_manager.broadcast_game_event = AsyncMock()

        await _apply_deltas_and_events(db, gm_response, batch=batch)

    stage = await state_manager.get_quest_flag(db, f"secret_objective_hint_stage:{player_id}")
    progress = await state_manager.get_quest_flag(db, f"secret_objective_progress:{player_id}")

    assert stage == "1"
    assert progress == "35"
    assert mock_manager.broadcast_game_event.call_args_list
    hint_call = mock_manager.broadcast_game_event.call_args_list[-1]
    assert hint_call.args[0] == "FACTION_CONFLICT"
    assert hint_call.args[1]["type"] == "FACTION_CONFLICT"

