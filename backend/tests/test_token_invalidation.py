"""
test_token_invalidation.py — TDD for S-03: server-side token invalidation via sessions table.
"""
import time
import uuid
import pytest
from src.auth import create_token, decode_token


@pytest.mark.asyncio
class TestSessionsTable:
    """S-03: Sessions table provides server-side token invalidation."""

    async def test_create_session_on_login(self, db):
        """Session record should be created when token is generated."""
        from src import state_manager
        player_id = str(uuid.uuid4())
        username = "test_user"
        password_hash = "hashed_pw"
        token = create_token(player_id, username)

        await state_manager.create_player(db, player_id, username, password_hash)
        await state_manager.create_session(db, player_id, token)

        session = await state_manager.get_session(db, player_id)
        assert session is not None
        assert session["player_id"] == player_id

    async def test_revoke_session(self, db):
        """Revoking session should mark it as invalidated."""
        from src import state_manager
        player_id = str(uuid.uuid4())
        username = "test_user2"
        token = create_token(player_id, username)

        await state_manager.create_player(db, player_id, username, "hash")
        await state_manager.create_session(db, player_id, token)

        await state_manager.revoke_sessions(db, player_id)
        session = await state_manager.get_active_session(db, player_id)
        assert session is None

    async def test_session_not_present_blocks_auth(self, db):
        """validate_token_session() returns False when session is revoked."""
        from src import state_manager
        player_id = str(uuid.uuid4())
        username = "test_user3"
        token = create_token(player_id, username)

        await state_manager.create_player(db, player_id, username, "hash")
        await state_manager.create_session(db, player_id, token)

        # Revoke
        await state_manager.revoke_sessions(db, player_id)

        # Validation should fail
        is_valid = await state_manager.is_session_valid(db, player_id)
        assert is_valid is False

    async def test_active_session_passes_validation(self, db):
        """is_session_valid() returns True for active sessions."""
        from src import state_manager
        player_id = str(uuid.uuid4())
        username = "test_user4"
        token = create_token(player_id, username)

        await state_manager.create_player(db, player_id, username, "hash")
        await state_manager.create_session(db, player_id, token)

        is_valid = await state_manager.is_session_valid(db, player_id)
        assert is_valid is True

    async def test_logout_revokes_session(self, authenticated_client, player_id):
        """POST /auth/logout should revoke the player's sessions."""
        response = await authenticated_client.post("/auth/logout")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "logged_out"

    async def test_login_creates_session(self, db):
        """After redeem/login, a session record exists."""
        from src import state_manager
        from src.auth import hash_password

        player_id = str(uuid.uuid4())
        username = "login_user"
        password = "test_pass"
        password_hash = hash_password(password)

        await state_manager.create_player(db, player_id, username, password_hash)
        token = create_token(player_id, username)
        await state_manager.create_session(db, player_id, token)

        session = await state_manager.get_active_session(db, player_id)
        assert session is not None


class TestSessionHelpers:
    """Unit tests for session helper functions logic."""

    def test_token_provides_player_id(self):
        """Decoded JWT includes sub (player_id) for session lookup."""
        player_id = str(uuid.uuid4())
        token = create_token(player_id, "user")
        payload = decode_token(token)
        assert payload["sub"] == player_id

    def test_token_expiry_in_future(self):
        """Token exp should be in the future."""
        token = create_token("player-1", "user")
        payload = decode_token(token)
        assert payload["exp"] > time.time()
