import json

import pytest

from job_app_helix.restoration_strategy_router import RestorationRoutingError
from job_app_helix.restoration_workforce_cli import main as workforce_cli
from job_app_helix.restoration_workforce_intelligence import (
    MAKE_IT_HEAVY_DONOR,
    compile_staffed_restoration_decision,
    select_restoration_workforce,
)


def candidate(cid="restore", **overrides):
    row = {
        "candidate_id": cid,
        "title": cid,
        "repository": f"GlacierEQ/{cid}",
        "tier": "P1",
        "operator_impact": 9,
        "urgency": 8,
        "capability_gain": 9,
        "bottleneck_relief": 8,
        "recruiter_leverage": 9,
        "recovery_value": 9,
        "composition_gain": 9,
        "dependency_unlocking": 8,
        "success_likelihood": 9,
        "prior_gain_preservation": 9,
        "destructive_risk": 6,
        "blocker_cost": 2,
        "market_demand": 9,
        "differentiation": 9,
        "evidence_strength": 7,
        "strategic_fit": 10,
        "time_to_value": 8,
        "reversibility": 9,
        "estimated_effort": 1,
    }
    row.update(overrides)
    return row


def workers():
    return [
        {
            "role": "source_mapper",
            "capabilities": ["source_mapping", "proof_engineering"],
            "quality_score": 94,
            "benefit_score": 0.92,
            "unique_contribution": 0.95,
        },
        {
            "role": "adversarial_breaker",
            "capabilities": ["adversarial_validation", "proof_engineering"],
            "quality_score": 96,
            "benefit_score": 0.94,
            "unique_contribution": 0.90,
        },
        {
            "role": "systems_architect",
            "capabilities": ["systems_architecture", "innovation"],
            "quality_score": 95,
            "benefit_score": 0.93,
            "unique_contribution": 0.97,
        },
        {
            "role": "presentation_strategist",
            "capabilities": ["presentation_strategy"],
            "quality_score": 91,
            "benefit_score": 0.90,
            "unique_contribution": 0.88,
        },
    ]


def test_compounds_megamind_decision_with_full_capability_workforce():
    payload = {
        "candidates": [candidate()],
        "workers": workers(),
        "worker_budget": 4,
    }
    result = compile_staffed_restoration_decision(payload)

    assert result["schema"] == "glaciereq.job-restore.staffed-intelligence.v1"
    assert result["winner"]["candidate_id"] == "restore"
    assert result["workforce_plan"][0]["coverage_ratio"] == 1.0
    assert result["workforce_plan"][0]["uncovered_capabilities"] == []
    assert set(result["workforce_plan"][0]["selected_roles"]) == {
        "source_mapper",
        "adversarial_breaker",
        "systems_architect",
        "presentation_strategist",
    }
    assert result["workforce_donor"] == MAKE_IT_HEAVY_DONOR
    assert "minimax_regret" in result["mechanisms"]
    assert "exploration_exploitation" in result["mechanisms"]


def test_longitudinal_failures_can_demote_flashy_current_worker():
    task = candidate(
        recovery_value=0,
        destructive_risk=0,
        composition_gain=0,
        differentiation=0,
        recruiter_leverage=0,
        evidence_strength=9,
        required_capabilities=["proof_engineering"],
    )
    pool = [
        {
            "role": "flashy",
            "capabilities": ["proof_engineering"],
            "quality_score": 99,
            "benefit_score": 0.99,
            "unique_contribution": 0.99,
        },
        {
            "role": "reliable",
            "capabilities": ["proof_engineering"],
            "quality_score": 88,
            "benefit_score": 0.88,
            "unique_contribution": 0.88,
        },
    ]
    history = {
        "flashy": [
            {"runtime_status": "error", "performance_valid": False}
            for _ in range(4)
        ],
        "reliable": [
            {
                "quality_score": 90,
                "benefit_score": 0.90,
                "unique_contribution": 0.90,
                "runtime_status": "ok",
                "performance_valid": True,
            }
            for _ in range(4)
        ],
    }

    result = select_restoration_workforce(
        task, pool, worker_history=history, worker_budget=1
    )
    assert result["selected_roles"] == ["reliable"]
    assert result["signals"]["flashy"]["failure_penalty"] == 0.3


def test_observational_history_never_invents_causal_uplift():
    task = candidate(required_capabilities=["proof_engineering"])
    pool = [
        {
            "role": "proof_engineer",
            "capabilities": ["proof_engineering"],
            "quality_score": 90,
            "benefit_score": 0.9,
            "unique_contribution": 0.9,
        }
    ]
    history = {
        "proof_engineer": [
            {
                "quality_score": 92,
                "benefit_score": 0.91,
                "unique_contribution": 0.9,
                "runtime_status": "ok",
                "performance_valid": True,
            }
        ]
    }
    result = select_restoration_workforce(
        task, pool, worker_history=history, worker_budget=1
    )
    assert result["signals"]["proof_engineer"]["causal_bonus"] == 0.0


def test_missing_required_capability_is_observable_not_faked():
    task = candidate(required_capabilities=["rare_capability"])
    result = select_restoration_workforce(task, workers(), worker_budget=2)
    assert "rare_capability" in result["uncovered_capabilities"]
    assert result["coverage_ratio"] < 1.0


def test_mandatory_role_must_exist():
    with pytest.raises(RestorationRoutingError, match="mandatory worker roles"):
        select_restoration_workforce(
            candidate(), workers(), worker_budget=2, mandatory_roles=["missing_role"]
        )


def test_cli_writes_staffed_decision_receipt(tmp_path):
    source = tmp_path / "queue.json"
    output = tmp_path / "decision.json"
    source.write_text(
        json.dumps(
            {
                "candidates": [candidate()],
                "workers": workers(),
                "worker_budget": 4,
            }
        ),
        encoding="utf-8",
    )

    assert workforce_cli([str(source), "--output", str(output)]) == 0
    receipt = json.loads(output.read_text(encoding="utf-8"))
    assert receipt["schema"] == "glaciereq.job-restore.staffed-intelligence.v1"
    assert receipt["winner"]["candidate_id"] == "restore"
    assert receipt["workforce_plan"][0]["coverage_ratio"] == 1.0
