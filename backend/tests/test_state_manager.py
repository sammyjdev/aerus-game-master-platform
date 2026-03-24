"""
test_state_manager.py â€” Testes de integraÃ§Ã£o para state_manager.py.
Usa banco SQLite em arquivo temporÃ¡rio (nÃ£o in-memory) para simular WAL mode.
Cobre: invites, players, history, world_state, memory, delta de estado.
"""
import json
import uuid

import aiosqlite
import pytest
import pytest_asyncio

from src import state_manager
from src.state_manager import (
    _apply_resource_changes,
    _apply_xp_and_attrs,
    _xp_threshold,
)



# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_row(**kwargs) -> dict:
    """Substituto de aiosqlite.Row para testar funÃ§Ãµes puras."""
    defaults = {
        "current_hp": 100, "max_hp": 100,
        "current_mp": 50,  "max_mp": 50,
        "current_stamina": 100, "max_stamina": 100,
        "experience": 0, "level": 1, "status": "alive",
        "attributes_json": "{}",
    }
    defaults.update(kwargs)
    return defaults


async def _seed_player(conn, player_id="player-1", username=None, pw_hash="testhash"):
    """Cria e retorna um jogador base."""
    username = username or f"user-{player_id}"
    await state_manager.create_player(conn, player_id, username, pw_hash)
    return player_id


async def _seed_character(conn, player_id="player-1", username=None):
    """Cria jogador com personagem completo."""
    await _seed_player(conn, player_id, username=username)
    await state_manager.set_character(
        conn,
        player_id=player_id,
        name="Kael",
        race="humano",
        faction="guild_of_threads",
        backstory="Um arqueiro errante.",
        inferred_class="Arqueiro",
        secret_objective="Destruir o Fio Primordial.",
        max_hp=120,
    )
    return player_id


# ---------------------------------------------------------------------------
# init_db
# ---------------------------------------------------------------------------

async def test_init_db_creates_all_tables(db):
    """Todas as 13 tabelas do schema devem existir apÃ³s init_db."""
    expected_tables = {
        "invites", "players", "sessions", "inventory", "conditions",
        "history", "summaries", "quest_flags", "world_state",
        "character_memory", "world_memory", "arc_memory", "generated_images",
    }
    async with db.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ) as cursor:
        rows = await cursor.fetchall()
    found = {r["name"] for r in rows}
    assert expected_tables.issubset(found)


async def test_init_db_is_idempotent(db, tmp_db, monkeypatch):
    """Chamar init_db duas vezes nÃ£o deve falhar nem duplicar tabelas."""
    monkeypatch.setattr(state_manager, "DB_PATH", tmp_db)
    await state_manager.init_db()  # segunda chamada
    async with db.execute(
        "SELECT COUNT(*) as n FROM sqlite_master WHERE type='table'"
    ) as cursor:
        row = await cursor.fetchone()
    assert row["n"] >= 13  # sem duplicatas extras


async def test_wal_mode_is_active(db):
    """WAL mode deve estar ativo na conexÃ£o fornecida pelo fixture."""
    async with db.execute("PRAGMA journal_mode") as cursor:
        row = await cursor.fetchone()
    assert row[0] == "wal"


# ---------------------------------------------------------------------------
# Invites
# ---------------------------------------------------------------------------

async def test_create_and_redeem_invite(db):
    code = "AERUS-2026"
    player_id = str(uuid.uuid4())

    await state_manager.create_invite(db, code, created_by="admin")
    result = await state_manager.redeem_invite(db, code, player_id)

    assert result is True


async def test_redeem_invite_twice_fails(db):
    code = "REUSE-ME"
    pid = str(uuid.uuid4())

    await state_manager.create_invite(db, code, created_by="admin")
    await state_manager.redeem_invite(db, code, pid)
    second = await state_manager.redeem_invite(db, code, str(uuid.uuid4()))

    assert second is False


async def test_redeem_nonexistent_invite_fails(db):
    result = await state_manager.redeem_invite(db, "FAKE-CODE", "pid")
    assert result is False


