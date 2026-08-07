#!/usr/bin/env python3
"""Validate the governed company second-depth progression contract."""

from __future__ import annotations

import json
import re
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
EXPECTED_STAGE_REQUIREMENTS = {
    "MAPPED_ONLY": (),
    "ROLE_VERIFIED": ("role_evidence",),
    "PROBLEM_BOUNDED": ("role_evidence", "problem_evidence"),
    "CODE_INSPECTED": (
        "role_evidence",
        "problem_evidence",
        "inspected_repositories",
    ),
    "REMEDY_BOUNDED": (
        "role_evidence",
        "problem_evidence",
        "inspected_repositories",
        "gap_queue",
    ),
    "IMPLEMENTED": (
        "role_evidence",
        "problem_evidence",
        "inspected_repositories",
        "gap_queue",
        "implementation_receipts",
    ),
    "PROOF_REPRODUCED": (
        "role_evidence",
        "problem_evidence",
        "inspected_repositories",
        "gap_queue",
        "implementation_receipts",
        "proof_artifacts",
    ),
    "CLAIM_PROMOTED": (
        "role_evidence",
        "problem_evidence",
        "inspected_repositories",
        "gap_queue",
        "implementation_receipts",
        "proof_artifacts",
        "claim_receipts",
    ),
}
EXPECTED_STAGE_CEILINGS = {
    "MAPPED_ONLY": "company_alignment_only",
    "ROLE_VERIFIED": "verified_role_alignment",
    "PROBLEM_BOUNDED": "externally_bounded_problem_alignment",
    "CODE_INSPECTED": "inspected_implementation_alignment",
    "REMEDY_BOUNDED": "bounded_remedy_design",
    "IMPLEMENTED": "implemented_candidate_capability",
    "PROOF_REPRODUCED": "reproducible_company_specific_proof",
    "CLAIM_PROMOTED": "proof_bound_company_specific",
}
EVIDENCE_KIND_BY_FIELD = {
    "role_evidence": "role",
    "problem_evidence": "problem",
    "inspected_repositories": "repository_inspection",
    "gap_queue": "bounded_gap",
    "implementation_receipts": "implementation_receipt",
    "proof_artifacts": "proof_artifact",
    "claim_receipts": "claim_receipt",
}
EVIDENCE_FIELDS = set(EVIDENCE_KIND_BY_FIELD)
EVIDENCE_REQUIRED_FIELDS = {
    "id",
    "kind",
    "source_identity",
    "source_ref",
    "visibility",
    "verification_state",
}
MINIMUM_VERIFICATION_STATE = {
    field: "REPRODUCED" if field == "proof_artifacts" else "VERIFIED"
    for field in EVIDENCE_FIELDS
}
VERIFICATION_RANK = {"VERIFIED": 1, "REPRODUCED": 2}
SOURCE_IDENTITY_PREFIXES = ("https://", "GlacierEQ/")
EVIDENCE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
COMMIT_REF_PATTERN = re.compile(r"^commit:[a-f0-9]{40}$")
SHA256_REF_PATTERN = re.compile(r"^sha256:[a-f0-9]{64}$")


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


def validate_evidence_contract(registry: dict[str, Any]) -> None:
    contract = registry.get("evidence_reference_contract")
    if not isinstance(contract, dict):
        fail("company_second_depth.evidence_reference_contract must be an object")

    required_fields = require_list(
        contract,
        "required_fields",
        "company_second_depth.evidence_reference_contract",
    )
    if set(required_fields) != EVIDENCE_REQUIRED_FIELDS:
        fail("evidence_reference_contract.required_fields drift from canonical schema")
    if contract.get("visibility") != "public":
        fail("evidence_reference_contract.visibility must be public")
    if contract.get("verification_states") != ["VERIFIED", "REPRODUCED"]:
        fail("evidence_reference_contract.verification_states drift")
    if contract.get("field_kinds") != EVIDENCE_KIND_BY_FIELD:
        fail("evidence_reference_contract.field_kinds drift")
    if contract.get("minimum_verification_state") != MINIMUM_VERIFICATION_STATE:
        fail("evidence_reference_contract.minimum_verification_state drift")
    if contract.get("source_identity_prefixes") != list(SOURCE_IDENTITY_PREFIXES):
        fail("evidence_reference_contract.source_identity_prefixes drift")
    expected_ref_formats = [
        "commit:<40-lowercase-hex>",
        "sha256:<64-lowercase-hex>",
    ]
    if contract.get("source_ref_formats") != expected_ref_formats:
        fail("evidence_reference_contract.source_ref_formats drift")
    require_string(
        contract,
        "public_safety_rule",
        "company_second_depth.evidence_reference_contract",
    )


