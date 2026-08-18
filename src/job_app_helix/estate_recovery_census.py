"""Estate-wide recovery census across GlacierEQ repositories.

Recovered and strengthened from the stranded ``apex/mass-job-repo-recovery`` donor.
Unlike the in-repository ref graph, this runtime evaluates repository-level state across
an organization-sized estate and emits a deterministic recovery queue without mutating
any donor repository.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

Runner = Callable[[Sequence[str]], subprocess.CompletedProcess[str]]

RECOVERY_SIGNAL = re.compile(
    r"(?i)(restore|recovery|rollback|neutraliz|dual-plane|amputat|stranded|clipped)"
)
POWER_SIGNAL = re.compile(r"(?i)(implement|runtime|engine|compiler|agent|proof|deploy|execute)")


@dataclass(frozen=True)
class RepositoryRecoveryObservation:
    repository: str
    exists: bool
    archived: bool
    disabled: bool
    fork: bool
    size_kb: int
    default_branch: str | None
    pushed_at: str | None
    recent_messages: tuple[str, ...]
    recovery_signal_count: int
    power_signal_count: int
    recovery_class: str
    priority_score: int
    error: str | None = None

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class EstateRecoveryCensus:
    schema: str
    owner: str
    checked_count: int
    class_counts: Mapping[str, int]
    observations: tuple[RepositoryRecoveryObservation, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "owner": self.owner,
            "checked_count": self.checked_count,
            "class_counts": dict(self.class_counts),
            "observations": [row.as_dict() for row in self.observations],
        }


def _run(command: Sequence[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, check=False)


def load_repository_names(path: Path) -> tuple[str, ...]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError("repository manifest must be an object")
    rows = payload.get("repositories")
    if not isinstance(rows, list) or not rows:
        raise ValueError("repository manifest requires non-empty repositories")
    names: set[str] = set()
    for index, value in enumerate(rows):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"repositories[{index}] must be a non-empty string")
        names.add(value.rsplit("/", maxsplit=1)[-1])
    return tuple(sorted(names, key=str.casefold))


def _classify(
    *,
    exists: bool,
    archived: bool,
    disabled: bool,
    size_kb: int,
    recovery_signal_count: int,
    power_signal_count: int,
) -> tuple[str, int]:
    if not exists:
        return "MISSING_OR_INACCESSIBLE", 100
    if disabled:
        return "DISABLED_REPOSITORY", 95
    if archived:
        return "ARCHIVED_PRESERVE", 35
    if recovery_signal_count and power_signal_count == 0:
        return "RECOVERY_SIGNAL_WITHOUT_EXECUTABLE_POWER", 90
    if size_kb < 15:
        return "THIN_EXECUTABLE_SURFACE", 75
    if recovery_signal_count:
        return "RECOVERY_IN_PROGRESS", 60
    return "HEALTHY_MONITOR", 10


def inspect_repository(
    owner: str,
    repository: str,
    *,
    runner: Runner = _run,
    recent_commit_limit: int = 8,
) -> RepositoryRecoveryObservation:
    repo = runner(("gh", "api", f"repos/{owner}/{repository}"))
    if repo.returncode != 0:
        error = (repo.stderr or repo.stdout or "repository lookup failed").strip()[:240]
        recovery_class, score = _classify(
            exists=False,
            archived=False,
            disabled=False,
            size_kb=0,
            recovery_signal_count=0,
            power_signal_count=0,
        )
        return RepositoryRecoveryObservation(
            repository=repository,
            exists=False,
            archived=False,
            disabled=False,
            fork=False,
            size_kb=0,
            default_branch=None,
            pushed_at=None,
            recent_messages=(),
            recovery_signal_count=0,
            power_signal_count=0,
            recovery_class=recovery_class,
            priority_score=score,
            error=error,
        )

    metadata = json.loads(repo.stdout)
    if not isinstance(metadata, Mapping):
        raise ValueError(f"GitHub metadata for {repository} must be an object")
    commits = runner(
        (
            "gh",
            "api",
            f"repos/{owner}/{repository}/commits?per_page={recent_commit_limit}",
            "--jq",
            ".[ ].commit.message",
        )
    )
    messages = tuple(
        line.split("\n", maxsplit=1)[0][:120]
        for line in commits.stdout.splitlines()
        if line.strip()
    ) if commits.returncode == 0 else ()
    recovery_count = sum(bool(RECOVERY_SIGNAL.search(message)) for message in messages)
    power_count = sum(bool(POWER_SIGNAL.search(message)) for message in messages)
    size_kb = int(metadata.get("size") or 0)
    archived = bool(metadata.get("archived"))
    disabled = bool(metadata.get("disabled"))
    recovery_class, score = _classify(
        exists=True,
        archived=archived,
        disabled=disabled,
        size_kb=size_kb,
        recovery_signal_count=recovery_count,
        power_signal_count=power_count,
    )
    return RepositoryRecoveryObservation(
        repository=repository,
        exists=True,
        archived=archived,
        disabled=disabled,
        fork=bool(metadata.get("fork")),
        size_kb=size_kb,
        default_branch=str(metadata.get("default_branch")) if metadata.get("default_branch") else None,
        pushed_at=str(metadata.get("pushed_at")) if metadata.get("pushed_at") else None,
        recent_messages=messages,
        recovery_signal_count=recovery_count,
        power_signal_count=power_count,
        recovery_class=recovery_class,
        priority_score=score,
    )


def build_estate_recovery_census(
    owner: str,
    repositories: Sequence[str],
    *,
    runner: Runner = _run,
) -> EstateRecoveryCensus:
    if not repositories:
        raise ValueError("estate recovery census requires at least one repository")
    observations = tuple(
        sorted(
            (inspect_repository(owner, name, runner=runner) for name in set(repositories)),
            key=lambda row: (-row.priority_score, row.repository.casefold()),
        )
    )
    counts = Counter(row.recovery_class for row in observations)
    return EstateRecoveryCensus(
        schema="glaciereq.estate-recovery-census.v1",
        owner=owner,
        checked_count=len(observations),
        class_counts=dict(sorted(counts.items())),
        observations=observations,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="job-app-helix-estate-recovery")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--owner", default="GlacierEQ")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    census = build_estate_recovery_census(args.owner, load_repository_names(args.manifest))
    rendered = json.dumps(census.as_dict(), indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 2 if census.class_counts.get("MISSING_OR_INACCESSIBLE", 0) else 0


if __name__ == "__main__":
    raise SystemExit(main())
