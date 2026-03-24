"""
billing_router.py - Model and API-key selection based on BYOK.

Phase 1: use admin-managed models.
Phase 2: support per-player BYOK with tension-based model selection.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass

from .config_loader import get_campaign_value
from .crypto import decrypt_api_key

logger = logging.getLogger(__name__)


@dataclass
class BillingConfig:
    api_key: str
    model: str
    base_url: str = "https://openrouter.ai/api/v1"
    is_byok: bool = False
    player_id: str | None = None


def select_billing_config(
    tension_level: int,
    player_byok_encrypted: str | None = None,
    player_id: str | None = None,
) -> BillingConfig:
    """
    Select the model and API key based on tension level and BYOK availability.

    Phase 1: always use the admin key.
    Phase 2: prefer the player's BYOK when available.
    """
    if player_byok_encrypted:
        try:
            player_key = decrypt_api_key(player_byok_encrypted)
            model = _select_model_by_tension(tension_level)
            logger.debug("Active BYOK for player %s - model: %s", player_id, model)
            return BillingConfig(
                api_key=player_key,
                model=model,
                is_byok=True,
                player_id=player_id,
            )
        except ValueError:
            logger.warning("Invalid BYOK for player %s - falling back to admin key", player_id)

    admin_key = os.getenv("OPENROUTER_API_KEY")
    if not admin_key:
        raise RuntimeError("OPENROUTER_API_KEY is not set and no BYOK is available")

    model = _select_model_by_tension(tension_level)
    logger.debug("Using admin key - model: %s (tension: %d)", model, tension_level)

    return BillingConfig(
        api_key=admin_key,
        model=model,
        is_byok=False,
    )


def _select_model_by_tension(tension_level: int) -> str:
    """Phase 2 model selection for BYOK-enabled hosted models."""
    thresholds = get_campaign_value("model_selection.tension_thresholds", {})

    if tension_level <= thresholds.get("low", {}).get("max", 3):
        return thresholds.get("low", {}).get("model", "google/gemini-2.5-flash")
    if tension_level <= thresholds.get("medium", {}).get("max", 6):
        return thresholds.get("medium", {}).get("model", "anthropic/claude-sonnet-4-6")
    if tension_level <= thresholds.get("high", {}).get("max", 8):
        return thresholds.get("high", {}).get("model", "anthropic/claude-sonnet-4-6")
    return thresholds.get("critical", {}).get("model", "anthropic/claude-opus-4-6")


def _select_model_by_tension_phase1(_tension_level: int) -> str:
    """Phase 1 model selection for low-cost validation."""
    default_model = get_campaign_value("model_selection.default", "google/gemini-2.5-flash")
    return default_model