# ---------------------------------------------------------------------------
# Players â€” CRUD
# ---------------------------------------------------------------------------

async def test_create_player_and_retrieve_by_username(db):
    pid = str(uuid.uuid4())
    await state_manager.create_player(db, pid, "kael", "hash123")

    row = await state_manager.get_player_by_username(db, "kael")
    assert row is not None
    assert row["player_id"] == pid
    assert row["username"] == "kael"


async def test_get_player_by_id(db):
    await _seed_player(db, player_id="pid-abc")
    row = await state_manager.get_player_by_id(db, "pid-abc")
    assert row is not None
    assert row["player_id"] == "pid-abc"


async def test_get_player_nonexistent_returns_none(db):
    row = await state_manager.get_player_by_id(db, "nao-existe")
    assert row is None


async def test_get_all_alive_players_only_with_name(db):
    """get_all_alive_players deve excluir jogadores sem personagem criado."""
    pid1 = str(uuid.uuid4())
    pid2 = str(uuid.uuid4())

    # pid1: tem personagem; pid2: sÃ³ conta, sem nome
    await _seed_character(db, player_id=pid1)
    await _seed_player(db, player_id=pid2, username="sem-personagem")

    rows = await state_manager.get_all_alive_players(db)
    ids = [r["player_id"] for r in rows]

    assert pid1 in ids
    assert pid2 not in ids


async def test_get_all_alive_players_excludes_dead(db):
    pid = await _seed_character(db)
    # Mata o jogador diretamente
    await db.execute("UPDATE players SET status = 'dead' WHERE player_id = ?", (pid,))
    await db.commit()

    rows = await state_manager.get_all_alive_players(db)
    assert all(r["player_id"] != pid for r in rows)


async def test_set_character_stores_default_attributes(db):
    pid = await _seed_character(db)
    row = await state_manager.get_player_by_id(db, pid)
    attrs = json.loads(row["attributes_json"])

    for attr in ("strength", "dexterity", "intelligence", "vitality", "luck", "charisma"):
        assert attr in attrs
        assert attrs[attr] == 10


async def test_set_character_sets_max_hp(db):
    pid = await _seed_character(db)
    row = await state_manager.get_player_by_id(db, pid)
    assert row["max_hp"] == 120
    assert row["current_hp"] == 120


# ---------------------------------------------------------------------------
# apply_state_delta â€” integraÃ§Ã£o
# ---------------------------------------------------------------------------

async def test_apply_state_delta_reduces_hp(db):
    pid = await _seed_character(db)
    await state_manager.apply_state_delta(db, pid, {"hp_change": -30})

    row = await state_manager.get_player_by_id(db, pid)
    assert row["current_hp"] == 90  # 120 - 30


async def test_apply_state_delta_hp_cannot_go_below_zero(db):
    pid = await _seed_character(db)
    await state_manager.apply_state_delta(db, pid, {"hp_change": -9999})

    row = await state_manager.get_player_by_id(db, pid)
    assert row["current_hp"] == 0


async def test_apply_state_delta_hp_zero_marks_player_dead(db):
    pid = await _seed_character(db)
    await state_manager.apply_state_delta(db, pid, {"hp_change": -9999})

    row = await state_manager.get_player_by_id(db, pid)
    assert row["status"] == "dead"


async def test_apply_state_delta_hp_cannot_exceed_max(db):
    pid = await _seed_character(db)
    # Reduz HP para 50 primeiro
    await state_manager.apply_state_delta(db, pid, {"hp_change": -70})
    # Tenta curar 9999 â€” nÃ£o pode ultrapassar max_hp
    await state_manager.apply_state_delta(db, pid, {"hp_change": 9999})

    row = await state_manager.get_player_by_id(db, pid)
    assert row["current_hp"] == row["max_hp"]


