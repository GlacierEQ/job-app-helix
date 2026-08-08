#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from job_app_helix.innovation_engine import load_policy

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schemas" / "estate"
REQUIRED_SCHEMAS = {
    "estate",
    "repository",
    "lineage",
    "system",
    "capability",
    "mechanism",
    "bottleneck",
    "environment-model",
    "research-record",
    "hypothesis",
    "hypothesis-assessment",
    "hypothesis-tournament",
    "novelty-review",
    "experiment",
    "failure-model",
    "observability-contract",
    "measurement",
    "evidence",
    "verification",
    "promotion",
    "engineering-run",
    "adversarial-review",
    "target-assessment",
    "target-queue",
    "engineering-ledger",
}


def main() -> int:
    policy = load_policy()
    states = policy["states"]
    unknown_targets = sorted(
        {target for targets in states.values() for target in targets if target not in states}
    )
    if unknown_targets:
        raise SystemExit(f"unknown state transition targets: {unknown_targets}")

    requirements = policy.get("transition_requirements", {})
    if not isinstance(requirements, dict):
        raise SystemExit("transition_requirements must be an object")
    unknown_requirement_states = sorted(set(requirements) - set(states))
    if unknown_requirement_states:
        raise SystemExit(
            f"transition requirements reference unknown states: {unknown_requirement_states}"
        )

    schema_paths = sorted(SCHEMA_DIR.glob("*.schema.json"))
    names = {path.name.removesuffix(".schema.json") for path in schema_paths}
    missing = sorted(REQUIRED_SCHEMAS - names)
    if missing:
        raise SystemExit(f"missing estate schemas: {missing}")
    for path in schema_paths:
        schema = json.loads(path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)

    print(
        json.dumps(
            {
                "status": "VERIFIED",
                "policy_schema": policy["schema"],
                "states": len(states),
                "schemas": len(schema_paths),
                "transition_gates": len(requirements),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
