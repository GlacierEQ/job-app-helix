from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

import job_app_helix.library_cli as library_cli
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
)
WAVE6 = ROOT / "manifests/public_repository_surface_reconciliation_wave6_2026-08-09.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def report_through_wave5() -> dict:
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


def test_wave6_advances_only_proof_complete_repository_to_admit() -> None:
    before = report_through_wave5()
    after = apply_surface_reconciliation(before, load(WAVE6))
    assert subset_counts(before) == {
        "ADMIT": 12,
        "QUARANTINED": 3,
        "REFERENCE": 1,
        "REPAIR_REQUIRED": 42,
    }
    assert subset_counts(after) == {
        "ADMIT": 13,
        "QUARANTINED": 3,
        "REFERENCE": 1,
        "REPAIR_REQUIRED": 41,
    }


def test_colossus_training_flux_is_exact_head_admit() -> None:
    report = apply_surface_reconciliation(report_through_wave5(), load(WAVE6))
    record = next(
        item
        for item in report["repositories"]
        if item["repository"] == "GlacierEQ/colossus-training-flux"
    )
    head = "ad4ae574efad762550b373967a57008848986df4"
    assert record["admission"] == "ADMIT"
    assert record["decision_evidence"]["canonical_head"] == head
    receipts = record["decision_evidence"]["proof_receipts"]
    assert {receipt["id"] for receipt in receipts} == {31349338606, 31349338843}
    assert all(receipt["head_sha"] == head for receipt in receipts)
    assert all(receipt["conclusion"] == "success" for receipt in receipts)


def test_repaired_but_blocked_surfaces_remain_repair_required() -> None:
    report = apply_surface_reconciliation(report_through_wave5(), load(WAVE6))
    by_repo = {item["repository"]: item for item in report["repositories"]}

    auto = by_repo["GlacierEQ/ai-auto-driller-unified"]
    assert auto["admission"] == "REPAIR_REQUIRED"
    assert (
        auto["decision_evidence"]["canonical_head"]
        == "c0c5d8b3d3e1adb47480a9619e10ed18ed1e3f76"
    )
    assert "v4.0" in auto["decision_evidence"]["blocking_metadata"]["description"]

    storage = by_repo["GlacierEQ/computer-user-storage"]
    assert storage["admission"] == "REPAIR_REQUIRED"
    assert (
        storage["decision_evidence"]["canonical_head"]
        == "ad307c30ab53df53876c7ecaff6682964c5ae5b1"
    )
    storage_description = storage["decision_evidence"]["blocking_metadata"][
        "description"
    ]
    assert "Distributed Storage Backend" in storage_description

    apex = by_repo["GlacierEQ/apex-cli"]
    assert apex["admission"] == "REPAIR_REQUIRED"
    assert apex["repair_priority"] == "P0"
    security_history = apex["decision_evidence"]["blocking_security_history"]
    assert "Historical public Git commits" in security_history


def test_wave6_admit_remains_fail_closed_against_receipt_drift() -> None:
    predecessor = report_through_wave5()
    mismatch = deepcopy(load(WAVE6))
    mismatch["items"][0]["evidence"]["proof_receipts"][0]["head_sha"] = "0" * 40
    with pytest.raises(RepositorySurfaceError, match="proof/head drift"):
        apply_surface_reconciliation(predecessor, mismatch)


def test_canonical_manifests_are_cwd_independent_and_wheel_packaged(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    canonical_paths = (
        library_cli.DEFAULT_PROGRAM,
        library_cli.DEFAULT_SURFACE_OBSERVATIONS,
        library_cli.DEFAULT_SURFACE_DECISIONS,
        *library_cli.DEFAULT_SURFACE_RECONCILIATIONS,
    )
    assert all(path.is_absolute() and path.is_file() for path in canonical_paths)

    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert '[tool.hatch.build.targets.wheel.force-include]' in pyproject
    assert '"manifests" = "job_app_helix/_library_manifests"' in pyproject

    monkeypatch.setattr(library_cli, "_SOURCE_ROOT", tmp_path)
    fallback = library_cli._default_manifest("example.json")
    assert fallback == library_cli._PACKAGE_DIR / "_library_manifests" / "example.json"
