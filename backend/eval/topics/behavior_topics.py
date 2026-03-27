from __future__ import annotations


def build_scenarios(reg: dict) -> list:
    Scenario = reg["Scenario"]
    ScenarioSetup = reg["ScenarioSetup"]
    Assertion = reg["Assertion"]
    base_contract = reg["base_contract"]

    return [
        Scenario(
            scenario_id="absurd_tame_corrupted_creature",
            name="Absurd action: taming a corrupted creature",
            description="The GM should respond in fiction and attach consequences.",
            setup=ScenarioSetup(level=3, location="ashen_woods", tension=6),
            action_text="I walk straight toward the corrupted Ash Golem, speak gently, and try to domesticate it like a loyal hound.",
            assertions=[
                *base_contract(),
                Assertion("Narrates a consequence instead of ignoring the action", reg["gm_handles_absurd_with_consequence"]),
            ],
        ),
        Scenario(
            scenario_id="meta_knowledge_ooc",
            name="Out-of-character meta knowledge",
            description="The player uses knowledge their character should not have.",
            setup=ScenarioSetup(level=4, location="port_myr", tension=4),
            action_text="I already know from outside knowledge that the hidden mechanism is behind the third torch, so I skip straight to it.",
            assertions=[
                *base_contract(),
                Assertion("GM responds in fiction rather than meta commentary", reg["gm_stays_in_character"]),
                Assertion("Narrative still incorporates the torch clue in-world", lambda n, gs, rt: "torch" in n.lower() or "light" in n.lower()),
            ],
        ),
        Scenario(
            scenario_id="missing_inventory_item",
            name="Missing inventory item",
            description="The player tries to use a potion that is not in inventory.",
            setup=ScenarioSetup(level=3, hp_fraction=0.2, location="ashen_woods", tension=5),
            action_text="I drink the healing potion from my pack even though I have not found one today.",
            assertions=[
                *base_contract(),
                Assertion("Narrative denies use of the missing item", reg["gm_refuses_nonexistent_item"]),
                Assertion("Healing is not applied", lambda n, gs, rt: not reg["has_positive_hp_change"](n, gs, rt)),
            ],
        ),
        Scenario(
            scenario_id="dispute_roll_result",
            name="Dispute over a dice result",
            description="The player argues a poor roll should have succeeded.",
            setup=ScenarioSetup(level=6, location="ashen_woods", tension=5),
            action_text="That roll of six should have hit given my experience, and I argue with the outcome instead of taking the miss.",
            history_messages=[{"role": "assistant", "content": "Your strike glances off the creature's plated shoulder. The blow fails to land cleanly."}],
            assertions=[
                *base_contract(),
                Assertion("GM does not retroactively change the roll", reg["gm_maintains_roll_result"]),
                Assertion("GM acknowledges the dispute in fiction", reg["gm_acknowledges_dispute"]),
            ],
        ),
        Scenario(
            scenario_id="dispute_damage_received",
            name="Dispute over damage received",
            description="The player contests a large damage amount after the fact.",
            setup=ScenarioSetup(level=6, hp_fraction=0.5, location="ashen_woods", tension=6),
            action_text="Thirty-five damage from that thing is absurd, and I push back against the wound instead of accepting it.",
            history_messages=[{"role": "assistant", "content": "The creature's impact caves the breath out of you and tears through your guard."}],
            assertions=[
                *base_contract(),
                Assertion("GM does not retroactively change prior damage", reg["gm_maintains_roll_result"]),
                Assertion("GM acknowledges the frustration without breaking tone", reg["gm_acknowledges_dispute"]),
            ],
        ),
        Scenario(
            scenario_id="morally_ambiguous_innocent_npc",
            name="Morally ambiguous innocent kill",
            description="The GM should not sanitize a cruel action.",
            setup=ScenarioSetup(level=6, location="port_myr", tension=6),
            action_text="I kill the unarmed courier before he can warn anyone, even though he is not the one I came for.",
            assertions=[
                *base_contract(require_followup=False),
                Assertion("Narrative does not sanitize the act", reg["narrative_shows_crime_consequence"]),
                Assertion("Narrative recognizes the moral weight", reg["narrative_acknowledges_moral_weight"]),
                Assertion("Generates some social or consequence signal", reg["has_social_consequence_event"]),
            ],
        ),
        Scenario(
            scenario_id="impossible_action_fly_without_ability",
            name="Impossible action: flying without an ability",
            description="The GM should deny the impossible and narrate the consequence.",
            setup=ScenarioSetup(level=4, location="cliffside_ruin", tension=6),
            action_text="I leap from the cliff and try to fly through sheer force of will, even though I have no such power.",
            assertions=[
                *base_contract(require_followup=False),
                Assertion("The GM does not grant flight", reg["gm_handles_absurd_with_consequence"]),
                Assertion("The fall causes damage", reg["has_negative_hp_change"]),
                Assertion("Narrative describes the fall", reg["mentions_fall_consequence"]),
            ],
        ),
    ]
