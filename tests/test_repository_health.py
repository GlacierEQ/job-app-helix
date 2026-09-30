from __future__ import annotations

from copy import deepcopy

import pytest

from job_app_helix.repository_health import (
    RepositoryHealthError,
    assess_repository_health,
    load_policy,
)

HEAD = "a" * 40
OLD_HEAD = "b" * 40


def verified_payload(raw_score: int = 96) -> dict:
    policy = load_policy()
    dimensions = {
        name: {
            "state": "VERIFIED",
            "raw_score": raw_score,
            "confidence": 1.0,
            "verified_sha": HEAD,
            "receipts": [f"receipts/{name}/{HEAD}.json"],
            "findings": [],
            "blockers": [],
        }
        for name in policy["dimensions"]
    }
    return {
        "repository": "GlacierEQ/example-repository",
        "observed_head_sha": HEAD,
        "observed_at": "2026-08-01T19:38:00-10:00",
        "dimensions": dimensions,
        "quality_context": {
            "connector_quality_score": 95,
            "data_quality_score": 96,
        },
        "blockers": [],
    }


def test_policy_weights_total_one_hundred() -> None:
    policy = load_policy()
    assert sum(item["weight"] for item in policy["dimensions"].values()) == 100


def test_fully_current_receipted_evidence_can_reach_elite() -> None:
    assessment = assess_repository_health(verified_payload())
    assert assessment["health_state"] == "ELITE_VERIFIED"
    assert assessment["health_score"] == 96
    assert assessment["evidence_coverage"] == 100
    assert assessment["elite_eligible"] is True
    assert assessment["critical_not_verified"] == []


def test_unknown_evidence_scores_zero() -> None:
    payload = verified_payload()
    payload["dimensions"]["tests"] = {
        "state": "UNVERIFIED",
        "raw_score": 100,
        "confidence": 1.0,
        "receipts": [],
    }
    assessment = assess_repository_health(payload)
    assert assessment["dimensions"]["tests"]["points"] == 0
    assert assessment["health_state"] != "ELITE_VERIFIED"
    assert "tests" in assessment["critical_not_verified"]


def test_verified_without_receipt_is_downgraded() -> None:
    payload = verified_payload()
    payload["dimensions"]["build"]["receipts"] = []
    assessment = assess_repository_health(payload)
    build = assessment["dimensions"]["build"]
    assert build["requested_state"] == "VERIFIED"
    assert build["state"] == "UNVERIFIED"
    assert build["points"] == 0
    assert "verified state lacked a receipt" in build["normalization_reasons"]


def test_sha_drift_marks_evidence_stale_and_caps_credit() -> None:
    payload = verified_payload()
    payload["dimensions"]["tests"]["verified_sha"] = OLD_HEAD
    assessment = assess_repository_health(payload)
    tests = assessment["dimensions"]["tests"]
    assert tests["state"] == "STALE"
    assert tests["points"] == pytest.approx(7.68)
    assert assessment["health_state"] == "STALE"
    assert f"reverify tests against {HEAD}" in assessment["next_actions"]


def test_connector_and_data_quality_do_not_inflate_health_score() -> None:
    high_quality = verified_payload()
    low_quality = deepcopy(high_quality)
    low_quality["quality_context"] = {
        "connector_quality_score": 20,
        "data_quality_score": 20,
    }
    high = assess_repository_health(high_quality)
    low = assess_repository_health(low_quality)
    assert high["health_score"] == low["health_score"]
    assert high["elite_eligible"] is True
    assert low["elite_eligible"] is False


def test_critical_failure_blocks_promotion() -> None:
    payload = verified_payload()
    payload["dimensions"]["security"].update(
        {
            "state": "FAILED",
            "raw_score": 100,
            "blockers": ["secret scan failed"],
        }
    )
    assessment = assess_repository_health(payload)
    assert assessment["health_state"] == "FAILED"
    assert assessment["dimensions"]["security"]["points"] == 0
    assert "secret scan failed" in assessment["blockers"]


def test_assessment_is_deterministic() -> None:
    payload = verified_payload()
    first = assess_repository_health(payload)
    second = assess_repository_health(payload)
    assert first == second
    assert len(first["assessment_id"]) == 64


def test_unknown_dimension_fails_closed() -> None:
    payload = verified_payload()
    payload["dimensions"]["marketing_magic"] = {
        "state": "VERIFIED",
        "raw_score": 100,
        "confidence": 1.0,
        "verified_sha": HEAD,
        "receipts": ["receipt.json"],
    }
    with pytest.raises(RepositoryHealthError, match="unknown health dimensions"):
        assess_repository_health(payload)
