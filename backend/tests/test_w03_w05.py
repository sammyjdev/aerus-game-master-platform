"""
test_w03_w05.py — TDD tests for:
  W-03: faction_objective_update WS message schema and emission
  W-05: dice_result WS message and /game/roll endpoint
"""
import pytest


# ── W-03: FactionObjectiveUpdateMessage schema ────────────────────────────────

class TestFactionObjectiveUpdateSchema:
    def test_faction_update_message_valid(self):
        from src.ws_contracts import FactionObjectiveUpdateMessage
        msg = FactionObjectiveUpdateMessage(
            faction="merchants",
            objective="trade_route",
            status="in_progress",
            cred_change=5.0,
        )
        assert msg.type == "faction_objective_update"
        assert msg.faction == "merchants"
        assert msg.cred_change == 5.0

    def test_faction_update_status_enum(self):
        from src.ws_contracts import FactionObjectiveUpdateMessage
        import pydantic
        with pytest.raises((pydantic.ValidationError, ValueError)):
            FactionObjectiveUpdateMessage(
                faction="x", objective="y", status="invalid_status", cred_change=0
            )

    def test_faction_update_in_outgoing_union(self):
        from src.ws_contracts import OutgoingWSMessage
        from pydantic import TypeAdapter
        ta = TypeAdapter(OutgoingWSMessage)
        msg = ta.validate_python({
            "type": "faction_objective_update",
            "faction": "merchants",
            "objective": "trade",
            "status": "completed",
            "cred_change": 10.0,
        })
        assert msg.type == "faction_objective_update"


# ── W-05: dice_result WS message and /game/roll endpoint ─────────────────────

@pytest.mark.asyncio
class TestDiceResult:
    async def test_roll_dice_valid(self, authenticated_client):
        resp = await authenticated_client.post("/game/roll", json={"die": 6})
        assert resp.status_code == 200
        data = resp.json()
        assert 1 <= data["result"] <= 6
        assert data["die"] == 6

    async def test_roll_dice_natural_20(self, authenticated_client):
        resp = await authenticated_client.post("/game/roll", json={"die": 20})
        assert resp.status_code == 200
        data = resp.json()
        assert 1 <= data["result"] <= 20

    async def test_roll_dice_invalid_die(self, authenticated_client):
        resp = await authenticated_client.post("/game/roll", json={"die": 1})
        assert resp.status_code == 422

    async def test_roll_dice_negative_die(self, authenticated_client):
        resp = await authenticated_client.post("/game/roll", json={"die": -5})
        assert resp.status_code == 422

    async def test_roll_dice_unauthenticated(self, client):
        resp = await client.post("/game/roll", json={"die": 20})
        assert resp.status_code == 401

    async def test_dice_result_ws_message_valid(self):
        from src.ws_contracts import OutgoingWSMessage
        from pydantic import TypeAdapter
        ta = TypeAdapter(OutgoingWSMessage)
        msg = ta.validate_python({
            "type": "dice_result",
            "player_id": "p123",
            "die": 20,
            "result": 15,
        })
        assert msg.type == "dice_result"
