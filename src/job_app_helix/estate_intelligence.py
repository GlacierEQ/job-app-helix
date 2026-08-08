from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import Any

from .estate_compiler import digest, public_safe_projection

SUPPORT_RELATIONS = {"DEPENDENCY_OF", "REFERENCE_OF"}


def _rules(policy: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = policy.get("role_capability_rules", [])
    if not isinstance(rows, list) or not rows:
        raise ValueError("role_capability_rules must be a non-empty list")
    result = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"role rule {index} must be an object")
        matches, capabilities = row.get("match_any"), row.get("capabilities")
        if (
            not isinstance(matches, list)
            or not all(isinstance(item, str) and item for item in matches)
            or not isinstance(capabilities, list)
            or not all(isinstance(item, str) and item for item in capabilities)
        ):
            raise ValueError(f"role rule {index} is invalid")
        result.append(
            {
                "match_any": [item.casefold() for item in matches],
                "capabilities": list(dict.fromkeys(capabilities)),
            }
        )
    return result


def role_profile(role: str, policy: Mapping[str, Any]) -> list[str]:
    text = role.casefold()
    desired = {
        capability
        for rule in _rules(policy)
        if any(token in text for token in rule["match_any"])
        for capability in rule["capabilities"]
    }
    return sorted(desired)


def role_fit(
    capabilities: Sequence[str], role: str, policy: Mapping[str, Any]
) -> dict[str, Any]:
    profile = role_profile(role, policy)
    if not profile:
        return {
            "fit_score": 0.0,
            "coverage_state": "UNMAPPED_ROLE",
            "profile_capabilities": [],
            "matched_capabilities": [],
        }
    matched = sorted(set(capabilities) & set(profile))
    return {
        "fit_score": round(100.0 * len(matched) / len(profile), 2),
        "coverage_state": "MAPPED_ROLE",
        "profile_capabilities": profile,
        "matched_capabilities": matched,
    }


def _repo_to_system(bundle: Mapping[str, Any]) -> dict[str, str]:
    result = {}
    for system in bundle["canonical_system_registry"]["systems"]:
        for repository in system.get("member_repositories", []):
            if isinstance(repository, str):
                result[repository] = str(system["system_id"])
    return result


def _support_rows(
    facts: Mapping[str, Any] | None, repository_names: set[str]
) -> list[dict[str, Any]]:
    if not facts:
        return []
    rows = facts.get("supports", [])
    if not isinstance(rows, list):
        raise ValueError("estate facts supports must be a list")
    result, seen = [], set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"support row {index} must be an object")
        repository, target, relation = (
            row.get("repository"),
            row.get("target"),
            row.get("relation"),
        )
        refs = row.get("evidence_refs")
        if repository not in repository_names or target not in repository_names:
            raise ValueError(f"support row {index} references unknown repository")
        if relation not in SUPPORT_RELATIONS:
            raise ValueError(f"support row {index} has invalid relation")
        if (
            not isinstance(refs, list)
            or not refs
            or not all(isinstance(item, str) and item for item in refs)
        ):
            raise ValueError(f"support row {index} requires evidence_refs")
        key = (repository, relation, target)
        if key in seen:
            raise ValueError(f"duplicate support assertion: {key}")
        seen.add(key)
        result.append(
            {
                "repository": repository,
                "relation": relation,
                "target": target,
                "evidence_refs": list(refs),
                "collapse_lineage": False,
                "counts_as_independent_accomplishment": False,
            }
        )
    return result


def _caps_by_system(bundle: Mapping[str, Any]) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    for capability in bundle["capability_donor_registry"]["capabilities"]:
        capability_id = capability.get("capability_id")
        if not isinstance(capability_id, str):
            continue
        for system_id in capability.get("donor_systems", []):
            if isinstance(system_id, str):
                result.setdefault(system_id, set()).add(capability_id)
    return result


def _dynamic_score(components: Mapping[str, Any], relevance: float) -> tuple[float, dict[str, float]]:
    dynamic = {}
    for key in ("originality", "technical_depth", "verification_strength", "transferability"):
        value = components.get(key)
        if not isinstance(value, (int, float)):
            raise ValueError(f"promotion component {key} is missing")
        dynamic[key] = float(value)
    dynamic["target_company_relevance"] = float(relevance)
    return round(sum(dynamic.values()) / 5.0, 2), dynamic


