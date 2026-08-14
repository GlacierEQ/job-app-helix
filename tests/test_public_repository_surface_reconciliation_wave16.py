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
LAYER_NAMES = (
    "public_repository_surface_reconciliation_2026-08-09.json",
    "public_repository_surface_reconciliation_wave3_2026-08-09.json",
    "public_repository_surface_reconciliation_wave4_2026-08-09.json",
    "public_repository_surface_reconciliation_wave5_2026-08-09.json",
    "public_repository_surface_reconciliation_wave6_2026-08-09.json",
    "public_repository_surface_reconciliation_wave7_2026-08-10.json",
    "public_repository_surface_reconciliation_wave8_2026-08-10.json",
    "public_repository_surface_reconciliation_wave9_2026-08-10.json",
    "public_repository_surface_reconciliation_wave10_2026-08-10.json",
    "public_repository_surface_reconciliation_wave11_2026-08-11.json",
    "public_repository_surface_reconciliation_wave12_2026-08-11.json",
    "public_repository_surface_reconciliation_wave13_2026-08-11.json",
    "public_repository_surface_reconciliation_wave14_2026-08-11.json",
    "public_repository_surface_reconciliation_wave15_2026-08-11.json",
)
LAYERS = tuple(ROOT / "manifests" / name for name in LAYER_NAMES)
WAVE16 = ROOT / (
    "manifests/public_repository_surface_reconciliation_wave16_2026-08-13.json"
)
RECEIPT = ROOT / "status/public-repository-surface-repair-wave16-2026-08-13.json"
HEAD = "489cff52ed1da8c5e7da0769807bad8b58ef394f"
RUN_ID = 31641804512
TARGET = "GlacierEQ/spacex-satellite-mesh"
TOKEN = "LOCAL_MESH_SIMULATION_NOT_SPACECRAFT_OR_LASER_TERMINAL_AUTHORITY"
CAPABILITY = "deterministic-local-static-and-temporal-satellite-mesh-routing"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def report_through_wave15() -> dict:
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
            admission = item["admission"]
            counts[admission] = counts.get(admission, 0) + 1
    return counts


def test_wave16_admits_only_exact_head_satellite_mesh() -> None:
    before = report_through_wave15()
    after = apply_surface_reconciliation(before, load(WAVE16))
    assert subset_counts(before) == {
        "ADMIT": 20,
        "QUARANTINED": 3,
        "REFERENCE": 1,
        "REPAIR_REQUIRED": 34,
    }
    assert subset_counts(after) == {
        "ADMIT": 21,
        "QUARANTINED": 3,
        "REFERENCE": 1,
        "REPAIR_REQUIRED": 33,
    }
    before_by_repo = {item["repository"]: item for item in before["repositories"]}
    after_by_repo = {item["repository"]: item for item in after["repositories"]}
    assert before_by_repo[TARGET]["admission"] == "REPAIR_REQUIRED"
    assert after_by_repo[TARGET]["admission"] == "ADMIT"
    for repository in before_by_repo:
        if repository != TARGET:
            assert before_by_repo[repository] == after_by_repo[repository]


def test_satellite_mesh_admission_binds_native_proof() -> None:
    report = apply_surface_reconciliation(report_through_wave15(), load(WAVE16))
    record = next(
        item for item in report["repositories"] if item["repository"] == TARGET
    )
    evidence = record["decision_evidence"]
    assert record["prior_reconciled_admission"] == "REPAIR_REQUIRED"
    assert record["admission"] == "ADMIT"
    assert record["repair_priority"] is None
    assert evidence["canonical_head"] == HEAD
    assert evidence["evidence_token"] == TOKEN
    assert evidence["verified_capability"] == CAPABILITY
    assert evidence["proof_receipts"] == [
        {
            "kind": "workflow_run",
            "id": RUN_ID,
            "name": "Native functional verification",
            "head_sha": HEAD,
            "conclusion": "success",
        }
    ]
    native = evidence["native_receipts"]
    assert native["python"]["versions"] == ["3.11", "3.12", "3.13"]
    assert native["python"]["pytest"] == "PASS"
    assert native["rust"]["cargo_check_all_targets"] == "PASS"
    assert native["rust"]["cargo_test"] == "PASS"
    assert native["aggregate_required_functional_proof"] == "PASS"
    assert native["authority"]["github_token_contents"] == "read"
    assert native["authority"]["checkout_persist_credentials"] is False


def test_wave16_receipt_matches_reconciliation_authority() -> None:
    wave = load(WAVE16)["items"][0]
    receipt = load(RECEIPT)
    assert receipt["repository"] == wave["repository"] == TARGET
    assert receipt["source_canonical_head"] == HEAD
    assert wave["evidence"]["canonical_head"] == HEAD
    assert receipt["evidence_token"] == wave["evidence"]["evidence_token"] == TOKEN
    assert receipt["verified_capability"] == CAPABILITY
    assert wave["evidence"]["verified_capability"] == CAPABILITY
    assert receipt["proof_receipts"][0]["id"] == RUN_ID
    assert receipt["surface_decision"] == "ADMIT"
    assert receipt["governed_subset_delta"] == {
        "ADMIT": 1,
        "REPAIR_REQUIRED": -1,
    }


def test_wave16_admission_fails_closed_on_receipt_drift() -> None:
    mismatch = deepcopy(load(WAVE16))
    mismatch["items"][0]["evidence"]["proof_receipts"][0]["head_sha"] = "0" * 40
    with pytest.raises(RepositorySurfaceError, match="proof/head drift"):
        apply_surface_reconciliation(report_through_wave15(), mismatch)


def test_wave16_reapplication_fails_closed_on_prior_decision_drift() -> None:
    once = apply_surface_reconciliation(report_through_wave15(), load(WAVE16))
    with pytest.raises(RepositorySurfaceError, match="prior decision drift"):
        apply_surface_reconciliation(once, load(WAVE16))
