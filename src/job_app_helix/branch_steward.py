from __future__ import annotations

import json
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence


class BranchStewardError(RuntimeError):
    pass


@dataclass(frozen=True)
class BranchAssessment:
    repository: str
    canonical_branch: str
    branch: str
    merge_base: str
    ahead: int
    behind: int
    unique_patch_commits: tuple[str, ...]
    changed_files: tuple[str, ...]
    classification: str
    safe_direct_merge: bool
    retirement_ready: bool
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


def _unique_patch_commits(repo: Path, canonical: str, branch: str) -> tuple[str, ...]:
    # git cherry compares patch identity, so cherry-picked commits already represented
    # on canonical do not masquerade as unique branch value merely because SHA differs.
    rows = _line_output(repo, "cherry", canonical, branch)
    return tuple(row[2:].strip() for row in rows if row.startswith("+ "))


def _changed_files(repo: Path, canonical: str, branch: str) -> tuple[str, ...]:
    return _line_output(repo, "diff", "--name-only", f"{canonical}...{branch}")


def assess_branch(repo: Path, canonical: str, branch: str) -> BranchAssessment:
    repo = repo.resolve()
    if not (repo / ".git").exists():
        raise BranchStewardError(f"not a git checkout: {repo}")

    merge_base = _run(repo, "merge-base", canonical, branch).stdout.strip()
    if not merge_base:
        raise BranchStewardError(f"no merge base for {canonical} and {branch}")

    behind, ahead = _count_pair(repo, canonical, branch)
    unique = _unique_patch_commits(repo, canonical, branch)
    files = _changed_files(repo, canonical, branch)

    if ahead == 0:
        classification = "ANCESTRY_EXHAUSTED"
        safe_direct_merge = False
        retirement_ready = True
        reason = "branch has no commits absent from canonical ancestry"
    elif not unique:
        classification = "PATCH_EQUIVALENT_EXHAUSTED"
        safe_direct_merge = False
        retirement_ready = True
        reason = "branch SHAs differ, but git-cherry found no unique patch value"
    elif behind == 0:
        classification = "CURRENT_UNIQUE_VALUE"
        safe_direct_merge = True
        retirement_ready = False
        reason = "branch is based on canonical ancestry and contains unique patches"
    else:
        classification = "DIVERGED_UNIQUE_VALUE"
        safe_direct_merge = False
        retirement_ready = False
        reason = (
            "branch is behind canonical and still contains unique patches; synthesize its useful delta "
            "onto fresh canonical ancestry instead of merging the stale tip directly"
        )

    return BranchAssessment(
        repository=repo.name,
        canonical_branch=canonical,
        branch=branch,
        merge_base=merge_base,
        ahead=ahead,
        behind=behind,
        unique_patch_commits=unique,
        changed_files=files,
        classification=classification,
        safe_direct_merge=safe_direct_merge,
        retirement_ready=retirement_ready,
        reason=reason,
    )


def list_remote_branches(
    repo: Path,
    canonical: str = "main",
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
        branch = row[len(prefix):]
        if branch in {"HEAD", canonical}:
            continue
        if branch.casefold().startswith(protected):
            continue
        out.append(branch)
    return tuple(sorted(set(out), key=str.casefold))


def assess_repository(
    repo: Path,
    canonical: str = "main",
    remote: str = "origin",
) -> dict[str, object]:
    canonical_ref = f"{remote}/{canonical}"
    branches = list_remote_branches(repo, canonical=canonical, remote=remote)
    assessments = [
        assess_branch(repo, canonical_ref, f"{remote}/{branch}")
        for branch in branches
    ]
    priority_order = {
        "DIVERGED_UNIQUE_VALUE": 0,
        "CURRENT_UNIQUE_VALUE": 1,
        "PATCH_EQUIVALENT_EXHAUSTED": 2,
        "ANCESTRY_EXHAUSTED": 3,
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
        "canonical": canonical_ref,
        "branch_count": len(assessments),
        "actionable_unique": sum(not item.retirement_ready for item in assessments),
        "retirement_ready": sum(item.retirement_ready for item in assessments),
        "branches": [item.to_dict() for item in assessments],
    }


def write_receipt(payload: dict[str, object], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path
