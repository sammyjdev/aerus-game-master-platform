from __future__ import annotations


def build_scenarios(reg: dict) -> list:
    Scenario = reg["Scenario"]
    ScenarioSetup = reg["ScenarioSetup"]
    Assertion = reg["Assertion"]
    base_contract = reg["base_contract"]

    return [
        Scenario(
            scenario_id="narr_001_scene_opening",
            name="Abertura de cena — Porto Myr",
            description=(
                "Opening narration must be grounded and specific. "
                "No clichés, no introspective language, no exposition dumps."
            ),
            setup=ScenarioSetup(location="isles_of_myr", tension=3, level=1),
            action_text="Eu me levanto e busco formas de conseguir entender onde eu estou",
            hard_fail_labels={
                "Avoids forbidden cliché phrases",
            },
            assertions=[
                *base_contract(),
                Assertion("Returns substantial narrative", reg["has_nonempty_narrative"]),
                Assertion("Avoids forbidden cliché phrases", reg["has_no_cliche_phrases"]),
                Assertion("Mentions Port Myr or the harbor", reg["mentions_port_myr"]),
                Assertion("Keeps exploration tension low", reg["tension_at_most"](4)),
            ],
            suites={"narration"},
            tags={"narration", "opening", "cta"},
        ),
        Scenario(
            scenario_id="narr_002_social_npc",
            name="Resposta social — NPC age, não só fala",
            description=(
                "Social action response must show NPC physical behavior, not just dialogue. "
                "No clichés. No neutral outcome — NPC must open or close a path."
            ),
            setup=ScenarioSetup(location="isles_of_myr", tension=4, level=1),
            action_text="Tento me aproximar do grupo maior e iniciar conversa para extrair informação",
            hard_fail_labels={
                "Avoids forbidden cliché phrases",
            },
            assertions=[
                *base_contract(),
                Assertion("Returns substantial narrative", reg["has_nonempty_narrative"]),
                Assertion("Avoids forbidden cliché phrases", reg["has_no_cliche_phrases"]),
                Assertion("Mentions Port Myr or the harbor", reg["mentions_port_myr"]),
            ],
            suites={"narration"},
            tags={"narration", "social", "npc"},
        ),
        Scenario(
            scenario_id="narr_003_railroading",
            name="Railroading suave — pressão externa",
            description=(
                "When a player circles without progressing, the GM must introduce an external "
                "pressure element that forces a decision without removing agency. No clichés."
            ),
            tier="extended",
            setup=ScenarioSetup(location="isles_of_myr", tension=5, level=1),
            action_text="Continuo observando o bar em busca de mais informações",
            hard_fail_labels={
                "Avoids forbidden cliché phrases",
            },
            assertions=[
                *base_contract(),
                Assertion("Returns substantial narrative", reg["has_nonempty_narrative"]),
                Assertion("Avoids forbidden cliché phrases", reg["has_no_cliche_phrases"]),
            ],
            suites={"narration"},
            tags={"narration", "railroading", "cta"},
        ),
    ]
