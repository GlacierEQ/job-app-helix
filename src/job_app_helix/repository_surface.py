"""Fail-closed repository-surface admission for public portfolio compilation."""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from .repository_health import sha256_json

ADMISSION_STATES = {
    "ADMIT",
    "REPAIR_REQUIRED",
    "INTERNAL_ONLY",
    "STALE_AUTHORITY",
    "SUPERSEDED",
    "QUARANTINED",
    "REFERENCE",
}
ASSESSMENT_STATES = {"UNASSESSED", "PARTIAL", "COMPLETE"}
LINEAGE_STATES = {
    "FLAGSHIP",
    "ACTIVE_SYSTEM",
    "CAPABILITY_DONOR",
    "EXPERIMENT",
    "REFERENCE",
    "SUPERSEDED",
    "ARCHIVED_PROVENANCE",
    "QUARANTINED",
}
EVIDENCE_LEVELS = {
    "INVENTORY",
    "DOCUMENTATION",
    "STATIC_ANALYSIS",
    "BUILD",
    "TEST",
    "INTEGRATION",
    "DEPLOYMENT",
    "UNASSESSED",
}
GOVERNED_DECISION_STATES = {
    "ADMIT",
    "REPAIR_REQUIRED",
    "QUARANTINED",
    "REFERENCE",
    "SUPERSEDED",
}
GOVERNED_DECISION_SCHEMA = "glaciereq.public-repository-surface-decisions.v1"
ADMIT_FORBIDDEN_BASE_ADMISSIONS = {
    "INTERNAL_ONLY",
    "QUARANTINED",
    "STALE_AUTHORITY",
    "SUPERSEDED",
}
ADMIT_FORBIDDEN_LINEAGE_STATES = {
    "QUARANTINED",
    "SUPERSEDED",
    "ARCHIVED_PROVENANCE",
}
ADMIT_FORBIDDEN_FINDINGS = {
    "AFFILIATION_RISK",
    "COMPANY_AFFILIATION_BOUNDARY_MISSING",
    "COMPANY_AFFILIATION_BOUNDARY_UNRESOLVED",
    "INTEGRATION_OR_DEPLOYMENT_CLAIM_RISK",
    "PRIVACY_RISK",
    "SCALE_OR_PERFORMANCE_CLAIM_RISK",
    "STALE_AUTHORITY",
    "HEALTH_BLOCKED",
    "HEALTH_FAILED",
}
EXACT_SHA_RE = re.compile(r"[0-9a-fA-F]{40}")


class RepositorySurfaceError(ValueError):
    """Raised when a repository-surface observation or report is invalid."""


