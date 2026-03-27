"""
gm_eval.py - Orchestrates behavioral evaluation runs for the Aerus Game Master.

Usage:
    cd backend
    .venv/Scripts/python eval/gm_eval.py

Optional environment variables:
    AERUS_EVAL_PROFILE=default   Use default, extended, or full-baseline presets
    AERUS_EVAL_SCENARIOS=1,3     Run only specific scenario indexes
    AERUS_EVAL_LIMIT=2           Run only the first N scenarios
    AERUS_EVAL_TIER=core         Run only core, extended, or all scenarios
    AERUS_EVAL_SUITES=basic      Filter by suite names
    AERUS_EVAL_INCLUDE_STABLE=1  Re-run scenarios that already passed in the last baseline
    AERUS_EVAL_MAX_TOKENS=600    Override the response budget for GM calls
    AERUS_EVAL_SCENARIO_TIMEOUT_SECONDS=75  Per-scenario timeout for the GM call
    AERUS_EVAL_CONCURRENCY=2     Number of independent scenarios to run in parallel
    AERUS_EVAL_HISTORY_FILE=...  Override the JSONL history file path
"""
from __future__ import annotations

import asyncio
import os
import sys
import time
from pathlib import Path

# Force UTF-8 on Windows consoles so reports remain readable
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]

# Make backend/src importable from backend/eval/
sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ.setdefault("CONFIG_DIR", str(Path(__file__).parent.parent / "config"))

# Eval defaults: OpenRouter-first validation, with Ollama kept only as an
# optional fallback/default local profile.
os.environ.setdefault("AERUS_OLLAMA_TIMEOUT_SECONDS", "60")
os.environ.setdefault("AERUS_LOCAL_ONLY", "false")
os.environ.setdefault("AERUS_OLLAMA_MODEL", "qwen2.5:7b-instruct")
os.environ.setdefault("AERUS_OLLAMA_GM_MODEL", os.environ["AERUS_OLLAMA_MODEL"])
os.environ.setdefault("AERUS_OLLAMA_EXTRACTOR_MODEL", os.environ["AERUS_OLLAMA_MODEL"])
os.environ.setdefault("AERUS_OLLAMA_BACKSTORY_MODEL", os.environ["AERUS_OLLAMA_MODEL"])
os.environ.setdefault("AERUS_OLLAMA_SUMMARIZER_MODEL", "phi4:mini")
os.environ.setdefault("AERUS_OLLAMA_HINT_MODEL", "phi4:mini")
os.environ.setdefault("AERUS_OLLAMA_CONVOCATION_MODEL", "phi4:mini")

from eval.gm_eval_assertions import build_topic_registry
from eval.gm_eval_models import Scenario, ScenarioTurn
from eval.gm_eval_reporting import (
    LINE,
    _append_history_record,
    _build_run_record,
    _find_previous_record,
    _history_file_path,
    _load_history_records,
    _print_final_report,
)
from eval.gm_eval_runtime import run_selected_scenarios
from eval.topics.behavior_topics import build_scenarios as build_behavior_topic_scenarios
from eval.topics.core_topics import build_scenarios as build_core_topic_scenarios
from eval.topics.multiplayer_topics import build_scenarios as build_multiplayer_topic_scenarios
from eval.topics.progression_topics import build_scenarios as build_progression_topic_scenarios
from eval.topics.session_topics import build_scenarios as build_session_topic_scenarios
from eval.topics.world_topics import build_scenarios as build_world_topic_scenarios
from src import vector_store
from src.local_llm import _ollama_model, configured_execution_mode, configured_hosted_model, configured_model_label, is_local_only

SUITE_ALIASES = {
    "basic": "critical_path",
    "intermediate": "full_core",
    "complex": "extended_story",
}


def _scenario_tier_for_id(scenario_id: str) -> str:
    core_ids = {
        "arrival_port_myr",
        "tier1_combat",
        "reputation_help_church",
        "coop_mission_blocking",
        "ability_unlock_level5",
        "structured_levelup",
        "loot_complete_structure",
        "player_death_permadeath",
        "debuff_condition_applied",
        "healing_potion_use",
        "two_players_divergent_actions",
        "missing_inventory_item",
        "class_mutation_level25",
        "mp_usage_spellcasting",
        "partial_xp_no_level",
        "multiplayer_item_sharing",
        "lore_accuracy_pact_of_myr",
        "stamina_heavy_attack",
        "antidote_condition_removal",
        "tier2_combat_rot_herald",
        "corrupted_magic_backfire",
        "buy_item_smith_sword",
    }
    return "core" if scenario_id in core_ids else "extended"


