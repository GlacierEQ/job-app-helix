from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

SCHEMA = "glaciereq.library.priority-spine.v2"
RECEIPT_SCHEMA = "glaciereq.library.execution-receipt.v1"
EXPECTED_REPOSITORIES = (
    "GlacierEQ/the-tower-of-babel",
    "GlacierEQ/job-application",
    "GlacierEQ/job-app-helix",
    "GlacierEQ/monolith",
    "GlacierEQ/AKOS",
    "GlacierEQ/pro-code",
    "GlacierEQ/Pro_Code",
    "GlacierEQ/mastermind",
    "GlacierEQ/megaminds-pdf",
)
VALID_ACTIONS = {
    "EVOLVE_AND_INTEGRATE",
    "EVOLVE_AND_DEPLOY",
    "EXTEND_UPWARD_EXECUTION_ENGINE",
    "COMPLETE_AND_EXPAND_ACTIVE_CAPABILITY",
    "EVOLVE_AND_CONNECT",
    "HARDEN_EXPAND_AND_INTEGRATE",
    "RESTORE_EXPAND_AND_INTEGRATE",
    "RECONSTRUCT_PURPOSE_AND_EVOLVE",
}
BRANCH_LIFECYCLE = (
    "DISCOVER",
    "RECONSTRUCT_PURPOSE",
    "COMPARE_LINEAGE",
    "EXTRACT_UNIQUE_VALUE",
    "RESTORE_LOST_CAPABILITY",
    "COMPOSE_GAINS",
    "IMPLEMENT",
    "VERIFY",
    "INTEGRATE",
    "DEPLOY_OR_PACKAGE",
    "RECEIPT",
)
FORBIDDEN_ACTIVE_ACTION_FRAGMENTS = (
    "DELETE",
    "ARCHIVE",
    "KILL",
    "MERGE_OR_CLOSE",
    "CONSOLIDATE",
    "SUPERSEDE",
)
DESTRUCTIVE_DISPOSITION_FRAGMENTS = (
    "DELETE",
    "ARCHIVE",
    "DISCARD",
    "REMOVE_REF",
)


class LibraryProgramError(ValueError):
    """Raised when the library evolution contract is incomplete or contradicts upward execution."""


def _require_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise LibraryProgramError(f"{label} must be an object")
    return value


def _require_nonempty_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LibraryProgramError(f"{label} must be non-empty text")
    return value.strip()


def _normalized_alias(value: str) -> str:
    return " ".join(value.casefold().split())


def _repository_root(program_path: Path) -> Path:
    if program_path.parent.name == "manifests":
        return program_path.parent.parent
    return program_path.parent


def _assert_upward_policy(policy: Mapping[str, Any]) -> None:
    if policy.get("direction") != "MAXIMUM_COHERENT_ADVANCE":
        raise LibraryProgramError("direction must remain MAXIMUM_COHERENT_ADVANCE")
    required_true = (
        "preserve_unique_value",
        "require_repository_native_proof",
        "require_explicit_nonclaims",
        "inventory_cannot_authorize_retirement",
        "similarity_cannot_establish_redundancy",
        "failed_proof_cannot_establish_irrelevance",
        "unverified_cannot_mean_disposable",
    )
    for key in required_true:
        if policy.get(key) is not True:
            raise LibraryProgramError(f"{key} must remain true")

    lifecycle = tuple(policy.get("branch_lifecycle", ()))
    if lifecycle != BRANCH_LIFECYCLE:
        raise LibraryProgramError("branch lifecycle does not match upward capability evolution")
    if any(
        fragment in step
        for step in lifecycle
        for fragment in FORBIDDEN_ACTIVE_ACTION_FRAGMENTS
    ):
        raise LibraryProgramError("active lifecycle contains a retirement/contraction action")

    boundary = _require_nonempty_text(
        policy.get("retirement_boundary"), "retirement_boundary"
    )
    if "unique_contribution=0" not in boundary.casefold():
        raise LibraryProgramError(
            "retirement boundary must require provider-read-back UNIQUE_CONTRIBUTION=0"
        )
    if "preserve_drained_lineage" not in boundary.casefold():
        raise LibraryProgramError(
            "retirement boundary must preserve drained lineage rather than delete refs"
        )


