from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from job_app_helix.repository_surface import (
    RepositorySurfaceError,
    compile_governed_surface_report,
)
from job_app_helix.surface_reconciliation import apply_surface_reconciliation

ROOT = Path(__file__).resolve().parents[1]
OBSERVATIONS = ROOT / "manifests/public_repository_surface_observations_2026-08-08.json"
DECISIONS = ROOT / "manifests/public_repository_surface_decisions_2026-08-08.json"
LAYERS = (
    ROOT / "manifests/public_repository_surface_reconciliation_2026-08-09.json",
    ROOT / "manifests/public_repository_surface_reconciliation_wave3_2026-08-09.json",
    ROOT / "manifests/public_repository_surface_reconciliation_wave4_2026-08-09.json",
    ROOT / "manifests/public_repository_surface_reconciliation_wave5_2026-08-09.json",
    ROOT / "manifests/public_repository_surface_reconciliation_wave6_2026-08-09.json",
    ROOT / "manifests/public_repository_surface_reconciliation_wave7_2026-08-10.json",
    ROOT / "manifests/public_repository_surface_reconciliation_wave8_2026-08-10.json",
    ROOT / "manifests/public_repository_surface_reconciliation_wave9_2026-08-10.json",
    ROOT / "manifests/public_repository_surface_reconciliation_wave10_2026-08-10.json",
    ROOT / "manifests/public_repository_surface_reconciliation_wave11_2026-08-11.json",
    ROOT / "manifests/public_repository_surface_reconciliation_wave12_2026-08-11.json",
    ROOT / "manifests/public_repository_surface_reconciliation_wave13_2026-08-11.json",
)
WAVE14 = ROOT / "manifests/public_repository_surface_reconciliation_wave14_2026-08-11.json"
RECEIPT = ROOT / "status/public-repository-surface-repair-wave14-2026-08-11.json"
HEAD = "1903e562e801a6153b0e78b9d236418c849f1867"
RUN_IDS = {31546261209, 31546261244}
TARGET = "GlacierEQ/spacex-propulsion-monitor"
TOKEN = "LOCAL_PROPULSION_HEALTH_SIMULATION_NOT_FLIGHT_ENGINE_AUTHORITY"
CAPABILITY = "deterministic-local-multi-sensor-health-evaluation"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def report_through_wave13() -> dict:
    report = compile_governed_surface_report(
        load(OBSERVATIONS), load(DECISIONS), expected_public_count=75
    )
    for layer in LAYERS:
        report = apply_surface_reconciliation(report, load(layer))
    return report


def subset_counts(report: dict) -> dict[str, int]:
    original = {item["repository"] for item in load(DECISIONS)["items"]}
    counts: dict[str, int] = {}
    for item in report["repositories"]:
        if item["repository"] in original:
            counts[item["admission"]] = counts.get(item["admission"], 0) + 1
    return counts


def test_wave14_admits_only_exact_head_propulsion_health_surface() -> None:
    before = report_through_wave13()
    after = apply_surface_reconciliation(before, load(WAVE14))
    assert subset_counts(before) == {
        "ADMIT": 18,
        "QUARANTINED": 3,
        "REFERENCE": 1,
        "REPAIR_REQUIRED": 36,
    }
    assert subset_counts(after) == {
        "ADMIT": 19,
        "QUARANTINED": 3,
        "REFERENCE": 1,
        "REPAIR_REQUIRED": 35,
    }

    before_by_repo = {item["repository"]: item for item in before["repositories"]}
    after_by_repo = {item["repository"]: item for item in after["repositories"]}
    assert set(before_by_repo) == set(after_by_repo)
    assert before_by_repo[TARGET]["admission"] == "REPAIR_REQUIRED"
    assert after_by_repo[TARGET]["admission"] == "ADMIT"
    for repository in before_by_repo:
        if repository != TARGET:
            assert before_by_repo[repository] == after_by_repo[repository]


def test_propulsion_admission_is_scope_and_receipt_bound() -> None:
    report = apply_surface_reconciliation(report_through_wave13(), load(WAVE14))
    record = next(
        item for item in report["repositories"] if item["repository"] == TARGET
    )
    evidence = record["decision_evidence"]
    assert record["prior_reconciled_admission"] == "REPAIR_REQUIRED"
    assert record["admission"] == "ADMIT"
    assert record["repair_priority"] is None
    assert record["decision_excellence_state"] == (
        "LOCAL_MULTI_SENSOR_HEALTH_SIMULATION_VERIFIED"
    )
    assert "SURFACE_ASSESSMENT_UNASSESSED" not in record["findings"]
    assert evidence["canonical_head"] == HEAD
    assert evidence["evidence_token"] == TOKEN
    assert evidence["verified_capability"] == CAPABILITY
    receipts = evidence["proof_receipts"]
    assert {receipt["id"] for receipt in receipts} == RUN_IDS
    assert all(receipt["head_sha"] == HEAD for receipt in receipts)
    assert all(receipt["conclusion"] == "success" for receipt in receipts)
    scope = evidence["proof_scope"]
    assert "per-unit health isolation and recovery" in scope
    assert "timestamp-aligned key-scoped cross-sensor correlation" in scope
    assert "does not establish SpaceX affiliation" in scope
    assert "flight-engine command authority" in scope
    assert "calibrated failure probability" in scope
    assert "controlling README" in evidence["metadata_readback"]["assessment"]


def test_wave14_receipt_matches_reconciliation_authority() -> None:
    wave = load(WAVE14)["items"][0]
    receipt = load(RECEIPT)
    assert receipt["repository"] == wave["repository"]
    assert receipt["source_canonical_head"] == wave["evidence"]["canonical_head"] == HEAD
    assert receipt["evidence_token"] == wave["evidence"]["evidence_token"] == TOKEN
    assert receipt["verified_capability"] == wave["evidence"]["verified_capability"] == CAPABILITY
    assert {item["id"] for item in receipt["proof_receipts"]} == RUN_IDS
    assert all(item["head_sha"] == HEAD for item in receipt["proof_receipts"])
    assert all(item["conclusion"] == "success" for item in receipt["proof_receipts"])
    assert receipt["surface_decision"] == "ADMIT"
    assert receipt["governed_subset_delta"] == {"ADMIT": 1, "REPAIR_REQUIRED": -1}


def test_wave14_admission_fails_closed_on_receipt_drift() -> None:
    predecessor = report_through_wave13()
    mismatch = deepcopy(load(WAVE14))
    mismatch["items"][0]["evidence"]["proof_receipts"][0]["head_sha"] = "0" * 40
    with pytest.raises(RepositorySurfaceError, match="proof/head drift"):
        apply_surface_reconciliation(predecessor, mismatch)


def test_wave14_reapplication_fails_closed_on_prior_decision_drift() -> None:
    once = apply_surface_reconciliation(report_through_wave13(), load(WAVE14))
    with pytest.raises(RepositorySurfaceError, match="prior decision drift"):
        apply_surface_reconciliation(once, load(WAVE14))
