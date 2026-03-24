"""
test_billing_router.py — Testes do billing_router.py.
Cobre seleção de modelo por tension_level e fallback de chaves.
"""
import os
from unittest.mock import patch

import pytest

from src.billing_router import (
    BillingConfig,
    _select_model_by_tension,
    _select_model_by_tension_phase1,
    select_billing_config,
)

# ---------------------------------------------------------------------------
# Constantes de teste
# ---------------------------------------------------------------------------

ADMIN_KEY = "sk-admin-test-key"
PHASE1_DEFAULT_MODEL = "google/gemini-2.5-flash"
PHASE1_FALLBACK_MODEL = "deepseek/deepseek-chat"
LOW_MODEL = "google/gemini-2.5-flash"
MEDIUM_MODEL = "anthropic/claude-sonnet-4-6"
HIGH_MODEL = "anthropic/claude-opus-4-6"


# ---------------------------------------------------------------------------
# _select_model_by_tension_phase1
# ---------------------------------------------------------------------------

class TestSelectModelPhase1:
    """Fase 1 sempre usa o modelo padrão econômico independente da tensão."""

    def _call(self, tension: int) -> str:
        with patch("src.billing_router.get_campaign_value") as mock_cv:
            mock_cv.side_effect = lambda key, default=None: {
                "model_selection.default": PHASE1_DEFAULT_MODEL,
                "model_selection.fallback": PHASE1_FALLBACK_MODEL,
            }.get(key, default)
            return _select_model_by_tension_phase1(tension)

    def test_tension_low_uses_default(self):
        assert self._call(1) == PHASE1_DEFAULT_MODEL

    def test_tension_medium_uses_default(self):
        assert self._call(5) == PHASE1_DEFAULT_MODEL

    def test_tension_high_uses_default(self):
        assert self._call(10) == PHASE1_DEFAULT_MODEL

    def test_returns_campaign_default_model(self):
        """Modelo vem do campaign.yaml, não hardcoded."""
        with patch("src.billing_router.get_campaign_value") as mock_cv:
            mock_cv.side_effect = lambda key, default=None: {
                "model_selection.default": "custom/model-x",
                "model_selection.fallback": "custom/fallback-y",
            }.get(key, default)
            result = _select_model_by_tension_phase1(5)
        assert result == "custom/model-x"


class TestSelectModelByTension:
    def _call(self, tension: int) -> str:
        with patch("src.billing_router.get_campaign_value") as mock_cv:
            mock_cv.return_value = {
                "low": {"max": 4, "model": LOW_MODEL},
                "medium": {"max": 7, "model": MEDIUM_MODEL},
                "high": {"model": HIGH_MODEL},
            }
            return _select_model_by_tension(tension)

    def test_low_bucket(self):
        assert self._call(3) == LOW_MODEL

    def test_medium_bucket(self):
        assert self._call(7) == MEDIUM_MODEL

    def test_high_bucket(self):
        assert self._call(9) == HIGH_MODEL


# ---------------------------------------------------------------------------
# select_billing_config — sem BYOK
# ---------------------------------------------------------------------------

class TestSelectBillingConfigAdminKey:
    """Quando não há BYOK, deve usar a chave admin do ambiente."""

    def test_uses_admin_key_when_no_byok(self):
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": ADMIN_KEY}):
            with patch("src.billing_router.get_campaign_value") as mock_cv:
                mock_cv.return_value = {
                    "low": {"max": 4, "model": LOW_MODEL},
                    "medium": {"max": 7, "model": MEDIUM_MODEL},
                    "high": {"model": HIGH_MODEL},
                }
                config = select_billing_config(tension_level=5)

        assert config.api_key == ADMIN_KEY
        assert config.is_byok is False
        assert config.player_id is None

    def test_returns_billing_config_instance(self):
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": ADMIN_KEY}):
            with patch("src.billing_router.get_campaign_value") as mock_cv:
                mock_cv.return_value = {
                    "low": {"max": 4, "model": LOW_MODEL},
                    "medium": {"max": 7, "model": MEDIUM_MODEL},
                    "high": {"model": HIGH_MODEL},
                }
                config = select_billing_config(tension_level=3)

        assert isinstance(config, BillingConfig)

    def test_base_url_is_openrouter(self):
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": ADMIN_KEY}):
            with patch("src.billing_router.get_campaign_value") as mock_cv:
                mock_cv.return_value = {
                    "low": {"max": 4, "model": LOW_MODEL},
                    "medium": {"max": 7, "model": MEDIUM_MODEL},
                    "high": {"model": HIGH_MODEL},
                }
                config = select_billing_config(tension_level=5)

        assert "openrouter.ai" in config.base_url

    def test_raises_when_no_admin_key_and_no_byok(self):
        """Sem OPENROUTER_API_KEY e sem BYOK deve levantar RuntimeError."""
        env = {k: v for k, v in os.environ.items() if k != "OPENROUTER_API_KEY"}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(RuntimeError, match="OPENROUTER_API_KEY"):
                select_billing_config(tension_level=5)

    def test_model_is_phase1_default(self):
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": ADMIN_KEY}):
            with patch("src.billing_router.get_campaign_value") as mock_cv:
                mock_cv.return_value = {
                    "low": {"max": 4, "model": LOW_MODEL},
                    "medium": {"max": 7, "model": MEDIUM_MODEL},
                    "high": {"model": HIGH_MODEL},
                }
                config = select_billing_config(tension_level=9)

        assert config.model == HIGH_MODEL


