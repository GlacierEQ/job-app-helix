from __future__ import annotations

import hashlib
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
        "operator_authorization_required_for_retirement",
    )
    for key in required_true:
        if policy.get(key) is not True:
            raise LibraryProgramError(f"{key} must remain true")

    lifecycle = tuple(policy.get("branch_lifecycle", ()))
    if lifecycle != BRANCH_LIFECYCLE:
        raise LibraryProgramError("branch lifecycle does not match upward capability evolution")
    if any(fragment in step for step in lifecycle for fragment in FORBIDDEN_ACTIVE_ACTION_FRAGMENTS):
        raise LibraryProgramError("active lifecycle contains a retirement/contraction action")

    boundary = _require_nonempty_text(policy.get("retirement_boundary"), "retirement_boundary")
    if "operator" not in boundary.casefold() or "not authorized" not in boundary.casefold():
        raise LibraryProgramError("retirement boundary must reserve destructive lifecycle decisions to operator authority")


def _assert_mesh_safe_disposition(branch: Mapping[str, Any], *, label: str) -> None:
    """No generated receipt may grant destructive ref authority or assume zero loss."""
    disposition = branch.get("remote_ref_disposition")
    if isinstance(disposition, str) and any(
        token in disposition.upper()
        for token in ("DELETE", "ARCHIVE", "DISCARD", "REMOVE_REF")
    ):
        raise LibraryProgramError(
            f"{label}: destructive remote-ref disposition is forbidden"
        )

    unique = branch.get("unique_value")
    if isinstance(unique, str) and unique.strip().upper() in {
        "NONE", "ZERO", "NO_UNIQUE_VALUE"
    }:
        proof = branch.get("unique_contribution_verification")
        if not isinstance(proof, Mapping):
            raise LibraryProgramError(
                f"{label}: zero claim requires unique_contribution_verification"
            )
        if proof.get("verdict") != "ZERO":
            raise LibraryProgramError(
                f"{label}: UNIQUE_CONTRIBUTION=0 requires a ZERO verdict"
            )
        refs = proof.get("provider_readback_refs")
        if not isinstance(refs, list) or not refs or not all(
            isinstance(ref, str) and ref.strip() for ref in refs
        ):
            raise LibraryProgramError(
                f"{label}: zero claim requires nonempty provider readback refs"
            )
        if proof.get("lineage_preserved") is not True:
            raise LibraryProgramError(
                f"{label}: retirement requires verified durable lineage preservation"
            )


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
            raise LibraryProgramError(f"{name}: priority must be a non-negative integer")
        action = _require_nonempty_text(repository.get("action"), f"{name}.action")
        if action not in VALID_ACTIONS:
            raise LibraryProgramError(f"{name}: unsupported action {action!r}")
        if any(fragment in action for fragment in FORBIDDEN_ACTIVE_ACTION_FRAGMENTS):
            raise LibraryProgramError(f"{name}: contraction action is not permitted")
        if repository.get("default_branch") not in {"main", "master"}:
            raise LibraryProgramError(f"{name}: unsupported default branch")
        if repository.get("visibility") not in {"public", "private"}:
            raise LibraryProgramError(f"{name}: visibility must be public or private")

        for field in ("role", "readme_state", "proof_state", "branch_state", "identity_state"):
            _require_nonempty_text(repository.get(field), f"{name}.{field}")

        aliases = repository.get("aliases")
        if not isinstance(aliases, list) or not aliases:
            raise LibraryProgramError(f"{name}: aliases must be a non-empty list")
        for alias in aliases:
            alias_text = _require_nonempty_text(alias, f"{name}.alias")
            normalized = _normalized_alias(alias_text)
            prior_owner = observed_aliases.get(normalized)
            if prior_owner and prior_owner != name:
                raise LibraryProgramError(
                    f"alias {alias_text!r} is shared by {prior_owner} and {name}"
                )
            observed_aliases[normalized] = name

        observed_repositories.append(name)
        observed_priorities.append(priority)

    if tuple(observed_repositories) != EXPECTED_REPOSITORIES:
        raise LibraryProgramError(
            "priority repositories must remain exact and ordered: "
            f"observed={tuple(observed_repositories)!r}"
        )
    if observed_priorities != list(range(len(repositories))):
        raise LibraryProgramError("priorities must be unique and contiguous from zero")

    megamind = repositories[-1]
    if megamind.get("identity_state") != "PENDING_USER_INTENT_CONFIRMATION":
        raise LibraryProgramError("the megamind alias must remain explicitly unresolved")

    return dict(payload)


