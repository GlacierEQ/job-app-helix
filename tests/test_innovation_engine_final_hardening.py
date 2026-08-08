from __future__ import annotations

from job_app_helix.innovation_engine import promotion_gate, transition_run


def test_artifact_presence_rejects_scalar_integer() -> None:
    run = {"state": "DISCOVERED", "history": [], "census_ref": 1}
    try:
        transition_run(run, "CENSUSED", ["fixture:census"])
    except ValueError as exc:
        assert "missing required artifacts" in str(exc)
    else:
        raise AssertionError("integer artifact unexpectedly satisfied transition requirement")


def test_artifact_presence_accepts_object_promotion_record() -> None:
    record = {
        "schema": "glaciereq.promotion.v1",
        "repository": "GlacierEQ/high",
        "source_head": "abc123",
        "expected_head": "abc123",
        "observed_head": "abc123",
        "baseline_preserved": True,
        "central_mechanism_implemented": True,
        "existing_tests_pass": True,
        "new_behavior_tested": True,
        "failure_path_tested": True,
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
        "decision": "PROMOTION_READY",
        "evidence_refs": ["verification:fixture"],
    }
    run = {
        "state": "ADVERSARIALLY_REVIEWED",
        "history": [],
        "repository": "GlacierEQ/high",
        "expected_head": "abc123",
        "observed_head": "abc123",
        "promotion_id": "promotion-1",
        "promotion_record": record,
    }
    assert transition_run(run, "PROMOTION_READY", ["promotion:fixture"])["state"] == (
        "PROMOTION_READY"
    )


def test_required_benchmark_rejects_empty_measurement_object() -> None:
    record = {
        "expected_head": "abc123",
        "observed_head": "abc123",
        "source_head": "abc123",
        "baseline_preserved": True,
        "central_mechanism_implemented": True,
        "existing_tests_pass": True,
        "new_behavior_tested": True,
        "failure_path_tested": True,
        "regression_risk_assessed": True,
        "claims_match_evidence": True,
        "architecture_documented": True,
        "limitations_documented": True,
        "decision": "PROMOTION_READY",
        "benchmark": {
            "required": True,
            "measured": True,
            "results": [{}],
            "reason": "Performance claim introduced.",
        },
    }
    decision = promotion_gate(record)
    assert not decision.ready
    assert "benchmark_results" in decision.failures
