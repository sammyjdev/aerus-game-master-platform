from __future__ import annotations


def build_scenarios(reg: dict) -> list:
    Scenario = reg["Scenario"]
    ScenarioSetup = reg["ScenarioSetup"]
    Assertion = reg["Assertion"]
    base_contract = reg["base_contract"]

    return [
        Scenario(
            scenario_id="travel_route_checkpoint_pressure",
            name="Travel route pressure and delay",
            description="Travel should feel like a risky process with route constraints instead of instant teleportation.",
            setup=ScenarioSetup(
                level=5,
                location="port_myr",
                tension=6,
                world_state={
                    "travel_active": "1",
                    "travel_origin": "port_myr",
                    "travel_destination": "auramveld",
                    "travel_day_current": "3",
                    "travel_day_total": "7",
                    "travel_current_segment": "sea",
                },
            ),
            action_text="I ask what is slowing our passage to Auramveld and whether the sea lane or imperial checkpoints are the greater threat.",
            assertions=[
                *base_contract(),
                Assertion("Narrative reflects travel pressure", reg["mentions_travel_pressure"], dimension="world"),
                Assertion("Narrative remains creatively specific", reg["narrative_is_creative_enough"], dimension="narrative"),
                Assertion("Keeps tension active", reg["tension_at_least"](5), dimension="world"),
            ],
            suites={"complex"},
            tags={"travel", "world", "pressure"},
        ),
        Scenario(
            scenario_id="crafting_regeneration_salve",
            name="Crafting a regeneration salve",
            description="Crafting should be handled narratively with process, tools, and concrete inventory output.",
            setup=ScenarioSetup(
                level=6,
                location="vel_ossian",
                tension=3,
                initial_inventory=[
                    {"item_id": "ash-thorn-sap-1", "name": "Ash-Thorn Sap", "description": "Sticky sap from corrupted flora.", "rarity": "common", "quantity": 3},
                    {"item_id": "grade1-keth", "name": "Grade 1 Keth", "description": "Raw stabilizing Keth.", "rarity": "common", "quantity": 1},
                    {"item_id": "alchemist-kit", "name": "Alchemist Kit", "description": "Portable mixing tools and glassware.", "rarity": "common", "quantity": 1},
                ],
            ),
            action_text="Using the alchemist kit, I try to craft a regeneration salve from the Ash-Thorn Sap and the Grade 1 Keth.",
            assertions=[
                *base_contract(),
                Assertion("Adds an item to inventory", reg["has_inventory_add"], dimension="progression"),
                Assertion("Narrative describes the crafting process", reg["mentions_crafting_process"], dimension="narrative"),
                Assertion("Narrative remains creatively specific", reg["narrative_is_creative_enough"], dimension="narrative"),
            ],
            suites={"complex"},
            tags={"crafting", "economy", "items"},
        ),
        Scenario(
            scenario_id="language_gate_aeridian_archaic",
            name="Aeridian language gate",
            description="A player without Aeridian Archaic should face an in-world reading constraint rather than effortless access.",
            setup=ScenarioSetup(level=4, location="vel_ossian", tension=2, languages=["common_tongue"]),
            action_text="I open the sealed Aeridian manuscript and try to read the original script without help.",
            assertions=[
                *base_contract(),
                Assertion("Narrative acknowledges the language barrier", reg["mentions_language_constraint"], dimension="world"),
                Assertion("Lore remains specific instead of generic", reg["lore_is_specific_not_generic"], dimension="world"),
                Assertion("Keeps conversational tension low", reg["tension_at_most"](4), dimension="world"),
            ],
            suites={"complex"},
            tags={"language", "lore", "guild"},
            hard_fail_labels={"Lore remains specific instead of generic"},
        ),
    ]
