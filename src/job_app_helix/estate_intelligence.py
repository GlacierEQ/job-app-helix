from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from .estate_compiler import digest
from .estate_intelligence_company import enrich_company_registry
from .estate_intelligence_public import public_intelligence_projection
from .estate_intelligence_roles import (
    role_fit,
    role_profile,
    validate_role_rules,
)
from .estate_intelligence_support import (
    apply_capability_assertions,
    repository_system_map,
    support_rows,
)

__all__ = [
    "project_estate_intelligence",
    "public_intelligence_projection",
    "role_fit",
    "role_profile",
]


def project_estate_intelligence(
    bundle: Mapping[str, Any],
    *,
    policy: Mapping[str, Any],
    company_intelligence: Mapping[str, Mapping[str, Any]] | None = None,
    estate_facts: Mapping[str, Any] | None = None,
    census: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    projected = deepcopy(dict(bundle))
    intelligence = company_intelligence or {}
    validate_role_rules(policy)

    support_only, supports = _resolve_supports(
        projected,
        estate_facts,
        census,
    )
    capability_assertions = apply_capability_assertions(
        projected,
        estate_facts,
        census,
    )
    reference = projected["system_registry"]
    experiment_ids = _experiment_ids(projected)
    unresolved_ids = {
        row["system_id"]
        for row in reference["systems"]
        if row.get("lineage_complete") is False
    }
    archived_ids = {
        row["system_id"]
        for row in reference["systems"]
        if row.get("archived") is True
    }
    excluded = support_only | experiment_ids | unresolved_ids | archived_ids

    _project_reference_systems(
        reference,
        support_only=support_only,
        experiment_ids=experiment_ids,
        unresolved_ids=unresolved_ids,
        archived_ids=archived_ids,
        supports=supports,
    )
    capability_registry = _project_capability_donors(
        projected["capability_donor_registry"],
        excluded,
    )
    enrich_company_registry(
        projected,
        policy=policy,
        intelligence=intelligence,
        excluded=excluded,
    )
    company_registry = projected["company_projection_registry"]
    company_registry["content_hash"] = _content_hash(company_registry)

    _update_bundle_receipt(
        projected,
        policy=policy,
        intelligence=intelligence,
        supports=supports,
        capability_assertions=capability_assertions,
        reference=reference,
        capability_registry=capability_registry,
        company_registry=company_registry,
        support_only=support_only,
        experiment_ids=experiment_ids,
        unresolved_ids=unresolved_ids,
    )
    projected["content_hash"] = _content_hash(projected)
    return projected


def _resolve_supports(
    projected: Mapping[str, Any],
    estate_facts: Mapping[str, Any] | None,
    census: Mapping[str, Any] | None,
) -> tuple[set[str], list[dict[str, Any]]]:
    if census is None:
        return set(), []
    repository_names = {
        row["repository"]
        for row in census.get("repositories", [])
        if isinstance(row, dict) and isinstance(row.get("repository"), str)
    }
    repo_to_system = repository_system_map(projected)
    support_only: set[str] = set()
    resolved: list[dict[str, Any]] = []
    for row in support_rows(estate_facts, repository_names):
        source_id = repo_to_system.get(row["repository"])
        target_id = repo_to_system.get(row["target"])
        if target_id is None:
            raise ValueError(f"support target is not reference: {row['target']}")
        if source_id is not None and source_id == target_id:
            raise ValueError(
                "support assertion resolves inside one lineage: "
                f"{row['repository']}"
            )
        if source_id is not None:
            support_only.add(source_id)
        resolved.append(
            {
                **row,
                "source_system_id": source_id,
                "target_system_id": target_id,
            }
        )
    return support_only, resolved


def _experiment_ids(projected: Mapping[str, Any]) -> set[str]:
    return {
        row["system_id"]
        for row in projected.get("experiment_pipeline", [])
        if isinstance(row, dict) and isinstance(row.get("system_id"), str)
    }


def _project_reference_systems(
    reference: dict[str, Any],
    *,
    support_only: set[str],
    experiment_ids: set[str],
    unresolved_ids: set[str],
    archived_ids: set[str],
    supports: list[dict[str, Any]],
) -> None:
    for system in reference["systems"]:
        system_id = str(system["system_id"])
        reasons = []
        if system_id in support_only:
            reasons.append("SUPPORT_REFERENCE_ONLY")
        if system_id in experiment_ids:
            reasons.append("EXPERIMENT")
        if system_id in unresolved_ids:
            reasons.append("UNRESOLVED_LINEAGE")
        if system_id in archived_ids:
            reasons.append("ARCHIVED_ROOT")
        system["counts_as_independent_accomplishment"] = not reasons
        system["accomplishment_exclusion_reasons"] = reasons

    reference["schema"] = "glaciereq.reference-system-registry.v2"
    reference["raw_reference_graph_system_count"] = len(reference["systems"])
    reference["reference_accomplishment_count"] = sum(
        row["counts_as_independent_accomplishment"]
        for row in reference["systems"]
    )
    reference["support_references"] = supports
    reference["content_hash"] = _content_hash(reference)


def _project_capability_donors(
    registry: dict[str, Any],
    excluded: set[str],
) -> dict[str, Any]:
    for capability in registry["capabilities"]:
        all_donors = list(capability.get("donor_systems", []))
        capability["all_donor_systems"] = all_donors
        capability["excluded_non_accomplishment_donors"] = [
            system_id for system_id in all_donors if system_id in excluded
        ]
        capability["donor_systems"] = [
            system_id for system_id in all_donors if system_id not in excluded
        ]
        donor_count = len(capability["donor_systems"])
        capability["independent_donor_count"] = donor_count
        capability["repeat_pattern"] = donor_count >= 2
        if donor_count == 0 and all_donors:
            capability["verification_state"] = "SUPPORT_OR_NONSOURCE_BOUND_ONLY"
    registry["schema"] = "glaciereq.capability-donor-registry.v2"
    registry["content_hash"] = _content_hash(registry)
    return registry


def _update_bundle_receipt(
    projected: dict[str, Any],
    *,
    policy: Mapping[str, Any],
    intelligence: Mapping[str, Mapping[str, Any]],
    supports: list[dict[str, Any]],
    capability_assertions: list[dict[str, Any]],
    reference: Mapping[str, Any],
    capability_registry: Mapping[str, Any],
    company_registry: Mapping[str, Any],
    support_only: set[str],
    experiment_ids: set[str],
    unresolved_ids: set[str],
) -> None:
    base_digest = projected.get("source_digest")
    projected["schema"] = "glaciereq.estate-intelligence.v2"
    projected["base_compiler_source_digest"] = base_digest
    projected["source_digest"] = digest(
        {
            "base_bundle_hash": projected.get("content_hash"),
            "base_source_digest": base_digest,
            "policy": policy,
            "company_intelligence": intelligence,
            "supports": supports,
            "capability_assertions": capability_assertions,
        }
    )
    receipt = projected["receipt"]
    receipt["schema"] = "glaciereq.estate-intelligence-receipt.v2"
    receipt["base_compiler_source_digest"] = base_digest
    receipt["source_digest"] = projected["source_digest"]
    receipt["counts"].update(
        {
            "raw_reference_graph_systems": len(reference["systems"]),
            "reference_accomplishments": reference[
                "reference_accomplishment_count"
            ],
            "support_references": len(supports),
            "capability_assertions_applied": len(capability_assertions),
            "support_only_systems": len(support_only),
            "experiment_systems_excluded_from_accomplishments": len(
                experiment_ids
            ),
            "unresolved_systems_excluded_from_accomplishments": len(
                unresolved_ids
            ),
        }
    )
    receipt["registry_hashes"] = {
        "system_registry": reference["content_hash"],
        "capability_donor_registry": capability_registry["content_hash"],
        "company_projection_registry": company_registry["content_hash"],
    }
    receipt["invariants"].update(
        {
            "support_references_do_not_collapse_lineage": True,
            "support_references_do_not_count_as_independent_accomplishments": True,
            "estate_capability_assertions_are_evidence_bound": True,
            "estate_capability_assertions_cannot_cross_namespace_boundary": True,
            "experiments_do_not_count_as_reference_accomplishments": True,
            "unresolved_lineage_does_not_count_as_reference_accomplishment": True,
            "target_company_relevance_is_role_capability_overlap": True,
            "observed_company_pressure_is_distinct_from_glaciereq_inference": True,
        }
    )


def _content_hash(value: Mapping[str, Any]) -> str:
    return digest(
        {
            key: item
            for key, item in value.items()
            if key != "content_hash"
        }
    )