def _minimal_surface(rows: Sequence[Mapping[str, Any]], limit: int) -> list[str]:
    remaining, selected = list(rows), []
    uncovered = {
        capability
        for row in remaining
        for capability in row.get("capabilities", [])
        if isinstance(capability, str)
    }
    while remaining and len(selected) < limit:
        best = max(
            remaining,
            key=lambda row: (
                len(uncovered & set(row.get("capabilities", []))),
                float(row.get("promotion_score", 0.0)),
                str(row.get("system_id", "")),
            ),
        )
        system_id = str(best["system_id"])
        new = uncovered & set(best.get("capabilities", []))
        if selected and uncovered and not new:
            break
        selected.append(system_id)
        uncovered -= new
        remaining = [row for row in remaining if row.get("system_id") != system_id]
    return selected


def _intel(company_id: str, intelligence: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    row = intelligence.get(company_id)
    if not isinstance(row, Mapping):
        return {
            "intelligence_state": "NOT_LOADED",
            "observed_operating_pressure": None,
            "inferred_bottleneck": None,
            "inferred_brick_wall": None,
            "application_move": None,
            "official_sources": [],
            "research_as_of": None,
            "freshness_state": None,
            "inference_boundary": None,
        }
    return {
        "intelligence_state": "SOURCE_BACKED_SNAPSHOT",
        "observed_operating_pressure": row.get("observed_current_pressure"),
        "inferred_bottleneck": row.get("inferred_bottleneck"),
        "inferred_brick_wall": row.get("inferred_brick_wall"),
        "leverage_mechanism": row.get("leverage_mechanism"),
        "expected_impact": row.get("expected_impact"),
        "application_move": row.get("application_move"),
        "next_deep_dive": row.get("next_deep_dive"),
        "official_sources": list(row.get("official_sources", [])),
        "research_as_of": row.get("research_as_of"),
        "freshness_state": row.get("freshness_state"),
        "inference_boundary": row.get("inference_boundary"),
    }


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
    _rules(policy)

    repo_names = {
        row["repository"]
        for row in (census or {}).get("repositories", [])
        if isinstance(row, dict) and isinstance(row.get("repository"), str)
    }
    repo_to_system = _repo_to_system(projected)
    support_only, supports = set(), []
    for row in _support_rows(estate_facts, repo_names) if census else []:
        source_id, target_id = repo_to_system.get(row["repository"]), repo_to_system.get(row["target"])
        if target_id is None:
            raise ValueError(f"support target is not canonical: {row['target']}")
        if source_id is not None and source_id == target_id:
            raise ValueError(f"support assertion resolves inside one lineage: {row['repository']}")
        if source_id is not None:
            support_only.add(source_id)
        supports.append({**row, "source_system_id": source_id, "target_system_id": target_id})

    canonical = projected["canonical_system_registry"]
    experiment_ids = {
        row["system_id"]
        for row in projected.get("experiment_pipeline", [])
        if isinstance(row, dict) and isinstance(row.get("system_id"), str)
    }
    unresolved_ids = {
        row["system_id"] for row in canonical["systems"] if row.get("lineage_complete") is False
    }
    archived_ids = {row["system_id"] for row in canonical["systems"] if row.get("archived") is True}
    excluded = support_only | experiment_ids | unresolved_ids | archived_ids

    for system in canonical["systems"]:
        sid = str(system["system_id"])
        reasons = []
        if sid in support_only:
            reasons.append("SUPPORT_REFERENCE_ONLY")
        if sid in experiment_ids:
            reasons.append("EXPERIMENT")
        if sid in unresolved_ids:
            reasons.append("UNRESOLVED_LINEAGE")
        if sid in archived_ids:
            reasons.append("ARCHIVED_ROOT")
        system["counts_as_independent_accomplishment"] = not reasons
        system["accomplishment_exclusion_reasons"] = reasons
    canonical["schema"] = "glaciereq.canonical-system-registry.v2"
    canonical["raw_canonical_graph_system_count"] = len(canonical["systems"])
    canonical["canonical_accomplishment_count"] = sum(
        row["counts_as_independent_accomplishment"] for row in canonical["systems"]
    )
    canonical["support_references"] = supports
    canonical["content_hash"] = digest({k: v for k, v in canonical.items() if k != "content_hash"})

    capability_registry = projected["capability_donor_registry"]
    for capability in capability_registry["capabilities"]:
        all_donors = list(capability.get("donor_systems", []))
        capability["all_donor_systems"] = all_donors
        capability["excluded_non_accomplishment_donors"] = [sid for sid in all_donors if sid in excluded]
        capability["donor_systems"] = [sid for sid in all_donors if sid not in excluded]
        capability["independent_donor_count"] = len(capability["donor_systems"])
        capability["repeat_pattern"] = capability["independent_donor_count"] >= 2
        if not capability["donor_systems"] and all_donors:
            capability["verification_state"] = "SUPPORT_OR_NONCANONICAL_ONLY"
    capability_registry["schema"] = "glaciereq.capability-donor-registry.v2"
    capability_registry["content_hash"] = digest(
        {k: v for k, v in capability_registry.items() if k != "content_hash"}
    )
    caps = _caps_by_system(projected)

    company_registry = projected["company_projection_registry"]
    global_scores = company_registry.get("promotion_scores", {})
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
    company_scores = {}
    for projection in company_registry["projections"]:
        company_id = str(projection["company_id"])
        roles = [role for role in projection.get("target_roles", []) if isinstance(role, str) and role]
        ranked, fits_by_system = [], {}
        for row in projection.get("ranked_evidence", []):
            sid = str(row["system_id"])
            if sid in excluded:
                continue
            system_caps = sorted(caps.get(sid, set()))
            fits = {role: role_fit(system_caps, role, policy) for role in roles}
            fits_by_system[sid] = fits
            relevance = max((float(fit["fit_score"]) for fit in fits.values()), default=0.0)
            base = global_scores.get(sid, {}).get("components", {})
            total, components = _dynamic_score(base, relevance)
            enriched = {
                **row,
                "legacy_promotion_score": row.get("promotion_score"),
                "promotion_score": total,
                "promotion_score_components": components,
                "capabilities": system_caps,
                "target_relevance_state": (
                    "ROLE_CAPABILITY_OVERLAP"
                    if any(fit["coverage_state"] == "MAPPED_ROLE" for fit in fits.values())
                    else "UNMAPPED_ROLE_ZERO"
                ),
            }
            ranked.append(enriched)
            company_scores[f"{company_id}:{sid}"] = {
                "company_id": company_id,
                "system_id": sid,
                "promotion_score": total,
                "components": components,
                "role_fit": fits,
            }
        ranked.sort(key=lambda row: (-float(row["promotion_score"]), str(row["system_id"])))
        projection["ranked_evidence"] = ranked
        projection["canonical_systems"] = [row["system_id"] for row in ranked]
        projection["capabilities"] = sorted({cap for row in ranked for cap in row["capabilities"]})
        projection["minimal_proof_surface"] = _minimal_surface(ranked, caps_by_audience["company_reviewer"])
        projection["projection_innovation"] = "bounded_greedy_capability_set_cover_with_role_relevance"
        projection["role_projection"] = {}
        for role in roles:
            profile = role_profile(role, policy)
            role_rows = [
                {
                    "system_id": row["system_id"],
                    "fit_score": fits_by_system[str(row["system_id"])][role]["fit_score"],
                    "matched_capabilities": fits_by_system[str(row["system_id"])][role]["matched_capabilities"],
                    "promotion_score": row["promotion_score"],
                }
                for row in ranked
                if fits_by_system[str(row["system_id"])][role]["fit_score"] > 0
            ]
            role_rows.sort(key=lambda item: (-float(item["fit_score"]), -float(item["promotion_score"]), str(item["system_id"])))
            projection["role_projection"][role] = {
                "profile_capabilities": profile,
                "coverage_state": "MAPPED_ROLE" if profile else "UNMAPPED_ROLE",
                "systems": role_rows,
            }
        proof_ids = projection["minimal_proof_surface"]
        projection["audience_projection"] = {
            "recruiter": proof_ids[: caps_by_audience["recruiter"]],
            "company_reviewer": proof_ids[: caps_by_audience["company_reviewer"]],
            "senior_engineer": [row["system_id"] for row in ranked[: caps_by_audience["senior_engineer"]]],
        }
        projection["dossier_next_gate"] = projection.get("operating_problem")
        projection.update(_intel(company_id, intelligence))

    company_registry["schema"] = "glaciereq.company-projection-registry.v2"
    company_registry["company_promotion_scores"] = company_scores
    company_registry["policy"]["target_company_relevance"] = "max capability overlap across declared target roles"
    company_registry["policy"]["support_references_are_not_accomplishments"] = True
    company_registry["content_hash"] = digest({k: v for k, v in company_registry.items() if k != "content_hash"})

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
        }
    )
    receipt = projected["receipt"]
    receipt["schema"] = "glaciereq.estate-intelligence-receipt.v2"
    receipt["base_compiler_source_digest"] = base_digest
    receipt["source_digest"] = projected["source_digest"]
    receipt["counts"].update(
        {
            "raw_canonical_graph_systems": len(canonical["systems"]),
            "canonical_accomplishments": canonical["canonical_accomplishment_count"],
            "support_references": len(supports),
            "support_only_systems": len(support_only),
            "experiment_systems_excluded_from_accomplishments": len(experiment_ids),
            "unresolved_systems_excluded_from_accomplishments": len(unresolved_ids),
        }
    )
    receipt["registry_hashes"] = {
        "canonical_system_registry": canonical["content_hash"],
        "capability_donor_registry": capability_registry["content_hash"],
        "company_projection_registry": company_registry["content_hash"],
    }
    receipt["invariants"].update(
        {
            "support_references_do_not_collapse_lineage": True,
            "support_references_do_not_count_as_independent_accomplishments": True,
            "experiments_do_not_count_as_canonical_accomplishments": True,
            "unresolved_lineage_does_not_count_as_canonical_accomplishment": True,
            "target_company_relevance_is_role_capability_overlap": True,
            "observed_company_pressure_is_distinct_from_glaciereq_inference": True,
        }
    )
    projected["content_hash"] = digest({k: v for k, v in projected.items() if k != "content_hash"})
    return projected


