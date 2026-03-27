from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

DIMENSIONS = ("contract", "narrative", "progression", "world", "multiplayer")


@dataclass
class Assertion:
    label: str
    fn: Callable[[str, dict[str, Any], "RuntimeContext"], bool]
    category: str = "narrative"
    dimension: str = "narrative"


@dataclass
class ScenarioSetup:
    num_players: int = 1
    level: int = 1
    hp_fraction: float = 1.0
    location: str = "isles_of_myr"
    tension: int = 3
    coop_mission_active: bool = False
    coop_mission_completed: bool = True
    inferred_class: str = "Warrior"
    faction: str = "guild_of_threads"
    initial_inventory: list[dict[str, Any]] = field(default_factory=list)
    active_conditions: list[dict[str, Any]] = field(default_factory=list)
    extra_level: int | None = None
    extra_hp_fraction: float | None = None
    extra_inferred_class: str = "Mage"
    extra_faction: str = "myr_council"
    extra_initial_inventory: list[dict[str, Any]] = field(default_factory=list)
    extra_active_conditions: list[dict[str, Any]] = field(default_factory=list)
    current_turn: int = 1
    languages: list[str] = field(default_factory=lambda: ["common_tongue"])
    extra_languages: list[str] = field(default_factory=lambda: ["common_tongue"])
    currency: dict[str, int] = field(default_factory=lambda: {"copper": 0, "silver": 5, "gold": 0, "platinum": 0})
    extra_currency: dict[str, int] = field(default_factory=lambda: {"copper": 0, "silver": 5, "gold": 0, "platinum": 0})
    macros: list[dict[str, Any]] = field(default_factory=list)
    spell_aliases: dict[str, str] = field(default_factory=dict)
    extra_macros: list[dict[str, Any]] = field(default_factory=list)
    extra_spell_aliases: dict[str, str] = field(default_factory=dict)
    world_state: dict[str, str] = field(default_factory=dict)


@dataclass
class ScenarioTurn:
    action_text: str
    history_messages: list[dict[str, str]] = field(default_factory=list)
    dynamic_followup: bool = False


@dataclass
class Scenario:
    scenario_id: str
    name: str
    description: str
    setup: ScenarioSetup
    action_text: str = ""
    tier: str = "extended"
    assertions: list[Assertion] = field(default_factory=list)
    history_messages: list[dict[str, str]] = field(default_factory=list)
    suites: set[str] = field(default_factory=set)
    tags: set[str] = field(default_factory=set)
    hard_fail_labels: set[str] = field(default_factory=set)
    turns: list[ScenarioTurn] = field(default_factory=list)


@dataclass
class ScenarioResult:
    scenario: Scenario
    narrative: str
    game_state: dict[str, Any]
    raw_response: str
    passed: list[str]
    failed: list[str]
    error: str | None = None
    elapsed_seconds: float = 0.0
    dimension_scores: dict[str, dict[str, int]] = field(default_factory=dict)
    hard_failures: list[str] = field(default_factory=list)
    turn_results: list[dict[str, Any]] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.passed) + len(self.failed)

    @property
    def score(self) -> int:
        return len(self.passed)


@dataclass
class RuntimeContext:
    player_ids: list[str]
    player_names: list[str]
    player_name_to_id: dict[str, str]
    current_turn: int = 1
