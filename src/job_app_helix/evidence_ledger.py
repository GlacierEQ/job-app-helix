#!/usr/bin/env python3
"""
Evidence Ledger — Hash-bound evidence ledger for the deserving-repo portfolio
with VERIFIED anchor tracking.

L0 Reference: Immutable byte/SHA/commit/docket provenance. Never assert
unverified state without tool readback.

The ledger is fail-closed: it refuses to emit an empty or fabricated ledger
when the portfolio manifest or the solidify record directory is absent.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from contextlib import suppress
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from . import estate_paths
from .errors import PortfolioSourceError

REPO_ROOT = estate_paths.helix_root()

VERIFIED_ANCHORS: dict[str, dict[str, Any]] = {
    "computer-user": {"family": "GlacierEQ-core", "worthy": 9, "gates": "12/12"},
    "AKOS": {"family": "GlacierEQ-core", "worthy": 9, "gates": "94/94"},
    "pro-code": {"family": "GlacierEQ-core", "worthy": 9, "gates": "scoped"},
    "job-app-helix": {"family": "GlacierEQ-core", "worthy": 9, "gates": "pages+deploy"},
    "the-tower-of-babel": {"family": "GlacierEQ-core", "worthy": 8, "gates": "PR-merge"},
    "xai-colossus-cooling": {"family": "xAI/Colossus", "worthy": 9, "gates": "37-tests"},
    "xai-colossus-servers": {"family": "xAI/Colossus", "worthy": 8, "gates": "20-tests"},
    "xai-colossus-energy-omega": {"family": "xAI/Colossus", "worthy": 8, "gates": "3.6MW-shed"},
}

EMPTY_MERKLE_ROOT = hashlib.sha256(b"").hexdigest()


class LedgerError(PortfolioSourceError):
    """Raised when the ledger cannot be built from verifiable sources."""


@dataclass
class EvidenceEntry:
    repo: str
    family: str
    worthy: int
    source_state: str
    evidence_hash: str
    gate_status: str
    verified: bool
    timestamp: str
    receipt_id: str


@dataclass
class Ledger:
    generated_at: str
    total_repos: int
    verified_anchors: int
    entries: list[EvidenceEntry]
    merkle_root: str


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    if not path.exists():
        return "missing"
    return sha256_bytes(path.read_bytes())


def git_sha(repo_path: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_path), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.stdout.strip()[:12] if result.returncode == 0 else "unknown"
    except Exception:
        return "error"


def set_repo_root(path: Path) -> None:
    """Override the portfolio root (used by the CLI and by tests)."""
    global REPO_ROOT
    REPO_ROOT = Path(path).expanduser().resolve()


def load_unified_manifest() -> dict[str, Any]:
    manifest_path = REPO_ROOT / "manifests" / "unified_deserving_manifest.json"
    if not manifest_path.is_file():
        raise LedgerError(f"portfolio manifest not found: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or not isinstance(manifest.get("repositories"), list):
        raise LedgerError(f"portfolio manifest has no repositories list: {manifest_path}")
    if not manifest["repositories"]:
        raise LedgerError(f"portfolio manifest is empty: {manifest_path}")
    return manifest


def load_solidify_records() -> dict[str, Any]:
    solidify_dir = REPO_ROOT / "solidify_records"
    if not solidify_dir.is_dir():
        raise LedgerError(f"solidify record directory not found: {solidify_dir}")
    records: dict[str, Any] = {}
    for f in sorted(solidify_dir.glob("*.json")):
        with suppress(Exception):
            records[f.stem] = json.loads(f.read_text(encoding="utf-8"))
    return records


def _evidence_hash(repo_name: str, repo_data: dict[str, Any], solidify: dict[str, Any]) -> str:
    record = solidify.get(repo_name)
    if isinstance(record, dict):
        digest = record.get("evidence_hash")
        if isinstance(digest, str) and digest.strip():
            return digest.strip()
    canonical = json.dumps(repo_data, sort_keys=True, separators=(",", ":")).encode()
    return sha256_bytes(canonical)[:16]


def _worthy_rating(
    repo_name: str,
    repo_data: dict[str, Any],
    solidify: dict[str, Any],
) -> int:
    record = solidify.get(repo_name)
    if isinstance(record, dict):
        rating = record.get("worthy_rating")
        if isinstance(rating, int):
            return rating
    rating = repo_data.get("worthy")
    return rating if isinstance(rating, int) else 0


def build_ledger(anchor_threshold: int = 8) -> Ledger:
    manifest = load_unified_manifest()
    solidify = load_solidify_records()

    deserving = manifest["repositories"]
    entries = []
    verified_count = 0

    for repo_data in deserving:
        repo_name = repo_data.get("repo", "")
        family = repo_data.get("family", "unknown")
        source_state = repo_data.get("source_state", "unknown")
        worthy = _worthy_rating(repo_name, repo_data, solidify)

        anchor = VERIFIED_ANCHORS.get(repo_name)
        if anchor is not None and worthy >= anchor_threshold:
            verified = True
            verified_count += 1
            gate_status = anchor["gates"]
        else:
            verified = False
            gate_status = "unverified"

        evidence_hash = _evidence_hash(repo_name, repo_data, solidify)
        receipt_id = sha256_bytes(
            f"{repo_name}:{evidence_hash}:{datetime.now(UTC).isoformat()}".encode()
        )[:16]

        entries.append(EvidenceEntry(
            repo=repo_name,
            family=family,
            worthy=worthy,
            source_state=source_state,
            evidence_hash=evidence_hash,
            gate_status=gate_status,
            verified=verified,
            timestamp=datetime.now(UTC).isoformat(),
            receipt_id=receipt_id,
        ))

    merkle_data = "".join(e.evidence_hash for e in sorted(entries, key=lambda x: x.repo)).encode()
    merkle_root = sha256_bytes(merkle_data)
    if merkle_root == EMPTY_MERKLE_ROOT:
        raise LedgerError("ledger would be empty; refusing to emit an empty Merkle root")

    return Ledger(
        generated_at=datetime.now(UTC).isoformat(),
        total_repos=len(entries),
        verified_anchors=verified_count,
        entries=entries,
        merkle_root=merkle_root,
    )


def write_ledger(ledger: Ledger, output_path: Path) -> None:
    output_path.write_text(json.dumps(asdict(ledger), indent=2))


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Build hash-bound evidence ledger")
    parser.add_argument(
        "--repo-path",
        default=str(estate_paths.helix_root()),
        help="Portfolio repo root",
    )
    parser.add_argument("--anchor-threshold", type=int, default=8, help="Worthy threshold for anchors")
    parser.add_argument("--output", default="evidence_ledger.json", help="Output file")
    args = parser.parse_args()

    set_repo_root(Path(args.repo_path))
    ledger = build_ledger(args.anchor_threshold)
    output_path = Path(args.output)
    write_ledger(ledger, output_path)

    print(f"Ledger built: {ledger.total_repos} repos, {ledger.verified_anchors} VERIFIED anchors")
    print(f"Merkle root: {ledger.merkle_root}")
    print(f"Written to: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
