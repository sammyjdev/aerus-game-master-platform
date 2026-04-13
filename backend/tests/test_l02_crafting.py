"""
test_l02_crafting.py — Tests for the Crafting system (L-02).
"""
import pytest


class TestRecipeManager:
    def test_recipes_yaml_loads(self):
        from src.recipe_manager import load_recipes
        recipes = load_recipes()
        assert "common" in recipes
        assert len(recipes["common"]) >= 3

    def test_find_recipe_by_name(self):
        from src.recipe_manager import find_recipe
        r = find_recipe("MP Absorption")
        assert r is not None
        assert "check" in r

    def test_find_recipe_case_insensitive(self):
        from src.recipe_manager import find_recipe
        r = find_recipe("mp absorption")
        assert r is not None

    def test_find_recipe_not_found(self):
        from src.recipe_manager import find_recipe
        r = find_recipe("nonexistent potion")
        assert r is None

    def test_get_recipes_context_nonempty(self):
        from src.recipe_manager import get_recipes_context
        ctx = get_recipes_context()
        assert len(ctx) > 50
        assert "Crafting Recipes" in ctx

    def test_recipes_context_contains_tiers(self):
        from src.recipe_manager import get_recipes_context
        ctx = get_recipes_context()
        assert "COMMON" in ctx
        assert "RARE" in ctx

    def test_find_recipe_returns_all_fields(self):
        from src.recipe_manager import find_recipe
        r = find_recipe("Keth Oil")
        assert r is not None
        assert "ingredients" in r
        assert "effect" in r
        assert "item_id" in r

    def test_rare_recipe_found(self):
        from src.recipe_manager import find_recipe
        r = find_recipe("Disruption Blade")
        assert r is not None
        assert r["item_id"] == "blade_disruption"


@pytest.mark.asyncio
class TestCraftEndpoint:
    async def test_craft_valid_recipe(self, authenticated_client):
        resp = await authenticated_client.post("/game/craft", json={"recipe": "MP Absorption Potion"})
        assert resp.status_code == 200
        data = resp.json()
        assert "recipe" in data
        assert "message" in data

    async def test_craft_unknown_recipe(self, authenticated_client):
        resp = await authenticated_client.post("/game/craft", json={"recipe": "nonexistent recipe xyz"})
        assert resp.status_code == 404

    async def test_craft_no_recipe_name(self, authenticated_client):
        resp = await authenticated_client.post("/game/craft", json={})
        assert resp.status_code == 422

    async def test_craft_unauthenticated(self, client):
        resp = await client.post("/game/craft", json={"recipe": "Keth Oil"})
        assert resp.status_code == 401

    async def test_craft_returns_recipe_details(self, authenticated_client):
        resp = await authenticated_client.post("/game/craft", json={"recipe": "Keth Oil"})
        assert resp.status_code == 200
        data = resp.json()
        recipe = data["recipe"]
        assert recipe["item_id"] == "oil_keth"
        assert "ingredients" in recipe
        assert "check" in recipe

    async def test_craft_partial_name_match(self, authenticated_client):
        resp = await authenticated_client.post("/game/craft", json={"recipe": "Regeneration"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["recipe"]["item_id"] == "salve_regeneration"


@pytest.mark.asyncio
class TestCraftOutcomeDelta:
    async def test_craft_success_adds_to_inventory(self, authenticated_client, player_id):
        from src import state_manager
        async with state_manager.db_context() as conn:
            result = await state_manager.apply_state_delta(conn, player_id, {
                "craft_outcome": {
                    "success": True,
                    "item_id": "potion_mp_absorption",
                    "item_name": "MP Absorption Potion",
                    "description": "Test crafted item",
                    "rarity": "common",
                    "quantity": 1,
                }
            })
        assert result.get("crafted_item") == "MP Absorption Potion"

        # Verify item is in inventory
        async with state_manager.db_context() as conn:
            items = await state_manager.get_player_inventory(conn, player_id)
        names = [i["name"] for i in items]
        assert "MP Absorption Potion" in names

    async def test_craft_failure_does_not_add_item(self, authenticated_client, player_id):
        from src import state_manager
        async with state_manager.db_context() as conn:
            result = await state_manager.apply_state_delta(conn, player_id, {
                "craft_outcome": {
                    "success": False,
                    "item_id": "potion_mp_absorption",
                    "item_name": "MP Absorption Potion",
                }
            })
        assert not result.get("crafted_item")

    async def test_craft_outcome_without_success_flag(self, authenticated_client, player_id):
        from src import state_manager
        async with state_manager.db_context() as conn:
            result = await state_manager.apply_state_delta(conn, player_id, {
                "craft_outcome": {
                    "item_id": "potion_mp_absorption",
                    "item_name": "MP Absorption Potion",
                }
            })
        # No success key defaults to falsy — item must not be added
        assert not result.get("crafted_item")

    async def test_craft_outcome_sets_rarity(self, authenticated_client, player_id):
        from src import state_manager
        async with state_manager.db_context() as conn:
            await state_manager.apply_state_delta(conn, player_id, {
                "craft_outcome": {
                    "success": True,
                    "item_id": "blade_disruption",
                    "item_name": "Disruption Blade",
                    "rarity": "rare",
                    "quantity": 1,
                }
            })
        async with state_manager.db_context() as conn:
            items = await state_manager.get_player_inventory(conn, player_id)
        blade = next((i for i in items if i["name"] == "Disruption Blade"), None)
        assert blade is not None
        assert blade["rarity"] == "rare"

    async def test_craft_outcome_default_quantity_one(self, authenticated_client, player_id):
        from src import state_manager
        async with state_manager.db_context() as conn:
            await state_manager.apply_state_delta(conn, player_id, {
                "craft_outcome": {
                    "success": True,
                    "item_id": "oil_keth",
                    "item_name": "Keth Oil",
                }
            })
        async with state_manager.db_context() as conn:
            items = await state_manager.get_player_inventory(conn, player_id)
        oil = next((i for i in items if i["name"] == "Keth Oil"), None)
        assert oil is not None
        assert oil["quantity"] == 1
