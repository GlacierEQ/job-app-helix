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
)
WAVE10 = ROOT / "manifests/public_repository_surface_reconciliation_wave10_2026-08-10.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def report_through_wave9() -> dict:
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


def test_wave10_admits_exact_head_mission_control_surface() -> None:
    before = report_through_wave9()
    after = apply_surface_reconciliation(before, load(WAVE10))
    assert subset_counts(before) == {
        "ADMIT": 14,
        "QUARANTINED": 3,
        "REFERENCE": 1,
        "REPAIR_REQUIRED": 40,
    }
    assert subset_counts(after) == {
        "ADMIT": 15,
        "QUARANTINED": 3,
        "REFERENCE": 1,
        "REPAIR_REQUIRED": 39,
    }


def test_mission_control_admission_is_scope_and_receipt_bound() -> None:
    report = apply_surface_reconciliation(report_through_wave9(), load(WAVE10))
    record = next(
        item
        for item in report["repositories"]
        if item["repository"] == "GlacierEQ/spacex-mission-control"
    )
    head = "18f46561b6ff1eb00fb3b5c228f88996c9b13590"
    evidence = record["decision_evidence"]
    assert record["prior_reconciled_admission"] == "REPAIR_REQUIRED"
    assert record["admission"] == "ADMIT"
    assert record["repair_priority"] is None
    assert record["decision_excellence_state"] == "SYNTHETIC_MISSION_OPERATIONS_VERIFIED"
    assert "SURFACE_ASSESSMENT_UNASSESSED" not in record["findings"]
    assert evidence["canonical_head"] == head
    assert evidence["evidence_token"] == (
        "LOCAL_MISSION_OPS_SIMULATION_NOT_FLIGHT_COMMAND_AUTHORITY"
    )
    receipts = evidence["proof_receipts"]
    assert {receipt["id"] for receipt in receipts} == {31463234798, 31463235182}
    assert all(receipt["head_sha"] == head for receipt in receipts)
    assert all(receipt["conclusion"] == "success" for receipt in receipts)
    assert "does not assert SpaceX affiliation" in evidence["metadata_readback"]["assessment"]


def test_wave10_admission_fails_closed_on_receipt_drift() -> None:
    predecessor = report_through_wave9()
    mismatch = deepcopy(load(WAVE10))
    mismatch["items"][0]["evidence"]["proof_receipts"][0]["head_sha"] = "0" * 40
    with pytest.raises(RepositorySurfaceError, match="proof/head drift"):
        apply_surface_reconciliation(predecessor, mismatch)
