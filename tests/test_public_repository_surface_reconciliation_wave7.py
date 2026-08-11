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
)
WAVE7 = ROOT / "manifests/public_repository_surface_reconciliation_wave7_2026-08-10.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def report_through_wave6() -> dict:
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


def test_wave7_advances_verified_local_router_to_admit() -> None:
    before = report_through_wave6()
    after = apply_surface_reconciliation(before, load(WAVE7))
    assert subset_counts(before) == {
        "ADMIT": 13,
        "QUARANTINED": 3,
        "REFERENCE": 1,
        "REPAIR_REQUIRED": 41,
    }
    assert subset_counts(after) == {
        "ADMIT": 14,
        "QUARANTINED": 3,
        "REFERENCE": 1,
        "REPAIR_REQUIRED": 40,
    }


def test_mcp_stack_admission_is_exact_head_and_scope_bound() -> None:
    report = apply_surface_reconciliation(report_through_wave6(), load(WAVE7))
    record = next(
        item
        for item in report["repositories"]
        if item["repository"] == "GlacierEQ/glaciereq-mcp-stack"
    )
    head = "2ab81b15283505c407265ef27e3862279f61a94f"
    evidence = record["decision_evidence"]
    assert record["admission"] == "ADMIT"
    assert evidence["canonical_head"] == head
    assert evidence["verified_capability"] == "policy-gated-local-tool-dispatch"
    assert evidence["evidence_token"] == (
        "LOCAL_ALLOWLIST_ROUTER_NOT_EXTERNAL_MCP_DEPLOYMENT"
    )
    receipts = evidence["proof_receipts"]
    assert {receipt["id"] for receipt in receipts} == {31460004637, 31460004959}
    assert all(receipt["head_sha"] == head for receipt in receipts)
    assert all(receipt["conclusion"] == "success" for receipt in receipts)


def test_wave7_admission_fails_closed_on_receipt_drift() -> None:
    predecessor = report_through_wave6()
    mismatch = deepcopy(load(WAVE7))
    mismatch["items"][0]["evidence"]["proof_receipts"][0]["head_sha"] = "0" * 40
    with pytest.raises(RepositorySurfaceError, match="proof/head drift"):
        apply_surface_reconciliation(predecessor, mismatch)