async def test_apply_state_delta_experience_gain_and_level_up(db):
    pid = await _seed_character(db)
    # NÃ­vel 1 precisa de 100 XP para avanÃ§ar (_xp_threshold(1) == 100)
    await state_manager.apply_state_delta(db, pid, {"experience_gain": 150})

    row = await state_manager.get_player_by_id(db, pid)
    assert row["level"] == 2
    assert row["experience"] == 50  # 150 - 100 residual


async def test_apply_state_delta_attribute_changes(db):
    pid = await _seed_character(db)
    await state_manager.apply_state_delta(db, pid, {"attribute_changes": {"strength": 5}})

    row = await state_manager.get_player_by_id(db, pid)
    attrs = json.loads(row["attributes_json"])
    assert attrs["strength"] == 15  # 10 base + 5


async def test_apply_state_delta_missing_player_is_noop(db):
    """Delta para player inexistente nÃ£o deve levantar exceÃ§Ã£o."""
    await state_manager.apply_state_delta(db, "player-inexistente", {"hp_change": -10})


# ---------------------------------------------------------------------------
# apply_state_delta â€” inventory e conditions (bugs corrigidos)
# ---------------------------------------------------------------------------

async def test_apply_state_delta_inventory_add_persists(db):
    """inventory_add deve inserir itens na tabela inventory."""
    pid = await _seed_character(db)
    item_id = str(uuid.uuid4())
    item = {
        "item_id": item_id,
        "name": "Espada das Cinzas",
        "description": "Forjada nas ruÃ­nas.",
        "rarity": "epico",
        "quantity": 1,
        "equipped": False,
    }
    await state_manager.apply_state_delta(db, pid, {"inventory_add": [item]})

    rows = await state_manager.get_player_inventory(db, pid)
    assert len(rows) == 1
    assert rows[0]["item_id"] == item_id
    assert rows[0]["name"] == "Espada das Cinzas"
    assert rows[0]["rarity"] == "epico"


async def test_apply_state_delta_inventory_remove(db):
    """inventory_remove deve excluir itens pelo item_id."""
    pid = await _seed_character(db)
    item_id = str(uuid.uuid4())
    item = {"item_id": item_id, "name": "PoÃ§Ã£o", "description": "", "rarity": "comum", "quantity": 1, "equipped": False}

    await state_manager.apply_state_delta(db, pid, {"inventory_add": [item]})
    await state_manager.apply_state_delta(db, pid, {"inventory_remove": [item_id]})

    rows = await state_manager.get_player_inventory(db, pid)
    assert len(rows) == 0


async def test_apply_state_delta_inventory_add_upserts_quantity(db):
    """Adicionar o mesmo item_id atualiza a quantidade, nÃ£o duplica."""
    pid = await _seed_character(db)
    item_id = str(uuid.uuid4())
    item = {"item_id": item_id, "name": "Seta", "description": "", "rarity": "comum", "quantity": 10, "equipped": False}

    await state_manager.apply_state_delta(db, pid, {"inventory_add": [item]})
    item_updated = {**item, "quantity": 20}
    await state_manager.apply_state_delta(db, pid, {"inventory_add": [item_updated]})

    rows = await state_manager.get_player_inventory(db, pid)
    assert len(rows) == 1
    assert rows[0]["quantity"] == 20


async def test_conditions_table_has_is_buff_column(db):
    """A tabela conditions deve ter a coluna is_buff apÃ³s a migration."""
    async with db.execute("PRAGMA table_info(conditions)") as cursor:
        rows = await cursor.fetchall()
    columns = {r["name"] for r in rows}
    assert "is_buff" in columns


async def test_apply_state_delta_conditions_add_persists(db):
    """conditions_add deve inserir condiÃ§Ãµes na tabela conditions."""
    pid = await _seed_character(db)
    cond_id = str(uuid.uuid4())
    cond = {
        "condition_id": cond_id,
        "name": "Envenenado",
        "description": "Perde 5 HP por turno.",
        "duration_turns": 3,
        "applied_at_turn": 5,
        "is_buff": False,
    }
    await state_manager.apply_state_delta(db, pid, {"conditions_add": [cond]})

    rows = await state_manager.get_player_conditions(db, pid)
    assert len(rows) == 1
    assert rows[0]["condition_id"] == cond_id
    assert rows[0]["name"] == "Envenenado"
    assert rows[0]["is_buff"] == 0


