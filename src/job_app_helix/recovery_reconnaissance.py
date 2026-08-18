"""History-wide donor discovery for intelligent capability recovery.

The lower-level recovery stack can restore exact bytes, symbols, semantic
closures, and federated donors. This module answers the question that matters
before those engines can act: *which historical heads deserve attention?*

It consumes exact historical ref records, resolves or boundedly acquires their
commit objects, compares every donor to one target revision, and emits a
ranked reconnaissance report. A missing donor never aborts the whole scan.
Directly deleted source/test capability dominates the ranking; branch names and
retirement labels are provenance, not proof that a donor is useful or obsolete.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

from .capability_archaeology import ArchaeologyError, excavate, resolve_commit
from .intelligent_recovery import build_intelligent_recovery_plan, summarize_recovery_plan

DonorAvailability = Literal["AVAILABLE", "FETCHED", "UNAVAILABLE"]
DonorDisposition = Literal[
    "HIGH_PRIORITY_STRANDED",
    "COMPOSITION_CANDIDATE",
    "EVIDENCE_CANDIDATE",
    "NO_CURRENT_DELTA",
    "UNAVAILABLE",
]


class RecoveryReconnaissanceError(RuntimeError):
    """Raised when reconnaissance input itself is invalid."""


@dataclass(frozen=True)
class HistoricalDonor:
    name: str
    expected_head_sha: str
    source_bucket: str
    state: str
    pull_request: int | None = None
    reason: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class DonorReconnaissance:
    name: str
    expected_head_sha: str
    resolved_sha: str | None
    source_bucket: str
    state: str
    pull_request: int | None
    availability: DonorAvailability
    reachable_from_target: bool | None
    candidate_count: int
    deleted_source_test_count: int
    modified_source_test_count: int
    control_surface_count: int
    documentation_count: int
    total_donor_bytes: int
    recovery_signal: float
    priority_score: float
    disposition: DonorDisposition
    top_paths: tuple[str, ...]
    blocker: str | None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class RecoveryReconnaissanceReport:
    repository: str
    target_sha: str
    donors: tuple[DonorReconnaissance, ...]
    available_donor_shas: tuple[str, ...]
    intelligent_plan_summary: dict[str, object] | None
    receipt_sha256: str

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": "glaciereq.recovery-reconnaissance.v1",
            "repository": self.repository,
            "target_sha": self.target_sha,
            "donors": [donor.to_dict() for donor in self.donors],
            "available_donor_shas": list(self.available_donor_shas),
            "intelligent_plan_summary": self.intelligent_plan_summary,
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
        raise RecoveryReconnaissanceError(f"git {' '.join(args)} failed: {detail}")
    return proc


def _commit_available(repo: Path, sha: str) -> bool:
    return _git(repo, "cat-file", "-e", f"{sha}^{{commit}}", check=False).returncode == 0


def _fetch_exact_commit(repo: Path, sha: str, remote: str) -> tuple[bool, str | None]:
    proc = _git(
        repo,
        "fetch",
        "--no-tags",
        "--no-recurse-submodules",
        remote,
        sha,
        check=False,
    )
    if proc.returncode == 0 and _commit_available(repo, sha):
        return True, None
    detail = proc.stderr.strip() or proc.stdout.strip() or "exact commit fetch failed"
    return False, detail


def _reachable(repo: Path, donor_sha: str, target_sha: str) -> bool:
    proc = _git(repo, "merge-base", "--is-ancestor", donor_sha, target_sha, check=False)
    return proc.returncode == 0


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
        return "SOURCE"
    if name in {
        "pyproject.toml", "package.json", "package-lock.json", "pnpm-lock.yaml",
        "yarn.lock", "cargo.toml", "cargo.lock", "go.mod", "go.sum", "dockerfile",
    }:
        return "CONTROL"
    if suffix in {".md", ".rst", ".adoc", ".txt"} or "docs" in parts:
        return "DOC"
    return "OTHER"


def _manifest_rows(payload: dict[str, object]) -> Iterable[HistoricalDonor]:
    buckets = (
        "retired_refs",
        "restored_refs_after_failed_transaction",
        "preserved_active_refs",
        "blocked_refs",
    )
    for bucket in buckets:
        raw_rows = payload.get(bucket, [])
        if not isinstance(raw_rows, list):
            raise RecoveryReconnaissanceError(f"manifest field {bucket!r} must be a list")
        for raw in raw_rows:
            if not isinstance(raw, dict):
                raise RecoveryReconnaissanceError(f"manifest {bucket!r} contains a non-object row")
            name = raw.get("name")
            sha = raw.get("expected_head_sha")
            if not isinstance(name, str) or not name:
                continue
            if not isinstance(sha, str) or len(sha) < 7:
                continue
            pull_request = raw.get("pull_request")
            yield HistoricalDonor(
                name=name,
                expected_head_sha=sha,
                source_bucket=bucket,
                state=str(raw.get("state", "UNKNOWN")),
                pull_request=pull_request if isinstance(pull_request, int) else None,
                reason=str(raw["reason"]) if raw.get("reason") is not None else None,
            )


def load_historical_donors(manifest_path: Path) -> tuple[HistoricalDonor, ...]:
    """Load exact donor identities from a branch-retirement/recovery manifest."""
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RecoveryReconnaissanceError("recovery manifest root must be an object")
    by_sha: dict[str, HistoricalDonor] = {}
    for donor in _manifest_rows(payload):
        existing = by_sha.get(donor.expected_head_sha)
        if existing is None:
            by_sha[donor.expected_head_sha] = donor
            continue
        # Prefer preservation/recovery records over retirement labels when the exact
        # same historical head appears in multiple bookkeeping buckets.
        rank = {
            "preserved_active_refs": 4,
            "restored_refs_after_failed_transaction": 3,
            "blocked_refs": 2,
            "retired_refs": 1,
        }
        if rank.get(donor.source_bucket, 0) > rank.get(existing.source_bucket, 0):
            by_sha[donor.expected_head_sha] = donor
    return tuple(sorted(by_sha.values(), key=lambda item: (item.name, item.expected_head_sha)))


def _priority(
    *,
    deleted_source_test: int,
    modified_source_test: int,
    control_surface: int,
    candidate_count: int,
    recovery_signal: float,
    reachable: bool,
) -> float:
    direct_loss = min(0.48, 0.10 * deleted_source_test)
    composition = min(0.20, 0.04 * modified_source_test)
    control = min(0.08, 0.02 * control_surface)
    breadth = min(0.08, candidate_count / 250.0)
    nonancestor = 0.08 if not reachable else 0.0
    score = 0.08 + direct_loss + composition + control + breadth + nonancestor
    score += min(0.08, recovery_signal / 100.0)
    return round(min(1.0, score), 6)


def _disposition(
    deleted_source_test: int,
    modified_source_test: int,
    candidate_count: int,
    priority_score: float,
) -> DonorDisposition:
    if deleted_source_test > 0 and priority_score >= 0.40:
        return "HIGH_PRIORITY_STRANDED"
    if modified_source_test > 0:
        return "COMPOSITION_CANDIDATE"
    if candidate_count > 0:
        return "EVIDENCE_CANDIDATE"
    return "NO_CURRENT_DELTA"


def _unavailable(donor: HistoricalDonor, blocker: str) -> DonorReconnaissance:
    return DonorReconnaissance(
        name=donor.name,
        expected_head_sha=donor.expected_head_sha,
        resolved_sha=None,
        source_bucket=donor.source_bucket,
        state=donor.state,
        pull_request=donor.pull_request,
        availability="UNAVAILABLE",
        reachable_from_target=None,
        candidate_count=0,
        deleted_source_test_count=0,
        modified_source_test_count=0,
        control_surface_count=0,
        documentation_count=0,
        total_donor_bytes=0,
        recovery_signal=0.0,
        priority_score=0.0,
        disposition="UNAVAILABLE",
        top_paths=(),
        blocker=blocker,
    )


def inspect_historical_donor(
    repo: Path,
    donor: HistoricalDonor,
    *,
    target_sha: str,
    fetch_missing: bool = False,
    remote: str = "origin",
) -> DonorReconnaissance:
    """Inspect one exact historical head without allowing it to abort the wider scan."""
    repo = repo.resolve()
    availability: DonorAvailability = "AVAILABLE"
    if not _commit_available(repo, donor.expected_head_sha):
        if not fetch_missing:
            return _unavailable(donor, "historical commit object is not present locally")
        fetched, blocker = _fetch_exact_commit(repo, donor.expected_head_sha, remote)
        if not fetched:
            return _unavailable(donor, blocker or "historical commit fetch failed")
        availability = "FETCHED"

    try:
        resolved_sha = resolve_commit(repo, donor.expected_head_sha)
        report = excavate(repo, donor_ref=resolved_sha, target_ref=target_sha)
    except (ArchaeologyError, RecoveryReconnaissanceError) as exc:
        return _unavailable(donor, str(exc))

    deleted_source_test = 0
    modified_source_test = 0
    control_surface = 0
    documentation = 0
    total_donor_bytes = 0
    recovery_signal = 0.0
    ranked_paths: list[tuple[float, str]] = []
    for candidate in report.candidates:
        role = _path_role(candidate.path)
        target_absent = candidate.target_blob_sha256 is None or candidate.status == "D"
        if role in {"SOURCE", "TEST"}:
            if target_absent:
                deleted_source_test += 1
            else:
                modified_source_test += 1
        elif role == "CONTROL":
            control_surface += 1
        elif role == "DOC":
            documentation += 1
        total_donor_bytes += candidate.donor_size
        recovery_signal += candidate.recovery_score
        role_weight = 1.0 if role in {"SOURCE", "TEST"} else 0.7 if role == "CONTROL" else 0.4
        absence_weight = 1.25 if target_absent else 1.0
        ranked_paths.append((candidate.recovery_score * role_weight * absence_weight, candidate.path))

    reachable = _reachable(repo, resolved_sha, target_sha)
    priority_score = _priority(
        deleted_source_test=deleted_source_test,
        modified_source_test=modified_source_test,
        control_surface=control_surface,
        candidate_count=len(report.candidates),
        recovery_signal=recovery_signal,
        reachable=reachable,
    )
    disposition = _disposition(
        deleted_source_test,
        modified_source_test,
        len(report.candidates),
        priority_score,
    )
    ranked_paths.sort(key=lambda item: (-item[0], item[1]))
    return DonorReconnaissance(
        name=donor.name,
        expected_head_sha=donor.expected_head_sha,
        resolved_sha=resolved_sha,
        source_bucket=donor.source_bucket,
        state=donor.state,
        pull_request=donor.pull_request,
        availability=availability,
        reachable_from_target=reachable,
        candidate_count=len(report.candidates),
        deleted_source_test_count=deleted_source_test,
        modified_source_test_count=modified_source_test,
        control_surface_count=control_surface,
        documentation_count=documentation,
        total_donor_bytes=total_donor_bytes,
        recovery_signal=round(recovery_signal, 6),
        priority_score=priority_score,
        disposition=disposition,
        top_paths=tuple(path for _, path in ranked_paths[:8]),
        blocker=None,
    )


def build_recovery_reconnaissance(
    repo: Path,
    *,
    donors: Sequence[HistoricalDonor],
    target_ref: str = "HEAD",
    fetch_missing: bool = False,
    remote: str = "origin",
    max_auto_actions: int = 8,
) -> RecoveryReconnaissanceReport:
    """Rank historical donors and compose them into the intelligent recovery planner."""
    if not donors:
        raise RecoveryReconnaissanceError("at least one historical donor is required")
    repo = repo.resolve()
    target_sha = resolve_commit(repo, target_ref)
    rows = [
        inspect_historical_donor(
            repo,
            donor,
            target_sha=target_sha,
            fetch_missing=fetch_missing,
            remote=remote,
        )
        for donor in donors
    ]
    rows.sort(
        key=lambda item: (
            item.disposition == "UNAVAILABLE",
            -item.priority_score,
            -item.deleted_source_test_count,
            -item.modified_source_test_count,
            item.name,
        )
    )
    available_shas = tuple(
        dict.fromkeys(
            row.resolved_sha
            for row in rows
            if row.resolved_sha is not None and row.candidate_count > 0
        )
    )
    plan_summary: dict[str, object] | None = None
    if available_shas:
        plan = build_intelligent_recovery_plan(
            repo,
            donor_refs=available_shas,
            target_ref=target_sha,
            max_auto_actions=max_auto_actions,
        )
        plan_summary = summarize_recovery_plan(plan)

    repository = _git(repo, "config", "--get", "remote.origin.url", check=False).stdout.strip()
    repository = repository or str(repo)
    payload = {
        "schema": "glaciereq.recovery-reconnaissance.v1",
        "repository": repository,
        "target_sha": target_sha,
        "donors": [row.to_dict() for row in rows],
        "available_donor_shas": list(available_shas),
        "intelligent_plan_summary": plan_summary,
    }
    receipt = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return RecoveryReconnaissanceReport(
        repository=repository,
        target_sha=target_sha,
        donors=tuple(rows),
        available_donor_shas=available_shas,
        intelligent_plan_summary=plan_summary,
        receipt_sha256=receipt,
    )


def discover_from_manifest(
    repo: Path,
    manifest_path: Path,
    *,
    target_ref: str = "HEAD",
    fetch_missing: bool = False,
    remote: str = "origin",
    max_auto_actions: int = 8,
) -> RecoveryReconnaissanceReport:
    donors = load_historical_donors(manifest_path)
    return build_recovery_reconnaissance(
        repo,
        donors=donors,
        target_ref=target_ref,
        fetch_missing=fetch_missing,
        remote=remote,
        max_auto_actions=max_auto_actions,
    )
