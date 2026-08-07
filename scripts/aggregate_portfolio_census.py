"""Aggregate per-repository census receipts into one reconciled estate summary."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

AUDIT_SCHEMA = "glaciereq.portfolio.audit.v2"
SUMMARY_SCHEMA = "glaciereq.portfolio.census.summary.v1"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipts-dir", type=Path, required=True)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return payload


def expected_repositories(inventory: dict[str, Any]) -> tuple[str, list[str]]:
    owner = inventory.get("owner")
    root = inventory.get("portfolio_root")
    workspace = inventory.get("workspace_repositories")
    declared_total = inventory.get("total_repositories")
    if not isinstance(owner, str) or not owner:
        raise ValueError("Inventory owner is required")
    if not isinstance(root, str) or not root:
        raise ValueError("Inventory portfolio_root is required")
    if (
        not isinstance(workspace, list)
        or not workspace
        or not all(isinstance(item, str) and item for item in workspace)
    ):
        raise ValueError("Inventory workspace_repositories must be non-empty strings")

    root_repository = f"{owner}/{root}"
    repositories = [root_repository, *(f"{owner}/{item}" for item in workspace)]
    if len(repositories) != len(set(repositories)):
        raise ValueError("Canonical inventory contains duplicate repositories")
    if declared_total is not None:
        if not isinstance(declared_total, int) or declared_total < 1:
            raise ValueError("Inventory total_repositories must be a positive integer")
        if declared_total != len(repositories):
            raise ValueError(
                "Inventory total_repositories does not match root + workspace: "
                f"declared={declared_total} calculated={len(repositories)}"
            )
    return root_repository, repositories


def count_values(records: list[dict[str, Any]], *path: str) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for record in records:
        value: Any = record
        for key in path:
            if not isinstance(value, dict):
                value = None
                break
            value = value.get(key)
        counts[str(value if value is not None else "MISSING")] += 1
    return dict(sorted(counts.items()))


def action_queues(records: list[dict[str, Any]]) -> dict[str, list[str]]:
    queues = {
        "provenance_review": [],
        "attributed_downstream_review": [],
        "documentation_gap_review": [],
        "access_review": [],
        "reference_only": [],
        "retired": [],
        "verification_failed": [],
        "verification_dependency_blocked": [],
        "verification_no_test_path": [],
    }
    for record in records:
        repository = record.get("repository")
        if not isinstance(repository, str) or not repository:
            raise ValueError("Missing repository identity in action queue input")
        admission = record.get("admission_class")
        provenance = record.get("provenance")
        provenance_state = (
            provenance.get("state") if isinstance(provenance, dict) else None
        )
        verification = record.get("verification")
        python_verification = (
            verification.get("python") if isinstance(verification, dict) else None
        )
        verification_state = (
            python_verification.get("status")
            if isinstance(python_verification, dict)
            else None
        )

        if provenance_state == "UNRESOLVED":
            queues["provenance_review"].append(repository)
        if admission == "candidate_attributed_downstream":
            queues["attributed_downstream_review"].append(repository)
        if admission == "candidate_missing_readme":
            queues["documentation_gap_review"].append(repository)
        if admission in {"private_excluded", "private_or_inaccessible_excluded"}:
            queues["access_review"].append(repository)
        if admission == "supporting_reference_fork":
            queues["reference_only"].append(repository)
        if admission == "archive_or_retired":
            queues["retired"].append(repository)
        if verification_state == "FAILED":
            queues["verification_failed"].append(repository)
        if verification_state == "BLOCKED_DEPENDENCY":
            queues["verification_dependency_blocked"].append(repository)
        if verification_state == "NO_TEST_PATH":
            queues["verification_no_test_path"].append(repository)

    return {name: sorted(values) for name, values in queues.items()}


def summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "repository_count": len(records),
        "admission_classes": count_values(records, "admission_class"),
        "provenance_states": count_values(records, "provenance", "state"),
        "python_verification_states": count_values(
            records,
            "verification",
            "python",
            "status",
        ),
        "action_queues": action_queues(records),
    }


def build_summary(receipts_dir: Path, inventory: dict[str, Any]) -> dict[str, Any]:
    root_repository, expected = expected_repositories(inventory)
    expected_set = set(expected)

    records_by_repository: dict[str, dict[str, Any]] = {}
    for path in sorted(receipts_dir.rglob("census-*.json")):
        record = load_json(path)
        if record.get("schema") != AUDIT_SCHEMA:
            raise ValueError(
                f"Unexpected census schema in {path}: {record.get('schema')!r}"
            )
        repository = record.get("repository")
        if not isinstance(repository, str) or not repository:
            raise ValueError(f"Missing repository identity in {path}")
        if repository in records_by_repository:
            raise ValueError(f"Duplicate census receipt for {repository}")
        records_by_repository[repository] = record

    observed_set = set(records_by_repository)
    missing = sorted(expected_set - observed_set)
    unexpected = sorted(observed_set - expected_set)
    if missing or unexpected:
        raise ValueError(
            "Census coverage mismatch: "
            f"missing={missing!r} unexpected={unexpected!r}"
        )

    ordered_records = [records_by_repository[name] for name in expected]
    workspace_records = [
        record for record in ordered_records if record["repository"] != root_repository
    ]

    return {
        "schema": SUMMARY_SCHEMA,
        "owner": inventory["owner"],
        "portfolio_root": root_repository,
        "declared_repository_count": inventory.get("total_repositories"),
        "expected_repository_count": len(expected),
        "workspace_repository_count": len(workspace_records),
        "coverage": {
            "observed_repository_count": len(ordered_records),
            "unique_repository_count": len(records_by_repository),
            "missing_repositories": [],
            "unexpected_repositories": [],
            "complete": True,
        },
        "all_repositories": summarize(ordered_records),
        "workspace": summarize(workspace_records),
        "nonclaims": [
            "Census inclusion does not establish recruiter eligibility.",
            "Public and non-fork metadata does not establish authorship or originality.",
            "Verification state is bounded to the recorded test surface and exact receipt.",
        ],
    }


def main() -> int:
    args = parse_args()
    inventory = load_json(args.inventory)
    summary = build_summary(args.receipts_dir, inventory)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
