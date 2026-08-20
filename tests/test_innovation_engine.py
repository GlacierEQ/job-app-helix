from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from job_app_helix.estate_compiler import SCHEMA_VERSION as ESTATE_SCHEMA_VERSION
from job_app_helix.estate_compiler import digest as estate_digest
from job_app_helix.innovation_engine import (
    InnovationContractError,
    adversarial_gate,
    assert_expected_head,
    build_evidence_receipt,
    compile_engineering_ledger,
    compile_estate_target_queue,
    compile_hypothesis_tournament,
    load_policy,
    novelty_gate,
    priority_score,
    promotion_gate,
    rank_targets,
    transition_allowed,
    transition_run,
    validate_estate_bundle_integrity,
    validate_payload,
)

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schemas" / "estate"


def assessment(repository: str, system_id: str, value: float) -> dict[str, object]:
    return {
        "schema": "glaciereq.target-assessment.v1",
        "repository": repository,
        "system_id": system_id,
        "bottleneck_importance": value,
        "repository_fit": value,
        "proofability": value,
        "cross_repo_compounding": value,
        "enterprise_relevance": value,
        "expected_value": value,
        "implementation_cost": 1.0 - value,
        "regression_risk": 1.0 - value,
        "uncertainty": 1.0 - value,
        "rationale_refs": ["fixture:assessment"],
    }


def hypothesis(hypothesis_id: str, value: float) -> dict[str, object]:
    return {
        "schema": "glaciereq.hypothesis-assessment.v1",
        "hypothesis_id": hypothesis_id,
        "bottleneck_fit": value,
        "expected_system_effect": value,
        "proofability": value,
        "information_advantage": value,
        "simplicity": value,
        "reuse_compounding": value,
        "novelty_confidence": value,
        "implementation_cost": 1.0 - value,
        "regression_risk": 1.0 - value,
        "uncertainty": 1.0 - value,
        "standard_solution_penalty": 1.0 - value,
        "rationale_refs": ["fixture:hypothesis"],
    }


def novelty_review(decision: str) -> dict[str, object]:
    return {
        "schema": "glaciereq.novelty-review.v1",
        "novelty_review_id": "novelty-1",
        "hypothesis_id": "candidate-a",
        "alternatives": [
            {
                "name": "existing-library",
                "why_not_selected": "Fixture comparison for contract testing.",
                "evidence_refs": ["fixture:alternative"],
            }
        ],
        "wrapper_only": False,
        "standard_functionality_rebranded": False,
        "existing_library_superior": False,
        "meaningful_new_combination": True,
        "ignored_information": ["fixture signal"],
        "operational_steps_eliminated": [],
        "asymptotic_change": None,
        "failure_characteristic_change": "Fixture failure improvement.",
        "enables_previously_impractical": None,
        "measurable_improvement": "Fixture metric.",
        "decision": decision,
        "evidence_refs": ["fixture:novelty"],
        "limitations": [],
    }


def measurement() -> dict[str, object]:
    return {
        "metric": "p95_ms",
        "unit": "ms",
        "before": 20.0,
        "after": 12.0,
        "sample_size": 100,
        "methodology_ref": "benchmarks/p95.md",
        "evidence_ref": "evidence/p95.json",
    }


def promotion_record(head: str = "abc123", *, ready: bool = True) -> dict[str, object]:
    return {
        "schema": "glaciereq.promotion.v1",
        "repository": "GlacierEQ/high",
        "source_head": head,
        "expected_head": head,
        "observed_head": head,
        "baseline_preserved": True,
        "central_mechanism_implemented": True,
        "existing_tests_pass": True,
        "new_behavior_tested": True,
        "failure_path_tested": ready,
        "regression_risk_assessed": True,
        "claims_match_evidence": True,
        "architecture_documented": True,
        "limitations_documented": True,
        "benchmark": {
            "required": False,
            "measured": False,
            "results": [],
            "reason": "No performance claim introduced.",
        },
        "decision": "PROMOTION_READY" if ready else "REJECTED",
        "evidence_refs": ["verification:fixture"],
    }


def operator_authorization(
    target_state: str,
    *,
    repository: str = "GlacierEQ/high",
    expected_head: str = "abc123",
    observed_head: str = "abc123",
) -> dict[str, object]:
    return {
        "authorization_id": "operator-authorization-1",
        "operator_intent_id": "operator-intent-1",
        "status": "APPROVED",
        "target_state": target_state,
        "repository": repository,
        "expected_head": expected_head,
        "observed_head": observed_head,
    }


