"""
test_game_master.py — Testes das funções puras do game_master.py.
Sem chamadas de rede ou banco — apenas lógica de parse e formatação.
"""
import pytest

from src.game_master import (
    _calculate_encounter_scaling,
    _extract_narrative_only,
    _flush_buffer,
    _format_batch_as_user_message,
    _parse_gm_response,
)
from src.models import ActionBatch, GMResponse, PlayerAction

# ---------------------------------------------------------------------------
# _extract_narrative_only
# ---------------------------------------------------------------------------

def test_extract_narrative_only_removes_game_state_block():
    raw = (
        "O goblin avança com fúria.\n\n"
        "<game_state>\n"
        '{"dice_rolls": [], "state_delta": {}, "game_events": [], "tension_level": 5}\n'
        "</game_state>"
    )
    result = _extract_narrative_only(raw)
    assert "<game_state>" not in result
    assert "</game_state>" not in result
    assert "O goblin avança com fúria." in result


def test_extract_narrative_only_no_block_returns_full():
    raw = "A névoa se dissipa sobre as Ilhas de Myr."
    result = _extract_narrative_only(raw)
    assert result == raw


def test_extract_narrative_only_strips_surrounding_whitespace():
    raw = "  Narrativa.  \n<game_state>{}</game_state>\n  "
    result = _extract_narrative_only(raw)
    assert result == "Narrativa."


def test_extract_narrative_only_multiline_game_state():
    raw = (
        "Linha 1.\nLinha 2.\n"
        "<game_state>\n{\n  \"tension_level\": 7\n}\n</game_state>\n"
        "Linha 3."
    )
    result = _extract_narrative_only(raw)
    assert "Linha 1." in result
    assert "Linha 2." in result
    assert "Linha 3." in result
    assert "tension_level" not in result


# ---------------------------------------------------------------------------
# _parse_gm_response
# ---------------------------------------------------------------------------

_FAKE_UUID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"

VALID_RESPONSE = (
    "O cavaleiro cai de joelhos.\n\n"
    "<game_state>\n"
    "{\n"
    '  "dice_rolls": [{"player": "Kael", "die": 20, "purpose": "ataque", "result": 18}],\n'
    '  "state_delta": {"' + _FAKE_UUID + '": {"hp_change": -30, "experience_gain": 50}},\n'
    '  "game_events": [{"type": "LOOT", "player_id": "' + _FAKE_UUID + '", "player_name": "Kael", "items": []}],\n'
    '  "tension_level": 7,\n'
    '  "audio_cue": "sword_hit",\n'
    '  "next_scene_query": "cavaleiro caindo"\n'
    "}\n"
    "</game_state>"
)


def test_parse_gm_response_valid():
    result = _parse_gm_response(VALID_RESPONSE)
    assert isinstance(result, GMResponse)
    assert "cavaleiro cai" in result.narrative
    assert len(result.dice_rolls) == 1
    assert result.dice_rolls[0]["player"] == "Kael"
    assert result.dice_rolls[0]["result"] == 18
    assert result.state_delta[_FAKE_UUID]["hp_change"] == -30
    assert result.state_delta[_FAKE_UUID]["experience_gain"] == 50
    assert len(result.game_events) == 1
    assert result.game_events[0]["type"] == "LOOT"
    assert result.tension_level == 7
    assert result.audio_cue == "sword_hit"
    assert result.image_prompt == "cavaleiro caindo"


def test_parse_gm_response_no_game_state_marker():
    """Sem marcador <game_state>, retorna GMResponse só com a narrativa."""
    raw = "A batalha continua. Sem estrutura JSON aqui."
    result = _parse_gm_response(raw)
    assert isinstance(result, GMResponse)
    assert result.narrative == raw
    assert result.dice_rolls == []
    assert result.state_delta == {}
    assert result.game_events == []
    assert result.tension_level == 5  # default


def test_parse_gm_response_malformed_json():
    """JSON inválido dentro de <game_state> deve retornar GMResponse padrão."""
    raw = (
        "Narrativa normal.\n"
        "<game_state>\n"
        "{ invalid json {{{\n"
        "</game_state>"
    )
    result = _parse_gm_response(raw)
    assert isinstance(result, GMResponse)
    assert result.narrative == "Narrativa normal."
    assert result.dice_rolls == []
    assert result.game_events == []


def test_parse_gm_response_empty_game_state():
    """game_state vazio não deve estourar KeyError."""
    raw = (
        "Narrativa.\n"
        "<game_state>\n"
        "{}\n"
        "</game_state>"
    )
    result = _parse_gm_response(raw)
    assert result.narrative == "Narrativa."
    assert result.dice_rolls == []
    assert result.tension_level == 5


def test_parse_gm_response_preserves_is_critical_absence():
    """dice_rolls não têm is_critical/is_fumble no parse — são adicionados em _apply_deltas."""
    result = _parse_gm_response(VALID_RESPONSE)
    roll = result.dice_rolls[0]
    # Parse não enriquece — enriquecimento é feito em _apply_deltas_and_events
    assert "is_critical" not in roll
    assert "is_fumble" not in roll


