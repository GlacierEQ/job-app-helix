"""Repository-wide historical ref graph for intelligent recovery.

Engine 1 answers *how* to restore a qualified donor safely.
Engine 2 answers *which exact historical heads* in a known manifest contain
recoverable capability.
This engine expands the search boundary to the repository's complete local ref
graph. It discovers divergent branch families, collapses equivalent branch
lineages by exact delta fingerprint, rejects patch-equivalent/integrated work,
and sends only the strongest unresolved families to Engine 2.

The graph is read-only. Ref discovery never mutates branches, files, or history.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

from .capability_archaeology import resolve_commit
from .recovery_reconnaissance import (
    DonorReconnaissance,
    HistoricalDonor,
    RecoveryReconnaissanceReport,
    build_recovery_reconnaissance,
)

RefState = Literal[
    "TARGET",
    "ANCESTOR",
    "PATCH_EQUIVALENT",
    "DIVERGENT",
    "NO_DELTA",
    "UNAVAILABLE",
]


class RecoveryRefGraphError(RuntimeError):
    """Raised when ref-graph discovery cannot preserve its invariants."""


@dataclass(frozen=True)
class RefDelta:
    ref_name: str
    short_name: str
    head_sha: str
    merge_base_sha: str | None
    state: RefState
    unique_commit_count: int
    changed_path_count: int
    executable_path_count: int
    test_path_count: int
    control_path_count: int
    delta_fingerprint: str | None
    changed_paths: tuple[str, ...]
    blocker: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class RefFamily:
    family_id: str
    representative_ref: str
    representative_sha: str
    aliases: tuple[str, ...]
    delta_fingerprint: str
    unique_commit_count: int
    changed_path_count: int
    executable_path_count: int
    test_path_count: int
    control_path_count: int
    preliminary_score: float
    reconnaissance: DonorReconnaissance | None

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["reconnaissance"] = (
            self.reconnaissance.to_dict() if self.reconnaissance is not None else None
        )
        return payload


@dataclass(frozen=True)
class RecoveryRefGraphReport:
    repository: str
    target_sha: str
    refs_scanned: int
    divergent_refs: int
    equivalent_refs: int
    ancestor_refs: int
    families: tuple[RefFamily, ...]
    deep_reconnaissance: RecoveryReconnaissanceReport | None
    receipt_sha256: str

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": "glaciereq.recovery-ref-graph.v1",
            "repository": self.repository,
            "target_sha": self.target_sha,
            "refs_scanned": self.refs_scanned,
            "divergent_refs": self.divergent_refs,
            "equivalent_refs": self.equivalent_refs,
            "ancestor_refs": self.ancestor_refs,
            "families": [family.to_dict() for family in self.families],
            "deep_reconnaissance": (
                self.deep_reconnaissance.to_dict()
                if self.deep_reconnaissance is not None
                else None
            ),
            "receipt_sha256": self.receipt_sha256,
        }


def _git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if check and proc.returncode != 0:
        detail = proc.stderr.strip() or proc.stdout.strip() or "unknown git failure"
        raise RecoveryRefGraphError(f"git {' '.join(args)} failed: {detail}")
    return proc


def _short_ref(ref_name: str) -> str:
    for prefix in ("refs/remotes/origin/", "refs/heads/"):
        if ref_name.startswith(prefix):
            return ref_name[len(prefix) :]
    return ref_name


def _list_refs(repo: Path, namespaces: Sequence[str]) -> tuple[tuple[str, str], ...]:
    rows: dict[str, str] = {}
    for namespace in namespaces:
        proc = _git(
            repo,
            "for-each-ref",
            "--format=%(refname)%09%(objectname)",
            namespace,
            check=False,
        )
        if proc.returncode != 0:
            continue
        for line in proc.stdout.splitlines():
            if "\t" not in line:
                continue
            ref_name, sha = line.split("\t", 1)
            if ref_name.endswith("/HEAD"):
                continue
            if len(sha) == 40:
                rows[ref_name] = sha
    return tuple(sorted(rows.items()))


def _merge_base(repo: Path, left: str, right: str) -> str | None:
    proc = _git(repo, "merge-base", left, right, check=False)
    if proc.returncode != 0:
        return None
    value = proc.stdout.strip()
    return value if len(value) == 40 else None


def _is_ancestor(repo: Path, ancestor: str, target: str) -> bool:
    return _git(
        repo,
        "merge-base",
        "--is-ancestor",
        ancestor,
        target,
        check=False,
    ).returncode == 0


def _changed_paths(repo: Path, base_sha: str, head_sha: str) -> tuple[str, ...]:
    proc = _git(
        repo,
        "diff",
        "--name-only",
        "--diff-filter=AMRT",
        base_sha,
        head_sha,
    )
    return tuple(sorted({line.strip() for line in proc.stdout.splitlines() if line.strip()}))


def _delta_fingerprint(repo: Path, base_sha: str, head_sha: str) -> str:
    """Hash exact branch-owned tree delta independent of branch name/commit IDs."""
    proc = _git(
        repo,
        "diff",
        "--raw",
        "--no-abbrev",
        "-M",
        base_sha,
        head_sha,
    )
    normalized = "\n".join(line.rstrip() for line in proc.stdout.splitlines() if line.strip())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _unique_commit_count(repo: Path, target_sha: str, head_sha: str) -> int:
    """Count donor commits whose patch is not represented in target according to git cherry."""
    proc = _git(repo, "cherry", target_sha, head_sha, check=False)
    if proc.returncode != 0:
        return 0
    return sum(1 for line in proc.stdout.splitlines() if line.startswith("+ "))


def _path_role(path: str) -> str:
    normalized = path.lower()
    parts = set(Path(normalized).parts)
    name = Path(normalized).name
    suffix = Path(normalized).suffix
    if ".github" in parts or "workflows" in parts:
        return "CONTROL"
    if "tests" in parts or "test" in parts or name.startswith("test_"):
        return "TEST"
    if suffix in {
        ".py", ".pyi", ".js", ".jsx", ".ts", ".tsx", ".rs", ".go", ".java",
        ".kt", ".swift", ".c", ".cc", ".cpp", ".h", ".hpp", ".cs", ".rb",
        ".php", ".sh",
    } or "src" in parts:
        return "EXECUTABLE"
    if name in {
        "pyproject.toml", "package.json", "package-lock.json", "pnpm-lock.yaml",
        "yarn.lock", "cargo.toml", "cargo.lock", "go.mod", "go.sum", "dockerfile",
    }:
        return "CONTROL"
    return "OTHER"


def _role_counts(paths: Sequence[str]) -> tuple[int, int, int]:
    executable = 0
    tests = 0
    control = 0
    for path in paths:
        role = _path_role(path)
        if role == "EXECUTABLE":
            executable += 1
        elif role == "TEST":
            tests += 1
        elif role == "CONTROL":
            control += 1
    return executable, tests, control


def inspect_ref(
    repo: Path,
    *,
    ref_name: str,
    head_sha: str,
    target_sha: str,
) -> RefDelta:
    """Classify one ref without conflating branch ancestry with capability loss."""
    if head_sha == target_sha:
        return RefDelta(
            ref_name,
            _short_ref(ref_name),
            head_sha,
            target_sha,
            "TARGET",
            0,
            0,
            0,
            0,
            0,
            None,
            (),
        )
    if _is_ancestor(repo, head_sha, target_sha):
        return RefDelta(
            ref_name,
            _short_ref(ref_name),
            head_sha,
            head_sha,
            "ANCESTOR",
            0,
            0,
            0,
            0,
            0,
            None,
            (),
        )
    base_sha = _merge_base(repo, head_sha, target_sha)
    if base_sha is None:
        return RefDelta(
            ref_name,
            _short_ref(ref_name),
            head_sha,
            None,
            "UNAVAILABLE",
            0,
            0,
            0,
            0,
            0,
            None,
            (),
            "no merge-base with target",
        )
    paths = _changed_paths(repo, base_sha, head_sha)
    if not paths:
        return RefDelta(
            ref_name,
            _short_ref(ref_name),
            head_sha,
            base_sha,
            "NO_DELTA",
            0,
            0,
            0,
            0,
            0,
            _delta_fingerprint(repo, base_sha, head_sha),
            (),
        )
    executable, tests, control = _role_counts(paths)
    unique_commits = _unique_commit_count(repo, target_sha, head_sha)
    state: RefState = "PATCH_EQUIVALENT" if unique_commits == 0 else "DIVERGENT"
    return RefDelta(
        ref_name=ref_name,
        short_name=_short_ref(ref_name),
        head_sha=head_sha,
        merge_base_sha=base_sha,
        state=state,
        unique_commit_count=unique_commits,
        changed_path_count=len(paths),
        executable_path_count=executable,
        test_path_count=tests,
        control_path_count=control,
        delta_fingerprint=_delta_fingerprint(repo, base_sha, head_sha),
        changed_paths=paths,
    )


def _preliminary_score(delta: RefDelta) -> float:
    executable = min(0.50, 0.08 * delta.executable_path_count)
    tests = min(0.16, 0.04 * delta.test_path_count)
    control = min(0.08, 0.02 * delta.control_path_count)
    commits = min(0.14, 0.02 * delta.unique_commit_count)
    breadth = min(0.07, delta.changed_path_count / 200.0)
    return round(min(1.0, 0.05 + executable + tests + control + commits + breadth), 6)


def _family_id(fingerprint: str) -> str:
    return f"ref-family-{fingerprint[:16]}"


def _collapse_families(deltas: Sequence[RefDelta]) -> tuple[RefFamily, ...]:
    grouped: dict[str, list[RefDelta]] = defaultdict(list)
    for delta in deltas:
        if delta.state != "DIVERGENT" or delta.delta_fingerprint is None:
            continue
        grouped[delta.delta_fingerprint].append(delta)

    families: list[RefFamily] = []
    for fingerprint, members in grouped.items():
        members.sort(
            key=lambda row: (
                -_preliminary_score(row),
                -row.executable_path_count,
                -row.test_path_count,
                row.short_name,
            )
        )
        representative = members[0]
        families.append(
            RefFamily(
                family_id=_family_id(fingerprint),
                representative_ref=representative.short_name,
                representative_sha=representative.head_sha,
                aliases=tuple(sorted(member.short_name for member in members)),
                delta_fingerprint=fingerprint,
                unique_commit_count=representative.unique_commit_count,
                changed_path_count=representative.changed_path_count,
                executable_path_count=representative.executable_path_count,
                test_path_count=representative.test_path_count,
                control_path_count=representative.control_path_count,
                preliminary_score=_preliminary_score(representative),
                reconnaissance=None,
            )
        )
    families.sort(
        key=lambda row: (
            -row.preliminary_score,
            -row.executable_path_count,
            -row.test_path_count,
            row.representative_ref,
        )
    )
    return tuple(families)


def _attach_reconnaissance(
    families: Sequence[RefFamily],
    report: RecoveryReconnaissanceReport,
) -> tuple[RefFamily, ...]:
    by_sha = {
        row.resolved_sha: row
        for row in report.donors
        if row.resolved_sha is not None
    }
    enriched = [
        RefFamily(
            family_id=family.family_id,
            representative_ref=family.representative_ref,
            representative_sha=family.representative_sha,
            aliases=family.aliases,
            delta_fingerprint=family.delta_fingerprint,
            unique_commit_count=family.unique_commit_count,
            changed_path_count=family.changed_path_count,
            executable_path_count=family.executable_path_count,
            test_path_count=family.test_path_count,
            control_path_count=family.control_path_count,
            preliminary_score=family.preliminary_score,
            reconnaissance=by_sha.get(family.representative_sha),
        )
        for family in families
    ]
    enriched.sort(
        key=lambda row: (
            -(
                row.reconnaissance.priority_score
                if row.reconnaissance is not None
                else row.preliminary_score
            ),
            -row.executable_path_count,
            row.representative_ref,
        )
    )
    return tuple(enriched)


def build_ref_graph(
    repo: Path,
    *,
    target_ref: str = "HEAD",
    namespaces: Sequence[str] = ("refs/remotes/origin", "refs/heads"),
    max_deep_families: int = 64,
    max_auto_actions: int = 8,
) -> RecoveryRefGraphReport:
    """Discover and deeply rank unresolved capability across the complete ref graph."""
    if max_deep_families <= 0:
        raise RecoveryRefGraphError("max_deep_families must be positive")
    repo = repo.resolve()
    target_sha = resolve_commit(repo, target_ref)
    ref_rows = _list_refs(repo, namespaces)
    deltas = tuple(
        inspect_ref(repo, ref_name=ref_name, head_sha=head_sha, target_sha=target_sha)
        for ref_name, head_sha in ref_rows
    )
    families = _collapse_families(deltas)
    deep_candidates = [
        family
        for family in families
        if family.executable_path_count > 0 or family.test_path_count > 0
    ][:max_deep_families]

    deep_report: RecoveryReconnaissanceReport | None = None
    if deep_candidates:
        donors = tuple(
            HistoricalDonor(
                name=family.representative_ref,
                expected_head_sha=family.representative_sha,
                source_bucket="ref_graph",
                state="DISCOVERED_DIVERGENT_REF",
            )
            for family in deep_candidates
        )
        deep_report = build_recovery_reconnaissance(
            repo,
            donors=donors,
            target_ref=target_sha,
            max_auto_actions=max_auto_actions,
        )
        families = _attach_reconnaissance(families, deep_report)

    repository = _git(repo, "config", "--get", "remote.origin.url", check=False).stdout.strip()
    repository = repository or str(repo)
    payload = {
        "schema": "glaciereq.recovery-ref-graph.v1",
        "repository": repository,
        "target_sha": target_sha,
        "refs_scanned": len(deltas),
        "divergent_refs": sum(delta.state == "DIVERGENT" for delta in deltas),
        "equivalent_refs": sum(delta.state == "PATCH_EQUIVALENT" for delta in deltas),
        "ancestor_refs": sum(delta.state == "ANCESTOR" for delta in deltas),
        "families": [family.to_dict() for family in families],
        "deep_reconnaissance_receipt": (
            deep_report.receipt_sha256 if deep_report is not None else None
        ),
    }
    receipt = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return RecoveryRefGraphReport(
        repository=repository,
        target_sha=target_sha,
        refs_scanned=len(deltas),
        divergent_refs=sum(delta.state == "DIVERGENT" for delta in deltas),
        equivalent_refs=sum(delta.state == "PATCH_EQUIVALENT" for delta in deltas),
        ancestor_refs=sum(delta.state == "ANCESTOR" for delta in deltas),
        families=families,
        deep_reconnaissance=deep_report,
        receipt_sha256=receipt,
    )