async def test_apply_state_delta_conditions_buff_flag(db):
    """is_buff deve ser corretamente armazenado como 1 para buffs."""
    pid = await _seed_character(db)
    cond = {
        "condition_id": str(uuid.uuid4()),
        "name": "BÃªnÃ§Ã£o",
        "description": "+2 em todos os testes.",
        "duration_turns": 5,
        "applied_at_turn": 1,
        "is_buff": True,
    }
    await state_manager.apply_state_delta(db, pid, {"conditions_add": [cond]})

    rows = await state_manager.get_player_conditions(db, pid)
    assert rows[0]["is_buff"] == 1


async def test_apply_state_delta_conditions_remove(db):
    """conditions_remove deve excluir condiÃ§Ãµes pelo condition_id."""
    pid = await _seed_character(db)
    cond_id = str(uuid.uuid4())
    cond = {"condition_id": cond_id, "name": "Lento", "description": "", "duration_turns": 2, "applied_at_turn": 1, "is_buff": False}

    await state_manager.apply_state_delta(db, pid, {"conditions_add": [cond]})
    await state_manager.apply_state_delta(db, pid, {"conditions_remove": [cond_id]})

    rows = await state_manager.get_player_conditions(db, pid)
    assert len(rows) == 0


# ---------------------------------------------------------------------------
# get_player_inventory e get_player_conditions
# ---------------------------------------------------------------------------

async def test_get_player_inventory_empty(db):
    pid = await _seed_character(db)
    rows = await state_manager.get_player_inventory(db, pid)
    assert rows == []


async def test_get_player_conditions_empty(db):
    pid = await _seed_character(db)
    rows = await state_manager.get_player_conditions(db, pid)
    assert rows == []


async def test_get_player_inventory_multiple_items(db):
    pid = await _seed_character(db)
    for i in range(3):
        item = {"item_id": str(uuid.uuid4()), "name": f"Item {i}", "description": "", "rarity": "comum", "quantity": 1, "equipped": False}
        await state_manager.apply_state_delta(db, pid, {"inventory_add": [item]})

    rows = await state_manager.get_player_inventory(db, pid)
    assert len(rows) == 3


# ---------------------------------------------------------------------------
# FunÃ§Ãµes puras â€” _apply_resource_changes / _apply_xp_and_attrs
# ---------------------------------------------------------------------------

def test_apply_resource_changes_normal_damage():
    row = _make_row(current_hp=100, max_hp=100, current_mp=50, max_mp=50,
                    current_stamina=80, max_stamina=100, status="alive")
    hp, _mp, _stamina, status = _apply_resource_changes(row, {"hp_change": -25})
    assert hp == 75
    assert status == "alive"


def test_apply_resource_changes_lethal_damage_sets_dead():
    row = _make_row(current_hp=10, max_hp=100)
    hp, _mp, _st, status = _apply_resource_changes(row, {"hp_change": -100})
    assert hp == 0
    assert status == "dead"


def test_apply_resource_changes_healing_capped_at_max():
    row = _make_row(current_hp=50, max_hp=100)
    hp, _mp, _st, _status = _apply_resource_changes(row, {"hp_change": 9999})
    assert hp == 100


def test_apply_resource_changes_mp_and_stamina():
    row = _make_row(current_mp=30, max_mp=50, current_stamina=60, max_stamina=100)
    _hp, mp, stamina, _st = _apply_resource_changes(
        row, {"mp_change": -15, "stamina_change": -30}
    )
    assert mp == 15
    assert stamina == 30


def test_apply_resource_changes_no_changes_preserves_values():
    row = _make_row(current_hp=70, max_hp=100)
    hp, _mp, _st, status = _apply_resource_changes(row, {})
    assert hp == 70
    assert status == "alive"