# ---------------------------------------------------------------------------
# select_billing_config — com BYOK
# ---------------------------------------------------------------------------

class TestSelectBillingConfigBYOK:
    """Quando BYOK é fornecido e válido, deve preferir a chave do jogador."""

    ENCRYPTED = "fernet-encrypted-key"
    DECRYPTED = "sk-player-real-key"

    def test_byok_uses_player_key(self):
        with patch("src.billing_router.decrypt_api_key", return_value=self.DECRYPTED):
            with patch("src.billing_router.get_campaign_value") as mock_cv:
                mock_cv.return_value = {
                    "low": {"max": 4, "model": LOW_MODEL},
                    "medium": {"max": 7, "model": MEDIUM_MODEL},
                    "high": {"model": HIGH_MODEL},
                }
                config = select_billing_config(
                    tension_level=5,
                    player_byok_encrypted=self.ENCRYPTED,
                    player_id="pid-1",
                )

        assert config.api_key == self.DECRYPTED
        assert config.is_byok is True
        assert config.player_id == "pid-1"

    def test_byok_invalid_key_falls_back_to_admin(self):
        """Se decrypt falhar com ValueError, deve usar chave admin como fallback."""
        with patch("src.billing_router.decrypt_api_key", side_effect=ValueError("bad key")):
            with patch.dict(os.environ, {"OPENROUTER_API_KEY": ADMIN_KEY}):
                with patch("src.billing_router.get_campaign_value") as mock_cv:
                    mock_cv.return_value = {
                        "low": {"max": 4, "model": LOW_MODEL},
                        "medium": {"max": 7, "model": MEDIUM_MODEL},
                        "high": {"model": HIGH_MODEL},
                    }
                    config = select_billing_config(
                        tension_level=5,
                        player_byok_encrypted=self.ENCRYPTED,
                        player_id="pid-1",
                    )

        assert config.api_key == ADMIN_KEY
        assert config.is_byok is False

    def test_byok_none_uses_admin(self):
        """player_byok_encrypted=None deve usar admin sem tentar decrypt."""
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": ADMIN_KEY}):
            with patch("src.billing_router.get_campaign_value") as mock_cv:
                mock_cv.return_value = {
                    "low": {"max": 4, "model": LOW_MODEL},
                    "medium": {"max": 7, "model": MEDIUM_MODEL},
                    "high": {"model": HIGH_MODEL},
                }
                with patch("src.billing_router.decrypt_api_key") as mock_decrypt:
                    config = select_billing_config(
                        tension_level=5,
                        player_byok_encrypted=None,
                    )
                    mock_decrypt.assert_not_called()

        assert config.is_byok is False


# ---------------------------------------------------------------------------
# BUG: tension_level hardcoded em _resolve_billing do game_master
# ---------------------------------------------------------------------------

class TestPhase1ModelFunctionStillDeterministic:
    """
    Documenta função legada da Fase 1 (ainda disponível por compatibilidade).
    """

    def test_phase1_model_ignores_tension_level(self):
        with patch("src.billing_router.get_campaign_value") as mock_cv:
            mock_cv.side_effect = lambda key, default=None: {
                "model_selection.default": PHASE1_DEFAULT_MODEL,
                "model_selection.fallback": PHASE1_FALLBACK_MODEL,
            }.get(key, default)

            low = _select_model_by_tension_phase1(1)
            high = _select_model_by_tension_phase1(10)

        assert low == high == PHASE1_DEFAULT_MODEL
