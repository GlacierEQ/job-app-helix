from __future__ import annotations

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

TRANSITION_GATE_REQUIREMENTS = {
    ("PROOF_REPRODUCED", "PROMOTED"): (
        "security_authority_bounded",
        "projections_truth_consistent",
    ),
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
    _require_text(evolution.get("next_gate"), "evolution.next_gate")

    if state in {"PROOF_REPRODUCED", "PROMOTED", "CANONICAL", "EVOLVING"}:
        receipt = payload.get("proof_receipt")
        if not isinstance(receipt, Mapping):
            raise ExcellenceContractError(f"{state} requires proof_receipt")
        _require_text(receipt.get("source_sha"), "proof_receipt.source_sha")
        _require_text(receipt.get("identity"), "proof_receipt.identity")

    if state in {"PROMOTED", "CANONICAL", "EVOLVING"} and not transition_gates_satisfied(
        "PROOF_REPRODUCED", "PROMOTED", gates
    ):
        required = ", ".join(
            transition_gate_requirements("PROOF_REPRODUCED", "PROMOTED")
        )
        raise ExcellenceContractError(
            f"{state} requires earned PROOF_REPRODUCED->PROMOTED gates: {required}"
        )

    if state in {"CANONICAL", "EVOLVING"} and identity.get("canonical_head") == "UNRESOLVED":
        raise ExcellenceContractError(f"{state} requires a resolved canonical head")

    return dict(payload)
