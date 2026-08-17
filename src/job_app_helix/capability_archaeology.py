"""Exact-source capability archaeology for targeted restoration work.

This module treats Git history as evidence, not authority. It identifies files that
were deleted or materially changed between a donor revision and the current target,
extracts exact donor blobs, and ranks recoverable mechanisms without reverting the
repository wholesale.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


class ArchaeologyError(RuntimeError):
    """Raised when repository evidence cannot be resolved exactly."""


@dataclass(frozen=True)
class CapabilityCandidate:
    path: str
    status: str
    donor_sha: str
    target_sha: str
    donor_blob_sha256: str
    target_blob_sha256: str | None
    donor_size: int
    target_size: int | None
    recovery_score: float
    reason: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ArchaeologyReport:
    repository: str
    donor_sha: str
    target_sha: str
    candidates: tuple[CapabilityCandidate, ...]
    receipt_sha256: str

    def to_dict(self) -> dict[str, object]:
        return {
            "repository": self.repository,
            "donor_sha": self.donor_sha,
            "target_sha": self.target_sha,
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "receipt_sha256": self.receipt_sha256,
        }


def _git(repo: Path, *args: str, check: bool = True) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if check and proc.returncode != 0:
        detail = proc.stderr.strip() or proc.stdout.strip() or "unknown git failure"
        raise ArchaeologyError(f"git {' '.join(args)} failed: {detail}")
    return proc.stdout


def resolve_commit(repo: Path, ref: str) -> str:
    return _git(repo, "rev-parse", "--verify", f"{ref}^{{commit}}").strip()


def repository_identity(repo: Path) -> str:
    remote = _git(repo, "config", "--get", "remote.origin.url", check=False).strip()
    return remote or str(repo.resolve())


def _blob(repo: Path, sha: str, path: str) -> bytes | None:
    proc = subprocess.run(
        ["git", "-C", str(repo), "show", f"{sha}:{path}"],
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        return None
    return proc.stdout


def _hash(blob: bytes | None) -> str | None:
    return hashlib.sha256(blob).hexdigest() if blob is not None else None


def _name_status(repo: Path, donor_sha: str, target_sha: str) -> Iterable[tuple[str, str]]:
    output = _git(repo, "diff", "--name-status", "--find-renames", donor_sha, target_sha)
    for raw in output.splitlines():
        if not raw.strip():
            continue
        fields = raw.split("\t")
        status = fields[0]
        if status.startswith("R") and len(fields) >= 3:
            yield status, fields[1]
            continue
        if len(fields) >= 2:
            yield status, fields[1]


def _score(status: str, donor: bytes, target: bytes | None) -> tuple[float, str]:
    if status == "D" or target is None:
        return 1.0, "present in donor and absent at target; strongest direct restoration signal"
    donor_size = max(1, len(donor))
    target_size = len(target)
    shrink = max(0.0, (donor_size - target_size) / donor_size)
    if status.startswith("R"):
        return min(0.98, 0.72 + 0.20 * shrink), "renamed lineage with recoverable donor implementation"
    if status == "M":
        return min(0.95, 0.58 + 0.32 * shrink), "materially changed lineage; inspect donor mechanism against later gains"
    return 0.45, "historical difference may contain reusable mechanism"


def excavate(
    repo: Path,
    *,
    donor_ref: str,
    target_ref: str = "HEAD",
    include_paths: tuple[str, ...] = (),
) -> ArchaeologyReport:
    """Find exact donor mechanisms that diverged from a target revision.

    ``include_paths`` is a prefix allow-list. Empty means inspect every changed path.
    Generated output is deterministic for the same repository state and refs.
    """
    repo = repo.resolve()
    donor_sha = resolve_commit(repo, donor_ref)
    target_sha = resolve_commit(repo, target_ref)
    candidates: list[CapabilityCandidate] = []

    for status, path in _name_status(repo, donor_sha, target_sha):
        if include_paths and not any(path == prefix or path.startswith(f"{prefix}/") for prefix in include_paths):
            continue
        donor = _blob(repo, donor_sha, path)
        if donor is None:
            continue
        target = _blob(repo, target_sha, path)
        score, reason = _score(status, donor, target)
        candidates.append(
            CapabilityCandidate(
                path=path,
                status=status,
                donor_sha=donor_sha,
                target_sha=target_sha,
                donor_blob_sha256=_hash(donor) or "",
                target_blob_sha256=_hash(target),
                donor_size=len(donor),
                target_size=len(target) if target is not None else None,
                recovery_score=round(score, 6),
                reason=reason,
            )
        )

    candidates.sort(key=lambda item: (-item.recovery_score, item.path))
    payload = {
        "repository": repository_identity(repo),
        "donor_sha": donor_sha,
        "target_sha": target_sha,
        "candidates": [candidate.to_dict() for candidate in candidates],
    }
    receipt = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return ArchaeologyReport(
        repository=payload["repository"],
        donor_sha=donor_sha,
        target_sha=target_sha,
        candidates=tuple(candidates),
        receipt_sha256=receipt,
    )


def read_donor_blob(repo: Path, *, donor_sha: str, path: str) -> bytes:
    blob = _blob(repo.resolve(), donor_sha, path)
    if blob is None:
        raise ArchaeologyError(f"donor blob missing: {donor_sha}:{path}")
    return blob
