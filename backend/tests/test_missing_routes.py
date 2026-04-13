"""
test_missing_routes.py — Integration tests for Tier 1 missing endpoints (TDD).
Tests for: A-01 (admin routes), A-02 (auth/me, logout, etc.), A-07 (health)
"""
import pytest
from httpx import AsyncClient
from fastapi import status
from src.auth import create_token
from src.models import LoginRequest, CreateCharacterRequest, Faction, Race


@pytest.mark.asyncio
class TestHealthEndpoint:
    """GAP A-07: GET /health deployment probe."""

    async def test_health_endpoint_exists(self, client: AsyncClient):
        """GET /health should exist and return 200."""
        response = await client.get("/health")
        assert response.status_code == status.HTTP_200_OK

    async def test_health_endpoint_structure(self, client: AsyncClient):
        """GET /health should return JSON with status."""
        response = await client.get("/health")
        data = response.json()
        assert "status" in data
        assert data["status"] == "ok"

    async def test_health_endpoint_no_auth_required(self, client: AsyncClient):
        """GET /health should not require authentication."""
        # No Authorization header
        response = await client.get("/health")
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
class TestAuthMeEndpoint:
    """GAP A-02: GET /auth/me for current user profile."""

    async def test_auth_me_returns_current_user(self, authenticated_client: AsyncClient, player_id: str, username: str):
        """GET /auth/me returns current player profile."""
        response = await authenticated_client.get("/auth/me")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["player_id"] == player_id
        assert data["username"] == username

    async def test_auth_me_requires_auth(self, client: AsyncClient):
        """GET /auth/me should require authentication."""
        response = await client.get("/auth/me")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_auth_me_with_expired_token(self, client: AsyncClient):
        """GET /auth/me with expired token should return 401."""
        # This would require mocking time or manually creating an expired token
        pass  # Defer to integration tests


@pytest.mark.asyncio
class TestAuthLogoutEndpoint:
    """GAP A-02: POST /auth/logout for session termination."""

    async def test_logout_succeeds(self, authenticated_client: AsyncClient):
        """POST /auth/logout should return 200."""
        response = await authenticated_client.post("/auth/logout")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "status" in data

    async def test_logout_requires_auth(self, client: AsyncClient):
        """POST /auth/logout should require authentication."""
        response = await client.post("/auth/logout")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
class TestDeleteApiKeyEndpoint:
    """GAP A-04: DELETE /player/api-key for BYOK removal."""

    async def test_delete_api_key_succeeds(self, authenticated_client: AsyncClient):
        """DELETE /player/api-key should return 200."""
        # First, set a key
        await authenticated_client.post("/player/byok", json={"openrouter_api_key": "sk-test-123"})
        # Then delete it
        response = await authenticated_client.delete("/player/api-key")
        assert response.status_code == status.HTTP_200_OK

    async def test_delete_api_key_requires_auth(self, client: AsyncClient):
        """DELETE /player/api-key should require authentication."""
        response = await client.delete("/player/api-key")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
class TestAdminPlayersEndpoint:
    """GAP A-01: GET /admin/players for listing players."""

    async def test_admin_players_requires_admin_secret(self, client: AsyncClient):
        """GET /admin/players should require X-Admin-Secret header."""
        response = await client.get("/admin/players")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_admin_players_with_valid_secret(self, admin_client: AsyncClient):
        """GET /admin/players with valid secret returns player list."""
        response = await admin_client.get("/admin/players")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "players" in data
        assert isinstance(data["players"], list)

    async def test_admin_players_response_structure(self, admin_client: AsyncClient):
        """Response should include player ID, username, status."""
        response = await admin_client.get("/admin/players")
        data = response.json()
        if data["players"]:
            player = data["players"][0]
            assert "player_id" in player
            assert "username" in player
            assert "status" in player


@pytest.mark.asyncio
class TestAdminPauseEndpoint:
    """GAP A-01: POST /admin/pause for campaign pause."""

    async def test_admin_pause_requires_admin_secret(self, client: AsyncClient):
        """POST /admin/pause should require X-Admin-Secret header."""
        response = await client.post("/admin/pause", json={"paused": True})
        assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_admin_pause_sets_pause_state(self, admin_client: AsyncClient):
        """POST /admin/pause sets campaign pause state."""
        response = await admin_client.post("/admin/pause", json={"paused": True})
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["campaign_paused"] is True

    async def test_admin_pause_resume(self, admin_client: AsyncClient):
        """POST /admin/pause can resume campaign."""
        # Pause
        await admin_client.post("/admin/pause", json={"paused": True})
        # Resume
        response = await admin_client.post("/admin/pause", json={"paused": False})
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["campaign_paused"] is False


@pytest.mark.asyncio
class TestAdminReloadEndpoint:
    """GAP A-01: POST /admin/reload for config reload."""

    async def test_admin_reload_requires_admin_secret(self, client: AsyncClient):
        """POST /admin/reload should require X-Admin-Secret header."""
        response = await client.post("/admin/reload")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_admin_reload_succeeds(self, admin_client: AsyncClient):
        """POST /admin/reload should return 200 and reload config."""
        response = await admin_client.post("/admin/reload")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "status" in data or "message" in data


@pytest.mark.asyncio
class TestAdminInvitesEndpoint:
    """GAP A-05: GET /admin/invites to list invite codes."""

    async def test_admin_invites_requires_admin_secret(self, client: AsyncClient):
        """GET /admin/invites should require X-Admin-Secret header."""
        response = await client.get("/admin/invites")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_admin_invites_returns_list(self, admin_client: AsyncClient):
        """GET /admin/invites returns a list of invites."""
        response = await admin_client.get("/admin/invites")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "invites" in data
        assert isinstance(data["invites"], list)

    async def test_admin_invites_include_metadata(self, admin_client: AsyncClient):
        """Invite objects should include code, created_by, created_at, used status."""
        response = await admin_client.get("/admin/invites")
        data = response.json()
        if data["invites"]:
            invite = data["invites"][0]
            assert "code" in invite
            assert "created_by" in invite
            assert "created_at" in invite
            assert "used" in invite


@pytest.mark.asyncio
class TestGameHistoryEndpoint:
    """GAP A-06: GET /game/history to retrieve narrative history via REST."""

    async def test_game_history_requires_auth(self, client: AsyncClient):
        """GET /game/history should require authentication."""
        response = await client.get("/game/history")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_game_history_returns_history(self, authenticated_client: AsyncClient):
        """GET /game/history returns narrative history."""
        response = await authenticated_client.get("/game/history")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "history" in data
        assert isinstance(data["history"], list)

    async def test_game_history_includes_turns(self, authenticated_client: AsyncClient):
        """History entries should include turn, role, content."""
        response = await authenticated_client.get("/game/history")
        data = response.json()
        if data["history"]:
            entry = data["history"][0]
            assert "role" in entry  # "user" or "assistant"
            assert "content" in entry
            assert "turn_number" in entry or "turn" in entry

    async def test_game_history_respects_limit(self, authenticated_client: AsyncClient):
        """GET /game/history?limit=5 should respect limit parameter."""
        response = await authenticated_client.get("/game/history?limit=5")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["history"]) <= 5
