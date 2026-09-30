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
    ROOT / "manifests/public_repository_surface_reconciliation_wave14_2026-08-11.json",
)
WAVE15 = ROOT / "manifests/public_repository_surface_reconciliation_wave15_2026-08-11.json"
RECEIPT = ROOT / "status/public-repository-surface-repair-wave15-2026-08-11.json"
THERMAL_BLOCKER = ROOT / (
    "status/public-repository-surface-repair-blocker-spacex-thermal-protection-2026-08-11.json"
)
HEAD = "156629c65bdeff5397c1370b3e098eec26aa9377"
RUN_ID = 31549408943
TARGET = "GlacierEQ/spacex-autonomy"
TOKEN = "LOCAL_AUTONOMY_SIMULATION_NOT_FLIGHT_CONTROL_AUTHORITY"
CAPABILITY = "deterministic-local-python-go-autonomy-simulation"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def report_through_wave14() -> dict:
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


def test_wave15_admits_only_exact_head_autonomy_surface() -> None:
    before = report_through_wave14()
    after = apply_surface_reconciliation(before, load(WAVE15))
    assert subset_counts(before) == {
        "ADMIT": 19,
        "QUARANTINED": 3,
        "REFERENCE": 1,
        "REPAIR_REQUIRED": 35,
    }
    assert subset_counts(after) == {
        "ADMIT": 20,
        "QUARANTINED": 3,
        "REFERENCE": 1,
        "REPAIR_REQUIRED": 34,
    }
    before_by_repo = {item["repository"]: item for item in before["repositories"]}
    after_by_repo = {item["repository"]: item for item in after["repositories"]}
    assert before_by_repo[TARGET]["admission"] == "REPAIR_REQUIRED"
    assert after_by_repo[TARGET]["admission"] == "ADMIT"
    for repository in before_by_repo:
        if repository != TARGET:
            assert before_by_repo[repository] == after_by_repo[repository]


def test_autonomy_admission_binds_exact_native_receipts() -> None:
    report = apply_surface_reconciliation(report_through_wave14(), load(WAVE15))
    record = next(item for item in report["repositories"] if item["repository"] == TARGET)
    evidence = record["decision_evidence"]
    assert record["prior_reconciled_admission"] == "REPAIR_REQUIRED"
    assert record["admission"] == "ADMIT"
    assert record["repair_priority"] is None
    assert record["decision_excellence_state"] == (
        "LOCAL_AUTONOMY_SIMULATION_NATIVE_PROOF_VERIFIED"
    )
    assert evidence["source_head"] == HEAD
    assert evidence["evidence_token"] == TOKEN
    assert evidence["verified_capability"] == CAPABILITY
    workflow = evidence["proof_receipts"]
    assert workflow == [
        {
            "kind": "workflow_run",
            "id": RUN_ID,
            "name": "Autonomy Simulation Verification",
            "head_sha": HEAD,
            "conclusion": "success",
        }
    ]
    python_receipts = evidence["native_receipts"]["python"]
    assert {item["version"] for item in python_receipts} == {"3.11", "3.12", "3.13"}
    assert all(item["executed"] == 70 for item in python_receipts)
    assert all(item["failures"] == 0 for item in python_receipts)
    assert all(item["conclusion"] == "VERIFIED" for item in python_receipts)
    go = evidence["native_receipts"]["go"]
    assert go["executed"] == go["passed"] == 7
    assert go["failed"] == 0
    assert go["race_enabled"] is True
    assert go["conclusion"] == "VERIFIED"
    assert "does not establish SpaceX affiliation" in evidence["proof_scope"]
    assert "race_enabled=true" in evidence["proof_scope"]


def test_wave15_receipt_matches_reconciliation_authority() -> None:
    wave = load(WAVE15)["items"][0]
    receipt = load(RECEIPT)
    assert receipt["repository"] == wave["repository"] == TARGET
    assert receipt["source_head"] == wave["evidence"]["source_head"] == HEAD
    assert receipt["evidence_token"] == wave["evidence"]["evidence_token"] == TOKEN
    assert receipt["verified_capability"] == wave["evidence"]["verified_capability"] == CAPABILITY
    assert receipt["proof_receipts"][0]["id"] == RUN_ID
    assert receipt["native_receipts"]["go"]["race_enabled"] is True
    assert receipt["surface_decision"] == "ADMIT"
    assert receipt["governed_subset_delta"] == {"ADMIT": 1, "REPAIR_REQUIRED": -1}


def test_thermal_source_gain_is_preserved_without_false_admission() -> None:
    blocker = load(THERMAL_BLOCKER)
    assert blocker["repository"] == "GlacierEQ/spacex-thermal-protection"
    assert blocker["source_head"] == "f35cef2d9c115218766ac3ef8d023f8316ac02f0"
    assert blocker["surface_decision"] == "REPAIR_REQUIRED"
    assert blocker["blocker"] == "GITHUB_ABOUT_DESCRIPTION_CONTRADICTS_CLAIM_CEILING"
    assert blocker["connector_capability"]["repository_description_mutation"] == (
        "UNAVAILABLE_AT_LATEST_DISCOVERY"
    )
    assert blocker["connector_capability"]["no_false_remediation_claim"] is True
    assert {item["id"] for item in blocker["source_proof"]} == {
        31548120212,
        31548120213,
    }


def test_wave15_admission_fails_closed_on_receipt_drift() -> None:
    mismatch = deepcopy(load(WAVE15))
    mismatch["items"][0]["evidence"]["proof_receipts"][0]["head_sha"] = "0" * 40
    with pytest.raises(RepositorySurfaceError, match="proof/head drift"):
        apply_surface_reconciliation(report_through_wave14(), mismatch)


def test_wave15_reapplication_fails_closed_on_prior_decision_drift() -> None:
    once = apply_surface_reconciliation(report_through_wave14(), load(WAVE15))
    with pytest.raises(RepositorySurfaceError, match="prior decision drift"):
        apply_surface_reconciliation(once, load(WAVE15))
