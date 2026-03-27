from __future__ import annotations


def build_scenarios(reg: dict) -> list:
    Scenario = reg["Scenario"]
    ScenarioSetup = reg["ScenarioSetup"]
    Assertion = reg["Assertion"]
    base_contract = reg["base_contract"]

    return [
        Scenario(
            scenario_id="class_mutation_level25",
            name="CLASS_MUTATION at level 25",
            description="A warrior crossing level 25 should trigger formal mutation and ability growth.",
            setup=ScenarioSetup(level=25, location="ashen_woods", tension=7, inferred_class="Warrior"),
            action_text="I break through the final limit of my old martial path and let the new shape of my power take hold.",
            assertions=[
                *base_contract(),
                Assertion("Emits CLASS_MUTATION with a new class", reg["has_class_mutation_event"]),
                Assertion("Also emits ABILITY_UNLOCK", lambda n, gs, rt: reg["has_event_type"](n, gs, rt, "ABILITY_UNLOCK")),
                Assertion("Narrative treats the transformation as dramatic", reg["mentions_progression"]),
            ],
        ),
        Scenario(
            scenario_id="dual_faction_reputation",
            name="Dual-faction reputation change",
            description="Helping the Church while betraying the Children should move both reputations.",
            setup=ScenarioSetup(level=7, location="port_myr", tension=5),
            action_text="I report the hidden Children of the Broken Thread cell to the Church and give the sentinel names and routes.",
            assertions=[
                *base_contract(),
                Assertion("Affects at least two factions", reg["has_dual_faction_rep"]),
                Assertion("Includes both positive and negative deltas", reg["has_opposing_rep_deltas"]),
                Assertion("Narrative recognizes the betrayal", reg["narrative_acknowledges_moral_weight"]),
            ],
        ),
        Scenario(
            scenario_id="mp_usage_spellcasting",
            name="MP usage from spellcasting",
            description="A mage casts a costly fire spell.",
            setup=ScenarioSetup(level=5, location="ashen_woods", tension=6, inferred_class="Mage"),
            action_text="I cast a fireball into the clustered enemies and force the heat to spread through the undergrowth.",
            assertions=[
                *base_contract(),
                Assertion("Consumes mana", reg["has_mp_change_negative"]),
                Assertion("Includes dice rolls", reg["has_dice_rolls"]),
                Assertion("Narrative mentions magic or fire", lambda n, gs, rt: "magic" in n.lower() or "fire" in n.lower()),
            ],
        ),
        Scenario(
            scenario_id="currency_reward_mission_complete",
            name="Currency reward for mission completion",
            description="Turning in a bandit bounty should produce payment.",
            setup=ScenarioSetup(level=4, location="port_myr", tension=3),
            action_text="I hand the bandit leader's signet and proof of the kill to the guard captain and demand the promised reward.",
            assertions=[
                *base_contract(),
                Assertion("Adds currency or monetary reward", reg["has_currency_gain"]),
                Assertion("Narrative mentions reward or payment", reg["mentions_reward_or_payment"]),
            ],
        ),
        Scenario(
            scenario_id="blessing_buff_condition",
            name="Blessing buff condition",
            description="A priest blesses the player before a dangerous mission.",
            setup=ScenarioSetup(level=4, location="port_myr", tension=3, inferred_class="Cleric"),
            action_text="The priest places a hand on my shoulder and I accept the blessing before we march into danger.",
            assertions=[
                *base_contract(),
                Assertion("Adds a buff condition", reg["has_buff_condition"]),
                Assertion("Narrative mentions divine protection", reg["mentions_blessing_or_divine_protection"]),
            ],
        ),
        Scenario(
            scenario_id="partial_xp_no_level",
            name="Partial XP without level up",
            description="A weak enemy should grant XP without forcing a level-up event.",
            setup=ScenarioSetup(level=4, location="ashen_woods", tension=4),
            action_text="I kill the weakened scavenger quickly and move on without much trouble.",
            assertions=[
                *base_contract(),
                Assertion("Includes positive experience gain", reg["has_experience_gain"]),
                Assertion("Does not emit LEVELUP", reg["no_levelup_event"]),
            ],
        ),
        Scenario(
            scenario_id="multiple_conditions_simultaneous",
            name="Multiple simultaneous conditions",
            description="An ambush should stack more than one harmful effect.",
            setup=ScenarioSetup(level=5, location="ashen_woods", tension=7),
            action_text="The ambushers hit me all at once with poisoned blades and jagged hooks before I can recover my footing.",
            assertions=[
                *base_contract(),
                Assertion("Applies two or more conditions", reg["has_multiple_conditions"]),
                Assertion("Also inflicts damage", reg["has_negative_hp_change"]),
                Assertion("Narrative conveys ambush urgency", reg["is_visceral"]),
            ],
        ),
        Scenario(
            scenario_id="stamina_heavy_attack",
            name="Stamina-heavy attack",
            description="A warrior spends serious physical effort on a devastating swing.",
            setup=ScenarioSetup(level=6, location="ashen_woods", tension=6, inferred_class="Warrior"),
            action_text="I plant my feet and pour everything into one devastating overhead strike meant to split the monster in half.",
            assertions=[
                *base_contract(),
                Assertion("Consumes stamina", reg["has_stamina_change_negative"]),
                Assertion("Includes dice rolls", reg["has_dice_rolls"]),
                Assertion("Narrative reflects extreme physical effort", reg["mentions_extreme_effort"]),
            ],
        ),
        Scenario(
            scenario_id="antidote_condition_removal",
            name="Condition removal through antidote",
            description="An existing poison should be removable with the right item.",
            setup=ScenarioSetup(
                level=4,
                location="ashen_woods",
                tension=5,
                initial_inventory=[{"item_id": "antidote", "name": "Antidote", "description": "A sharp-smelling anti-toxin vial.", "rarity": "common"}],
                active_conditions=[{"condition_id": "poisoned", "name": "Poisoned", "description": "Loses 5 HP per turn.", "duration_turns": 3, "applied_at_turn": 0, "is_buff": False}],
            ),
            action_text="I uncork the antidote, drink it at once, and force the poison out before it spreads any farther.",
            assertions=[
                *base_contract(),
                Assertion("Removes an active condition", reg["has_conditions_remove"]),
                Assertion("Consumes the antidote", reg["has_inventory_remove"]),
                Assertion("Narrative confirms poison relief", reg["narrative_shows_healing"]),
            ],
        ),
        Scenario(
            scenario_id="tier2_combat_rot_herald",
            name="Tier 2 combat against the Herald of Rot",
            description="A high-level combat test should stay dangerous and structured.",
            setup=ScenarioSetup(level=35, location="sealed_wastes", tension=7, inferred_class="Warrior"),
            action_text="I charge the Herald of Rot head-on and try to break through its corrupted guard before the blight floods the field.",
            assertions=[
                *base_contract(),
                Assertion("Includes combat dice rolls", reg["has_dice_rolls"]),
                Assertion("Inflicts real damage pressure", reg["has_negative_hp_change"]),
                Assertion("Keeps tension high", reg["tension_at_least"](6)),
            ],
        ),
        Scenario(
            scenario_id="corrupted_magic_backfire",
            name="Corrupted magic backfire",
            description="Unsafe spellcasting in a tainted zone should rebound on the caster.",
            setup=ScenarioSetup(level=8, location="sealed_wastes", tension=7, inferred_class="Mage"),
            action_text="I cast without restraint inside the corrupted zone and force the Thread to obey me.",
            assertions=[
                *base_contract(),
                Assertion("Consumes mana", reg["has_mp_change_negative"]),
                Assertion("Backfire also harms the caster", reg["has_negative_hp_change"]),
                Assertion("Narrative describes corruption backlash", reg["mentions_corruption_backfire"]),
            ],
        ),
        Scenario(
            scenario_id="buy_item_smith_sword",
            name="Buying an item from the smith",
            description="A straightforward transaction should still produce concrete inventory output.",
            setup=ScenarioSetup(level=3, location="port_myr", tension=2),
            action_text="I pay the smith for a serviceable sword and inspect the blade before leaving the stall.",
            assertions=[
                *base_contract(),
                Assertion("Adds an item to inventory", reg["has_inventory_add"]),
                Assertion("Narrative confirms the transaction", lambda n, gs, rt: "pay" in n.lower() or "smith" in n.lower() or "coin" in n.lower()),
            ],
        ),
        Scenario(
            scenario_id="lore_vorathek_primordial_thread",
            name="Lore: Vor'Athek and the Primordial Thread",
            description="A lore-heavy question should surface proper canon vocabulary.",
            setup=ScenarioSetup(level=5, location="port_myr", tension=2),
            action_text="I ask the Guild scholar what Vor'Athek truly was and what the Primordial Thread still means for Aerus.",
            assertions=[
                *base_contract(),
                Assertion("Narrative mentions Vor'Athek by name", reg["mentions_vorathek"]),
                Assertion("Narrative mentions the Primordial Thread or corruption", reg["mentions_primordial_thread_or_corruption"]),
                Assertion("Keeps conversational tension low", reg["tension_at_most"](4)),
            ],
        ),
        Scenario(
            scenario_id="corrupted_zone_arcane_ash_desert",
            name="Corrupted zone traversal",
            description="Crossing a highly corrupted environment should show environmental hostility.",
            setup=ScenarioSetup(level=10, location="sealed_wastes", tension=6),
            action_text="I cross the Arcane Ash Desert at the edge of the old sealing scar and watch how the land itself reacts to me.",
            assertions=[
                *base_contract(),
                Assertion("Narrative describes environmental corruption", reg["mentions_primordial_thread_or_corruption"]),
                Assertion("Keeps tension elevated", reg["tension_at_least"](5)),
                Assertion("Produces state change or events", lambda n, gs, rt: bool(gs.get("state_delta")) or bool(gs.get("game_events"))),
            ],
        ),
    ]
