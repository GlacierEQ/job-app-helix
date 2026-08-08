from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .estate_intelligence_roles import role_fit, role_profile
from .estate_intelligence_support import (
    capabilities_by_system,
    company_intelligence_fields,
    dynamic_score,
    minimal_surface,
)


def enrich_company_registry(
    projected: dict[str, Any],
    *,
    policy: Mapping[str, Any],
    intelligence: Mapping[str, Mapping[str, Any]],
    excluded: set[str],
) -> None:
    capabilities = capabilities_by_system(projected)
    registry = projected["company_projection_registry"]
    global_scores = registry.get("promotion_scores", {})
    if not isinstance(global_scores, dict):
        raise ValueError("company promotion_scores must be an object")
    audience = policy.get("audience_caps", {})
    if not isinstance(audience, dict):
        raise ValueError("audience_caps must be an object")
    caps_by_audience = {
        "recruiter": int(audience.get("recruiter", 10)),
        "company_reviewer": int(audience.get("company_reviewer", 5)),
        "senior_engineer": int(audience.get("senior_engineer", 20)),
    }

    company_scores: dict[str, Any] = {}
    for projection in registry["projections"]:
        company_id = str(projection["company_id"])
        roles = [
            role
            for role in projection.get("target_roles", [])
            if isinstance(role, str) and role
        ]
        ranked: list[dict[str, Any]] = []
        fits_by_system: dict[str, dict[str, dict[str, Any]]] = {}
        for row in projection.get("ranked_evidence", []):
            system_id = str(row["system_id"])
            if system_id in excluded:
                continue
            system_capabilities = sorted(capabilities.get(system_id, set()))
            fits = {
                role: role_fit(system_capabilities, role, policy)
                for role in roles
            }
            fits_by_system[system_id] = fits
            relevance = max(
                (float(fit["fit_score"]) for fit in fits.values()),
                default=0.0,
            )
            components = global_scores.get(system_id, {}).get("components", {})
            score, dynamic_components = dynamic_score(components, relevance)
            enriched = {
                **row,
                "legacy_promotion_score": row.get("promotion_score"),
                "promotion_score": score,
                "promotion_score_components": dynamic_components,
                "capabilities": system_capabilities,
                "target_relevance_state": _relevance_state(fits),
            }
            ranked.append(enriched)
            company_scores[f"{company_id}:{system_id}"] = {
                "company_id": company_id,
                "system_id": system_id,
                "promotion_score": score,
                "components": dynamic_components,
                "role_fit": fits,
            }

        ranked.sort(
            key=lambda row: (
                -float(row["promotion_score"]),
                str(row["system_id"]),
            )
        )
        projection["ranked_evidence"] = ranked
        projection["canonical_systems"] = [
            row["system_id"] for row in ranked
        ]
        projection["capabilities"] = sorted(
            {
                capability
                for row in ranked
                for capability in row["capabilities"]
            }
        )
        projection["minimal_proof_surface"] = minimal_surface(
            ranked,
            caps_by_audience["company_reviewer"],
        )
        projection["projection_innovation"] = (
            "bounded_greedy_capability_set_cover_with_role_relevance"
        )
        projection["role_projection"] = _role_projection(
            ranked,
            roles,
            fits_by_system,
            policy,
        )
        proof_ids = projection["minimal_proof_surface"]
        projection["audience_projection"] = {
            "recruiter": proof_ids[: caps_by_audience["recruiter"]],
            "company_reviewer": proof_ids[
                : caps_by_audience["company_reviewer"]
            ],
            "senior_engineer": [
                row["system_id"]
                for row in ranked[: caps_by_audience["senior_engineer"]]
            ],
        }
        projection["dossier_next_gate"] = projection.get("operating_problem")
        projection.update(company_intelligence_fields(company_id, intelligence))

    registry["schema"] = "glaciereq.company-projection-registry.v2"
    registry["company_promotion_scores"] = company_scores
    registry["policy"]["target_company_relevance"] = (
        "max capability overlap across declared target roles"
    )
    registry["policy"]["support_references_are_not_accomplishments"] = True


def _relevance_state(
    fits: Mapping[str, Mapping[str, Any]],
) -> str:
    if any(
        fit.get("coverage_state") == "MAPPED_ROLE"
        for fit in fits.values()
    ):
        return "ROLE_CAPABILITY_OVERLAP"
    return "UNMAPPED_ROLE_ZERO"


def _role_projection(
    ranked: list[dict[str, Any]],
    roles: list[str],
    fits_by_system: Mapping[str, Mapping[str, Mapping[str, Any]]],
    policy: Mapping[str, Any],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for role in roles:
        profile = role_profile(role, policy)
        rows: list[dict[str, Any]] = []
        for ranked_row in ranked:
            system_id = str(ranked_row["system_id"])
            fit = fits_by_system[system_id][role]
            if float(fit["fit_score"]) <= 0:
                continue
            rows.append(
                {
                    "system_id": system_id,
                    "fit_score": fit["fit_score"],
                    "matched_capabilities": fit["matched_capabilities"],
                    "promotion_score": ranked_row["promotion_score"],
                }
            )
        rows.sort(
            key=lambda item: (
                -float(item["fit_score"]),
                -float(item["promotion_score"]),
                str(item["system_id"]),
            )
        )
        result[role] = {
            "profile_capabilities": profile,
            "coverage_state": "MAPPED_ROLE" if profile else "UNMAPPED_ROLE",
            "systems": rows,
        }
    return result
