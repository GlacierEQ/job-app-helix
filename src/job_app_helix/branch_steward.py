from __future__ import annotations

import json
import subprocess
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path


class BranchStewardError(RuntimeError):
    pass


@dataclass(frozen=True)
class BranchAssessment:
    repository: str
    reference_branch: str
    branch: str
    merge_base: str
    ahead: int
    behind: int
    unique_patch_commits: tuple[str, ...]
    changed_files: tuple[str, ...]
    classification: str
    safe_direct_merge: bool
    retirement_ready: bool
    operator_review_required: bool
    capability_review_required: bool
    reason: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _run(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )
    if check and completed.returncode != 0:
        raise BranchStewardError(
            f"git {' '.join(args)} failed ({completed.returncode}): {completed.stderr.strip()}"
        )
    return completed


def _line_output(repo: Path, *args: str) -> tuple[str, ...]:
    output = _run(repo, *args).stdout
    return tuple(line.strip() for line in output.splitlines() if line.strip())


def _count_pair(repo: Path, left: str, right: str) -> tuple[int, int]:
    raw = _run(repo, "rev-list", "--left-right", "--count", f"{left}...{right}").stdout.strip()
    fields = raw.split()
    if len(fields) != 2:
        raise BranchStewardError(f"unexpected rev-list count output: {raw!r}")
    left_only, right_only = (int(value) for value in fields)
    return left_only, right_only


def _unique_patch_commits(repo: Path, reference: str, branch: str) -> tuple[str, ...]:
    # Patch identity is useful evidence but is not a complete capability comparison.
    # A patch-equivalent branch may still contain purpose, structure, history, tests,
    # generated assets, integration context, or donor value that deserves inspection.
    rows = _line_output(repo, "cherry", reference, branch)
    return tuple(row[2:].strip() for row in rows if row.startswith("+ "))


def _changed_files(repo: Path, reference: str, branch: str) -> tuple[str, ...]:
    return _line_output(repo, "diff", "--name-only", f"{reference}...{branch}")


def assess_branch(repo: Path, reference: str, branch: str) -> BranchAssessment:
    """Assess branch ancestry without converting ancestry into deletion authority.

    This function intentionally cannot declare a branch retirement-ready. Git ancestry
    and patch equivalence are only inputs to a later capability/lineage review. Any
    actual retirement remains an explicit OPERATOR decision outside this module.
    """

    repo = repo.resolve()
    if not (repo / ".git").exists():
        raise BranchStewardError(f"not a git checkout: {repo}")

    merge_base = _run(repo, "merge-base", reference, branch).stdout.strip()
    if not merge_base:
        raise BranchStewardError(f"no merge base for {reference} and {branch}")

    behind, ahead = _count_pair(repo, reference, branch)
    unique = _unique_patch_commits(repo, reference, branch)
    files = _changed_files(repo, reference, branch)

    if ahead == 0:
        classification = "ANCESTRY_EQUIVALENT_CAPABILITY_REVIEW_REQUIRED"
        safe_direct_merge = False
        reason = (
            "branch has no commits absent from reference ancestry, but ancestry alone "
            "cannot establish capability exhaustion; inspect purpose, lineage, artifacts, "
            "consumers, and historical donor value before any lifecycle decision"
        )
    elif not unique:
        classification = "PATCH_EQUIVALENT_CAPABILITY_REVIEW_REQUIRED"
        safe_direct_merge = False
        reason = (
            "git-cherry found no unique patch commits, but patch equivalence is not proof "
            "of functional or historical redundancy; perform capability review"
        )
    elif behind == 0:
        classification = "CURRENT_UNIQUE_VALUE"
        safe_direct_merge = True
        reason = (
            "branch is based on current ancestry and contains unique patches; verify and "
            "compose its useful capability into the strongest current system"
        )
    else:
        classification = "DIVERGED_UNIQUE_VALUE"
        safe_direct_merge = False
        reason = (
            "branch is behind current ancestry and contains unique patches; synthesize its "
            "useful delta with later gains on fresh ancestry rather than discarding either side"
        )

    return BranchAssessment(
        repository=repo.name,
        reference_branch=reference,
        branch=branch,
        merge_base=merge_base,
        ahead=ahead,
        behind=behind,
        unique_patch_commits=unique,
        changed_files=files,
        classification=classification,
        safe_direct_merge=safe_direct_merge,
        retirement_ready=False,
        operator_review_required=True,
        capability_review_required=True,
        reason=reason,
    )


def list_remote_branches(
    repo: Path,
    reference: str = "main",
    remote: str = "origin",
    protected_prefixes: Sequence[str] = ("upstream", "vendor", "release/"),
) -> tuple[str, ...]:
    rows = _line_output(
        repo,
        "for-each-ref",
        "--format=%(refname:short)",
        f"refs/remotes/{remote}/",
    )
    protected = tuple(prefix.casefold() for prefix in protected_prefixes)
    out: list[str] = []
    for row in rows:
        prefix = f"{remote}/"
        if not row.startswith(prefix):
            continue
        branch = row[len(prefix) :]
        if branch in {"HEAD", reference}:
            continue
        if branch.casefold().startswith(protected):
            continue
        out.append(branch)
    return tuple(sorted(set(out), key=str.casefold))


def assess_repository(
    repo: Path,
    reference: str = "main",
    remote: str = "origin",
) -> dict[str, object]:
    reference_ref = f"{remote}/{reference}"
    branches = list_remote_branches(repo, reference=reference, remote=remote)
    assessments = [assess_branch(repo, reference_ref, f"{remote}/{branch}") for branch in branches]
    priority_order = {
        "DIVERGED_UNIQUE_VALUE": 0,
        "CURRENT_UNIQUE_VALUE": 1,
        "PATCH_EQUIVALENT_CAPABILITY_REVIEW_REQUIRED": 2,
        "ANCESTRY_EQUIVALENT_CAPABILITY_REVIEW_REQUIRED": 3,
    }
    assessments.sort(
        key=lambda item: (
            priority_order.get(item.classification, 99),
            -len(item.unique_patch_commits),
            item.branch.casefold(),
        )
    )
    return {
        "repository": repo.name,
        "reference": reference_ref,
        "branch_count": len(assessments),
        "actionable_unique": sum(bool(item.unique_patch_commits) for item in assessments),
        "capability_review_required": len(assessments),
        "retirement_ready": 0,
        "retirement_policy": "OPERATOR_AUTHORIZATION_REQUIRED_AFTER_CAPABILITY_REVIEW",
        "branches": [item.to_dict() for item in assessments],
    }


def write_receipt(payload: dict[str, object], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path
