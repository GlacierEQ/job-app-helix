from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from math import isfinite
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from job_app_helix.estate_compiler import SCHEMA_VERSION as ESTATE_SCHEMA_VERSION
from job_app_helix.estate_compiler import digest as estate_digest

POLICY_SCHEMA = "glaciereq.frontier-innovation-policy.v1"
MEASURED_STATUS = "MEASURED"
VERIFICATION_ASSERTING_STATUSES = {"VERIFIED", "MEASURED"}
OPERATOR_ONLY_TRANSITIONS = frozenset({"SOURCE_BOUND", "SUPERSEDED", "ARCHIVED"})
ESTATE_REGISTRIES = (
    "system_registry",
    "capability_donor_registry",
    "company_projection_registry",
)


class InnovationContractError(ValueError):
    """Raised when an innovation-engine invariant is violated."""


@dataclass(frozen=True)
class PromotionDecision:
    ready: bool
    failures: tuple[str, ...]


@dataclass(frozen=True)
class ReviewDecision:
    survives: bool
    blockers: tuple[str, ...]


@dataclass(frozen=True)
class RankedTarget:
    repository: str
    system_id: str
    score: float


@dataclass(frozen=True)
class RankedHypothesis:
    hypothesis_id: str
    score: float


def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise InnovationContractError(f"{path} must contain a JSON object")
    return payload


def load_policy(path: Path | None = None) -> dict[str, Any]:
    policy_path = path or repository_root() / "manifests" / "innovation_engine_policy.json"
    policy = load_json(policy_path)
    if policy.get("schema") != POLICY_SCHEMA:
        raise InnovationContractError("innovation policy schema mismatch")
    states = policy.get("states")
    if not isinstance(states, dict) or not states:
        raise InnovationContractError("innovation policy requires states")
    if any(not isinstance(targets, list) for targets in states.values()):
        raise InnovationContractError("innovation policy state targets must be lists")
    return policy


def schema_path(name: str, root: Path | None = None) -> Path:
    base = root or repository_root()
    path = base / "schemas" / "estate" / f"{name}.schema.json"
    if not path.is_file():
        raise InnovationContractError(f"unknown estate schema: {name}")
    return path


def validate_payload(
    payload: Mapping[str, Any],
    schema_name: str,
    root: Path | None = None,
) -> None:
    schema = load_json(schema_path(schema_name, root))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(dict(payload)), key=lambda item: list(item.path))
    if errors:
        rendered = "; ".join(error.message for error in errors)
        raise InnovationContractError(f"{schema_name} validation failed: {rendered}")


def assert_expected_head(expected_head: str, observed_head: str) -> None:
    if not expected_head or not observed_head:
        raise InnovationContractError("expected-head guard requires both commit identities")
    if expected_head != observed_head:
        raise InnovationContractError(
            f"stale repository state: expected {expected_head}, observed {observed_head}"
        )


def transition_allowed(
    current: str,
    target: str,
    policy: Mapping[str, Any] | None = None,
) -> bool:
    active = dict(policy or load_policy())
    states = active.get("states")
    if not isinstance(states, dict) or current not in states:
        raise InnovationContractError(f"unknown current state: {current}")
    targets = states[current]
    if not isinstance(targets, list):
        raise InnovationContractError(f"invalid transition policy for {current}")
    return target in targets


def _has_artifact(run: Mapping[str, Any], field: str) -> bool:
    value = run.get(field)
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return bool(value)
    if isinstance(value, Mapping):
        return bool(value)
    if isinstance(value, Sequence) and not isinstance(value, bytes):
        return bool(value)
    return False


def _assert_run_head_fresh(run: Mapping[str, Any], target: str) -> None:
    if target in {"BLOCKED", "QUARANTINED"}:
        return
    expected = run.get("expected_head")
    observed = run.get("observed_head")
    if expected is None and observed is None:
        return
    assert_expected_head(str(expected or ""), str(observed or ""))


def _assert_promotion_record(run: Mapping[str, Any]) -> None:
    record = run.get("promotion_record")
    if not isinstance(record, dict):
        raise InnovationContractError("promotion transition requires promotion_record")
    validate_payload(record, "promotion")
    decision = promotion_gate(record)
    if not decision.ready:
        raise InnovationContractError(
            f"promotion record is not ready: {list(decision.failures)}"
        )
    bindings = {
        "repository": run.get("repository"),
        "expected_head": run.get("expected_head"),
        "observed_head": run.get("observed_head"),
    }
    for field, expected_value in bindings.items():
        if record.get(field) != expected_value:
            raise InnovationContractError(
                f"promotion record {field} does not match engineering run"
            )
    if record.get("source_head") != run.get("observed_head"):
        raise InnovationContractError(
            "promotion record source_head does not match observed engineering head"
        )


