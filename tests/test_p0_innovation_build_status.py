from __future__ import annotations

import json
from pathlib import Path

from job_app_helix.p0_builds import P0_IDS

ROOT = Path(__file__).resolve().parents[1]
STATUS = ROOT / "status" / "p0-innovation-build-verification-2026-08-11.json"
CONTRACT = (
    ROOT
    / "manifests"
    / "application_intelligence"
    / "p0_innovation_build_contract.v1.json"
)


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_p0_build_status_is_exact_head_and_complete() -> None:
    status = load(STATUS)
    head = status["source_canonical_head"]

    assert status["schema"] == "glaciereq.p0-innovation-build-status.v1"
    assert status["verification_state"] == "REFERENCE_BUILDS_VERIFIED"
    assert len(head) == 40
    assert status["expected_count"] == 25
    assert status["verified_count"] == 25
    assert status["failed"] == []
    assert tuple(status["checks"]) == P0_IDS
    assert all(status["checks"].values())

    assert status["artifact"]["source_commit"] == head
    assert status["artifact"]["status"] == "PASS"
    assert status["artifact"]["expected_count"] == 25
    assert status["artifact"]["verified_count"] == 25
    assert status["artifact"]["digest"].startswith("sha256:")

    assert len(status["queue"]["sha256"]) == 64
    assert len(status["implementation"]["sha256"]) == 64
    assert {item["name"] for item in status["workflow_receipts"]} == {
        "P0 Innovation Build Verification",
        "CI",
    }
    assert all(item["event"] == "push" for item in status["workflow_receipts"])
    assert all(item["head_sha"] == head for item in status["workflow_receipts"])
    assert all(item["conclusion"] == "success" for item in status["workflow_receipts"])


def test_status_covers_exact_build_contract() -> None:
    status = load(STATUS)
    contract = load(CONTRACT)

    contract_ids = tuple(item["company_id"] for item in contract["builds"])
    assert contract["count"] == 25
    assert contract_ids == P0_IDS
    assert tuple(status["checks"]) == contract_ids

    boundary = status["truth_boundary"]
    assert boundary["reference_build_is_not_company_deployment"] is True
    assert boundary["reference_build_is_not_company_affiliation"] is True
    assert boundary["successful_build_does_not_equal_company_adoption"] is True
    assert boundary["successful_build_does_not_equal_measured_company_impact"] is True
    assert boundary["successful_build_does_not_equal_promotion_ready"] is True
