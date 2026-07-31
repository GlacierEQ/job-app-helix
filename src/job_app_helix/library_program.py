from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

SCHEMA = "glaciereq.library.priority-spine.v1"
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
    "VERIFY_AND_CONSOLIDATE",
    "EXTEND_CONTROL_PLANE",
    "COMPLETE_ACTIVE_PR",
    "PRESERVE_AND_MONITOR",
    "HARDEN_AND_VERIFY",
    "HARDEN_AND_BOUND",
    "AUDIT_HARDEN_AND_CONSOLIDATE",
    "IDENTITY_REVIEW_BEFORE_HARDENING",
}
BRANCH_LIFECYCLE = (
    "DISCOVER",
    "COMPARE",
    "PRESERVE",
    "VERIFY",
    "MERGE_OR_CLOSE",
    "DELETE_REF",
    "RECEIPT",
)


class LibraryProgramError(ValueError):
    """Raised when the library priority contract is incomplete or contradictory."""


def _require_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise LibraryProgramError(f"{label} must be an object")
    return value


def _require_nonempty_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LibraryProgramError(f"{label} must be non-empty text")
    return value.strip()


def _normalized_alias(value: str) -> str:
    """Normalize case and whitespace without collapsing meaningful separators."""

    return " ".join(value.casefold().split())


def _repository_root(program_path: Path) -> Path:
    if program_path.parent.name == "manifests":
        return program_path.parent.parent
    return program_path.parent


def validate_library_program(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    root = _require_mapping(payload, "library program")

    if root.get("schema") != SCHEMA:
        raise LibraryProgramError(f"schema must be {SCHEMA}")
    if root.get("canonical_control_plane") != "GlacierEQ/job-app-helix":
        raise LibraryProgramError("canonical control plane must be GlacierEQ/job-app-helix")
    if root.get("canonical_branch") != "main":
        raise LibraryProgramError("canonical branch must be main")

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

    policy = _require_mapping(root.get("policy"), "policy")
    lifecycle = tuple(policy.get("branch_lifecycle", ()))
    if lifecycle != BRANCH_LIFECYCLE:
        raise LibraryProgramError("branch lifecycle does not match the canonical retirement order")
    if policy.get("main_is_canonical") is not True:
        raise LibraryProgramError("main_is_canonical must be true")
    if policy.get("preserve_unique_value_before_closure") is not True:
        raise LibraryProgramError("unique value must be preserved before closure")

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
        if repository.get("action") not in VALID_ACTIONS:
            raise LibraryProgramError(f"{name}: unsupported action {repository.get('action')!r}")
        if repository.get("default_branch") not in {"main", "master"}:
            raise LibraryProgramError(f"{name}: unsupported default branch")
        if repository.get("visibility") not in {"public", "private"}:
            raise LibraryProgramError(f"{name}: visibility must be public or private")

        for field in (
            "role",
            "readme_state",
            "proof_state",
            "branch_state",
            "identity_state",
        ):
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
    if receipt.get("canonical_control_plane") != program_payload.get(
        "canonical_control_plane"
    ):
        raise LibraryProgramError("execution receipt control plane does not match the program")

    scope = _require_mapping(receipt.get("scope"), "execution receipt scope")
    if scope.get("kind") != "priority_spine_wave":
        raise LibraryProgramError("execution receipt must describe a priority_spine_wave")
    if scope.get("repositories") != len(EXPECTED_REPOSITORIES):
        raise LibraryProgramError("execution receipt repository count is not exact")
    if scope.get("whole_library_completion_claimed") is not False:
        raise LibraryProgramError("execution receipt must not claim whole-library completion")

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
    if observed != EXPECTED_REPOSITORIES:
        raise LibraryProgramError(
            "execution receipt outcomes must match the exact priority spine order"
        )

    receipt_policy = _require_mapping(receipt.get("policy"), "execution receipt policy")
    if receipt_policy.get("pr_closure_is_branch_deletion") is not False:
        raise LibraryProgramError("execution receipt conflates PR closure with branch deletion")
    if receipt_policy.get("remote_ref_deletion_capability_available") is not False:
        raise LibraryProgramError("execution receipt overstates remote-ref deletion capability")

    summary = _require_mapping(receipt.get("summary"), "execution receipt summary")
    if summary.get("whole_library_complete") is not False:
        raise LibraryProgramError("execution receipt overstates whole-library completion")
    if summary.get("remote_branch_refs_deleted") != 0:
        raise LibraryProgramError("execution receipt overstates remote branch deletion")

    return dict(receipt_payload)


def render_library_program(payload: Mapping[str, Any]) -> str:
    repositories = payload["repositories"]
    lines = [
        "# Library README and Branch Consolidation Program",
        "",
        "`main` is canonical. Claims advance only with repository-native evidence, and "
        "unique branch value is preserved before closure.",
        "",
        "| Priority | Repository | Role | Action | README | Proof | Branch |",
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
            "## Branch retirement",
            "",
            "`DISCOVER -> COMPARE -> PRESERVE -> VERIFY -> MERGE_OR_CLOSE -> "
            "DELETE_REF -> RECEIPT`",
            "",
            "Closing a pull request does not prove that its remote branch ref was deleted.",
        )
    )
    return "\n".join(lines) + "\n"
