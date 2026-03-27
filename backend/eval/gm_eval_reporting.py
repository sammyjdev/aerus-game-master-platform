"""Shared history, comparison, and final reporting helpers for GM eval runs."""
from __future__ import annotations

import datetime as dt
import json
import time
import uuid
from pathlib import Path
from typing import Any, Sequence

from eval.gm_eval_assertions import assertion_category, assertion_dimension, scenario_hard_fail_labels
from eval.gm_eval_models import DIMENSIONS

LINE = "=" * 72
THIN = "-" * 72
PASS = "PASS"
FAIL = "FAIL"


def _history_file_path(default_filename: str = "gm_eval_runs.jsonl", env_value: str | None = None) -> Path:
    env_path = (env_value or "").strip()
    return Path(env_path) if env_path else Path(__file__).parent / "history" / default_filename


def _load_history_records(path: Path, max_records: int = 200) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8") as fp:
            for line in fp:
                raw = line.strip()
                if not raw:
                    continue
                try:
                    parsed = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if isinstance(parsed, dict):
                    records.append(parsed)
    except OSError:
        return []
    return records[-max_records:]


def _append_history_record(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(record, ensure_ascii=False) + "\n")


def _get_attr_or_item(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(key, default)
    return getattr(value, key, default)


def _build_run_record(
    results: Sequence[Any],
    model_name: str,
    run_started_at: float,
    profile: dict[str, str],
) -> dict[str, Any]:
    total_checks = sum(int(_get_attr_or_item(result, "total", 0) or 0) for result in results)
    total_passed = sum(int(_get_attr_or_item(result, "score", 0) or 0) for result in results)
    pass_percent = int(100 * total_passed / total_checks) if total_checks else 0
    contract_total = 0
    contract_passed = 0
    narrative_total = 0
    narrative_passed = 0
    core_total = 0
    core_passed = 0
    extended_total = 0
    extended_passed = 0
    dimension_totals: dict[str, dict[str, int]] = {dimension: {"passed": 0, "total": 0} for dimension in DIMENSIONS}
    suite_totals: dict[str, dict[str, int]] = {}
    hard_fail_count = 0

    scenario_entries: list[dict[str, Any]] = []
    for idx, result in enumerate(results, start=1):
        scenario = _get_attr_or_item(result, "scenario", {})
        assertions = list(_get_attr_or_item(scenario, "assertions", []) or [])
        passed = list(_get_attr_or_item(result, "passed", []) or [])
        failed = list(_get_attr_or_item(result, "failed", []) or [])
        category_by_label = {
            _get_attr_or_item(assertion, "label", ""): assertion_category(assertion)
            for assertion in assertions
        }
        dimension_by_label = {
            _get_attr_or_item(assertion, "label", ""): assertion_dimension(assertion)
            for assertion in assertions
        }
        scenario_contract_total = sum(1 for assertion in assertions if assertion_category(assertion) == "contract")
        scenario_narrative_total = sum(1 for assertion in assertions if assertion_category(assertion) == "narrative")
        scenario_contract_passed = sum(1 for label in passed if category_by_label.get(label) == "contract")
        scenario_narrative_passed = sum(1 for label in passed if category_by_label.get(label) == "narrative")

        contract_total += scenario_contract_total
        contract_passed += scenario_contract_passed
        narrative_total += scenario_narrative_total
        narrative_passed += scenario_narrative_passed
        if _get_attr_or_item(scenario, "tier", "core") == "core":
            core_total += int(_get_attr_or_item(result, "total", 0) or 0)
            core_passed += int(_get_attr_or_item(result, "score", 0) or 0)
        else:
            extended_total += int(_get_attr_or_item(result, "total", 0) or 0)
            extended_passed += int(_get_attr_or_item(result, "score", 0) or 0)
        dimension_scores = _get_attr_or_item(result, "dimension_scores", {}) or {}
        for dimension, values in dimension_scores.items():
            dimension_totals.setdefault(dimension, {"passed": 0, "total": 0})
            dimension_totals[dimension]["passed"] += int((values or {}).get("passed", 0))
            dimension_totals[dimension]["total"] += int((values or {}).get("total", 0))
        for suite in _get_attr_or_item(scenario, "suites", []) or []:
            suite_totals.setdefault(suite, {"passed": 0, "total": 0})
            suite_totals[suite]["passed"] += int(_get_attr_or_item(result, "score", 0) or 0)
            suite_totals[suite]["total"] += int(_get_attr_or_item(result, "total", 0) or 0)
        hard_fail_count += len(list(_get_attr_or_item(result, "hard_failures", []) or []))

        scenario_entries.append(
            {
                "index": idx,
                "scenario_id": _get_attr_or_item(scenario, "scenario_id", ""),
                "name": _get_attr_or_item(scenario, "name", ""),
                "tier": _get_attr_or_item(scenario, "tier", "core"),
                "suites": sorted(set(_get_attr_or_item(scenario, "suites", []) or [])),
                "tags": sorted(set(_get_attr_or_item(scenario, "tags", []) or [])),
                "score": int(_get_attr_or_item(result, "score", 0) or 0),
                "total": int(_get_attr_or_item(result, "total", 0) or 0),
                "error": _get_attr_or_item(result, "error", None),
                "failed_assertions": failed,
                "passed_assertions": passed,
                "hard_failures": list(_get_attr_or_item(result, "hard_failures", []) or []),
                "failed_assertions_detail": [
                    {
                        "label": label,
                        "category": category_by_label.get(label, "contract"),
                        "dimension": dimension_by_label.get(label, "contract"),
                        "hard_fail": label in scenario_hard_fail_labels(scenario),
                    }
                    for label in failed
                ],
                "passed_assertions_detail": [
                    {
                        "label": label,
                        "category": category_by_label.get(label, "contract"),
                        "dimension": dimension_by_label.get(label, "contract"),
                    }
                    for label in passed
                ],
                "contract_checks": {"passed": scenario_contract_passed, "total": scenario_contract_total},
                "narrative_checks": {"passed": scenario_narrative_passed, "total": scenario_narrative_total},
                "dimension_scores": dimension_scores,
                "elapsed_seconds": round(float(_get_attr_or_item(result, "elapsed_seconds", 0.0) or 0.0), 2),
                "json_present": bool(_get_attr_or_item(result, "game_state", None)),
                "narrative_chars": len(_get_attr_or_item(result, "narrative", "") or ""),
                "turn_results": list(_get_attr_or_item(result, "turn_results", []) or []),
            }
        )

    return {
        "version": 4,
        "run_id": str(uuid.uuid4()),
        "timestamp_utc": dt.datetime.now(dt.UTC).isoformat(),
        "model": model_name,
        "profile": profile.get("profile"),
        "track": profile.get("track"),
        "suite": profile.get("suite"),
        "tier_filter": profile.get("tier"),
        "duration_seconds": round(time.time() - run_started_at, 2),
        "total_checks": total_checks,
        "total_passed": total_passed,
        "pass_percent": pass_percent,
        "contract_checks": {"passed": contract_passed, "total": contract_total},
        "narrative_checks": {"passed": narrative_passed, "total": narrative_total},
        "core_checks": {"passed": core_passed, "total": core_total},
        "extended_checks": {"passed": extended_passed, "total": extended_total},
        "dimension_scores": dimension_totals,
        "suite_scores": suite_totals,
        "hard_fail_count": hard_fail_count,
        "scenario_count": len(results),
        "problem_scenarios": [
            idx
            for idx, result in enumerate(results, start=1)
            if _get_attr_or_item(result, "failed", []) or _get_attr_or_item(result, "error", None) or _get_attr_or_item(result, "hard_failures", [])
        ],
        "scenarios": scenario_entries,
    }


def _failed_assertion_map(record: dict[str, Any]) -> dict[str, dict[str, Any]]:
    mapping: dict[str, dict[str, Any]] = {}
    scenarios = record.get("scenarios", [])
    if not isinstance(scenarios, list):
        return mapping
    for scenario in scenarios:
        if not isinstance(scenario, dict):
            continue
        scenario_key = scenario.get("scenario_id") or scenario.get("index")
        for label in scenario.get("failed_assertions", []):
            key = f"{scenario_key}|{label}"
            mapping[key] = {
                "index": scenario.get("index"),
                "scenario_id": scenario.get("scenario_id"),
                "scenario_name": scenario.get("name", ""),
                "assertion": label,
            }
    return mapping


def _top_failed_assertions(record: dict[str, Any], limit: int = 8) -> list[tuple[str, int]]:
    counts: dict[str, int] = {}
    scenarios = record.get("scenarios", [])
    if not isinstance(scenarios, list):
        return []
    for scenario in scenarios:
        if not isinstance(scenario, dict):
            continue
        for label in scenario.get("failed_assertions", []):
            counts[label] = counts.get(label, 0) + 1
    return sorted(counts.items(), key=lambda item: item[1], reverse=True)[:limit]


def _find_previous_record(history: list[dict[str, Any]], model_name: str, profile: dict[str, str]) -> dict[str, Any] | None:
    for record in reversed(history):
        if (
            record.get("model") == model_name
            and record.get("suite") == profile.get("suite")
            and record.get("track") == profile.get("track")
        ):
            return record
    return history[-1] if history else None


def _print_comparison_report(current_record: dict[str, Any], previous_record: dict[str, Any] | None) -> None:
    print(f"\n{LINE}")
    print("History Comparison")
    print(LINE)
    if previous_record is None:
        print("No previous run found. This run becomes the new baseline.")
        return

    current_failed = _failed_assertion_map(current_record)
    previous_failed = _failed_assertion_map(previous_record)
    current_keys = set(current_failed)
    previous_keys = set(previous_failed)

    new_failures = sorted(current_keys - previous_keys)
    fixed_failures = sorted(previous_keys - current_keys)
    persistent = sorted(current_keys & previous_keys)

    print(f"Compared with: {previous_record.get('timestamp_utc', 'unknown')} ({previous_record.get('model', 'unknown')})")
    print(f"New regressions: {len(new_failures)}")
    print(f"Fixed checks: {len(fixed_failures)}")
    print(f"Persistent failures: {len(persistent)}")

    if new_failures:
        print("\nNew regressions:")
        for key in new_failures[:10]:
            item = current_failed[key]
            print(f"- [{item['index']}] {item['scenario_name']} :: {item['assertion']}")

    if persistent:
        print("\nStill failing:")
        for key in persistent[:12]:
            item = current_failed[key]
            print(f"- [{item['index']}] {item['scenario_name']} :: {item['assertion']}")


def _print_final_report(
    results: Sequence[Any],
    current_record: dict[str, Any],
    previous_record: dict[str, Any] | None,
) -> None:
    total_checks = int(current_record.get("total_checks", 0) or 0)
    total_passed = int(current_record.get("total_passed", 0) or 0)
    pass_percent = int(current_record.get("pass_percent", 0) or 0)
    contract = current_record.get("contract_checks", {}) or {}
    narrative = current_record.get("narrative_checks", {}) or {}
    core = current_record.get("core_checks", {}) or {}
    extended = current_record.get("extended_checks", {}) or {}
    dimensions = current_record.get("dimension_scores", {}) or {}
    suites = current_record.get("suite_scores", {}) or {}
    hard_fail_count = int(current_record.get("hard_fail_count", 0) or 0)
    print(f"\n{LINE}")
    print(f"Final Result: {total_passed}/{total_checks} checks passed ({pass_percent}%)")
    print(LINE)
    print(
        "Contract checks: "
        f"{int(contract.get('passed', 0))}/{int(contract.get('total', 0))} | "
        "Narrative checks: "
        f"{int(narrative.get('passed', 0))}/{int(narrative.get('total', 0))}"
    )
    print(
        "Core tier: "
        f"{int(core.get('passed', 0))}/{int(core.get('total', 0))} | "
        "Extended tier: "
        f"{int(extended.get('passed', 0))}/{int(extended.get('total', 0))}"
    )
    print(f"Hard fails: {hard_fail_count}")
    if dimensions:
        print("Dimension scores:")
        for dimension in DIMENSIONS:
            values = dimensions.get(dimension, {})
            print(f"- {dimension}: {int(values.get('passed', 0))}/{int(values.get('total', 0))}")
    if suites:
        print("Suite scores:")
        for suite_name, values in sorted(suites.items()):
            if suite_name == "all":
                continue
            print(f"- {suite_name}: {int(values.get('passed', 0))}/{int(values.get('total', 0))}")

    if current_record.get("problem_scenarios"):
        print(f"Problem scenarios: {current_record['problem_scenarios']}")
    else:
        print("All evaluated scenarios passed.")
    scenarios = current_record.get("scenarios", [])
    if isinstance(scenarios, list):
        problem_entries = [
            scenario
            for scenario in scenarios
            if isinstance(scenario, dict) and (scenario.get("failed_assertions") or scenario.get("error") or scenario.get("hard_failures"))
        ]
        if problem_entries:
            print("Scenario failures:")
            for scenario in problem_entries[:8]:
                labels = ", ".join(str(label) for label in scenario.get("failed_assertions", [])[:6]) or "runtime error"
                if scenario.get("hard_failures"):
                    labels += f" | hard-fails: {', '.join(str(label) for label in scenario.get('hard_failures', [])[:4])}"
                print(f"- [{scenario.get('index')}] {scenario.get('name', 'unknown')}: {labels}")
    top_failures = _top_failed_assertions(current_record)
    if top_failures:
        print("Most common failing checks:")
        for label, count in top_failures:
            print(f"- {count}x {label}")

    if results:
        slowest = sorted(results, key=lambda result: float(_get_attr_or_item(result, "elapsed_seconds", 0.0) or 0.0), reverse=True)[:3]
        print("\nSlowest scenarios:")
        for result in slowest:
            scenario = _get_attr_or_item(result, "scenario", {})
            scenario_name = _get_attr_or_item(scenario, "name", "")
            elapsed = float(_get_attr_or_item(result, "elapsed_seconds", 0.0) or 0.0)
            print(f"- {scenario_name}: {elapsed:.1f}s")

    _print_comparison_report(current_record, previous_record)
