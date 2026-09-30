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
    "public_repository_surface_reconciliation_wave22_2026-08-14.json",
)
LAYERS = tuple(ROOT / "manifests" / name for name in LAYER_NAMES)
WAVE23 = ROOT / "manifests/public_repository_surface_reconciliation_wave23_2026-08-14.json"
GROK = "GlacierEQ/grokodile"
TRAINIUM = "GlacierEQ/aws-trainium-neuron-sentinel"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def report_through_wave22() -> dict:
    report = compile_governed_surface_report(
        load(OBSERVATIONS),
        load(DECISIONS),
        expected_public_count=75,
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


def test_wave23_has_one_new_admission_and_one_zero_delta_refresh() -> None:
    before = report_through_wave22()
    after = apply_surface_reconciliation(before, load(WAVE23))
    assert subset_counts(before) == {
        "ADMIT": 30,
        "QUARANTINED": 3,
        "REFERENCE": 1,
        "REPAIR_REQUIRED": 24,
    }
    assert subset_counts(after) == {
        "ADMIT": 31,
        "QUARANTINED": 3,
        "REFERENCE": 1,
        "REPAIR_REQUIRED": 23,
    }
    b = {x["repository"]: x for x in before["repositories"]}
    a = {x["repository"]: x for x in after["repositories"]}
    assert b[GROK]["admission"] == "REPAIR_REQUIRED"
    assert a[GROK]["admission"] == "ADMIT"
    assert b[TRAINIUM]["admission"] == "ADMIT"
    assert a[TRAINIUM]["admission"] == "ADMIT"
    for repo in b:
        if repo not in {GROK, TRAINIUM}:
            assert b[repo] == a[repo]


def test_wave23_exact_heads_and_receipts_are_bound() -> None:
    report = apply_surface_reconciliation(report_through_wave22(), load(WAVE23))
    by_repo = {x["repository"]: x for x in report["repositories"]}
    grok = by_repo[GROK]
    trainium = by_repo[TRAINIUM]
    assert grok["prior_reconciled_admission"] == "REPAIR_REQUIRED"
    assert (
        grok["decision_evidence"]["source_head"]
        == "fb51c671e66005e93385d3828053b051083f4c5d"
    )
    assert grok["decision_evidence"]["proof_receipts"][0]["id"] == 31854959743
    assert trainium["prior_reconciled_admission"] == "ADMIT"
    assert (
        trainium["decision_evidence"]["source_head"]
        == "bfffd8dc67ecbd86e06dc375b9550f72788a398f"
    )
    assert trainium["decision_evidence"]["proof_receipts"][0]["id"] == 31854768152
    assert (
        trainium["decision_evidence"]["source_contract"][
            "refreshes_existing_admission"
        ]
        is True
    )


def test_wave23_receipts_match_mixed_delta_contract() -> None:
    wave = {x["repository"]: x for x in load(WAVE23)["items"]}
    grok_receipt = load(
        ROOT / "status/public-repository-surface-repair-wave23-grokodile-2026-08-14.json"
    )
    trainium_receipt = load(
        ROOT
        / "status/public-repository-surface-repair-wave23-trainium-refresh-2026-08-14.json"
    )
    assert (
        grok_receipt["source_head"]
        == wave[GROK]["evidence"]["source_head"]
    )
    assert grok_receipt["governed_subset_delta"] == {
        "ADMIT": 1,
        "REPAIR_REQUIRED": -1,
    }
    assert (
        trainium_receipt["source_head"]
        == wave[TRAINIUM]["evidence"]["source_head"]
    )
    assert trainium_receipt["prior_surface_decision"] == "ADMIT"
    assert trainium_receipt["refreshes_existing_admission"] is True
    assert trainium_receipt["governed_subset_delta"] == {
        "ADMIT": 0,
        "REPAIR_REQUIRED": 0,
    }


def test_wave23_fails_closed_on_each_proof_head_drift() -> None:
    for index in range(2):
        mismatch = deepcopy(load(WAVE23))
        mismatch["items"][index]["evidence"]["proof_receipts"][0]["head_sha"] = (
            "0" * 40
        )
        with pytest.raises(RepositorySurfaceError, match="proof/head drift"):
            apply_surface_reconciliation(report_through_wave22(), mismatch)


def test_wave23_fails_closed_on_predecessor_drift() -> None:
    mismatch = deepcopy(load(WAVE23))
    mismatch["items"][0]["prior_decision"] = "ADMIT"
    with pytest.raises(RepositorySurfaceError, match="prior decision drift"):
        apply_surface_reconciliation(report_through_wave22(), mismatch)
