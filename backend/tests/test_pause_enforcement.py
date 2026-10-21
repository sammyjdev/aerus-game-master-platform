"""Tests for campaign pause enforcement and client notifications."""
import asyncio
import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock

from src import game_master, main, state_manager
from src.auth import create_token
from src.models import WSMessageType


@pytest.mark.asyncio
async def test_admin_pause_broadcasts_game_event_to_campaign(db, monkeypatch):
    monkeypatch.setenv("ADMIN_SECRET", "test-admin-secret")
    manager = game_master.cm.manager

    # Mock sockets
    socket_default = AsyncMock()
    socket_other = AsyncMock()

    await manager.connect(socket_default, "p1", "Player1", campaign_id="default")
    await manager.connect(socket_other, "p2", "Player2", campaign_id="other_camp")

    async with AsyncClient(transport=ASGITransport(app=main.app), base_url="http://test") as client:
        resp = await client.post(
            "/admin/pause",
            headers={"X-Admin-Secret": "test-admin-secret"},
            json={"paused": True, "campaign_id": "default"},
        )
        assert resp.status_code == 200
        assert resp.json()["campaign_paused"] is True

    # Check that default campaign received the pause game event, but other campaign did not
    assert socket_default.send_text.await_count >= 1
    call_args = [call.args[0] for call in socket_default.send_text.call_args_list]
    assert any("CAMPAIGN_PAUSED" in arg or "campaign_paused" in arg for arg in call_args)
    assert socket_other.send_text.await_count == 0


@pytest.mark.asyncio
async def test_submit_action_rejected_when_campaign_paused(db, authenticated_client, player_id):
    # Pause the campaign
    await state_manager.set_world_state(db, "campaign_paused", "1", campaign_id="default")
    await db.commit()

    # Attempting to submit an action directly via submit_action must raise ValueError
    with pytest.raises(ValueError, match="paused"):
        await game_master.submit_action(player_id, "TestHero", "I try to walk forward.")


@pytest.mark.asyncio
async def test_ws_message_sends_error_when_campaign_paused(db, player_id, monkeypatch):
    await state_manager.create_player(db, player_id, "TestHero", "test-hash")
    await state_manager.set_character(
        db, player_id=player_id, name="TestHero", race="human",
        faction="guild_of_threads", backstory="A traveler.",
        inferred_class="Traveler", secret_objective="", max_hp=100,
    )
    await state_manager.set_world_state(db, "campaign_paused", "1", campaign_id="default")
    await db.commit()


    manager = game_master.cm.manager
    mock_socket = AsyncMock()
    await manager.connect(mock_socket, player_id, "TestHero", campaign_id="default")

    await main._handle_ws_message({"action": "I try to walk."}, player_id, "TestHero")

    assert mock_socket.send_text.await_count >= 1
    call_args = [call.args[0] for call in mock_socket.send_text.call_args_list]
    assert any("Campaign is paused" in arg for arg in call_args)
