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
    "public_repository_surface_reconciliation_wave17_2026-08-13.json",
    "public_repository_surface_reconciliation_wave18_2026-08-13.json",
    "public_repository_surface_reconciliation_wave19_2026-08-14.json",
    "public_repository_surface_reconciliation_wave20_2026-08-14.json",
)
LAYERS = tuple(ROOT / "manifests" / name for name in LAYER_NAMES)
WAVE21 = ROOT / (
    "manifests/public_repository_surface_reconciliation_wave21_2026-08-14.json"
)
TARGETS = {
    "GlacierEQ/apple-ane-kv-quantizer": {
        "head": "f784f80b8b17484e8aa89b034348687b6e8b85ab",
        "run": 31853557343,
        "token": "MODELED_SCENARIO_NOT_HARDWARE_MEASUREMENT",
        "capability": (
            "deterministic-modeled-kv-storage-reduction-and-"
            "transfer-time-estimation"
        ),
        "receipt": (
            "status/public-repository-surface-repair-wave21-apple-ane-2026-08-14.json"
        ),
    },
    "GlacierEQ/deepmind-tpu-mesh-optimizer": {
        "head": "2a23cd011367f23891c014c92e75f0b592c29db1",
        "run": 31853699272,
        "token": "MODELED_MESH_SCENARIO_NOT_TPU_MEASUREMENT",
        "capability": (
            "deterministic-modeled-mesh-sharding-transfer-compute-overlap-"
            "and-token-balancing"
        ),
        "receipt": (
            "status/public-repository-surface-repair-wave21-tpu-mesh-2026-08-14.json"
        ),
    },
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def report_through_wave20() -> dict:
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


def test_wave21_admits_only_two_exact_head_modeled_surfaces() -> None:
    before = report_through_wave20()
    after = apply_surface_reconciliation(before, load(WAVE21))
    assert subset_counts(before) == {
        "ADMIT": 29,
        "QUARANTINED": 3,
        "REFERENCE": 1,
        "REPAIR_REQUIRED": 25,
    }
    assert subset_counts(after) == {
        "ADMIT": 31,
        "QUARANTINED": 3,
        "REFERENCE": 1,
        "REPAIR_REQUIRED": 23,
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


def test_wave21_admissions_are_exact_head_scope_and_receipt_bound() -> None:
    report = apply_surface_reconciliation(report_through_wave20(), load(WAVE21))
    by_repo = {item["repository"]: item for item in report["repositories"]}
    for repository, expected in TARGETS.items():
        record = by_repo[repository]
        evidence = record["decision_evidence"]
        assert record["prior_reconciled_admission"] == "REPAIR_REQUIRED"
        assert evidence["canonical_head"] == expected["head"]
        assert evidence["evidence_token"] == expected["token"]
        assert evidence["verified_capability"] == expected["capability"]
        assert evidence["proof_receipts"] == [
            {
                "kind": "workflow_run",
                "id": expected["run"],
                "name": "Public Truth Gate",
                "head_sha": expected["head"],
                "conclusion": "success",
            }
        ]
        source_contract = evidence["source_contract"]
        assert source_contract["remaining_exact_head_native_proof_gate_satisfied"]


def test_wave21_receipts_match_reconciliation_authority() -> None:
    wave_by_repo = {
        item["repository"]: item for item in load(WAVE21)["items"]
    }
    assert set(wave_by_repo) == set(TARGETS)
    for repository, expected in TARGETS.items():
        wave = wave_by_repo[repository]
        receipt = load(ROOT / expected["receipt"])
        assert receipt["repository"] == repository
        assert receipt["source_canonical_head"] == expected["head"]
        assert wave["evidence"]["canonical_head"] == expected["head"]
        assert receipt["evidence_token"] == expected["token"]
        assert wave["evidence"]["evidence_token"] == expected["token"]
        assert receipt["verified_capability"] == expected["capability"]
        assert wave["evidence"]["verified_capability"] == expected["capability"]
        assert receipt["proof_receipts"] == wave["evidence"]["proof_receipts"]
        assert receipt["surface_decision"] == "ADMIT"
        assert receipt["governed_subset_delta"] == {
            "ADMIT": 1,
            "REPAIR_REQUIRED": -1,
        }


def test_wave21_fails_closed_on_each_proof_head_drift() -> None:
    for repository in TARGETS:
        mismatch = deepcopy(load(WAVE21))
        item = next(
            row for row in mismatch["items"] if row["repository"] == repository
        )
        item["evidence"]["proof_receipts"][0]["head_sha"] = "0" * 40
        with pytest.raises(RepositorySurfaceError, match="proof/head drift"):
            apply_surface_reconciliation(report_through_wave20(), mismatch)


def test_wave21_reapplication_fails_closed_on_prior_decision_drift() -> None:
    once = apply_surface_reconciliation(report_through_wave20(), load(WAVE21))
    with pytest.raises(RepositorySurfaceError, match="prior decision drift"):
        apply_surface_reconciliation(once, load(WAVE21))
