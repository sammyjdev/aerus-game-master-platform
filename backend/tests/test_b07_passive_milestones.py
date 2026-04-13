"""
test_b07_passive_milestones.py — Tests for passive milestone unlock logic in apply_state_delta.
"""
import json
import uuid

import pytest

from src import state_manager
from src.state_manager import _check_passive_milestones


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _seed_character(conn, player_id=None, username=None):
    pid = player_id or str(uuid.uuid4())
    uname = username or f"user_{pid[:8]}"
    await state_manager.create_player(conn, pid, uname, "testhash")
    await state_manager.set_character(
        conn,
        player_id=pid,
        name="Test Hero",
        race="human",
        faction="guild_of_threads",
        backstory="A wanderer.",
        inferred_class="Adventurer",
        secret_objective="",
        max_hp=100,
    )
    return pid


# ---------------------------------------------------------------------------
# Unit tests for _check_passive_milestones (pure function)
# ---------------------------------------------------------------------------

def test_check_passive_milestones_strength():
    attrs = {"strength": 20, "intelligence": 10, "vitality": 10,
             "dexterity": 10, "charisma": 10, "luck": 10}
    result = _check_passive_milestones(attrs, level=1, existing_milestones=[])
    assert "iron_physique" in result


def test_check_passive_milestones_all_attrs_at_threshold():
    attrs = {"strength": 20, "intelligence": 20, "vitality": 20,
             "dexterity": 20, "charisma": 20, "luck": 20}
    result = _check_passive_milestones(attrs, level=1, existing_milestones=[])
    expected = {"iron_physique", "arcane_clarity", "unwavering_endurance",
                "shadow_step", "voice_of_the_realm", "fortune_favored"}
    assert expected.issubset(set(result))


def test_check_passive_milestones_below_threshold():
    attrs = {"strength": 19, "intelligence": 19, "vitality": 10,
             "dexterity": 10, "charisma": 10, "luck": 10}
    result = _check_passive_milestones(attrs, level=1, existing_milestones=[])
    assert result == []


def test_check_passive_milestones_no_duplicates():
    attrs = {"strength": 20, "intelligence": 10, "vitality": 10,
             "dexterity": 10, "charisma": 10, "luck": 10}
    result = _check_passive_milestones(attrs, level=1, existing_milestones=["iron_physique"])
    assert "iron_physique" not in result


def test_check_passive_milestones_veteran_at_level_10():
    attrs = {"strength": 10, "intelligence": 10, "vitality": 10,
             "dexterity": 10, "charisma": 10, "luck": 10}
    result = _check_passive_milestones(attrs, level=10, existing_milestones=[])
    assert "veteran" in result


def test_check_passive_milestones_legend_at_level_25():
    attrs = {"strength": 10, "intelligence": 10, "vitality": 10,
             "dexterity": 10, "charisma": 10, "luck": 10}
    result = _check_passive_milestones(attrs, level=25, existing_milestones=[])
    assert "veteran" in result
    assert "legend" in result


def test_check_passive_milestones_veteran_not_duplicated():
    attrs = {"strength": 10, "intelligence": 10, "vitality": 10,
             "dexterity": 10, "charisma": 10, "luck": 10}
    result = _check_passive_milestones(attrs, level=10, existing_milestones=["veteran"])
    assert "veteran" not in result


# ---------------------------------------------------------------------------
# Integration tests via apply_state_delta
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_strength_milestone_unlocked_via_delta(db):
    pid = await _seed_character(db)
    result = await state_manager.apply_state_delta(
        db, pid, {"attribute_changes": {"strength": 10}}
    )
    assert "iron_physique" in result["milestones_unlocked"]

    row = await state_manager.get_player_by_id(db, pid)
    milestones = json.loads(row["milestones_json"])
    assert "iron_physique" in milestones


@pytest.mark.asyncio
async def test_milestone_not_duplicated_on_repeat_delta(db):
    pid = await _seed_character(db)
    # First delta — should unlock iron_physique
    await state_manager.apply_state_delta(
        db, pid, {"attribute_changes": {"strength": 10}}
    )
    # Second delta — same attribute, should NOT re-add iron_physique
    result2 = await state_manager.apply_state_delta(
        db, pid, {"attribute_changes": {"strength": 0}}
    )
    assert "iron_physique" not in result2["milestones_unlocked"]

    row = await state_manager.get_player_by_id(db, pid)
    milestones = json.loads(row["milestones_json"])
    assert milestones.count("iron_physique") == 1


@pytest.mark.asyncio
async def test_level_milestone_veteran_via_xp(db):
    pid = await _seed_character(db)
    # Give enough XP to reach level 10 (levels 1-9 threshold: 100*level each)
    # Sum of 100+200+...+900 = 4500 XP needed for level 10
    xp_to_level_10 = sum(i * 100 for i in range(1, 10))
    result = await state_manager.apply_state_delta(
        db, pid, {"experience_gain": xp_to_level_10}
    )
    assert "veteran" in result["milestones_unlocked"]

    row = await state_manager.get_player_by_id(db, pid)
    milestones = json.loads(row["milestones_json"])
    assert "veteran" in milestones


@pytest.mark.asyncio
async def test_no_milestone_below_threshold(db):
    pid = await _seed_character(db)
    result = await state_manager.apply_state_delta(
        db, pid, {"attribute_changes": {"strength": 5}}
    )
    # strength goes to 15, not yet 20
    assert result["milestones_unlocked"] == []


@pytest.mark.asyncio
async def test_milestones_unlocked_list_in_return_value(db):
    pid = await _seed_character(db)
    result = await state_manager.apply_state_delta(
        db, pid, {"attribute_changes": {"charisma": 10}}
    )
    assert "milestones_unlocked" in result
    assert isinstance(result["milestones_unlocked"], list)
    assert "voice_of_the_realm" in result["milestones_unlocked"]


@pytest.mark.asyncio
async def test_multiple_milestones_in_one_delta(db):
    pid = await _seed_character(db)
    result = await state_manager.apply_state_delta(
        db, pid,
        {"attribute_changes": {"strength": 10, "intelligence": 10, "vitality": 10}}
    )
    unlocked = set(result["milestones_unlocked"])
    assert "iron_physique" in unlocked
    assert "arcane_clarity" in unlocked
    assert "unwavering_endurance" in unlocked


@pytest.mark.asyncio
async def test_missing_player_returns_empty_milestones(db):
    result = await state_manager.apply_state_delta(
        db, "nonexistent-player-id", {"attribute_changes": {"strength": 10}}
    )
    assert result["milestones_unlocked"] == []
