"""
test_o04_b07.py — Tests for:
  O-04: Normalized location IDs in travel.yaml (no Portuguese IDs)
  B-07: Passive milestone unlock logic in apply_state_delta
"""
import json
import os
import uuid

import pytest
import pytest_asyncio

from src import state_manager
from src.state_manager import apply_state_delta, create_player, set_character


# ── O-04: Location ID normalization ─────────────────────────────────────────

# Resolve path relative to the tests/ folder → backend/config/travel.yaml
TRAVEL_YAML_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "config", "travel.yaml")
)


class TestLocationIDNormalization:
    def test_no_portuguese_location_ids(self):
        import yaml

        with open(TRAVEL_YAML_PATH, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        portuguese_patterns = [
            "fendas_de",
            "passagem_",
            "coracao_cinzas",
            "urbes_ambulantes",
        ]
        for loc_id in data.get("locations", {}).keys():
            for pat in portuguese_patterns:
                assert pat not in loc_id, f"Still has Portuguese ID: {loc_id}"

    def test_english_replacements_present(self):
        import yaml

        with open(TRAVEL_YAML_PATH, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        location_ids = set(data.get("locations", {}).keys())
        for expected in ("gorath_fissures", "ondrek_passage", "ash_heart", "wandering_cities"):
            assert expected in location_ids, f"Expected location ID '{expected}' not found"

    def test_all_routes_reference_valid_locations(self):
        import yaml

        with open(TRAVEL_YAML_PATH, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        location_ids = set(data.get("locations", {}).keys())
        for route_id, route in data.get("routes", {}).items():
            for segment in route.get("segments", []):
                dest = segment.get("destination")
                if dest:
                    assert dest in location_ids, (
                        f"Route '{route_id}' references unknown destination '{dest}'"
                    )


# ── B-07: Passive milestone unlock logic ─────────────────────────────────────

async def _make_player(conn) -> str:
    """Create + configure a player with default attributes (all = 10)."""
    pid = str(uuid.uuid4())
    await create_player(conn, pid, f"user_{pid[:8]}", "hash")
    await set_character(
        conn,
        pid,
        f"char_{pid[:8]}",
        "human",
        "guild_of_threads",
        "A test backstory.",
        "Adventurer",
        "secret",
        100,
    )
    return pid


@pytest.mark.asyncio
class TestPassiveMilestones:
    async def test_strength_milestone_unlocked_at_20(self, db):
        pid = await _make_player(db)
        # Default strength = 10; +10 reaches 20 → unlocks iron_physique
        result = await apply_state_delta(db, pid, {"attribute_changes": {"strength": 10}})
        assert "iron_physique" in result["milestones_unlocked"]

        async with db.execute(
            "SELECT milestones_json FROM players WHERE player_id = ?", (pid,)
        ) as cur:
            row = await cur.fetchone()
        assert "iron_physique" in json.loads(row["milestones_json"])

    async def test_milestone_not_duplicated_on_second_call(self, db):
        pid = await _make_player(db)
        # First call unlocks iron_physique
        await apply_state_delta(db, pid, {"attribute_changes": {"strength": 10}})
        # Second call with same (or higher) strength should NOT duplicate
        result2 = await apply_state_delta(db, pid, {})
        assert "iron_physique" not in result2["milestones_unlocked"]

        async with db.execute(
            "SELECT milestones_json FROM players WHERE player_id = ?", (pid,)
        ) as cur:
            row = await cur.fetchone()
        milestones = json.loads(row["milestones_json"])
        assert milestones.count("iron_physique") == 1

    async def test_level_milestone_veteran(self, db):
        pid = await _make_player(db)
        # Directly set level = 10 in DB so the next delta triggers the "veteran" check
        await db.execute("UPDATE players SET level = 10 WHERE player_id = ?", (pid,))
        await db.commit()

        result = await apply_state_delta(db, pid, {})
        assert "veteran" in result["milestones_unlocked"]

        async with db.execute(
            "SELECT milestones_json FROM players WHERE player_id = ?", (pid,)
        ) as cur:
            row = await cur.fetchone()
        assert "veteran" in json.loads(row["milestones_json"])

    async def test_no_milestone_below_threshold(self, db):
        pid = await _make_player(db)
        # Default attributes are all 10: no threshold crossed → no milestones
        result = await apply_state_delta(db, pid, {})
        assert result["milestones_unlocked"] == []

    async def test_multiple_milestones_same_call(self, db):
        pid = await _make_player(db)
        # Raise both strength and intelligence to 20 in one delta
        result = await apply_state_delta(
            db, pid, {"attribute_changes": {"strength": 10, "intelligence": 10}}
        )
        assert "iron_physique" in result["milestones_unlocked"]
        assert "arcane_clarity" in result["milestones_unlocked"]

    async def test_legend_milestone_at_level_25(self, db):
        pid = await _make_player(db)
        await db.execute("UPDATE players SET level = 25 WHERE player_id = ?", (pid,))
        await db.commit()

        result = await apply_state_delta(db, pid, {})
        unlocked = result["milestones_unlocked"]
        # level 25 ≥ 10 → veteran; level 25 ≥ 25 → legend
        assert "veteran" in unlocked
        assert "legend" in unlocked

    async def test_result_always_has_milestones_unlocked_key(self, db):
        pid = await _make_player(db)
        result = await apply_state_delta(db, pid, {})
        assert "milestones_unlocked" in result

    async def test_player_not_found_returns_empty(self, db):
        result = await apply_state_delta(db, "nonexistent-player-id", {})
        assert result == {"milestones_unlocked": []}