def _object(value: Any, name: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise RepositorySurfaceError(f"{name} must be an object")
    return deepcopy(dict(value))


def _strings(value: Any, name: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise RepositorySurfaceError(f"{name} must be an array")
    return sorted({str(item).strip() for item in value if str(item).strip()})


def _false_findings(prefix: str, payload: Mapping[str, Any]) -> list[str]:
    findings: list[str] = []
    for key, value in sorted(payload.items()):
        if value is False:
            findings.append(f"{prefix}_{key.upper()}")
    return findings


def audit_repository_surface(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Resolve one repository to a deterministic public-admission state."""

    item = deepcopy(dict(payload))
    repository = str(item.get("repository", "")).strip()
    if not repository or "/" not in repository:
        raise RepositorySurfaceError("repository must use owner/name form")

    public = item.get("public")
    if not isinstance(public, bool):
        raise RepositorySurfaceError("public must be boolean")

    assessment_state = str(item.get("assessment_state", "UNASSESSED")).upper()
    if assessment_state not in ASSESSMENT_STATES:
        raise RepositorySurfaceError(f"invalid assessment_state: {assessment_state}")

    lineage_state = str(item.get("lineage_state", "ACTIVE_SYSTEM")).upper()
    if lineage_state not in LINEAGE_STATES:
        raise RepositorySurfaceError(f"invalid lineage_state: {lineage_state}")

    readme = _object(item.get("readme"), "readme")
    metadata = _object(item.get("metadata"), "metadata")
    proof = _object(item.get("proof"), "proof")
    risk = _object(item.get("risk"), "risk")
    health = _object(item.get("health"), "health")

    evidence_level = str(proof.get("evidence_level", "UNASSESSED")).upper()
    if evidence_level not in EVIDENCE_LEVELS:
        raise RepositorySurfaceError(f"invalid evidence_level: {evidence_level}")

    findings: list[str] = []
    blockers: list[str] = []

    if assessment_state == "UNASSESSED":
        findings.append("SURFACE_ASSESSMENT_UNASSESSED")
    elif assessment_state == "PARTIAL":
        findings.append("SURFACE_ASSESSMENT_PARTIAL")

    if readme.get("exists") is False:
        findings.append("README_MISSING")
    readme_checks = {key: value for key, value in readme.items() if key != "exists"}
    findings.extend(_false_findings("README", readme_checks))
    findings.extend(_false_findings("METADATA", metadata))

    affiliation = _strings(risk.get("affiliation"), "risk.affiliation")
    scale = _strings(risk.get("scale_or_performance"), "risk.scale_or_performance")
    integration = _strings(
        risk.get("integration_or_deployment"), "risk.integration_or_deployment"
    )
    privacy = _strings(risk.get("privacy"), "risk.privacy")
    stale_claims = _strings(risk.get("stale_claims"), "risk.stale_claims")

    if affiliation:
        findings.append("AFFILIATION_RISK")
        blockers.extend(affiliation)
    if scale:
        findings.append("SCALE_OR_PERFORMANCE_CLAIM_RISK")
        blockers.extend(scale)
    if integration:
        findings.append("INTEGRATION_OR_DEPLOYMENT_CLAIM_RISK")
        blockers.extend(integration)
    if privacy:
        findings.append("PRIVACY_RISK")
        blockers.extend(privacy)
    if stale_claims:
        findings.append("STALE_PUBLIC_CLAIM")
        blockers.extend(stale_claims)

    company_named = bool(item.get("company_named", False))
    non_affiliation_boundary = item.get("non_affiliation_boundary")
    if company_named and non_affiliation_boundary is False:
        findings.append("COMPANY_AFFILIATION_BOUNDARY_MISSING")
    elif (
        company_named
        and non_affiliation_boundary is None
        and assessment_state != "UNASSESSED"
    ):
        findings.append("COMPANY_AFFILIATION_BOUNDARY_UNRESOLVED")

    health_state = str(health.get("health_state", "UNASSESSED")).upper()
    stale_authority = (
        bool(proof.get("newer_authority_conflicts", False)) or health_state == "STALE"
    )
    if proof.get("receipt_fresh") is False or proof.get("source_head_bound") is False:
        stale_authority = True
    if stale_authority:
        findings.append("STALE_AUTHORITY")
    if health_state in {"FAILED", "BLOCKED"}:
        findings.append(f"HEALTH_{health_state}")

    if lineage_state == "QUARANTINED" or privacy:
        admission = "QUARANTINED"
    elif not public:
        admission = "INTERNAL_ONLY"
    elif lineage_state in {"SUPERSEDED", "ARCHIVED_PROVENANCE"}:
        admission = "SUPERSEDED"
    elif stale_authority:
        admission = "STALE_AUTHORITY"
    elif findings:
        admission = "REPAIR_REQUIRED"
    elif assessment_state == "COMPLETE":
        admission = "ADMIT"
    else:
        admission = "REPAIR_REQUIRED"

    if admission == "ADMIT" and findings:
        raise RepositorySurfaceError("ADMIT cannot contain blocking findings")

    p0_markers = {
        "AFFILIATION_RISK",
        "COMPANY_AFFILIATION_BOUNDARY_MISSING",
        "INTEGRATION_OR_DEPLOYMENT_CLAIM_RISK",
        "PRIVACY_RISK",
        "SCALE_OR_PERFORMANCE_CLAIM_RISK",
        "STALE_AUTHORITY",
    }
    p1_prefixes = ("README_", "METADATA_", "STALE_PUBLIC_CLAIM", "HEALTH_")
    if (
        admission in {"QUARANTINED", "STALE_AUTHORITY"}
        or p0_markers.intersection(findings)
    ):
        repair_priority: str | None = "P0"
    elif admission == "ADMIT":
        repair_priority = None
    elif (
        any(value.startswith(p1_prefixes) for value in findings)
        or assessment_state == "PARTIAL"
    ):
        repair_priority = "P1"
    else:
        repair_priority = "P2"

    return {
        "repository": repository,
        "public": public,
        "lineage_state": lineage_state,
        "portfolio_tier": item.get("portfolio_tier"),
        "assessment_state": assessment_state,
        "company_family": item.get("company_family"),
        "company_named": company_named,
        "non_affiliation_boundary": non_affiliation_boundary,
        "evidence_level": evidence_level,
        "health_state": health_state,
        "health_assessment_id": health.get("assessment_id"),
        "readme": readme,
        "metadata": metadata,
        "risk": {
            "affiliation": affiliation,
            "scale_or_performance": scale,
            "integration_or_deployment": integration,
            "privacy": privacy,
            "stale_claims": stale_claims,
        },
        "findings": sorted(set(findings)),
        "blockers": sorted(set(blockers)),
        "admission": admission,
        "repair_priority": repair_priority,
    }


def _expand_observations(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    defaults = _object(payload.get("defaults"), "defaults")
    repositories = payload.get("public_repositories")
    if not isinstance(repositories, list) or not repositories:
        raise RepositorySurfaceError("public_repositories must be a non-empty array")
    names = [str(value).strip() for value in repositories]
    if any(not value or "/" not in value for value in names):
        raise RepositorySurfaceError("every public repository must use owner/name form")
    if len(names) != len(set(names)):
        raise RepositorySurfaceError("public_repositories contains duplicates")

    overrides = _object(payload.get("overrides"), "overrides")
    unknown_overrides = sorted(set(overrides) - set(names))
    if unknown_overrides:
        joined = ", ".join(unknown_overrides)
        raise RepositorySurfaceError(
            f"overrides reference repositories outside the census: {joined}"
        )

    expanded: list[dict[str, Any]] = []
    for repository in sorted(names):
        record = deepcopy(defaults)
        record.update(_object(overrides.get(repository), f"overrides.{repository}"))
        record["repository"] = repository
        expanded.append(record)
    return expanded


def _repair_queue(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    queue = [
        {
            "repository": item["repository"],
            "priority": item["repair_priority"],
            "admission": item["admission"],
            "findings": item["findings"],
        }
        for item in records
        if item["repair_priority"]
    ]
    priority_rank = {"P0": 0, "P1": 1, "P2": 2}
    queue.sort(key=lambda item: (priority_rank[item["priority"]], item["repository"]))
    return queue


def _surface_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    admission_counts = Counter(item["admission"] for item in records)
    assessment_counts = Counter(item["assessment_state"] for item in records)
    priority_counts = Counter(
        item["repair_priority"] for item in records if item["repair_priority"]
    )
    repair_queue = _repair_queue(records)
    company_family_by_repository = {
        record["repository"]: record["company_family"] for record in records
    }
    xai_queue = [
        item
        for item in repair_queue
        if company_family_by_repository.get(item["repository"]) == "xai"
    ]
    metadata_queue = [
        item
        for item in repair_queue
        if any(value.startswith("METADATA_") for value in item["findings"])
    ]
    return {
        "summary": {
            "admission": dict(sorted(admission_counts.items())),
            "assessment": dict(sorted(assessment_counts.items())),
            "repair_priority": dict(sorted(priority_counts.items())),
            "xai_repair_count": len(xai_queue),
            "metadata_repair_count": len(metadata_queue),
        },
        "repair_queue": repair_queue,
        "xai_truth_hardening_queue": xai_queue,
        "metadata_cleanup_queue": metadata_queue,
    }


def compile_surface_report(
    payload: Mapping[str, Any], expected_public_count: int | None = None
) -> dict[str, Any]:
    """Compile a deterministic estate-wide surface report from census observations."""

    records = [audit_repository_surface(item) for item in _expand_observations(payload)]
    if expected_public_count is not None and len(records) != expected_public_count:
        count_error = (
            f"public repository count mismatch: expected {expected_public_count}, "
            f"got {len(records)}"
        )
        raise RepositorySurfaceError(count_error)

    queues = _surface_summary(records)
    body = {
        "schema": "glaciereq.repository-surface-report.v1",
        "observed_at": payload.get("observed_at"),
        "source_query": payload.get("source_query"),
        "definition": payload.get("definition"),
        "identity_coverage": {
            "public_repository_count": len(records),
            "complete": (
                expected_public_count is None or len(records) == expected_public_count
            ),
        },
        **queues,
        "repositories": records,
    }
    body["report_id"] = sha256_json(body)
    return body


def _decision_priority_map(payload: Mapping[str, Any]) -> dict[str, str]:
    raw = payload.get("priority_escalations", [])
    if raw is None:
        return {}
    if not isinstance(raw, list):
        raise RepositorySurfaceError("priority_escalations must be an array")
    priorities: dict[str, str] = {}
    for index, value in enumerate(raw):
        item = _object(value, f"priority_escalations[{index}]")
        repository = str(item.get("repository", "")).strip()
        priority = str(item.get("priority", "")).strip().upper()
        if not repository or "/" not in repository:
            raise RepositorySurfaceError(
                f"priority_escalations[{index}].repository must use owner/name form"
            )
        if priority.startswith("P0"):
            priorities[repository] = "P0"
        elif priority in {"P1", "P2"}:
            priorities[repository] = priority
        else:
            raise RepositorySurfaceError(
                f"priority_escalations[{index}].priority must be P0/P1/P2"
            )
    return priorities


def _admit_base_blockers(record: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if record.get("public") is not True:
        blockers.append("repository_not_public")

    base_admission = str(record.get("admission", "")).upper()
    if base_admission in ADMIT_FORBIDDEN_BASE_ADMISSIONS:
        blockers.append(f"base_admission:{base_admission}")

    lineage_state = str(record.get("lineage_state", "")).upper()
    if lineage_state in ADMIT_FORBIDDEN_LINEAGE_STATES:
        blockers.append(f"lineage_state:{lineage_state}")

    findings = {str(value).upper() for value in record.get("findings", [])}
    for finding in sorted(findings.intersection(ADMIT_FORBIDDEN_FINDINGS)):
        blockers.append(f"finding:{finding}")
    return blockers


def apply_surface_decisions(
    report: Mapping[str, Any], decisions: Mapping[str, Any]
) -> dict[str, Any]:
    """Overlay later governed decisions without rewriting historical observations."""

    if decisions.get("schema") != GOVERNED_DECISION_SCHEMA:
        raise RepositorySurfaceError("unsupported governed surface decision schema")

    body = deepcopy(dict(report))
    records = body.get("repositories")
    if not isinstance(records, list) or not records:
        raise RepositorySurfaceError("surface report repositories must be a non-empty array")
    by_repository = {str(item.get("repository", "")): item for item in records}
    if len(by_repository) != len(records):
        raise RepositorySurfaceError("surface report contains duplicate repositories")

    historical_unassessed = {
        repository
        for repository, record in by_repository.items()
        if record.get("assessment_state") == "UNASSESSED"
    }

    raw_items = decisions.get("items")
    if not isinstance(raw_items, list) or not raw_items:
        raise RepositorySurfaceError("governed decision items must be a non-empty array")

    priorities = _decision_priority_map(decisions)
    seen: set[str] = set()
    for index, raw in enumerate(raw_items):
        decision_item = _object(raw, f"items[{index}]")
        repository = str(decision_item.get("repository", "")).strip()
        if repository in seen:
            raise RepositorySurfaceError(
                f"governed decisions contain duplicate repository: {repository}"
            )
        seen.add(repository)
        if repository not in by_repository:
            raise RepositorySurfaceError(
                f"governed decision references repository outside surface report: {repository}"
            )

        decision = str(decision_item.get("decision", "")).strip().upper()
        if decision not in GOVERNED_DECISION_STATES:
            raise RepositorySurfaceError(
                f"invalid governed decision for {repository}: {decision}"
            )
        next_gate = str(decision_item.get("next_gate", "")).strip()
        if not next_gate:
            raise RepositorySurfaceError(
                f"governed decision for {repository} requires next_gate"
            )
        evidence = _object(decision_item.get("evidence"), f"items[{index}].evidence")
        record = by_repository[repository]
        if decision == "ADMIT":
            source_head = str(evidence.get("source_head", "")).strip()
            if EXACT_SHA_RE.fullmatch(source_head) is None:
                raise RepositorySurfaceError(
                    f"ADMIT decision for {repository} requires exact source_head"
                )
            base_blockers = _admit_base_blockers(record)
            if base_blockers:
                joined = ", ".join(base_blockers)
                raise RepositorySurfaceError(
                    f"ADMIT decision for {repository} conflicts with base blockers: {joined}"
                )

        record["base_admission"] = record["admission"]
        record["base_assessment_state"] = record["assessment_state"]
        record["base_repair_priority"] = record["repair_priority"]
        record["governed_decision"] = decision
        record["decision_next_gate"] = next_gate
        record["decision_evidence"] = evidence
        record["decision_excellence_state"] = decision_item.get("excellence_state")

        lineage_state = str(
            decision_item.get("lineage_state", record["lineage_state"])
        ).upper()
        if lineage_state not in LINEAGE_STATES:
            raise RepositorySurfaceError(
                f"invalid governed lineage_state for {repository}: {lineage_state}"
            )
        record["lineage_state"] = lineage_state
        record["admission"] = decision
        record["assessment_state"] = (
            "PARTIAL" if decision == "REPAIR_REQUIRED" else "COMPLETE"
        )

        if decision == "QUARANTINED":
            record["repair_priority"] = "P0"
        elif decision == "REPAIR_REQUIRED":
            record["repair_priority"] = priorities.get(
                repository, record["base_repair_priority"] or "P2"
            )
        else:
            record["repair_priority"] = None

    if seen != historical_unassessed:
        missing = sorted(historical_unassessed - seen)
        unexpected = sorted(seen - historical_unassessed)
        raise RepositorySurfaceError(
            "governed decisions must exactly cover historical UNASSESSED repositories: "
            f"missing={missing}, unexpected={unexpected}"
        )

    governed_counts = Counter(
        item["governed_decision"]
        for item in records
        if item.get("governed_decision") is not None
    )
    historical_unassessed_resolved = sum(
        1
        for item in records
        if item.get("base_assessment_state") == "UNASSESSED"
        and item.get("governed_decision") is not None
    )
    unassessed_after_decisions = sum(
        1 for item in records if item["assessment_state"] == "UNASSESSED"
    )
    if unassessed_after_decisions:
        raise RepositorySurfaceError(
            "governed surface overlay left unresolved UNASSESSED repositories"
        )

    body["base_report_id"] = body.pop("report_id", None)
    body.update(_surface_summary(records))
    body["governed_overlay"] = {
        "schema": decisions.get("schema"),
        "generated_at": decisions.get("generated_at"),
        "decision_count": len(seen),
        "decision_counts": dict(sorted(governed_counts.items())),
        "historical_unassessed_resolved": historical_unassessed_resolved,
        "unassessed_remaining_after_decisions": unassessed_after_decisions,
        "historical_source": decisions.get("historical_source"),
    }
    body["report_id"] = sha256_json(body)
    return body


def compile_governed_surface_report(
    observations: Mapping[str, Any],
    decisions: Mapping[str, Any],
    expected_public_count: int | None = None,
) -> dict[str, Any]:
    """Compile historical observations plus a later governed-decision overlay."""

    historical = compile_surface_report(
        observations, expected_public_count=expected_public_count
    )
    return apply_surface_decisions(historical, decisions)
