"""Tests for campaign scoping in ConnectionManager broadcasts."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.connection_manager import (
    ConnectionManager,
    WSContractViolation,
    _validate_and_serialize,
)


def _fake_ws() -> MagicMock:
    ws = MagicMock()
    ws.accept = AsyncMock()
    ws.send_text = AsyncMock()
    return ws


@pytest.mark.asyncio
async def test_broadcast_without_campaign_reaches_all() -> None:
    mgr = ConnectionManager()
    ws_a, ws_b = _fake_ws(), _fake_ws()
    await mgr.connect(ws_a, "p1", "alice", campaign_id="campA")
    await mgr.connect(ws_b, "p2", "bob", campaign_id="campB")

    await mgr.broadcast({"type": "stream_end"})

    assert ws_a.send_text.await_count == 1
    assert ws_b.send_text.await_count == 1


@pytest.mark.asyncio
async def test_broadcast_with_campaign_scopes_recipients() -> None:
    mgr = ConnectionManager()
    ws_a, ws_b, ws_c = _fake_ws(), _fake_ws(), _fake_ws()
    await mgr.connect(ws_a, "p1", "alice", campaign_id="campA")
    await mgr.connect(ws_b, "p2", "bob", campaign_id="campA")
    await mgr.connect(ws_c, "p3", "carol", campaign_id="campB")

    await mgr.broadcast({"type": "stream_end"}, campaign_id="campA")

    assert ws_a.send_text.await_count == 1
    assert ws_b.send_text.await_count == 1
    assert ws_c.send_text.await_count == 0


@pytest.mark.asyncio
async def test_player_joined_excludes_self() -> None:
    mgr = ConnectionManager()
    ws_a, ws_b = _fake_ws(), _fake_ws()
    await mgr.connect(ws_a, "p1", "alice", campaign_id="campA")
    await mgr.connect(ws_b, "p2", "bob", campaign_id="campA")

    await mgr.broadcast_player_joined(
        "campA",
        {"player_id": "p2", "username": "bob"},
    )

    assert ws_a.send_text.await_count == 1
    assert ws_b.send_text.await_count == 0


@pytest.mark.asyncio
async def test_player_left_skips_other_campaign() -> None:
    mgr = ConnectionManager()
    ws_a, ws_c = _fake_ws(), _fake_ws()
    await mgr.connect(ws_a, "p1", "alice", campaign_id="campA")
    await mgr.connect(ws_c, "p3", "carol", campaign_id="campB")

    await mgr.broadcast_player_left("campA", "p2", "bob")

    assert ws_a.send_text.await_count == 1
    assert ws_c.send_text.await_count == 0


@pytest.mark.asyncio
async def test_connected_roster_in_campaign() -> None:
    mgr = ConnectionManager()
    await mgr.connect(_fake_ws(), "p1", "alice", campaign_id="campA")
    await mgr.connect(_fake_ws(), "p2", "bob", campaign_id="campA")
    await mgr.connect(_fake_ws(), "p3", "carol", campaign_id="campB")

    roster = mgr.connected_roster_in_campaign("campA")
    ids = sorted(entry["player_id"] for entry in roster)
    assert ids == ["p1", "p2"]


# --- ADR-014: fail-closed contract enforcement ---------------------------------


def test_validate_and_serialize_raises_on_contract_violation() -> None:
    """Bad payloads raise WSContractViolation rather than emitting unvalidated bytes."""
    with pytest.raises(WSContractViolation):
        # narrative_token requires a `token` field; omitting it must fail closed.
        _validate_and_serialize({"type": "narrative_token"})


@pytest.mark.asyncio
async def test_broadcast_drops_invalid_message_but_keeps_connection_alive() -> None:
    """A schema-violating broadcast is dropped; the connection survives and accepts the next valid message."""
    mgr = ConnectionManager()
    ws_a = _fake_ws()
    await mgr.connect(ws_a, "p1", "alice", campaign_id="campA")

    # Invalid: narrative_token without `token`. Must not be sent.
    await mgr.broadcast({"type": "narrative_token"}, campaign_id="campA")
    assert ws_a.send_text.await_count == 0
    assert "p1" in mgr.connected_player_ids()  # connection still alive

    # Valid follow-up message goes through on the same connection.
    await mgr.broadcast(
        {"type": "narrative_token", "token": "hello"}, campaign_id="campA"
    )
    assert ws_a.send_text.await_count == 1
    assert "p1" in mgr.connected_player_ids()


@pytest.mark.asyncio
async def test_send_to_drops_invalid_message_but_keeps_connection_alive() -> None:
    """send_to() returns False on contract violation without disconnecting the player."""
    mgr = ConnectionManager()
    ws_a = _fake_ws()
    await mgr.connect(ws_a, "p1", "alice", campaign_id="campA")

    ok = await mgr.send_to("p1", {"type": "narrative_token"})  # missing token
    assert ok is False
    assert ws_a.send_text.await_count == 0
    assert "p1" in mgr.connected_player_ids()

    # Valid message still goes through.
    ok2 = await mgr.send_to("p1", {"type": "narrative_token", "token": "hi"})
    assert ok2 is True
    assert ws_a.send_text.await_count == 1
    assert "p1" in mgr.connected_player_ids()
