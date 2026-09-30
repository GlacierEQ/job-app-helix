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

OBSERVATIONS = Path(
    "manifests/public_repository_surface_observations_2026-08-08.json"
)
DECISIONS = Path("manifests/public_repository_surface_decisions_2026-08-08.json")
WAVE2 = Path("manifests/public_repository_surface_reconciliation_2026-08-09.json")
WAVE3 = Path(
    "manifests/public_repository_surface_reconciliation_wave3_2026-08-09.json"
)


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def governed_report() -> dict:
    return compile_governed_surface_report(
        load(OBSERVATIONS),
        load(DECISIONS),
        expected_public_count=75,
    )


def current_report() -> dict:
    report = apply_surface_reconciliation(governed_report(), load(WAVE2))
    return apply_surface_reconciliation(report, load(WAVE3))


def by_repository(report: dict) -> dict[str, dict]:
    return {item["repository"]: item for item in report["repositories"]}


def test_wave3_advances_two_repairs_after_wave2_without_rewriting_history() -> None:
    original = governed_report()
    wave2 = apply_surface_reconciliation(original, load(WAVE2))
    wave3 = apply_surface_reconciliation(wave2, load(WAVE3))

    assert wave3["base_report_id"] == original["base_report_id"]
    assert wave3["governed_overlay"] == original["governed_overlay"]
    assert wave3["summary"]["admission"]["ADMIT"] == (
        original["summary"]["admission"]["ADMIT"] + 4
    )
    assert wave3["summary"]["admission"]["REPAIR_REQUIRED"] == (
        original["summary"]["admission"]["REPAIR_REQUIRED"] - 4
    )
    assert wave3["reconciliation_overlay"]["item_count"] == 2


def test_echo_is_admitted_only_from_exact_current_head_proof() -> None:
    echo = by_repository(current_report())["GlacierEQ/ECHO"]

    assert echo["admission"] == "ADMIT"
    assert echo["prior_reconciled_admission"] == "REPAIR_REQUIRED"
    assert echo["decision_excellence_state"] == "PUBLIC_BOUNDARY_VERIFIED"
    assert echo["decision_evidence"]["source_head"] == (
        "6acdb3be1739f1659f3cec9f4b7d39d5799cd476"
    )
    assert {receipt["id"] for receipt in echo["decision_evidence"]["proof_receipts"]} == {
        31340641959,
        31340641961,
    }
    assert all(
        receipt["conclusion"] == "success"
        for receipt in echo["decision_evidence"]["proof_receipts"]
    )
    assert len(echo["reconciliation_history"]) == 1


def test_apple_is_admitted_only_as_modeled_capability() -> None:
    apple = by_repository(current_report())["GlacierEQ/apple-ane-kv-quantizer"]

    assert apple["admission"] == "ADMIT"
    assert apple["prior_reconciled_admission"] == "REPAIR_REQUIRED"
    assert apple["decision_excellence_state"] == "MODELED_CAPABILITY_VERIFIED"
    assert apple["decision_evidence"]["source_head"] == (
        "32f69cfa064cbb833b663bc43ace04507f8570c5"
    )
    assert apple["decision_evidence"]["evidence_token"] == (
        "MODELED_SCENARIO_NOT_HARDWARE_MEASUREMENT"
    )
    receipts = apple["decision_evidence"]["proof_receipts"]
    assert [(item["id"], item["name"]) for item in receipts] == [
        (31340687801, "Public Truth Gate")
    ]


def test_wave3_rejects_invalid_head_receipt_or_predecessor_state() -> None:
    wave2 = apply_surface_reconciliation(governed_report(), load(WAVE2))

    malformed = deepcopy(load(WAVE3))
    malformed["items"][0]["evidence"]["source_head"] = "z" * 40
    with pytest.raises(RepositorySurfaceError, match="exact source_head"):
        apply_surface_reconciliation(wave2, malformed)

    mismatch = deepcopy(load(WAVE3))
    mismatch["items"][1]["evidence"]["proof_receipts"][0]["head_sha"] = "0" * 40
    with pytest.raises(RepositorySurfaceError, match="proof/head drift"):
        apply_surface_reconciliation(wave2, mismatch)

    drift = deepcopy(load(WAVE3))
    drift["items"][0]["prior_decision"] = "ADMIT"
    with pytest.raises(RepositorySurfaceError, match="prior decision drift"):
        apply_surface_reconciliation(wave2, drift)
