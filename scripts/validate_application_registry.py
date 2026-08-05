#!/usr/bin/env python3
"""Validate complete application-company and personal-flagship coverage."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_COLUMNS = (
    "repository",
    "skill_innovation_level",
    "promotion_state",
    "visibility",
    "inventory_scope",
    "provenance_state",
)
ENUM_FIELDS = {
    "promotion_state",
    "visibility",
    "inventory_scope",
    "provenance_state",
}


class RegistryValidationError(ValueError):
    """Raised when the application registry violates its governing contract."""


def fail(message: str) -> None:
    raise RegistryValidationError(message)


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


def require_dict(payload: dict[str, Any], field: str, source: str) -> dict[str, Any]:
    value = payload.get(field)
    if not isinstance(value, dict):
        fail(f"{source}.{field} must be an object")
    return value


def string_set(values: list[Any], source: str) -> set[str]:
    if not all(isinstance(value, str) and value for value in values):
        fail(f"{source} contains an invalid string value")
    strings = set(values)
    if len(strings) != len(values):
        fail(f"{source} contains duplicate values")
    return strings


def validate_registry(root: Path = ROOT) -> dict[str, Any]:
    """Validate governing registry files rooted at a repository checkout."""
    index = load_json(root / "manifests" / "company_dossiers.json")
    flagships = load_json(root / "manifests" / "flagship_registry.json")
    inventory = load_json(root / "manifests" / "portfolio_repositories.json")

    authority = index.get("authority")
    if authority != "GlacierEQ/job-app-helix":
        fail(f"unexpected registry authority: {authority!r}")
    if flagships.get("authority") != authority:
        fail("flagship authority does not match company-dossier authority")

    columns = require_list(
        index, "repository_record_columns", "company_dossiers"
    )
    if tuple(columns) != REPOSITORY_COLUMNS:
        fail(
            "repository_record_columns must exactly equal "
            f"{list(REPOSITORY_COLUMNS)}"
        )

    enum_contract = require_dict(
        index, "repository_record_enums", "company_dossiers"
    )
    if set(enum_contract) != ENUM_FIELDS:
        fail(
            "repository_record_enums fields mismatch "
            f"expected={sorted(ENUM_FIELDS)} actual={sorted(enum_contract)}"
        )
    allowed_values: dict[str, set[str]] = {}
    for field in sorted(ENUM_FIELDS):
        values = enum_contract.get(field)
        if not isinstance(values, list) or not values:
            fail(f"repository_record_enums.{field} must be a non-empty array")
        allowed_values[field] = string_set(
            values, f"repository_record_enums.{field}"
        )

    dossier_files = require_list(index, "dossier_files", "company_dossiers")
    companies: list[dict[str, Any]] = []
    for relative_path in dossier_files:
        if not isinstance(relative_path, str) or not relative_path:
            fail("company_dossiers.dossier_files contains an invalid path")
        shard = load_json(root / relative_path)
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

    required_tracks = string_set(
        require_list(index, "required_company_tracks", "company_dossiers"),
        "company_dossiers.required_company_tracks",
    )
    if set(company_ids) != required_tracks:
        missing = sorted(required_tracks - set(company_ids))
        unexpected = sorted(set(company_ids) - required_tracks)
        fail(
            "company-track coverage mismatch "
            f"missing={missing} unexpected={unexpected}"
        )

    level_definitions = require_dict(
        index, "level_definitions", "company_dossiers"
    )
    if not level_definitions:
        fail("company_dossiers.level_definitions must not be empty")
    if not all(
        isinstance(level, str)
        and level
        and isinstance(description, str)
        and description
        for level, description in level_definitions.items()
    ):
        fail("company_dossiers.level_definitions contains invalid entries")
    levels = set(level_definitions)

    flagship_levels = require_dict(flagships, "levels", "flagship_registry")
    if flagship_levels != level_definitions:
        fail("flagship level definitions drift from company-dossier definitions")

    workspace_raw = require_list(
        inventory, "workspace_repositories", "portfolio_repositories"
    )
    workspace_repositories = string_set(
        workspace_raw, "portfolio_repositories.workspace_repositories"
    )
    if len(workspace_raw) != 66:
        fail(
            "Helix workspace inventory must contain exactly 66 unique children; "
            f"found {len(workspace_raw)}"
        )
    total_repositories = inventory.get("total_repositories")
    if total_repositories != len(workspace_raw) + 1:
        fail(
            "portfolio_repositories.total_repositories must equal the 66 children "
            f"plus the Helix root; found {total_repositories!r}"
        )
    if inventory.get("owner") != "GlacierEQ":
        fail("portfolio_repositories.owner must be GlacierEQ")
    if inventory.get("portfolio_root") != "job-app-helix":
        fail("portfolio_repositories.portfolio_root must be job-app-helix")

    mapped: dict[str, list[str]] = {}
    for company in companies:
        company_id = company["company_id"]
        repositories = require_list(company, "repositories", company_id)
        seen: set[str] = set()
        for row in repositories:
            if not isinstance(row, list):
                fail(f"repository record in {company_id} must be an array")
            if len(row) != len(REPOSITORY_COLUMNS):
                fail(f"bad row width in {company_id}")
            if not all(isinstance(value, str) and value for value in row):
                fail(f"repository record in {company_id} contains an invalid value")

            record = dict(zip(REPOSITORY_COLUMNS, row, strict=True))
            repository = record["repository"]
            level = record["skill_innovation_level"]
            if repository in seen:
                fail(f"duplicate repo in {company_id}: {repository}")
            seen.add(repository)

            if not repository.startswith("GlacierEQ/"):
                fail(f"foreign owner: {repository}")
            if level not in levels:
                fail(f"bad level: {repository}")
            for field in sorted(ENUM_FIELDS):
                value = record[field]
                if value not in allowed_values[field]:
                    fail(
                        f"invalid {field}={value!r} for {repository}; "
                        f"allowed={sorted(allowed_values[field])}"
                    )

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
    flagships_by_id: dict[str, dict[str, Any]] = {}
    for record in flagship_records:
        system_id = record.get("system_id")
        if not isinstance(system_id, str) or not system_id:
            fail("flagship record is missing a valid system_id")
        flagship_ids.append(system_id)
        flagships_by_id[system_id] = record

    required_flagships = string_set(
        require_list(
            flagships, "required_named_flagships", "flagship_registry"
        ),
        "flagship_registry.required_named_flagships",
    )
    if set(flagship_ids) != required_flagships:
        missing = sorted(required_flagships - set(flagship_ids))
        unexpected = sorted(set(flagship_ids) - required_flagships)
        fail(f"flagship coverage mismatch missing={missing} unexpected={unexpected}")
    if len(flagship_ids) != len(set(flagship_ids)):
        fail("duplicate flagship")

    root_flagship = flagships_by_id.get("job_app_helix")
    if root_flagship is None or root_flagship.get("repository") != authority:
        fail("Helix root flagship is missing or points to the wrong repository")

    for record in flagship_records:
        level = record.get("level")
        if level not in levels:
            fail(f"bad flagship level: {record['system_id']}")

    return {
        "status": "PASS",
        "total_inventory_repositories": total_repositories,
        "helix_children_mapped": len(workspace_repositories),
        "helix_children_exactly_once": True,
        "company_tracks": len(company_ids),
        "named_flagships": len(flagship_ids),
        "zero_direct_omission_gate": True,
    }


def main() -> int:
    try:
        result = validate_registry()
    except RegistryValidationError as exc:
        print(f"APPLICATION REGISTRY: FAIL: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