def test_parse_gm_response_tension_level_cast_to_int():
    """tension_level deve ser sempre int, mesmo que LLM retorne float."""
    raw = (
        "Narrativa.\n"
        '<game_state>{"tension_level": 6.9}</game_state>'
    )
    result = _parse_gm_response(raw)
    assert isinstance(result.tension_level, int)
    assert result.tension_level == 6


def test_parse_gm_response_audio_cue_none_when_absent():
    raw = (
        "Narrativa.\n"
        '<game_state>{"tension_level": 5}</game_state>'
    )
    result = _parse_gm_response(raw)
    assert result.audio_cue is None


def test_parse_gm_response_image_prompt_from_next_scene_query():
    raw = (
        "Narrativa.\n"
        '<game_state>{"next_scene_query": "floresta sombria"}</game_state>'
    )
    result = _parse_gm_response(raw)
    assert result.image_prompt == "floresta sombria"


# ---------------------------------------------------------------------------
# _format_batch_as_user_message
# ---------------------------------------------------------------------------

def _make_batch(*actions: tuple[str, str, str]) -> ActionBatch:
    """Helper: cria ActionBatch a partir de tuplas (player_id, name, text)."""
    player_actions = [
        PlayerAction(player_id=pid, player_name=name, action_text=text, timestamp=0.0)
        for pid, name, text in actions
    ]
    return ActionBatch(actions=player_actions, turn_number=3)


def test_format_batch_single_action():
    batch = _make_batch(("p1", "Kael", "Ataco o goblin com a espada."))
    msg = _format_batch_as_user_message(batch)
    assert "[Turn 3]" in msg
    assert "**Kael**" in msg
    assert "Ataco o goblin com a espada." in msg


def test_format_batch_multiple_actions():
    batch = _make_batch(
        ("p1", "Kael", "Ataco o líder."),
        ("p2", "Lyra", "Lanço uma bola de fogo."),
    )
    msg = _format_batch_as_user_message(batch)
    assert "**Kael**" in msg
    assert "**Lyra**" in msg
    assert "bola de fogo" in msg


def test_format_batch_includes_turn_number():
    batch = _make_batch(("p1", "Kael", "Ação qualquer."))
    batch.turn_number = 42
    msg = _format_batch_as_user_message(batch)
    assert "[Turn 42]" in msg


def test_format_batch_empty_actions():
    """Batch sem ações deve retornar pelo menos o header de turno."""
    batch = ActionBatch(actions=[], turn_number=1)
    msg = _format_batch_as_user_message(batch)
    assert "[Turn 1]" in msg


# ---------------------------------------------------------------------------
# _flush_buffer
# ---------------------------------------------------------------------------

def test_flush_buffer_splits_on_game_state_marker():
    buffer = "Narrativa antes.<game_state>json aqui"
    to_emit, new_buffer = _flush_buffer(buffer)
    assert to_emit == "Narrativa antes."
    assert new_buffer == ""


def test_flush_buffer_short_no_marker_emits_nothing():
    """Buffer curto sem marcador: não emite, mantém no buffer."""
    buffer = "curto"
    to_emit, new_buffer = _flush_buffer(buffer)
    assert to_emit == ""
    assert new_buffer == "curto"


def test_flush_buffer_long_no_marker_emits_partial():
    """Buffer longo sem marcador: emite parte, retém os últimos 20 chars."""
    buffer = "A" * 60
    to_emit, new_buffer = _flush_buffer(buffer)
    assert len(to_emit) == 40   # 60 - 20
    assert len(new_buffer) == 20


def test_flush_buffer_exactly_50_chars_emits_partial():
    """Buffer com exatamente 51 chars (> 50) deve emitir."""
    buffer = "B" * 51
    to_emit, new_buffer = _flush_buffer(buffer)
    assert len(to_emit) == 31
    assert len(new_buffer) == 20


def test_flush_buffer_marker_at_start():
    """Marcador no início: nada a emitir antes."""
    buffer = "<game_state>resto"
    to_emit, new_buffer = _flush_buffer(buffer)
    assert to_emit == ""
    assert new_buffer == ""


def test_calculate_encounter_scaling_grows_with_party_size():
    scale1, boss1 = _calculate_encounter_scaling(1)
    scale3, boss3 = _calculate_encounter_scaling(3)
    scale5, boss5 = _calculate_encounter_scaling(5)

    assert scale1 == pytest.approx(1.0)
    assert scale3 > scale1
    assert scale5 > scale3
    assert boss1 == 0
    assert boss3 == 1
    assert boss5 == 2


def test_calculate_encounter_scaling_respects_boss_step_curve():
    _, boss2 = _calculate_encounter_scaling(2)
    _, boss4 = _calculate_encounter_scaling(4)
    _, boss6 = _calculate_encounter_scaling(6)

    assert boss2 == 0
    assert boss4 == 1
    assert boss6 == 2