def _resolve_eval_profile() -> dict[str, str]:
    profile = os.getenv("AERUS_EVAL_PROFILE", "default").strip().lower() or "default"
    presets = {
        "default": {"tier": "core", "include_stable": "0", "track": "critical_path", "suite": "basic"},
        "basic": {"tier": "core", "include_stable": "0", "track": "critical_path", "suite": "basic"},
        "core-full": {"tier": "core", "include_stable": "0", "track": "full_core", "suite": "intermediate"},
        "intermediate": {"tier": "core", "include_stable": "0", "track": "full_core", "suite": "intermediate"},
        "extended": {"tier": "extended", "include_stable": "0", "track": "extended_story", "suite": "complex"},
        "complex": {"tier": "extended", "include_stable": "0", "track": "extended_story", "suite": "complex"},
        "full-baseline": {"tier": "all", "include_stable": "1", "track": "all", "suite": "baseline"},
    }
    if profile not in presets:
        raise SystemExit("Invalid AERUS_EVAL_PROFILE. Use default/basic, core-full/intermediate, extended/complex, or full-baseline.")
    return {"profile": profile, **presets[profile]}


def _eval_max_tokens() -> int:
    raw = os.getenv("AERUS_EVAL_MAX_TOKENS", "").strip()
    if raw.isdigit():
        return max(350, int(raw))
    return 600


def _scenario_timeout_seconds() -> float:
    raw = os.getenv("AERUS_EVAL_SCENARIO_TIMEOUT_SECONDS", "").strip()
    try:
        return max(15.0, float(raw)) if raw else 75.0
    except ValueError:
        return 75.0


def _eval_concurrency() -> int:
    raw = os.getenv("AERUS_EVAL_CONCURRENCY", "").strip()
    if raw.isdigit():
        return max(1, int(raw))
    return 1


def _critical_path_scenario_ids() -> set[str]:
    return {
        "arrival_port_myr",
        "tier1_combat",
        "reputation_help_church",
        "coop_mission_blocking",
        "healing_potion_use",
        "two_players_divergent_actions",
        "missing_inventory_item",
        "lore_accuracy_pact_of_myr",
    }


def _build_scenarios() -> list[Scenario]:
    reg = build_topic_registry()
    scenarios: list[Scenario] = []
    scenarios.extend(build_core_topic_scenarios(reg))
    scenarios.extend(build_multiplayer_topic_scenarios(reg))
    scenarios.extend(build_behavior_topic_scenarios(reg))
    scenarios.extend(build_progression_topic_scenarios(reg))
    scenarios.extend(build_world_topic_scenarios(reg))
    scenarios.extend(build_session_topic_scenarios(reg))
    return scenarios


def _stable_scenario_ids(previous_record: dict[str, object] | None) -> set[str]:
    if not previous_record:
        return set()
    stable: set[str] = set()
    scenarios = previous_record.get("scenarios", [])
    if not isinstance(scenarios, list):
        return stable
    for scenario in scenarios:
        if not isinstance(scenario, dict) or scenario.get("error"):
            continue
        if int(scenario.get("score", 0) or 0) == int(scenario.get("total", 0) or 0):
            scenario_id = scenario.get("scenario_id")
            if isinstance(scenario_id, str) and scenario_id:
                stable.add(scenario_id)
    return stable


def _apply_scenario_metadata(scenarios: list[Scenario]) -> list[Scenario]:
    for scenario in scenarios:
        scenario.tier = _scenario_tier_for_id(scenario.scenario_id)
        scenario.suites = set(scenario.suites)
        if scenario.scenario_id in _critical_path_scenario_ids():
            scenario.suites.add("critical_path")
            scenario.suites.add("basic")
        if scenario.tier == "core":
            scenario.suites.add("full_core")
            scenario.suites.add("intermediate")
        if scenario.tier == "extended":
            scenario.suites.add("extended_story")
            scenario.suites.add("complex")
        scenario.suites.add("all")
        if not scenario.turns:
            scenario.turns = [ScenarioTurn(action_text=scenario.action_text, history_messages=list(scenario.history_messages))]
    return scenarios


