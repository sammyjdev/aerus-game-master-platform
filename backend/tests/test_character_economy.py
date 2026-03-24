import json
import uuid

import pytest

from src import state_manager


async def _seed_player(conn, player_id, username="test", pw_hash="hash"):
    await state_manager.create_player(conn, player_id, username, pw_hash)


@pytest.mark.asyncio
async def test_set_character_initial_currency_defaults_to_5_silver(db):
    player_id = str(uuid.uuid4())
    await _seed_player(db, player_id, username="silver-starter")

    await state_manager.set_character(
        db,
        player_id=player_id,
        name="Arin",
        race="humano",
        faction="guild_of_threads",
        backstory="Um viajante sem armadura.",
        inferred_class="Aventureiro",
        secret_objective="Sobreviver",
        max_hp=100,
    )

    row = await state_manager.get_player_by_id(db, player_id)
    currency = json.loads(row["currency_json"])

    assert currency == {
        "copper": 0,
        "silver": 5,
        "gold": 0,
        "platinum": 0,
    }


@pytest.mark.asyncio
async def test_set_character_initial_weight_fields_are_set(db):
    player_id = str(uuid.uuid4())
    await _seed_player(db, player_id, username="weight-starter")

    await state_manager.set_character(
        db,
        player_id=player_id,
        name="Kael",
        race="humano",
        faction="guild_of_threads",
        backstory="Chega sem equipamentos pesados.",
        inferred_class="Aventureiro",
        secret_objective="Explorar",
        max_hp=100,
    )

    row = await state_manager.get_player_by_id(db, player_id)
    assert row["inventory_weight"] == pytest.approx(0.0)
    assert row["weight_capacity"] == pytest.approx(80.0)