def _hashed_registry(payload: dict[str, object]) -> dict[str, object]:
    result = dict(payload)
    result["content_hash"] = estate_digest(result)
    return result


def estate_bundle() -> dict[str, object]:
    systems = _hashed_registry(
        {
            "schema": "glaciereq.reference-system-registry.v1",
            "systems": [
                {"source_repository": "GlacierEQ/high", "system_id": "sys-high"}
            ],
        }
    )
    capabilities = _hashed_registry(
        {"schema": "glaciereq.capability-donor-registry.v1", "capabilities": []}
    )
    companies = _hashed_registry(
        {
            "schema": "glaciereq.company-projection-registry.v1",
            "projections": [],
            "promotion_scores": {},
        }
    )
    bundle: dict[str, object] = {
        "schema": ESTATE_SCHEMA_VERSION,
        "source_digest": "source-fixture",
        "system_registry": systems,
        "capability_donor_registry": capabilities,
        "company_projection_registry": companies,
        "experiment_pipeline": [],
        "receipt": {
            "schema": "glaciereq.estate-compiler-receipt.v1",
            "status": "PASS",
            "registry_hashes": {
                "system_registry": systems["content_hash"],
                "capability_donor_registry": capabilities["content_hash"],
                "company_projection_registry": companies["content_hash"],
            },
        },
    }
    bundle["content_hash"] = estate_digest(bundle)
    return bundle


def test_all_estate_schemas_are_valid_draft_2020_12() -> None:
    paths = sorted(SCHEMA_DIR.glob("*.schema.json"))
    assert len(paths) >= 25
    for path in paths:
        Draft202012Validator.check_schema(json.loads(path.read_text(encoding="utf-8")))


def test_transition_requires_state_specific_artifacts() -> None:
    policy = load_policy()
    run = {"state": "DISCOVERED", "history": []}
    with pytest.raises(InnovationContractError, match="missing required artifacts"):
        transition_run(run, "CENSUSED", ["census:verified"], policy)

    run["census_ref"] = "census:verified"
    advanced = transition_run(run, "CENSUSED", ["census:verified"], policy)
    assert advanced["state"] == "CENSUSED"
    assert advanced["history"][0]["evidence_refs"] == ["census:verified"]

    with pytest.raises(InnovationContractError, match="operator-only status"):
        transition_run(run, "SOURCE_BOUND", ["wishful-thinking"], policy)
    with pytest.raises(InnovationContractError, match="require evidence_refs"):
        transition_run(run, "CENSUSED", [], policy)


def test_any_normal_state_advance_rejects_stale_head() -> None:
    run = {
        "state": "DISCOVERED",
        "history": [],
        "census_ref": "fixture:census",
        "expected_head": "abc123",
        "observed_head": "def456",
    }
    with pytest.raises(InnovationContractError, match="stale repository state"):
        transition_run(run, "CENSUSED", ["fixture:census"])


def test_blocked_run_can_only_resume_at_recorded_stage() -> None:
    run = {
        "state": "CENSUSED",
        "history": [],
        "census_ref": "fixture:census",
        "expected_head": "abc123",
        "observed_head": "def456",
    }
    blocked = transition_run(run, "BLOCKED", ["fixture:blocker"])
    assert blocked["blocked_from_state"] == "CENSUSED"
    with pytest.raises(InnovationContractError, match="blocked_from_state"):
        transition_run(blocked, "PROMOTION_READY", ["fixture:skip"])

    blocked["observed_head"] = "abc123"
    resumed = transition_run(blocked, "CENSUSED", ["fixture:resume"])
    assert resumed["state"] == "CENSUSED"
    assert resumed["blocked_from_state"] is None


def test_semantic_transition_guards_block_false_verification() -> None:
    run = {
        "state": "IMPLEMENTED",
        "history": [],
        "verification": ["verification:fixture"],
        "verification_status": "FAILED",
        "failure_model_id": "failure:fixture",
        "observability_contract_id": "observability:fixture",
    }
    with pytest.raises(InnovationContractError, match="verification_status='VERIFIED'"):
        transition_run(run, "VERIFIED", ["verification:fixture"])

    run["verification_status"] = "VERIFIED"
    assert transition_run(run, "VERIFIED", ["verification:fixture"])["state"] == "VERIFIED"


