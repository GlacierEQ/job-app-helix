"""Fail-closed repository-surface admission for public portfolio compilation."""

from __future__ import annotations

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
    findings.extend(_false_findings("README", {k: v for k, v in readme.items() if k != "exists"}))
    findings.extend(_false_findings("METADATA", metadata))

    affiliation = _strings(risk.get("affiliation"), "risk.affiliation")
    scale = _strings(risk.get("scale_or_performance"), "risk.scale_or_performance")
    integration = _strings(risk.get("integration_or_deployment"), "risk.integration_or_deployment")
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
    elif company_named and non_affiliation_boundary is None and assessment_state != "UNASSESSED":
        findings.append("COMPANY_AFFILIATION_BOUNDARY_UNRESOLVED")

    health_state = str(health.get("health_state", "UNASSESSED")).upper()
    stale_authority = bool(proof.get("newer_authority_conflicts", False)) or health_state == "STALE"
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
    if admission in {"QUARANTINED", "STALE_AUTHORITY"} or p0_markers.intersection(findings):
        repair_priority: str | None = "P0"
    elif admission == "ADMIT":
        repair_priority = None
    elif any(value.startswith(p1_prefixes) for value in findings) or assessment_state == "PARTIAL":
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
        raise RepositorySurfaceError(
            "overrides reference repositories outside the census: " + ", ".join(unknown_overrides)
        )

    expanded: list[dict[str, Any]] = []
    for repository in sorted(names):
        record = deepcopy(defaults)
        record.update(_object(overrides.get(repository), f"overrides.{repository}"))
        record["repository"] = repository
        expanded.append(record)
    return expanded


def compile_surface_report(
    payload: Mapping[str, Any], expected_public_count: int | None = None
) -> dict[str, Any]:
    """Compile a deterministic estate-wide surface report from census observations."""

    records = [audit_repository_surface(item) for item in _expand_observations(payload)]
    if expected_public_count is not None and len(records) != expected_public_count:
        raise RepositorySurfaceError(
            f"public repository count mismatch: expected {expected_public_count}, got {len(records)}"
        )

    admission_counts = Counter(item["admission"] for item in records)
    assessment_counts = Counter(item["assessment_state"] for item in records)
    priority_counts = Counter(item["repair_priority"] for item in records if item["repair_priority"])

    repair_queue = [
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
    repair_queue.sort(key=lambda item: (priority_rank[item["priority"]], item["repository"]))

    xai_queue = [
        item for item in repair_queue if next(
            record["company_family"] == "xai"
            for record in records
            if record["repository"] == item["repository"]
        )
    ]
    metadata_queue = [
        item for item in repair_queue if any(value.startswith("METADATA_") for value in item["findings"])
    ]

    body = {
        "schema": "glaciereq.repository-surface-report.v1",
        "observed_at": payload.get("observed_at"),
        "source_query": payload.get("source_query"),
        "definition": payload.get("definition"),
        "identity_coverage": {
            "public_repository_count": len(records),
            "complete": expected_public_count is None or len(records) == expected_public_count,
        },
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
        "repositories": records,
    }
    body["report_id"] = sha256_json(body)
    return body
