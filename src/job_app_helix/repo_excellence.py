from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

PRINCIPAL_STATES = (
    "DISCOVERED",
    "IDENTITY_RESOLVED",
    "PROBLEM_VERIFIED",
    "TARGET_CONTRACTED",
    "SEEDED",
    "VERTICAL_SLICE",
    "IMPLEMENTED",
    "TESTED",
    "ADVERSARIAL_VERIFIED",
    "OPERABLE",
    "PROOF_REPRODUCED",
    "PROMOTED",
    "CANONICAL",
    "EVOLVING",
)

SIDE_EXIT_STATES = {
    "BLOCKED",
    "EXPERIMENT",
    "REFERENCE",
    "SUPERSEDED",
    "RETIREMENT_READY",
    "QUARANTINE",
}

CANONICAL_ROLES = {
    "CANONICAL_SYSTEM",
    "SPECIALIST_COMPONENT",
    "EXPERIMENT",
    "DONOR",
    "REFERENCE",
    "SUPERSEDED",
    "BACKUP",
    "RETIREMENT_READY",
}

PROOF_GRADES = {"A", "B", "C", "D", "Q"}

REQUIRED_EXCELLENT_GATES = (
    "problem_verified",
    "unique_value_known",
    "canonical_identity_known",
    "central_mechanism_implemented",
    "deterministic_tests_pass",
    "adversarial_tests_pass",
    "runtime_behavior_observed",
    "security_authority_bounded",
    "proof_receipt_bound_to_sha",
    "reusable_capabilities_extracted",
    "projections_truth_consistent",
    "evolution_cursor_defined",
)

CANONICAL_RECEIPT_REQUIRED_FLAGS = (
    "canonical_position_resolved",
    "lineage_conflict_absent",
    "duplicate_repository_rejected",
    "proof_sha_bound",
    "projection_truth_closed",
    "authority_bounded",
    "evolution_cursor_defined",
    "company_claim_separate",
)

TRANSITION_GATE_REQUIREMENTS = {
    ("PROOF_REPRODUCED", "PROMOTED"): (
        "security_authority_bounded",
        "projections_truth_consistent",
    ),
    ("PROMOTED", "CANONICAL"): REQUIRED_EXCELLENT_GATES,
}

PROMOTED_STATES = {"PROMOTED", "CANONICAL", "EVOLVING"}
GIT_COMMIT_PATTERN = re.compile(r"[0-9a-fA-F]{40}\Z")
PROOF_DIGEST_PATTERN = re.compile(r"(?:[0-9a-fA-F]{40}|[0-9a-fA-F]{64})\Z")
PLACEHOLDER_PROOF_VALUES = {
    "tbd",
    "todo",
    "placeholder",
    "resolved",
    "hyper_validated_sha256",
    "hyper_validated_identity",
}


class ExcellenceContractError(ValueError):
    """Raised when a repository excellence record violates the canonical contract."""


@dataclass(frozen=True)
class ScoreVector:
    target_architecture: float
    current_proof: str
    company_fit: float | None
    canonical_confidence: float


def _require_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ExcellenceContractError(f"{label} must be non-empty text")
    return value.strip()


def _require_bound_proof_receipt(
    receipt: Mapping[str, Any],
    identity: Mapping[str, Any],
    state: str,
) -> None:
    source_sha = _require_text(receipt.get("source_sha"), "proof_receipt.source_sha")
    receipt_identity = _require_text(receipt.get("identity"), "proof_receipt.identity")
    canonical_merge_sha = _require_text(
        receipt.get("canonical_merge_sha"),
        "proof_receipt.canonical_merge_sha",
    )
    canonical_head = _require_text(identity.get("canonical_head"), "identity.canonical_head")

    if source_sha.lower() in PLACEHOLDER_PROOF_VALUES:
        raise ExcellenceContractError(f"{state} rejects placeholder proof_receipt.source_sha")
    if receipt_identity.lower() in PLACEHOLDER_PROOF_VALUES:
        raise ExcellenceContractError(f"{state} rejects placeholder proof_receipt.identity")
    if canonical_merge_sha.lower() in PLACEHOLDER_PROOF_VALUES:
        raise ExcellenceContractError(
            f"{state} rejects placeholder proof_receipt.canonical_merge_sha"
        )
    if not PROOF_DIGEST_PATTERN.fullmatch(source_sha):
        raise ExcellenceContractError(
            f"{state} requires proof_receipt.source_sha to be a 40- or 64-hex digest"
        )
    if not GIT_COMMIT_PATTERN.fullmatch(canonical_head):
        raise ExcellenceContractError(
            f"{state} requires identity.canonical_head to be an exact 40-hex Git commit"
        )
    if not GIT_COMMIT_PATTERN.fullmatch(canonical_merge_sha):
        raise ExcellenceContractError(
            f"{state} requires proof_receipt.canonical_merge_sha to be an exact 40-hex Git commit"
        )
    if canonical_merge_sha.lower() != canonical_head.lower():
        raise ExcellenceContractError(
            f"{state} requires proof_receipt.canonical_merge_sha to match identity.canonical_head"
        )


