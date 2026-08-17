from __future__ import annotations

import json
from pathlib import Path

import pytest

from job_app_helix.restoration_strategy_cli import main as route_main
from job_app_helix.restoration_strategy_router import (
    MEGAMIND_DONOR,
    RestorationRoutingError,
    compile_restoration_decision,
)


def candidate(candidate_id: str, tier: str = "P1", **overrides):
    value = {
        "candidate_id": candidate_id,
        "title": candidate_id.replace("-", " ").title(),
        "repository": f"GlacierEQ/{candidate_id}",
        "tier": tier,
        "operator_impact": 7,
        "urgency": 7,
        "capability_gain": 7,
        "bottleneck_relief": 7,
        "recruiter_leverage": 7,
        "recovery_value": 7,
        "composition_gain": 7,
        "dependency_unlocking": 7,
        "success_likelihood": 8,
        "prior_gain_preservation": 9,
        "destructive_risk": 2,
        "blocker_cost": 2,
    }
    value.update(overrides)
    return value


def test_p0_precedes_higher_scoring_p1():
    p0 = candidate("production-blocker", "P0", capability_gain=4, recruiter_leverage=3)
    p1 = candidate(
        "shiny-p1",
        "P1",
        operator_impact=10,
        capability_gain=10,
        recruiter_leverage=10,
        composition_gain=10,
        destructive_risk=0,
        blocker_cost=0,
    )
    result = compile_restoration_decision({"candidates": [p1, p0]})
    assert result["winner"]["candidate_id"] == "production-blocker"
    assert result["winner"]["tier"] == "P0"


def test_blocked_candidate_never_wins_and_remains_visible():
    blocked = candidate(
        "blocked-giant",
        "P0",
        blocked=True,
        blocker="connector unavailable",
        capability_gain=10,
    )
    executable = candidate("executable-p1", "P1")
    result = compile_restoration_decision({"candidates": [blocked, executable]})
    assert result["winner"]["candidate_id"] == "executable-p1"
    blocked_row = next(
        row for row in result["ranking"] if row["candidate_id"] == "blocked-giant"
    )
    assert blocked_row["blocked"] is True
    assert "connector unavailable" in blocked_row["reasons"][0]


def test_p4_cannot_displace_executable_product_work():
    product = candidate("recruiter-feature", "P2", capability_gain=5, recruiter_leverage=5)
    governance = candidate(
        "perfect-governance",
        "P4",
        operator_impact=10,
        urgency=10,
        capability_gain=10,
        bottleneck_relief=10,
        recruiter_leverage=10,
        recovery_value=10,
        composition_gain=10,
        dependency_unlocking=10,
        success_likelihood=10,
        prior_gain_preservation=10,
        destructive_risk=0,
        blocker_cost=0,
    )
    result = compile_restoration_decision({"candidates": [governance, product]})
    assert result["winner"]["candidate_id"] == "recruiter-feature"
    governance_row = next(
        row for row in result["ranking"] if row["candidate_id"] == "perfect-governance"
    )
    assert governance_row["reasons"] == ["deferred behind executable P2 work"]


def test_pareto_dominance_breaks_same_tier_candidates():
    weak = candidate("weak", capability_gain=6, recruiter_leverage=6, destructive_risk=3)
    strong = candidate("strong", capability_gain=8, recruiter_leverage=8, destructive_risk=1)
    result = compile_restoration_decision({"candidates": [weak, strong]})
    assert result["winner"]["candidate_id"] == "strong"
    weak_row = next(row for row in result["ranking"] if row["candidate_id"] == "weak")
    assert weak_row["dominated_by"] == ["strong"]
    assert weak_row["pareto_front"] is False


def test_low_execution_confidence_penalizes_speculative_candidate():
    speculative = candidate(
        "speculative",
        capability_gain=10,
        recruiter_leverage=10,
        composition_gain=10,
        success_likelihood=1,
    )
    reliable = candidate(
        "reliable",
        capability_gain=8,
        recruiter_leverage=8,
        composition_gain=8,
        success_likelihood=10,
    )
    result = compile_restoration_decision({"candidates": [speculative, reliable]})
    assert result["winner"]["candidate_id"] == "reliable"


def test_receipt_carries_exact_megamind_lineage_and_mechanisms():
    result = compile_restoration_decision({"candidates": [candidate("one")]})
    assert result["donor"] == MEGAMIND_DONOR
    assert result["donor"]["commit"] == "2d56b95621fbf9d20012438d336bd53b1f4026e9"
    assert result["mechanisms"] == [
        "priority_tier",
        "pareto_dominance",
        "confidence_adjusted_utility",
    ]


def test_duplicate_and_all_blocked_queues_fail_closed():
    with pytest.raises(RestorationRoutingError, match="candidate_id values must be unique"):
        compile_restoration_decision({"candidates": [candidate("dup"), candidate("dup")]})
    with pytest.raises(RestorationRoutingError, match="all restoration candidates are blocked"):
        compile_restoration_decision(
            {"candidates": [candidate("blocked", blocked=True, blocker="real blocker")]}
        )


def test_cli_writes_machine_readable_decision(tmp_path: Path):
    source = tmp_path / "queue.json"
    output = tmp_path / "decision" / "receipt.json"
    source.write_text(json.dumps({"candidates": [candidate("route-me")]}), encoding="utf-8")
    assert route_main([str(source), "--output", str(output)]) == 0
    receipt = json.loads(output.read_text(encoding="utf-8"))
    assert receipt["winner"]["candidate_id"] == "route-me"
    assert receipt["schema"] == "glaciereq.job-restore.megamind-routing.v1"