def test_xp_threshold_scales_with_level():
    assert _xp_threshold(1) == 100
    assert _xp_threshold(5) == 500
    assert _xp_threshold(10) == 1000


def test_apply_xp_and_attrs_no_level_up():
    row = _make_row(experience=0, level=1)
    attrs = {"strength": 10}
    exp, level = _apply_xp_and_attrs(row, {"experience_gain": 50}, attrs)
    assert exp == 50
    assert level == 1


def test_apply_xp_and_attrs_triggers_level_up():
    row = _make_row(experience=80, level=1)
    attrs = {}
    exp, level = _apply_xp_and_attrs(row, {"experience_gain": 50}, attrs)
    # 80 + 50 = 130 >= 100 (threshold nÃ­vel 1) â†’ level up, residual = 30
    assert level == 2
    assert exp == 30


def test_apply_xp_and_attrs_attribute_floor_is_10():
    """Atributo nÃ£o pode cair abaixo de 10."""
    row = _make_row(experience=0, level=1)
    attrs = {"strength": 10}
    _exp, _lvl = _apply_xp_and_attrs(row, {"attribute_changes": {"strength": -50}}, attrs)
    assert attrs["strength"] == 10  # clampado


def test_apply_xp_and_attrs_ignores_unknown_attributes():
    """Delta de atributos desconhecidos nÃ£o deve inserir chaves novas."""
    row = _make_row(experience=0, level=1)
    attrs = {"strength": 10}
    _exp, _lvl = _apply_xp_and_attrs(row, {"attribute_changes": {"luck": 5}}, attrs)
    assert "luck" not in attrs


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------

async def test_append_history_and_retrieve_in_order(db):
    h1, h2, h3 = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())
    await state_manager.append_history(db, h1, turn_number=1, role="user", content="Ataco o goblin")
    await state_manager.append_history(db, h2, turn_number=1, role="assistant", content="O goblin morre.")
    await state_manager.append_history(db, h3, turn_number=2, role="user", content="AvanÃ§o para a caverna.")

    rows = await state_manager.get_recent_history(db, limit=10)

    assert len(rows) == 3
    assert rows[0]["role"] == "user"
    assert rows[0]["content"] == "Ataco o goblin"
    assert rows[-1]["content"] == "AvanÃ§o para a caverna."


async def test_get_recent_history_respects_limit(db):
    for i in range(15):
        await state_manager.append_history(
            db, str(uuid.uuid4()), turn_number=i, role="user", content=f"AÃ§Ã£o {i}"
        )
    rows = await state_manager.get_recent_history(db, limit=10)
    assert len(rows) == 10


async def test_get_current_turn_number_empty_returns_zero(db):
    turn = await state_manager.get_current_turn_number(db)
    assert turn == 0


async def test_get_current_turn_number_after_inserts(db):
    await state_manager.append_history(db, str(uuid.uuid4()), turn_number=7, role="user", content="x")
    turn = await state_manager.get_current_turn_number(db)
    assert turn == 7


# ---------------------------------------------------------------------------
# World state & Quest flags
# ---------------------------------------------------------------------------

async def test_set_and_get_world_state(db):
    await state_manager.set_world_state(db, "current_location", "Ilhas de Myr")
    val = await state_manager.get_world_state(db, "current_location")
    assert val == "Ilhas de Myr"


async def test_world_state_upsert_overwrites(db):
    await state_manager.set_world_state(db, "tension", "3")
    await state_manager.set_world_state(db, "tension", "8")
    val = await state_manager.get_world_state(db, "tension")
    assert val == "8"


async def test_get_world_state_missing_key_returns_none(db):
    val = await state_manager.get_world_state(db, "chave-inexistente")
    assert val is None


