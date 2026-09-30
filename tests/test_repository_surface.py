from __future__ import annotations

import json
from pathlib import Path

import pytest

from job_app_helix.repository_surface import (
    RepositorySurfaceError,
    audit_repository_surface,
    compile_surface_report,
)

OBSERVATIONS = Path(
    "manifests/public_repository_surface_observations_2026-08-08.json"
)


def clean_record() -> dict:
    return {
        "repository": "GlacierEQ/example",
        "public": True,
        "assessment_state": "COMPLETE",
        "lineage_state": "ACTIVE_SYSTEM",
        "readme": {
            "exists": True,
            "claims_match_evidence": True,
            "referenced_paths_resolve": True,
            "current_state_is_separate_from_aspiration": True,
            "nonclaims_present": True,
        },
        "metadata": {
            "description_matches_readme": True,
            "homepage_matches_reference_surface": True,
            "topics_present": True,
            "license_state_explicit": True,
        },
        "proof": {
            "evidence_level": "TEST",
            "receipt_fresh": True,
            "source_head_bound": True,
        },
        "risk": {},
        "health": {"health_state": "RECRUITER_READY", "assessment_id": "health-1"},
    }


def test_complete_clean_surface_can_admit() -> None:
    result = audit_repository_surface(clean_record())
    assert result["admission"] == "ADMIT"
    assert result["repair_priority"] is None
    assert result["findings"] == []


def test_unassessed_surface_fails_visible() -> None:
    record = clean_record()
    record["assessment_state"] = "UNASSESSED"
    result = audit_repository_surface(record)
    assert result["admission"] == "REPAIR_REQUIRED"
    assert result["repair_priority"] == "P2"
    assert "SURFACE_ASSESSMENT_UNASSESSED" in result["findings"]


def test_company_named_without_boundary_is_p0() -> None:
    record = clean_record()
    record.update(
        {
            "company_named": True,
            "company_family": "xai",
            "non_affiliation_boundary": False,
        }
    )
    result = audit_repository_surface(record)
    assert result["admission"] == "REPAIR_REQUIRED"
    assert result["repair_priority"] == "P0"
    assert "COMPANY_AFFILIATION_BOUNDARY_MISSING" in result["findings"]


def test_stale_health_forces_stale_authority() -> None:
    record = clean_record()
    record["health"] = {"health_state": "STALE", "assessment_id": "old-health"}
    result = audit_repository_surface(record)
    assert result["admission"] == "STALE_AUTHORITY"
    assert result["repair_priority"] == "P0"
    assert "STALE_AUTHORITY" in result["findings"]


def test_privacy_risk_quarantines_even_if_otherwise_clean() -> None:
    record = clean_record()
    record["risk"] = {"privacy": ["case-specific material crossed public boundary"]}
    result = audit_repository_surface(record)
    assert result["admission"] == "QUARANTINED"
    assert result["repair_priority"] == "P0"


def test_private_repository_is_internal_only() -> None:
    record = clean_record()
    record["public"] = False
    result = audit_repository_surface(record)
    assert result["admission"] == "INTERNAL_ONLY"


def test_superseded_repository_cannot_be_current_public_proof() -> None:
    record = clean_record()
    record["lineage_state"] = "SUPERSEDED"
    result = audit_repository_surface(record)
    assert result["admission"] == "SUPERSEDED"


def test_duplicate_census_entries_fail_closed() -> None:
    payload = {
        "public_repositories": ["GlacierEQ/example", "GlacierEQ/example"],
        "defaults": {"public": True},
    }
    with pytest.raises(RepositorySurfaceError, match="duplicates"):
        compile_surface_report(payload)


def test_expected_public_count_is_enforced() -> None:
    payload = {
        "public_repositories": ["GlacierEQ/example"],
        "defaults": {"public": True},
    }
    with pytest.raises(RepositorySurfaceError, match="count mismatch"):
        compile_surface_report(payload, expected_public_count=2)


def test_first_public_estate_manifest_compiles_all_75() -> None:
    payload = json.loads(OBSERVATIONS.read_text(encoding="utf-8"))
    report = compile_surface_report(payload, expected_public_count=75)
    assert report["identity_coverage"] == {
        "public_repository_count": 75,
        "complete": True,
    }
    assert len(report["repositories"]) == 75
    assert len({item["repository"] for item in report["repositories"]}) == 75
    assert report["summary"]["xai_repair_count"] == 11
    assert report["summary"]["metadata_repair_count"] >= 5
    assert any(
        item["repository"] == "GlacierEQ/xai-colossus-2"
        and item["priority"] == "P0"
        for item in report["repair_queue"]
    )
    assert any(
        item["repository"] == "GlacierEQ/job-application"
        and item["priority"] == "P1"
        for item in report["metadata_cleanup_queue"]
    )


def test_first_public_estate_report_is_deterministic() -> None:
    payload = json.loads(OBSERVATIONS.read_text(encoding="utf-8"))
    first = compile_surface_report(payload, expected_public_count=75)
    second = compile_surface_report(payload, expected_public_count=75)
    assert first == second
    assert len(first["report_id"]) == 64
