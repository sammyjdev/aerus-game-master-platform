"""
test_b05_b06.py — B-05 Language Skill Enforcement + B-06 Isekai Rooting Timeline.
"""
import json

import pytest
import pytest_asyncio

from src import state_manager
from src.state_manager import apply_state_delta, maybe_advance_rooting


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _seed_player(conn, player_id, username):
    await state_manager.create_player(conn, player_id, username, "testhash")


async def _seed_character(conn, player_id, username, race="human"):
    await _seed_player(conn, player_id, username)
    await state_manager.set_character(
        conn, player_id, "Kael", race, "guild_of_threads",
        "A traveler from another world.", "Fighter", "Survive", 100
    )


# ---------------------------------------------------------------------------
# B-05: Language Skill Enforcement
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestLanguageSkills:
    async def test_learn_language_via_delta(self, db, player_id, username):
        await _seed_player(db, player_id, username)

        result = await apply_state_delta(db, player_id, {"learn_language": "valdrekian"})

        row = await state_manager.get_player_by_id(db, player_id)
        langs = json.loads(row["languages_json"])
        assert "valdrekian" in langs
        assert result.get("learned_language") == "valdrekian"

    async def test_learn_language_not_duplicated(self, db, player_id, username):
        await _seed_player(db, player_id, username)

        await apply_state_delta(db, player_id, {"learn_language": "valdrekian"})
        await apply_state_delta(db, player_id, {"learn_language": "valdrekian"})

        row = await state_manager.get_player_by_id(db, player_id)
        langs = json.loads(row["languages_json"])
        assert langs.count("valdrekian") == 1

    async def test_default_language_is_common_tongue(self, db, player_id, username):
        await _seed_player(db, player_id, username)

        row = await state_manager.get_player_by_id(db, player_id)
        langs = json.loads(row["languages_json"])
        assert "common_tongue" in langs

    async def test_delta_without_language_returns_no_learned_key(self, db, player_id, username):
        await _seed_player(db, player_id, username)

        result = await apply_state_delta(db, player_id, {"hp_change": 0})
        assert "learned_language" not in result

    async def test_learn_multiple_languages(self, db, player_id, username):
        await _seed_player(db, player_id, username)

        await apply_state_delta(db, player_id, {"learn_language": "valdrekian"})
        await apply_state_delta(db, player_id, {"learn_language": "myr_pidgin"})

        row = await state_manager.get_player_by_id(db, player_id)
        langs = json.loads(row["languages_json"])
        assert "common_tongue" in langs
        assert "valdrekian" in langs
        assert "myr_pidgin" in langs


@pytest.mark.asyncio
class TestLanguageContext:
    async def test_format_languages_uses_display_names(self):
        from src.context_builder import _format_languages

        result = _format_languages('["common_tongue", "valdrekian"]')
        assert "Common Tongue" in result
        assert "Valdrekian" in result

    async def test_format_languages_empty_returns_common_tongue(self):
        from src.context_builder import _format_languages

        assert _format_languages(None) == "Common Tongue"
        assert _format_languages("[]") == "Common Tongue"

    async def test_format_languages_unknown_key_shown_as_is(self):
        from src.context_builder import _format_languages

        result = _format_languages('["common_tongue", "mystery_tongue"]')
        assert "Common Tongue" in result
        assert "mystery_tongue" in result

    async def test_format_languages_all_known_keys(self):
        from src.context_builder import _format_languages, LANGUAGE_DISPLAY_NAMES

        all_keys = json.dumps(list(LANGUAGE_DISPLAY_NAMES.keys()))
        result = _format_languages(all_keys)
        for display in LANGUAGE_DISPLAY_NAMES.values():
            assert display in result


