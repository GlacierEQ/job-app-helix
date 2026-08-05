#!/usr/bin/env python3
"""Validate complete application-company and personal-flagship coverage."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        fail(f"JSON root must be an object: {path}")
    return payload


def fail(message: str) -> None:
    raise SystemExit(f"APPLICATION REGISTRY: FAIL: {message}")


def main() -> int:
    index = load_json(ROOT / "manifests" / "company_dossiers.json")
    flagships = load_json(ROOT / "manifests" / "flagship_registry.json")
    inventory = load_json(ROOT / "manifests" / "portfolio_repositories.json")

    companies: list[dict[str, Any]] = []
    for relative_path in index["dossier_files"]:
        shard = load_json(ROOT / relative_path)
        companies.extend(shard["companies"])

    company_ids = [company["company_id"] for company in companies]
    if len(company_ids) != len(set(company_ids)):
        fail("duplicate company_id")

    required_tracks = set(index["required_company_tracks"])
    if set(company_ids) != required_tracks:
        missing = sorted(required_tracks - set(company_ids))
        unexpected = sorted(set(company_ids) - required_tracks)
        fail(f"company-track coverage mismatch missing={missing} unexpected={unexpected}")

    levels = set(index["level_definitions"])
    columns = index["repository_record_columns"]
    workspace_repositories = set(inventory["workspace_repositories"])
    mapped: dict[str, list[str]] = {}

    for company in companies:
        seen: set[str] = set()
        for row in company["repositories"]:
            if len(row) != len(columns):
                fail(f"bad row width in {company['company_id']}")

            record = dict(zip(columns, row, strict=True))
            repository = record["repository"]
            if repository in seen:
                fail(f"duplicate repo in {company['company_id']}: {repository}")
            seen.add(repository)

            if not repository.startswith("GlacierEQ/"):
                fail(f"foreign owner: {repository}")
            if record["skill_innovation_level"] not in levels:
                fail(f"bad level: {repository}")

            repository_name = repository.split("/", 1)[1]
            if repository_name in workspace_repositories:
                mapped.setdefault(repository_name, []).append(company["company_id"])

    mapped_names = set(mapped)
    if mapped_names != workspace_repositories:
        missing = sorted(workspace_repositories - mapped_names)
        unexpected = sorted(mapped_names - workspace_repositories)
        fail(f"Helix mismatch missing={missing} unexpected={unexpected}")

    duplicate_mappings = {
        repository: tracks
        for repository, tracks in mapped.items()
        if len(tracks) != 1
    }
    if duplicate_mappings:
        fail(f"Helix children mapped more than once: {duplicate_mappings}")

    flagship_records = flagships["flagships"]
    flagship_ids = [record["system_id"] for record in flagship_records]
    required_flagships = set(flagships["required_named_flagships"])
    if set(flagship_ids) != required_flagships:
        missing = sorted(required_flagships - set(flagship_ids))
        unexpected = sorted(set(flagship_ids) - required_flagships)
        fail(f"flagship coverage mismatch missing={missing} unexpected={unexpected}")
    if len(flagship_ids) != len(set(flagship_ids)):
        fail("duplicate flagship")
    if "job_app_helix" not in flagship_ids:
        fail("Helix root missing")

    for record in flagship_records:
        if record["level"] not in levels:
            fail(f"bad flagship level: {record['system_id']}")

    result = {
        "status": "PASS",
        "helix_children_mapped": len(workspace_repositories),
        "helix_children_exactly_once": True,
        "company_tracks": len(company_ids),
        "named_flagships": len(flagship_ids),
        "zero_direct_omission_gate": True,
    }
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
