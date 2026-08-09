from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECEIPT = ROOT / "status" / "public-repository-governance-wave-2026-08-08.json"
SPINE = ROOT / "manifests" / "library_priority_spine.json"

EXPECTED_ALPHA_OMEGA = {
    "GlacierEQ/xai-colossus-cooling-alpha": "bb96e13e23839e93016d8606984a8d81c61d340d",
    "GlacierEQ/xai-colossus-cooling-omega": "61ae6c24a997316bd77137872936412e795c9019",
    "GlacierEQ/xai-colossus-energy-alpha": "ab76336ee12de0d3c7ee765332c06b0e42381fe6",
    "GlacierEQ/xai-colossus-energy-omega": "24e3cc3e144e7acc64b54559ecabf39f32edb59f",
}
PRO_CODE_HEAD = "c9aa2faa0dcede7d6b7e7e6891b7930ee87040ab"
RECEIPT_PATH = "status/public-repository-governance-wave-2026-08-08.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_post_wave_receipt_binds_current_promoted_heads() -> None:
    receipt = load(RECEIPT)
    observed = {
        item["repository"]: item["canonical_head"]
        for item in receipt["alpha_omega_admission"]["repositories"]
    }
    assert receipt["alpha_omega_admission"]["state"] == "COMPLETE"
    assert receipt["alpha_omega_admission"]["count"] == 4
    assert observed == EXPECTED_ALPHA_OMEGA

    lineage = receipt["colossal_cooling_legacy_lineage"]
    assert lineage["legacy_pr_state"] == "CLOSED_UNMERGED"
    assert lineage["unique_files"] == 9
    assert lineage["capability_donor_candidates"] == 6
    assert lineage["historical_or_aspirational_documents"] == 3

    pro_code = receipt["pro_code_authority"]
    assert pro_code["canonical_head"] == PRO_CODE_HEAD
    assert pro_code["state"] == "LOCAL_OPERABLE"
    assert pro_code["evidence_level"] == "TEST"
    assert pro_code["promotion_gates"] == [
        "Pro-Code native verification: PASS",
        "Helix Verify: PASS",
        "Nervous System Contract: PASS",
    ]


def test_historical_unknowns_are_resolved_without_visibility_overclaim() -> None:
    receipt = load(RECEIPT)
    resolved = receipt["historical_unassessed_resolution"]
    assert resolved["historical_unassessed_count"] == 58
    assert resolved["decision_count"] == 58
    assert resolved["unassessed_remaining_after_decisions"] == 0
    assert resolved["decision_counts"] == {
        "ADMIT": 2,
        "REPAIR_REQUIRED": 52,
        "QUARANTINED": 3,
        "REFERENCE": 1,
    }

    boundary = receipt["privacy_and_visibility_boundary"]
    assert boundary["compiler_quarantine_changes_repository_visibility"] is False
    assert boundary["repository_visibility_mutation_performed"] is False
    assert boundary["public_legal_or_private_content_projected_as_recruiter_capability"] is False


def test_priority_spine_points_to_current_pro_code_authority_without_rewriting_july_receipt() -> None:
    spine = load(SPINE)
    assert spine["latest_execution_receipt"] == "status/priority-spine-wave-2-2026-07-31.json"
    pro_code = next(
        item for item in spine["repositories"] if item["repository"] == "GlacierEQ/pro-code"
    )
    assert pro_code["authority_state"] == "CURRENT"
    assert pro_code["authority_head"] == PRO_CODE_HEAD
    assert pro_code["authority_receipt"] == RECEIPT_PATH
    assert pro_code["readme_state"] == "LOCAL_OPERABLE_TRUTH_BOUNDARY_MERGED"
    assert pro_code["proof_state"] == (
        "LOCAL_NEXUS_AUTOMATION_NATIVE_CI_HELIX_AND_NERVOUS_SYSTEM_VERIFIED"
    )
