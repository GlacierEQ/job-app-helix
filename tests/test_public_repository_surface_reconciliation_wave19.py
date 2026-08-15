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
)
LAYERS = tuple(ROOT / "manifests" / name for name in LAYER_NAMES)
WAVE19 = ROOT / (
    "manifests/public_repository_surface_reconciliation_wave19_2026-08-14.json"
)
TARGETS = {
    "GlacierEQ/Pro-comet-agent": {
        "head": "27879babe8dfd3242f7579b3604c809686e84940",
        "token": "BOUNDED_CONNECTOR_RUNTIME_NOT_LIVE_SAAS_OR_BROWSER_AUTHORITY",
        "capability": (
            "deterministic-explicit-connector-adapter-runtime-with-"
            "typescript-browser-service-build-proof"
        ),
        "receipt": "status/public-repository-surface-repair-wave19-2026-08-14.json",
        "proof_receipts": [
            {
                "kind": "workflow_run",
                "id": 31851939532,
                "name": "CI",
                "head_sha": "27879babe8dfd3242f7579b3604c809686e84940",
                "conclusion": "success",
            }
        ],
        "native": {
            "python_3_11_compile_behavior_and_truth": "PASS",
            "python_3_12_compile_behavior_and_truth": "PASS",
            "python_3_13_compile_behavior_and_truth": "PASS",
            "typescript_server_build": "PASS",
            "public_truth_boundary": "PASS",
            "operational_authority_false": "PASS",
        },
    },
    "GlacierEQ/GlacierEQ_Swarm": {
        "head": "08d08a1cf35a975e8541e9305359ceddb190fc67",
        "token": "DURABLE_LOCAL_SWARM_RUNTIME_NOT_AUTOMATIC_ESTATE_AUTHORITY",
        "capability": (
            "deterministic-durable-capability-aware-swarm-and-"
            "crystallization-control-plane"
        ),
        "receipt": (
            "status/public-repository-surface-repair-wave19-swarm-2026-08-14.json"
        ),
        "proof_receipts": [
            {
                "kind": "workflow_run",
                "id": 31852306040,
                "name": "CI",
                "head_sha": "08d08a1cf35a975e8541e9305359ceddb190fc67",
                "conclusion": "success",
            },
            {
                "kind": "workflow_run",
                "id": 31852305754,
                "name": "Swarm Runtime",
                "head_sha": "08d08a1cf35a975e8541e9305359ceddb190fc67",
                "conclusion": "success",
            },
            {
                "kind": "workflow_run",
                "id": 31852305765,
                "name": "Swarm Container",
                "head_sha": "08d08a1cf35a975e8541e9305359ceddb190fc67",
                "conclusion": "success",
            },
        ],
        "native": {
            "python_3_11_crystallization_contract_and_truth": "PASS",
            "python_3_12_crystallization_contract_and_truth": "PASS",
            "python_3_13_crystallization_contract_and_truth": "PASS",
            "repository_owned_verification": "PASS",
            "trusted_caller_boundary": "PASS",
            "runtime_restart_failover_persistence_authenticated_api": "PASS",
            "container_image_build_real_task_restart_persistence": "PASS",
            "automatic_estate_completion_authority": False,
            "production_operational_authority": False,
        },
    },
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def report_through_wave18() -> dict:
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


def test_wave19_admits_only_two_exact_head_native_proof_surfaces() -> None:
    before = report_through_wave18()
    after = apply_surface_reconciliation(before, load(WAVE19))
    assert subset_counts(before) == {
        "ADMIT": 25,
        "QUARANTINED": 3,
        "REFERENCE": 1,
        "REPAIR_REQUIRED": 29,
    }
    assert subset_counts(after) == {
        "ADMIT": 27,
        "QUARANTINED": 3,
        "REFERENCE": 1,
        "REPAIR_REQUIRED": 27,
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


def test_wave19_admissions_are_exact_head_scope_and_receipt_bound() -> None:
    report = apply_surface_reconciliation(report_through_wave18(), load(WAVE19))
    by_repo = {item["repository"]: item for item in report["repositories"]}
    for repository, expected in TARGETS.items():
        record = by_repo[repository]
        evidence = record["decision_evidence"]
        assert record["prior_reconciled_admission"] == "REPAIR_REQUIRED"
        assert evidence["canonical_head"] == expected["head"]
        assert evidence["evidence_token"] == expected["token"]
        assert evidence["verified_capability"] == expected["capability"]
        assert evidence["proof_receipts"] == expected["proof_receipts"]
        source_contract = evidence["source_contract"]
        assert source_contract["remaining_exact_head_native_proof_gate_satisfied"]
        for key, value in expected["native"].items():
            assert evidence["native_receipts"][key] == value


def test_wave19_receipts_match_reconciliation_authority() -> None:
    wave_by_repo = {
        item["repository"]: item for item in load(WAVE19)["items"]
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
        assert receipt["proof_receipts"] == expected["proof_receipts"]
        assert receipt["surface_decision"] == "ADMIT"
        assert receipt["governed_subset_delta"] == {
            "ADMIT": 1,
            "REPAIR_REQUIRED": -1,
        }


def test_wave19_fails_closed_on_each_proof_head_drift() -> None:
    for repository in TARGETS:
        mismatch = deepcopy(load(WAVE19))
        item = next(
            row for row in mismatch["items"] if row["repository"] == repository
        )
        item["evidence"]["proof_receipts"][0]["head_sha"] = "0" * 40
        with pytest.raises(RepositorySurfaceError, match="proof/head drift"):
            apply_surface_reconciliation(report_through_wave18(), mismatch)


def test_wave19_reapplication_fails_closed_on_prior_decision_drift() -> None:
    once = apply_surface_reconciliation(report_through_wave18(), load(WAVE19))
    with pytest.raises(RepositorySurfaceError, match="prior decision drift"):
        apply_surface_reconciliation(once, load(WAVE19))
