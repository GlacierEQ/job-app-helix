from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

SUPPORT_RELATIONS = {"DEPENDENCY_OF", "REFERENCE_OF"}
CAPABILITY_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def repository_system_map(bundle: Mapping[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    for system in bundle["system_registry"]["systems"]:
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


def capability_rows(
    facts: Mapping[str, Any] | None,
    repository_names: set[str],
) -> list[dict[str, Any]]:
    if not facts:
        return []
    rows = facts.get("capabilities", [])
    if not isinstance(rows, list):
        raise ValueError("estate facts capabilities must be a list")
    result: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"capability row {index} must be an object")
        repository = row.get("repository")
        capability_id = row.get("capability_id")
        refs = row.get("evidence_refs")
        evidence = row.get("evidence")
        if repository not in repository_names:
            raise ValueError(f"capability row {index} references unknown repository")
        if not isinstance(capability_id, str) or not CAPABILITY_ID.fullmatch(capability_id):
            raise ValueError(f"capability row {index} has invalid capability_id")
        if (
            not isinstance(refs, list)
            or not refs
            or not all(isinstance(item, str) and item for item in refs)
        ):
            raise ValueError(f"capability row {index} requires evidence_refs")
        if evidence is not None and (
            not isinstance(evidence, str) or not evidence.strip()
        ):
            raise ValueError(f"capability row {index} evidence must be a non-empty string")
        key = (repository, capability_id)
        if key in seen:
            raise ValueError(f"duplicate capability assertion: {key}")
        seen.add(key)
        result.append(
            {
                "repository": repository,
                "capability_id": capability_id,
                "evidence_refs": list(refs),
                "evidence": evidence,
                "verification_state": "EVIDENCE_BOUND",
            }
        )
    return result


def apply_capability_assertions(
    bundle: dict[str, Any],
    facts: Mapping[str, Any] | None,
    census: Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    rows = facts.get("capabilities", []) if facts else []
    if not rows:
        return []
    if census is None:
        raise ValueError("capability assertions require the authenticated census")

    repository_names = {
        row["repository"]
        for row in census.get("repositories", [])
        if isinstance(row, dict) and isinstance(row.get("repository"), str)
    }
    assertions = capability_rows(facts, repository_names)
    repo_to_system = repository_system_map(bundle)
    registry = bundle["capability_donor_registry"]
    capabilities = registry.get("capabilities", [])
    if not isinstance(capabilities, list):
        raise ValueError("capability donor registry capabilities must be a list")

    by_id: dict[str, dict[str, Any]] = {}
    for row in capabilities:
        capability_id = row.get("capability_id") if isinstance(row, dict) else None
        if not isinstance(capability_id, str):
            raise ValueError("capability donor registry contains invalid capability row")
        by_id[capability_id] = row

    applied: list[dict[str, Any]] = []
    for assertion in assertions:
        repository = assertion["repository"]
        system_id = repo_to_system.get(repository)
        if system_id is None:
            raise ValueError(
                "capability assertion must resolve to a reference engineering system: "
                f"{repository}"
            )
        capability_id = assertion["capability_id"]
        capability = by_id.get(capability_id)
        if capability is None:
            capability = {
                "capability_id": capability_id,
                "donor_systems": [],
                "independent_donor_count": 0,
                "repeat_pattern": False,
                "proof_refs": [],
                "verification_state": "EVIDENCE_BOUND",
            }
            capabilities.append(capability)
            by_id[capability_id] = capability

        donor_systems = capability.setdefault("donor_systems", [])
        if system_id not in donor_systems:
            donor_systems.append(system_id)
            donor_systems.sort()

        proof_refs = capability.setdefault("proof_refs", [])
        proof = {
            "system_id": system_id,
            "source": "estate_facts.capabilities",
            "repository": repository,
            "evidence_refs": assertion["evidence_refs"],
        }
        if assertion.get("evidence"):
            proof["evidence"] = assertion["evidence"]
        if proof not in proof_refs:
            proof_refs.append(proof)

        capability["independent_donor_count"] = len(donor_systems)
        capability["repeat_pattern"] = len(donor_systems) >= 2
        capability["verification_state"] = "EVIDENCE_BOUND"
        applied.append(
            {
                **assertion,
                "system_id": system_id,
            }
        )

    capabilities.sort(key=lambda row: str(row["capability_id"]))
    policy = registry.setdefault("policy", {})
    policy["estate_capability_assertions_require_evidence_refs"] = True
    policy["estate_capability_assertions_require_reference_engineering_system"] = True
    return applied


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
            row for row in remaining if row.get("system_id") != system_id
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
