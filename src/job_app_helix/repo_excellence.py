from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Active progression is deliberately capability-first. Historical contraction labels
# remain readable through HISTORICAL_STATE_UPGRADES but cannot drive lifecycle action.
PRINCIPAL_STATES = (
    "DISCOVERED",
    "IDENTITY_RESOLVED",
    "PURPOSE_RECONSTRUCTED",
    "CAPABILITY_MAPPED",
    "RESTORATION_COMPOSED",
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
    "DONOR",
    "RECOVERY_REQUIRED",
    "COMPOSITION_REQUIRED",
}

HISTORICAL_STATE_UPGRADES = {
    "PROBLEM_VERIFIED": "PURPOSE_RECONSTRUCTED",
    "TARGET_CONTRACTED": "PURPOSE_RECONSTRUCTED",
    "SEEDED": "CAPABILITY_MAPPED",
    "VERTICAL_SLICE": "RESTORATION_COMPOSED",
    "SUPERSEDED": "RECOVERY_REQUIRED",
    "RETIREMENT_READY": "RECOVERY_REQUIRED",
    "QUARANTINE": "RECOVERY_REQUIRED",
}

CANONICAL_ROLES = {
    "INDEPENDENT_SYSTEM",
    "CANONICAL_SYSTEM",
    "SPECIALIST_COMPONENT",
    "EXPERIMENT",
    "DONOR",
    "REFERENCE",
    "BACKUP",
}