def validate_latest_execution_receipt(
    program_path: Path, program_payload: Mapping[str, Any]
) -> dict[str, Any]:
    receipt_reference = _require_nonempty_text(
        program_payload.get("latest_execution_receipt"), "latest_execution_receipt"
    )
    receipt_path = _repository_root(program_path) / receipt_reference
    receipt_payload = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt = _require_mapping(receipt_payload, "execution receipt")

    if receipt.get("schema") != RECEIPT_SCHEMA:
        raise LibraryProgramError(f"execution receipt schema must be {RECEIPT_SCHEMA}")

    scope = _require_mapping(receipt.get("scope"), "execution receipt scope")
    if scope.get("kind") != "priority_spine_wave":
        raise LibraryProgramError("execution receipt must describe a priority_spine_wave")
    if scope.get("repositories") != len(EXPECTED_REPOSITORIES):
        raise LibraryProgramError("execution receipt repository count is not exact")
    if scope.get("whole_library_completion_claimed") is not False:
        raise LibraryProgramError("execution receipt must not claim whole-library completion")

    policy = _require_mapping(receipt.get("policy"), "execution receipt policy")
    for key in (
        "preserve_unique_value_before_closure",
        "holographic_mesh_anti_replacement",
        "zero_unique_contribution_required_for_retirement",
        "latest_is_routing_cursor_only",
    ):
        if policy.get(key) is not True:
            raise LibraryProgramError(f"execution receipt must require {key}")

    provenance = receipt.get("historical_source_receipt")
    if provenance is not None:
        origin = _require_mapping(provenance, "historical_source_receipt")
        source_rel = _require_nonempty_text(origin.get("path"), "historical source path")
        source_path = Path(source_rel)
        if source_path.is_absolute() or ".." in source_path.parts:
            raise LibraryProgramError("historical source path must be repository-relative")
        try:
            source_bytes = (_repository_root(program_path) / source_path).read_bytes()
        except OSError as exc:
            raise LibraryProgramError("historical source receipt is unavailable") from exc
        observed_sha = hashlib.sha256(source_bytes).hexdigest()
        if observed_sha != origin.get("sha256"):
            raise LibraryProgramError("historical source receipt digest mismatch")

    outcomes = receipt.get("outcomes")
    if not isinstance(outcomes, list):
        raise LibraryProgramError("execution receipt outcomes must be a list")
    observed = tuple(
        _require_nonempty_text(
            _require_mapping(item, f"outcomes[{index}]").get("repository"),
            f"outcomes[{index}].repository",
        )
        for index, item in enumerate(outcomes)
    )
    for index, raw_item in enumerate(outcomes):
        item = _require_mapping(raw_item, f"outcomes[{index}]")
        _assert_mesh_safe_disposition(item, label=f"outcomes[{index}]")
        branches = item.get("branch_dispositions", [])
        if not isinstance(branches, list):
            raise LibraryProgramError(
                f"outcomes[{index}].branch_dispositions must be a list"
            )
        for j, branch in enumerate(branches):
            _assert_mesh_safe_disposition(
                _require_mapping(branch, f"outcomes[{index}].branch_dispositions[{j}]"),
                label=f"outcomes[{index}].branch_dispositions[{j}]",
            )

    if observed != EXPECTED_REPOSITORIES:
        raise LibraryProgramError("execution receipt outcomes must match the exact priority spine order")

    summary = _require_mapping(receipt.get("summary"), "execution receipt summary")
    if summary.get("whole_library_complete") is not False:
        raise LibraryProgramError("execution receipt overstates whole-library completion")

    return dict(receipt_payload)


def render_library_program(payload: Mapping[str, Any]) -> str:
    repositories = payload["repositories"]
    lines = [
        "# Library Capability Elevation Program",
        "",
        "The estate moves upward: reconstruct purpose, recover lost capability, preserve unique value, compose complementary gains, implement, verify, integrate, and deploy or package. Inventory, similarity, proof gaps, or assistant-generated classifications cannot authorize retirement.",
        "",
        "| Priority | Repository | Role | Upward action | README | Proof | Branch |",
        "|---:|---|---|---|---|---|---|",
    ]
    for repository in repositories:
        lines.append(
            "| {priority} | `{repository}` | {role} | `{action}` | `{readme_state}` | "
            "`{proof_state}` | `{branch_state}` |".format(**repository)
        )
    lines.extend(
        (
            "",
            "## Capability evolution",
            "",
            "`DISCOVER -> RECONSTRUCT_PURPOSE -> COMPARE_LINEAGE -> EXTRACT_UNIQUE_VALUE -> RESTORE_LOST_CAPABILITY -> COMPOSE_GAINS -> IMPLEMENT -> VERIFY -> INTEGRATE -> DEPLOY_OR_PACKAGE -> RECEIPT`",
            "",
            "Retirement, archival, merge-away, close-as-duplicate, and ref deletion are outside this automated lifecycle and require explicit operator authorization after verified capability preservation.",
        )
    )
    return "\n".join(lines) + "\n"