def _assert_transition_artifacts(
    run: Mapping[str, Any],
    target: str,
    policy: Mapping[str, Any],
) -> None:
    requirements = policy.get("transition_requirements", {})
    if not isinstance(requirements, dict):
        raise InnovationContractError("transition_requirements must be an object")
    fields = requirements.get(target, [])
    if not isinstance(fields, list):
        raise InnovationContractError(f"transition requirements for {target} must be a list")
    missing = [field for field in fields if not _has_artifact(run, field)]
    if missing:
        raise InnovationContractError(f"{target} missing required artifacts: {missing}")

    semantic_guards = {
        "BASELINE_VERIFIED": ("baseline_status", "VERIFIED"),
        "VERIFIED": ("verification_status", "VERIFIED"),
        "ADVERSARIALLY_REVIEWED": ("adversarial_review_decision", "SURVIVES"),
    }
    guard = semantic_guards.get(target)
    if guard and run.get(guard[0]) != guard[1]:
        raise InnovationContractError(
            f"{target} requires {guard[0]}={guard[1]!r}; observed {run.get(guard[0])!r}"
        )
    if target == "HYPOTHESES_EVALUATED" and run.get("novelty_decision") not in {
        "ADAPT",
        "PROCEED",
    }:
        raise InnovationContractError(
            "HYPOTHESES_EVALUATED requires novelty_decision='ADAPT' or 'PROCEED'"
        )
    if target in {"PROMOTION_READY", "SOURCE_BOUND"}:
        _assert_promotion_record(run)
    _assert_run_head_fresh(run, target)


