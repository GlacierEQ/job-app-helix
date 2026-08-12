#!/usr/bin/env python3
"""Validate complete application-company and admitted-portfolio coverage.

The registry is a living boundary. Its invariant is relational integrity, not a
frozen repository count: child identities are unique, total = children + root,
and every admitted child is mapped exactly once to a governed track.
"""

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
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        fail(f"required file not found: {path}")
    except OSError as exc:
        fail(f"could not read {path}: {exc}")
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
    shard: dict[str, Any],
    relative_path: str,
    required_fields: set[str],
) -> tuple[list[dict[str, Any]], int]:
    raw_companies = require_list(shard, "companies", relative_path)
    defaults_raw = shard.get("defaults")
    defaults: dict[str, Any] = {}
    if defaults_raw is not None:
        if not isinstance(defaults_raw, dict):
            fail(f"{relative_path}.defaults must be an object")
        if shard.get("defaults_apply_to_all_companies") is not True:
            fail(
                f"{relative_path} defines defaults without "
                "defaults_apply_to_all_companies=true"
            )
        defaults = defaults_raw

    resolved: list[dict[str, Any]] = []
    inherited_count = 0
    for raw_company in raw_companies:
        if not isinstance(raw_company, dict):
            fail(f"{relative_path}.companies contains a non-object record")
        if defaults and "track_state" not in raw_company:
            inherited_count += 1
        company = {**defaults, **raw_company}
        missing = sorted(required_fields - set(company))
        if missing:
            fail(f"{relative_path} company record missing fields: {missing}")
        for field in COMPANY_STRING_FIELDS:
            value = company.get(field)
            if not isinstance(value, str) or not value:
                fail(f"{relative_path}.{field} must be a non-empty string")
        roles = company.get("target_roles")
        if not isinstance(roles, list) or not roles:
            fail(f"{relative_path}.target_roles must be a non-empty array")
        string_set(roles, f"{relative_path}.target_roles")
        if not isinstance(company.get("repositories"), list):
            fail(f"{relative_path}.repositories must be an array")
        resolved.append(company)
    return resolved, inherited_count


