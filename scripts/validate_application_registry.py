#!/usr/bin/env python3
"""Validate complete application-company and personal-flagship coverage."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def fail(message: str) -> None:
    raise SystemExit(f"APPLICATION REGISTRY: FAIL: {message}")


def load_json(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        fail(f"required file not found: {path}")
    except OSError as exc:
        fail(f"could not read {path}: {exc}")

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        fail(f"invalid JSON in {path}: {exc}")

    if not isinstance(payload, dict):
        fail(f"JSON root must be an object: {path}")
    return payload


def require_list(payload: dict[str, Any], field: str, source: str) -> list[Any]:
    value = payload.get(field)
    if not isinstance(value, list):
        fail(f"{source}.{field} must be an array")
    return value


def main() -> int:
    index = load_json(ROOT / "manifests" / "company_dossiers.json")
    flagships = load_json(ROOT / "manifests" / "flagship_registry.json")
    inventory = load_json(ROOT / "manifests" / "portfolio_repositories.json")

    dossier_files = require_list(index, "dossier_files", "company_dossiers")
    companies: list[dict[str, Any]] = []
    for relative_path in dossier_files:
        if not isinstance(relative_path, str) or not relative_path:
            fail("company_dossiers.dossier_files contains an invalid path")
        shard = load_json(ROOT / relative_path)
        shard_companies = require_list(shard, "companies", relative_path)
        for company in shard_companies:
            if not isinstance(company, dict):
                fail(f"{relative_path}.companies contains a non-object record")
            companies.append(company)

    company_ids: list[str] = []
    for company in companies:
        company_id = company.get("company_id")
        if not isinstance(company_id, str) or not company_id:
            fail("company record is missing a valid company_id")
        company_ids.append(company_id)

    if len(company_ids) != len(set(company_ids)):
        fail("duplicate company_id")

    required_tracks_raw = require_list(
        index, "required_company_tracks", "company_dossiers"
    )
    required_tracks = set(required_tracks_raw)
    if set(company_ids) != required_tracks:
        missing = sorted(required_tracks - set(company_ids))
        unexpected = sorted(set(company_ids) - required_tracks)
        fail(
            "company-track coverage mismatch "
            f"missing={missing} unexpected={unexpected}"
        )

    levels_raw = index.get("level_definitions")
    if not isinstance(levels_raw, dict) or not levels_raw:
        fail("company_dossiers.level_definitions must be a non-empty object")
    levels = set(levels_raw)

    columns = require_list(
        index, "repository_record_columns", "company_dossiers"
    )
    if not all(isinstance(column, str) and column for column in columns):
        fail("repository_record_columns contains an invalid column")

    workspace_raw = require_list(
        inventory, "workspace_repositories", "portfolio_repositories"
    )
    if not all(isinstance(name, str) and name for name in workspace_raw):
        fail("portfolio_repositories contains an invalid repository name")
    workspace_repositories = set(workspace_raw)
    mapped: dict[str, list[str]] = {}

    for company in companies:
        company_id = company["company_id"]
        repositories = require_list(company, "repositories", company_id)
        seen: set[str] = set()
        for row in repositories:
            if not isinstance(row, list):
                fail(f"repository record in {company_id} must be an array")
            if len(row) != len(columns):
                fail(f"bad row width in {company_id}")

            record = dict(zip(columns, row, strict=True))
            repository = record.get("repository")
            level = record.get("skill_innovation_level")
            if not isinstance(repository, str) or not repository:
                fail(f"missing repository field in {company_id}")
            if not isinstance(level, str) or not level:
                fail(f"missing skill_innovation_level for {repository}")
            if repository in seen:
                fail(f"duplicate repo in {company_id}: {repository}")
            seen.add(repository)

            if not repository.startswith("GlacierEQ/"):
                fail(f"foreign owner: {repository}")
            if level not in levels:
                fail(f"bad level: {repository}")

            repository_name = repository.split("/", 1)[1]
            if repository_name in workspace_repositories:
                mapped.setdefault(repository_name, []).append(company_id)

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

    flagship_records_raw = require_list(flagships, "flagships", "flagship_registry")
    flagship_records: list[dict[str, Any]] = []
    for record in flagship_records_raw:
        if not isinstance(record, dict):
            fail("flagship_registry.flagships contains a non-object record")
        flagship_records.append(record)

    flagship_ids: list[str] = []
    for record in flagship_records:
        system_id = record.get("system_id")
        if not isinstance(system_id, str) or not system_id:
            fail("flagship record is missing a valid system_id")
        flagship_ids.append(system_id)

    required_flagships_raw = require_list(
        flagships, "required_named_flagships", "flagship_registry"
    )
    required_flagships = set(required_flagships_raw)
    if set(flagship_ids) != required_flagships:
        missing = sorted(required_flagships - set(flagship_ids))
        unexpected = sorted(set(flagship_ids) - required_flagships)
        fail(f"flagship coverage mismatch missing={missing} unexpected={unexpected}")
    if len(flagship_ids) != len(set(flagship_ids)):
        fail("duplicate flagship")
    if "job_app_helix" not in flagship_ids:
        fail("Helix root missing")

    for record in flagship_records:
        level = record.get("level")
        if level not in levels:
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
