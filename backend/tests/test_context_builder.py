"""
test_context_builder.py — Tests for context_builder.py.
Covers building the L0 and L1 layers and the lore utilities.
"""
from pathlib import Path
from unittest.mock import patch

from src.context_builder import (
    _LORE_CHAR_LIMIT,
    _build_l0_static,
    _build_l1_campaign,
    _build_lore_text,
    build_gm_system_prompt,
)
from src.models import LoreResult


# ---------------------------------------------------------------------------
# L0 — static kernel
# ---------------------------------------------------------------------------

class TestBuildL0Static:
    def test_build_l0_uses_kernel_not_world_md(self):
        """_build_l0_static must use load_world_kernel, not load_world_md."""
        with patch("src.context_builder.load_world_kernel", return_value="kernel content here") as mock_kernel:
            result = _build_l0_static()

        assert "kernel content here" in result
        mock_kernel.assert_called_once()

    def test_build_l0_truncates_long_kernel(self):
        """Kernels longer than 1000 chars must be truncated."""
        long_kernel = "x" * 2000
        with patch("src.context_builder.load_world_kernel", return_value=long_kernel):
            result = _build_l0_static()

        max_expected = 1000 + len("[...truncated]") + 1  # +1 for newline
        assert len(result) <= max_expected
        assert "x" * 2000 not in result


# ---------------------------------------------------------------------------
# L1 — campaign configuration
# ---------------------------------------------------------------------------

class TestBuildL1Campaign:
    _TYPICAL_CAMPAIGN = {
        "campaign": {"name": "A Queda de Myr"},
        "tone": {"darkness_level": 9},
        "difficulty": {"base": "brutal", "permadeath": True},
        "language": "pt-BR",
        "action_window_seconds": 3,
    }

    def test_build_l1_excludes_redundant_fields(self):
        """L1 should not include fields like Language or Action window."""
        with patch("src.context_builder.load_campaign", return_value=self._TYPICAL_CAMPAIGN):
            result = _build_l1_campaign()

        assert "Language" not in result
        assert "Action window" not in result

    def test_build_l1_includes_required_fields(self):
        """L1 must contain Campaign, Tone, Difficulty and Permadeath."""
        with patch("src.context_builder.load_campaign", return_value=self._TYPICAL_CAMPAIGN):
            result = _build_l1_campaign()

        assert "Campaign" in result
        assert "Tone" in result
        assert "Difficulty" in result
        assert "Permadeath" in result


# ---------------------------------------------------------------------------
# _LORE_CHAR_LIMIT
# ---------------------------------------------------------------------------

class TestLoreCharLimit:
    def test_lore_char_limit_is_expanded(self):
        """_LORE_CHAR_LIMIT must be exactly 3200."""
        assert _LORE_CHAR_LIMIT == 3200


# ---------------------------------------------------------------------------
# _build_lore_text — per-document truncation
# ---------------------------------------------------------------------------

class TestBuildLoreText:
    def test_build_lore_text_truncates_per_doc(self):
        """Each document must be truncated to ~600 chars individually."""
        doc_content = "a" * 800
        lore = LoreResult(
            documents=[doc_content, doc_content],
            metadatas=[{"name": "Doc1"}, {"name": "Doc2"}],
        )

        result = _build_lore_text(lore)

        # The original 800-char content must not appear intact
        assert "a" * 800 not in result
        # But the first 600 chars must still be present (via truncation)
        assert "a" * 600 in result


class TestNarrationPromptStyle:
    def test_runtime_narration_assets_avoid_long_dash_character(self):
        """The runtime narration guidance should not include the em dash character."""
        root = Path(__file__).resolve().parents[1]
        kernel = (root / "config" / "narration_bible_kernel.md").read_text(encoding="utf-8")
        prompt = build_gm_system_prompt(num_players=1, tension_level=3)

        assert "—" not in kernel
        assert "—" not in prompt

    def test_prompt_requires_second_person_player_address(self):
        """The GM prompt should explicitly require second-person narration anchored to the player name."""
        prompt = build_gm_system_prompt(
            num_players=2,
            tension_level=4,
            player_output_targets=[("p1", "Callum"), ("p2", "Lyra")],
        )

        assert "second-person" in prompt.lower() or "second person" in prompt.lower()
        assert "callum" in prompt.lower()
