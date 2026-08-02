from __future__ import annotations

import json
from pathlib import Path

from job_app_helix.live_evidence_adapter import compile_repository_observation

ROOT = Path(__file__).resolve().parents[1]
OBSERVATION_PATH = ROOT / "observations" / "repositories" / (
    "GlacierEQ__AKOS__1607c0d27897ea963eb572062300342f1922b84c.json"
)
ASSESSMENT_PATH = ROOT / "status" / "repository-assessments" / (
    "GlacierEQ__AKOS__1607c0d27897ea963eb572062300342f1922b84c.json"
)
REGISTRY_PATH = ROOT / "manifests" / "live_repository_evidence.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_persisted_assessment_matches_live_compilation() -> None:
    compiled = compile_repository_observation(load(OBSERVATION_PATH))
    persisted = load(ASSESSMENT_PATH)

    assert persisted == compiled


def test_registry_matches_persisted_assessment() -> None:
    persisted = load(ASSESSMENT_PATH)
    registry = load(REGISTRY_PATH)
    entry = registry["repositories"][0]
    assessment = persisted["assessment"]

    assert entry["repository"] == persisted["repository"]
    assert entry["observed_head_sha"] == persisted["observed_head_sha"]
    assert entry["observation_id"] == persisted["observation_id"]
    assert entry["assessment_id"] == assessment["assessment_id"]
    assert entry["state"] == assessment["health_state"]
    assert entry["health_score"] == assessment["health_score"]
    assert entry["evidence_coverage"] == assessment["evidence_coverage"]
    assert entry["confidence_score"] == assessment["confidence_score"]
    assert entry["connector_quality_score"] == assessment["quality_context"][
        "connector_quality_score"
    ]
    assert entry["data_quality_score"] == assessment["quality_context"][
        "data_quality_score"
    ]
    assert entry["blockers"] == assessment["blockers"]
