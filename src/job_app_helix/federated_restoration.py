"""Federated exact-source restoration across repository boundaries.

The local restoration stack can surgically compose historical Python capability, but
real GlacierEQ lineage frequently crosses repositories. This module imports one exact
donor revision into a namespaced, reachable Git ref inside the target repository, then
reuses the existing cross-file semantic engine without weakening its drift guards.

The imported ref is intentionally persistent: restoration packets remain reproducible
and applicable after archaeology instead of depending on an unreachable FETCH_HEAD or
objects that Git may garbage-collect.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from .capability_archaeology import ArchaeologyError, resolve_commit
from .cross_file_restoration import (
    CrossFileApplyReceipt,
    CrossFileRestorationPacket,
    apply_cross_file_packet,
    build_cross_file_packet,
    rollback_cross_file,
)
from .restoration_executor import RestorationError


@dataclass(frozen=True)
class DonorImportReceipt:
    donor_source: str
    requested_ref: str
    imported_ref: str
    donor_sha: str
    receipt_sha256: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class FederatedRestorationPacket:
    donor: DonorImportReceipt
    target_sha: str
    semantic_packet: CrossFileRestorationPacket
    packet_sha256: str

    def to_dict(self) -> dict[str, object]:
        return {
            "donor": self.donor.to_dict(),
            "target_sha": self.target_sha,
            "semantic_packet": self.semantic_packet.to_dict(),
            "packet_sha256": self.packet_sha256,
        }


@dataclass(frozen=True)
class FederatedApplyReceipt:
    packet_sha256: str
    donor_sha: str
    target_sha: str
    semantic_receipt: CrossFileApplyReceipt
    receipt_sha256: str

    def to_dict(self) -> dict[str, object]:
        return {
            "packet_sha256": self.packet_sha256,
            "donor_sha": self.donor_sha,
            "target_sha": self.target_sha,
            "semantic_receipt": self.semantic_receipt.to_dict(),
            "receipt_sha256": self.receipt_sha256,
        }


def _sha(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _git(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode:
        detail = proc.stderr.strip() or proc.stdout.strip() or "unknown git failure"
        raise ArchaeologyError(f"git {' '.join(args)} failed: {detail}")
    return proc.stdout.strip()


def _safe_source_identity(source: str | Path) -> str:
    """Return a stable donor identity without persisting URL credentials or queries."""
    raw = str(source)
    if isinstance(source, Path) or "://" not in raw:
        candidate = Path(raw).expanduser()
        if candidate.exists():
            return str(candidate.resolve())
        return raw
    parsed = urlsplit(raw)
    host = parsed.hostname or ""
    if parsed.port:
        host = f"{host}:{parsed.port}"
    return urlunsplit((parsed.scheme, host, parsed.path, "", ""))


def import_donor_revision(
    target_repo: Path,
    *,
    donor_source: str | Path,
    donor_ref: str,
) -> DonorImportReceipt:
    """Fetch one donor revision into a deterministic namespaced target-repository ref."""
    target_repo = target_repo.resolve()
    resolve_commit(target_repo, "HEAD")
    safe_source = _safe_source_identity(donor_source)
    source_key = hashlib.sha256(safe_source.encode()).hexdigest()[:16]
    staging_ref = f"refs/apex/donors/{source_key}/staging"

    # Fetch without a shell so repository/ref input cannot become command injection.
    _git(
        target_repo,
        "fetch",
        "--no-tags",
        "--force",
        str(donor_source),
        f"{donor_ref}:{staging_ref}",
    )
    donor_sha = resolve_commit(target_repo, staging_ref)
    imported_ref = f"refs/apex/donors/{source_key}/{donor_sha}"
    _git(target_repo, "update-ref", imported_ref, donor_sha)
    _git(target_repo, "update-ref", "-d", staging_ref)

    payload = {
        "donor_source": safe_source,
        "requested_ref": donor_ref,
        "imported_ref": imported_ref,
        "donor_sha": donor_sha,
    }
    return DonorImportReceipt(
        donor_source=safe_source,
        requested_ref=donor_ref,
        imported_ref=imported_ref,
        donor_sha=donor_sha,
        receipt_sha256=_sha(payload),
    )


def build_federated_packet(
    target_repo: Path,
    *,
    donor_source: str | Path,
    donor_ref: str,
    target_ref: str = "HEAD",
    root_path: str,
    selected_symbols: tuple[str, ...],
    allow_replace: bool = False,
    max_depth: int = 8,
) -> FederatedRestorationPacket:
    """Build recursive semantic closure from an exact revision in another repository."""
    target_repo = target_repo.resolve()
    donor = import_donor_revision(
        target_repo,
        donor_source=donor_source,
        donor_ref=donor_ref,
    )
    target_sha = resolve_commit(target_repo, target_ref)
    semantic_packet = build_cross_file_packet(
        target_repo,
        donor_ref=donor.imported_ref,
        target_ref=target_sha,
        root_path=root_path,
        selected_symbols=selected_symbols,
        allow_replace=allow_replace,
        max_depth=max_depth,
    )
    if semantic_packet.donor_sha != donor.donor_sha:
        raise ArchaeologyError("federated donor import SHA diverged during packet build")
    payload = {
        "donor": donor.to_dict(),
        "target_sha": target_sha,
        "semantic_packet": semantic_packet.to_dict(),
    }
    return FederatedRestorationPacket(
        donor=donor,
        target_sha=target_sha,
        semantic_packet=semantic_packet,
        packet_sha256=_sha(payload),
    )


def apply_federated_packet(
    target_repo: Path,
    packet: FederatedRestorationPacket,
) -> FederatedApplyReceipt:
    """Apply a federated packet after revalidating donor identity and target lineage."""
    target_repo = target_repo.resolve()
    current_donor = resolve_commit(target_repo, packet.donor.imported_ref)
    if current_donor != packet.donor.donor_sha:
        raise RestorationError(
            "federated donor ref drifted; rebuild the packet from the intended donor revision"
        )
    if packet.semantic_packet.donor_sha != packet.donor.donor_sha:
        raise RestorationError("semantic packet donor SHA does not match federated donor receipt")
    if packet.semantic_packet.target_sha != packet.target_sha:
        raise RestorationError("semantic packet target SHA does not match federated target receipt")

    semantic_receipt = apply_cross_file_packet(target_repo, packet.semantic_packet)
    payload = {
        "packet_sha256": packet.packet_sha256,
        "donor_sha": packet.donor.donor_sha,
        "target_sha": packet.target_sha,
        "semantic_receipt": semantic_receipt.to_dict(),
    }
    return FederatedApplyReceipt(
        packet_sha256=packet.packet_sha256,
        donor_sha=packet.donor.donor_sha,
        target_sha=packet.target_sha,
        semantic_receipt=semantic_receipt,
        receipt_sha256=_sha(payload),
    )


def rollback_federated(target_repo: Path, receipt: FederatedApplyReceipt) -> None:
    """Restore every touched target file to its exact pre-composition bytes."""
    rollback_cross_file(target_repo.resolve(), receipt.semantic_receipt)
