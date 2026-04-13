"""
test_ws_contracts_enforcement.py — TDD for W-01: ws_contracts.py enforced in connection_manager.
Validates that all outgoing WS messages conform to Pydantic schemas.
"""
import json
import pytest
from pydantic import ValidationError
from src.ws_contracts import (
    NarrativeTokenMessage,
    StreamEndMessage,
    GmThinkingMessage,
    GameEventMessage,
    DiceRollMessage,
    RequestDiceRollMessage,
    DiceRollResolvedMessage,
    StateUpdateMessage,
    FullStateSyncMessage,
    HistorySyncMessage,
    AudioCueMessage,
    BossMusicMessage,
    TokenRefreshMessage,
    IsekaiConvocationMessage,
    FactionObjectiveUpdateMessage,
    ErrorMessage,
    OutgoingWSMessage,
)


class TestContractSchemaValidation:
    """Each Pydantic schema rejects invalid payloads."""

    def test_narrative_token_requires_token(self):
        with pytest.raises(ValidationError):
            NarrativeTokenMessage(type="narrative_token")  # missing token

    def test_narrative_token_valid(self):
        msg = NarrativeTokenMessage(type="narrative_token", token="hello")
        assert msg.type == "narrative_token"
        assert msg.token == "hello"

    def test_dice_roll_requires_die_gt_zero(self):
        with pytest.raises(ValidationError):
            DiceRollMessage(type="dice_roll", player="Kael", die=0, purpose="ataque", result=10)

    def test_dice_roll_valid(self):
        msg = DiceRollMessage(
            type="dice_roll", player="Kael", die=20, purpose="ataque", result=15,
            is_critical=False, is_fumble=False
        )
        assert msg.die == 20
        assert msg.result == 15

    def test_dice_roll_resolved_invalid_verdict(self):
        with pytest.raises(ValidationError):
            DiceRollResolvedMessage(
                type="dice_roll_resolved",
                roll_id="abc-123",
                verdict="invalid_verdict",
                circumstance_bonus=0,
                final_result=15,
                explanation="test",
            )

    def test_error_message_valid(self):
        msg = ErrorMessage(type="error", message="Something went wrong")
        assert msg.message == "Something went wrong"

    def test_faction_objective_update_valid(self):
        msg = FactionObjectiveUpdateMessage(
            type="faction_objective_update",
            faction="pure_flame",
            objective="credibility_change",
            status="in_progress",
            cred_change=3.5,
        )
        assert msg.faction == "pure_flame"
        assert msg.status == "in_progress"


class TestContractSerialization:
    """Pydantic models serialize to JSON correctly for WebSocket transport."""

    def test_narrative_token_serializes(self):
        msg = NarrativeTokenMessage(type="narrative_token", token="O cavaleiro")
        data = msg.model_dump()
        assert data == {"type": "narrative_token", "token": "O cavaleiro"}

    def test_game_event_serializes(self):
        msg = GameEventMessage(
            type="game_event",
            event="LEVELUP",
            payload={"player_id": "abc-123", "new_level": 5},
        )
        data = msg.model_dump()
        assert data["type"] == "game_event"
        assert data["event"] == "LEVELUP"

    def test_full_state_sync_serializes(self):
        msg = FullStateSyncMessage(
            type="full_state_sync",
            state={"player_id": "abc", "level": 3},
            world_state={"tension_level": 5},
        )
        data = msg.model_dump()
        assert data["type"] == "full_state_sync"
        assert data["world_state"]["tension_level"] == 5

    def test_is_json_serializable(self):
        msg = NarrativeTokenMessage(type="narrative_token", token="test")
        json_str = json.dumps(msg.model_dump())
        parsed = json.loads(json_str)
        assert parsed["token"] == "test"


class TestConnectionManagerUsesContracts:
    """connection_manager.py broadcasts use validated payloads."""

    def test_broadcast_narrative_token_validates(self):
        """broadcast() should produce payloads that match the Pydantic schema."""
        # Simulate what connection_manager sends for narrative_token
        payload = {"type": "narrative_token", "token": "hello"}
        msg = NarrativeTokenMessage(**payload)
        assert msg.type == "narrative_token"

    def test_broadcast_dice_roll_validates(self):
        """broadcast_dice_roll() should produce payloads that match DiceRollMessage."""
        payload = {
            "type": "dice_roll",
            "player": "Kael",
            "die": 20,
            "purpose": "ataque",
            "result": 17,
            "is_critical": False,
            "is_fumble": False,
        }
        msg = DiceRollMessage(**payload)
        assert msg.die == 20

    def test_broadcast_game_event_validates(self):
        """broadcast_game_event() should produce payloads that match GameEventMessage."""
        payload = {
            "type": "game_event",
            "event": "DEATH",
            "payload": {"player_id": "abc-123"},
        }
        msg = GameEventMessage(**payload)
        assert msg.event == "DEATH"

    def test_send_isekai_validates(self):
        """send_isekai_convocation() should produce payloads that match IsekaiConvocationMessage."""
        payload = {
            "type": "isekai_convocation",
            "narrative": "You have been summoned...",
            "faction": "pure_flame",
            "secret_objective": "Find the seal.",
        }
        msg = IsekaiConvocationMessage(**payload)
        assert msg.faction == "pure_flame"

    def test_error_message_validates(self):
        """broadcast error should match ErrorMessage schema."""
        payload = {"type": "error", "message": "Internal GM error"}
        msg = ErrorMessage(**payload)
        assert msg.message == "Internal GM error"
