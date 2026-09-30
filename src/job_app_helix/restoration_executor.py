"""Deterministic, reversible restoration packets built from Git archaeology.

The executor applies only explicitly selected donor files. Existing target files are
protected by content preconditions, so later gains cannot be silently overwritten.
Whole-repository restoration is intentionally unsupported.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from .capability_archaeology import ArchaeologyError, CapabilityCandidate, read_donor_blob


class RestorationError(RuntimeError):
    """Raised when a restoration violates packet or target preconditions."""


@dataclass(frozen=True)
class RestorationAction:
    path: str
    donor_sha: str
    donor_blob_sha256: str
    expected_target_sha256: str | None
    mode: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class RestorationPacket:
    donor_sha: str
    target_sha: str
    actions: tuple[RestorationAction, ...]
    packet_sha256: str

    def to_dict(self) -> dict[str, object]:
        return {
            "donor_sha": self.donor_sha,
            "target_sha": self.target_sha,
            "actions": [action.to_dict() for action in self.actions],
            "packet_sha256": self.packet_sha256,
        }


@dataclass(frozen=True)
class ApplyReceipt:
    packet_sha256: str
    restored_paths: tuple[str, ...]
    backups: dict[str, str | None]
    receipt_sha256: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _file_sha(path: Path) -> str | None:
    if not path.exists():
        return None
    if not path.is_file():
        raise RestorationError(f"target is not a regular file: {path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_packet(
    candidates: tuple[CapabilityCandidate, ...],
    *,
    selected_paths: tuple[str, ...],
    allow_replace: bool = False,
) -> RestorationPacket:
    """Materialize an exact restoration packet from selected archaeology results.

    By default, only files absent from the target may be restored. Replacing an
    existing file requires explicit ``allow_replace`` and captures its expected hash.
    """
    if not selected_paths:
        raise RestorationError("selected_paths cannot be empty")
    by_path = {candidate.path: candidate for candidate in candidates}
    unknown = sorted(set(selected_paths) - set(by_path))
    if unknown:
        raise RestorationError(f"selected paths not present in archaeology report: {unknown}")

    chosen: list[RestorationAction] = []
    for path in sorted(set(selected_paths)):
        candidate = by_path[path]
        if candidate.target_blob_sha256 is not None and not allow_replace:
            raise RestorationError(
                f"refusing to overwrite later target capability at {path}; "
                "pass allow_replace=True only after explicit composition review"
            )
        chosen.append(
            RestorationAction(
                path=path,
                donor_sha=candidate.donor_sha,
                donor_blob_sha256=candidate.donor_blob_sha256,
                expected_target_sha256=candidate.target_blob_sha256,
                mode="replace" if candidate.target_blob_sha256 is not None else "restore_missing",
            )
        )

    donor_shas = {action.donor_sha for action in chosen}
    target_shas = {by_path[action.path].target_sha for action in chosen}
    if len(donor_shas) != 1 or len(target_shas) != 1:
        raise RestorationError("one packet must bind to exactly one donor and one target revision")

    payload = {
        "donor_sha": next(iter(donor_shas)),
        "target_sha": next(iter(target_shas)),
        "actions": [action.to_dict() for action in chosen],
    }
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return RestorationPacket(
        donor_sha=payload["donor_sha"],
        target_sha=payload["target_sha"],
        actions=tuple(chosen),
        packet_sha256=digest,
    )


def apply_packet(repo: Path, packet: RestorationPacket) -> ApplyReceipt:
    """Apply selected donor blobs with fail-closed target and donor hash checks.

    The caller owns the Git branch. This function mutates only packet paths and emits
    enough backup data to restore pre-apply content exactly within the same process.
    """
    repo = repo.resolve()
    backups: dict[str, str | None] = {}
    restored: list[str] = []

    for action in packet.actions:
        target = repo / action.path
        current_sha = _file_sha(target)
        if current_sha != action.expected_target_sha256:
            raise RestorationError(
                f"target drift at {action.path}: expected {action.expected_target_sha256}, "
                f"observed {current_sha}"
            )
        donor = read_donor_blob(repo, donor_sha=action.donor_sha, path=action.path)
        donor_sha = hashlib.sha256(donor).hexdigest()
        if donor_sha != action.donor_blob_sha256:
            message = (
                f"donor drift at {action.path}: expected {action.donor_blob_sha256}, "
                f"observed {donor_sha}"
            )
            raise ArchaeologyError(message)

        backups[action.path] = target.read_bytes().hex() if target.exists() else None
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(donor)
        restored.append(action.path)

    payload = {
        "packet_sha256": packet.packet_sha256,
        "restored_paths": sorted(restored),
        "backups": backups,
    }
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return ApplyReceipt(
        packet_sha256=packet.packet_sha256,
        restored_paths=tuple(sorted(restored)),
        backups=backups,
        receipt_sha256=digest,
    )


def rollback(repo: Path, receipt: ApplyReceipt) -> None:
    """Restore the exact pre-apply bytes represented by an apply receipt."""
    repo = repo.resolve()
    for path, encoded in receipt.backups.items():
        target = repo / path
        if encoded is None:
            if target.exists():
                target.unlink()
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(bytes.fromhex(encoded))