def test_hypothesis_state_rejects_failed_novelty_review() -> None:
    run = {
        "state": "RESEARCHED",
        "history": [],
        "hypothesis_ids": ["candidate-a", "candidate-b"],
        "hypothesis_tournament_id": "tournament-1",
        "novelty_review_ids": ["novelty-1"],
        "novelty_decision": "REJECT",
    }
    with pytest.raises(InnovationContractError, match="novelty_decision"):
        transition_run(run, "HYPOTHESES_EVALUATED", ["fixture:novelty"])

    run["novelty_decision"] = "PROCEED"
    updated = transition_run(run, "HYPOTHESES_EVALUATED", ["fixture:novelty"])
    assert updated["state"] == "HYPOTHESES_EVALUATED"


def test_expected_head_guard_fails_closed() -> None:
    assert_expected_head("abc", "abc")
    with pytest.raises(InnovationContractError, match="stale repository state"):
        assert_expected_head("abc", "def")


def test_measured_claim_requires_substantive_finite_results() -> None:
    with pytest.raises(InnovationContractError, match="MEASURED claims require"):
        build_evidence_receipt(
            claim_id="claim-1",
            claim="Latency improved.",
            status="MEASURED",
            mechanism="bounded batching",
            implementation=["src/example.py"],
            verification=["tests/test_example.py"],
            source_head="abc123",
        )
    with pytest.raises(InnovationContractError, match="measurement validation failed"):
        build_evidence_receipt(
            claim_id="claim-1",
            claim="Latency improved.",
            status="MEASURED",
            mechanism="bounded batching",
            implementation=["src/example.py"],
            verification=["tests/test_example.py"],
            source_head="abc123",
            measured_results=[{}],
        )
    invalid = measurement()
    invalid["after"] = float("nan")
    with pytest.raises(InnovationContractError, match="must be finite"):
        build_evidence_receipt(
            claim_id="claim-1",
            claim="Latency improved.",
            status="MEASURED",
            mechanism="bounded batching",
            implementation=["src/example.py"],
            verification=["tests/test_example.py"],
            source_head="abc123",
            measured_results=[invalid],
        )

    receipt = build_evidence_receipt(
        claim_id="claim-1",
        claim="Latency improved.",
        status="MEASURED",
        mechanism="bounded batching",
        implementation=["src/example.py"],
        verification=["tests/test_example.py"],
        source_head="abc123",
        measured_results=[measurement()],
    )
    assert receipt["status"] == "MEASURED"


def test_verified_claim_requires_verification_evidence() -> None:
    with pytest.raises(InnovationContractError, match="VERIFIED claims require"):
        build_evidence_receipt(
            claim_id="claim-verified",
            claim="Invariant holds.",
            status="VERIFIED",
            mechanism="generation fence",
            implementation=["src/example.py"],
            verification=[],
            source_head="abc123",
        )


def test_verification_schema_rejects_verified_receipt_with_failed_step() -> None:
    receipt = {
        "schema": "glaciereq.verification.v1",
        "verification_id": "verification-1",
        "repository": "GlacierEQ/high",
        "source_head": "abc123",
        "status": "VERIFIED",
        "steps": [
            {
                "kind": "UNIT",
                "result": "FAIL",
                "evidence_refs": ["tests:test"],
            }
        ],
        "limitations": [],
    }
    with pytest.raises(InnovationContractError, match="verification validation failed"):
        validate_payload(receipt, "verification")


def test_promotion_gate_rejects_failure_gap_benchmark_gap_and_stale_base() -> None:
    payload = promotion_record("abc123")
    payload["observed_head"] = "def456"
    payload["failure_path_tested"] = False
    payload["benchmark"] = {
        "required": True,
        "measured": False,
        "results": [],
        "reason": "Performance claim requires measurement.",
    }
    decision = promotion_gate(payload)
    assert not decision.ready
    assert set(decision.failures) == {
        "failure_path_tested",
        "expected_head_match",
        "source_head_match",
        "benchmark_measured",
        "benchmark_results",
    }


def test_promotion_transition_consumes_real_gate_not_boolean() -> None:
    run = {
        "state": "ADVERSARIALLY_REVIEWED",
        "history": [],
        "repository": "GlacierEQ/high",
        "expected_head": "abc123",
        "observed_head": "abc123",
        "promotion_id": "promotion-1",
        "promotion_record": promotion_record("abc123", ready=False),
        "promotion_ready": True,
    }
    with pytest.raises(InnovationContractError, match="promotion record is not ready"):
        transition_run(run, "PROMOTION_READY", ["promotion:fixture"])

    run["promotion_record"] = promotion_record("abc123", ready=True)
    promoted = transition_run(run, "PROMOTION_READY", ["promotion:fixture"])
    assert promoted["promotion_ready"] is True


