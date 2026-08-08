from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .estate_compiler import public_safe_projection

PUBLIC_FIELDS = (
    "observed_operating_pressure",
    "inferred_bottleneck",
    "inferred_brick_wall",
    "leverage_mechanism",
    "expected_impact",
    "application_move",
    "next_deep_dive",
    "official_sources",
    "research_as_of",
    "freshness_state",
    "inference_boundary",
    "intelligence_state",
    "dossier_next_gate",
)


def public_intelligence_projection(
    bundle: Mapping[str, Any],
) -> dict[str, Any]:
    public = public_safe_projection(bundle)
    internal = {
        row["company_id"]: row
        for row in bundle["company_projection_registry"]["projections"]
    }
    for projection in public["company_projections"]:
        source = internal[str(projection["company_id"])]
        safe_ids = {
            row["system_id"]
            for row in projection.get("ranked_evidence", [])
        }
        for key in PUBLIC_FIELDS:
            projection[key] = source.get(key)
        projection["minimal_proof_surface"] = [
            system_id
            for system_id in source.get("minimal_proof_surface", [])
            if system_id in safe_ids
        ]
        projection["audience_projection"] = {
            audience: [
                system_id
                for system_id in systems
                if system_id in safe_ids
            ]
            for audience, systems in source.get(
                "audience_projection",
                {},
            ).items()
        }
        projection["role_projection"] = _public_role_projection(
            source,
            safe_ids,
        )
        projection["ranked_evidence"] = _public_ranked_evidence(
            projection,
            source,
        )

    public["schema"] = "glaciereq.estate-public-projection.v2"
    public["boundary"] = {
        "private_repository_identities_omitted": True,
        "legal_private_records_omitted": True,
        "support_only_systems_omitted_from_accomplishment_projection": True,
        "experiment_systems_omitted_from_accomplishment_projection": True,
        "unresolved_lineage_omitted_from_accomplishment_projection": True,
        "native_estate_cardinality_intentionally_not_published": True,
        "observed_pressure_and_inferred_bottleneck_are_distinct": True,
        "role_projection_is_capability_fit_not_employer_endorsement": True,
    }
    return public


def _public_role_projection(
    source: Mapping[str, Any],
    safe_ids: set[str],
) -> dict[str, Any]:
    return {
        role: {
            "profile_capabilities": data.get("profile_capabilities", []),
            "coverage_state": data.get("coverage_state"),
            "systems": [
                row
                for row in data.get("systems", [])
                if row.get("system_id") in safe_ids
            ],
        }
        for role, data in source.get("role_projection", {}).items()
    }


def _public_ranked_evidence(
    projection: Mapping[str, Any],
    source: Mapping[str, Any],
) -> list[dict[str, Any]]:
    by_system = {
        row["system_id"]: row
        for row in source.get("ranked_evidence", [])
    }
    result: list[dict[str, Any]] = []
    for row in projection.get("ranked_evidence", []):
        system_id = row["system_id"]
        internal = by_system.get(system_id, {})
        result.append(
            {
                **row,
                "promotion_score": internal.get(
                    "promotion_score",
                    row.get("promotion_score"),
                ),
                "promotion_score_components": internal.get(
                    "promotion_score_components"
                ),
                "capabilities": internal.get("capabilities", []),
            }
        )
    return result