def validate_registry(root: Path = ROOT) -> dict[str, Any]:
    index = load_json(root / "manifests" / "company_dossiers.json")
    flagships = load_json(root / "manifests" / "flagship_registry.json")
    inventory = load_json(root / "manifests" / "portfolio_repositories.json")

    authority = index.get("authority")
    if authority != "GlacierEQ/job-app-helix":
        fail(f"unexpected registry authority: {authority!r}")
    if flagships.get("authority") != authority:
        fail("flagship authority does not match company-dossier authority")

    external_path = index.get("external_flagship_registry")
    if not isinstance(external_path, str) or not external_path:
        fail("company_dossiers.external_flagship_registry is required")
    external_registry = load_json(root / external_path)
    if external_registry.get("authority") != authority:
        fail("external flagship registry authority mismatch")

    required_fields = string_set(
        require_list(index, "company_record_required_fields", "company_dossiers"),
        "company_dossiers.company_record_required_fields",
    )
    expected_fields = {
        "company_id",
        "display_name",
        "track_state",
        "target_roles",
        "recruiter_thesis",
        "gap_or_next_gate",
        "non_affiliation",
        "repositories",
    }
    if required_fields != expected_fields:
        fail(
            "company_record_required_fields mismatch "
            f"expected={sorted(expected_fields)} actual={sorted(required_fields)}"
        )

    defaults_contract = require_dict(index, "shard_defaults_contract", "company_dossiers")
    if defaults_contract.get("allowed") is not True:
        fail("shard defaults contract must explicitly allow governed inheritance")
    if defaults_contract.get("required_marker") != "defaults_apply_to_all_companies":
        fail("shard defaults contract has an unexpected required marker")

    columns = require_list(index, "repository_record_columns", "company_dossiers")
    if tuple(columns) != REPOSITORY_COLUMNS:
        fail(f"repository_record_columns must exactly equal {list(REPOSITORY_COLUMNS)}")

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

    legacy = require_dict(index, "repository_record_legacy_aliases", "company_dossiers")
    if set(legacy) != {"promotion_state"}:
        fail("legacy aliases may exist only for promotion_state")
    raw_aliases = legacy["promotion_state"]
    if not isinstance(raw_aliases, dict) or not raw_aliases:
        fail("promotion_state legacy aliases must be a non-empty object")
    aliases: dict[str, str] = {}
    for source, target in raw_aliases.items():
        if not isinstance(source, str) or not source:
            fail("legacy promotion alias source must be a non-empty string")
        if not isinstance(target, str) or target not in allowed_values["promotion_state"]:
            fail(f"legacy promotion alias target is invalid: {target!r}")
        if source in allowed_values["promotion_state"]:
            fail(f"legacy promotion alias source is still a valid promotion state: {source}")
        aliases[source] = target

    notes = require_dict(index, "classification_notes", "company_dossiers")
    experiment_note = notes.get("l1_private_experiment_boundary")
    alias_note = notes.get("legacy_promotion_alias_boundary")
    if not isinstance(experiment_note, str) or not experiment_note:
        fail("l1_private_experiment_boundary classification note is required")
    if not isinstance(alias_note, str) or not alias_note:
        fail("legacy_promotion_alias_boundary classification note is required")

    companies: list[dict[str, Any]] = []
    inherited_count = 0
    for relative_path in require_list(index, "dossier_files", "company_dossiers"):
        if not isinstance(relative_path, str) or not relative_path:
            fail("company_dossiers.dossier_files contains an invalid path")
        shard = load_json(root / relative_path)
        shard_companies, shard_inherited = resolve_company_records(
            shard, relative_path, required_fields
        )
        companies.extend(shard_companies)
        inherited_count += shard_inherited

    company_ids = [company["company_id"] for company in companies]
    if len(company_ids) != len(set(company_ids)):
        fail("duplicate company_id")
    required_tracks = string_set(
        require_list(index, "required_company_tracks", "company_dossiers"),
        "company_dossiers.required_company_tracks",
    )
    if set(company_ids) != required_tracks:
        fail(
            "company-track coverage mismatch "
            f"missing={sorted(required_tracks - set(company_ids))} "
            f"unexpected={sorted(set(company_ids) - required_tracks)}"
        )

    level_definitions = require_dict(index, "level_definitions", "company_dossiers")
    if not level_definitions:
        fail("company_dossiers.level_definitions must not be empty")
    levels = set(level_definitions)
    if require_dict(flagships, "levels", "flagship_registry") != level_definitions:
        fail("flagship level definitions drift from company-dossier definitions")

    workspace_raw = require_list(inventory, "workspace_repositories", "portfolio_repositories")
    workspace = string_set(workspace_raw, "portfolio_repositories.workspace_repositories")
    if not workspace:
        fail("Helix workspace inventory must contain at least one child")
    total_repositories = inventory.get("total_repositories")
    if total_repositories != len(workspace_raw) + 1:
        fail(
            "portfolio_repositories.total_repositories must equal the unique children "
            f"plus the Helix root; found {total_repositories!r} for {len(workspace_raw)} children"
        )
    if inventory.get("owner") != "GlacierEQ":
        fail("portfolio_repositories.owner must be GlacierEQ")
    if inventory.get("portfolio_root") != "job-app-helix":
        fail("portfolio_repositories.portfolio_root must be job-app-helix")

    mapped: dict[str, list[str]] = {}
    private_experiments = 0
    normalized_aliases = 0
    for company in companies:
        company_id = company["company_id"]
        seen: set[str] = set()
        for row in company["repositories"]:
            if not isinstance(row, list) or len(row) != len(REPOSITORY_COLUMNS):
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
            if record["promotion_state"] in aliases:
                record["promotion_state"] = aliases[record["promotion_state"]]
                normalized_aliases += 1
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
                private_experiments += 1
            name = repository.split("/", 1)[1]
            if name in workspace:
                mapped.setdefault(name, []).append(company_id)

    if private_experiments and "candidate provenance" not in experiment_note:
        fail(
            "classification note must explain that ORIGINAL_CANDIDATE is "
            "candidate provenance for L1 private experiments"
        )
    if normalized_aliases and "never a recruiter admission state" not in alias_note:
        fail("legacy promotion alias note must deny recruiter admission semantics")

    mapped_names = set(mapped)
    if mapped_names != workspace:
        fail(
            f"Helix mismatch missing={sorted(workspace - mapped_names)} "
            f"unexpected={sorted(mapped_names - workspace)}"
        )
    duplicates = {name: tracks for name, tracks in mapped.items() if len(tracks) != 1}
    if duplicates:
        fail(f"Helix children mapped more than once: {duplicates}")

    flagship_rows = require_list(flagships, "flagships", "flagship_registry")
    flagship_records: list[dict[str, Any]] = []
    for record in flagship_rows:
        if not isinstance(record, dict):
            fail("flagship_registry.flagships contains a non-object record")
        flagship_records.append(record)
    flagship_ids = [record.get("system_id") for record in flagship_records]
    if not all(isinstance(system_id, str) and system_id for system_id in flagship_ids):
        fail("flagship record is missing a valid system_id")
    required_flagships = string_set(
        require_list(flagships, "required_named_flagships", "flagship_registry"),
        "flagship_registry.required_named_flagships",
    )
    actual_flagship_ids = {str(system_id) for system_id in flagship_ids}
    if actual_flagship_ids != required_flagships:
        fail(
            "flagship coverage mismatch "
            f"missing={sorted(required_flagships - actual_flagship_ids)} "
            f"unexpected={sorted(actual_flagship_ids - required_flagships)}"
        )
    if len(flagship_ids) != len(actual_flagship_ids):
        fail("duplicate flagship")

    root_flagship = next(
        (row for row in flagship_records if row.get("system_id") == "job_app_helix"),
        None,
    )
    if root_flagship is None or root_flagship.get("repository") != authority:
        fail("Helix root flagship is missing or points to the wrong repository")

    verified_external = string_set(
        require_list(
            external_registry,
            "verified_owner_estate_external_repositories",
            "flagship_external_repositories",
        ),
        "flagship_external_repositories.verified_owner_estate_external_repositories",
    )
    unresolved = string_set(
        require_list(
            external_registry,
            "unresolved_system_ids",
            "flagship_external_repositories",
        ),
        "flagship_external_repositories.unresolved_system_ids",
    )
    observed_external: set[str] = set()
    observed_unresolved: set[str] = set()
    for record in flagship_records:
        system_id = str(record["system_id"])
        level = record.get("level")
        if level not in levels:
            fail(f"bad flagship level: {system_id}")
        repository = record.get("repository")
        if repository is None:
            observed_unresolved.add(system_id)
            continue
        if not isinstance(repository, str) or not repository.startswith("GlacierEQ/"):
            fail(f"invalid flagship repository for {system_id}: {repository!r}")
        if repository == authority:
            continue
        if repository.split("/", 1)[1] not in workspace:
            observed_external.add(repository)

    if observed_external != verified_external:
        fail(
            "external flagship repository identity mismatch "
            f"missing={sorted(verified_external - observed_external)} "
            f"unexpected={sorted(observed_external - verified_external)}"
        )
    if observed_unresolved != unresolved:
        fail(
            "unresolved flagship identity mismatch "
            f"missing={sorted(unresolved - observed_unresolved)} "
            f"unexpected={sorted(observed_unresolved - unresolved)}"
        )

    return {
        "status": "PASS",
        "total_inventory_repositories": total_repositories,
        "helix_children_mapped": len(workspace),
        "helix_children_exactly_once": True,
        "company_tracks": len(company_ids),
        "named_flagships": len(flagship_ids),
        "external_flagship_repositories": len(verified_external),
        "unresolved_flagships": len(unresolved),
        "inherited_company_dossiers": inherited_count,
        "l1_private_experiments_documented": private_experiments,
        "normalized_legacy_promotion_aliases": normalized_aliases,
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