def test_priority_ranking_is_deterministic_and_penalizes_risk() -> None:
    high = assessment("GlacierEQ/high", "sys-high", 0.9)
    low = assessment("GlacierEQ/low", "sys-low", 0.4)
    ranked = rank_targets([low, high])
    assert [item.repository for item in ranked] == ["GlacierEQ/high", "GlacierEQ/low"]
    assert ranked[0].score > ranked[1].score


def test_scoring_rejects_nonfinite_values_and_zero_weight_sets() -> None:
    candidate = assessment("GlacierEQ/high", "sys-high", 0.9)
    candidate["expected_value"] = float("nan")
    with pytest.raises(InnovationContractError, match="must be finite"):
        priority_score(candidate)

    policy = load_policy()
    policy["priority_weights"] = {
        key: 0.0 for key in policy["priority_weights"]
    }
    with pytest.raises(InnovationContractError, match="non-zero sum"):
        priority_score(assessment("GlacierEQ/high", "sys-high", 0.9), policy)


def test_duplicate_target_and_hypothesis_identities_are_rejected() -> None:
    target = assessment("GlacierEQ/high", "sys-high", 0.9)
    with pytest.raises(InnovationContractError, match="duplicate target assessment"):
        rank_targets([target, dict(target)])

    idea = hypothesis("candidate-a", 0.9)
    with pytest.raises(InnovationContractError, match="duplicate hypothesis assessment"):
        compile_hypothesis_tournament([idea, dict(idea)])


def test_hypothesis_tournament_selects_strongest_and_rejects_weak_candidate() -> None:
    result = compile_hypothesis_tournament(
        [hypothesis("candidate-b", 0.3), hypothesis("candidate-a", 0.9)]
    )
    assert result["winner_hypothesis_id"] == "candidate-a"
    assert result["candidates"][0]["decision"] == "SELECTED"
    assert result["candidates"][1]["decision"] == "REJECTED"
    validate_payload(result, "hypothesis-tournament")


def test_hypothesis_tournament_requires_actual_competition() -> None:
    with pytest.raises(InnovationContractError, match="at least two candidates"):
        compile_hypothesis_tournament([hypothesis("candidate-a", 0.9)])


def test_novelty_gate_rejects_fake_novelty() -> None:
    review = novelty_review("PROCEED")
    review["wrapper_only"] = True
    decision = novelty_gate(review)
    assert not decision.survives
    assert decision.blockers == ("wrapper_only",)

    adapted = novelty_review("ADAPT")
    adapted["existing_library_superior"] = True
    assert novelty_gate(adapted).survives


def test_adversarial_schema_rejects_internal_contradiction() -> None:
    review = {
        "schema": "glaciereq.adversarial-review.v1",
        "review_id": "review-1",
        "repository": "GlacierEQ/high",
        "source_head": "abc123",
        "criticisms": [
            {
                "attack": "The mechanism duplicates a standard library.",
                "evidence_refs": ["fixture:comparison"],
                "disposition": "INVALIDATED_CANDIDATE",
                "resolution": "Candidate rejected before promotion.",
            }
        ],
        "remaining_limitations": [],
        "decision": "SURVIVES",
    }
    with pytest.raises(InnovationContractError, match="adversarial-review validation failed"):
        validate_payload(review, "adversarial-review")


def test_adversarial_gate_rejects_invalidated_candidate() -> None:
    review = {
        "schema": "glaciereq.adversarial-review.v1",
        "review_id": "review-1",
        "repository": "GlacierEQ/high",
        "source_head": "abc123",
        "criticisms": [
            {
                "attack": "The mechanism duplicates a standard library.",
                "evidence_refs": ["fixture:comparison"],
                "disposition": "INVALIDATED_CANDIDATE",
                "resolution": "Candidate rejected before promotion.",
            }
        ],
        "remaining_limitations": [],
        "decision": "INVALIDATED",
    }
    decision = adversarial_gate(review)
    assert not decision.survives
    assert set(decision.blockers) == {"review_decision", "candidate_invalidated"}


def test_estate_queue_binds_to_trusted_compiler_hash() -> None:
    bundle = estate_bundle()
    expected_hash = str(bundle["content_hash"])
    assert validate_estate_bundle_integrity(bundle, expected_hash) == expected_hash
    queue = compile_estate_target_queue(
        bundle,
        [assessment("GlacierEQ/high", "sys-high", 0.9)],
        expected_hash,
    )
    validate_payload(queue, "target-queue")
    assert queue["targets"][0]["rank"] == 1
    assert queue["estate_bundle_hash"] == expected_hash
    assert queue["estate_source_digest"] == "source-fixture"


