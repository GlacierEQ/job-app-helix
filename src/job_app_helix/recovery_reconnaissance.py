"""History-wide donor discovery for intelligent capability recovery.

The recovery stack needs to distinguish *a branch's unique capability* from
ordinary files that merely happened to exist in an old snapshot. This engine
therefore qualifies divergent donors at their exact merge-base before ranking
or forwarding them to the intelligent planner.

For a divergent historical branch only paths added/modified/renamed between the
fork point and donor head are recovery candidates. Files inherited unchanged
from the branch base are excluded, even if they disappeared from modern main.
Ancestor snapshots remain visible as historical-contraction candidates because
there is no divergent branch delta to isolate.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

from .capability_archaeology import ArchaeologyError, CapabilityCandidate, excavate, resolve_commit
from .intelligent_recovery import (
    IntelligentRecoveryCandidate,
    build_intelligent_recovery_plan,
)

DonorAvailability = Literal["AVAILABLE", "FETCHED", "UNAVAILABLE"]
DonorDisposition = Literal[
    "HIGH_PRIORITY_STRANDED",
    "COMPOSITION_CANDIDATE",
    "EVIDENCE_CANDIDATE",
    "NO_CURRENT_DELTA",
    "UNAVAILABLE",
]
LineageMode = Literal["DIVERGED_BRANCH", "ANCESTOR_SNAPSHOT", "UNAVAILABLE"]


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
    lineage_mode: LineageMode
    lineage_base_sha: str | None
    observed_candidate_count: int
    candidate_count: int
    excluded_baseline_count: int
    deleted_source_test_count: int
    modified_source_test_count: int
    control_surface_count: int
    documentation_count: int
    total_donor_bytes: int
    recovery_signal: float
    priority_score: float
    disposition: DonorDisposition
    qualified_paths: tuple[str, ...]
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
            "schema": "glaciereq.recovery-reconnaissance.v2",
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
    return _git(
        repo,
        "merge-base",
        "--is-ancestor",
        donor_sha,
        target_sha,
        check=False,
    ).returncode == 0


def _merge_base(repo: Path, donor_sha: str, target_sha: str) -> str:
    proc = _git(repo, "merge-base", donor_sha, target_sha)
    base = proc.stdout.strip()
    if not base:
        raise RecoveryReconnaissanceError(
            f"no merge-base for donor {donor_sha} and target {target_sha}"
        )
    return base


def _donor_delta_paths(repo: Path, base_sha: str, donor_sha: str) -> frozenset[str]:
    """Return donor-present paths changed on the branch after its fork point."""
    if base_sha == donor_sha:
        return frozenset()
    proc = _git(
        repo,
        "diff",
        "--name-only",
        "--diff-filter=AMRT",
        base_sha,
        donor_sha,
    )
    return frozenset(line.strip() for line in proc.stdout.splitlines() if line.strip())


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
    for bucket in (
        "retired_refs",
        "restored_refs_after_failed_transaction",
        "preserved_active_refs",
        "blocked_refs",
    ):
        rows = payload.get(bucket, [])
        if not isinstance(rows, list):
            raise RecoveryReconnaissanceError(f"manifest field {bucket!r} must be a list")
        for raw in rows:
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
    """Load exact heads, preferring preservation provenance over retirement labels."""
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RecoveryReconnaissanceError("recovery manifest root must be an object")
    rank = {
        "preserved_active_refs": 4,
        "restored_refs_after_failed_transaction": 3,
        "blocked_refs": 2,
        "retired_refs": 1,
    }
    by_sha: dict[str, HistoricalDonor] = {}
    for donor in _manifest_rows(payload):
        existing = by_sha.get(donor.expected_head_sha)
        if existing is None or rank.get(donor.source_bucket, 0) > rank.get(
            existing.source_bucket, 0
        ):
            by_sha[donor.expected_head_sha] = donor
    return tuple(sorted(by_sha.values(), key=lambda row: (row.name, row.expected_head_sha)))


def _qualify_candidates(
    repo: Path,
    donor_sha: str,
    target_sha: str,
    candidates: Sequence[CapabilityCandidate],
) -> tuple[LineageMode, str, tuple[CapabilityCandidate, ...], int]:
    reachable = _reachable(repo, donor_sha, target_sha)
    base_sha = _merge_base(repo, donor_sha, target_sha)
    if reachable:
        # An ancestor has no branch-only delta. Its target differences are still
        # useful as historical contraction evidence, but they are identified as
        # an ancestor snapshot rather than a stranded branch invention.
        return "ANCESTOR_SNAPSHOT", base_sha, tuple(candidates), 0

    branch_paths = _donor_delta_paths(repo, base_sha, donor_sha)
    qualified = tuple(candidate for candidate in candidates if candidate.path in branch_paths)
    return "DIVERGED_BRANCH", base_sha, qualified, len(candidates) - len(qualified)


def _priority(
    *,
    deleted_source_test: int,
    modified_source_test: int,
    control_surface: int,
    candidate_count: int,
    recovery_signal: float,
    lineage_mode: LineageMode,
) -> float:
    direct_loss = min(0.56, 0.16 * deleted_source_test)
    composition = min(0.20, 0.04 * modified_source_test)
    control = min(0.08, 0.02 * control_surface)
    breadth = min(0.07, candidate_count / 250.0)
    branch_uniqueness = 0.08 if lineage_mode == "DIVERGED_BRANCH" else 0.0
    score = 0.07 + direct_loss + composition + control + breadth + branch_uniqueness
    score += min(0.08, recovery_signal / 100.0)
    return round(min(1.0, score), 6)


def _disposition(
    deleted_source_test: int,
    modified_source_test: int,
    candidate_count: int,
) -> DonorDisposition:
    if deleted_source_test > 0:
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
        lineage_mode="UNAVAILABLE",
        lineage_base_sha=None,
        observed_candidate_count=0,
        candidate_count=0,
        excluded_baseline_count=0,
        deleted_source_test_count=0,
        modified_source_test_count=0,
        control_surface_count=0,
        documentation_count=0,
        total_donor_bytes=0,
        recovery_signal=0.0,
        priority_score=0.0,
        disposition="UNAVAILABLE",
        qualified_paths=(),
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
    """Inspect one exact historical head while containing donor-specific failure."""
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
        archaeology = excavate(repo, donor_ref=resolved_sha, target_ref=target_sha)
        lineage_mode, lineage_base, qualified, excluded = _qualify_candidates(
            repo,
            resolved_sha,
            target_sha,
            archaeology.candidates,
        )
    except (ArchaeologyError, RecoveryReconnaissanceError) as exc:
        return _unavailable(donor, str(exc))

    deleted_source_test = 0
    modified_source_test = 0
    control_surface = 0
    documentation = 0
    total_donor_bytes = 0
    recovery_signal = 0.0
    ranked_paths: list[tuple[float, str]] = []

    for candidate in qualified:
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

    priority = _priority(
        deleted_source_test=deleted_source_test,
        modified_source_test=modified_source_test,
        control_surface=control_surface,
        candidate_count=len(qualified),
        recovery_signal=recovery_signal,
        lineage_mode=lineage_mode,
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
        reachable_from_target=_reachable(repo, resolved_sha, target_sha),
        lineage_mode=lineage_mode,
        lineage_base_sha=lineage_base,
        observed_candidate_count=len(archaeology.candidates),
        candidate_count=len(qualified),
        excluded_baseline_count=excluded,
        deleted_source_test_count=deleted_source_test,
        modified_source_test_count=modified_source_test,
        control_surface_count=control_surface,
        documentation_count=documentation,
        total_donor_bytes=total_donor_bytes,
        recovery_signal=round(recovery_signal, 6),
        priority_score=priority,
        disposition=_disposition(deleted_source_test, modified_source_test, len(qualified)),
        qualified_paths=tuple(sorted(candidate.path for candidate in qualified)),
        top_paths=tuple(path for _, path in ranked_paths[:8]),
        blocker=None,
    )


def _compose_intelligent_summary(
    repo: Path,
    rows: Sequence[DonorReconnaissance],
    *,
    target_sha: str,
    max_auto_actions: int,
) -> dict[str, object] | None:
    """Compose per-donor lineage-scoped plans without cross-donor path leakage."""
    candidates: dict[tuple[str, str], IntelligentRecoveryCandidate] = {}
    contributing_donors = 0
    for row in rows:
        if row.resolved_sha is None or not row.qualified_paths:
            continue
        plan = build_intelligent_recovery_plan(
            repo,
            donor_refs=(row.resolved_sha,),
            target_ref=target_sha,
            include_paths=row.qualified_paths,
            max_auto_actions=max_auto_actions,
        )
        contributing_donors += 1
        for candidate in plan.candidates:
            key = (candidate.path, candidate.donor_blob_sha256)
            incumbent = candidates.get(key)
            if incumbent is None or (
                candidate.capability_value,
                -candidate.preservation_risk,
                candidate.confidence,
            ) > (
                incumbent.capability_value,
                -incumbent.preservation_risk,
                incumbent.confidence,
            ):
                candidates[key] = candidate

    if not candidates:
        return None
    ranked = sorted(
        candidates.values(),
        key=lambda item: (
            not item.auto_recoverable,
            -item.capability_value,
            item.preservation_risk,
            -item.confidence,
            item.path,
        ),
    )
    auto = [item for item in ranked if item.auto_recoverable][:max_auto_actions]
    mode_counts = Counter(item.mode for item in ranked)
    role_counts = Counter(item.role for item in ranked)
    payload: dict[str, object] = {
        "schema": "glaciereq.lineage-scoped-intelligent-recovery-summary.v1",
        "target_sha": target_sha,
        "donor_count": contributing_donors,
        "candidate_count": len(ranked),
        "auto_recoverable_count": len(auto),
        "review_count": len(ranked) - len(auto),
        "mode_counts": dict(sorted(mode_counts.items())),
        "role_counts": dict(sorted(role_counts.items())),
        "top_candidates": [
            {
                "candidate_id": item.candidate_id,
                "path": item.path,
                "donor_sha": item.donor_sha,
                "mode": item.mode,
                "capability_value": item.capability_value,
                "preservation_risk": item.preservation_risk,
                "confidence": item.confidence,
                "auto_recoverable": item.auto_recoverable,
            }
            for item in ranked[:10]
        ],
    }
    payload["receipt_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return payload


def build_recovery_reconnaissance(
    repo: Path,
    *,
    donors: Sequence[HistoricalDonor],
    target_ref: str = "HEAD",
    fetch_missing: bool = False,
    remote: str = "origin",
    max_auto_actions: int = 8,
) -> RecoveryReconnaissanceReport:
    """Rank exact historical donors and compose lineage-scoped recovery intelligence."""
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
        key=lambda row: (
            row.disposition == "UNAVAILABLE",
            -row.priority_score,
            -row.deleted_source_test_count,
            -row.modified_source_test_count,
            row.name,
        )
    )
    available_shas = tuple(
        dict.fromkeys(
            row.resolved_sha
            for row in rows
            if row.resolved_sha is not None and row.candidate_count > 0
        )
    )
    plan_summary = _compose_intelligent_summary(
        repo,
        rows,
        target_sha=target_sha,
        max_auto_actions=max_auto_actions,
    )
    repository = _git(repo, "config", "--get", "remote.origin.url", check=False).stdout.strip()
    repository = repository or str(repo)
    payload = {
        "schema": "glaciereq.recovery-reconnaissance.v2",
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
    """Discover, lineage-qualify, rank, and plan from a historical-ref manifest."""
    return build_recovery_reconnaissance(
        repo,
        donors=load_historical_donors(manifest_path),
        target_ref=target_ref,
        fetch_missing=fetch_missing,
        remote=remote,
        max_auto_actions=max_auto_actions,
    )
