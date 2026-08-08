from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = (
    ROOT
    / "manifests"
    / "application_intelligence"
    / "coreweave_reliability_lab_remediation.json"
)

EXPECTED_REPOSITORIES = {
    "GlacierEQ/coreweave-temporal-router",
    "GlacierEQ/coreweave-state-fusion",
    "GlacierEQ/coreweave-shadow-monitor",
    "GlacierEQ/coreweave-circuit-breaker",
    "GlacierEQ/coreweave-entropy-engine",
}


def load_ledger() -> dict:
    return json.loads(LEDGER.read_text(encoding="utf-8"))


def test_repairs_remain_below_tested_without_positive_receipts() -> None:
    ledger = load_ledger()
    assert ledger["promotion_state"] == "BLOCKED_BELOW_TESTED"
    repairs = ledger["repairs"]
    assert {row["repository"] for row in repairs} == EXPECTED_REPOSITORIES
    assert all(row["state"] == "OPEN_UNMERGED" for row in repairs)
    assert all(row["promotion_allowed"] is False for row in repairs)
    assert all(row["verification"]["runner_started"] is False for row in repairs)


def test_budget_block_is_distinct_from_missing_run() -> None:
    ledger = load_ledger()
    repairs = {row["repository"]: row for row in ledger["repairs"]}
    budget_blocked = EXPECTED_REPOSITORIES - {
        "GlacierEQ/coreweave-entropy-engine"
    }
    assert all(
        repairs[repo]["verification"]["gate"] == "ACTIONS_BUDGET"
        for repo in budget_blocked
    )
    entropy = repairs["GlacierEQ/coreweave-entropy-engine"]
    assert entropy["verification"]["gate"] == "NO_WORKFLOW_RUN_OBSERVED"
    assert entropy["verification"]["workflow_run_id"] is None


def test_governance_is_merged_but_repairs_are_not() -> None:
    ledger = load_ledger()
    governance = ledger["governance"]
    assert governance["result"] == "MERGED_PRIVATE_EXPERIMENT_GOVERNANCE"
    assert governance["exact_head_gates_passed"] == 6
    assert governance["exact_head_gates"] == 6
    assert ledger["next_gate"]["merge_before_gate"] is False
