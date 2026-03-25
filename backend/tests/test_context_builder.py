"""
test_context_builder.py — Testes do context_builder.py.
Cobre construção de camadas L0, L1 e utilitários de lore.
"""
from unittest.mock import patch

from src.context_builder import (
    _LORE_CHAR_LIMIT,
    _build_l0_static,
    _build_l1_campaign,
    _build_lore_text,
)
from src.models import LoreResult


# ---------------------------------------------------------------------------
# L0 — kernel estático
# ---------------------------------------------------------------------------

class TestBuildL0Static:
    def test_build_l0_uses_kernel_not_world_md(self):
        """_build_l0_static deve usar load_world_kernel, não load_world_md."""
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
# L1 — configuração de campanha
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
        """_LORE_CHAR_LIMIT deve ser exatamente 3200."""
        assert _LORE_CHAR_LIMIT == 3200


# ---------------------------------------------------------------------------
# _build_lore_text — truncamento por documento
# ---------------------------------------------------------------------------

class TestBuildLoreText:
    def test_build_lore_text_truncates_per_doc(self):
        """Cada documento deve ser truncado a ~600 chars individualmente."""
        doc_content = "a" * 800
        lore = LoreResult(
            documents=[doc_content, doc_content],
            metadatas=[{"name": "Doc1"}, {"name": "Doc2"}],
        )

        result = _build_lore_text(lore)

        # O conteúdo original de 800 chars não deve aparecer intacto
        assert "a" * 800 not in result
        # Mas os primeiros 600 chars devem estar presentes (via truncagem)
        assert "a" * 600 in result
