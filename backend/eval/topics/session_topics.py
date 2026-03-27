from __future__ import annotations


def build_scenarios(reg: dict) -> list:
    Scenario = reg["Scenario"]
    ScenarioSetup = reg["ScenarioSetup"]
    ScenarioTurn = reg["ScenarioTurn"]
    Assertion = reg["Assertion"]
    base_contract = reg["base_contract"]

    return [
        Scenario(
            scenario_id="session_emergent_followup",
            name="Emergent multi-turn session continuity",
            description="A two-turn scene where the second move follows a variable introduced by the model in the first response.",
            setup=ScenarioSetup(level=4, location="port_myr", tension=4, coop_mission_active=True, coop_mission_completed=False),
            turns=[
                ScenarioTurn(action_text="I press the dock official for answers about the mark on my arm and the false calm hanging over Port Myr."),
                ScenarioTurn(action_text="", dynamic_followup=True),
            ],
            assertions=[
                *base_contract(),
                Assertion("Returns substantial narrative", reg["has_nonempty_narrative"], dimension="narrative"),
                Assertion("Narrative remains creatively specific", reg["narrative_is_creative_enough"], dimension="narrative"),
                Assertion("Lore remains specific instead of generic", reg["lore_is_specific_not_generic"], dimension="world"),
            ],
            suites={"complex"},
            tags={"session", "continuity", "emergent"},
        ),
    ]
