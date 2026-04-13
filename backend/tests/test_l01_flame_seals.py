"""
test_l01_flame_seals.py — TDD tests for the Flame Seal system (L-01).

Tests cover:
- Schema: players.flame_seal column defaults to NULL
- apply_state_delta: grant_seal / revoke_seal delta keys
- Invalid seal types are silently ignored
- Double grant replaces the previous seal
- null_seal is stored correctly
- WS contract: SealEventMessage validates via OutgoingWSMessage union
"""
import uuid

import pytest
import pytest_asyncio

from src import state_manager
from src.auth import hash_password


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _create_player(conn, player_id: str, username: str) -> None:
    pw_hash = hash_password("test_pw_secure_123")
    await state_manager.create_player(conn, player_id, username, pw_hash)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def pid():
    return str(uuid.uuid4())


@pytest.fixture()
def uname():
    return f"sealuser_{uuid.uuid4().hex[:8]}"


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestFlameSealSchema:
    async def test_player_starts_with_no_seal(self, db, pid, uname):
        """flame_seal defaults to NULL for a freshly created player."""
        await _create_player(db, pid, uname)
        row = await state_manager.get_player_by_id(db, pid)
        assert row is not None
        assert row["flame_seal"] is None

    async def test_grant_seal_via_delta(self, db, pid, uname):
        """grant_seal delta sets flame_seal on the player."""
        await _create_player(db, pid, uname)
        result = await state_manager.apply_state_delta(db, pid, {"grant_seal": "trade"})
        assert result.get("seal_granted") == "trade"
        row = await state_manager.get_player_by_id(db, pid)
        assert row["flame_seal"] == "trade"

    async def test_grant_invalid_seal_is_ignored(self, db, pid, uname):
        """grant_seal with an unknown type writes nothing and doesn't crash."""
        await _create_player(db, pid, uname)
        result = await state_manager.apply_state_delta(db, pid, {"grant_seal": "fake_forbidden"})
        assert "seal_granted" not in result
        row = await state_manager.get_player_by_id(db, pid)
        assert row["flame_seal"] is None

    async def test_revoke_seal_clears_it(self, db, pid, uname):
        """revoke_seal sets flame_seal back to NULL."""
        await _create_player(db, pid, uname)
        await state_manager.apply_state_delta(db, pid, {"grant_seal": "common"})
        result = await state_manager.apply_state_delta(db, pid, {"revoke_seal": True})
        assert result.get("seal_revoked") is True
        row = await state_manager.get_player_by_id(db, pid)
        assert row["flame_seal"] is None

    async def test_double_grant_replaces_seal(self, db, pid, uname):
        """Granting a second seal replaces the first one."""
        await _create_player(db, pid, uname)
        await state_manager.apply_state_delta(db, pid, {"grant_seal": "common"})
        await state_manager.apply_state_delta(db, pid, {"grant_seal": "high_flame"})
        row = await state_manager.get_player_by_id(db, pid)
        assert row["flame_seal"] == "high_flame"

    async def test_null_seal_can_be_granted(self, db, pid, uname):
        """null_seal is a valid suppressgion seal and must be stored correctly."""
        await _create_player(db, pid, uname)
        result = await state_manager.apply_state_delta(db, pid, {"grant_seal": "null_seal"})
        assert result.get("seal_granted") == "null_seal"
        row = await state_manager.get_player_by_id(db, pid)
        assert row["flame_seal"] == "null_seal"

    async def test_all_valid_seal_types_accepted(self, db, pid, uname):
        """Every valid seal type can be granted without error."""
        await _create_player(db, pid, uname)
        valid_seals = ["common", "trade", "high_flame", "null_seal", "conclave"]
        for seal in valid_seals:
            result = await state_manager.apply_state_delta(db, pid, {"grant_seal": seal})
            assert result.get("seal_granted") == seal, f"Expected seal_granted={seal}"
        row = await state_manager.get_player_by_id(db, pid)
        assert row["flame_seal"] == "conclave"  # last granted

    async def test_revoke_when_no_seal_is_safe(self, db, pid, uname):
        """Revoking when no seal is held should succeed without error."""
        await _create_player(db, pid, uname)
        result = await state_manager.apply_state_delta(db, pid, {"revoke_seal": True})
        assert result.get("seal_revoked") is True
        row = await state_manager.get_player_by_id(db, pid)
        assert row["flame_seal"] is None


# ---------------------------------------------------------------------------
# WS contract tests
# ---------------------------------------------------------------------------

class TestSealEventWSContract:
    def test_seal_event_granted_validates(self):
        """SealEventMessage with action=granted validates via OutgoingWSMessage union."""
        from pydantic import TypeAdapter
        from src.ws_contracts import OutgoingWSMessage
        ta = TypeAdapter(OutgoingWSMessage)
        msg = ta.validate_python({
            "type": "seal_event",
            "player_id": "player-abc",
            "action": "granted",
            "seal_type": "trade",
        })
        assert msg.type == "seal_event"
        assert msg.action == "granted"
        assert msg.seal_type == "trade"

    def test_seal_event_revoked_validates(self):
        """SealEventMessage with action=revoked and null seal_type validates."""
        from pydantic import TypeAdapter
        from src.ws_contracts import OutgoingWSMessage
        ta = TypeAdapter(OutgoingWSMessage)
        msg = ta.validate_python({
            "type": "seal_event",
            "player_id": "player-xyz",
            "action": "revoked",
            "seal_type": None,
        })
        assert msg.type == "seal_event"
        assert msg.action == "revoked"
        assert msg.seal_type is None

    def test_seal_event_message_class_directly(self):
        """SealEventMessage can be imported and instantiated directly."""
        from src.ws_contracts import SealEventMessage
        msg = SealEventMessage(player_id="p1", action="granted", seal_type="high_flame")
        assert msg.type == "seal_event"
        assert msg.seal_type == "high_flame"
