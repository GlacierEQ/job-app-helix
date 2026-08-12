from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .repo_excellence import ExcellenceContractError, validate_repo_excellence_record

GIT_SHA = re.compile(r"[0-9a-f]{40}\Z")
SHA256 = re.compile(r"sha256:[0-9a-f]{64}\Z")
EXPECTED_PROOF_BLOBS = {
    "merge-authority.mjs",
    "merge-authority.test.mjs",
    "evolution-benchmark.test.mjs",
}
PUBLIC_PROOF_HOST = "GlacierEQ/public-actions-runner-host"


def _require_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ExcellenceContractError(f"{label} must be non-empty text")
    return value.strip()


def _require_git_sha(value: Any, label: str) -> str:
    text = _require_text(value, label)
    if not GIT_SHA.fullmatch(text):
        raise ExcellenceContractError(f"{label} must be an exact 40-hex Git SHA")
    return text


def _require_positive_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ExcellenceContractError(f"{label} must be a positive integer")
    return value


def _require_nonnegative_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ExcellenceContractError(f"{label} must be a non-negative integer")
    return value


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
    repository_root: Path | str,
) -> dict[str, Any]:
    """Validate a measured EVOLVING admission against an explicit checkout root."""
    root = Path(repository_root)
    validated = validate_repo_excellence_record(payload, root)
    if validated.get("state") != "EVOLVING":
        raise ExcellenceContractError("evolution validator requires state EVOLVING")

    identity = validated["identity"]
    anchor = _require_git_sha(identity.get("canonical_head"), "identity.canonical_head")
    evolved = _require_git_sha(
        identity.get("current_evolved_head"),
        "identity.current_evolved_head",
    )
    if anchor == evolved:
        raise ExcellenceContractError("EVOLVING requires a head distinct from its canonical anchor")

    evolution = validated.get("evolution")
    if not isinstance(evolution, Mapping):
        raise ExcellenceContractError("EVOLVING requires an evolution object")
    if evolution.get("next_gate") != "NEXT_MEASURED_EVOLUTION":
        raise ExcellenceContractError("EVOLVING requires NEXT_MEASURED_EVOLUTION as next gate")
    if evolution.get("canonical_anchor_head") != anchor:
        raise ExcellenceContractError("evolution canonical anchor drift")
    if evolution.get("current_head") != evolved:
        raise ExcellenceContractError("evolution current head drift")

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

    pointer_passed = _require_positive_int(
        pointer.get("tests_passed"),
        "evolution_receipt.tests_passed",
    )
    pointer_failed = _require_nonnegative_int(
        pointer.get("tests_failed"),
        "evolution_receipt.tests_failed",
    )
    if pointer_failed != 0:
        raise ExcellenceContractError("EVOLVING pointer requires zero failed tests")
    _require_positive_int(
        pointer.get("public_proof_run_id"),
        "evolution_receipt.public_proof_run_id",
    )
    _require_positive_int(
        pointer.get("public_proof_artifact_id"),
        "evolution_receipt.public_proof_artifact_id",
    )
    artifact_digest = _require_text(
        pointer.get("public_proof_artifact_digest"),
        "evolution_receipt.public_proof_artifact_digest",
    )
    if not SHA256.fullmatch(artifact_digest):
        raise ExcellenceContractError("EVOLVING pointer requires SHA-256 proof artifact digest")
    exact_source_blob = _require_git_sha(
        pointer.get("exact_source_blob"),
        "evolution_receipt.exact_source_blob",
    )

    relative = _require_text(pointer.get("path"), "evolution_receipt.path")
    if evolution.get("receipt") != relative:
        raise ExcellenceContractError("evolution receipt path drift")
    receipt_path = _resolve_file(root, relative, "evolution_receipt.path")
    blob_sha = _require_git_sha(pointer.get("blob_sha"), "evolution_receipt.blob_sha")
    if _git_blob_sha(receipt_path) != blob_sha:
        raise ExcellenceContractError(
            "EVOLVING receipt Git blob SHA does not match repository bytes"
        )

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
    if evolution.get("current_cycle") != experiment.get("id"):
        raise ExcellenceContractError("evolution current-cycle drift")
    baseline = experiment.get("baseline")
    candidate = experiment.get("candidate")
    comparison = experiment.get("comparison")
    if not all(isinstance(item, Mapping) for item in (baseline, candidate, comparison)):
        raise ExcellenceContractError("evolution experiment comparison contract incomplete")
    if baseline.get("head") != anchor or baseline.get("allowed") is not True:
        raise ExcellenceContractError("EVOLVING requires a reproduced weaker baseline")
    _require_git_sha(candidate.get("candidate_head"), "evolution candidate head")
    if candidate.get("merged_head") != evolved:
        raise ExcellenceContractError("evolution candidate merge head drift")
    candidate_source_blob = _require_git_sha(
        candidate.get("source_git_blob"),
        "evolution candidate source_git_blob",
    )
    candidate_test_blob = _require_git_sha(
        candidate.get("regression_test_git_blob"),
        "evolution candidate regression_test_git_blob",
    )
    candidate_benchmark_blob = _require_git_sha(
        candidate.get("benchmark_test_git_blob"),
        "evolution candidate benchmark_test_git_blob",
    )
    if candidate_source_blob != exact_source_blob:
        raise ExcellenceContractError("evolution candidate source blob pointer drift")
    if comparison.get("winner") != "candidate":
        raise ExcellenceContractError("evolution receipt did not preserve the measured winner")
    if comparison.get("baseline_allowed") is not True:
        raise ExcellenceContractError("evolution comparison did not reproduce weaker baseline")
    if comparison.get("candidate_allowed") is not False:
        raise ExcellenceContractError("evolution comparison did not reject ambiguous candidate")
    if comparison.get("candidate_reason") != "duplicate_check:security":
        raise ExcellenceContractError("evolution comparison rejection reason drift")
    if comparison.get("order_independent_rejection") is not True:
        raise ExcellenceContractError("EVOLVING requires order-independent duplicate rejection")
    if comparison.get("malformed_evidence_rejected_before_provider_access") is not True:
        raise ExcellenceContractError(
            "EVOLVING requires malformed evidence to fail before provider access"
        )

    proof = receipt.get("proof")
    if not isinstance(proof, Mapping):
        raise ExcellenceContractError("evolution receipt proof must be an object")
    if proof.get("public_host_repository") != PUBLIC_PROOF_HOST:
        raise ExcellenceContractError("evolution proof host repository drift")
    _require_positive_int(proof.get("public_host_pull_request"), "proof public-host PR")
    _require_git_sha(proof.get("workflow_run_head_sha"), "proof workflow run head")
    _require_git_sha(proof.get("workflow_checkout_merge_sha"), "proof checkout merge head")
    if proof.get("workflow_run_id") != pointer.get("public_proof_run_id"):
        raise ExcellenceContractError("public proof run pointer drift")
    if proof.get("artifact_id") != pointer.get("public_proof_artifact_id"):
        raise ExcellenceContractError("public proof artifact pointer drift")
    if proof.get("artifact_digest") != artifact_digest:
        raise ExcellenceContractError("public proof artifact digest pointer drift")

    tests = proof.get("tests")
    if not isinstance(tests, Mapping):
        raise ExcellenceContractError("evolution proof tests must be an object")
    proof_passed = _require_positive_int(tests.get("passed"), "proof.tests.passed")
    proof_failed = _require_nonnegative_int(tests.get("failed"), "proof.tests.failed")
    proof_total = _require_positive_int(tests.get("total"), "proof.tests.total")
    if proof_failed != 0 or proof_passed != proof_total:
        raise ExcellenceContractError("evolution public proof tests are not fully green")
    if proof_passed != pointer_passed:
        raise ExcellenceContractError("evolution public proof test count pointer drift")

    exact_blobs = proof.get("exact_git_blobs")
    readback = proof.get("post_merge_readback")
    if not isinstance(exact_blobs, Mapping) or not isinstance(readback, Mapping):
        raise ExcellenceContractError("evolution exact-byte proof is incomplete")
    if set(exact_blobs) != EXPECTED_PROOF_BLOBS:
        raise ExcellenceContractError("evolution exact-byte proof file set drift")
    for name, blob in exact_blobs.items():
        _require_git_sha(blob, f"proof.exact_git_blobs.{name}")
        if readback.get(name) != blob:
            raise ExcellenceContractError(f"evolution post-merge blob drift: {name}")
    if exact_blobs["merge-authority.mjs"] != candidate_source_blob:
        raise ExcellenceContractError("evolution exact source blob drift")
    if exact_blobs["merge-authority.test.mjs"] != candidate_test_blob:
        raise ExcellenceContractError("evolution exact regression-test blob drift")
    if exact_blobs["evolution-benchmark.test.mjs"] != candidate_benchmark_blob:
        raise ExcellenceContractError("evolution exact benchmark blob drift")
    if readback.get("apex_main_head") != evolved:
        raise ExcellenceContractError("evolution post-merge head readback drift")

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
        raise ExcellenceContractError(
            "repository evolution cannot advance company claim ceiling"
        )
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
    if result.get("next_gate") != evolution.get("next_gate"):
        raise ExcellenceContractError("evolution result next-gate drift")

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