def transition_run(
    run: Mapping[str, Any],
    target: str,
    evidence_refs: Sequence[str],
    policy: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    active = dict(policy or load_policy())
    current = str(run.get("state") or "")
    if target in OPERATOR_ONLY_TRANSITIONS:
        raise InnovationContractError(
            f"{target} is an operator-only status; the innovation engine may "
            "prepare evidence and a recommendation but cannot assign it."
        )
    if not transition_allowed(current, target, active):
        raise InnovationContractError(f"illegal transition: {current} -> {target}")
    if not evidence_refs:
        raise InnovationContractError("state transitions require evidence_refs")
    if current == "BLOCKED":
        blocked_from = run.get("blocked_from_state")
        if not isinstance(blocked_from, str) or target != blocked_from:
            raise InnovationContractError(
                f"BLOCKED run may resume only at blocked_from_state={blocked_from!r}"
            )
    _assert_transition_artifacts(run, target, active)
    updated = dict(run)
    history = list(updated.get("history") or [])
    history.append(
        {
            "from": current,
            "to": target,
            "evidence_refs": list(evidence_refs),
        }
    )
    updated["state"] = target
    updated["history"] = history
    if target == "BLOCKED":
        updated["blocked_from_state"] = current
    elif current == "BLOCKED":
        updated["blocked_from_state"] = None
    if target in {"PROMOTION_READY", "SOURCE_BOUND"}:
        updated["promotion_ready"] = True
    return updated


def _assert_measurement_records(records: Sequence[Mapping[str, Any]]) -> None:
    for index, record in enumerate(records):
        validate_payload(record, "measurement")
        for field in ("value", "before", "after"):
            value = record.get(field)
            if value is not None and not isfinite(float(value)):
                raise InnovationContractError(
                    f"measurement[{index}].{field} must be finite"
                )


def promotion_gate(
    payload: Mapping[str, Any],
    policy: Mapping[str, Any] | None = None,
) -> PromotionDecision:
    active = dict(policy or load_policy())
    required = active.get("promotion_required")
    if not isinstance(required, list) or not all(isinstance(item, str) for item in required):
        raise InnovationContractError("promotion policy requires string gate names")
    failures = [name for name in required if payload.get(name) is not True]

    expected = payload.get("expected_head")
    observed = payload.get("observed_head")
    source = payload.get("source_head")
    heads_present = expected is not None or observed is not None
    heads_mismatch = (
        not isinstance(expected, str)
        or not isinstance(observed, str)
        or expected != observed
    )
    if heads_present and heads_mismatch:
        failures.append("expected_head_match")
    if not isinstance(source, str) or source != observed:
        failures.append("source_head_match")
    if payload.get("decision") != "PROMOTION_READY":
        failures.append("promotion_decision")

    benchmark = payload.get("benchmark")
    if isinstance(benchmark, dict) and benchmark.get("required") is True:
        if benchmark.get("measured") is not True:
            failures.append("benchmark_measured")
        results = benchmark.get("results")
        if not isinstance(results, list) or not results:
            failures.append("benchmark_results")
        else:
            try:
                _assert_measurement_records(results)
            except InnovationContractError:
                failures.append("benchmark_results")

    deduplicated = tuple(dict.fromkeys(failures))
    return PromotionDecision(ready=not deduplicated, failures=deduplicated)


def adversarial_gate(payload: Mapping[str, Any]) -> ReviewDecision:
    validate_payload(payload, "adversarial-review")
    blockers = []
    if payload.get("decision") != "SURVIVES":
        blockers.append("review_decision")
    criticisms = payload.get("criticisms", [])
    if isinstance(criticisms, list) and any(
        isinstance(item, dict) and item.get("disposition") == "INVALIDATED_CANDIDATE"
        for item in criticisms
    ):
        blockers.append("candidate_invalidated")
    result = tuple(dict.fromkeys(blockers))
    return ReviewDecision(survives=not result, blockers=result)


def novelty_gate(payload: Mapping[str, Any]) -> ReviewDecision:
    validate_payload(payload, "novelty-review")
    blockers = []
    decision = payload.get("decision")
    if decision == "REJECT":
        blockers.append("novelty_rejected")
    if decision == "PROCEED" and payload.get("wrapper_only") is True:
        blockers.append("wrapper_only")
    if decision == "PROCEED" and payload.get("standard_functionality_rebranded") is True:
        blockers.append("standard_functionality_rebranded")
    if decision == "PROCEED" and payload.get("existing_library_superior") is True:
        blockers.append("existing_library_superior")
    result = tuple(dict.fromkeys(blockers))
    return ReviewDecision(survives=not result, blockers=result)


def build_evidence_receipt(
    *,
    claim_id: str,
    claim: str,
    status: str,
    mechanism: str,
    implementation: Sequence[str],
    verification: Sequence[str],
    source_head: str,
    measured_results: Sequence[Mapping[str, Any]] | None = None,
    limitations: Sequence[str] = (),
    policy: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    active = dict(policy or load_policy())
    statuses = active.get("claim_statuses")
    if not isinstance(statuses, list) or status not in statuses:
        raise InnovationContractError(f"unsupported claim status: {status}")
    if status in VERIFICATION_ASSERTING_STATUSES and not verification:
        raise InnovationContractError(f"{status} claims require verification evidence")
    if status == MEASURED_STATUS and not measured_results:
        raise InnovationContractError("MEASURED claims require measured_results")
    if measured_results:
        _assert_measurement_records(measured_results)
    if not claim_id or not claim or not mechanism or not source_head:
        raise InnovationContractError("evidence receipt identity fields are required")
    receipt = {
        "schema": "glaciereq.evidence.v1",
        "claim_id": claim_id,
        "claim": claim,
        "status": status,
        "mechanism": mechanism,
        "implementation": list(implementation),
        "verification": list(verification),
        "measured_results": [dict(item) for item in measured_results or []],
        "limitations": list(limitations),
        "source_head": source_head,
    }
    validate_payload(receipt, "evidence")
    return receipt


def _unit_interval(candidate: Mapping[str, Any], key: str) -> float:
    value = candidate.get(key)
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise InnovationContractError(f"{key} must be numeric")
    numeric = float(value)
    if not isfinite(numeric):
        raise InnovationContractError(f"{key} must be finite")
    if numeric < 0.0 or numeric > 1.0:
        raise InnovationContractError(f"{key} must be within [0, 1]")
    return numeric


def _weight(weights: Mapping[str, Any], key: str) -> float:
    if key not in weights:
        raise InnovationContractError(f"missing score weight: {key}")
    raw = weights[key]
    if not isinstance(raw, (int, float)) or isinstance(raw, bool):
        raise InnovationContractError(f"score weight {key} must be numeric")
    value = float(raw)
    if not isfinite(value) or value < 0.0:
        raise InnovationContractError(
            f"score weight {key} must be finite and non-negative"
        )
    return value


def _weighted_score(
    candidate: Mapping[str, Any],
    weights: Mapping[str, Any],
    positive_keys: Sequence[str],
    negative_keys: Sequence[str],
) -> float:
    positive_weights = {key: _weight(weights, key) for key in positive_keys}
    negative_weights = {key: _weight(weights, key) for key in negative_keys}
    positive_weight = sum(positive_weights.values())
    penalty_weight = sum(negative_weights.values())
    if positive_weight <= 0.0:
        raise InnovationContractError("positive score weights must have non-zero sum")
    if penalty_weight <= 0.0:
        raise InnovationContractError("penalty score weights must have non-zero sum")
    positive = sum(
        _unit_interval(candidate, key) * positive_weights[key] for key in positive_keys
    )
    benefit = positive / positive_weight
    penalty = sum(
        _unit_interval(candidate, key) * negative_weights[key] for key in negative_keys
    )
    return round(benefit / (1.0 + (penalty / penalty_weight)), 8)


def priority_score(
    candidate: Mapping[str, Any],
    policy: Mapping[str, Any] | None = None,
) -> float:
    active = dict(policy or load_policy())
    weights = active.get("priority_weights")
    if not isinstance(weights, dict):
        raise InnovationContractError("priority_weights must be an object")
    positive = (
        "bottleneck_importance",
        "repository_fit",
        "proofability",
        "cross_repo_compounding",
        "enterprise_relevance",
        "expected_value",
    )
    negative = ("implementation_cost", "regression_risk", "uncertainty")
    return _weighted_score(candidate, weights, positive, negative)


def hypothesis_score(
    candidate: Mapping[str, Any],
    policy: Mapping[str, Any] | None = None,
) -> float:
    active = dict(policy or load_policy())
    weights = active.get("hypothesis_weights")
    if not isinstance(weights, dict):
        raise InnovationContractError("hypothesis_weights must be an object")
    positive = (
        "bottleneck_fit",
        "expected_system_effect",
        "proofability",
        "information_advantage",
        "simplicity",
        "reuse_compounding",
        "novelty_confidence",
    )
    negative = (
        "implementation_cost",
        "regression_risk",
        "uncertainty",
        "standard_solution_penalty",
    )
    return _weighted_score(candidate, weights, positive, negative)


def rank_targets(
    candidates: Sequence[Mapping[str, Any]],
    policy: Mapping[str, Any] | None = None,
) -> tuple[RankedTarget, ...]:
    ranked: list[RankedTarget] = []
    seen: set[tuple[str, str]] = set()
    for candidate in candidates:
        repository = candidate.get("repository")
        system_id = candidate.get("system_id")
        if not isinstance(repository, str) or not repository:
            raise InnovationContractError("priority candidate requires repository")
        if not isinstance(system_id, str) or not system_id:
            raise InnovationContractError("priority candidate requires system_id")
        identity = (repository, system_id)
        if identity in seen:
            raise InnovationContractError(f"duplicate target assessment identity: {identity!r}")
        seen.add(identity)
        ranked.append(RankedTarget(repository, system_id, priority_score(candidate, policy)))
    return tuple(sorted(ranked, key=lambda item: (-item.score, item.repository.casefold())))


def rank_hypotheses(
    candidates: Sequence[Mapping[str, Any]],
    policy: Mapping[str, Any] | None = None,
) -> tuple[RankedHypothesis, ...]:
    if len(candidates) < 2:
        raise InnovationContractError("hypothesis tournament requires at least two candidates")
    ranked: list[RankedHypothesis] = []
    seen: set[str] = set()
    for candidate in candidates:
        validate_payload(candidate, "hypothesis-assessment")
        hypothesis_id = candidate.get("hypothesis_id")
        if not isinstance(hypothesis_id, str) or not hypothesis_id:
            raise InnovationContractError("hypothesis assessment requires hypothesis_id")
        if hypothesis_id in seen:
            raise InnovationContractError(
                f"duplicate hypothesis assessment identity: {hypothesis_id}"
            )
        seen.add(hypothesis_id)
        ranked.append(RankedHypothesis(hypothesis_id, hypothesis_score(candidate, policy)))
    return tuple(sorted(ranked, key=lambda item: (-item.score, item.hypothesis_id.casefold())))


def compile_hypothesis_tournament(
    assessments: Sequence[Mapping[str, Any]],
    policy: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    ranked = rank_hypotheses(assessments, policy)
    by_id = {item["hypothesis_id"]: dict(item) for item in assessments}
    result = {
        "schema": "glaciereq.hypothesis-tournament.v1",
        "winner_hypothesis_id": ranked[0].hypothesis_id,
        "candidates": [
            {
                **by_id[item.hypothesis_id],
                "score": item.score,
                "rank": rank,
                "decision": "SELECTED" if rank == 1 else "REJECTED",
            }
            for rank, item in enumerate(ranked, start=1)
        ],
    }
    validate_payload(result, "hypothesis-tournament")
    return result


def _verify_content_hash(payload: Mapping[str, Any], label: str) -> str:
    recorded = payload.get("content_hash")
    if not isinstance(recorded, str) or not recorded:
        raise InnovationContractError(f"{label} requires content_hash")
    unsigned = dict(payload)
    unsigned.pop("content_hash", None)
    actual = estate_digest(unsigned)
    if actual != recorded:
        raise InnovationContractError(
            f"{label} content_hash mismatch: recorded={recorded}, actual={actual}"
        )
    return recorded


def validate_estate_bundle_integrity(
    estate_bundle: Mapping[str, Any],
    expected_estate_hash: str,
) -> str:
    if not expected_estate_hash:
        raise InnovationContractError("trusted expected estate hash is required")
    if estate_bundle.get("schema") != ESTATE_SCHEMA_VERSION:
        raise InnovationContractError("unsupported estate compiler schema")
    bundle_hash = _verify_content_hash(estate_bundle, "estate bundle")
    if bundle_hash != expected_estate_hash:
        raise InnovationContractError(
            "estate bundle does not match trusted expected estate hash"
        )

    receipt = estate_bundle.get("receipt")
    if not isinstance(receipt, dict) or receipt.get("status") not in {
        "PASS",
        "PASS_WITH_UNRESOLVED",
    }:
        raise InnovationContractError("estate bundle requires a passing compiler receipt")
    registry_hashes = receipt.get("registry_hashes")
    if not isinstance(registry_hashes, dict):
        raise InnovationContractError("estate receipt requires registry_hashes")
    for name in ESTATE_REGISTRIES:
        registry = estate_bundle.get(name)
        if not isinstance(registry, dict):
            raise InnovationContractError(f"estate bundle missing {name}")
        registry_hash = _verify_content_hash(registry, name)
        if registry_hashes.get(name) != registry_hash:
            raise InnovationContractError(f"estate receipt hash mismatch for {name}")
    return bundle_hash


def compile_estate_target_queue(
    estate_bundle: Mapping[str, Any],
    assessments: Sequence[Mapping[str, Any]],
    expected_estate_hash: str,
    policy: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    bundle_hash = validate_estate_bundle_integrity(
        estate_bundle,
        expected_estate_hash,
    )
    source_digest = estate_bundle.get("source_digest")
    if not isinstance(source_digest, str) or not source_digest:
        raise InnovationContractError("estate bundle requires source_digest")
    registry = estate_bundle["system_registry"]
    systems = registry.get("systems")
    if not isinstance(systems, list):
        raise InnovationContractError("system_registry.systems must be a list")

    reference = {
        (row.get("source_repository"), row.get("system_id"))
        for row in systems
        if isinstance(row, dict)
    }
    normalized: list[dict[str, Any]] = []
    for assessment in assessments:
        candidate = dict(assessment)
        validate_payload(candidate, "target-assessment")
        identity = (candidate.get("repository"), candidate.get("system_id"))
        if identity not in reference:
            raise InnovationContractError(
                "target assessment must resolve to an existing reference estate system: "
                f"{identity!r}"
            )
        normalized.append(candidate)

    ranked = rank_targets(normalized, policy)
    by_identity = {
        (item["repository"], item["system_id"]): item for item in normalized
    }
    queue = {
        "schema": "glaciereq.frontier-target-queue.v1",
        "estate_bundle_hash": bundle_hash,
        "estate_source_digest": source_digest,
        "targets": [
            {
                **by_identity[(item.repository, item.system_id)],
                "priority_score": item.score,
                "rank": rank,
            }
            for rank, item in enumerate(ranked, start=1)
        ],
    }
    validate_payload(queue, "target-queue")
    return queue


def compile_engineering_ledger(run: Mapping[str, Any]) -> dict[str, Any]:
    fields = (
        "system",
        "bottleneck",
        "root_cause",
        "invention",
        "implementation",
        "verification",
        "measured_results",
        "enterprise_consequence",
        "failure_boundaries",
        "evidence",
        "next_constraint",
    )
    missing = [field for field in fields if field not in run]
    if missing:
        raise InnovationContractError(f"engineering ledger missing fields: {missing}")
    ledger = {field: run[field] for field in fields}
    validate_payload(ledger, "engineering-ledger")
    return ledger
