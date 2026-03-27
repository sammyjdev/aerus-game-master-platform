from __future__ import annotations


def build_scenarios(reg: dict) -> list:
    Scenario = reg["Scenario"]
    ScenarioSetup = reg["ScenarioSetup"]
    Assertion = reg["Assertion"]
    base_contract = reg["base_contract"]

    return [
        Scenario(
            scenario_id="arrival_port_myr",
            name="Arrival on the Isles of Myr",
            description="Low-tension onboarding scene that should ground the player in the world.",
            setup=ScenarioSetup(
                level=1,
                location="isles_of_myr",
                tension=3,
                coop_mission_active=True,
                coop_mission_completed=False,
            ),
            action_text="Kael steadies his breathing, scans the harbor, and asks the nearest dockworker where he is and why the sky above this place feels wrong.",
            assertions=[
                *base_contract(),
                Assertion("Returns substantial narrative", reg["has_nonempty_narrative"]),
                Assertion("Uses Aerus world vocabulary", reg["mentions_english_world_terms"]),
                Assertion("Mentions Port Myr or the harbor", reg["mentions_port_myr"]),
                Assertion("Keeps exploration tension low", reg["tension_at_most"](4)),
            ],
        ),
        Scenario(
            scenario_id="tier1_combat",
            name="Tier 1 creature combat",
            description="A level 3 martial attack against a low-tier threat.",
            setup=ScenarioSetup(level=3, location="ashen_woods", tension=5, inferred_class="Warrior"),
            action_text="I attack the ash-stalker with my sword and aim directly for its throat.",
            assertions=[
                *base_contract(),
                Assertion("Includes dice rolls", reg["has_dice_rolls"]),
                Assertion("Applies negative HP pressure", reg["has_negative_hp_change"]),
                Assertion("Narrative reads like combat", reg["mentions_combat"]),
                Assertion("Keeps combat tension active", reg["tension_at_least"](3)),
            ],
        ),
        Scenario(
            scenario_id="reputation_help_church",
            name="Reputation-generating intervention",
            description="A level 5 player helps a wounded church guard.",
            setup=ScenarioSetup(level=5, location="port_myr", tension=3, inferred_class="Paladin"),
            action_text="I help the wounded Church sentinel and hold the attacker back while I call for help.",
            assertions=[
                *base_contract(),
                Assertion("Produces Church reputation delta", lambda n, gs, rt: reg["has_named_reputation_delta"](n, gs, rt, "church_pure_flame")),
                Assertion("Church delta is positive", lambda n, gs, rt: reg["has_positive_reputation_delta"](n, gs, rt, "church_pure_flame")),
            ],
        ),
        Scenario(
            scenario_id="coop_mission_blocking",
            name="Blocking cooperative mission",
            description="Two players try to leave before the introductory cooperative mission is complete.",
            setup=ScenarioSetup(num_players=2, level=2, location="isles_of_myr", tension=4, coop_mission_active=True, coop_mission_completed=False),
            action_text="We ignore the regroup objective, rush to the harbor, and try to leave the Isles of Myr on the first ship we find.",
            assertions=[
                *base_contract(),
                Assertion("Narrative blocks or discourages departure", reg["blocks_or_discourages_departure"]),
                Assertion("Narrative does not describe a successful departure", reg["location_not_changed"]),
                Assertion("Includes per-player delta entries", reg["has_per_player_delta"]),
            ],
        ),
        Scenario(
            scenario_id="near_fatal_high_tension",
            name="High-tension near-fatal combat",
            description="A level 4 player with almost no HP tries to flee a brutal enemy.",
            setup=ScenarioSetup(level=4, hp_fraction=0.05, location="ashen_woods", tension=8),
            action_text="I stagger backward from the Ash Golem, bleeding heavily, and try to escape before it crushes me.",
            assertions=[
                *base_contract(),
                Assertion("Keeps tension very high", reg["tension_at_least"](7)),
                Assertion("Narrative feels urgent and dangerous", reg["is_visceral"]),
            ],
        ),
        Scenario(
            scenario_id="ability_unlock_level5",
            name="ABILITY_UNLOCK trigger at level 5",
            description="A level 5 player acts on instinct with a blade and should signal new progression.",
            setup=ScenarioSetup(level=5, location="ashen_woods", tension=5),
            action_text="I move on instinct and unleash a sword technique I have never fully understood before.",
            assertions=[
                *base_contract(),
                Assertion("Emits ABILITY_UNLOCK", lambda n, gs, rt: reg["has_event_type"](n, gs, rt, "ABILITY_UNLOCK")),
                Assertion("Narrative mentions progression or awakening", reg["mentions_progression"]),
            ],
        ),
        Scenario(
            scenario_id="structured_levelup",
            name="Structured LEVELUP event",
            description="A level 9 player gains enough experience to cross into level 10.",
            setup=ScenarioSetup(level=9, location="ashen_woods", tension=5),
            action_text="I finish the fight, claim the hard-earned victory, and push through the limit of my current strength.",
            assertions=[
                *base_contract(),
                Assertion("Emits LEVELUP with a new level", reg["has_levelup_event"]),
                Assertion("Includes experience gain", reg["has_experience_gain"]),
                Assertion("Narrative reads like progression", reg["mentions_progression"]),
            ],
        ),
        Scenario(
            scenario_id="loot_complete_structure",
            name="LOOT with complete structure",
            description="A level 7 player defeats a minor boss and loots a rare item.",
            setup=ScenarioSetup(level=7, location="ruined_quay", tension=6),
            action_text="I finish the corrupted overseer, search the corpse, and take whatever relic it guarded.",
            assertions=[
                *base_contract(),
                Assertion("Emits LOOT with items", reg["has_loot_event_with_items"]),
                Assertion("Loot rarity is not just common", reg["has_non_common_loot_rarity"]),
                Assertion("Narrative describes advancement or treasure weight", reg["mentions_progression"]),
            ],
        ),
        Scenario(
            scenario_id="player_death_permadeath",
            name="Player death and permadeath weight",
            description="A nearly dead low-level player is struck by a fatal hit.",
            setup=ScenarioSetup(level=2, hp_fraction=0.01, location="ashen_woods", tension=9),
            action_text="I try to stand my ground even though the Ash Golem is already swinging the final blow toward my chest.",
            assertions=[
                *base_contract(require_followup=False),
                Assertion("Emits death or a fatal state", reg["has_death_event_or_fatal_state"]),
                Assertion("Applies fatal damage pressure", reg["has_negative_hp_change"]),
                Assertion("Narrative gives death dramatic weight", reg["is_visceral"]),
            ],
        ),
        Scenario(
            scenario_id="debuff_condition_applied",
            name="Debuff condition applied",
            description="A corrupted creature attack should attach a meaningful negative condition.",
            setup=ScenarioSetup(level=4, location="ashen_woods", tension=6),
            action_text="The ash-stalker claws into me and I try to keep fighting through whatever corruption it injected.",
            assertions=[
                *base_contract(),
                Assertion("Adds at least one condition", reg["has_conditions_add"]),
                Assertion("Condition has positive duration", reg["has_condition_duration"]),
                Assertion("Also carries damage pressure", reg["has_negative_hp_change"]),
            ],
        ),
        Scenario(
            scenario_id="healing_potion_use",
            name="Healing potion use",
            description="A player with low HP uses a healing item from inventory.",
            setup=ScenarioSetup(
                level=3,
                hp_fraction=0.25,
                location="isles_of_myr",
                tension=4,
                initial_inventory=[{"item_id": "healing-potion", "name": "Healing Potion", "description": "A common restorative draught.", "rarity": "common"}],
            ),
            action_text="I pull a healing potion from my belt and drink it before the next wave hits.",
            assertions=[
                *base_contract(),
                Assertion("Applies positive HP change", reg["has_positive_hp_change"]),
                Assertion("Consumes an inventory item", reg["has_inventory_remove"]),
                Assertion("Narrative shows visible healing", reg["narrative_shows_healing"]),
            ],
        ),
        Scenario(
            scenario_id="lore_accuracy_pact_of_myr",
            name="Lore accuracy around the Pact of Myr",
            description="The GM should rely on canonical lore instead of generic fantasy filler.",
            setup=ScenarioSetup(level=3, location="port_myr", tension=2),
            action_text="I ask the local historian what the Pact of Myr truly changed and why these islands still hold together.",
            assertions=[
                *base_contract(),
                Assertion("Narrative uses canonical Aerus lore terms", reg["narrative_mentions_lore"]),
                Assertion("Keeps tension low for a lore scene", reg["tension_at_most"](4)),
            ],
        ),
    ]
