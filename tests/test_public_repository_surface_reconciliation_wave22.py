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
    "public_repository_surface_reconciliation_wave21_2026-08-14.json",
)
LAYERS = tuple(ROOT / "manifests" / name for name in LAYER_NAMES)
WAVE22 = ROOT / (
    "manifests/public_repository_surface_reconciliation_wave22_2026-08-14.json"
)
RECEIPT = ROOT / (
    "status/public-repository-surface-repair-wave22-apex-cli-2026-08-14.json"
)
TARGET = "GlacierEQ/apex-cli"
HEAD = "612c059b8e6a0103a1f7163af0461be7a7495fe9"
RUN_ID = 31854284196
TOKEN = "LOCAL_APEX_CLI_RUNTIME_NOT_EXTERNAL_SYSTEM_AUTHORITY"
CAPABILITY = (
    "deterministic-repository-local-cli-dispatch-and-"
    "fresh-install-runtime-bootstrap"
)


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def report_through_wave21() -> dict:
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


def test_wave22_admits_only_exact_head_apex_cli_surface() -> None:
    before = report_through_wave21()
    after = apply_surface_reconciliation(before, load(WAVE22))
    assert subset_counts(before) == {
        "ADMIT": 29,
        "QUARANTINED": 3,
        "REFERENCE": 1,
        "REPAIR_REQUIRED": 25,
    }
    assert subset_counts(after) == {
        "ADMIT": 30,
        "QUARANTINED": 3,
        "REFERENCE": 1,
        "REPAIR_REQUIRED": 24,
    }

    before_by_repo = {item["repository"]: item for item in before["repositories"]}
    after_by_repo = {item["repository"]: item for item in after["repositories"]}
    assert before_by_repo[TARGET]["admission"] == "REPAIR_REQUIRED"
    assert after_by_repo[TARGET]["admission"] == "ADMIT"
    assert after_by_repo[TARGET]["repair_priority"] is None
    for repository in before_by_repo:
        if repository != TARGET:
            assert before_by_repo[repository] == after_by_repo[repository]


def test_wave22_admission_is_exact_head_scope_and_receipt_bound() -> None:
    report = apply_surface_reconciliation(report_through_wave21(), load(WAVE22))
    record = next(
        item for item in report["repositories"] if item["repository"] == TARGET
    )
    evidence = record["decision_evidence"]
    assert record["prior_reconciled_admission"] == "REPAIR_REQUIRED"
    assert record["admission"] == "ADMIT"
    assert evidence["source_head"] == HEAD
    assert evidence["evidence_token"] == TOKEN
    assert evidence["verified_capability"] == CAPABILITY
    assert evidence["proof_receipts"] == [
        {
            "kind": "workflow_run",
            "id": RUN_ID,
            "name": "Public Truth Gate",
            "head_sha": HEAD,
            "conclusion": "success",
        }
    ]
    source_contract = evidence["source_contract"]
    assert source_contract["remaining_exact_head_native_proof_gate_satisfied"]
    native = evidence["native_receipts"]
    assert native["python_3_11_exact_source_compile_tests_runtime_and_truth"] == "PASS"
    assert native["python_3_12_exact_source_compile_tests_runtime_and_truth"] == "PASS"
    assert native["python_3_13_exact_source_compile_tests_runtime_and_truth"] == "PASS"
    assert native["missing_external_job_app_dependency_exit_78"] == "PASS"
    assert native["fresh_install_runtime_bootstrap_and_status"] == "PASS"
    assert native["legacy_whole_tree_lint_debt_excluded_from_scope"] is True


def test_wave22_receipt_matches_reconciliation_authority() -> None:
    wave = load(WAVE22)["items"][0]
    receipt = load(RECEIPT)
    assert receipt["repository"] == wave["repository"] == TARGET
    assert receipt["source_head"] == wave["evidence"]["source_head"] == HEAD
    assert receipt["evidence_token"] == wave["evidence"]["evidence_token"] == TOKEN
    assert receipt["verified_capability"] == wave["evidence"]["verified_capability"]
    assert receipt["verified_capability"] == CAPABILITY
    assert receipt["proof_receipts"] == wave["evidence"]["proof_receipts"]
    assert receipt["surface_decision"] == "ADMIT"
    assert receipt["governed_subset_delta"] == {
        "ADMIT": 1,
        "REPAIR_REQUIRED": -1,
    }


def test_wave22_fails_closed_on_proof_head_drift() -> None:
    mismatch = deepcopy(load(WAVE22))
    mismatch["items"][0]["evidence"]["proof_receipts"][0]["head_sha"] = "0" * 40
    with pytest.raises(RepositorySurfaceError, match="proof/head drift"):
        apply_surface_reconciliation(report_through_wave21(), mismatch)


def test_wave22_reapplication_fails_closed_on_prior_decision_drift() -> None:
    once = apply_surface_reconciliation(report_through_wave21(), load(WAVE22))
    with pytest.raises(RepositorySurfaceError, match="prior decision drift"):
        apply_surface_reconciliation(once, load(WAVE22))
