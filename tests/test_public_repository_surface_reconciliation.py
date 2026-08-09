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
RECONCILIATION = Path(
    "manifests/public_repository_surface_reconciliation_2026-08-09.json"
)


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def governed_report() -> dict:
    return compile_governed_surface_report(
        load(OBSERVATIONS),
        load(DECISIONS),
        expected_public_count=75,
    )


def by_repository(report: dict) -> dict[str, dict]:
    return {item["repository"]: item for item in report["repositories"]}


def test_reconciliation_closes_two_stale_repairs_without_rewriting_predecessor() -> None:
    predecessor = governed_report()
    report = apply_surface_reconciliation(predecessor, load(RECONCILIATION))

    assert report["base_report_id"] == predecessor["base_report_id"]
    assert report["governed_overlay"] == predecessor["governed_overlay"]
    assert report["reconciliation_overlay"]["item_count"] == 3
    assert report["summary"]["admission"]["ADMIT"] == (
        predecessor["summary"]["admission"]["ADMIT"] + 2
    )
    assert report["summary"]["admission"]["REPAIR_REQUIRED"] == (
        predecessor["summary"]["admission"]["REPAIR_REQUIRED"] - 2
    )


def test_sigma_and_gateway_are_current_head_admitted() -> None:
    report = apply_surface_reconciliation(governed_report(), load(RECONCILIATION))
    repos = by_repository(report)

    sigma = repos["GlacierEQ/sigma-glue"]
    assert sigma["prior_reconciled_admission"] == "REPAIR_REQUIRED"
    assert sigma["admission"] == "ADMIT"
    assert sigma["decision_evidence"]["canonical_head"] == (
        "4a1ca8e5c88a62e8a94a43213b2c509af6afcea3"
    )
    assert {receipt["id"] for receipt in sigma["decision_evidence"]["proof_receipts"]} == {
        31279895312,
        31279895318,
    }

    gateway = repos["GlacierEQ/colossus-gateway"]
    assert gateway["prior_reconciled_admission"] == "REPAIR_REQUIRED"
    assert gateway["admission"] == "ADMIT"
    assert gateway["decision_evidence"]["canonical_head"] == (
        "3b41af0465c55a7128e8d22130d0dd7e52b02a8b"
    )
    continuity = gateway["decision_evidence"]["source_continuity"]
    assert continuity["changed_files"] == ["LICENSE", "LICENSE_NOTICE.md"]
    assert continuity["admitted_capability_source_files_changed"] is False


def test_apex_control_plane_does_not_inherit_ancestor_admission() -> None:
    report = apply_surface_reconciliation(governed_report(), load(RECONCILIATION))
    apex = by_repository(report)["GlacierEQ/apex-control-plane"]

    assert apex["admission"] == "REPAIR_REQUIRED"
    assert apex["repair_priority"] == "P1"
    assert apex["decision_evidence"]["canonical_head"] == (
        "641b55787ea13c6c0b742eb045406803893fbfc5"
    )
    assert apex["decision_evidence"]["current_head_workflow_run_count"] == 0
    assert "exact current main" in apex["decision_next_gate"]


def test_admit_reconciliation_rejects_non_hex_or_mismatched_receipts() -> None:
    predecessor = governed_report()
    reconciliation = deepcopy(load(RECONCILIATION))
    sigma = reconciliation["items"][0]
    sigma["evidence"]["canonical_head"] = "z" * 40
    with pytest.raises(RepositorySurfaceError, match="exact canonical_head"):
        apply_surface_reconciliation(predecessor, reconciliation)

    reconciliation = deepcopy(load(RECONCILIATION))
    sigma = reconciliation["items"][0]
    sigma["evidence"]["proof_receipts"][0]["head_sha"] = "0" * 40
    with pytest.raises(RepositorySurfaceError, match="proof/head drift"):
        apply_surface_reconciliation(predecessor, reconciliation)


def test_reconciliation_cannot_admit_quarantined_or_unknown_repository() -> None:
    predecessor = governed_report()
    reconciliation = deepcopy(load(RECONCILIATION))
    sigma = reconciliation["items"][0]
    sigma["repository"] = "GlacierEQ/legal-powerhouse"
    sigma["prior_decision"] = "QUARANTINED"
    with pytest.raises(RepositorySurfaceError, match="conflicts with blockers"):
        apply_surface_reconciliation(predecessor, reconciliation)

    reconciliation = deepcopy(load(RECONCILIATION))
    reconciliation["items"][0]["repository"] = "GlacierEQ/not-in-census"
    with pytest.raises(RepositorySurfaceError, match="unknown repository"):
        apply_surface_reconciliation(predecessor, reconciliation)
