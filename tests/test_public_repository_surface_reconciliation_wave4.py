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
OBSERVATIONS = ROOT / (
    "manifests/public_repository_surface_observations_2026-08-08.json"
)
DECISIONS = ROOT / "manifests/public_repository_surface_decisions_2026-08-08.json"
WAVE2 = ROOT / (
    "manifests/public_repository_surface_reconciliation_2026-08-09.json"
)
WAVE3 = ROOT / (
    "manifests/public_repository_surface_reconciliation_wave3_2026-08-09.json"
)
WAVE4 = ROOT / (
    "manifests/public_repository_surface_reconciliation_wave4_2026-08-09.json"
)

EXPECTED = {
    "GlacierEQ/deepmind-tpu-mesh-optimizer": (
        "66864aed96061dc681555973452c0abdaeadc405",
        31341623265,
    ),
    "GlacierEQ/deepseek-mla-moe-sentinel": (
        "09ee2cfff69498ac3ccdd2d805ea83a3cd917bab",
        31341886084,
    ),
    "GlacierEQ/kimi-mooncake-kv-stream": (
        "5abe714fb6a2fc5088d8f80e1a6169373e944510",
        31341805561,
    ),
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def report_through(path: Path | None = None) -> dict:
    report = compile_governed_surface_report(
        load(OBSERVATIONS),
        load(DECISIONS),
        expected_public_count=75,
    )
    for layer in (WAVE2, WAVE3):
        report = apply_surface_reconciliation(report, load(layer))
    if path is not None:
        report = apply_surface_reconciliation(report, load(path))
    return report


def test_wave4_reduces_repair_debt_by_three_without_rewriting_prior_layers() -> None:
    before = report_through()
    after = report_through(WAVE4)
    before_counts = before["summary"]["admission"]
    after_counts = after["summary"]["admission"]
    assert after_counts["ADMIT"] == before_counts["ADMIT"] + 3
    assert after_counts["REPAIR_REQUIRED"] == before_counts["REPAIR_REQUIRED"] - 3
    assert after_counts["ADMIT"] == 9
    assert after_counts["REPAIR_REQUIRED"] == 45
    assert after["governed_overlay"] == before["governed_overlay"]


def test_wave4_admits_only_exact_current_heads_with_success_receipts() -> None:
    report = report_through(WAVE4)
    by_repo = {item["repository"]: item for item in report["repositories"]}
    for repository, (head, run_id) in EXPECTED.items():
        record = by_repo[repository]
        assert record["admission"] == "ADMIT"
        assert record["prior_reconciled_admission"] == "REPAIR_REQUIRED"
        assert record["decision_evidence"]["canonical_head"] == head
        receipts = record["decision_evidence"]["proof_receipts"]
        observed = [
            (item["id"], item["head_sha"], item["conclusion"])
            for item in receipts
        ]
        assert observed == [(run_id, head, "success")]


def test_wave4_rejects_head_drift_receipt_drift_and_predecessor_drift() -> None:
    predecessor = report_through()

    malformed = deepcopy(load(WAVE4))
    malformed["items"][0]["evidence"]["canonical_head"] = "z" * 40
    with pytest.raises(RepositorySurfaceError, match="exact canonical_head"):
        apply_surface_reconciliation(predecessor, malformed)

    mismatch = deepcopy(load(WAVE4))
    mismatch["items"][1]["evidence"]["proof_receipts"][0]["head_sha"] = "0" * 40
    with pytest.raises(RepositorySurfaceError, match="proof/head drift"):
        apply_surface_reconciliation(predecessor, mismatch)

    prior = deepcopy(load(WAVE4))
    prior["items"][2]["prior_decision"] = "ADMIT"
    with pytest.raises(RepositorySurfaceError, match="prior decision drift"):
        apply_surface_reconciliation(predecessor, prior)
