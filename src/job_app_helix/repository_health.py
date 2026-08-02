"""Evidence-weighted, SHA-bound repository health assessment."""

from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_POLICY = ROOT / "manifests" / "repository_health_policy.json"
SHA_PATTERN = re.compile(r"^[0-9a-f]{40,64}$")
KNOWN_STATES = {
    "VERIFIED",
    "PARTIALLY_VERIFIED",
    "STALE",
    "UNVERIFIED",
    "BLOCKED",
    "FAILED",
}


class RepositoryHealthError(ValueError):
    """Raised when a repository-health input or policy is invalid."""


def canonical_json(value: Any) -> str:
    """Return deterministic JSON suitable for hashing and receipts."""

    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_json(value: Any) -> str:
    """Hash a JSON-compatible value using canonical serialization."""

    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def load_policy(path: Path = DEFAULT_POLICY) -> dict[str, Any]:
    """Load and validate the repository-health scoring policy."""

    policy = json.loads(path.read_text(encoding="utf-8"))
    dimensions = policy.get("dimensions", {})
    if not dimensions:
        raise RepositoryHealthError("policy must define at least one dimension")
    total_weight = sum(item.get("weight", 0) for item in dimensions.values())
    if total_weight != 100:
        raise RepositoryHealthError(f"dimension weights must total 100, got {total_weight}")
    caps = policy.get("evidence_state_caps", {})
    if set(caps) != KNOWN_STATES:
        raise RepositoryHealthError("policy evidence-state caps must match known states")
    for state, cap in caps.items():
        if not 0 <= cap <= 1:
            raise RepositoryHealthError(f"invalid evidence cap for {state}: {cap}")
    return policy