def _require_canonical_position_receipt(
    receipt: Mapping[str, Any],
    identity: Mapping[str, Any],
    role: str,
    capability_id: str,
    blockers: Any,
    company_evidence: Any,
) -> None:
    if receipt.get("schema") != "glaciereq.repo-canonical-position-receipt.v1":
        raise ExcellenceContractError("CANONICAL requires canonical position receipt schema v1")
    if receipt.get("status") != "PASS":
        raise ExcellenceContractError("CANONICAL requires canonical position receipt status PASS")
    if receipt.get("transition") != "PROMOTED -> CANONICAL":
        raise ExcellenceContractError("CANONICAL transition receipt drift")

    _require_text(receipt.get("path"), "canonical_position_receipt.path")
    blob_sha = _require_text(receipt.get("blob_sha"), "canonical_position_receipt.blob_sha")
    if not GIT_COMMIT_PATTERN.fullmatch(blob_sha):
        raise ExcellenceContractError(
            "canonical position receipt must be content-addressed by Git blob SHA"
        )

    expected = {
        "repository": identity.get("repository"),
        "canonical_head": identity.get("canonical_head"),
        "canonical_role": role,
        "capability_id": capability_id,
        "lineage_action": identity.get("lineage_action"),
    }
    for field, value in expected.items():
        if receipt.get(field) != value:
            raise ExcellenceContractError(f"canonical position receipt {field} drift")

    source_blob_sha = _require_text(
        receipt.get("source_blob_sha"),
        "canonical_position_receipt.source_blob_sha",
    )
    if not GIT_COMMIT_PATTERN.fullmatch(source_blob_sha):
        raise ExcellenceContractError("canonical lineage source must be content-addressed")

    for flag in CANONICAL_RECEIPT_REQUIRED_FLAGS:
        if receipt.get(flag) is not True:
            raise ExcellenceContractError(f"CANONICAL requires {flag}=true")

    canonicalization_blockers = receipt.get("canonicalization_blockers")
    if canonicalization_blockers != []:
        raise ExcellenceContractError("CANONICAL rejects unresolved canonicalization blockers")

    retained = receipt.get("retained_noncanonicalization_blockers")
    if not isinstance(retained, list) or not all(isinstance(item, str) for item in retained):
        raise ExcellenceContractError(
            "canonical_position_receipt.retained_noncanonicalization_blockers must be a string list"
        )
    blocker_ids = (
        {
            item.get("id")
            for item in blockers
            if isinstance(item, Mapping) and isinstance(item.get("id"), str)
        }
        if isinstance(blockers, list)
        else set()
    )
    if not blocker_ids <= set(retained):
        raise ExcellenceContractError(
            "CANONICAL record blocker is not classified as non-canonicalization-blocking"
        )

    if isinstance(company_evidence, Mapping):
        if receipt.get("company_stage_unchanged") != company_evidence.get("stage"):
            raise ExcellenceContractError(
                "repository canonicalization cannot advance company stage"
            )
        if receipt.get("company_claim_ceiling_unchanged") != company_evidence.get(
            "claim_ceiling"
        ):
            raise ExcellenceContractError(
                "repository canonicalization cannot advance company claim ceiling"
            )


def validate_score_vector(raw: Mapping[str, Any]) -> ScoreVector:
    target = raw.get("target_architecture")
    proof = raw.get("current_proof")
    company = raw.get("company_fit")
    confidence = raw.get("canonical_confidence")

    if not isinstance(target, (int, float)) or not 0 <= float(target) <= 10:
        raise ExcellenceContractError("target_architecture must be 0..10")
    if proof not in PROOF_GRADES:
        raise ExcellenceContractError(f"current_proof must be one of {sorted(PROOF_GRADES)}")
    if company is not None and (
        not isinstance(company, (int, float)) or not 0 <= float(company) <= 10
    ):
        raise ExcellenceContractError("company_fit must be null or 0..10")
    if not isinstance(confidence, (int, float)) or not 0 <= float(confidence) <= 1:
        raise ExcellenceContractError("canonical_confidence must be 0..1")

    return ScoreVector(
        float(target),
        str(proof),
        None if company is None else float(company),
        float(confidence),
    )


def transition_gate_requirements(current: str, target: str) -> tuple[str, ...]:
    return TRANSITION_GATE_REQUIREMENTS.get((current, target), ())


def transition_gates_satisfied(
    current: str,
    target: str,
    gates: Mapping[str, Any] | None,
) -> bool:
    requirements = transition_gate_requirements(current, target)
    if not requirements:
        return True
    if not isinstance(gates, Mapping):
        return False
    return all(gates.get(name) is True for name in requirements)


