from job_app_helix.restoration_decision_intelligence import compile_intelligent_restoration_decision


def candidate(cid, **overrides):
    row = {"candidate_id":cid,"title":cid,"repository":f"GlacierEQ/{cid}","tier":"P1","operator_impact":8,"urgency":8,"capability_gain":8,"bottleneck_relief":8,"recruiter_leverage":8,"recovery_value":8,"composition_gain":8,"dependency_unlocking":8,"success_likelihood":8,"prior_gain_preservation":9,"destructive_risk":2,"blocker_cost":2,"market_demand":5,"differentiation":5,"evidence_strength":5,"strategic_fit":5,"time_to_value":5,"reversibility":8,"estimated_effort":1}
    row.update(overrides); return row


def test_recruiter_demand_can_break_old_utility_tie():
    wanted = candidate("wanted", market_demand=10, differentiation=10, recruiter_leverage=10)
    ordinary = candidate("ordinary")
    result = compile_intelligent_restoration_decision({"candidates":[ordinary,wanted]})
    assert result["winner"]["candidate_id"] == "wanted"
    assert result["schema"].endswith("v2")
    assert "minimax_regret" in result["mechanisms"]


def test_priority_precedence_survives_scenario_intelligence():
    p0 = candidate("p0", tier="P0", market_demand=1, recruiter_leverage=1)
    p1 = candidate("p1", market_demand=10, differentiation=10, recruiter_leverage=10)
    assert compile_intelligent_restoration_decision({"candidates":[p1,p0]})["winner"]["candidate_id"] == "p0"


def test_dependency_and_budget_plan_compose_work():
    foundation = candidate("foundation", estimated_effort=1, market_demand=8)
    multiplier = candidate("multiplier", dependencies=["foundation"], estimated_effort=1, composition_gain=10)
    result = compile_intelligent_restoration_decision({"candidates":[foundation,multiplier],"effort_budget":2})
    assert result["plan"]["selected_ids"] == ["foundation", "multiplier"]
    assert result["donor"]["commit"] == "ce8f255031d18beb21a0dfee58ec839d40ef06a0"
