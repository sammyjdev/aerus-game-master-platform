#!/usr/bin/env python3
"""Validate migration ledger integrity and deletion safety.

Usage:
  python scripts/validate_migration_ledger.py --ledger docs/ai-ops/migration/legacy-comparative-ledger.md
  python scripts/validate_migration_ledger.py --ledger ... --deleted-file path1 --deleted-file path2
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def _normalize(path: str) -> str:
    cleaned = path.strip().strip("`").strip()
    return cleaned.replace("\\", "/")


def _parse_table_rows(lines: list[str], required_headers: list[str]) -> tuple[int, list[list[str]]]:
    start = -1
    for idx, line in enumerate(lines):
        raw = line.strip().lower()
        if not raw.startswith("|"):
            continue
        if all(h.lower() in raw for h in required_headers):
            start = idx
            break
    if start == -1:
        return -1, []

    rows: list[list[str]] = []
    for line in lines[start + 2 :]:
        raw = line.strip()
        if not raw.startswith("|"):
            break
        cols = [c.strip() for c in raw.split("|")[1:-1]]
        rows.append(cols)
    return start, rows


def _parse_ledger(
    ledger_path: Path,
) -> tuple[dict[str, str], dict[str, tuple[str, str]], list[str], list[str]]:
    lines = ledger_path.read_text(encoding="utf-8").splitlines()

    _, main_rows = _parse_table_rows(lines, ["legacy file", "status", "notes"])
    status_map: dict[str, str] = {}
    pending_rows: list[str] = []
    issues: list[str] = []

    for cols in main_rows:
        if len(cols) < 4:
            continue
        legacy_file = _normalize(cols[0])
        status = cols[2]
        if legacy_file == "-":
            continue
        if legacy_file in status_map and status_map[legacy_file] != status:
            issues.append(f"Conflicting status for {legacy_file}: {status_map[legacy_file]} vs {status}")
        status_map[legacy_file] = status
        if status.startswith("pending"):
            pending_rows.append(legacy_file)

    _, removal_rows = _parse_table_rows(lines, ["file", "justification", "approved by", "date"])
    approvals: dict[str, tuple[str, str]] = {}
    for cols in removal_rows:
        if len(cols) < 4:
            continue
        file_path = _normalize(cols[0])
        approver = cols[2].strip()
        date = cols[3].strip()
        if file_path == "-":
            continue
        approvals[file_path] = (approver, date)

    return status_map, approvals, issues, pending_rows


def _parse_approvers(raw: str) -> list[str]:
    chunks = re.split(r"[+,;]", raw)
    return [c.strip() for c in chunks if c.strip()]


def _load_registry(path: Path) -> tuple[set[str], set[str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    allowed = set(data.get("allowed_approvers", []))
    required = set(data.get("required_for_removal", []))
    return allowed, required


def validate(ledger_path: Path, deleted_files: list[str], registry_path: Path | None = None) -> int:
    status_map, approvals, issues, pending_rows = _parse_ledger(ledger_path)
    allowed_approvers: set[str] = set()
    required_removal_approvers: set[str] = set()

    if registry_path is not None:
        if not registry_path.exists():
            issues.append(f"Approval registry not found: {registry_path}")
        else:
            allowed_approvers, required_removal_approvers = _load_registry(registry_path)

    for file_path, (approver, date) in approvals.items():
        if not approver or approver == "-":
            issues.append(f"Removal candidate missing approver: {file_path}")
        if not date or date == "-":
            issues.append(f"Removal candidate missing date: {file_path}")
        if file_path not in status_map:
            issues.append(f"Removal candidate not found in legacy table: {file_path}")
        elif status_map[file_path] == "kept":
            issues.append(f"Removal candidate cannot be status=kept: {file_path}")

        if approver and approver != "-" and allowed_approvers:
            parsed = _parse_approvers(approver)
            if not parsed:
                issues.append(f"Removal candidate has unparsable approver list: {file_path}")
            else:
                unknown = [a for a in parsed if a not in allowed_approvers]
                if unknown:
                    issues.append(
                        f"Removal candidate has unknown approver(s) {unknown}: {file_path}"
                    )
                if required_removal_approvers and not required_removal_approvers.issubset(set(parsed)):
                    issues.append(
                        f"Removal candidate missing required removal approvers {sorted(required_removal_approvers)}: {file_path}"
                    )

    normalized_deleted = [_normalize(f) for f in deleted_files]
    for file_path in normalized_deleted:
        if file_path not in approvals:
            issues.append(
                f"Deleted file is not approved in removal candidates table: {file_path}"
            )

    if pending_rows:
        issues.append(
            "Ledger still contains pending rows: " + ", ".join(sorted(pending_rows))
        )

    if issues:
        print("Ledger validation failed:")
        for item in issues:
            print(f"- {item}")
        return 1

    print("Ledger validation passed.")
    print(f"Tracked legacy rows: {len(status_map)}")
    print(f"Approved removal candidates: {len(approvals)}")
    print(f"Deleted files checked: {len(normalized_deleted)}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--ledger",
        default="docs/ai-ops/migration/legacy-comparative-ledger.md",
        help="Path to migration ledger markdown file",
    )
    parser.add_argument(
        "--deleted-file",
        action="append",
        default=[],
        help="Deleted file path to verify against approved removal candidates",
    )
    parser.add_argument(
        "--registry",
        default="docs/ai-ops/rules/approval-authority-registry.json",
        help="Approval authority registry JSON path",
    )
    args = parser.parse_args()

    ledger_path = Path(args.ledger)
    if not ledger_path.exists():
        print(f"Ledger not found: {ledger_path}")
        return 2

    registry_path = Path(args.registry) if args.registry else None
    return validate(ledger_path, args.deleted_file, registry_path)


if __name__ == "__main__":
    sys.exit(main())
