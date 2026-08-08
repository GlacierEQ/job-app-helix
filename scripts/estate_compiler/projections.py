from __future__ import annotations

from typing import Any

from discover_experience_graph import digest

from .common import EstateCompilerError

PUBLIC_STATES = {"PROMOTED", "REFERENCE_ONLY"}


def _score(
    repo_meta: dict[str, Any],
    assessment: dict[str, Any] | None,
    capabilities: list[str],
    policy: dict[str, Any],
) -> dict[str, Any]:
    weights = policy.get("promotion_score_weights", {})
    keys = {
        "originality",
        "technical_depth",
        "verification",
        "transferability",
        "target_relevance",
    }
    if not isinstance(weights, dict) or set(weights) != keys:
        raise EstateCompilerError("promotion_score_weights must define five dimensions")
    numeric = {key: float(value) for key, value in weights.items()}
    if abs(sum(numeric.values()) - 1.0) > 1e-9:
        raise EstateCompilerError("promotion_score_weights must sum to 1.0")

    originality = {
        "ORIGINAL_VERIFIED": 100.0,
        "ORIGINAL_CANDIDATE": 60.0,
        "UPSTREAM": 0.0,
        "UPSTREAM_OR_SAMPLE": 0.0,
        "UPSTREAM_SAMPLE": 0.0,
        "UPSTREAM_SHAPED": 10.0,
    }.get(repo_meta.get("provenance_state"))
    depth = verification = None
    if assessment:
        dimensions = assessment.get("dimensions", {})
        values = []
        if isinstance(dimensions, dict):
            for key in ("architecture", "reality", "integration", "ai_readiness"):
                dimension = dimensions.get(key)
                raw = dimension.get("raw_score") if isinstance(dimension, dict) else None
                if isinstance(raw, (int, float)) and 0 <= raw <= 100:
                    values.append(float(raw))
        if values:
            depth = sum(values) / len(values)
        coverage = assessment.get("evidence_coverage")
        health = assessment.get("health_score")
        if isinstance(coverage, (int, float)) and isinstance(health, (int, float)):
            verification = (float(coverage) + float(health)) / 2

    taxonomy_size = len(policy.get("capability_taxonomy", {}))
    transferability = (
        min(100.0, 35 + 65 * len(capabilities) / taxonomy_size)
        if capabilities and taxonomy_size
        else None
    )
    components = {
        "originality": originality,
        "technical_depth": depth,
        "verification": verification,
        "transferability": transferability,
        "target_relevance": 100.0,
    }
    coverage = sum(
        numeric[key] for key, value in components.items() if value is not None
    )
    complete = abs(coverage - 1.0) < 1e-9
    value = sum((components[key] or 0.0) * numeric[key] for key in keys)
    return {
        "score": round(value, 2) if complete else None,
        "coverage": round(coverage, 4),
        "complete": complete,
        "components": components,
        "public_visibility_derived_separately": True,
    }


def _company_state(company_id: str, second_depth: dict[str, Any]) -> dict[str, Any]:
    default = second_depth.get("default_company_state", {})
    overrides = second_depth.get("company_overrides", {})
    if not isinstance(default, dict) or not isinstance(overrides, dict):
        raise EstateCompilerError("Second-depth registry is invalid")
    override = overrides.get(company_id, {})
    if not isinstance(override, dict):
        raise EstateCompilerError(f"Invalid second-depth override: {company_id}")
    return {**default, **override}


