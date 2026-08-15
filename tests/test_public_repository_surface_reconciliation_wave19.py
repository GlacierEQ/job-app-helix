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
RECEIPT = ROOT / "status/public-repository-surface-repair-wave19-2026-08-14.json"
TARGET = "GlacierEQ/Pro-comet-agent"
HEAD = "27879babe8dfd3242f7579b3604c809686e84940"
RUN_ID = 31851939532
TOKEN = "BOUNDED_CONNECTOR_RUNTIME_NOT_LIVE_SAAS_OR_BROWSER_AUTHORITY"
CAPABILITY = (
    "deterministic-explicit-connector-adapter-runtime-with-"
    "typescript-browser-service-build-proof"
)


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


def test_wave19_admits_only_exact_head_pro_comet_surface() -> None:
    before = report_through_wave18()
    after = apply_surface_reconciliation(before, load(WAVE19))
    assert subset_counts(before) == {
        "ADMIT": 25,
        "QUARANTINED": 3,
        "REFERENCE": 1,
        "REPAIR_REQUIRED": 29,
    }
    assert subset_counts(after) == {
        "ADMIT": 26,
        "QUARANTINED": 3,
        "REFERENCE": 1,
        "REPAIR_REQUIRED": 28,
    }
    before_by_repo = {item["repository"]: item for item in before["repositories"]}
    after_by_repo = {item["repository"]: item for item in after["repositories"]}
    assert before_by_repo[TARGET]["admission"] == "REPAIR_REQUIRED"
    assert after_by_repo[TARGET]["admission"] == "ADMIT"
    assert after_by_repo[TARGET]["repair_priority"] is None
    for repository in before_by_repo:
        if repository != TARGET:
            assert before_by_repo[repository] == after_by_repo[repository]


def test_wave19_admission_is_exact_head_scope_and_receipt_bound() -> None:
    report = apply_surface_reconciliation(report_through_wave18(), load(WAVE19))
    record = next(
        item for item in report["repositories"] if item["repository"] == TARGET
    )
    evidence = record["decision_evidence"]
    assert record["prior_reconciled_admission"] == "REPAIR_REQUIRED"
    assert evidence["canonical_head"] == HEAD
    assert evidence["evidence_token"] == TOKEN
    assert evidence["verified_capability"] == CAPABILITY
    assert evidence["proof_receipts"] == [
        {
            "kind": "workflow_run",
            "id": RUN_ID,
            "name": "CI",
            "head_sha": HEAD,
            "conclusion": "success",
        }
    ]
    source_contract = evidence["source_contract"]
    assert source_contract["remaining_exact_head_native_proof_gate_satisfied"] is True
    native = evidence["native_receipts"]
    assert native["python_3_11_compile_behavior_and_truth"] == "PASS"
    assert native["python_3_12_compile_behavior_and_truth"] == "PASS"
    assert native["python_3_13_compile_behavior_and_truth"] == "PASS"
    assert native["typescript_server_build"] == "PASS"
    assert native["public_truth_boundary"] == "PASS"
    assert native["operational_authority_false"] == "PASS"


def test_wave19_receipt_matches_reconciliation_authority() -> None:
    wave = load(WAVE19)["items"][0]
    receipt = load(RECEIPT)
    assert receipt["repository"] == wave["repository"] == TARGET
    assert receipt["source_canonical_head"] == wave["evidence"]["canonical_head"] == HEAD
    assert receipt["evidence_token"] == wave["evidence"]["evidence_token"] == TOKEN
    assert (
        receipt["verified_capability"]
        == wave["evidence"]["verified_capability"]
        == CAPABILITY
    )
    assert receipt["proof_receipts"][0]["id"] == RUN_ID
    assert receipt["surface_decision"] == "ADMIT"
    assert receipt["governed_subset_delta"] == {
        "ADMIT": 1,
        "REPAIR_REQUIRED": -1,
    }


def test_wave19_fails_closed_on_proof_head_drift() -> None:
    mismatch = deepcopy(load(WAVE19))
    mismatch["items"][0]["evidence"]["proof_receipts"][0]["head_sha"] = "0" * 40
    with pytest.raises(RepositorySurfaceError, match="proof/head drift"):
        apply_surface_reconciliation(report_through_wave18(), mismatch)


def test_wave19_reapplication_fails_closed_on_prior_decision_drift() -> None:
    once = apply_surface_reconciliation(report_through_wave18(), load(WAVE19))
    with pytest.raises(RepositorySurfaceError, match="prior decision drift"):
        apply_surface_reconciliation(once, load(WAVE19))
