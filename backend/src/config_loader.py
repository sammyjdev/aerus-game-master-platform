"""Compatibility wrapper for legacy imports.

Canonical module: src.infrastructure.config.config_loader
"""

from .infrastructure.config.config_loader import (  # noqa: F401
    CONFIG_DIR,
    get_campaign_value,
    get_faction_config,
    load_bestiary_md,
    load_campaign,
    load_world_md,
    reload_campaign,
)

__all__ = [
    "CONFIG_DIR",
    "load_campaign",
    "load_world_md",
    "load_bestiary_md",
    "get_campaign_value",
    "get_faction_config",
    "reload_campaign",
]
