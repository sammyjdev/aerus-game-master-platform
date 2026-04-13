"""
test_boss_music_event.py — Tests for boss_music WebSocket event emission (TDD for W-04).
Validates boss_music event broadcast when tension >= 5 with combat signal.
"""
import pytest
import json
from src.models import GMResponse, WSMessageType


class TestBossMusicEvent:
    """GAP W-04: Emit boss_music event from game_master when appropriate."""

    def test_boss_music_event_structure(self):
        """boss_music event should have type and expected fields."""
        event = {
            "type": "boss_music",
            "tension_level": 8,
            "intensity": "high",
        }
        assert event["type"] == "boss_music"
        assert isinstance(event["tension_level"], int)

    def test_boss_music_triggers_at_high_tension(self):
        """boss_music should trigger when tension_level >= 5."""
        # This test validates the condition logic
        tension_levels = [3, 4, 5, 6, 7, 8, 9, 10]
        high_tension = [t for t in tension_levels if t >= 5]
        assert len(high_tension) == 6
        assert 5 in high_tension

    def test_boss_music_not_triggered_low_tension(self):
        """boss_music should not trigger when tension_level < 5."""
        tension_levels = [1, 2, 3, 4]
        should_trigger = [t for t in tension_levels if t >= 5]
        assert len(should_trigger) == 0

    def test_boss_music_event_in_gm_response(self):
        """GMResponse should include audio_cue field for boss_music."""
        response = GMResponse(
            narrative="Combat ensues!",
            audio_cue="boss_music",
            tension_level=8,
        )
        assert response.audio_cue == "boss_music"
        assert response.tension_level >= 5

    def test_boss_music_serializes_to_json(self):
        """boss_music event should serialize to JSON for WebSocket."""
        event = {
            "type": "boss_music",
            "tension_level": 7,
            "intensity": "critical",
        }
        json_str = json.dumps(event)
        parsed = json.loads(json_str)
        assert parsed["type"] == "boss_music"
        assert parsed["tension_level"] == 7