def build_company_registry(
    companies: dict[str, dict[str, Any]],
    repo_meta: dict[str, dict[str, Any]],
    second_depth: dict[str, Any],
    canonical: dict[str, Any],
    repo_to_system: dict[str, str],
    capability_by_system: dict[str, list[str]],
    assessment_by_repo: dict[str, dict[str, Any]],
    policy: dict[str, Any],
) -> dict[str, Any]:
    systems = {item["system_id"]: item for item in canonical["systems"]}
    caps = policy.get("audience_caps", {})
    limits = {
        "recruiter": int(caps.get("recruiter", 10)),
        "senior_engineer": int(caps.get("senior_engineer", 20)),
        "company_reviewer": int(caps.get("company_reviewer", 5)),
    }
    output = []
    for company_id, company in sorted(companies.items()):
        candidates: dict[str, dict[str, Any]] = {}
        for row in company.get("repositories", []):
            repo = row.get("repository")
            sid = repo_to_system.get(repo) if isinstance(repo, str) else None
            if not sid or sid not in systems:
                continue
            root_repo = systems[sid]["canonical_repository"]
            candidates[sid] = {
                "system_id": sid,
                "visibility": row.get("visibility"),
                "company_repository_state": row.get("promotion_state"),
                "capabilities": capability_by_system.get(sid, []),
                "promotion_score": _score(
                    repo_meta.get(root_repo, {}),
                    assessment_by_repo.get(root_repo),
                    capability_by_system.get(sid, []),
                    policy,
                ),
            }
        ordered = sorted(
            candidates.values(),
            key=lambda item: (
                0 if item["promotion_score"]["score"] is not None else 1,
                -(item["promotion_score"]["score"] or 0),
                item["system_id"],
            ),
        )
        state = _company_state(company_id, second_depth)
        output.append(
            {
                "company_id": company_id,
                "display_name": company.get("display_name", company_id),
                "track_state": company.get("track_state"),
                "target_roles": company.get("target_roles", []),
                "recruiter_thesis": company.get("recruiter_thesis"),
                "second_depth_stage": state.get("stage"),
                "claim_ceiling": state.get("claim_ceiling"),
                "problem_evidence": state.get("problem_evidence", []),
                "next_gate": state.get("next_gate"),
                "system_candidates": ordered,
                "audience_projection": {
                    name: [item["system_id"] for item in ordered[:limit]]
                    for name, limit in limits.items()
                },
            }
        )
    result = {
        "schema": "glaciereq.company-projection-registry.v1",
        "audience_caps": limits,
        "truth_boundary": {
            "company_pages_are_projections_of_one_graph": True,
            "unbounded_company_bottlenecks_are_not_invented": True,
            "promotion_score_never_overrides_public_safety": True,
        },
        "companies": output,
    }
    result["registry_id"] = digest(result)
    return result


def build_public_projection(
    canonical: dict[str, Any],
    capabilities: dict[str, Any],
    companies: dict[str, Any],
) -> dict[str, Any]:
    public_ids = {
        item["system_id"]
        for item in canonical["systems"]
        if item.get("visibility") == "public"
        and item.get("public_surface") in {"PUBLIC", None}
    }
    public_systems = [
        {
            key: item.get(key)
            for key in ("system_id", "canonical_repository", "flagship_level", "role")
        }
        for item in canonical["systems"]
        if item["system_id"] in public_ids
    ]
    public_capabilities = []
    for row in capabilities["capabilities"]:
        donors = [
            {"system_id": donor["system_id"]}
            for donor in row["donors"]
            if donor["system_id"] in public_ids
        ]
        if donors:
            public_capabilities.append(
                {
                    "capability": row["capability"],
                    "donor_system_count": len(donors),
                    "repetition_state": (
                        "MULTI_SYSTEM_PATTERN"
                        if len(donors) >= 2
                        else "SINGLE_SYSTEM_SIGNAL"
                    ),
                    "donors": donors,
                }
            )
    public_companies = []
    for company in companies["companies"]:
        systems = [
            {
                "system_id": row["system_id"],
                "capabilities": row["capabilities"],
                "promotion_score": row["promotion_score"],
            }
            for row in company["system_candidates"]
            if row["system_id"] in public_ids
            and row.get("visibility") == "public"
            and row.get("company_repository_state") in PUBLIC_STATES
        ]
        allowed = {row["system_id"] for row in systems}
        public_companies.append(
            {
                **{
                    key: company.get(key)
                    for key in (
                        "company_id",
                        "display_name",
                        "track_state",
                        "target_roles",
                        "recruiter_thesis",
                        "second_depth_stage",
                        "claim_ceiling",
                        "next_gate",
                    )
                },
                "systems": systems,
                "audience_projection": {
                    name: [sid for sid in values if sid in allowed]
                    for name, values in company["audience_projection"].items()
                },
            }
        )
    result = {
        "schema": "glaciereq.public-portfolio-projection.v1",
        "truth_boundary": {
            "native_estate_cardinality_intentionally_not_published": True,
            "private_repository_identities_omitted": True,
            "restricted_namespaces_omitted": True,
            "projection_is_derived_not_hand_curated": True,
        },
        "systems": public_systems,
        "capabilities": public_capabilities,
        "companies": public_companies,
    }
    result["projection_id"] = digest(result)
    return result