async def test_set_quest_flag_and_upsert(db):
    await state_manager.set_quest_flag(db, "ritual_started", "true")
    await state_manager.set_quest_flag(db, "ritual_started", "false")

    async with db.execute(
        "SELECT flag_value FROM quest_flags WHERE flag_key = 'ritual_started'"
    ) as cursor:
        row = await cursor.fetchone()
    assert row["flag_value"] == "false"


async def test_ensure_default_world_state_sets_start_location(db):
    await state_manager.ensure_default_world_state(db)
    location = await state_manager.get_world_state(db, "current_location")
    assert location == state_manager.DEFAULT_START_LOCATION


async def test_initialize_cooperative_mission_activates_for_party(db):
    pid1 = await _seed_character(db, player_id="coop-1")
    pid2 = await _seed_character(db, player_id="coop-2")

    snapshot = await state_manager.initialize_or_refresh_cooperative_mission(db)

    assert snapshot["cooperative_mission_active"] == "1"
    assert snapshot["cooperative_mission_completed"] == "0"
    assert snapshot["cooperative_mission_required_players"] == "2"
    assert await state_manager.get_quest_flag(db, f"cooperative_mission_player_done:{pid1}") == "0"
    assert await state_manager.get_quest_flag(db, f"cooperative_mission_player_done:{pid2}") == "0"


async def test_cooperative_mission_completes_when_all_alive_participate(db):
    pid1 = await _seed_character(db, player_id="coop-a")
    pid2 = await _seed_character(db, player_id="coop-b")
    await state_manager.initialize_or_refresh_cooperative_mission(db)

    mid = await state_manager.mark_cooperative_mission_participation(db, pid1)
    assert mid["cooperative_mission_active"] == "1"
    assert mid["cooperative_mission_completed_players"] == "1"

    done = await state_manager.mark_cooperative_mission_participation(db, pid2)
    assert done["cooperative_mission_active"] == "0"
    assert done["cooperative_mission_completed"] == "1"
    assert done["cooperative_mission_blocking"] == "0"


# ---------------------------------------------------------------------------
# Memory layers
# ---------------------------------------------------------------------------

async def test_get_memory_layers_empty_when_no_data(db):
    memory = await state_manager.get_memory_layers(db, ["player-x"])
    assert memory.character == ""
    assert memory.world == ""
    assert memory.arc == ""


async def test_upsert_character_memory_and_retrieve(db):
    pid = await _seed_player(db)
    await state_manager.upsert_character_memory(db, pid, "Kael teme o escuro.")
    memory = await state_manager.get_memory_layers(db, [pid])
    assert "Kael teme o escuro." in memory.character


async def test_upsert_world_memory(db):
    await state_manager.upsert_world_memory(db, "O Fio Primordial foi enfraquecido.")
    memory = await state_manager.get_memory_layers(db, [])
    assert "Fio Primordial" in memory.world


async def test_upsert_arc_memory(db):
    await state_manager.upsert_arc_memory(db, "Arco 1: A Chegada.")
    memory = await state_manager.get_memory_layers(db, [])
    assert "Arco 1" in memory.arc


# ---------------------------------------------------------------------------
# BYOK key
# ---------------------------------------------------------------------------

async def test_set_and_get_byok_key(db):
    pid = await _seed_player(db)
    await state_manager.set_byok_key(db, pid, "encrypted-key-xyz")
    key = await state_manager.get_byok_key(db, pid)
    assert key == "encrypted-key-xyz"


async def test_get_byok_key_missing_player_returns_none(db):
    key = await state_manager.get_byok_key(db, "nao-existe")
    assert key is None


# ---------------------------------------------------------------------------
# Mark convocation sent
# ---------------------------------------------------------------------------

async def test_mark_convocation_sent(db):
    pid = await _seed_player(db)
    await state_manager.mark_convocation_sent(db, pid)

    row = await state_manager.get_player_by_id(db, pid)
    assert row["convocation_sent"] == 1


# ---------------------------------------------------------------------------
# Dice roll argument flow
# ---------------------------------------------------------------------------