def _number(value: Any, name: str, minimum: float, maximum: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RepositoryHealthError(f"{name} must be numeric")
    result = float(value)
    if not minimum <= result <= maximum:
        raise RepositoryHealthError(f"{name} must be between {minimum} and {maximum}")
    return result


def _quality_score(value: Any, name: str) -> float | None:
    if value is None:
        return None
    return _number(value, name, 0, 100)


def _normalize_evidence(
    name: str,
    evidence: Mapping[str, Any] | None,
    observed_head_sha: str,
    cap: Mapping[str, float],
) -> tuple[dict[str, Any], list[str], list[str]]:
    item = deepcopy(dict(evidence or {}))
    requested_state = str(item.get("state", "UNVERIFIED")).upper()
    if requested_state not in KNOWN_STATES:
        raise RepositoryHealthError(f"{name}.state is invalid: {requested_state}")

    raw_score = _number(item.get("raw_score", 0), f"{name}.raw_score", 0, 100)
    confidence = _number(item.get("confidence", 0), f"{name}.confidence", 0, 1)
    receipts = sorted({str(value) for value in item.get("receipts", []) if str(value)})
    blockers = sorted({str(value) for value in item.get("blockers", []) if str(value)})
    findings = [str(value) for value in item.get("findings", [])]
    verified_sha = item.get("verified_sha")
    if verified_sha is not None:
        verified_sha = str(verified_sha).lower()
        if not SHA_PATTERN.fullmatch(verified_sha):
            raise RepositoryHealthError(f"{name}.verified_sha is not a valid Git SHA")

    normalized_state = requested_state
    normalization_reasons: list[str] = []
    if requested_state == "VERIFIED":
        if not receipts:
            normalized_state = "UNVERIFIED"
            normalization_reasons.append("verified state lacked a receipt")
        elif verified_sha != observed_head_sha:
            normalized_state = "STALE"
            normalization_reasons.append("verified SHA does not match observed HEAD")
    elif requested_state == "PARTIALLY_VERIFIED":
        if not receipts:
            normalized_state = "UNVERIFIED"
            normalization_reasons.append("partial verification lacked a receipt")
        elif verified_sha is not None and verified_sha != observed_head_sha:
            normalized_state = "STALE"
            normalization_reasons.append("partial verification targets an older SHA")
    elif requested_state == "STALE" and verified_sha == observed_head_sha:
        normalization_reasons.append("stale state was preserved explicitly")

    if normalized_state in {"UNVERIFIED", "BLOCKED", "FAILED"}:
        effective_raw_score = 0.0
    else:
        effective_raw_score = raw_score

    effective_fraction = (
        effective_raw_score / 100 * float(cap[normalized_state]) * confidence
    )
    normalized = {
        "state": normalized_state,
        "requested_state": requested_state,
        "raw_score": raw_score,
        "confidence": confidence,
        "verified_sha": verified_sha,
        "receipts": receipts,
        "findings": findings,
        "blockers": blockers,
        "normalization_reasons": normalization_reasons,
        "effective_fraction": effective_fraction,
    }
    next_actions: list[str] = []
    if normalized_state == "UNVERIFIED":
        next_actions.append(f"collect executable or reviewable evidence for {name}")
    elif normalized_state == "STALE":
        next_actions.append(f"reverify {name} against {observed_head_sha}")
    elif normalized_state == "BLOCKED":
        next_actions.append(f"resolve the documented blocker for {name}")
    elif normalized_state == "FAILED":
        next_actions.append(f"repair the failed {name} verification")
    return normalized, blockers, next_actions


def assess_repository_health(
    payload: Mapping[str, Any],
    policy: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Compute a deterministic, fail-closed repository-health assessment."""

    active_policy = deepcopy(dict(policy or load_policy()))
    repository = str(payload.get("repository", "")).strip()
    if not repository or "/" not in repository:
        raise RepositoryHealthError("repository must use owner/name form")
    observed_head_sha = str(payload.get("observed_head_sha", "")).lower()
    if not SHA_PATTERN.fullmatch(observed_head_sha):
        raise RepositoryHealthError("observed_head_sha is not a valid Git SHA")

    dimensions = active_policy["dimensions"]
    caps = active_policy["evidence_state_caps"]
    supplied_dimensions = payload.get("dimensions", {})
    if not isinstance(supplied_dimensions, Mapping):
        raise RepositoryHealthError("dimensions must be an object")
    unknown = sorted(set(supplied_dimensions) - set(dimensions))
    if unknown:
        raise RepositoryHealthError(f"unknown health dimensions: {', '.join(unknown)}")

    dimension_results: dict[str, Any] = {}
    blockers = sorted({str(value) for value in payload.get("blockers", []) if str(value)})
    next_actions: list[str] = []
    weighted_score = 0.0
    covered_weight = 0.0
    confidence_weight = 0.0
    critical_not_verified: list[str] = []

    for name, definition in dimensions.items():
        normalized, item_blockers, item_actions = _normalize_evidence(
            name,
            supplied_dimensions.get(name),
            observed_head_sha,
            caps,
        )
        weight = float(definition["weight"])
        points = weight * normalized["effective_fraction"]
        normalized["weight"] = weight
        normalized["points"] = points
        normalized["critical"] = bool(definition.get("critical", False))
        dimension_results[name] = normalized
        weighted_score += points
        confidence_weight += weight * normalized["confidence"]
        if normalized["receipts"]:
            covered_weight += weight
        blockers.extend(item_blockers)
        next_actions.extend(item_actions)
        if normalized["critical"] and normalized["state"] != "VERIFIED":
            critical_not_verified.append(name)

    precision = int(active_policy.get("score_precision", 2))
    health_score = round(weighted_score, precision)
    evidence_coverage = round(covered_weight, precision)
    confidence_score = round(confidence_weight, precision)
    quality = payload.get("quality_context", {})
    if not isinstance(quality, Mapping):
        raise RepositoryHealthError("quality_context must be an object")
    connector_quality = _quality_score(
        quality.get("connector_quality_score"), "connector_quality_score"
    )
    data_quality = _quality_score(quality.get("data_quality_score"), "data_quality_score")

    promotion = active_policy["promotion"]
    elite_failures: list[str] = []
    if health_score < promotion["elite_verified_min_score"]:
        elite_failures.append("health score below elite threshold")
    if evidence_coverage < promotion["elite_verified_min_evidence_coverage"]:
        elite_failures.append("evidence coverage below elite threshold")
    if data_quality is None or data_quality < promotion["elite_verified_min_data_quality"]:
        elite_failures.append("data quality is missing or below elite threshold")
    if connector_quality is None or connector_quality < promotion[
        "elite_verified_min_connector_quality"
    ]:
        elite_failures.append("connector quality is missing or below elite threshold")
    if promotion["elite_requires_all_critical_verified"] and critical_not_verified:
        elite_failures.append("critical dimensions are not currently verified")
    blockers = sorted(set(blockers))
    if promotion["elite_forbids_blockers"] and blockers:
        elite_failures.append("unresolved blockers remain")

    states = {item["state"] for item in dimension_results.values()}
    if "FAILED" in states:
        health_state = "FAILED"
    elif "BLOCKED" in states:
        health_state = "BLOCKED"
    elif "STALE" in states:
        health_state = "STALE"
    elif health_score == 0:
        health_state = "UNVERIFIED"
    elif not elite_failures:
        health_state = "ELITE_VERIFIED"
    elif health_score >= promotion["recruiter_ready_min_score"]:
        health_state = "RECRUITER_READY"
    else:
        health_state = "PARTIALLY_VERIFIED"

    normalized_input = {
        "repository": repository,
        "observed_head_sha": observed_head_sha,
        "observed_at": payload.get("observed_at"),
        "dimensions": dimension_results,
        "quality_context": {
            "connector_quality_score": connector_quality,
            "data_quality_score": data_quality,
        },
        "blockers": blockers,
    }
    assessment_id = sha256_json(
        {
            "policy_version": active_policy["version"],
            "repository": repository,
            "observed_head_sha": observed_head_sha,
            "dimensions": dimension_results,
            "quality_context": normalized_input["quality_context"],
        }
    )
    return {
        "schema": "glaciereq.repository-health-assessment.v1",
        "assessment_id": assessment_id,
        "repository": repository,
        "observed_head_sha": observed_head_sha,
        "observed_at": payload.get("observed_at"),
        "policy_version": active_policy["version"],
        "health_state": health_state,
        "health_score": health_score,
        "evidence_coverage": evidence_coverage,
        "confidence_score": confidence_score,
        "quality_context": normalized_input["quality_context"],
        "dimensions": dimension_results,
        "critical_not_verified": sorted(critical_not_verified),
        "blockers": blockers,
        "elite_eligible": not elite_failures,
        "elite_gate_failures": elite_failures,
        "next_actions": sorted(set(next_actions)),
        "integrity": {
            "input_sha256": sha256_json(dict(payload)),
            "policy_sha256": sha256_json(active_policy),
        },
    }
