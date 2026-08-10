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
WAVE2 = ROOT / "manifests/public_repository_surface_reconciliation_2026-08-09.json"
WAVE3 = ROOT / "manifests/public_repository_surface_reconciliation_wave3_2026-08-09.json"
WAVE4 = ROOT / "manifests/public_repository_surface_reconciliation_wave4_2026-08-09.json"
WAVE5 = ROOT / "manifests/public_repository_surface_reconciliation_wave5_2026-08-09.json"

EXPECTED = {
    "GlacierEQ/apex-control-plane": (
        "2ada79228f83c31cc21c5194062c64b353d9cc48",
        {31346871422, 31346871196},
    ),
    "GlacierEQ/aws-trainium-neuron-sentinel": (
        "b30bc0ae04030a565204c4e0abced082a7b50979",
        {31346903588},
    ),
    "GlacierEQ/megamind": (
        "b70121db3ef1fad23ef6001234707bcabce21856",
        {31347374683},
    ),
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def report_through_wave4() -> dict:
    report = compile_governed_surface_report(
        load(OBSERVATIONS), load(DECISIONS), expected_public_count=75
    )
    for layer in (WAVE2, WAVE3, WAVE4):
        report = apply_surface_reconciliation(report, load(layer))
    return report


def _historical_subset_counts(report: dict) -> dict[str, int]:
    original = {item["repository"] for item in load(DECISIONS)["items"]}
    counts: dict[str, int] = {}
    for item in report["repositories"]:
        if item["repository"] not in original:
            continue
        counts[item["admission"]] = counts.get(item["admission"], 0) + 1
    return counts


def test_wave5_reduces_original_repair_subset_by_three() -> None:
    before = report_through_wave4()
    after = apply_surface_reconciliation(before, load(WAVE5))
    before_counts = _historical_subset_counts(before)
    after_counts = _historical_subset_counts(after)

    assert before_counts == {
        "ADMIT": 9,
        "QUARANTINED": 3,
        "REFERENCE": 1,
        "REPAIR_REQUIRED": 45,
    }
    assert after_counts == {
        "ADMIT": 12,
        "QUARANTINED": 3,
        "REFERENCE": 1,
        "REPAIR_REQUIRED": 42,
    }


def test_wave5_admits_only_exact_current_heads_with_success_receipts() -> None:
    report = apply_surface_reconciliation(report_through_wave4(), load(WAVE5))
    by_repo = {item["repository"]: item for item in report["repositories"]}

    for repository, (head, run_ids) in EXPECTED.items():
        record = by_repo[repository]
        assert record["admission"] == "ADMIT"
        assert record["prior_reconciled_admission"] == "REPAIR_REQUIRED"
        assert record["decision_evidence"]["canonical_head"] == head
        receipts = record["decision_evidence"]["proof_receipts"]
        assert {receipt["id"] for receipt in receipts} == run_ids
        assert all(receipt["head_sha"] == head for receipt in receipts)
        assert all(receipt["conclusion"] == "success" for receipt in receipts)


def test_wave5_rejects_head_receipt_and_predecessor_drift() -> None:
    predecessor = report_through_wave4()

    malformed = deepcopy(load(WAVE5))
    malformed["items"][0]["evidence"]["canonical_head"] = "not-a-sha"
    with pytest.raises(RepositorySurfaceError, match="exact canonical_head"):
        apply_surface_reconciliation(predecessor, malformed)

    mismatch = deepcopy(load(WAVE5))
    mismatch["items"][1]["evidence"]["proof_receipts"][0]["head_sha"] = "0" * 40
    with pytest.raises(RepositorySurfaceError, match="proof/head drift"):
        apply_surface_reconciliation(predecessor, mismatch)

    prior = deepcopy(load(WAVE5))
    prior["items"][2]["prior_decision"] = "ADMIT"
    with pytest.raises(RepositorySurfaceError, match="prior decision drift"):
        apply_surface_reconciliation(predecessor, prior)