async def test_create_dice_roll_request_and_get(db):
    pid = await _seed_character(db)
    roll_id = str(uuid.uuid4())

    await state_manager.create_dice_roll_request(
        db,
        roll_id=roll_id,
        player_id=pid,
        roll_type="attack",
        dc=12,
        description="Ataque contra goblin",
    )

    row = await state_manager.get_dice_roll_request(db, roll_id)
    assert row is not None
    assert row["player_id"] == pid
    assert row["roll_type"] == "attack"
    assert row["dc"] == 12


async def test_submit_dice_roll_result_allows_only_one_argument(db):
    pid = await _seed_character(db)
    roll_id = str(uuid.uuid4())
    await state_manager.create_dice_roll_request(
        db,
        roll_id=roll_id,
        player_id=pid,
        roll_type="skill",
        dc=14,
        description="Escalar muro",
    )

    first = await state_manager.submit_dice_roll_result(
        db,
        roll_id=roll_id,
        player_id=pid,
        initial_roll=12,
        initial_result=14,
        argument="Tenho vantagem por corda",
    )
    second = await state_manager.submit_dice_roll_result(
        db,
        roll_id=roll_id,
        player_id=pid,
        initial_roll=18,
        initial_result=20,
        argument="Nova tentativa",
    )

    row = await state_manager.get_dice_roll_request(db, roll_id)
    assert first is True
    assert second is False
    assert row["argument_submitted"] == 1
    assert row["initial_roll"] == 12


async def test_resolve_dice_roll_accept_with_bonus(db):
    pid = await _seed_character(db)
    roll_id = str(uuid.uuid4())
    await state_manager.create_dice_roll_request(
        db,
        roll_id=roll_id,
        player_id=pid,
        roll_type="magic",
        dc=15,
        description="Canalizar chama",
    )
    await state_manager.submit_dice_roll_result(
        db,
        roll_id=roll_id,
        player_id=pid,
        initial_roll=13,
        initial_result=16,
        argument="Terreno favorece",
    )

    row = await state_manager.resolve_dice_roll(
        db,
        roll_id=roll_id,
        verdict="accept_with_bonus",
        circumstance_bonus=2,
        explanation="BÃ´nus aceito.",
    )

    assert row is not None
    assert row["verdict"] == "accept_with_bonus"
    assert row["circumstance_bonus"] == 2
    assert row["final_result"] == 18


async def test_set_and_get_character_macros(db):
    pid = await _seed_character(db)
    macros = [
        {"name": "/corte", "template": "Executo um corte horizontal."},
        {"name": "/estocar", "template": "FaÃ§o uma estocada precisa."},
    ]

    ok = await state_manager.set_character_macros(db, pid, macros)
    loaded = await state_manager.get_character_macros(db, pid)

    assert ok is True
    assert loaded == macros


async def test_update_backstory_marks_changed_recently(db):
    pid = await _seed_character(db)
    ok = await state_manager.update_backstory(db, pid, "Novo passado detalhado e coerente.")
    row = await state_manager.get_player_by_id(db, pid)

    assert ok is True
    assert row["backstory"] == "Novo passado detalhado e coerente."
    assert row["backstory_changed_recently"] == 1


async def test_seed_starter_inventory_creates_default_items_and_weight(db):
    pid = await _seed_character(db)
    await state_manager.seed_starter_inventory(db, pid, "um guerreiro com espada")

    rows = await state_manager.get_player_inventory(db, pid)
    names = {row["name"] for row in rows}
    player = await state_manager.get_player_by_id(db, pid)

    assert names == {"Arma BÃ¡sica", "Suprimentos", "Mochila"}
    assert player["inventory_weight"] > 0


async def test_set_and_get_spell_aliases(db):
    pid = await _seed_character(db)
    aliases = {
        "fogo": "LÃ¢mina Rubra",
        "ar": "Corte de Vendaval",
    }

    ok = await state_manager.set_spell_aliases(db, pid, aliases)
    loaded = await state_manager.get_spell_aliases(db, pid)

    assert ok is True
    assert loaded == aliases

