#!/usr/bin/env python3
"""Validate the canonical GlacierEQ portfolio root and emit a deterministic receipt."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
ROOT_MANIFEST = ROOT / "manifests" / "portfolio_root_truth.json"
ROOT_SCHEMA = ROOT / "schemas" / "portfolio_root_truth.schema.json"
RECRUITER_ELIGIBLE_STATES = {"PROMOTED", "REFERENCE_ONLY"}
PUBLIC_NON_RECRUITER_STATES = {
    "QUARANTINED",
    "EXCLUDED",
    "BLOCKED",
    "BLOCKED_SECURITY",
    "BLOCKED_PUBLIC",
    "EXCLUDED_AUTHORSHIP",
    "AUDIT_BEFORE_ADMISSION",
    "AUDIT_UPSTREAM_DELTA",
    "ARCHIVE",
}


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"missing required JSON file: {path.relative_to(ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {path.relative_to(ROOT)}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"expected object in {path.relative_to(ROOT)}")
    return value


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    ).encode("utf-8")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def repository_file(relative: str, label: str) -> Path:
    candidate = ROOT / relative
    try:
        resolved = candidate.resolve(strict=True)
    except FileNotFoundError as exc:
        raise ValueError(f"missing {label}: {relative}") from exc
    require(resolved.is_relative_to(ROOT), f"{label} escapes repository root: {relative}")
    require(resolved.is_file(), f"{label} is not a file: {relative}")
    return resolved


def validate_schema(manifest: dict[str, Any]) -> None:
    schema = load_json(ROOT_SCHEMA)
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(manifest), key=lambda error: list(error.absolute_path))
    if errors:
        details = []
        for error in errors:
            location = ".".join(str(part) for part in error.absolute_path) or "<root>"
            details.append(f"{location}: {error.message}")
        raise ValueError("root manifest schema validation failed: " + "; ".join(details))


def normalize_company(shard: dict[str, Any], company: dict[str, Any]) -> dict[str, Any]:
    defaults = shard.get("defaults", {})
    require(isinstance(defaults, dict), f"{shard.get('group_id')}: defaults must be an object")
    merged = dict(defaults)
    merged.update(company)
    return merged


def public_projection_eligible(level: str, promotion_state: str, visibility: str) -> bool:
    return visibility == "public" and level != "L0" and promotion_state in RECRUITER_ELIGIBLE_STATES


def validate() -> dict[str, Any]:
    root = load_json(ROOT_MANIFEST)
    validate_schema(root)
    require(
        root.get("schema") == "glaciereq.portfolio-root-truth.v1", "unexpected root-truth schema"
    )
    require(
        root.get("authority", {}).get("repository") == "GlacierEQ/job-app-helix",
        "invalid authority repository",
    )
    require(
        root.get("truth_model", {}).get("stale_on_source_head_change") is True,
        "root must become stale on source-head change",
    )
    require(
        root.get("truth_model", {}).get("fail_closed_on_missing_or_unsupported_evidence") is True,
        "root must fail closed",
    )

    source_rows = root.get("sources")
    require(isinstance(source_rows, list) and source_rows, "sources must be a nonempty list")
    source_ids: set[str] = set()
    source_paths: dict[str, Path] = {}
    source_hashes: dict[str, str] = {}
    for row in source_rows:
        require(isinstance(row, dict), "source rows must be objects")
        source_id = row.get("id")
        path_text = row.get("path")
        require(isinstance(source_id, str) and source_id, "source id is required")
        require(source_id not in source_ids, f"duplicate source id: {source_id}")
        require(
            isinstance(path_text, str) and path_text, f"source path is required for {source_id}"
        )
        path = repository_file(path_text, "source file")
        source_ids.add(source_id)
        source_paths[source_id] = path
        source_hashes[path_text] = sha256_file(path)

    projections = root.get("projections")
    require(isinstance(projections, list) and projections, "projections must be a nonempty list")
    projection_ids: set[str] = set()
    projection_states: dict[str, dict[str, Any]] = {}
    for projection in projections:
        require(isinstance(projection, dict), "projection rows must be objects")
        projection_id = projection.get("id")
        require(isinstance(projection_id, str) and projection_id, "projection id is required")
        require(projection_id not in projection_ids, f"duplicate projection id: {projection_id}")
        projection_ids.add(projection_id)
        required_sources = projection.get("required_sources")
        require(
            isinstance(required_sources, list) and required_sources,
            f"{projection_id}: required_sources must be nonempty",
        )
        unknown = sorted(set(required_sources) - source_ids)
        require(not unknown, f"{projection_id}: unknown source ids: {unknown}")
        projection_states[projection_id] = {
            "consumer_repository": projection.get("repository"),
            "contract_state": "DECLARED",
            "freshness_state": "PENDING_CONSUMER_RECEIPT",
            "required_sources": sorted(required_sources),
        }

    inventory = load_json(source_paths["inventory"])
    workspace = inventory.get("workspace_repositories")
    require(isinstance(workspace, list), "inventory workspace_repositories must be a list")
    require(
        all(isinstance(name, str) and name for name in workspace),
        "inventory repository names must be nonempty strings",
    )
    require(
        len(workspace) == len(set(workspace)), "inventory contains duplicate repository identities"
    )
    total = inventory.get("total_repositories")
    require(
        total == len(workspace) + 1,
        f"inventory total {total!r} does not equal root plus {len(workspace)} children",
    )
    workspace_set = set(workspace)

    flagships = load_json(source_paths["flagships"])
    flagship_rows = flagships.get("flagships")
    required_flagships = flagships.get("required_named_flagships")
    require(isinstance(flagship_rows, list) and flagship_rows, "flagship registry must be nonempty")
    require(
        isinstance(required_flagships, list) and required_flagships,
        "required_named_flagships must be nonempty",
    )
    require(
        len(required_flagships) == len(set(required_flagships)),
        "required_named_flagships contains duplicates",
    )
    flagship_ids: set[str] = set()
    for flagship in flagship_rows:
        require(isinstance(flagship, dict), "flagship entries must be objects")
        system_id = flagship.get("system_id")
        require(isinstance(system_id, str) and system_id, "flagship system_id is required")
        require(system_id not in flagship_ids, f"duplicate flagship system_id: {system_id}")
        flagship_ids.add(system_id)
        repository = flagship.get("repository")
        if repository is not None:
            require(
                isinstance(repository, str) and repository.startswith("GlacierEQ/"),
                f"invalid flagship repository: {repository!r}",
            )
        state = flagship.get("state")
        public_surface = flagship.get("public_surface")
        if state in {"QUARANTINED", "BLOCKED_SECURITY", "BLOCKED"}:
            require(
                public_surface not in {"PUBLIC_RECRUITER", "PUBLIC_PROMOTED"},
                f"unsafe flagship is publicly promoted: {system_id}",
            )
    require(
        flagship_ids == set(required_flagships),
        "flagship entries must exactly match required_named_flagships",
    )

    companies_index = load_json(source_paths["companies"])
    required_tracks = companies_index.get("required_company_tracks")
    dossier_files = companies_index.get("dossier_files")
    require(
        isinstance(required_tracks, list) and required_tracks,
        "required_company_tracks must be nonempty",
    )
    require(
        len(required_tracks) == len(set(required_tracks)),
        "required_company_tracks contains duplicates",
    )
    require(isinstance(dossier_files, list) and dossier_files, "dossier_files must be nonempty")

    company_ids: set[str] = set()
    mapped_inventory: set[str] = set()
    admitted_rows = 0
    public_recruiter_rows = 0
    public_non_recruiter_rows = 0
    private_rows = 0
    repository_memberships = 0

    for relative in dossier_files:
        require(isinstance(relative, str) and relative, "dossier path must be a nonempty string")
        shard_path = repository_file(relative, "dossier shard")
        source_hashes[relative] = sha256_file(shard_path)
        shard = load_json(shard_path)
        companies = shard.get("companies")
        require(isinstance(companies, list), f"{relative}: companies must be a list")
        for raw_company in companies:
            require(isinstance(raw_company, dict), f"{relative}: company entries must be objects")
            company = normalize_company(shard, raw_company)
            company_id = company.get("company_id")
            require(
                isinstance(company_id, str) and company_id, f"{relative}: company_id is required"
            )
            require(company_id not in company_ids, f"duplicate company_id: {company_id}")
            company_ids.add(company_id)
            repositories = company.get("repositories", [])
            require(isinstance(repositories, list), f"{company_id}: repositories must be a list")
            for row in repositories:
                require(
                    isinstance(row, list) and len(row) == 6,
                    f"{company_id}: repository rows must contain six columns",
                )
                repository, level, promotion_state, visibility, inventory_scope, provenance = row
                require(
                    isinstance(repository, str) and repository.startswith("GlacierEQ/"),
                    f"{company_id}: invalid repository {repository!r}",
                )
                require(
                    level in {"L0", "L1", "L2", "L3", "L4", "L5"},
                    f"{repository}: invalid level {level!r}",
                )
                require(
                    visibility in {"public", "private"},
                    f"{repository}: invalid visibility {visibility!r}",
                )
                require(
                    inventory_scope in {"HELIX_ADMITTED", "ESTATE_DISCOVERED_NOT_HELIX_ADMITTED"},
                    f"{repository}: invalid inventory scope",
                )
                require(
                    isinstance(promotion_state, str) and promotion_state,
                    f"{repository}: missing promotion state",
                )
                require(
                    isinstance(provenance, str) and provenance, f"{repository}: missing provenance"
                )
                repository_memberships += 1
                if visibility == "private":
                    private_rows += 1
                    require(
                        not public_projection_eligible(level, promotion_state, visibility),
                        f"{repository}: private record became projection eligible",
                    )
                elif public_projection_eligible(level, promotion_state, visibility):
                    public_recruiter_rows += 1
                else:
                    public_non_recruiter_rows += 1
                    if level == "L0":
                        require(
                            promotion_state in PUBLIC_NON_RECRUITER_STATES,
                            (
                                f"{repository}: public L0 record has unsafe promotion "
                                f"state {promotion_state}"
                            ),
                        )
                    require(
                        not promotion_state.startswith("PRIVATE_"),
                        f"{repository}: private-only promotion state appears on a public row",
                    )
                if inventory_scope == "HELIX_ADMITTED":
                    admitted_rows += 1
                    name = repository.split("/", 1)[1]
                    require(
                        name in workspace_set,
                        (
                            "HELIX_ADMITTED repository is absent from canonical "
                            f"inventory: {repository}"
                        ),
                    )
                    mapped_inventory.add(name)

    missing_tracks = sorted(set(required_tracks) - company_ids)
    unexpected_tracks = sorted(company_ids - set(required_tracks))
    require(not missing_tracks, f"missing required company tracks: {missing_tracks}")
    require(not unexpected_tracks, f"unexpected company tracks: {unexpected_tracks}")

    unmapped_inventory = sorted(workspace_set - mapped_inventory)
    require(
        not unmapped_inventory,
        f"canonical inventory children missing governed company/core mapping: {unmapped_inventory}",
    )

    source_digest = hashlib.sha256(canonical_bytes(source_hashes)).hexdigest()
    receipt = {
        "schema": "glaciereq.portfolio-root-truth-receipt.v1",
        "status": "PASS",
        "scope": "CONTROL_PLANE_SOURCES_ONLY",
        "root_version": root.get("version"),
        "evaluated_commit": os.environ.get("GITHUB_SHA", "LOCAL"),
        "source_digest": source_digest,
        "source_hashes": dict(sorted(source_hashes.items())),
        "projection_freshness": {
            "all_projections_current": False,
            "state": "PENDING_CONSUMER_RECEIPTS",
            "projections": projection_states,
            "boundary": (
                "Root validation proves source and contract integrity only. "
                "Each downstream consumer must emit its own current-source receipt "
                "before release."
            ),
        },
        "counts": {
            "total_repositories": total,
            "workspace_repositories": len(workspace),
            "flagship_systems": len(flagship_rows),
            "company_tracks": len(company_ids),
            "repository_memberships": repository_memberships,
            "helix_admitted_memberships": admitted_rows,
            "public_recruiter_memberships": public_recruiter_rows,
            "public_non_recruiter_memberships": public_non_recruiter_rows,
            "private_memberships": private_rows,
            "projections": len(projections),
            "required_sources": len(source_paths),
        },
        "invariants": {
            "root_schema_valid": True,
            "inventory_unique": True,
            "inventory_count_matches": True,
            "flagship_ids_exact": True,
            "required_company_tracks_complete": True,
            "all_admitted_repositories_in_inventory": True,
            "all_inventory_children_mapped": True,
            "projection_source_ids_resolve": True,
            "public_projection_policy_enforced": True,
        },
    }
    receipt["receipt_sha256"] = hashlib.sha256(canonical_bytes(receipt)).hexdigest()
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-receipt", type=Path)
    args = parser.parse_args()
    try:
        receipt = validate()
    except (ValueError, OSError) as exc:
        print(f"portfolio root truth: FAIL: {exc}")
        return 1

    if args.write_receipt:
        output = args.write_receipt
        if not output.is_absolute():
            output = ROOT / output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(canonical_bytes(receipt))
        print(f"wrote {output.relative_to(ROOT)}")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
