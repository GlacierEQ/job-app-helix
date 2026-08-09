from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from job_app_helix.repository_surface import (
    RepositorySurfaceError,
    apply_surface_decisions,
    compile_governed_surface_report,
    compile_surface_report,
)

OBSERVATIONS = Path(
    "manifests/public_repository_surface_observations_2026-08-08.json"
)
DECISIONS = Path("manifests/public_repository_surface_decisions_2026-08-08.json")


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_governed_overlay_resolves_all_58_historical_unknowns() -> None:
    report = compile_governed_surface_report(
        load(OBSERVATIONS), load(DECISIONS), expected_public_count=75
    )
    overlay = report["governed_overlay"]
    assert overlay["decision_count"] == 58
    assert overlay["historical_unassessed_resolved"] == 58
    assert overlay["unassessed_remaining_after_decisions"] == 0
    assert overlay["decision_counts"] == {
        "ADMIT": 2,
        "QUARANTINED": 3,
        "REFERENCE": 1,
        "REPAIR_REQUIRED": 52,
    }
    assert report["base_report_id"]
    assert report["base_report_id"] != report["report_id"]


def test_overlay_preserves_historical_base_state_per_repository() -> None:
    report = compile_governed_surface_report(
        load(OBSERVATIONS), load(DECISIONS), expected_public_count=75
    )
    by_repo = {item["repository"]: item for item in report["repositories"]}

    coordinator = by_repo["GlacierEQ/anthropic-agent-coordinator"]
    assert coordinator["base_assessment_state"] == "UNASSESSED"
    assert coordinator["base_admission"] == "REPAIR_REQUIRED"
    assert coordinator["admission"] == "ADMIT"
    assert coordinator["assessment_state"] == "COMPLETE"
    assert coordinator["decision_evidence"]["canonical_head"] == (
        "ac977563cfd59deb8e87177f53082184f6468aa8"
    )

    legal = by_repo["GlacierEQ/legal-powerhouse"]
    assert legal["base_assessment_state"] == "UNASSESSED"
    assert legal["admission"] == "QUARANTINED"
    assert legal["repair_priority"] == "P0"

    template = by_repo["GlacierEQ/Template"]
    assert template["admission"] == "REFERENCE"
    assert template["repair_priority"] is None


def test_historical_report_remains_reproducible_without_overlay() -> None:
    historical = compile_surface_report(load(OBSERVATIONS), expected_public_count=75)
    assert historical["summary"]["assessment"]["UNASSESSED"] == 58
    assert "governed_overlay" not in historical
    assert all("base_admission" not in item for item in historical["repositories"])


def test_admit_decision_requires_an_exact_hex_sha() -> None:
    historical = compile_surface_report(load(OBSERVATIONS), expected_public_count=75)
    decisions = deepcopy(load(DECISIONS))
    item = next(value for value in decisions["items"] if value["decision"] == "ADMIT")
    item["evidence"]["canonical_head"] = "z" * 40
    with pytest.raises(RepositorySurfaceError, match="exact canonical_head"):
        apply_surface_decisions(historical, decisions)


def test_decision_outside_public_census_fails_closed() -> None:
    historical = compile_surface_report(load(OBSERVATIONS), expected_public_count=75)
    decisions = deepcopy(load(DECISIONS))
    decisions["items"][0]["repository"] = "GlacierEQ/not-in-public-census"
    with pytest.raises(RepositorySurfaceError, match="outside surface report"):
        apply_surface_decisions(historical, decisions)


def test_truncated_overlay_cannot_leave_historical_unknown_unresolved() -> None:
    historical = compile_surface_report(load(OBSERVATIONS), expected_public_count=75)
    decisions = deepcopy(load(DECISIONS))
    decisions["items"].pop()
    with pytest.raises(RepositorySurfaceError, match="exactly cover historical UNASSESSED"):
        apply_surface_decisions(historical, decisions)


def test_admit_cannot_override_private_or_quarantined_base_state() -> None:
    historical = compile_surface_report(load(OBSERVATIONS), expected_public_count=75)
    decisions = deepcopy(load(DECISIONS))
    admitted_repository = next(
        item["repository"] for item in decisions["items"] if item["decision"] == "ADMIT"
    )
    base_record = next(
        item for item in historical["repositories"] if item["repository"] == admitted_repository
    )
    base_record["public"] = False
    base_record["admission"] = "QUARANTINED"
    base_record["lineage_state"] = "QUARANTINED"
    base_record["findings"] = sorted(set(base_record["findings"] + ["PRIVACY_RISK"]))

    with pytest.raises(RepositorySurfaceError, match="conflicts with base blockers"):
        apply_surface_decisions(historical, decisions)