def _select_scenarios(scenarios: list[Scenario], previous_record: dict[str, object] | None) -> list[Scenario]:
    selected = _apply_scenario_metadata(scenarios)
    profile = _resolve_eval_profile()
    raw_indexes = os.getenv("AERUS_EVAL_SCENARIOS", "").strip()
    if raw_indexes:
        wanted: set[int] = set()
        for part in raw_indexes.split(","):
            part = part.strip()
            if part.isdigit():
                wanted.add(int(part))
        selected = [scenario for idx, scenario in enumerate(selected, start=1) if idx in wanted]

    tier_filter = os.getenv("AERUS_EVAL_TIER", profile["tier"]).strip().lower()
    if tier_filter in {"core", "extended"}:
        selected = [scenario for scenario in selected if scenario.tier == tier_filter]
    elif tier_filter not in {"all", ""}:
        raise SystemExit("Invalid AERUS_EVAL_TIER. Use core, extended, or all.")

    track = profile.get("track", "")
    if track == "critical_path":
        critical_ids = _critical_path_scenario_ids()
        selected = [scenario for scenario in selected if scenario.scenario_id in critical_ids]
    elif track and track != "all":
        selected = [scenario for scenario in selected if track in scenario.suites]

    raw_suites = os.getenv("AERUS_EVAL_SUITES", "").strip().lower()
    if raw_suites:
        wanted = {SUITE_ALIASES.get(part.strip(), part.strip()) for part in raw_suites.split(",") if part.strip()}
        selected = [scenario for scenario in selected if scenario.suites & wanted]

    include_stable = os.getenv("AERUS_EVAL_INCLUDE_STABLE", profile["include_stable"]).strip().lower() in {"1", "true", "yes", "on"}
    if not raw_indexes and not include_stable:
        stable_ids = _stable_scenario_ids(previous_record)
        if stable_ids:
            selected = [scenario for scenario in selected if scenario.scenario_id not in stable_ids]

    raw_limit = os.getenv("AERUS_EVAL_LIMIT", "").strip()
    if raw_limit.isdigit():
        selected = selected[: int(raw_limit)]
    return selected


async def main() -> None:
    local_model_name = _ollama_model()
    run_started_at = time.time()
    history_path = _history_file_path(env_value=os.getenv("AERUS_EVAL_HISTORY_FILE", ""))
    history = _load_history_records(history_path)
    profile = _resolve_eval_profile()
    execution_mode = configured_execution_mode()
    hosted_model_name = configured_hosted_model(tension_level=5)
    model_name = configured_model_label(tension_level=5)
    previous_record = _find_previous_record(history, model_name, profile)

    print(LINE)
    print("AERUS GM EVALUATION")
    print(f"Execution mode: {execution_mode}")
    print(f"Eval model label: {model_name}")
    print(f"Local fallback model: {local_model_name}")
    if hosted_model_name:
        print(f"Hosted model: {hosted_model_name}")
    print(f"OpenRouter key present: {'yes' if bool(os.getenv('OPENROUTER_API_KEY', '').strip()) else 'no'}")
    print(f"Ollama URL: {os.getenv('AERUS_OLLAMA_URL', 'http://localhost:11434')}")
    print(f"Eval profile: {profile['profile']}")
    print(f"Eval suite: {profile.get('suite', 'unknown')}")
    print(f"Eval max tokens: {_eval_max_tokens()}")
    print(f"Per-scenario timeout: {_scenario_timeout_seconds():.0f}s")
    print(f"Eval concurrency: {_eval_concurrency()}")
    print(LINE)

    print("Preparing ChromaDB collections...")
    bestiary_count = await vector_store.ingest_bestiary()
    world_count = await vector_store.ingest_world_lore()
    print(f"ChromaDB ready: {bestiary_count} bestiary + {world_count} lore documents")

    scenarios = _select_scenarios(_build_scenarios(), previous_record)
    if not scenarios:
        raise SystemExit(
            "No scenarios selected. Everything may already be green, or the filters excluded all scenarios. "
            "Use AERUS_EVAL_INCLUDE_STABLE=1 to force a full run."
        )

    print(f"Running {len(scenarios)} scenario(s).")
    results = await run_selected_scenarios(
        scenarios,
        eval_max_tokens=_eval_max_tokens(),
        scenario_timeout_seconds=_scenario_timeout_seconds(),
        concurrency=_eval_concurrency(),
    )

    current_record = _build_run_record(results, model_name, run_started_at, profile)
    _print_final_report(results, current_record, previous_record)
    _append_history_record(history_path, current_record)
    print(f"\nHistory saved to: {history_path}")


if __name__ == "__main__":
    asyncio.run(main())
