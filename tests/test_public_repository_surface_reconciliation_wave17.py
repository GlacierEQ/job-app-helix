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
    "public_repository_surface_reconciliation_wave16_2026-08-13.json",
)
LAYERS = tuple(ROOT / "manifests" / name for name in LAYER_NAMES)
WAVE17 = ROOT / (
    "manifests/public_repository_surface_reconciliation_wave17_2026-08-13.json"
)
TARGETS = {
    "GlacierEQ/spacex-conjunction-sentinel": {
        "head": "17537ed7ee2c7b01edf60953f403ebcb3a6c2fd8",
        "run": 31639117944,
        "receipt": (
            "status/public-repository-surface-repair-wave17-conjunction-2026-08-13.json"
        ),
    },
    "GlacierEQ/spacex-cryogenics": {
        "head": "7b036b72c4a004fb0c21a18e08c7311aac8201e1",
        "run": 31639570712,
        "receipt": (
            "status/public-repository-surface-repair-wave17-cryogenics-2026-08-13.json"
        ),
    },
    "GlacierEQ/spacex-ground-network": {
        "head": "f8992a0ac0ab4608d10e7bb2e20444c9cbad54fd",
        "run": 31641017144,
        "receipt": (
            "status/public-repository-surface-repair-wave17-ground-network-2026-08-13.json"
        ),
    },
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def report_through_wave16() -> dict:
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


def test_wave17_admits_only_three_exact_native_proof_surfaces() -> None:
    before = report_through_wave16()
    after = apply_surface_reconciliation(before, load(WAVE17))
    assert subset_counts(before) == {
        "ADMIT": 21,
        "QUARANTINED": 3,
        "REFERENCE": 1,
        "REPAIR_REQUIRED": 33,
    }
    assert subset_counts(after) == {
        "ADMIT": 24,
        "QUARANTINED": 3,
        "REFERENCE": 1,
        "REPAIR_REQUIRED": 30,
    }
    before_by_repo = {item["repository"]: item for item in before["repositories"]}
    after_by_repo = {item["repository"]: item for item in after["repositories"]}
    assert set(before_by_repo) == set(after_by_repo)
    for repository in TARGETS:
        assert before_by_repo[repository]["admission"] == "REPAIR_REQUIRED"
        assert after_by_repo[repository]["admission"] == "ADMIT"
        assert after_by_repo[repository]["repair_priority"] is None
    for repository in before_by_repo:
        if repository not in TARGETS:
            assert before_by_repo[repository] == after_by_repo[repository]


def test_wave17_admissions_are_exact_head_and_native_receipt_bound() -> None:
    report = apply_surface_reconciliation(report_through_wave16(), load(WAVE17))
    by_repo = {item["repository"]: item for item in report["repositories"]}
    for repository, expected in TARGETS.items():
        record = by_repo[repository]
        evidence = record["decision_evidence"]
        assert record["prior_reconciled_admission"] == "REPAIR_REQUIRED"
        assert record["admission"] == "ADMIT"
        assert evidence["source_head"] == expected["head"]
        assert evidence["proof_receipts"] == [
            {
                "kind": "workflow_run",
                "id": expected["run"],
                "name": "Native functional verification",
                "head_sha": expected["head"],
                "conclusion": "success",
            }
        ]
        assert evidence["source_contract"][
            "remaining_exact_head_native_proof_gate_satisfied"
        ] is True
        assert evidence["native_receipts"]["operational_authority_false"] == "PASS"


def test_wave17_receipts_match_reconciliation_authority() -> None:
    wave_by_repo = {
        item["repository"]: item for item in load(WAVE17)["items"]
    }
    for repository, expected in TARGETS.items():
        receipt = load(ROOT / expected["receipt"])
        wave = wave_by_repo[repository]
        assert receipt["repository"] == repository
        assert receipt["source_head"] == expected["head"]
        assert wave["evidence"]["source_head"] == expected["head"]
        assert receipt["proof_receipts"][0]["id"] == expected["run"]
        assert wave["evidence"]["proof_receipts"][0]["id"] == expected["run"]
        assert receipt["surface_decision"] == "ADMIT"
        assert receipt["governed_subset_delta"] == {
            "ADMIT": 1,
            "REPAIR_REQUIRED": -1,
        }


def test_wave17_admission_fails_closed_on_each_proof_head_drift() -> None:
    for index in range(len(TARGETS)):
        mismatch = deepcopy(load(WAVE17))
        mismatch["items"][index]["evidence"]["proof_receipts"][0][
            "head_sha"
        ] = "0" * 40
        with pytest.raises(RepositorySurfaceError, match="proof/head drift"):
            apply_surface_reconciliation(report_through_wave16(), mismatch)


def test_wave17_reapplication_fails_closed_on_prior_decision_drift() -> None:
    once = apply_surface_reconciliation(report_through_wave16(), load(WAVE17))
    with pytest.raises(RepositorySurfaceError, match="prior decision drift"):
        apply_surface_reconciliation(once, load(WAVE17))