def _assert_zero_unique_contribution_proof(
    branch: Mapping[str, Any], *, label: str
) -> None:
    proof = branch.get("unique_contribution_verification")
    if not isinstance(proof, Mapping):
        raise LibraryProgramError(
            f"{label}: zero-contribution retirement requires "
            "unique_contribution_verification"
        )
    if proof.get("verdict") != "ZERO":
        raise LibraryProgramError(
            f"{label}: retirement requires UNIQUE_CONTRIBUTION=0"
        )
    refs = proof.get("provider_readback_refs")
    if not isinstance(refs, list) or not refs or not all(
        isinstance(ref, str) and ref.strip() for ref in refs
    ):
        raise LibraryProgramError(
            f"{label}: zero-unique-contribution proof requires provider readback refs"
        )
    if proof.get("lineage_preserved") is not True:
        raise LibraryProgramError(
            f"{label}: retirement requires verified durable lineage preservation"
        )


def _assert_mesh_safe_branch_disposition(
    branch: Mapping[str, Any], *, label: str
) -> None:
    unique_value = branch.get("unique_value")
    disposition = branch.get("remote_ref_disposition")
    destructive = isinstance(disposition, str) and any(
        fragment in disposition.upper()
        for fragment in DESTRUCTIVE_DISPOSITION_FRAGMENTS
    )
    if destructive:
        raise LibraryProgramError(
            f"{label}: retirement must preserve lineage pointers; destructive "
            "remote-ref disposition is forbidden"
        )

    declares_zero = isinstance(unique_value, str) and unique_value.strip().upper() in {
        "NONE",
        "ZERO",
        "NO_UNIQUE_VALUE",
    }
    if declares_zero:
        _assert_zero_unique_contribution_proof(branch, label=label)


def validate_library_program(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    root = _require_mapping(payload, "library program")

    if root.get("schema") != SCHEMA:
        raise LibraryProgramError(f"schema must be {SCHEMA}")
    if root.get("control_plane") != "GlacierEQ/job-app-helix":
        raise LibraryProgramError("control plane must be GlacierEQ/job-app-helix")
    if root.get("default_branch") != "main":
        raise LibraryProgramError("default branch must be main")

    receipt_reference = _require_nonempty_text(
        root.get("latest_execution_receipt"), "latest_execution_receipt"
    )
    if Path(receipt_reference).is_absolute() or ".." in Path(receipt_reference).parts:
        raise LibraryProgramError("latest execution receipt must be repository-relative")

    scopes = _require_mapping(root.get("scopes"), "scopes")
    recruiter = _require_mapping(scopes.get("recruiter_portfolio"), "recruiter_portfolio")
    if recruiter.get("source") != "manifests/portfolio_repositories.json":
        raise LibraryProgramError("recruiter portfolio must reuse the exact inventory manifest")
    if recruiter.get("rollout") != "manifests/portfolio_rollout.json":
        raise LibraryProgramError("recruiter portfolio must reuse the exact rollout manifest")

    owned = _require_mapping(scopes.get("owned_library"), "owned_library")
    if owned.get("kind") != "dynamic_census":
        raise LibraryProgramError("owned library must remain a dynamic census")

    policy = _require_mapping(root.get("policy"), "policy")
    _assert_upward_policy(policy)

    repositories = root.get("repositories")
    if not isinstance(repositories, list) or not repositories:
        raise LibraryProgramError("repositories must be a non-empty list")

    observed_repositories: list[str] = []
    observed_priorities: list[int] = []
    observed_aliases: dict[str, str] = {}

    for index, raw_repository in enumerate(repositories):
        repository = _require_mapping(raw_repository, f"repositories[{index}]")
        name = _require_nonempty_text(repository.get("repository"), "repository")
        priority = repository.get("priority")
        if not isinstance(priority, int) or priority < 0:
            raise LibraryProgramError(f"repositories[{index}].priority must be a non-negative integer")
        observed_repositories.append(name)
        observed_priorities.append(priority)
        for alias in repository.get("aliases", []):
            alias_text = _require_nonempty_text(alias, f"repositories[{index}].aliases")
            normalized = _normalized_alias(alias_text)
            existing = observed_aliases.get(normalized)
            if existing and existing != name:
                raise LibraryProgramError(f"alias collision: {alias_text}")
            observed_aliases[normalized] = name

    if tuple(observed_repositories) != EXPECTED_REPOSITORIES:
        raise LibraryProgramError("priority spine repository order changed unexpectedly")
    if observed_priorities != list(range(len(observed_priorities))):
        raise LibraryProgramError("priority spine priorities must be contiguous from zero")

    return payload
