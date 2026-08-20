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
)
WAVE12 = ROOT / "manifests/public_repository_surface_reconciliation_wave12_2026-08-11.json"
RECEIPT = ROOT / "status/public-repository-surface-repair-wave12-2026-08-11.json"
HEAD = "b99a1f7ea0534d3a268f9bea432399c9862bd1e4"
RUN_IDS = {31534343810, 31534343822}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def report_through_wave11() -> dict:
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


def test_wave12_admits_exact_head_orbital_math_surface() -> None:
    before = report_through_wave11()
    after = apply_surface_reconciliation(before, load(WAVE12))
    assert subset_counts(before) == {
        "ADMIT": 16,
        "QUARANTINED": 3,
        "REFERENCE": 1,
        "REPAIR_REQUIRED": 38,
    }
    assert subset_counts(after) == {
        "ADMIT": 17,
        "QUARANTINED": 3,
        "REFERENCE": 1,
        "REPAIR_REQUIRED": 37,
    }


def test_orbital_admission_is_scope_and_receipt_bound() -> None:
    report = apply_surface_reconciliation(report_through_wave11(), load(WAVE12))
    record = next(
        item
        for item in report["repositories"]
        if item["repository"] == "GlacierEQ/spacex-orbital-mechanics"
    )
    evidence = record["decision_evidence"]
    assert record["prior_reconciled_admission"] == "REPAIR_REQUIRED"
    assert record["admission"] == "ADMIT"
    assert record["repair_priority"] is None
    assert record["decision_excellence_state"] == "LOCAL_ORBITAL_MATH_VERIFIED"
    assert "SURFACE_ASSESSMENT_UNASSESSED" not in record["findings"]
    assert evidence["source_head"] == HEAD
    assert evidence["evidence_token"] == (
        "LOCAL_ORBITAL_MATH_NOT_FLIGHT_DYNAMICS_AUTHORITY"
    )
    assert evidence["verified_capability"] == (
        "deterministic-local-orbital-mechanics-calculation"
    )
    receipts = evidence["proof_receipts"]
    assert {receipt["id"] for receipt in receipts} == RUN_IDS
    assert all(receipt["head_sha"] == HEAD for receipt in receipts)
    assert all(receipt["conclusion"] == "success" for receipt in receipts)
    scope = evidence["proof_scope"]
    assert "historical C++ Lambert filename" in scope
    assert "do not establish Lambert" in scope
    assert "controlling SpaceX non-affiliation" in evidence["metadata_readback"]["assessment"]


def test_wave12_receipt_matches_reconciliation_authority() -> None:
    wave = load(WAVE12)["items"][0]
    receipt = load(RECEIPT)
    assert receipt["repository"] == wave["repository"]
    assert receipt["source_head"] == wave["evidence"]["source_head"] == HEAD
    assert receipt["evidence_token"] == wave["evidence"]["evidence_token"]
    assert receipt["verified_capability"] == wave["evidence"]["verified_capability"]
    assert {item["id"] for item in receipt["proof_receipts"]} == RUN_IDS
    assert all(item["head_sha"] == HEAD for item in receipt["proof_receipts"])
    assert all(item["conclusion"] == "success" for item in receipt["proof_receipts"])


def test_wave12_admission_fails_closed_on_receipt_drift() -> None:
    predecessor = report_through_wave11()
    mismatch = deepcopy(load(WAVE12))
    mismatch["items"][0]["evidence"]["proof_receipts"][0]["head_sha"] = "0" * 40
    with pytest.raises(RepositorySurfaceError, match="proof/head drift"):
        apply_surface_reconciliation(predecessor, mismatch)