def test_estate_queue_rejects_tamper_wrong_hash_and_nonreference_target() -> None:
    bundle = estate_bundle()
    expected_hash = str(bundle["content_hash"])
    with pytest.raises(InnovationContractError, match="trusted expected estate hash"):
        compile_estate_target_queue(
            bundle,
            [assessment("GlacierEQ/high", "sys-high", 0.9)],
            "wrong-hash",
        )

    tampered = dict(bundle)
    tampered_registry = dict(tampered["system_registry"])
    tampered_registry["systems"] = []
    tampered["system_registry"] = tampered_registry
    with pytest.raises(InnovationContractError, match="content_hash mismatch"):
        compile_estate_target_queue(
            tampered,
            [assessment("GlacierEQ/high", "sys-high", 0.9)],
            expected_hash,
        )

    with pytest.raises(InnovationContractError, match="existing reference estate system"):
        compile_estate_target_queue(
            bundle,
            [assessment("GlacierEQ/fake", "sys-fake", 1.0)],
            expected_hash,
        )


def test_engineering_run_supports_progressive_state_before_final_ledger() -> None:
    run = {
        "schema": "glaciereq.engineering-run.v1",
        "run_id": "fixture-run",
        "repository": "GlacierEQ/high",
        "expected_head": "abc123",
        "observed_head": "abc123",
        "state": "DISCOVERED",
        "history": [],
        "census_ref": "fixture:census",
    }
    validate_payload(run, "engineering-run")
    updated = transition_run(run, "CENSUSED", ["fixture:census"])
    validate_payload(updated, "engineering-run")


def test_engine_cannot_assign_operator_only_statuses_even_with_approval_record() -> None:
    run = {
        "state": "PROMOTION_READY",
        "history": [],
        "repository": "GlacierEQ/high",
        "expected_head": "abc123",
        "observed_head": "abc123",
        "promotion_id": "promotion-1",
        "promotion_record": promotion_record("abc123"),
        "source_commit": "candidate123",
        "operator_authorization": operator_authorization("SOURCE_BOUND"),
    }

    for target in ("SOURCE_BOUND", "SUPERSEDED", "ARCHIVED"):
        with pytest.raises(InnovationContractError, match="operator-only status"):
            transition_run(run, target, ["operator-decision-required"])


def test_operator_only_persisted_state_requires_bound_operator_authorization() -> None:
    run = {
        "schema": "glaciereq.engineering-run.v1",
        "run_id": "operator-state-fixture",
        "repository": "GlacierEQ/high",
        "expected_head": "abc123",
        "observed_head": "abc123",
        "state": "SOURCE_BOUND",
        "history": [],
    }
    with pytest.raises(InnovationContractError, match="operator_authorization"):
        validate_payload(run, "engineering-run")

    run["operator_authorization"] = operator_authorization("SOURCE_BOUND")
    validate_payload(run, "engineering-run")
    monitored = transition_run(run, "MONITORED", ["operator:authorization"])
    assert monitored["state"] == "MONITORED"

    run["operator_authorization"]["observed_head"] = "def456"
    with pytest.raises(InnovationContractError, match="observed_head does not match"):
        validate_payload(run, "engineering-run")

    run["observed_head"] = "def456"
    with pytest.raises(InnovationContractError, match="stale repository state"):
        validate_payload(run, "engineering-run")


def test_injected_policy_cannot_make_operator_only_status_reachable(tmp_path: Path) -> None:
    policy = load_policy()
    policy["states"]["PROMOTION_READY"].append("SOURCE_BOUND")
    policy_path = tmp_path / "injected-policy.json"
    policy_path.write_text(json.dumps(policy), encoding="utf-8")

    with pytest.raises(InnovationContractError, match="cannot expose engine transitions"):
        load_policy(policy_path)
    with pytest.raises(InnovationContractError, match="cannot expose engine transitions"):
        transition_allowed("PROMOTION_READY", "SOURCE_BOUND", policy)


def test_engineering_ledger_requires_all_truth_surfaces() -> None:
    run = {
        "system": "fixture",
        "bottleneck": "fixture bottleneck",
        "root_cause": "fixture cause",
        "invention": "fixture mechanism",
        "implementation": ["src/fixture.py"],
        "verification": ["tests/test_fixture.py"],
        "measured_results": [],
        "enterprise_consequence": "fixture consequence",
        "failure_boundaries": [],
        "evidence": [],
        "next_constraint": "fixture next",
    }
    ledger = compile_engineering_ledger(run)
    assert ledger["system"] == "fixture"
    with pytest.raises(InnovationContractError, match="missing fields"):
        compile_engineering_ledger({"system": "fixture"})
