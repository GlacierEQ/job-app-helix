"""Compile source-linked repository observations into health assessments."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from copy import deepcopy
from pathlib import Path
from typing import Any

from .repository_health import assess_repository_health, load_policy

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ADAPTER_POLICY = ROOT / "manifests" / "live_evidence_adapter_policy.json"
HEALTH_DIMENSIONS = {
    "reality",
    "build",
    "tests",
    "documentation",
    "architecture",
    "security",
    "integration",
    "recruiter_impact",
    "ai_readiness",
}
EXECUTION_STATES = {
    "SUCCESS",
    "FAILURE",
    "IN_PROGRESS",
    "AMBIGUOUS",
    "NOT_CONFIGURED",
    "NOT_RUN",
}
AUTHENTICATION_STATES = {
    "AUTHENTICATED",
    "NOT_REQUIRED_PUBLIC",
    "NOT_ASSERTED",
    "BLOCKED",
}
CONNECTOR_ERROR_STATES = {"NONE", "PARTIAL", "BLOCKED"}


class LiveEvidenceAdapterError(ValueError):
    """Raised when an observation cannot be safely compiled."""


def canonical_json(value: Any) -> str:
    """Return deterministic JSON for hashes and receipt identities."""

    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_json(value: Any) -> str:
    """Hash a JSON-compatible object using canonical serialization."""

    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def load_adapter_policy(path: Path = DEFAULT_ADAPTER_POLICY) -> dict[str, Any]:
    """Load and validate the adapter policy."""

    policy = json.loads(path.read_text(encoding="utf-8"))
    defaults = policy.get("dimension_defaults", {})
    if set(defaults) != HEALTH_DIMENSIONS:
        missing = sorted(HEALTH_DIMENSIONS - set(defaults))
        extra = sorted(set(defaults) - HEALTH_DIMENSIONS)
        raise LiveEvidenceAdapterError(
            f"adapter policy dimensions mismatch; missing={missing}, extra={extra}"
        )
    return policy


def _require_mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise LiveEvidenceAdapterError(f"{name} must be an object")
    return value


def _require_sequence(value: Any, name: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise LiveEvidenceAdapterError(f"{name} must be an array")
    return value


def _artifact_receipts(value: Any, name: str) -> list[str]:
    receipts: list[str] = []
    for index, artifact in enumerate(_require_sequence(value, name)):
        item = _require_mapping(artifact, f"{name}[{index}]")
        path = str(item.get("path", "")).strip()
        url = str(item.get("url", "")).strip()
        if not path or not url:
            raise LiveEvidenceAdapterError(f"{name}[{index}] requires path and url")
        receipts.append(url)
    return sorted(set(receipts))


def _optional_artifact_receipts(value: Any, name: str) -> list[str]:
    item = _require_mapping(value, name)
    present = item.get("present")
    if not isinstance(present, bool):
        raise LiveEvidenceAdapterError(f"{name}.present must be boolean")
    if not present:
        return []
    path = str(item.get("path", "")).strip()
    url = str(item.get("url", "")).strip()
    if not path or not url:
        raise LiveEvidenceAdapterError(f"present {name} requires path and url")
    return [url]


def _execution_item(value: Any, name: str) -> dict[str, Any]:
    item = _require_mapping(value, f"execution.{name}")
    state = str(item.get("state", "")).upper()
    if state not in EXECUTION_STATES:
        raise LiveEvidenceAdapterError(f"execution.{name}.state is invalid: {state}")
    receipts = sorted(
        {
            str(receipt).strip()
            for receipt in _require_sequence(
                item.get("receipts", []), f"execution.{name}.receipts"
            )
            if str(receipt).strip()
        }
    )
    test_count = item.get("test_count")
    if test_count is not None and (
        isinstance(test_count, bool) or not isinstance(test_count, int) or test_count < 0
    ):
        raise LiveEvidenceAdapterError(
            f"execution.{name}.test_count must be a non-negative integer or null"
        )
    notes = [
        str(note)
        for note in _require_sequence(item.get("notes", []), f"execution.{name}.notes")
    ]
    return {
        "state": state,
        "receipts": receipts,
        "test_count": test_count,
        "notes": notes,
    }


def _receipts_bound_to_head(receipts: Sequence[str], head_sha: str) -> bool:
    return bool(receipts) and all(head_sha in receipt for receipt in receipts)


def _execution_can_verify(
    item: Mapping[str, Any],
    head_sha: str,
    *,
    require_positive_test_count: bool = False,
) -> bool:
    if item["state"] != "SUCCESS":
        return False
    if not _receipts_bound_to_head(item["receipts"], head_sha):
        return False
    if require_positive_test_count and not item["test_count"]:
        return False
    return True


def _evidence(
    *,
    state: str,
    raw_score: float,
    confidence: float,
    head_sha: str,
    receipts: Sequence[str],
    findings: Sequence[str] = (),
    blockers: Sequence[str] = (),
) -> dict[str, Any]:
    return {
        "state": state,
        "raw_score": raw_score,
        "confidence": confidence,
        "verified_sha": head_sha if state in {"VERIFIED", "PARTIALLY_VERIFIED"} else None,
        "receipts": sorted(set(receipts)),
        "findings": list(findings),
        "blockers": sorted(set(blockers)),
    }


def _compile_execution_dimension(
    name: str,
    execution: Mapping[str, Any],
    head_sha: str,
    defaults: Mapping[str, Any],
    fallback_receipts: Sequence[str] = (),
) -> dict[str, Any]:
    item = _execution_item(execution.get(name), name)
    receipts = item["receipts"]
    state = item["state"]
    findings = list(item["notes"])

    if receipts and not _receipts_bound_to_head(receipts, head_sha):
        return _evidence(
            state="STALE",
            raw_score=float(defaults["raw_score"]),
            confidence=float(defaults["confidence"]),
            head_sha=head_sha,
            receipts=receipts,
            findings=[*findings, "provider receipt is not bound to the observed HEAD"],
        )

    if state == "SUCCESS":
        if not receipts:
            return _evidence(
                state="UNVERIFIED",
                raw_score=0,
                confidence=0,
                head_sha=head_sha,
                receipts=fallback_receipts,
                findings=[*findings, "success was reported without a provider receipt"],
            )
        if name == "tests" and not item["test_count"]:
            return _evidence(
                state="UNVERIFIED",
                raw_score=0,
                confidence=0,
                head_sha=head_sha,
                receipts=receipts,
                findings=[*findings, "test success lacked a positive executed-test count"],
            )
        if name == "tests":
            findings.append(f"executed test count: {item['test_count']}")
        return _evidence(
            state="VERIFIED",
            raw_score=float(defaults["raw_score"]),
            confidence=float(defaults["confidence"]),
            head_sha=head_sha,
            receipts=receipts,
            findings=findings,
        )

    if state == "FAILURE" and receipts:
        return _evidence(
            state="FAILED",
            raw_score=0,
            confidence=1,
            head_sha=head_sha,
            receipts=receipts,
            findings=findings or [f"{name} verification failed"],
        )

    if state == "IN_PROGRESS":
        findings.append(f"{name} verification is still in progress")
    elif state == "AMBIGUOUS":
        findings.append(f"{name} invocation state is ambiguous")
    elif state == "NOT_CONFIGURED":
        findings.append(f"{name} verification is not configured")
    elif state == "NOT_RUN":
        findings.append(f"{name} verification has not been run for the observed SHA")
    elif state == "FAILURE":
        findings.append(f"{name} failure was reported without a provider receipt")

    return _evidence(
        state="UNVERIFIED",
        raw_score=0,
        confidence=0,
        head_sha=head_sha,
        receipts=[*receipts, *fallback_receipts],
        findings=findings,
    )


def _connector_quality(
    connector: Mapping[str, Any],
    observation: Mapping[str, Any],
    artifact_receipts: Sequence[str],
    critical_execution: Mapping[str, dict[str, Any]],
    policy: Mapping[str, Any],
) -> float:
    points = policy["connector_quality_points"]
    receipts = [str(item) for item in connector.get("receipts", [])]
    score = 0.0
    if receipts and observation.get("repository_id") and observation.get("canonical_url"):
        score += float(points["repository_metadata_receipt"])
    head_sha = str(observation["observed_head_sha"])
    if any(head_sha in receipt or "/commit/" in receipt for receipt in receipts):
        score += float(points["head_commit_receipt"])
    if artifact_receipts and all(head_sha in receipt for receipt in artifact_receipts):
        score += float(points["sha_bound_artifact_receipts"])
    if all(item["state"] != "AMBIGUOUS" for item in critical_execution.values()):
        score += float(points["resolved_ci_invocation_state"])

    error_state = str(connector.get("error_state", "BLOCKED")).upper()
    if error_state not in CONNECTOR_ERROR_STATES:
        raise LiveEvidenceAdapterError(f"connector.error_state is invalid: {error_state}")
    if error_state == "BLOCKED":
        return 0.0
    if error_state == "PARTIAL":
        return min(score, 75.0)
    return min(score, 100.0)


def _data_quality(
    observation: Mapping[str, Any],
    category_receipts: Mapping[str, Sequence[str]],
    critical_execution: Mapping[str, dict[str, Any]],
    policy: Mapping[str, Any],
) -> float:
    points = policy["data_quality_points"]
    provenance = _require_mapping(observation["provenance"], "provenance")
    score = 0.0
    if provenance.get("source_linked") is True:
        score += float(points["source_linked"])
    if provenance.get("head_sha_bound") is True:
        score += float(points["head_sha_bound"])

    required = policy["required_artifact_categories"]
    present = sum(1 for name in required if category_receipts.get(name))
    score += float(points["required_artifact_categories_observed"]) * present / len(required)

    resolved = sum(
        1 for item in critical_execution.values() if item["state"] != "AMBIGUOUS"
    )
    score += float(points["critical_execution_states_resolved"]) * resolved / len(
        critical_execution
    )
    return round(min(score, 100.0), 2)


def compile_repository_observation(
    observation: Mapping[str, Any],
    *,
    adapter_policy: Mapping[str, Any] | None = None,
    health_policy: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Compile one source-linked observation into a deterministic health assessment."""

    payload = deepcopy(dict(observation))
    if payload.get("schema") != "glaciereq.repository-observation.v1":
        raise LiveEvidenceAdapterError("unsupported repository observation schema")

    repository = str(payload.get("repository", "")).strip()
    if repository.count("/") != 1 or any(not part for part in repository.split("/")):
        raise LiveEvidenceAdapterError("repository must use owner/name form")
    canonical_url = str(payload.get("canonical_url", "")).rstrip("/")
    expected_url = f"https://github.com/{repository}"
    if canonical_url != expected_url:
        raise LiveEvidenceAdapterError(
            f"canonical_url must equal {expected_url}, got {canonical_url}"
        )

    head_sha = str(payload.get("observed_head_sha", "")).lower()
    if len(head_sha) < 40 or any(
        character not in "0123456789abcdef" for character in head_sha
    ):
        raise LiveEvidenceAdapterError("observed_head_sha must be a lowercase Git SHA")

    provenance = _require_mapping(payload.get("provenance"), "provenance")
    if provenance.get("original_bytes_copied") is not False:
        raise LiveEvidenceAdapterError("copied repository bytes are forbidden")
    if provenance.get("source_linked") is not True:
        raise LiveEvidenceAdapterError("source-linked provenance is required")
    if provenance.get("head_sha_bound") is not True:
        raise LiveEvidenceAdapterError("head-SHA-bound provenance is required")

    active_policy = deepcopy(dict(adapter_policy or load_adapter_policy()))
    defaults = active_policy["dimension_defaults"]
    artifacts = _require_mapping(payload.get("artifacts"), "artifacts")
    connector = _require_mapping(payload.get("connector"), "connector")
    execution = _require_mapping(payload.get("execution"), "execution")

    authentication_state = str(
        connector.get("authentication_state", "NOT_ASSERTED")
    ).upper()
    if authentication_state not in AUTHENTICATION_STATES:
        raise LiveEvidenceAdapterError(
            f"connector.authentication_state is invalid: {authentication_state}"
        )

    readme = _optional_artifact_receipts(artifacts.get("readme"), "artifacts.readme")
    package_manifest = _optional_artifact_receipts(
        artifacts.get("package_manifest"), "artifacts.package_manifest"
    )
    license_receipts = _optional_artifact_receipts(
        artifacts.get("license", {"present": False, "path": None, "url": None}),
        "artifacts.license",
    )
    security_policy_receipts = _optional_artifact_receipts(
        artifacts.get(
            "security_policy", {"present": False, "path": None, "url": None}
        ),
        "artifacts.security_policy",
    )
    category_receipts = {
        "readme": readme,
        "package_manifest": package_manifest,
        "workflows": _artifact_receipts(
            artifacts.get("workflows"), "artifacts.workflows"
        ),
        "source_files": _artifact_receipts(
            artifacts.get("source_files"), "artifacts.source_files"
        ),
        "test_files": _artifact_receipts(
            artifacts.get("test_files"), "artifacts.test_files"
        ),
        "architecture_files": _artifact_receipts(
            artifacts.get("architecture_files"), "artifacts.architecture_files"
        ),
        "integration_files": _artifact_receipts(
            artifacts.get("integration_files"), "artifacts.integration_files"
        ),
        "ai_files": _artifact_receipts(
            artifacts.get("ai_files"), "artifacts.ai_files"
        ),
        "recruiter_files": _artifact_receipts(
            artifacts.get("recruiter_files"), "artifacts.recruiter_files"
        ),
    }
    artifact_receipts = sorted(
        {
            receipt
            for receipts in category_receipts.values()
            for receipt in receipts
        }
        | set(license_receipts)
        | set(security_policy_receipts)
    )
    unbound = [receipt for receipt in artifact_receipts if head_sha not in receipt]
    if unbound:
        raise LiveEvidenceAdapterError(
            f"artifact receipts must be bound to observed HEAD: {', '.join(unbound)}"
        )

    critical_execution = {
        name: _execution_item(execution.get(name), name)
        for name in active_policy["critical_execution_fields"]
    }

    dimensions: dict[str, Any] = {}
    source_receipts = [*package_manifest, *category_receipts["source_files"]]
    if package_manifest and category_receipts["source_files"]:
        reality_verified = _execution_can_verify(
            critical_execution["build"], head_sha
        ) and _execution_can_verify(
            critical_execution["tests"],
            head_sha,
            require_positive_test_count=True,
        )
        dimensions["reality"] = _evidence(
            state="VERIFIED" if reality_verified else "PARTIALLY_VERIFIED",
            raw_score=float(defaults["reality"]["raw_score"]),
            confidence=float(defaults["reality"]["confidence"]),
            head_sha=head_sha,
            receipts=source_receipts,
            findings=[
                "substantive source and a package manifest were observed",
                *([] if reality_verified else ["runtime behavior remains separately gated"]),
            ],
        )
    else:
        dimensions["reality"] = _evidence(
            state="UNVERIFIED",
            raw_score=0,
            confidence=0,
            head_sha=head_sha,
            receipts=source_receipts,
            findings=["source code or package manifest evidence is missing"],
        )

    dimensions["build"] = _compile_execution_dimension(
        "build",
        execution,
        head_sha,
        defaults["build"],
        category_receipts["workflows"],
    )
    dimensions["tests"] = _compile_execution_dimension(
        "tests",
        execution,
        head_sha,
        defaults["tests"],
        [*category_receipts["workflows"], *category_receipts["test_files"]],
    )

    documentation_execution = _compile_execution_dimension(
        "documentation",
        execution,
        head_sha,
        defaults["documentation"],
        [*readme, *category_receipts["recruiter_files"]],
    )
    if documentation_execution["state"] == "UNVERIFIED" and readme:
        dimensions["documentation"] = _evidence(
            state="PARTIALLY_VERIFIED",
            raw_score=float(defaults["documentation"]["raw_score"]),
            confidence=float(defaults["documentation"]["confidence"]),
            head_sha=head_sha,
            receipts=[*readme, *category_receipts["recruiter_files"]],
            findings=[
                "current README and recruiter-facing documentation were observed",
                "the repository documentation verifier was not proven for the observed SHA",
            ],
        )
    else:
        dimensions["documentation"] = documentation_execution

    if category_receipts["architecture_files"]:
        dimensions["architecture"] = _evidence(
            state="PARTIALLY_VERIFIED",
            raw_score=float(defaults["architecture"]["raw_score"]),
            confidence=float(defaults["architecture"]["confidence"]),
            head_sha=head_sha,
            receipts=category_receipts["architecture_files"],
            findings=[
                "architecture artifacts were observed; implementation alignment is unexecuted"
            ],
        )
    else:
        dimensions["architecture"] = _evidence(
            state="UNVERIFIED",
            raw_score=0,
            confidence=0,
            head_sha=head_sha,
            receipts=[],
            findings=["no architecture artifact was observed"],
        )

    dimensions["security"] = _compile_execution_dimension(
        "security",
        execution,
        head_sha,
        defaults["security"],
        security_policy_receipts,
    )

    for dimension, category, finding in (
        (
            "integration",
            "integration_files",
            "integration surfaces were observed but not executed",
        ),
        (
            "recruiter_impact",
            "recruiter_files",
            "recruiter-facing surfaces were observed but impact is not a runtime claim",
        ),
        (
            "ai_readiness",
            "ai_files",
            "machine-readable AI surfaces were observed but not executed",
        ),
    ):
        receipts = category_receipts[category]
        if receipts:
            dimensions[dimension] = _evidence(
                state="PARTIALLY_VERIFIED",
                raw_score=float(defaults[dimension]["raw_score"]),
                confidence=float(defaults[dimension]["confidence"]),
                head_sha=head_sha,
                receipts=receipts,
                findings=[finding],
            )
        else:
            dimensions[dimension] = _evidence(
                state="UNVERIFIED",
                raw_score=0,
                confidence=0,
                head_sha=head_sha,
                receipts=[],
                findings=[f"no {dimension.replace('_', ' ')} artifact was observed"],
            )

    connector_quality = _connector_quality(
        connector,
        payload,
        artifact_receipts,
        critical_execution,
        active_policy,
    )
    data_quality = _data_quality(
        payload,
        category_receipts,
        critical_execution,
        active_policy,
    )
    health_input = {
        "repository": repository,
        "observed_head_sha": head_sha,
        "observed_at": payload.get("observed_at"),
        "dimensions": dimensions,
        "quality_context": {
            "connector_quality_score": connector_quality,
            "data_quality_score": data_quality,
        },
        "blockers": sorted(
            {str(item) for item in payload.get("blockers", []) if str(item)}
        ),
    }
    active_health_policy = deepcopy(dict(health_policy or load_policy()))
    assessment = assess_repository_health(health_input, active_health_policy)
    observation_id = sha256_json(payload)
    return {
        "schema": "glaciereq.live-evidence-adapter-result.v1",
        "observation_id": observation_id,
        "repository": repository,
        "observed_head_sha": head_sha,
        "adapter_policy_version": active_policy["version"],
        "health_policy_version": active_health_policy["version"],
        "health_input": health_input,
        "assessment": assessment,
        "integrity": {
            "observation_sha256": observation_id,
            "adapter_policy_sha256": sha256_json(active_policy),
            "health_policy_sha256": sha256_json(active_health_policy),
        },
    }
