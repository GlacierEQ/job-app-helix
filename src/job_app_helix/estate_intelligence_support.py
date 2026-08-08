from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

SUPPORT_RELATIONS = {"DEPENDENCY_OF", "REFERENCE_OF"}


def repository_system_map(bundle: Mapping[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    for system in bundle["canonical_system_registry"]["systems"]:
        for repository in system.get("member_repositories", []):
            if isinstance(repository, str):
                result[repository] = str(system["system_id"])
    return result


def support_rows(
    facts: Mapping[str, Any] | None,
    repository_names: set[str],
) -> list[dict[str, Any]]:
    if not facts:
        return []
    rows = facts.get("supports", [])
    if not isinstance(rows, list):
        raise ValueError("estate facts supports must be a list")
    result: list[dict[str, Any]] = []
    seen: set[tuple[Any, Any, Any]] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"support row {index} must be an object")
        repository = row.get("repository")
        target = row.get("target")
        relation = row.get("relation")
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


def capabilities_by_system(bundle: Mapping[str, Any]) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    for capability in bundle["capability_donor_registry"]["capabilities"]:
        capability_id = capability.get("capability_id")
        if not isinstance(capability_id, str):
            continue
        for system_id in capability.get("donor_systems", []):
            if isinstance(system_id, str):
                result.setdefault(system_id, set()).add(capability_id)
    return result


def dynamic_score(
    components: Mapping[str, Any],
    relevance: float,
) -> tuple[float, dict[str, float]]:
    dynamic: dict[str, float] = {}
    keys = (
        "originality",
        "technical_depth",
        "verification_strength",
        "transferability",
    )
    for key in keys:
        value = components.get(key)
        if not isinstance(value, (int, float)):
            raise ValueError(f"promotion component {key} is missing")
        dynamic[key] = float(value)
    dynamic["target_company_relevance"] = float(relevance)
    return round(sum(dynamic.values()) / 5.0, 2), dynamic


def minimal_surface(
    rows: Sequence[Mapping[str, Any]],
    limit: int,
) -> list[str]:
    remaining = list(rows)
    selected: list[str] = []
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
        newly_covered = uncovered & set(best.get("capabilities", []))
        if selected and uncovered and not newly_covered:
            break
        selected.append(system_id)
        uncovered -= newly_covered
        remaining = [
            row
            for row in remaining
            if row.get("system_id") != system_id
        ]
    return selected


def company_intelligence_fields(
    company_id: str,
    intelligence: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
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
