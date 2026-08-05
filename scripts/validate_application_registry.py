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
COMPANY_STRING_FIELDS = {
    "company_id",
    "display_name",
    "track_state",
    "recruiter_thesis",
    "gap_or_next_gate",
    "non_affiliation",
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


def resolve_company_records(
    shard: dict[str, Any], relative_path: str, required_fields: set[str]
) -> list[dict[str, Any]]:
    raw_companies = require_list(shard, "companies", relative_path)
    defaults_raw = shard.get("defaults")
    if defaults_raw is None:
        defaults: dict[str, Any] = {}
    else:
        if not isinstance(defaults_raw, dict):
            fail(f"{relative_path}.defaults must be an object")
        if shard.get("defaults_apply_to_all_companies") is not True:
            fail(
                f"{relative_path} defines defaults without "
                "defaults_apply_to_all_companies=true"
            )
        defaults = defaults_raw

    resolved_companies: list[dict[str, Any]] = []
    for raw_company in raw_companies:
        if not isinstance(raw_company, dict):
            fail(f"{relative_path}.companies contains a non-object record")
        company = {**defaults, **raw_company}
        missing = sorted(required_fields - set(company))
        if missing:
            fail(f"{relative_path} company record missing fields: {missing}")
        for field in COMPANY_STRING_FIELDS:
            value = company.get(field)
            if not isinstance(value, str) or not value:
                fail(f"{relative_path}.{field} must be a non-empty string")
        target_roles = company.get("target_roles")
        if not isinstance(target_roles, list) or not target_roles:
            fail(f"{relative_path}.target_roles must be a non-empty array")
        string_set(target_roles, f"{relative_path}.target_roles")
        if not isinstance(company.get("repositories"), list):
            fail(f"{relative_path}.repositories must be an array")
        resolved_companies.append(company)
    return resolved_companies


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

    external_registry_path = index.get("external_flagship_registry")
    if not isinstance(external_registry_path, str) or not external_registry_path:
        fail("company_dossiers.external_flagship_registry is required")
    external_registry = load_json(root / external_registry_path)
    if external_registry.get("authority") != authority:
        fail("external flagship registry authority mismatch")

    required_company_fields = string_set(
        require_list(index, "company_record_required_fields", "company_dossiers"),
        "company_dossiers.company_record_required_fields",
    )
    required_company_fields_expected = {
        "company_id",
        "display_name",
        "track_state",
        "target_roles",
        "recruiter_thesis",
        "gap_or_next_gate",
        "non_affiliation",
        "repositories",
    }
    if required_company_fields != required_company_fields_expected:
        fail(
            "company_record_required_fields mismatch "
            f"expected={sorted(required_company_fields_expected)} "
            f"actual={sorted(required_company_fields)}"
        )

    defaults_contract = require_dict(index, "shard_defaults_contract", "company_dossiers")
    if defaults_contract.get("allowed") is not True:
        fail("shard defaults contract must explicitly allow governed inheritance")
    if defaults_contract.get("required_marker") != "defaults_apply_to_all_companies":
        fail("shard defaults contract has an unexpected required marker")

    columns = require_list(index, "repository_record_columns", "company_dossiers")
    if tuple(columns) != REPOSITORY_COLUMNS:
        fail(
            "repository_record_columns must exactly equal "
            f"{list(REPOSITORY_COLUMNS)}"
        )

    enum_contract = require_dict(index, "repository_record_enums", "company_dossiers")
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
        allowed_values[field] = string_set(values, f"repository_record_enums.{field}")

    legacy_alias_contract = require_dict(
        index, "repository_record_legacy_aliases", "company_dossiers"
    )
    if set(legacy_alias_contract) != {"promotion_state"}:
        fail("legacy aliases may exist only for promotion_state")
    promotion_aliases_raw = legacy_alias_contract["promotion_state"]
    if not isinstance(promotion_aliases_raw, dict) or not promotion_aliases_raw:
        fail("promotion_state legacy aliases must be a non-empty object")
    promotion_aliases: dict[str, str] = {}
    for source, target in promotion_aliases_raw.items():
        if not isinstance(source, str) or not source:
            fail("legacy promotion alias source must be a non-empty string")
        if not isinstance(target, str) or target not in allowed_values["promotion_state"]:
            fail(f"legacy promotion alias target is invalid: {target!r}")
        if source in allowed_values["promotion_state"]:
            fail(f"legacy promotion alias source is still a valid promotion state: {source}")
        promotion_aliases[source] = target

    classification_notes = require_dict(index, "classification_notes", "company_dossiers")
    experiment_note = classification_notes.get("l1_private_experiment_boundary")
    if not isinstance(experiment_note, str) or not experiment_note:
        fail("l1_private_experiment_boundary classification note is required")
    alias_note = classification_notes.get("legacy_promotion_alias_boundary")
    if not isinstance(alias_note, str) or not alias_note:
        fail("legacy_promotion_alias_boundary classification note is required")

    dossier_files = require_list(index, "dossier_files", "company_dossiers")
    companies: list[dict[str, Any]] = []
    for relative_path in dossier_files:
        if not isinstance(relative_path, str) or not relative_path:
            fail("company_dossiers.dossier_files contains an invalid path")
        shard = load_json(root / relative_path)
        companies.extend(
            resolve_company_records(shard, relative_path, required_company_fields)
        )

    company_ids = [company["company_id"] for company in companies]
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

    level_definitions = require_dict(index, "level_definitions", "company_dossiers")
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
    l1_private_experiment_count = 0
    normalized_legacy_promotion_aliases = 0
    for company in companies:
        company_id = company["company_id"]
        repositories = company["repositories"]
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

            raw_promotion_state = record["promotion_state"]
            if raw_promotion_state in promotion_aliases:
                record["promotion_state"] = promotion_aliases[raw_promotion_state]
                normalized_legacy_promotion_aliases += 1

            for field in sorted(ENUM_FIELDS):
                value = record[field]
                if value not in allowed_values[field]:
                    fail(
                        f"invalid {field}={value!r} for {repository}; "
                        f"allowed={sorted(allowed_values[field])}"
                    )

            if (
                level == "L1"
                and record["promotion_state"] == "PRIVATE_EXPERIMENT"
                and record["provenance_state"] == "ORIGINAL_CANDIDATE"
            ):
                l1_private_experiment_count += 1

            repository_name = repository.split("/", 1)[1]
            if repository_name in workspace_repositories:
                mapped.setdefault(repository_name, []).append(company_id)

    if l1_private_experiment_count and "candidate provenance" not in experiment_note:
        fail(
            "classification note must explain that ORIGINAL_CANDIDATE is "
            "candidate provenance for L1 private experiments"
        )
    if (
        normalized_legacy_promotion_aliases
        and "never a recruiter admission state" not in alias_note
    ):
        fail("legacy promotion alias note must deny recruiter admission semantics")

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
        require_list(flagships, "required_named_flagships", "flagship_registry"),
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

    verified_external_repositories = string_set(
        require_list(
            external_registry,
            "verified_owner_estate_external_repositories",
            "flagship_external_repositories",
        ),
        "flagship_external_repositories.verified_owner_estate_external_repositories",
    )
    unresolved_system_ids = string_set(
        require_list(
            external_registry,
            "unresolved_system_ids",
            "flagship_external_repositories",
        ),
        "flagship_external_repositories.unresolved_system_ids",
    )

    observed_external_repositories: set[str] = set()
    observed_unresolved_system_ids: set[str] = set()
    for record in flagship_records:
        system_id = record["system_id"]
        level = record.get("level")
        if level not in levels:
            fail(f"bad flagship level: {system_id}")
        repository = record.get("repository")
        if repository is None:
            observed_unresolved_system_ids.add(system_id)
            continue
        if not isinstance(repository, str) or not repository.startswith("GlacierEQ/"):
            fail(f"invalid flagship repository for {system_id}: {repository!r}")
        if repository == authority:
            continue
        repository_name = repository.split("/", 1)[1]
        if repository_name not in workspace_repositories:
            observed_external_repositories.add(repository)

    if observed_external_repositories != verified_external_repositories:
        missing = sorted(verified_external_repositories - observed_external_repositories)
        unexpected = sorted(observed_external_repositories - verified_external_repositories)
        fail(
            "external flagship repository identity mismatch "
            f"missing={missing} unexpected={unexpected}"
        )
    if observed_unresolved_system_ids != unresolved_system_ids:
        missing = sorted(unresolved_system_ids - observed_unresolved_system_ids)
        unexpected = sorted(observed_unresolved_system_ids - unresolved_system_ids)
        fail(
            "unresolved flagship identity mismatch "
            f"missing={missing} unexpected={unexpected}"
        )

    return {
        "status": "PASS",
        "total_inventory_repositories": total_repositories,
        "helix_children_mapped": len(workspace_repositories),
        "helix_children_exactly_once": True,
        "company_tracks": len(company_ids),
        "named_flagships": len(flagship_ids),
        "external_flagship_repositories": len(verified_external_repositories),
        "unresolved_flagships": len(unresolved_system_ids),
        "inherited_company_dossiers": sum(
            1 for company in companies if company["track_state"] == "NO_DIRECT_EXHIBIT_VERIFIED"
        ),
        "l1_private_experiments_documented": l1_private_experiment_count,
        "normalized_legacy_promotion_aliases": normalized_legacy_promotion_aliases,
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
