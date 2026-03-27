from __future__ import annotations


def build_scenarios(reg: dict) -> list:
    Scenario = reg["Scenario"]
    ScenarioSetup = reg["ScenarioSetup"]
    Assertion = reg["Assertion"]
    base_contract = reg["base_contract"]

    return [
        Scenario(
            scenario_id="two_players_divergent_actions",
            name="Two players with divergent actions",
            description="Kael attacks directly while Lyra supports with magic.",
            setup=ScenarioSetup(num_players=2, level=4, location="ashen_woods", tension=5, extra_inferred_class="Mage"),
            action_text="Kael pushes into melee while Lyra casts support magic from the flank to keep him alive.",
            assertions=[
                *base_contract(),
                Assertion("Contains entries for both players", reg["has_per_player_delta"]),
                Assertion("Includes at least one dice roll", reg["has_dice_rolls"]),
                Assertion("Narrative mentions both Kael and Lyra", reg["mentions_both_players"]),
            ],
        ),
        Scenario(
            scenario_id="coop_completed_celebration",
            name="Completed cooperative mission celebration",
            description="The opening cooperative mission is already complete, so the GM should narrate payoff instead of blocking.",
            setup=ScenarioSetup(num_players=2, level=3, location="isles_of_myr", tension=3, coop_mission_active=False, coop_mission_completed=True),
            action_text="We gather after the last objective is done and look for the first moment to breathe and take stock of what we achieved together.",
            assertions=[
                *base_contract(),
                Assertion("Keeps post-victory tension low", reg["tension_at_most"](4)),
                Assertion("Narrative feels like resolution or celebration", lambda n, gs, rt: any(token in n.lower() for token in ["relief", "victory", "together", "celebration", "earned"])),
            ],
        ),
        Scenario(
            scenario_id="multiplayer_item_sharing",
            name="Multiplayer item sharing",
            description="Kael passes a healing resource to Lyra.",
            setup=ScenarioSetup(
                num_players=2,
                level=4,
                location="ashen_woods",
                tension=5,
                extra_hp_fraction=0.2,
                initial_inventory=[{"item_id": "healing-potion", "name": "Healing Potion", "description": "A common restorative draught.", "rarity": "common"}],
            ),
            action_text="Kael tosses Lyra a healing potion and orders her to drink it while he covers the approach.",
            assertions=[
                *base_contract(),
                Assertion("Contains entries for both players", reg["has_per_player_delta"]),
                Assertion("Kael loses an item", reg["kael_loses_item"]),
                Assertion("Lyra receives healing or an item", reg["lyra_receives_help"]),
            ],
        ),
    ]
