from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = (
    ROOT
    / "manifests/application_intelligence/p0_real_implementation_surface_audit_2026-08-13.json"
)
QUEUE = ROOT / "manifests/application_intelligence/p0_fine_tune_execution_queue.v1.json"
ORIGINAL_QUEUE = (
    ROOT
    / "manifests/application_intelligence/company_innovation_execution_queue.v1.json"
)


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_current_maturity_accounts_for_all_p0_tracks() -> None:
    audit = load(AUDIT)
    assert audit["summary"] == {
        "count": 25,
        "dedicated_implementation_count": 9,
        "terminal_crystallized_count": 4,
        "implemented_evidence_adapter_count": 3,
        "implemented_live_integration_count": 1,
        "implemented_normalized_input_count": 1,
        "helix_reference_only_count": 16,
        "dedicated_scaffold_count": 0,
        "build_surface_coverage_pct": 36.0,
        "terminal_coverage_pct": 16.0,
    }
    accounted = (
        len(audit["terminal_crystallized"])
        + len(audit["implemented_nonterminal"])
        + len(audit["reference_only"])
    )
    assert accounted == 25


def test_yesterdays_scaffold_snapshot_is_explicitly_superseded() -> None:
    audit = load(AUDIT)
    assert audit["supersedes"].endswith(
        "p0_real_implementation_surface_audit_2026-08-12.json"
    )
    assert audit["truth_boundary"]["historical_audits_are_not_live_state"] is True
    assert audit["summary"]["dedicated_scaffold_count"] == 0


def test_terminal_state_requires_completion_receipt() -> None:
    audit = load(AUDIT)
    terminal = {item["company_id"] for item in audit["terminal_crystallized"]}
    assert terminal == {"cursor", "cognition", "crusoe", "pinecone"}
    for item in audit["terminal_crystallized"]:
        assert item["state"] == "TERMINAL_CRYSTALLIZED"
        assert item["completion_receipt"] == "machine/crystallization/completion-receipt.json"
        assert item["repository"].startswith("GlacierEQ/")
        assert len(item["repo_head"]) == 40


def test_nonterminal_implementations_keep_exact_next_gate() -> None:
    audit = load(AUDIT)
    states = {item["company_id"]: item["state"] for item in audit["implemented_nonterminal"]}
    assert states == {
        "fireworks_ai": "IMPLEMENTED_EVIDENCE_ADAPTER",
        "lambda": "IMPLEMENTED_EVIDENCE_ADAPTER",
        "mongodb": "IMPLEMENTED_EVIDENCE_ADAPTER",
        "supabase": "IMPLEMENTED_LIVE_INTEGRATION",
        "together_ai": "IMPLEMENTED_NORMALIZED_INPUT",
    }
    assert all(item["next_gate"] for item in audit["implemented_nonterminal"])


def test_remaining_build_queue_equals_reference_only_set() -> None:
    audit = load(AUDIT)
    queue = load(QUEUE)
    reference_only = {item["company_id"] for item in audit["reference_only"]}
    queued = {item["company_id"] for item in queue["queue"]}
    assert queue["count"] == 16
    assert queued == reference_only
    assert [item["priority"] for item in queue["queue"]] == list(range(1, 17))


def test_remaining_builds_are_real_specific_and_donor_bound() -> None:
    queue = load(QUEUE)
    targets = [item["target_repository"] for item in queue["queue"]]
    assert len(targets) == len(set(targets)) == 16
    for item in queue["queue"]:
        assert item["next_action"] == "BUILD_DEDICATED_MECHANISM"
        assert item["target_repository"].startswith("GlacierEQ/")
        assert item["donors"]
        assert item["smallest_real_slice"]
        assert item["proof_gate"]


def test_current_audit_preserves_original_p0_membership() -> None:
    audit = load(AUDIT)
    original = load(ORIGINAL_QUEUE)
    current_ids = {
        *(item["company_id"] for item in audit["terminal_crystallized"]),
        *(item["company_id"] for item in audit["implemented_nonterminal"]),
        *(item["company_id"] for item in audit["reference_only"]),
    }
    assert current_ids == {item["company_id"] for item in original["queue"]}
