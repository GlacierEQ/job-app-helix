from __future__ import annotations

import json
from pathlib import Path

from job_app_helix.repository_surface import compile_governed_surface_report
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
    ROOT / "manifests/public_repository_surface_reconciliation_wave7_2026-08-10.json",
)
WAVE8 = ROOT / "manifests/public_repository_surface_reconciliation_wave8_2026-08-10.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def report_through_wave7() -> dict:
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


def test_wave8_preserves_counts_while_advancing_source_evidence() -> None:
    before = report_through_wave7()
    after = apply_surface_reconciliation(before, load(WAVE8))
    expected = {
        "ADMIT": 14,
        "QUARANTINED": 3,
        "REFERENCE": 1,
        "REPAIR_REQUIRED": 40,
    }
    assert subset_counts(before) == expected
    assert subset_counts(after) == expected


def test_colossus_gateway_is_source_complete_but_metadata_blocked() -> None:
    report = apply_surface_reconciliation(report_through_wave7(), load(WAVE8))
    record = next(
        item
        for item in report["repositories"]
        if item["repository"] == "GlacierEQ/colossus-gateway"
    )
    head = "940dd403c797a0fcc71b7b576a7d1c5d23ebadb5"
    evidence = record["decision_evidence"]
    assert record["admission"] == "REPAIR_REQUIRED"
    assert record["repair_priority"] == "P1"
    assert record["decision_excellence_state"] == "SOURCE_TRUTH_COMPLETE_METADATA_BLOCKED"
    assert evidence["canonical_head"] == head
    assert evidence["evidence_token"] == (
        "LOCAL_MCP_STDIO_SERVER_NOT_EXTERNAL_COLOSSUS_RUNTIME"
    )
    assert evidence["blocking_metadata"]["finding"] == "METADATA_DESCRIPTION_DRIFT"
    receipts = evidence["proof_receipts"]
    assert {receipt["id"] for receipt in receipts} == {
        31461006818,
        31461006820,
        31461006836,
    }
    assert all(receipt["head_sha"] == head for receipt in receipts)
    assert all(receipt["conclusion"] == "success" for receipt in receipts)


def test_wave8_does_not_claim_about_metadata_mutated() -> None:
    wave = load(WAVE8)
    item = wave["items"][0]
    blocker = item["evidence"]["blocking_metadata"]
    assert item["decision"] == "REPAIR_REQUIRED"
    assert blocker["description"] == (
        "Universal MCP bridge for Colossus-class orchestration. AKOS portfolio."
    )
    assert "Update and read back GitHub About description" in item["next_gate"]
