"""recipe_manager.py — loads and provides crafting recipe data."""
from __future__ import annotations
import logging
from pathlib import Path
import yaml

logger = logging.getLogger(__name__)

_CONFIG_DIR = Path(__file__).parent.parent / "config"
_RECIPES_YAML = _CONFIG_DIR / "recipes.yaml"

_recipes: dict[str, list[dict]] = {}


def load_recipes() -> dict[str, list[dict]]:
    """Load recipes.yaml. Called at startup."""
    global _recipes
    if _RECIPES_YAML.exists():
        with open(_RECIPES_YAML, encoding="utf-8") as f:
            _recipes = yaml.safe_load(f) or {}
        logger.info("Loaded %d recipe tiers from %s", len(_recipes), _RECIPES_YAML)
    else:
        logger.warning("recipes.yaml not found at %s", _RECIPES_YAML)
        _recipes = {}
    return _recipes


def get_all_recipes() -> dict[str, list[dict]]:
    """Return all recipe tiers."""
    if not _recipes:
        load_recipes()
    return _recipes


def get_recipes_context() -> str:
    """Return a compact summary of all recipes for LLM context injection."""
    all_recipes = get_all_recipes()
    if not all_recipes:
        return ""
    lines = ["Crafting Recipes:"]
    for tier, recipes in all_recipes.items():
        lines.append(f"[{tier.upper()}]")
        for r in recipes:
            ingr = ", ".join(r.get("ingredients", []))
            lines.append(f"  {r['name']} | {ingr} | {r.get('check', '?')} | {r.get('effect', '?')}")
    return "\n".join(lines)


def find_recipe(item_name: str) -> dict | None:
    """Find a recipe by item name (case-insensitive)."""
    term = item_name.lower()
    for recipes in get_all_recipes().values():
        for recipe in recipes:
            if term in recipe["name"].lower():
                return recipe
    return None
