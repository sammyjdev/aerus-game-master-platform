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
    is_slm: bool = False
    is_hosted_narrator: bool = False
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
    Phase 3 (SLM): route to local fine-tuned model when SLM_ENABLED=true.
    """
    # Hosted narrator — frontier model + RAG + guardrail (the recommended path; see
    # docs/GAP_ANALYSIS_NARRATOR.md). DeepSeek for value, Haiku for premium.
    # Rollback: set HOSTED_NARRATOR_ENABLED=false to fall back to SLM/OpenRouter.
    if os.getenv("HOSTED_NARRATOR_ENABLED", "false").lower() == "true":
        hn_key = os.getenv("HOSTED_NARRATOR_API_KEY") or os.getenv("OPENROUTER_API_KEY")
        if hn_key:
            hn_base = os.getenv("HOSTED_NARRATOR_BASE_URL", "https://openrouter.ai/api/v1")
            hn_model = os.getenv("HOSTED_NARRATOR_MODEL", "deepseek/deepseek-chat")
            logger.debug("HOSTED_NARRATOR_ENABLED — routing narrative to %s at %s", hn_model, hn_base)
            return BillingConfig(
                api_key=hn_key,
                model=hn_model,
                base_url=hn_base,
                is_byok=False,
                is_hosted_narrator=True,
                player_id=player_id,
            )
        logger.warning("HOSTED_NARRATOR_ENABLED but no API key set — falling through")

    # SLM integration ("B1" path) — routes narrative to a local fine-tuned model.
    # Dormant by default and superseded by the hosted narrator above; see
    # docs/GAP_ANALYSIS_NARRATOR.md. Rollback: set SLM_ENABLED=false to return to OpenRouter.
    if os.getenv("SLM_ENABLED", "false").lower() == "true":
        slm_base_url = os.getenv("SLM_BASE_URL", "http://localhost:8001/v1")
        slm_model = os.getenv("SLM_MODEL", "aerum-gm")
        logger.debug("SLM_ENABLED — routing to local model: %s at %s", slm_model, slm_base_url)
        return BillingConfig(
            api_key="local",
            model=slm_model,
            base_url=slm_base_url,
            is_byok=False,
            is_slm=True,
            player_id=player_id,
        )

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
