from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "manifests/application_intelligence/p0_real_implementation_surface_audit_2026-08-12.json"
QUEUE = ROOT / "manifests/application_intelligence/company_innovation_execution_queue.v1.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_real_surface_audit_covers_exact_p0_queue() -> None:
    audit = load(AUDIT)
    queue = load(QUEUE)
    assert audit["summary"]["count"] == queue["count"] == 25
    assert [item["company_id"] for item in audit["items"]] == [
        item["company_id"] for item in queue["queue"]
    ]
    assert [item["rank"] for item in audit["items"]] == list(range(1, 26))


def test_surface_counts_match_actual_architecture() -> None:
    audit = load(AUDIT)
    counts: dict[str, int] = {}
    for item in audit["items"]:
        state = item["surface_state"]
        counts[state] = counts.get(state, 0) + 1
    assert counts == {
        "DEDICATED_SCAFFOLD": 7,
        "DEDICATED_IMPLEMENTED_PROOF_PENDING": 2,
        "HELIX_REFERENCE_ONLY": 16,
    }
    assert audit["summary"]["dedicated_repository_count"] == 9
    assert audit["summary"]["promotion_valid_count"] == 0
    assert audit["summary"]["strict_built_right_count"] == 0
    assert audit["summary"]["gate"] == "FAIL"


def test_existing_vs_new_track_split_is_not_conflated() -> None:
    audit = load(AUDIT)
    deepened = {
        item["company_id"]
        for item in audit["items"]
        if item["track_action"] == "DEEPEN_EXISTING"
    }
    dedicated = {
        item["company_id"]
        for item in audit["items"]
        if item["dedicated_repository"] is not None
    }
    assert dedicated == deepened
    reference_only = {
        item["company_id"]
        for item in audit["items"]
        if item["surface_state"] == "HELIX_REFERENCE_ONLY"
    }
    admitted_new = {
        item["company_id"]
        for item in audit["items"]
        if item["track_action"] == "ADMIT_NET_NEW"
    }
    assert reference_only == admitted_new


def test_only_pinecone_and_supabase_are_bodybuilt() -> None:
    audit = load(AUDIT)
    implemented = {
        item["company_id"]
        for item in audit["items"]
        if item["surface_state"] == "DEDICATED_IMPLEMENTED_PROOF_PENDING"
    }
    assert implemented == {"pinecone", "supabase"}
    for item in audit["items"]:
        if item["company_id"] in implemented:
            assert item["exact_head_ci"]["exact_head"] == "PASS"
            assert "IMPLEMENTATION_PROOF_MISSING" in item["blockers"]
            assert item["promotion_eligible"] is False


def test_scaffolds_and_reference_only_surfaces_fail_closed() -> None:
    audit = load(AUDIT)
    for item in audit["items"]:
        if item["surface_state"] == "DEDICATED_SCAFFOLD":
            assert "SCAFFOLD_MARKERS_PRESENT" in item["blockers"]
            assert "IMPLEMENTATION_PROOF_MISSING" in item["blockers"]
        elif item["surface_state"] == "HELIX_REFERENCE_ONLY":
            assert item["dedicated_repository"] is None
            assert item["dedicated_head"] is None
            assert item["blockers"] == ["DEDICATED_IMPLEMENTATION_ABSENT"]
        assert item["built_right"] is False
        assert item["promotion_eligible"] is False


def test_legacy_receipts_cannot_be_treated_as_current_build_truth() -> None:
    audit = load(AUDIT)
    boundary = audit["truth_boundary"]
    assert boundary["legacy_wave_c_v1_promoted_claim_is_superseded_by_promotion_policy_v2"]
    assert boundary["legacy_25_of_25_reference_execution_receipt_is_not_real_surface_verification"]
    assert boundary["legacy_p0_semantic_audit_only_grades_helix_reference_functions"]
    stale_paths = {item["path"] for item in audit["conflicting_or_stale_artifacts"]}
    assert "excellence/framework/WAVE_C_INNOVATION_SCAFFOLD_MAP.md" in stale_paths
    assert "excellence/receipts/wave_c_latest.json" in stale_paths