def validate_evidence_reference(
    company_id: str,
    field: str,
    item: Any,
) -> None:
    if not isinstance(item, dict):
        fail(f"{company_id}.{field} evidence entries must be objects")
    if set(item) != EVIDENCE_REQUIRED_FIELDS:
        fail(
            f"{company_id}.{field} evidence keys must exactly equal "
            f"{sorted(EVIDENCE_REQUIRED_FIELDS)}"
        )

    for key in EVIDENCE_REQUIRED_FIELDS:
        value = item.get(key)
        if not isinstance(value, str) or not value:
            fail(f"{company_id}.{field}.{key} must be a non-empty string")

    evidence_id = item["id"]
    if not EVIDENCE_ID_PATTERN.fullmatch(evidence_id):
        fail(f"{company_id}.{field}.id has an invalid format")
    if item["kind"] != EVIDENCE_KIND_BY_FIELD[field]:
        fail(f"{company_id}.{field}.kind does not match the evidence field")

    source_identity = item["source_identity"]
    if not source_identity.startswith(SOURCE_IDENTITY_PREFIXES):
        fail(f"{company_id}.{field}.source_identity is not public-addressable")

    source_ref = item["source_ref"]
    if not (
        COMMIT_REF_PATTERN.fullmatch(source_ref)
        or SHA256_REF_PATTERN.fullmatch(source_ref)
    ):
        fail(f"{company_id}.{field}.source_ref is not an immutable supported ref")

    if item["visibility"] != "public":
        fail(f"{company_id}.{field}.visibility must be public")

    verification_state = item["verification_state"]
    if verification_state not in VERIFICATION_RANK:
        fail(f"{company_id}.{field}.verification_state is invalid")
    minimum = MINIMUM_VERIFICATION_STATE[field]
    if VERIFICATION_RANK[verification_state] < VERIFICATION_RANK[minimum]:
        fail(
            f"{company_id}.{field}.verification_state must be at least {minimum}"
        )


def validate_state(
    company_id: str,
    state: dict[str, Any],
    stage_index: dict[str, int],
) -> None:
    stage = state.get("stage")
    if stage not in stage_index:
        fail(f"{company_id}: invalid second-depth stage {stage!r}")

    for field in sorted(EVIDENCE_FIELDS):
        value = state.get(field)
        if not isinstance(value, list):
            fail(f"{company_id}.{field} must be an array")
        for item in value:
            validate_evidence_reference(company_id, field, item)

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

    required_evidence = EXPECTED_STAGE_REQUIREMENTS[stage]
    for field in required_evidence:
        if not state.get(field):
            fail(f"{company_id}: stage {stage} requires non-empty {field}")

    expected_ceiling = EXPECTED_STAGE_CEILINGS[stage]
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
    company_index = load_json(root / "manifests" / "company_dossiers.json")
    registry_path = require_string(
        company_index,
        "second_depth_registry",
        "company_dossiers",
    )
    registry = load_json(root / registry_path)

    if registry.get("schema") != "glaciereq.company-second-depth.v1":
        fail("unexpected second-depth schema")
    if registry.get("authority") != "GlacierEQ/job-app-helix":
        fail("unexpected second-depth authority")
    if registry.get("company_index") != "manifests/company_dossiers.json":
        fail("second-depth company index pointer drift")

    validate_evidence_contract(registry)

    required_tracks = string_set(
        require_list(company_index, "required_company_tracks", "company_dossiers"),
        "company_dossiers.required_company_tracks",
    )

    stage_rows = require_list(registry, "stage_order", "company_second_depth")
    if len(stage_rows) != len(EXPECTED_STAGES):
        fail("second-depth stage count mismatch")
    stage_ids: list[str] = []
    previous_requirements: set[str] = set()
    for ordinal, row in enumerate(stage_rows):
        if not isinstance(row, dict):
            fail("company_second_depth.stage_order contains a non-object")
        stage_id = require_string(row, "id", "company_second_depth.stage_order")
        if row.get("ordinal") != ordinal:
            fail(f"stage {stage_id} has non-monotonic ordinal")
        minimum_evidence = require_list(row, "minimum_evidence", stage_id)
        expected_requirements = list(EXPECTED_STAGE_REQUIREMENTS.get(stage_id, ()))
        if minimum_evidence != expected_requirements:
            fail(f"stage {stage_id} minimum_evidence contract drift")
        if not previous_requirements <= set(minimum_evidence):
            fail(f"stage {stage_id} drops an earlier evidence prerequisite")
        previous_requirements = set(minimum_evidence)

        claim_ceiling = require_string(row, "public_claim_ceiling", stage_id)
        if claim_ceiling != EXPECTED_STAGE_CEILINGS.get(stage_id):
            fail(f"stage {stage_id} public_claim_ceiling contract drift")
        stage_ids.append(stage_id)

    if stage_ids != EXPECTED_STAGES:
        fail(f"second-depth stage order mismatch: {stage_ids}")
    stage_index = {stage_id: ordinal for ordinal, stage_id in enumerate(stage_ids)}

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
        fail(
            "second-depth overrides reference unknown companies: "
            f"{sorted(unknown_overrides)}"
        )

    priority_wave = string_set(
        require_list(registry, "priority_wave", "company_second_depth"),
        "company_second_depth.priority_wave",
    )
    if not priority_wave <= required_tracks:
        unknown_priority = sorted(priority_wave - required_tracks)
        fail(
            "second-depth priority wave references unknown companies: "
            f"{unknown_priority}"
        )

    resolved: dict[str, dict[str, Any]] = {}
    for company_id in sorted(required_tracks):
        override = overrides.get(company_id, {})
        if not isinstance(override, dict):
            fail(f"{company_id}: override must be an object")
        state = resolved_state(defaults, override)
        validate_state(company_id, state, stage_index)
        resolved[company_id] = state

    invariants = require_list(registry, "promotion_invariants", "company_second_depth")
    if len(invariants) < 10 or not all(
        isinstance(item, str) and item for item in invariants
    ):
        fail("company_second_depth.promotion_invariants is incomplete")

    consumer = registry.get("consumer_contract")
    if not isinstance(consumer, dict):
        fail("company_second_depth.consumer_contract must be an object")
    consumer_fields = (
        "merge_rule",
        "missing_override_behavior",
        "public_projection",
        "promotion_writer",
    )
    for field in consumer_fields:
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
        "evidence_reference_schema_enforced": True,
        "stage_contract_locked": True,
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
