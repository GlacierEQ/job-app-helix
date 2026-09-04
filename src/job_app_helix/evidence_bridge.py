#!/usr/bin/env python3
"""
Evidence Bridge — Bridge job-app-helix evidence ledger to monolith legal spines and case evidence.

L0 Reference: Immutable byte/SHA/commit/docket provenance. Never assert unverified state without tool readback.
"""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

JOB_APP_HELIX_ROOT = Path("/data/data/com.termux/files/home/job-app-helix")
MONOLITH_ROOT = Path("/data/data/com.termux/files/home/monolith")


@dataclass
class EvidenceItem:
    id: str
    source_repo: str
    source_path: str
    content_hash: str
    evidence_type: str
    timestamp: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SpineEntry:
    spine_id: str
    case_id: str
    evidence_id: str
    content_hash: str
    bridge_hash: str
    timestamp: str
    provenance: dict[str, Any] = field(default_factory=dict)


@dataclass
class BridgeReceipt:
    evidence_item: EvidenceItem
    target_spine: str
    spine_entry: SpineEntry
    timestamp: str
    receipt_hash: str


def load_evidence_ledger() -> dict[str, Any]:
    ledger_path = JOB_APP_HELIX_ROOT / "manifests" / "evidence_ledger_unified.json"
    if ledger_path.exists():
        return json.loads(ledger_path.read_text())
    return {}


def load_monolith_legal_spines(spine_path: Path) -> dict[str, Any]:
    if spine_path.exists():
        return json.loads(spine_path.read_text())
    return {}


def compute_content_hash(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()


def bridge_evidence(evidence: EvidenceItem, target_spine: str, monolith_legal_path: Path) -> BridgeReceipt:
    spines = load_monolith_legal_spines(monolith_legal_path / f"{target_spine}.json")

    bridge_data = f"{evidence.id}:{evidence.content_hash}:{target_spine}:{datetime.now(timezone.utc).isoformat()}"
    bridge_hash = hashlib.sha256(bridge_data.encode()).hexdigest()

    spine_entry = SpineEntry(
        spine_id=target_spine,
        case_id=spines.get("case_id", "unknown"),
        evidence_id=evidence.id,
        content_hash=evidence.content_hash,
        bridge_hash=bridge_hash,
        timestamp=datetime.now(timezone.utc).isoformat(),
        provenance={
            "source_repo": evidence.source_repo,
            "source_path": evidence.source_path,
            "evidence_type": evidence.evidence_type,
            "original_timestamp": evidence.timestamp,
        },
    )

    receipt_data = f"{evidence.id}:{target_spine}:{bridge_hash}:{datetime.now(timezone.utc).isoformat()}"
    receipt_hash = hashlib.sha256(receipt_data.encode()).hexdigest()[:16]

    receipt = BridgeReceipt(
        evidence_item=evidence,
        target_spine=target_spine,
        spine_entry=spine_entry,
        timestamp=datetime.now(timezone.utc).isoformat(),
        receipt_hash=receipt_hash,
    )

    spines.setdefault("evidence", []).append(asdict(spine_entry))
    spines["last_bridged"] = datetime.now(timezone.utc).isoformat()

    (monolith_legal_path / f"{target_spine}.json").write_text(json.dumps(spines, indent=2))

    return receipt


def bridge_from_ledger(target_spine: str, monolith_legal_path: Path) -> list[BridgeReceipt]:
    ledger = load_evidence_ledger()
    receipts = []

    for item in ledger.get("entries", []):
        evidence = EvidenceItem(
            id=item.get("receipt_id", ""),
            source_repo=item.get("repo", ""),
            source_path=f"solidify_records/{item.get('repo', '')}.json",
            content_hash=item.get("evidence_hash", ""),
            evidence_type="portfolio_evidence",
            timestamp=item.get("timestamp", ""),
            metadata={"worthy": item.get("worthy", 0), "verified": item.get("verified", False)},
        )

        if evidence.content_hash and evidence.content_hash != "missing":
            receipt = bridge_evidence(evidence, target_spine, monolith_legal_path)
            receipts.append(receipt)

    return receipts


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Bridge evidence ledger to monolith legal spines")
    parser.add_argument("--evidence-id", help="Specific evidence ID to bridge")
    parser.add_argument("--target-spine", required=True, help="Target legal spine")
    parser.add_argument("--monolith-legal-path", default="/data/data/com.termux/files/home/monolith/catalog/legal_spines", help="Monolith legal spines path")
    parser.add_argument("--output", default="bridge_receipt.json", help="Output file")
    parser.add_argument("--all-from-ledger", action="store_true", help="Bridge all evidence from ledger")
    args = parser.parse_args()

    global MONOLITH_ROOT
    MONOLITH_ROOT = Path(args.monolith_legal_path).parent.parent

    receipts = []

    if args.all_from_ledger:
        receipts = bridge_from_ledger(args.target_spine, Path(args.monolith_legal_path))
    elif args.evidence_id:
        ledger = load_evidence_ledger()
        for item in ledger.get("entries", []):
            if item.get("receipt_id") == args.evidence_id:
                evidence = EvidenceItem(
                    id=item.get("receipt_id", ""),
                    source_repo=item.get("repo", ""),
                    source_path=f"solidify_records/{item.get('repo', '')}.json",
                    content_hash=item.get("evidence_hash", ""),
                    evidence_type="portfolio_evidence",
                    timestamp=item.get("timestamp", ""),
                )
                receipt = bridge_evidence(evidence, args.target_spine, Path(args.monolith_legal_path))
                receipts.append(receipt)
                break
    else:
        print("Error: Must specify --evidence-id or --all-from-ledger")
        return 1

    result = {
        "bridged_count": len(receipts),
        "receipts": [asdict(r) for r in receipts],
    }

    Path(args.output).write_text(json.dumps(result, indent=2))

    print(f"Bridged {len(receipts)} evidence items to spine '{args.target_spine}'")
    for r in receipts:
        print(f"  {r.evidence_item.id} -> {r.receipt_hash}")
    return 0


if __name__ == "__main__":
    sys.exit(main())