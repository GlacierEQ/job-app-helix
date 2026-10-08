#!/usr/bin/env python3
"""Migrate legacy repo-excellence authority projections without deleting evidence.

The migration is additive and reversible:
- active machine state loses project-authority-shaped gates;
- original gate payloads remain under historical_legacy_gates;
- transition history remains intact and is explicitly typed as historical evidence;
- legacy machine promotion grants are preserved byte-for-byte under machine/historical/;
- the active promotion-authority compatibility file becomes evidence-only metadata.

Dry-run is the default. Pass --apply to write changes.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


LEGACY_ACTIVE_GATES = (
    "AUTHORITY_BOUND",
    "CANONICAL_POSITION_RESOLVED",
)
LEGACY_HISTORY_GATES = frozenset(LEGACY_ACTIVE_GATES)


def _stable_json_bytes(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(
        dict(payload),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")


def migrate_state_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    migrated = copy.deepcopy(dict(payload))
    gates = migrated.get("gates")
    if not isinstance(gates, dict):
        gates = {}
        migrated["gates"] = gates

    historical = migrated.get("historical_legacy_gates")
    if not isinstance(historical, dict):
        historical = {}

    for gate in LEGACY_ACTIVE_GATES:
        if gate in gates:
            historical.setdefault(gate, copy.deepcopy(gates.pop(gate)))

    if historical:
        migrated["historical_legacy_gates"] = historical
        migrated["historical_legacy_gate_semantics"] = (
            "Preserved technical evidence only. Historical authority/canonical-position "
            "labels do not create project direction, lifecycle permission, release "
            "authority, cross-repository authority, or asset disposition power."
        )

    history = migrated.get("history")
    if isinstance(history, list):
        for event in history:
            if not isinstance(event, dict):
                continue
            if event.get("gate") in LEGACY_HISTORY_GATES:
                event.setdefault(
                    "historical_semantics",
                    "technical evidence only; no project authority",
                )

    migrated["project_direction_authority"] = "OPERATOR"
    migrated["machine_state_creates_project_authority"] = False
    migrated["compatibility_semantics"] = {
        **(
            migrated.get("compatibility_semantics")
            if isinstance(migrated.get("compatibility_semantics"), dict)
            else {}
        ),
        "PROMOTED": "evidence_bounded_outward_claim_readiness_only",
        "CANONICAL": "historical/current-selection compatibility label only; never project authority",
    }
    migrated["retirement_authorized_by_machine_state"] = False
    migrated["remote_ref_deletion_authorized_by_machine_state"] = False
    return migrated


def migrate_grant_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    raw = dict(payload)
    return {
        "schema": "glaciereq.promotion-proof-compatibility.v2",
        "status": "EVIDENCE_BOUND_NON_AUTHORITATIVE",
        "repository": raw.get("repository"),
        "source_sha": raw.get("source_sha"),
        "proof_receipt_digest": raw.get("proof_receipt_digest"),
        "project_direction_authority": False,
        "repository_lifecycle_authority": False,
        "cross_repository_authority": False,
        "merge_or_release_authority": False,
        "technical_meaning": (
            "Legacy proof-binding metadata preserved for compatibility. Verification "
            "of this record cannot authorize project direction, promotion, merge, "
            "release, retirement, repository disposition, or cross-repository action."
        ),
        "legacy_record_sha256": hashlib.sha256(_stable_json_bytes(raw)).hexdigest(),
        "legacy_fields_preserved_in_history": sorted(raw),
    }


def _load_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected JSON object")
    return payload


def migrate_leaf(leaf: Path, *, apply: bool) -> dict[str, Any]:
    machine = leaf / "machine"
    state_path = machine / "excellence-state.json"
    grant_path = machine / "promotion_authority.json"
    result: dict[str, Any] = {
        "leaf": leaf.name,
        "state_found": state_path.is_file(),
        "grant_found": grant_path.is_file(),
        "state_changed": False,
        "grant_changed": False,
        "historical_grant_preserved": False,
    }

    if state_path.is_file():
        original = _load_object(state_path)
        migrated = migrate_state_payload(original)
        result["state_changed"] = migrated != original
        if apply and migrated != original:
            state_path.write_text(json.dumps(migrated, indent=2) + "\n", encoding="utf-8")

    if grant_path.is_file():
        original_grant = _load_object(grant_path)
        already_safe = original_grant.get("status") == "EVIDENCE_BOUND_NON_AUTHORITATIVE"
        if not already_safe:
            historical_dir = machine / "historical"
            historical_path = historical_dir / "promotion_authority_legacy.json"
            safe = migrate_grant_payload(original_grant)
            result["grant_changed"] = safe != original_grant
            result["historical_grant_path"] = str(historical_path)
            if apply:
                historical_dir.mkdir(parents=True, exist_ok=True)
                if not historical_path.exists():
                    historical_path.write_text(
                        json.dumps(original_grant, indent=2) + "\n",
                        encoding="utf-8",
                    )
                grant_path.write_text(json.dumps(safe, indent=2) + "\n", encoding="utf-8")
                result["historical_grant_preserved"] = True

    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("repos"))
    parser.add_argument("--apply", action="store_true")
    parser.add_argument(
        "--receipt",
        type=Path,
        default=Path("excellence/receipts/legacy_authority_migration_latest.json"),
    )
    args = parser.parse_args()

    leaves = sorted(path for path in args.root.iterdir() if path.is_dir())
    results = [migrate_leaf(leaf, apply=args.apply) for leaf in leaves]
    summary = {
        "schema": "glaciereq.legacy-authority-migration.v1",
        "mode": "APPLY" if args.apply else "DRY_RUN",
        "root": str(args.root),
        "project_direction_authority": "OPERATOR",
        "machine_project_direction_authority": False,
        "leaf_count": len(results),
        "state_changes": sum(bool(item["state_changed"]) for item in results),
        "grant_changes": sum(bool(item["grant_changed"]) for item in results),
        "results": results,
    }
    print(json.dumps(summary, indent=2))
    if args.apply:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
