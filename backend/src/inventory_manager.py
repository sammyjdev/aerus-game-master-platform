"""Inventory logic: weight, carrying capacity, and currency."""
from __future__ import annotations

import unicodedata
from pathlib import Path
from typing import Any

import yaml


_CURRENCY_ORDER = ["copper", "silver", "gold", "platinum"]
_CURRENCY_FACTOR = {
    "copper": 1,
    "silver": 100,
    "gold": 10_000,
    "platinum": 1_000_000,
}


def get_default_starter_inventory() -> list[dict[str, Any]]:
    """Default starter inventory with uniform early-game balance and no armor."""
    return [
        {
            "item_id": "starter-weapon",
            "name": "Basic Weapon",
            "description": "A simple weapon matched to the character's style.",
            "rarity": "common",
            "quantity": 1,
            "equipped": True,
        },
        {
            "item_id": "starter-supplies",
            "name": "Supplies",
            "description": "A starter travel kit with survival essentials.",
            "rarity": "common",
            "quantity": 1,
            "equipped": False,
        },
        {
            "item_id": "starter-backpack",
            "name": "Backpack",
            "description": "A simple pack for carrying equipment.",
            "rarity": "common",
            "quantity": 1,
            "equipped": False,
        },
    ]


def get_default_weight_catalog() -> dict[str, dict[str, Any]]:
    """Minimal fallback weight catalog for starter items and development use."""
    return {
        "basic weapon": {"weight": 3.5},
        "supplies": {"weight": 0.5},
        "backpack": {"weight": 1.0},
    }


def _normalize_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    without_accents = "".join(char for char in normalized if not unicodedata.combining(char))
    return without_accents.strip().lower()


def load_item_catalog(config_path: str | Path) -> dict[str, dict[str, Any]]:
    """Load an item catalog from YAML and index it by normalized item name."""
    path = Path(config_path)
    if not path.exists():
        return {}

    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}

    items = data.get("items", {})
    catalog: dict[str, dict[str, Any]] = {}
    for _, item in items.items():
        if not isinstance(item, dict):
            continue
        name = _normalize_name(str(item.get("name", "")))
        if not name:
            continue
        catalog[name] = item
    return catalog


def sum_inventory_weight(
    inventory: list[dict[str, Any]],
    item_catalog: dict[str, dict[str, Any]],
    unknown_item_weight: float = 0.1,
) -> float:
    """Sum total item weight using the catalog when possible."""
    if not inventory:
        return 0.0

    total = 0.0
    for item in inventory:
        name = _normalize_name(str(item.get("name", "")))
        quantity = int(item.get("quantity", 1) or 1)
        quantity = max(0, quantity)
        weight = float(item_catalog.get(name, {}).get("weight", unknown_item_weight))
        total += weight * quantity
    return round(total, 3)


def get_weight_capacity(strength: int, vitality: int) -> float:
    """Compute carrying capacity from STR and VIT."""
    return round((max(1, strength) * 5.0) + (max(1, vitality) * 3.0), 3)


def get_weight_penalty(current_weight: float, weight_capacity: float) -> dict[str, int | str | float]:
    """Return the load state and percentage penalty from carrying too much."""
    if weight_capacity <= 0:
        return {"state": "immobilized", "penalty_percent": 100, "load_ratio": 1.2}

    ratio = current_weight / weight_capacity
    if ratio < 0.8:
        return {"state": "normal", "penalty_percent": 0, "load_ratio": round(ratio, 3)}
    if ratio < 1.0:
        penalty = int(round((ratio - 0.8) / 0.2 * 20))
        return {"state": "encumbered", "penalty_percent": max(1, penalty), "load_ratio": round(ratio, 3)}
    if ratio < 1.2:
        penalty = 20 + int(round((ratio - 1.0) / 0.2 * 60))
        return {"state": "overloaded", "penalty_percent": min(80, penalty), "load_ratio": round(ratio, 3)}
    return {"state": "immobilized", "penalty_percent": 100, "load_ratio": round(ratio, 3)}


def currency_to_copper(wallet: dict[str, int]) -> int:
    """Convert a multi-tier wallet into total copper value."""
    total = 0
    for tier, factor in _CURRENCY_FACTOR.items():
        total += int(wallet.get(tier, 0) or 0) * factor
    return total


def normalize_currency(total_copper: int) -> dict[str, int]:
    """Normalize total copper into platinum/gold/silver/copper using 100:1 steps."""
    remaining = max(0, int(total_copper))
    wallet = dict.fromkeys(_CURRENCY_ORDER, 0)
    for tier in reversed(_CURRENCY_ORDER):
        factor = _CURRENCY_FACTOR[tier]
        wallet[tier] = remaining // factor
        remaining = remaining % factor
    return wallet


def convert_currency(amount: int, from_tier: str, to_tier: str) -> int:
    """Convert directly between currency tiers using a 100:1 rule."""
    if amount < 0:
        raise ValueError("amount must be non-negative")
    if from_tier not in _CURRENCY_FACTOR or to_tier not in _CURRENCY_FACTOR:
        raise ValueError("invalid currency tier")

    amount_in_copper = int(amount) * _CURRENCY_FACTOR[from_tier]
    return amount_in_copper // _CURRENCY_FACTOR[to_tier]
