from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DOSSIER = ROOT / "manifests" / "company_dossiers" / "additional_targets.json"
AUDIT = (
    ROOT
    / "manifests"
    / "application_intelligence"
    / "intel_npu_provenance_audit.json"
)


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def intel_company() -> dict[str, Any]:
    dossier = load(DOSSIER)
    return next(
        company
        for company in dossier["companies"]
        if company["company_id"] == "intel"
    )


def test_intel_repository_is_not_an_original_candidate() -> None:
    company = intel_company()
    assert company["track_state"] == "UPSTREAM_DERIVED_DELTA_AUDIT"
    private_repo = next(
        row
        for row in company["repositories"]
        if row[0] == "GlacierEQ/intel-npu-acceleration-library"
    )
    assert private_repo[2] == "AUDIT_UPSTREAM_DELTA"
    assert private_repo[3] == "private"
    assert private_repo[5] == "UPSTREAM_SHAPED"


def test_ahead_count_is_not_treated_as_originality() -> None:
    audit = load(AUDIT)
    graph = audit["upstream_graph"]
    assert graph["comparison_status"] == "diverged"
    assert graph["casey_side_ahead_by"] == 37
    assert graph["casey_side_behind_by"] == 2
    assert audit["decision"]["repo_level_original_accomplishment"] is False
    assert audit["truth_boundary"]["ahead_commit_count_claimed_as_originality"] is False


def test_candidate_sdpa_delta_remains_unverified() -> None:
    audit = load(AUDIT)
    decision = audit["decision"]
    assert decision["candidate_delta_donor_exists"] is True
    assert decision["candidate_delta_donor_verified"] is False
    assert decision["recruiter_admission_allowed"] is False
    assert audit["truth_boundary"]["candidate_sdpa_delta_claimed_as_verified"] is False
    assert audit["promotion_gate"]["requires"]


def test_imported_branch_merge_does_not_transfer_authorship() -> None:
    audit = load(AUDIT)
    boundary = audit["imported_history_boundary"]
    assert boundary["merge_import_example"] == (
        "e9c39900e8418b8e5fd1bc94e048555704f8929d"
    )
    assert audit["truth_boundary"]["upstream_merge_claimed_as_authorship"] is False
