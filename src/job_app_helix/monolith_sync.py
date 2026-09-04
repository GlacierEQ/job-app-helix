#!/usr/bin/env python3
"""
Monolith Catalog Sync — Sync portfolio state to monolith catalog (capabilities_3layer, runtime_power_spine, library).

L3 Backend Awareness: Deep substrate comprehension — SQLite indices, event loop concurrency, OS process limits.
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
class SyncReceipt:
    timestamp: str
    mode: str
    updated_catalogs: list[str]
    conflicts: list[dict[str, Any]]
    repo_count: int
    receipt_hash: str


def load_portfolio_manifest() -> dict[str, Any]:
    manifest_path = JOB_APP_HELIX_ROOT / "manifests" / "unified_deserving_manifest.json"
    if manifest_path.exists():
        data = json.loads(manifest_path.read_text())
        # Transform 'repositories' to 'deserving' for compatibility
        if "repositories" in data and "deserving" not in data:
            data["deserving"] = data["repositories"]
        return data
    return {}


def load_solidify_records() -> dict[str, Any]:
    solidify_dir = JOB_APP_HELIX_ROOT / "solidify_records"
    records = {}
    if solidify_dir.exists():
        for f in solidify_dir.glob("*.json"):
            try:
                records[f.stem] = json.loads(f.read_text())
            except Exception:
                pass
    return records


def load_monolith_catalog(name: str) -> dict[str, Any]:
    catalog_path = MONOLITH_ROOT / "catalog" / name
    if catalog_path.exists():
        return json.loads(catalog_path.read_text())
    return {}


def write_monolith_catalog(name: str, data: dict[str, Any]) -> None:
    catalog_path = MONOLITH_ROOT / "catalog" / name
    catalog_path.write_text(json.dumps(data, indent=2))


def sync_capabilities_3layer(portfolio: dict[str, Any], solidify: dict[str, Any], mode: str) -> dict[str, Any]:
    existing = load_monolith_catalog("capabilities_3layer.json")
    layers = existing.get("layers", {})

    if mode == "full" or "portfolio" not in layers:
        layers["portfolio"] = {"repositories": []}

    portfolio_layer = layers["portfolio"]
    existing_repos = {r.get("name"): r for r in portfolio_layer.get("repositories", [])}

    deserving = portfolio.get("deserving", [])
    for repo_data in deserving:
        repo_name = repo_data.get("repo", "")
        solidify_record = solidify.get(repo_name, {})

        repo_entry = {
            "name": repo_name,
            "family": repo_data.get("family", "unknown"),
            "domain": repo_data.get("domain", "general"),
            "description": solidify_record.get("innovation_summary", repo_data.get("description", "")),
            "entrypoint": solidify_record.get("entrypoint", ""),
            "interface": "library|cli",
            "verified": repo_data.get("worthy", 0) >= 8,
            "worthy": repo_data.get("worthy", 0),
            "source_state": repo_data.get("source_state", "unknown"),
            "evidence_hash": solidify_record.get("evidence_hash", ""),
            "last_synced": datetime.now(timezone.utc).isoformat(),
        }

        if mode == "incremental" and repo_name in existing_repos:
            existing_entry = existing_repos[repo_name]
            if existing_entry.get("evidence_hash") == repo_entry["evidence_hash"]:
                continue

        existing_repos[repo_name] = repo_entry

    portfolio_layer["repositories"] = list(existing_repos.values())
    return {"layers": layers}


def sync_runtime_power_spine(portfolio: dict[str, Any], mode: str) -> dict[str, Any]:
    existing = load_monolith_catalog("runtime_power_spine.json")

    verified_anchors = [r for r in portfolio.get("deserving", []) if r.get("worthy", 0) >= 8]

    spine_entry = {
        "source": "job-app-helix",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "verified_anchors": len(verified_anchors),
        "total_repos": len(portfolio.get("deserving", [])),
        "anchor_details": [
            {
                "repo": r.get("repo"),
                "family": r.get("family"),
                "worthy": r.get("worthy"),
                "gates": solidify.get(r.get("repo"), {}).get("gates", "unknown"),
            }
            for r in verified_anchors
        ],
    }

    if "sources" not in existing:
        existing["sources"] = []

    if mode == "full":
        existing["sources"] = [spine_entry]
    else:
        existing["sources"] = [s for s in existing["sources"] if s.get("source") != "job-app-helix"]
        existing["sources"].append(spine_entry)

    return existing


def sync_library(portfolio: dict[str, Any], mode: str) -> dict[str, Any]:
    existing = load_monolith_catalog("library.json")

    families = {}
    for repo in portfolio.get("deserving", []):
        family = repo.get("family", "unknown")
        if family not in families:
            families[family] = {"repos": [], "count": 0}
        families[family]["repos"].append(repo.get("repo"))
        families[family]["count"] += 1

    if "families" not in existing:
        existing["families"] = {}

    if mode == "full":
        existing["families"] = families
    else:
        existing["families"].update(families)

    return existing


def sync_repo_excellence_state_machine(portfolio: dict[str, Any], mode: str) -> dict[str, Any]:
    existing = load_monolith_catalog("repo_excellence_state_machine.json")

    if "portfolio_state" not in existing:
        existing["portfolio_state"] = {}

    existing["portfolio_state"]["job-app-helix"] = {
        "last_sync": datetime.now(timezone.utc).isoformat(),
        "total_deserving": len(portfolio.get("deserving", [])),
        "verified_anchors": len([r for r in portfolio.get("deserving", []) if r.get("worthy", 0) >= 8]),
        "mode": mode,
    }

    return existing


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Sync portfolio state to monolith catalog")
    parser.add_argument("--monolith-root", default="/data/data/com.termux/files/home/monolith", help="Monolith root path")
    parser.add_argument("--portfolio-manifest", default="/data/data/com.termux/files/home/job-app-helix/manifests/unified_deserving_manifest.json", help="Portfolio manifest")
    parser.add_argument("--mode", choices=["full", "incremental", "verify"], default="incremental", help="Sync mode")
    parser.add_argument("--output", default="sync_receipt.json", help="Output receipt file")
    args = parser.parse_args()

    global MONOLITH_ROOT
    MONOLITH_ROOT = Path(args.monolith_root)

    portfolio = load_portfolio_manifest()
    solidify = load_solidify_records()

    updated = []
    conflicts = []

    if args.mode != "verify":
        caps_3layer = sync_capabilities_3layer(portfolio, solidify, args.mode)
        write_monolith_catalog("capabilities_3layer.json", caps_3layer)
        updated.append("capabilities_3layer.json")

        spine = sync_runtime_power_spine(portfolio, args.mode)
        write_monolith_catalog("runtime_power_spine.json", spine)
        updated.append("runtime_power_spine.json")

        library = sync_library(portfolio, args.mode)
        write_monolith_catalog("library.json", library)
        updated.append("library.json")

        state_machine = sync_repo_excellence_state_machine(portfolio, args.mode)
        write_monolith_catalog("repo_excellence_state_machine.json", state_machine)
        updated.append("repo_excellence_state_machine.json")

    receipt_data = f"{args.mode}:{len(updated)}:{datetime.now(timezone.utc).isoformat()}"
    receipt_hash = hashlib.sha256(receipt_data.encode()).hexdigest()[:16]

    receipt = SyncReceipt(
        timestamp=datetime.now(timezone.utc).isoformat(),
        mode=args.mode,
        updated_catalogs=updated,
        conflicts=conflicts,
        repo_count=len(portfolio.get("deserving", [])),
        receipt_hash=receipt_hash,
    )

    Path(args.output).write_text(json.dumps(asdict(receipt), indent=2))

    print(f"Sync {args.mode}: updated {len(updated)} catalogs, {receipt.repo_count} repos")
    print(f"Receipt: {receipt_hash}")
    return 0


if __name__ == "__main__":
    sys.exit(main())