def allowed_transition(
    current: str,
    target: str,
    gates: Mapping[str, Any] | None = None,
) -> bool:
    if target in SIDE_EXIT_STATES:
        return True
    if current in SIDE_EXIT_STATES:
        return target == "DISCOVERED"
    if current not in PRINCIPAL_STATES or target not in PRINCIPAL_STATES:
        return False
    topology_allowed = PRINCIPAL_STATES.index(target) == PRINCIPAL_STATES.index(current) + 1
    if not topology_allowed:
        return False
    return transition_gates_satisfied(current, target, gates)


def excellent(gates: Mapping[str, Any]) -> bool:
    return all(gates.get(name) is True for name in REQUIRED_EXCELLENT_GATES)


def validate_repo_excellence_record(payload: Mapping[str, Any]) -> dict[str, Any]:
    if payload.get("schema") != "glaciereq.repo-excellence.record.v1":
        raise ExcellenceContractError("unsupported schema")

    identity = payload.get("identity")
    if not isinstance(identity, Mapping):
        raise ExcellenceContractError("identity must be an object")
    identity_fields = (
        "repository",
        "repository_id",
        "canonical_head",
        "default_branch",
        "lineage_action",
    )
    for field in identity_fields:
        _require_text(identity.get(field), f"identity.{field}")

    state = _require_text(payload.get("state"), "state")
    if state not in PRINCIPAL_STATES and state not in SIDE_EXIT_STATES:
        raise ExcellenceContractError(f"unsupported state {state}")

    role = _require_text(payload.get("canonical_role"), "canonical_role")
    if role not in CANONICAL_ROLES:
        raise ExcellenceContractError(f"unsupported canonical_role {role}")

    scores = payload.get("scores")
    if not isinstance(scores, Mapping):
        raise ExcellenceContractError("scores must be an object")
    validate_score_vector(scores)

    gates = payload.get("gates")
    if not isinstance(gates, Mapping):
        raise ExcellenceContractError("gates must be an object")
    unknown = set(gates) - set(REQUIRED_EXCELLENT_GATES)
    if unknown:
        raise ExcellenceContractError(f"unknown excellence gates: {sorted(unknown)}")
    for name, value in gates.items():
        if not isinstance(value, bool):
            raise ExcellenceContractError(f"gate {name} must be boolean")

    evolution = payload.get("evolution")
    if not isinstance(evolution, Mapping):
        raise ExcellenceContractError("evolution must be an object")
    next_gate = _require_text(evolution.get("next_gate"), "evolution.next_gate")

    if state in PROMOTED_STATES:
        missing_gates = [name for name in REQUIRED_EXCELLENT_GATES if gates.get(name) is not True]
        if missing_gates:
            raise ExcellenceContractError(
                f"{state} requires every excellence gate; missing: {', '.join(missing_gates)}"
            )
        if not transition_gates_satisfied("PROOF_REPRODUCED", "PROMOTED", gates):
            required = ", ".join(
                transition_gate_requirements("PROOF_REPRODUCED", "PROMOTED")
            )
            raise ExcellenceContractError(
                f"{state} requires earned PROOF_REPRODUCED->PROMOTED gates: {required}"
            )

    if state in {"PROOF_REPRODUCED", *PROMOTED_STATES}:
        receipt = payload.get("proof_receipt")
        if not isinstance(receipt, Mapping):
            raise ExcellenceContractError(f"{state} requires proof_receipt")
        _require_text(receipt.get("source_sha"), "proof_receipt.source_sha")
        _require_text(receipt.get("identity"), "proof_receipt.identity")
        if state in PROMOTED_STATES:
            _require_bound_proof_receipt(receipt, identity, state)

    if state in {"CANONICAL", "EVOLVING"}:
        if identity.get("canonical_head") == "UNRESOLVED":
            raise ExcellenceContractError(f"{state} requires a resolved canonical head")
        capability_id = _require_text(payload.get("capability_id"), "capability_id")
        canonical_receipt = payload.get("canonical_position_receipt")
        if not isinstance(canonical_receipt, Mapping):
            raise ExcellenceContractError(f"{state} requires canonical_position_receipt")
        _require_canonical_position_receipt(
            canonical_receipt,
            identity,
            role,
            capability_id,
            payload.get("blockers"),
            payload.get("company_evidence"),
        )
        projection_refs = payload.get("projection_refs")
        if not isinstance(projection_refs, list) or not projection_refs:
            raise ExcellenceContractError(f"{state} requires projection_refs")
        for index, projection_ref in enumerate(projection_refs):
            _require_text(projection_ref, f"projection_refs[{index}]")
        if state == "CANONICAL" and next_gate != "EVOLVING":
            raise ExcellenceContractError("CANONICAL requires evolution.next_gate EVOLVING")

    return dict(payload)
