from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .repo_excellence import ExcellenceContractError, validate_repo_excellence_record

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
GIT_SHA = re.compile(r"[0-9a-f]{40}\Z")
SHA256 = re.compile(r"sha256:[0-9a-f]{64}\Z")


def _require_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ExcellenceContractError(f"{label} must be non-empty text")
    return value.strip()


def _resolve_file(root: Path, relative: str, label: str) -> Path:
    path = (root / relative).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise ExcellenceContractError(f"{label} escapes repository root") from exc
    if not path.is_file():
        raise ExcellenceContractError(f"{label} does not exist: {relative}")
    return path


def _git_blob_sha(path: Path) -> str:
    payload = path.read_bytes()
    framed = b"blob " + str(len(payload)).encode() + b"\0" + payload
    return hashlib.sha1(framed, usedforsecurity=False).hexdigest()


def _load_json(path: Path, label: str) -> Mapping[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ExcellenceContractError(f"{label} is not valid JSON") from exc
    if not isinstance(value, Mapping):
        raise ExcellenceContractError(f"{label} must contain a JSON object")
    return value


def validate_evolving_repo_excellence_record(
    payload: Mapping[str, Any],
    repository_root: Path | str | None = None,
) -> dict[str, Any]:
    """Validate the base excellence record plus the measured EVOLVING admission contract."""
    root = Path(repository_root) if repository_root is not None else REPOSITORY_ROOT
    validated = validate_repo_excellence_record(payload, root)
    if validated.get("state") != "EVOLVING":
        raise ExcellenceContractError("evolution validator requires state EVOLVING")

    identity = validated["identity"]
    anchor = _require_text(identity.get("canonical_head"), "identity.canonical_head")
    evolved = _require_text(identity.get("current_evolved_head"), "identity.current_evolved_head")
    if not GIT_SHA.fullmatch(anchor) or not GIT_SHA.fullmatch(evolved):
        raise ExcellenceContractError("EVOLVING requires exact 40-hex anchor and evolved heads")
    if anchor == evolved:
        raise ExcellenceContractError("EVOLVING requires a head distinct from its canonical anchor")

    pointer = validated.get("evolution_receipt")
    if not isinstance(pointer, Mapping):
        raise ExcellenceContractError("EVOLVING requires evolution_receipt")
    if pointer.get("schema") != "glaciereq.repo-evolution-receipt.v1":
        raise ExcellenceContractError("EVOLVING requires evolution receipt schema v1")
    if pointer.get("status") != "PASS":
        raise ExcellenceContractError("EVOLVING requires evolution receipt status PASS")
    if pointer.get("transition") != "CANONICAL -> EVOLVING":
        raise ExcellenceContractError("EVOLVING transition receipt drift")
    if pointer.get("canonical_anchor_head") != anchor:
        raise ExcellenceContractError("evolution receipt canonical anchor pointer drift")
    if pointer.get("evolved_head") != evolved:
        raise ExcellenceContractError("evolution receipt evolved-head pointer drift")
    if pointer.get("winner") != "candidate":
        raise ExcellenceContractError("EVOLVING requires a measured candidate winner")
    if pointer.get("tests_failed") != 0 or not isinstance(pointer.get("tests_passed"), int):
        raise ExcellenceContractError("EVOLVING pointer requires passing measured tests")
    if pointer.get("tests_passed", 0) <= 0:
        raise ExcellenceContractError("EVOLVING pointer requires at least one passing test")
    if not SHA256.fullmatch(str(pointer.get("public_proof_artifact_digest", ""))):
        raise ExcellenceContractError("EVOLVING pointer requires SHA-256 proof artifact digest")

    relative = _require_text(pointer.get("path"), "evolution_receipt.path")
    receipt_path = _resolve_file(root, relative, "evolution_receipt.path")
    blob_sha = _require_text(pointer.get("blob_sha"), "evolution_receipt.blob_sha")
    if not GIT_SHA.fullmatch(blob_sha):
        raise ExcellenceContractError("EVOLVING receipt must be content-addressed by Git blob SHA")
    if _git_blob_sha(receipt_path) != blob_sha:
        raise ExcellenceContractError("EVOLVING receipt Git blob SHA does not match repository bytes")

    receipt = _load_json(receipt_path, "evolution receipt")
    for field in ("schema", "status", "transition"):
        if receipt.get(field) != pointer.get(field):
            raise ExcellenceContractError(f"evolution receipt {field} pointer drift")

    repository = receipt.get("repository")
    if not isinstance(repository, Mapping):
        raise ExcellenceContractError("evolution receipt repository must be an object")
    expected_repository = {
        "full_name": identity.get("repository"),
        "repository_id": identity.get("repository_id"),
        "canonical_anchor_head": anchor,
        "evolved_head": evolved,
        "default_branch": identity.get("default_branch"),
        "canonical_role": validated.get("canonical_role"),
        "capability_id": validated.get("capability_id"),
        "lineage_action": identity.get("lineage_action"),
    }
    for field, value in expected_repository.items():
        if repository.get(field) != value:
            raise ExcellenceContractError(f"evolution receipt repository.{field} drift")

    experiment = receipt.get("experiment")
    if not isinstance(experiment, Mapping):
        raise ExcellenceContractError("evolution receipt experiment must be an object")
    if experiment.get("id") != pointer.get("experiment_id"):
        raise ExcellenceContractError("evolution experiment identity drift")
    baseline = experiment.get("baseline")
    candidate = experiment.get("candidate")
    comparison = experiment.get("comparison")
    if not all(isinstance(item, Mapping) for item in (baseline, candidate, comparison)):
        raise ExcellenceContractError("evolution experiment comparison contract incomplete")
    if baseline.get("head") != anchor or baseline.get("allowed") is not True:
        raise ExcellenceContractError("EVOLVING requires a reproduced weaker baseline")
    if candidate.get("merged_head") != evolved:
        raise ExcellenceContractError("evolution candidate merge head drift")
    if candidate.get("source_git_blob") != pointer.get("exact_source_blob"):
        raise ExcellenceContractError("evolution candidate source blob pointer drift")
    if comparison.get("winner") != "candidate":
        raise ExcellenceContractError("evolution receipt did not preserve the measured winner")
    if comparison.get("baseline_allowed") is not True or comparison.get("candidate_allowed") is not False:
        raise ExcellenceContractError("evolution comparison does not demonstrate improvement")
    if comparison.get("candidate_reason") != "duplicate_check:security":
        raise ExcellenceContractError("evolution comparison rejection reason drift")
    if comparison.get("order_independent_rejection") is not True:
        raise ExcellenceContractError("EVOLVING requires order-independent duplicate rejection")
    if comparison.get("malformed_evidence_rejected_before_provider_access") is not True:
        raise ExcellenceContractError("EVOLVING requires malformed evidence to fail before provider access")

    proof = receipt.get("proof")
    if not isinstance(proof, Mapping):
        raise ExcellenceContractError("evolution receipt proof must be an object")
    if proof.get("workflow_run_id") != pointer.get("public_proof_run_id"):
        raise ExcellenceContractError("public proof run pointer drift")
    if proof.get("artifact_id") != pointer.get("public_proof_artifact_id"):
        raise ExcellenceContractError("public proof artifact pointer drift")
    if proof.get("artifact_digest") != pointer.get("public_proof_artifact_digest"):
        raise ExcellenceContractError("public proof artifact digest pointer drift")
    tests = proof.get("tests")
    if not isinstance(tests, Mapping):
        raise ExcellenceContractError("evolution proof tests must be an object")
    if tests.get("passed") != tests.get("total") or tests.get("failed") != 0:
        raise ExcellenceContractError("evolution public proof tests are not fully green")
    if tests.get("passed") != pointer.get("tests_passed"):
        raise ExcellenceContractError("evolution public proof test count pointer drift")

    exact_blobs = proof.get("exact_git_blobs")
    readback = proof.get("post_merge_readback")
    if not isinstance(exact_blobs, Mapping) or not isinstance(readback, Mapping):
        raise ExcellenceContractError("evolution exact-byte proof is incomplete")
    if exact_blobs.get("merge-authority.mjs") != pointer.get("exact_source_blob"):
        raise ExcellenceContractError("evolution exact source blob drift")
    if readback.get("apex_main_head") != evolved:
        raise ExcellenceContractError("evolution post-merge head readback drift")
    for name, blob in exact_blobs.items():
        if readback.get(name) != blob:
            raise ExcellenceContractError(f"evolution post-merge blob drift: {name}")

    decision = receipt.get("decision")
    if not isinstance(decision, Mapping):
        raise ExcellenceContractError("evolution receipt decision must be an object")
    required_flags = (
        "measured_improvement_present",
        "candidate_beats_baseline",
        "winner_preserved_on_main",
        "exact_candidate_bytes_publicly_reproduced",
        "post_merge_bytes_match_proven_candidate",
        "canonical_anchor_preserved",
        "lineage_conflict_absent",
        "company_claim_separate",
    )
    for flag in required_flags:
        if decision.get(flag) is not True:
            raise ExcellenceContractError(f"EVOLVING requires {flag}=true")
    if decision.get("duplicate_repository_created") is not False:
        raise ExcellenceContractError("EVOLVING rejects duplicate repository creation")
    if decision.get("evolution_blockers") != []:
        raise ExcellenceContractError("EVOLVING rejects unresolved evolution blockers")

    company = validated.get("company_evidence")
    claim = receipt.get("claim_boundary")
    if not isinstance(company, Mapping) or not isinstance(claim, Mapping):
        raise ExcellenceContractError("EVOLVING company claim boundary missing")
    if claim.get("company_stage_unchanged") != company.get("stage"):
        raise ExcellenceContractError("repository evolution cannot advance company stage")
    if claim.get("company_claim_ceiling_unchanged") != company.get("claim_ceiling"):
        raise ExcellenceContractError("repository evolution cannot advance company claim ceiling")
    if pointer.get("company_stage_unchanged") != company.get("stage"):
        raise ExcellenceContractError("evolution company-stage pointer drift")
    if pointer.get("company_claim_ceiling_unchanged") != company.get("claim_ceiling"):
        raise ExcellenceContractError("evolution company-ceiling pointer drift")
    for field in (
        "github_adoption_claimed",
        "github_affiliation_claimed",
        "github_capability_production_deployment_claimed",
        "production_scale_reliability_claimed",
    ):
        if claim.get(field) is not False:
            raise ExcellenceContractError(f"repository evolution cannot create {field}")

    result = receipt.get("result")
    if not isinstance(result, Mapping):
        raise ExcellenceContractError("evolution receipt result must be an object")
    if result.get("repository_state") != "EVOLVING":
        raise ExcellenceContractError("evolution receipt result state drift")
    if result.get("canonical_anchor_head") != anchor:
        raise ExcellenceContractError("evolution result canonical anchor drift")
    if result.get("current_evolved_head") != evolved:
        raise ExcellenceContractError("evolution result current head drift")

    for projection_ref in validated.get("projection_refs", []):
        projection_path = _resolve_file(root, projection_ref, "projection_ref")
        projection = _load_json(projection_path, f"projection {projection_ref}")
        implementation = projection.get("implementation")
        if not isinstance(implementation, Mapping):
            raise ExcellenceContractError("EVOLVING projection implementation missing")
        if implementation.get("state") != "EVOLVING":
            raise ExcellenceContractError("EVOLVING projection state drift")
        if implementation.get("canonical_head") != anchor:
            raise ExcellenceContractError("EVOLVING projection canonical anchor drift")
        if implementation.get("evolved_head") != evolved:
            raise ExcellenceContractError("EVOLVING projection current head drift")
        if implementation.get("evolution_receipt") != relative:
            raise ExcellenceContractError("EVOLVING projection receipt pointer drift")

    return dict(validated)
