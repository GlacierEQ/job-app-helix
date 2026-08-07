#!/usr/bin/env python3
"""Validate the governed company second-depth progression contract."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_STAGES = [
    "MAPPED_ONLY",
    "ROLE_VERIFIED",
    "PROBLEM_BOUNDED",
    "CODE_INSPECTED",
    "REMEDY_BOUNDED",
    "IMPLEMENTED",
    "PROOF_REPRODUCED",
    "CLAIM_PROMOTED",
]
EVIDENCE_FIELDS = {
    "role_evidence",
    "problem_evidence",
    "inspected_repositories",
    "gap_queue",
    "implementation_receipts",
    "proof_artifacts",
    "claim_receipts",
}


class SecondDepthValidationError(ValueError):
    """Raised when the second-depth registry violates its contract."""


def fail(message: str) -> None:
    raise SecondDepthValidationError(message)


def load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        fail(f"required file not found: {path}")
    except OSError as exc:
        fail(f"could not read {path}: {exc}")
    except json.JSONDecodeError as exc:
        fail(f"invalid JSON in {path}: {exc}")
    if not isinstance(payload, dict):
        fail(f"JSON root must be an object: {path}")
    return payload


def require_string(payload: dict[str, Any], field: str, source: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value:
        fail(f"{source}.{field} must be a non-empty string")
    return value


def require_list(payload: dict[str, Any], field: str, source: str) -> list[Any]:
    value = payload.get(field)
    if not isinstance(value, list):
        fail(f"{source}.{field} must be an array")
    return value


def string_set(values: list[Any], source: str) -> set[str]:
    if not all(isinstance(value, str) and value for value in values):
        fail(f"{source} contains an invalid string")
    if len(values) != len(set(values)):
        fail(f"{source} contains duplicate values")
    return set(values)


def resolved_state(defaults: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    return {**defaults, **override}


def validate_state(
    company_id: str,
    state: dict[str, Any],
    stage_index: dict[str, int],
    stage_contract: dict[str, dict[str, Any]],
) -> None:
    stage = state.get("stage")
    if stage not in stage_index:
        fail(f"{company_id}: invalid second-depth stage {stage!r}")

    for field in sorted(EVIDENCE_FIELDS):
        value = state.get(field)
        if not isinstance(value, list):
            fail(f"{company_id}.{field} must be an array")
        if not all(isinstance(item, (str, dict)) for item in value):
            fail(f"{company_id}.{field} contains an unsupported evidence value")

    blockers = state.get("blockers")
    if not isinstance(blockers, list) or not all(
        isinstance(item, str) and item for item in blockers
    ):
        fail(f"{company_id}.blockers must be an array of non-empty strings")

    next_gate = state.get("next_gate")
    if not isinstance(next_gate, str) or not next_gate:
        fail(f"{company_id}.next_gate must be a non-empty string")

    claim_ceiling = state.get("claim_ceiling")
    if not isinstance(claim_ceiling, str) or not claim_ceiling:
        fail(f"{company_id}.claim_ceiling must be a non-empty string")

    contract = stage_contract[stage]
    required_evidence = contract["minimum_evidence"]
    for field in required_evidence:
        if not state.get(field):
            fail(f"{company_id}: stage {stage} requires non-empty {field}")

    expected_ceiling = contract["public_claim_ceiling"]
    if claim_ceiling != expected_ceiling:
        fail(
            f"{company_id}: claim ceiling {claim_ceiling!r} does not match "
            f"stage {stage} ceiling {expected_ceiling!r}"
        )

    if stage_index[stage] < stage_index["PROOF_REPRODUCED"] and state["proof_artifacts"]:
        fail(f"{company_id}: proof artifacts cannot precede PROOF_REPRODUCED")
    if stage_index[stage] < stage_index["CLAIM_PROMOTED"] and state["claim_receipts"]:
        fail(f"{company_id}: claim receipts cannot precede CLAIM_PROMOTED")


def validate_second_depth(root: Path = ROOT) -> dict[str, Any]:
    index = load_json(root / "manifests" / "company_dossiers.json")
    registry_path = require_string(index, "second_depth_registry", "company_dossiers")
    registry = load_json(root / registry_path)

    if registry.get("schema") != "glaciereq.company-second-depth.v1":
        fail("unexpected second-depth schema")
    if registry.get("authority") != "GlacierEQ/job-app-helix":
        fail("unexpected second-depth authority")
    if registry.get("company_index") != "manifests/company_dossiers.json":
        fail("second-depth company index pointer drift")

    required_tracks = string_set(
        require_list(index, "required_company_tracks", "company_dossiers"),
        "company_dossiers.required_company_tracks",
    )

    stage_rows = require_list(registry, "stage_order", "company_second_depth")
    if len(stage_rows) != len(EXPECTED_STAGES):
        fail("second-depth stage count mismatch")
    stage_ids: list[str] = []
    stage_contract: dict[str, dict[str, Any]] = {}
    for ordinal, row in enumerate(stage_rows):
        if not isinstance(row, dict):
            fail("company_second_depth.stage_order contains a non-object")
        stage_id = require_string(row, "id", "company_second_depth.stage_order")
        if row.get("ordinal") != ordinal:
            fail(f"stage {stage_id} has non-monotonic ordinal")
        minimum_evidence = require_list(row, "minimum_evidence", stage_id)
        unknown_fields = set(minimum_evidence) - EVIDENCE_FIELDS
        if unknown_fields:
            fail(f"stage {stage_id} references unknown evidence fields: {sorted(unknown_fields)}")
        require_string(row, "public_claim_ceiling", stage_id)
        stage_ids.append(stage_id)
        stage_contract[stage_id] = row
    if stage_ids != EXPECTED_STAGES:
        fail(f"second-depth stage order mismatch: {stage_ids}")
    stage_index = {stage_id: index for index, stage_id in enumerate(stage_ids)}

    defaults = registry.get("default_company_state")
    if not isinstance(defaults, dict):
        fail("company_second_depth.default_company_state must be an object")
    if defaults.get("stage") != "MAPPED_ONLY":
        fail("default second-depth stage must be MAPPED_ONLY")

    overrides = registry.get("company_overrides")
    if not isinstance(overrides, dict):
        fail("company_second_depth.company_overrides must be an object")
    unknown_overrides = set(overrides) - required_tracks
    if unknown_overrides:
        fail(f"second-depth overrides reference unknown companies: {sorted(unknown_overrides)}")

    priority_wave = string_set(
        require_list(registry, "priority_wave", "company_second_depth"),
        "company_second_depth.priority_wave",
    )
    if not priority_wave <= required_tracks:
        fail(f"second-depth priority wave references unknown companies: {sorted(priority_wave - required_tracks)}")

    resolved: dict[str, dict[str, Any]] = {}
    for company_id in sorted(required_tracks):
        override = overrides.get(company_id, {})
        if not isinstance(override, dict):
            fail(f"{company_id}: override must be an object")
        state = resolved_state(defaults, override)
        validate_state(company_id, state, stage_index, stage_contract)
        resolved[company_id] = state

    invariants = require_list(registry, "promotion_invariants", "company_second_depth")
    if len(invariants) < 8 or not all(isinstance(item, str) and item for item in invariants):
        fail("company_second_depth.promotion_invariants is incomplete")

    consumer = registry.get("consumer_contract")
    if not isinstance(consumer, dict):
        fail("company_second_depth.consumer_contract must be an object")
    for field in ("merge_rule", "missing_override_behavior", "public_projection", "promotion_writer"):
        require_string(consumer, field, "company_second_depth.consumer_contract")

    counts: dict[str, int] = {stage: 0 for stage in EXPECTED_STAGES}
    for state in resolved.values():
        counts[state["stage"]] += 1

    return {
        "status": "PASS",
        "company_tracks": len(required_tracks),
        "stage_count": len(EXPECTED_STAGES),
        "priority_wave": len(priority_wave),
        "company_overrides": len(overrides),
        "stage_counts": counts,
        "claim_promotion_requires_receipt": True,
        "zero_implicit_completion": True,
    }


def main() -> int:
    try:
        result = validate_second_depth()
    except SecondDepthValidationError as exc:
        print(f"COMPANY SECOND DEPTH: FAIL: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