def public_intelligence_projection(bundle: Mapping[str, Any]) -> dict[str, Any]:
    public = public_safe_projection(bundle)
    internal = {row["company_id"]: row for row in bundle["company_projection_registry"]["projections"]}
    for projection in public["company_projections"]:
        source = internal[str(projection["company_id"])]
        safe_ids = {row["system_id"] for row in projection.get("ranked_evidence", [])}
        for key in (
            "observed_operating_pressure", "inferred_bottleneck", "inferred_brick_wall",
            "leverage_mechanism", "expected_impact", "application_move", "next_deep_dive",
            "official_sources", "research_as_of", "freshness_state", "inference_boundary",
            "intelligence_state", "dossier_next_gate",
        ):
            projection[key] = source.get(key)
        projection["minimal_proof_surface"] = [sid for sid in source.get("minimal_proof_surface", []) if sid in safe_ids]
        projection["audience_projection"] = {
            audience: [sid for sid in systems if sid in safe_ids]
            for audience, systems in source.get("audience_projection", {}).items()
        }
        projection["role_projection"] = {
            role: {
                "profile_capabilities": data.get("profile_capabilities", []),
                "coverage_state": data.get("coverage_state"),
                "systems": [row for row in data.get("systems", []) if row.get("system_id") in safe_ids],
            }
            for role, data in source.get("role_projection", {}).items()
        }
        by_system = {row["system_id"]: row for row in source.get("ranked_evidence", [])}
        projection["ranked_evidence"] = [
            {
                **row,
                "promotion_score": by_system.get(row["system_id"], {}).get("promotion_score", row.get("promotion_score")),
                "promotion_score_components": by_system.get(row["system_id"], {}).get("promotion_score_components"),
                "capabilities": by_system.get(row["system_id"], {}).get("capabilities", []),
            }
            for row in projection.get("ranked_evidence", [])
        ]

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