HISTORICAL_ROLE_UPGRADES = {
    "SUPERSEDED": "DONOR",
    "RETIREMENT_READY": "DONOR",
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

# These flags bind an exact source/integration anchor. They do not confer lifecycle
# authority over sibling repositories. In particular, duplicate_repository_rejected
# is intentionally NOT an active requirement.
CANONICAL_RECEIPT_REQUIRED_FLAGS = (
    "canonical_position_resolved",
    "lineage_conflict_absent",
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
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


class ExcellenceContractError(ValueError):
    """Raised when a repository excellence record violates the upward contract."""


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


def _resolve_repository_path(root: Path, relative: str, label: str) -> Path:
    path = (root / relative).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise ExcellenceContractError(f"{label} escapes repository root") from exc
    if not path.is_file():
        raise ExcellenceContractError(f"{label} does not exist: {relative}")
    return path


def _load_json(path: Path, label: str) -> Mapping[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ExcellenceContractError(f"{label} is not valid JSON") from exc
    if not isinstance(value, Mapping):
        raise ExcellenceContractError(f"{label} must contain a JSON object")
    return value


def _git_blob_sha(path: Path) -> str:
    payload = path.read_bytes()
    framed = b"blob " + str(len(payload)).encode() + b"\0" + payload
    return hashlib.sha1(framed, usedforsecurity=False).hexdigest()


def _upgrade_state(state: str) -> tuple[str, str | None]:
    upgraded = HISTORICAL_STATE_UPGRADES.get(state)
    if upgraded is None:
        return state, None
    return upgraded, state


def _upgrade_role(role: str) -> tuple[str, str | None]:
    upgraded = HISTORICAL_ROLE_UPGRADES.get(role)
    if upgraded is None:
        return role, None
    return upgraded, role


def _require_bound_proof_receipt(
    receipt: Mapping[str, Any],
    identity: Mapping[str, Any],
    state: str,
) -> None:
    source_sha = _require_text(receipt.get("source_sha"), "proof_receipt.source_sha")
    receipt_identity = _require_text(receipt.get("identity"), "proof_receipt.identity")
    canonical_merge_sha = _require_text(
        receipt.get("canonical_merge_sha"), "proof_receipt.canonical_merge_sha"
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
    pointer: Mapping[str, Any],
    identity: Mapping[str, Any],
    role: str,
    capability_id: str,
    blockers: Any,
    company_evidence: Mapping[str, Any],
    repository_root: Path,
) -> Mapping[str, Any]:
    """Validate an exact source/integration anchor without minting retirement authority."""

    if pointer.get("schema") != "glaciereq.repo-canonical-position-receipt.v1":
        raise ExcellenceContractError("CANONICAL requires canonical position receipt schema v1")
    if pointer.get("status") != "PASS":
        raise ExcellenceContractError("CANONICAL requires canonical position receipt status PASS")
    if pointer.get("transition") != "PROMOTED -> CANONICAL":
        raise ExcellenceContractError("CANONICAL transition receipt drift")

    relative = _require_text(pointer.get("path"), "canonical_position_receipt.path")
    receipt_path = _resolve_repository_path(repository_root, relative, "canonical_position_receipt.path")
    blob_sha = _require_text(pointer.get("blob_sha"), "canonical_position_receipt.blob_sha")
    if not GIT_COMMIT_PATTERN.fullmatch(blob_sha):
        raise ExcellenceContractError(
            "canonical position receipt must be content-addressed by Git blob SHA"
        )
    if _git_blob_sha(receipt_path) != blob_sha:
        raise ExcellenceContractError(
            "canonical position receipt Git blob SHA does not match repository bytes"
        )

    receipt = _load_json(receipt_path, "canonical position receipt")
    for field in ("schema", "status", "transition"):
        if receipt.get(field) != pointer.get(field):
            raise ExcellenceContractError(f"canonical position receipt {field} drift")

    repository = receipt.get("repository")
    if not isinstance(repository, Mapping):
        raise ExcellenceContractError("canonical position receipt repository must be an object")
    expected_repository = {
        "full_name": identity.get("repository"),
        "repository_id": identity.get("repository_id"),
        "canonical_head": identity.get("canonical_head"),
        "default_branch": identity.get("default_branch"),
        "canonical_role": role,
        "capability_id": capability_id,
    }
    for field, value in expected_repository.items():
        if repository.get(field) != value:
            raise ExcellenceContractError(f"canonical position receipt repository.{field} drift")

    lineage = receipt.get("lineage")
    if not isinstance(lineage, Mapping):
        raise ExcellenceContractError("canonical position receipt lineage must be an object")
    if lineage.get("action") != identity.get("lineage_action"):
        raise ExcellenceContractError("canonical position receipt lineage action drift")
    if lineage.get("action") != "EXTEND_CANONICAL":
        raise ExcellenceContractError("CANONICAL anchor requires EXTEND_CANONICAL lineage action")
    if lineage.get("source_commit") != identity.get("canonical_head"):
        raise ExcellenceContractError("canonical position receipt lineage source commit drift")
    source_blob_sha = _require_text(
        lineage.get("source_blob_sha"), "canonical position receipt lineage.source_blob_sha"
    )
    if not GIT_COMMIT_PATTERN.fullmatch(source_blob_sha):
        raise ExcellenceContractError("canonical lineage source must be content-addressed")
    if source_blob_sha != pointer.get("source_blob_sha"):
        raise ExcellenceContractError("canonical lineage source blob pointer drift")

    # Legacy receipts may still record NEW_REPO or duplicate-repository decisions. They
    # remain historical evidence only and are intentionally not prerequisites here.
    decision = receipt.get("decision")
    if not isinstance(decision, Mapping):
        raise ExcellenceContractError("canonical position receipt decision must be an object")
    for flag in CANONICAL_RECEIPT_REQUIRED_FLAGS:
        if decision.get(flag) is not True or pointer.get(flag) is not True:
            raise ExcellenceContractError(f"CANONICAL requires {flag}=true")
    if decision.get("canonicalization_blockers") != []:
        raise ExcellenceContractError("CANONICAL source anchor has unresolved identity blockers")
    if pointer.get("canonicalization_blockers") != []:
        raise ExcellenceContractError("CANONICAL pointer carries unresolved identity blockers")

    retained = decision.get("retained_noncanonicalization_blockers")
    pointer_retained = pointer.get("retained_noncanonicalization_blockers")
    if not isinstance(retained, list) or not all(isinstance(item, str) for item in retained):
        raise ExcellenceContractError(
            "canonical receipt retained_noncanonicalization_blockers must be a string list"
        )
    if retained != pointer_retained:
        raise ExcellenceContractError("canonical blocker classification pointer drift")

    if blockers is None:
        blockers = []
    if not isinstance(blockers, list):
        raise ExcellenceContractError("blockers must be a list")
    blocker_ids: list[str] = []
    for index, item in enumerate(blockers):
        if not isinstance(item, Mapping):
            raise ExcellenceContractError(f"blockers[{index}] must be an object")
        blocker_ids.append(_require_text(item.get("id"), f"blockers[{index}].id"))
    if blocker_ids != retained:
        raise ExcellenceContractError(
            "CANONICAL record blockers do not match retained non-canonicalization blockers"
        )

    claim_boundary = receipt.get("claim_boundary")
    if not isinstance(claim_boundary, Mapping):
        raise ExcellenceContractError("canonical position receipt claim_boundary must be an object")
    stage = _require_text(company_evidence.get("stage"), "company_evidence.stage")
    ceiling = _require_text(company_evidence.get("claim_ceiling"), "company_evidence.claim_ceiling")
    if claim_boundary.get("company_stage_unchanged") != stage:
        raise ExcellenceContractError("repository source anchoring cannot advance company stage")
    if pointer.get("company_stage_unchanged") != stage:
        raise ExcellenceContractError("canonical company-stage pointer drift")
    if claim_boundary.get("company_claim_ceiling_unchanged") != ceiling:
        raise ExcellenceContractError("repository source anchoring cannot advance company claim ceiling")
    if pointer.get("company_claim_ceiling_unchanged") != ceiling:
        raise ExcellenceContractError("canonical company-claim-ceiling pointer drift")
    if claim_boundary.get("github_adoption_claimed") is not False:
        raise ExcellenceContractError("repository source anchoring cannot create adoption claim")
    if claim_boundary.get("github_capability_production_deployment_claimed") is not False:
        raise ExcellenceContractError("repository source anchoring cannot create deployment claim")

    result = receipt.get("result")
    if not isinstance(result, Mapping):
        raise ExcellenceContractError("canonical position receipt result must be an object")
    if result.get("repository_state") != "CANONICAL":
        raise ExcellenceContractError("canonical position receipt result state drift")
    if result.get("next_gate") != "EVOLVING":
        raise ExcellenceContractError("canonical position receipt next gate drift")

    return receipt


def _require_projection_binding(
    projection_ref: str,
    payload: Mapping[str, Any],
    capability_id: str,
    company_evidence: Mapping[str, Any],
    repository_root: Path,
) -> None:
    projection_path = _resolve_repository_path(repository_root, projection_ref, "projection_ref")
    projection = _load_json(projection_path, f"projection {projection_ref}")
    implementation = projection.get("implementation")
    if not isinstance(implementation, Mapping):
        raise ExcellenceContractError(f"{projection_ref}: implementation must be an object")

    identity = payload["identity"]
    expected_implementation = {
        "repository": identity.get("repository"),
        "canonical_head": identity.get("canonical_head"),
        "capability": capability_id,
        "state": payload.get("state"),
    }
    for field, value in expected_implementation.items():
        if implementation.get(field) != value:
            raise ExcellenceContractError(f"{projection_ref}: implementation {field} drift")
    if projection.get("stage") != company_evidence.get("stage"):
        raise ExcellenceContractError(f"{projection_ref}: company stage drift")
    if projection.get("claim_ceiling") != company_evidence.get("claim_ceiling"):
        raise ExcellenceContractError(f"{projection_ref}: company claim ceiling drift")


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
    # Historical contraction states cannot be entered by active execution.
    if target in HISTORICAL_STATE_UPGRADES:
        return False
    current, historical_current = _upgrade_state(current)
    if historical_current is not None:
        # A historical state resumes as an upward recovery state, never a retirement state.
        return target in {"DISCOVERED", "RECOVERY_REQUIRED", "PURPOSE_RECONSTRUCTED"}
    if target in SIDE_EXIT_STATES:
        return True
    if current in SIDE_EXIT_STATES:
        return target in {"DISCOVERED", "PURPOSE_RECONSTRUCTED"}
    if current not in PRINCIPAL_STATES or target not in PRINCIPAL_STATES:
        return False
    topology_allowed = PRINCIPAL_STATES.index(target) == PRINCIPAL_STATES.index(current) + 1
    if not topology_allowed:
        return False
    return transition_gates_satisfied(current, target, gates)


def excellent(gates: Mapping[str, Any]) -> bool:
    return all(gates.get(name) is True for name in REQUIRED_EXCELLENT_GATES)


def validate_repo_excellence_record(
    payload: Mapping[str, Any],
    repository_root: Path | str | None = None,
) -> dict[str, Any]:
    if payload.get("schema") not in {
        "glaciereq.repo-excellence.record.v1",
        "glaciereq.repo-excellence.record.v2",
    }:
        raise ExcellenceContractError("unsupported schema")

    result_payload = dict(payload)

    identity = payload.get("identity")
    if not isinstance(identity, Mapping):
        raise ExcellenceContractError("identity must be an object")
    for field in (
        "repository",
        "repository_id",
        "canonical_head",
        "default_branch",
        "lineage_action",
    ):
        _require_text(identity.get(field), f"identity.{field}")

    raw_state = _require_text(payload.get("state"), "state")
    state, historical_state = _upgrade_state(raw_state)
    if state not in PRINCIPAL_STATES and state not in SIDE_EXIT_STATES:
        raise ExcellenceContractError(f"unsupported state {raw_state}")
    if historical_state is not None:
        result_payload["historical_state"] = historical_state
        result_payload["state"] = state
        result_payload["recovery_required"] = True

    raw_role = _require_text(payload.get("canonical_role"), "canonical_role")
    role, historical_role = _upgrade_role(raw_role)
    if role not in CANONICAL_ROLES:
        raise ExcellenceContractError(f"unsupported canonical_role {raw_role}")
    if historical_role is not None:
        result_payload["historical_canonical_role"] = historical_role
        result_payload["canonical_role"] = role
        result_payload["recovery_required"] = True

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
            raise ExcellenceContractError(f"{state} requires a resolved source anchor")
        capability_id = _require_text(payload.get("capability_id"), "capability_id")
        company_evidence = payload.get("company_evidence")
        if not isinstance(company_evidence, Mapping):
            raise ExcellenceContractError(f"{state} requires company_evidence")
        _require_text(company_evidence.get("stage"), "company_evidence.stage")
        _require_text(company_evidence.get("claim_ceiling"), "company_evidence.claim_ceiling")

        canonical_pointer = payload.get("canonical_position_receipt")
        if not isinstance(canonical_pointer, Mapping):
            raise ExcellenceContractError(f"{state} requires canonical_position_receipt")
        root = Path(repository_root) if repository_root is not None else REPOSITORY_ROOT
        _require_canonical_position_receipt(
            canonical_pointer,
            identity,
            role,
            capability_id,
            payload.get("blockers"),
            company_evidence,
            root,
        )

        projection_refs = payload.get("projection_refs")
        if not isinstance(projection_refs, list) or not projection_refs:
            raise ExcellenceContractError(f"{state} requires projection_refs")
        projection_payload = dict(payload)
        projection_payload["state"] = state
        for index, projection_ref in enumerate(projection_refs):
            reference = _require_text(projection_ref, f"projection_refs[{index}]")
            _require_projection_binding(
                reference,
                projection_payload,
                capability_id,
                company_evidence,
                root,
            )
        if state == "CANONICAL" and next_gate != "EVOLVING":
            raise ExcellenceContractError("CANONICAL requires evolution.next_gate EVOLVING")

    # Explicit anti-contraction metadata is synthesized on every validated record.
    result_payload["direction"] = "MAXIMUM_COHERENT_ADVANCE"
    result_payload["retirement_authorized"] = False
    result_payload["retirement_requires_operator_authorization"] = True
    result_payload["similarity_establishes_redundancy"] = False
    return result_payload
