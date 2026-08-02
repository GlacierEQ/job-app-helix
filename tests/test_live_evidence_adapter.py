from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from job_app_helix.live_evidence_adapter import (
    LiveEvidenceAdapterError,
    compile_repository_observation,
)

ROOT = Path(__file__).resolve().parents[1]
OBSERVATION = ROOT / "observations" / "repositories" / (
    "GlacierEQ__AKOS__1607c0d27897ea963eb572062300342f1922b84c.json"
)
HEAD = "1607c0d27897ea963eb572062300342f1922b84c"


def load_observation() -> dict:
    return json.loads(OBSERVATION.read_text(encoding="utf-8"))


def current_receipt(kind: str) -> str:
    return f"https://github.com/GlacierEQ/AKOS/actions/runs/999/{kind}?sha={HEAD}"


def test_akos_probe_is_truthfully_partial() -> None:
    result = compile_repository_observation(load_observation())
    assessment = result["assessment"]

    assert result["repository"] == "GlacierEQ/AKOS"
    assert result["observed_head_sha"] == HEAD
    assert assessment["health_state"] == "PARTIALLY_VERIFIED"
    assert assessment["elite_eligible"] is False
    assert assessment["dimensions"]["reality"]["state"] == "PARTIALLY_VERIFIED"
    assert assessment["dimensions"]["build"]["state"] == "UNVERIFIED"
    assert assessment["dimensions"]["tests"]["state"] == "UNVERIFIED"
    assert assessment["dimensions"]["documentation"]["state"] == "PARTIALLY_VERIFIED"
    assert assessment["dimensions"]["security"]["state"] == "UNVERIFIED"
    assert assessment["quality_context"]["connector_quality_score"] == 75
    assert assessment["quality_context"]["data_quality_score"] == 85
    assert assessment["health_score"] < 80
    assert len(assessment["blockers"]) == 2


def test_observation_is_deterministic() -> None:
    first = compile_repository_observation(load_observation())
    second = compile_repository_observation(load_observation())

    assert first["observation_id"] == second["observation_id"]
    assert first["assessment"]["assessment_id"] == second["assessment"]["assessment_id"]
    assert first["integrity"] == second["integrity"]


def test_copied_child_bytes_are_rejected() -> None:
    observation = load_observation()
    observation["provenance"]["original_bytes_copied"] = True

    with pytest.raises(LiveEvidenceAdapterError, match="copied repository bytes"):
        compile_repository_observation(observation)


def test_unbound_artifact_receipt_is_rejected() -> None:
    observation = load_observation()
    observation["artifacts"]["source_files"][0]["url"] = (
        "https://github.com/GlacierEQ/AKOS/blob/main/operational_cognition/engine.py"
    )

    with pytest.raises(LiveEvidenceAdapterError, match="bound to observed HEAD"):
        compile_repository_observation(observation)


def test_success_requires_provider_receipt() -> None:
    observation = load_observation()
    observation["execution"]["build"] = {
        "state": "SUCCESS",
        "receipts": [],
        "test_count": None,
        "notes": [],
    }

    result = compile_repository_observation(observation)

    assert result["assessment"]["dimensions"]["build"]["state"] == "UNVERIFIED"
    assert "without a provider receipt" in " ".join(
        result["assessment"]["dimensions"]["build"]["findings"]
    )


def test_test_success_requires_positive_executed_count() -> None:
    observation = load_observation()
    observation["execution"]["tests"] = {
        "state": "SUCCESS",
        "receipts": [current_receipt("tests")],
        "test_count": 0,
        "notes": [],
    }

    result = compile_repository_observation(observation)

    assert result["assessment"]["dimensions"]["tests"]["state"] == "UNVERIFIED"
    assert "positive executed-test count" in " ".join(
        result["assessment"]["dimensions"]["tests"]["findings"]
    )


def test_verified_runtime_still_does_not_create_an_elite_claim() -> None:
    observation = load_observation()
    observation["connector"]["error_state"] = "NONE"
    observation["blockers"] = []
    for name in ("build", "documentation", "security"):
        observation["execution"][name] = {
            "state": "SUCCESS",
            "receipts": [current_receipt(name)],
            "test_count": None,
            "notes": [],
        }
    observation["execution"]["tests"] = {
        "state": "SUCCESS",
        "receipts": [current_receipt("tests")],
        "test_count": 94,
        "notes": [],
    }

    result = compile_repository_observation(observation)
    assessment = result["assessment"]

    assert assessment["dimensions"]["reality"]["state"] == "VERIFIED"
    assert assessment["dimensions"]["build"]["state"] == "VERIFIED"
    assert assessment["dimensions"]["tests"]["state"] == "VERIFIED"
    assert assessment["dimensions"]["documentation"]["state"] == "VERIFIED"
    assert assessment["dimensions"]["security"]["state"] == "VERIFIED"
    assert assessment["quality_context"]["connector_quality_score"] == 100
    assert assessment["quality_context"]["data_quality_score"] == 100
    assert assessment["health_state"] == "RECRUITER_READY"
    assert assessment["elite_eligible"] is False
    assert "health score below elite threshold" in assessment["elite_gate_failures"]


def test_failed_execution_with_receipt_fails_closed() -> None:
    observation = load_observation()
    observation["execution"]["tests"] = {
        "state": "FAILURE",
        "receipts": [current_receipt("tests")],
        "test_count": 94,
        "notes": ["one or more tests failed"],
    }

    result = compile_repository_observation(observation)

    assert result["assessment"]["dimensions"]["tests"]["state"] == "FAILED"
    assert result["assessment"]["health_state"] == "FAILED"


def test_connector_quality_and_data_quality_are_independent() -> None:
    observation = load_observation()
    connector_degraded = deepcopy(observation)
    connector_degraded["connector"]["error_state"] = "BLOCKED"

    normal = compile_repository_observation(observation)["assessment"]["quality_context"]
    degraded = compile_repository_observation(connector_degraded)["assessment"][
        "quality_context"
    ]

    assert normal["data_quality_score"] == degraded["data_quality_score"]
    assert normal["connector_quality_score"] == 75
    assert degraded["connector_quality_score"] == 0
