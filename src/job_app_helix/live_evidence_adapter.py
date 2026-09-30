"""Compile source-linked repository observations into health assessments."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from copy import deepcopy
from importlib.resources import files
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError

from .repository_health import assess_repository_health, load_policy

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
ARTIFACT_CATEGORIES = {
    "readme",
    "package_manifest",
    "workflows",
    "source_files",
    "test_files",
    "architecture_files",
    "integration_files",
    "ai_files",
    "recruiter_files",
}
EXECUTION_STATES = {
    "SUCCESS",
    "FAILURE",
    "IN_PROGRESS",
    "AMBIGUOUS",
    "NOT_CONFIGURED",
    "NOT_RUN",
}
CRITICAL_EXECUTION_FIELDS = {"build", "tests", "documentation", "security"}
FINAL_EXECUTION_STATES = {"SUCCESS", "FAILURE"}
AUTHENTICATION_STATES = {
    "AUTHENTICATED",
    "NOT_REQUIRED_PUBLIC",
    "NOT_ASSERTED",
    "BLOCKED",
}
CONNECTOR_ERROR_STATES = {"NONE", "PARTIAL", "BLOCKED"}
RESOURCE_PACKAGE = "job_app_helix.resources"


class LiveEvidenceAdapterError(ValueError):
    """Raised when an observation cannot be safely compiled."""


def reference_json(value: Any) -> str:
    """Return deterministic JSON for hashes and receipt identities."""

    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_json(value: Any) -> str:
    """Hash a JSON-compatible object using reference serialization."""

    return hashlib.sha256(reference_json(value).encode("utf-8")).hexdigest()


def _load_json_resource(name: str) -> dict[str, Any]:
    text = files(RESOURCE_PACKAGE).joinpath(name).read_text(encoding="utf-8")
    value = json.loads(text)
    if not isinstance(value, dict):
        raise LiveEvidenceAdapterError(f"installed resource {name} must be an object")
    return value


def _validate_adapter_policy(policy: Mapping[str, Any]) -> dict[str, Any]:
    normalized = deepcopy(dict(policy))
    defaults = normalized.get("dimension_defaults", {})
    if set(defaults) != HEALTH_DIMENSIONS:
        missing = sorted(HEALTH_DIMENSIONS - set(defaults))
        extra = sorted(set(defaults) - HEALTH_DIMENSIONS)
        raise LiveEvidenceAdapterError(
            f"adapter policy dimensions mismatch; missing={missing}, extra={extra}"
        )

    execution_states = normalized.get("execution_states")
    if not isinstance(execution_states, list) or set(execution_states) != EXECUTION_STATES:
        raise LiveEvidenceAdapterError(
            "adapter policy execution_states must match implemented execution states"
        )

    required_categories = normalized.get("required_artifact_categories")
    if not isinstance(required_categories, list) or not required_categories:
        raise LiveEvidenceAdapterError(
            "adapter policy required_artifact_categories must be a non-empty array"
        )
    if set(required_categories) != ARTIFACT_CATEGORIES:
        raise LiveEvidenceAdapterError(
            "adapter policy required_artifact_categories must match known categories"
        )

    critical_fields = normalized.get("critical_execution_fields")
    if not isinstance(critical_fields, list) or not critical_fields:
        raise LiveEvidenceAdapterError(
            "adapter policy critical_execution_fields must be a non-empty array"
        )
    if set(critical_fields) != CRITICAL_EXECUTION_FIELDS:
        raise LiveEvidenceAdapterError(
            "adapter policy critical_execution_fields must match known fields"
        )
    return normalized


def load_adapter_policy(path: Path | None = None) -> dict[str, Any]:
    """Load and validate the adapter policy from a file or installed resource."""

    if path is None:
        policy = _load_json_resource("live_evidence_adapter_policy.json")
    else:
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise LiveEvidenceAdapterError("adapter policy must be an object")
        policy = value
    return _validate_adapter_policy(policy)


def load_observation_schema(path: Path | None = None) -> dict[str, Any]:
    """Load and validate the repository observation JSON Schema."""

    if path is None:
        schema = _load_json_resource("repository_observation.schema.json")
    else:
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise LiveEvidenceAdapterError("repository observation schema must be an object")
        schema = value
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as exc:
        raise LiveEvidenceAdapterError(
            f"invalid repository observation schema: {exc.message}"
        ) from exc
    return schema


def _validate_observation_contract(observation: Mapping[str, Any]) -> dict[str, Any]:
    payload = deepcopy(dict(observation))
    validator = Draft202012Validator(
        load_observation_schema(),
        format_checker=FormatChecker(),
    )
    errors = sorted(validator.iter_errors(payload), key=lambda item: list(item.absolute_path))
    if errors:
        error = errors[0]
        location = ".".join(str(part) for part in error.absolute_path) or "$"
        raise LiveEvidenceAdapterError(
            f"repository observation violates schema at {location}: {error.message}"
        ) from error
    return payload


def _require_mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise LiveEvidenceAdapterError(f"{name} must be an object")
    return value


def _require_sequence(value: Any, name: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise LiveEvidenceAdapterError(f"{name} must be an array")
    return value


def _source_path(source_url: str) -> str:
    parsed = urlparse(source_url)
    if parsed.scheme != "https" or parsed.netloc != "github.com":
        raise LiveEvidenceAdapterError("reference repository URL must use github.com HTTPS")
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) != 2:
        raise LiveEvidenceAdapterError("reference repository URL must use owner/name form")
    return f"/{parts[0]}/{parts[1]}"


def _normalize_artifact_path(path: str, name: str) -> str:
    if not path or "\\" in path:
        raise LiveEvidenceAdapterError(f"{name}.path must be a non-empty POSIX path")
    candidate = PurePosixPath(path)
    if candidate.is_absolute() or any(part in {"", ".", ".."} for part in candidate.parts):
        raise LiveEvidenceAdapterError(f"{name}.path must be a safe repository-relative path")
    normalized = candidate.as_posix()
    if normalized != path:
        raise LiveEvidenceAdapterError(f"{name}.path must be normalized: {normalized}")
    return normalized


def _trusted_artifact_url(
    receipt: str,
    declared_path: str,
    head_sha: str,
    source_url: str,
) -> bool:
    parsed = urlparse(receipt)
    if parsed.scheme != "https" or parsed.netloc != "github.com":
        return False
    if parsed.query or parsed.fragment:
        return False
    expected = f"{_source_path(source_url)}/blob/{head_sha}/{declared_path}"
    return unquote(parsed.path) == expected


def _artifact_receipts(
    value: Any,
    name: str,
    head_sha: str,
    source_url: str,
) -> list[str]:
    receipts: list[str] = []
    for index, artifact in enumerate(_require_sequence(value, name)):
        item_name = f"{name}[{index}]"
        item = _require_mapping(artifact, item_name)
        path = _normalize_artifact_path(str(item.get("path", "")).strip(), item_name)
        url = str(item.get("url", "")).strip()
        if not url or not _trusted_artifact_url(url, path, head_sha, source_url):
            raise LiveEvidenceAdapterError(
                f"{item_name}.url must resolve to its declared path at the observed HEAD"
            )
        receipts.append(url)
    return sorted(set(receipts))


def _optional_artifact_receipts(
    value: Any,
    name: str,
    head_sha: str,
    source_url: str,
) -> list[str]:
    item = _require_mapping(value, name)
    present = item.get("present")
    if not isinstance(present, bool):
        raise LiveEvidenceAdapterError(f"{name}.present must be boolean")
    if not present:
        return []
    path = _normalize_artifact_path(str(item.get("path", "")).strip(), name)
    url = str(item.get("url", "")).strip()
    if not url or not _trusted_artifact_url(url, path, head_sha, source_url):
        raise LiveEvidenceAdapterError(
            f"{name}.url must resolve to its declared path at the observed HEAD"
        )
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


def _trusted_metadata_receipt(receipt: str, source_url: str) -> bool:
    source_path = _source_path(source_url)
    parsed = urlparse(receipt)
    if parsed.scheme != "https" or parsed.query or parsed.fragment:
        return False
    return (
        parsed.netloc == "github.com" and parsed.path.rstrip("/") == source_path
    ) or (
        parsed.netloc == "api.github.com"
        and parsed.path.rstrip("/") == f"/repos{source_path}"
    )


def _trusted_receipt_bound_to_head(
    receipt: str,
    head_sha: str,
    source_url: str,
) -> bool:
    source_path = _source_path(source_url)
    parsed = urlparse(receipt)
    if parsed.scheme != "https" or parsed.fragment:
        return False

    if parsed.netloc == "github.com":
        prefix = f"{source_path}/"
        if not parsed.path.startswith(prefix):
            return False
        relative_path = parsed.path[len(prefix) :]
        if relative_path.startswith(f"blob/{head_sha}/"):
            return not parsed.query
        if relative_path in {f"commit/{head_sha}", f"commit/{head_sha}/"}:
            return not parsed.query
        path_parts = relative_path.split("/")
        if (
            len(path_parts) >= 3
            and path_parts[:2] == ["actions", "runs"]
            and path_parts[2].isdigit()
        ):
            return parse_qs(parsed.query).get("sha") == [head_sha]
        return False

    if parsed.netloc == "api.github.com":
        prefix = f"/repos{source_path}/"
        if not parsed.path.startswith(prefix):
            return False
        return parse_qs(parsed.query).get("sha") == [head_sha]
    return False


def _execution_can_verify(
    item: Mapping[str, Any],
    head_sha: str,
    source_url: str,
    *,
    require_positive_test_count: bool = False,
) -> bool:
    if item["state"] != "SUCCESS":
        return False
    if not item["receipts"] or not all(
        _trusted_receipt_bound_to_head(receipt, head_sha, source_url)
        for receipt in item["receipts"]
    ):
        return False
    return not require_positive_test_count or bool(item["test_count"])


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
    source_url: str,
    defaults: Mapping[str, Any],
) -> dict[str, Any]:
    item = _execution_item(execution.get(name), name)
    receipts = item["receipts"]
    state = item["state"]
    findings = list(item["notes"])
    current_receipts = [
        receipt
        for receipt in receipts
        if _trusted_receipt_bound_to_head(receipt, head_sha, source_url)
    ]
    rejected_receipts = sorted(set(receipts) - set(current_receipts))

    if state == "FAILURE":
        if current_receipts:
            if rejected_receipts:
                findings.append(
                    f"ignored {len(rejected_receipts)} non-current or untrusted receipt(s)"
                )
            return _evidence(
                state="FAILED",
                raw_score=0,
                confidence=1,
                head_sha=head_sha,
                receipts=current_receipts,
                findings=findings or [f"{name} verification failed"],
            )
        if receipts:
            findings.append(
                f"{name} failure lacked a trusted receipt for the observed HEAD"
            )
        else:
            findings.append(f"{name} failure was reported without a provider receipt")
        return _evidence(
            state="UNVERIFIED",
            raw_score=0,
            confidence=0,
            head_sha=head_sha,
            receipts=[],
            findings=findings,
        )

    if state == "SUCCESS":
        if not receipts:
            return _evidence(
                state="UNVERIFIED",
                raw_score=0,
                confidence=0,
                head_sha=head_sha,
                receipts=[],
                findings=[*findings, "success was reported without a provider receipt"],
            )
        if rejected_receipts:
            return _evidence(
                state="UNVERIFIED",
                raw_score=0,
                confidence=0,
                head_sha=head_sha,
                receipts=[],
                findings=[
                    *findings,
                    "success included a non-current or untrusted provider receipt",
                ],
            )
        if name == "tests" and not item["test_count"]:
            return _evidence(
                state="UNVERIFIED",
                raw_score=0,
                confidence=0,
                head_sha=head_sha,
                receipts=current_receipts,
                findings=[*findings, "test success lacked a positive executed-test count"],
            )
        if name == "tests":
            findings.append(f"executed test count: {item['test_count']}")
        return _evidence(
            state="VERIFIED",
            raw_score=float(defaults["raw_score"]),
            confidence=float(defaults["confidence"]),
            head_sha=head_sha,
            receipts=current_receipts,
            findings=findings,
        )

    if state == "IN_PROGRESS":
        findings.append(f"{name} verification is still in progress")
    elif state == "AMBIGUOUS":
        findings.append(f"{name} invocation state is ambiguous")
    elif state == "NOT_CONFIGURED":
        findings.append(f"{name} verification is not configured")
    elif state == "NOT_RUN":
        findings.append(f"{name} verification has not been run for the observed SHA")

    if rejected_receipts:
        findings.append(
            f"ignored {len(rejected_receipts)} non-current or untrusted receipt(s)"
        )
    return _evidence(
        state="UNVERIFIED",
        raw_score=0,
        confidence=0,
        head_sha=head_sha,
        receipts=current_receipts,
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
    source_url = str(observation["source_url"])
    head_sha = str(observation["observed_head_sha"])
    score = 0.0

    if (
        observation.get("repository_id")
        and any(_trusted_metadata_receipt(receipt, source_url) for receipt in receipts)
    ):
        score += float(points["repository_metadata_receipt"])
    if any(
        _trusted_receipt_bound_to_head(receipt, head_sha, source_url)
        and "/commit/" in urlparse(receipt).path
        for receipt in receipts
    ):
        score += float(points["head_commit_receipt"])
    if artifact_receipts and all(
        _trusted_receipt_bound_to_head(receipt, head_sha, source_url)
        for receipt in artifact_receipts
    ):
        score += float(points["sha_bound_artifact_receipts"])
    if all(
        item["state"] in FINAL_EXECUTION_STATES for item in critical_execution.values()
    ):
        score += float(points["resolved_ci_invocation_state"])

    authentication_state = str(
        connector.get("authentication_state", "NOT_ASSERTED")
    ).upper()
    error_state = str(connector.get("error_state", "BLOCKED")).upper()
    if error_state not in CONNECTOR_ERROR_STATES:
        raise LiveEvidenceAdapterError(f"connector.error_state is invalid: {error_state}")
    if authentication_state == "BLOCKED" or error_state == "BLOCKED":
        return 0.0
    if authentication_state == "NOT_ASSERTED":
        score = min(score, 50.0)
    if error_state == "PARTIAL":
        score = min(score, 75.0)
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
    score += float(points["required_artifact_categories_observed"]) * present / len(
        required
    )

    resolved = sum(
        1
        for item in critical_execution.values()
        if item["state"] in FINAL_EXECUTION_STATES
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

    if not isinstance(observation, Mapping):
        raise LiveEvidenceAdapterError("repository observation must be an object")
    payload = _validate_observation_contract(observation)

    repository = str(payload["repository"]).strip()
    source_url = str(payload["source_url"]).rstrip("/")
    expected_url = f"https://github.com/{repository}"
    if source_url != expected_url:
        raise LiveEvidenceAdapterError(
            f"source_url must equal {expected_url}, got {source_url}"
        )
    _source_path(source_url)

    head_sha = str(payload["observed_head_sha"]).lower()
    if len(head_sha) not in {40, 64} or any(
        character not in "0123456789abcdef" for character in head_sha
    ):
        raise LiveEvidenceAdapterError(
            "observed_head_sha must contain exactly 40 or 64 lowercase hex characters"
        )

    provenance = _require_mapping(payload["provenance"], "provenance")
    if provenance.get("original_bytes_copied") is not False:
        raise LiveEvidenceAdapterError("copied repository bytes are forbidden")
    if provenance.get("source_linked") is not True:
        raise LiveEvidenceAdapterError("source-linked provenance is required")
    if provenance.get("head_sha_bound") is not True:
        raise LiveEvidenceAdapterError("head-SHA-bound provenance is required")

    active_policy = _validate_adapter_policy(adapter_policy or load_adapter_policy())
    defaults = active_policy["dimension_defaults"]
    artifacts = _require_mapping(payload["artifacts"], "artifacts")
    connector = _require_mapping(payload["connector"], "connector")
    execution = _require_mapping(payload["execution"], "execution")

    authentication_state = str(connector["authentication_state"]).upper()
    if authentication_state not in AUTHENTICATION_STATES:
        raise LiveEvidenceAdapterError(
            f"connector.authentication_state is invalid: {authentication_state}"
        )

    readme = _optional_artifact_receipts(
        artifacts["readme"], "artifacts.readme", head_sha, source_url
    )
    package_manifest = _optional_artifact_receipts(
        artifacts["package_manifest"],
        "artifacts.package_manifest",
        head_sha,
        source_url,
    )
    license_receipts = _optional_artifact_receipts(
        artifacts.get("license", {"present": False, "path": None, "url": None}),
        "artifacts.license",
        head_sha,
        source_url,
    )
    security_policy_receipts = _optional_artifact_receipts(
        artifacts.get(
            "security_policy", {"present": False, "path": None, "url": None}
        ),
        "artifacts.security_policy",
        head_sha,
        source_url,
    )
    category_receipts = {
        "readme": readme,
        "package_manifest": package_manifest,
        "workflows": _artifact_receipts(
            artifacts["workflows"], "artifacts.workflows", head_sha, source_url
        ),
        "source_files": _artifact_receipts(
            artifacts["source_files"],
            "artifacts.source_files",
            head_sha,
            source_url,
        ),
        "test_files": _artifact_receipts(
            artifacts["test_files"], "artifacts.test_files", head_sha, source_url
        ),
        "architecture_files": _artifact_receipts(
            artifacts["architecture_files"],
            "artifacts.architecture_files",
            head_sha,
            source_url,
        ),
        "integration_files": _artifact_receipts(
            artifacts["integration_files"],
            "artifacts.integration_files",
            head_sha,
            source_url,
        ),
        "ai_files": _artifact_receipts(
            artifacts["ai_files"], "artifacts.ai_files", head_sha, source_url
        ),
        "recruiter_files": _artifact_receipts(
            artifacts["recruiter_files"],
            "artifacts.recruiter_files",
            head_sha,
            source_url,
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

    critical_execution = {
        name: _execution_item(execution[name], name)
        for name in active_policy["critical_execution_fields"]
    }

    dimensions: dict[str, Any] = {}
    source_receipts = [*package_manifest, *category_receipts["source_files"]]
    if package_manifest and category_receipts["source_files"]:
        reality_verified = _execution_can_verify(
            critical_execution["build"], head_sha, source_url
        ) and _execution_can_verify(
            critical_execution["tests"],
            head_sha,
            source_url,
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
        "build", execution, head_sha, source_url, defaults["build"]
    )
    dimensions["tests"] = _compile_execution_dimension(
        "tests", execution, head_sha, source_url, defaults["tests"]
    )

    documentation_item = critical_execution["documentation"]
    documentation_execution = _compile_execution_dimension(
        "documentation",
        execution,
        head_sha,
        source_url,
        defaults["documentation"],
    )
    if (
        documentation_execution["state"] == "UNVERIFIED"
        and readme
        and documentation_item["state"] != "FAILURE"
    ):
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
        "security", execution, head_sha, source_url, defaults["security"]
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
        "observed_at": payload["observed_at"],
        "dimensions": dimensions,
        "quality_context": {
            "connector_quality_score": connector_quality,
            "data_quality_score": data_quality,
        },
        "blockers": sorted({str(item) for item in payload["blockers"] if str(item)}),
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
