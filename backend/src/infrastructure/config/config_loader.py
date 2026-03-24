"""
config_loader.py - YAML and Markdown configuration loading.
Responsibility: read campaign.yaml, world.md, and bestiary.md.
Does not access SQLite or ChromaDB.
"""
from __future__ import annotations

import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

CONFIG_DIR = Path(os.getenv("CONFIG_DIR", Path(__file__).parent.parent.parent.parent / "config"))


@lru_cache(maxsize=1)
def load_campaign() -> dict[str, Any]:
    """Load campaign.yaml. Cached and only refreshed on restart unless cleared manually."""
    path = CONFIG_DIR / "campaign.yaml"
    logger.info("Loading campaign.yaml from %s", path)
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data


@lru_cache(maxsize=1)
def load_world_md() -> str:
    """Load the full world.md file. Immutable at runtime."""
    path = CONFIG_DIR / "world.md"
    logger.info("Loading world.md from %s", path)
    return path.read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def load_world_kernel() -> str:
    """Load world_kernel.md, the compact summary used for the L0 static layer."""
    path = CONFIG_DIR / "world_kernel.md"
    return path.read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def load_bestiary_md() -> str:
    """Load and concatenate all tiered bestiary_tN.md files."""
    parts: list[str] = []
    for tier in range(1, 6):
        path = CONFIG_DIR / f"bestiary_t{tier}.md"
        if path.exists():
            parts.append(path.read_text(encoding="utf-8"))
        else:
            logger.warning("Bestiary file not found: %s", path)
    if not parts:
        legacy = CONFIG_DIR / "bestiary.md"
        if legacy.exists():
            logger.warning("Using legacy monolithic bestiary.md")
            return legacy.read_text(encoding="utf-8")
    logger.info("Loading bestiary from %d tier files", len(parts))
    return "\n\n".join(parts)


def get_campaign_value(key_path: str, default: Any = None) -> Any:
    """
    Access a value in campaign.yaml via dotted path notation.
    Example: get_campaign_value("model_selection.default")
    """
    data = load_campaign()
    keys = key_path.split(".")
    current = data
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key, default)
    return current


def get_faction_config(faction_id: str) -> dict[str, Any] | None:
    """Return the configuration for a specific faction."""
    campaign = load_campaign()
    factions = campaign.get("factions", [])
    for faction in factions:
        if faction.get("id") == faction_id:
            return faction
    return None


def reload_campaign() -> None:
    """Clear the campaign.yaml cache. Use carefully in production."""
    load_campaign.cache_clear()
    logger.info("campaign.yaml cache cleared")