# ---------------------------------------------------------------------------
# B-06: Isekai Rooting Timeline
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestIsekaiRooting:
    async def test_rooting_stage_0_default(self, db, player_id, username):
        await _seed_character(db, player_id, username, race="human_isekai")

        row = await state_manager.get_player_by_id(db, player_id)
        assert row["rooting_stage"] == 0
        assert row["days_in_world"] == 0

    async def test_days_passed_delta_advances_days(self, db, player_id, username):
        await _seed_character(db, player_id, username)

        await apply_state_delta(db, player_id, {"days_passed": 100})

        row = await state_manager.get_player_by_id(db, player_id)
        assert row["days_in_world"] == 100

    async def test_days_passed_accumulates(self, db, player_id, username):
        await _seed_character(db, player_id, username)

        await apply_state_delta(db, player_id, {"days_passed": 200})
        await apply_state_delta(db, player_id, {"days_passed": 165})

        row = await state_manager.get_player_by_id(db, player_id)
        assert row["days_in_world"] == 365

    async def test_rooting_stage_advances_at_365(self, db, player_id, username):
        await _seed_character(db, player_id, username)

        result = await apply_state_delta(db, player_id, {"days_passed": 365})

        row = await state_manager.get_player_by_id(db, player_id)
        assert row["rooting_stage"] == 1
        assert result.get("rooting_advanced") == 1

    async def test_rooting_stage_advances_at_730(self, db, player_id, username):
        await _seed_character(db, player_id, username)

        result = await apply_state_delta(db, player_id, {"days_passed": 730})

        row = await state_manager.get_player_by_id(db, player_id)
        assert row["rooting_stage"] == 2
        assert result.get("rooting_advanced") == 2

    async def test_rooting_stage_advances_at_1825(self, db, player_id, username):
        await _seed_character(db, player_id, username)

        result = await apply_state_delta(db, player_id, {"days_passed": 1825})

        row = await state_manager.get_player_by_id(db, player_id)
        assert row["rooting_stage"] == 4
        assert result.get("rooting_advanced") == 4

    async def test_rooting_stage_does_not_regress(self, db, player_id, username):
        await _seed_character(db, player_id, username)

        # Advance to stage 2
        await apply_state_delta(db, player_id, {"days_passed": 730})
        row = await state_manager.get_player_by_id(db, player_id)
        assert row["rooting_stage"] == 2

        # Apply more days that don't reach stage 3 threshold (1095)
        result = await apply_state_delta(db, player_id, {"days_passed": 50})
        row = await state_manager.get_player_by_id(db, player_id)
        assert row["rooting_stage"] == 2
        assert "rooting_advanced" not in result

    async def test_rooting_no_advance_before_threshold(self, db, player_id, username):
        await _seed_character(db, player_id, username)

        result = await apply_state_delta(db, player_id, {"days_passed": 100})

        row = await state_manager.get_player_by_id(db, player_id)
        assert row["rooting_stage"] == 0
        assert "rooting_advanced" not in result

    async def test_maybe_advance_rooting_returns_new_stage(self, db, player_id, username):
        await _seed_character(db, player_id, username)

        new_stage = await maybe_advance_rooting(db, player_id, 365)
        assert new_stage == 1

        row = await state_manager.get_player_by_id(db, player_id)
        assert row["rooting_stage"] == 1

    async def test_maybe_advance_rooting_no_regression(self, db, player_id, username):
        await _seed_character(db, player_id, username)

        # Manually set to stage 2
        await db.execute(
            "UPDATE players SET rooting_stage = 2, days_in_world = 730 WHERE player_id = ?",
            (player_id,),
        )
        await db.commit()

        # Same threshold as stage 2 — should not change
        result = await maybe_advance_rooting(db, player_id, 730)
        assert result is None

        row = await state_manager.get_player_by_id(db, player_id)
        assert row["rooting_stage"] == 2

    async def test_days_passed_result_empty_when_no_advance(self, db, player_id, username):
        await _seed_character(db, player_id, username)

        result = await apply_state_delta(db, player_id, {"days_passed": 10})
        assert "rooting_advanced" not in result
