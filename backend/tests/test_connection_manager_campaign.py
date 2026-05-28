"""Tests for campaign scoping in ConnectionManager broadcasts."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.connection_manager import ConnectionManager


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
