"""Robust JOB_RESTORE decision intelligence composed from Megamind v2.

Adds scenario analysis, minimax regret, pairwise outranking, dependency
feasibility, and budgeted portfolio selection above the existing Helix
priority/Pareto router. The existing router remains available as a stable
fallback and compatibility surface.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from statistics import mean
from typing import Any, Mapping

from .restoration_strategy_router import (
    RestorationCandidate,
    RestorationRoutingError,
    rank_restoration_queue,
)

MEGAMIND_V2_DONOR = {
    "repository": "GlacierEQ/megamind",
    "commit": "ce8f255031d18beb21a0dfee58ec839d40ef06a0",
    "path": "src/megamind/decision_intelligence.py",
    "blob_sha": "8c656b993b9238d71caaca187142103e76260839",
}

SCENARIOS = {
    "recruiter_demand": {
        "operator_impact": 1.1, "capability_gain": 1.2, "recruiter_leverage": 1.8,
        "market_demand": 1.8, "differentiation": 1.5, "evidence_strength": 1.3,
        "strategic_fit": 1.2, "time_to_value": 1.0, "destructive_risk": -1.2,
        "blocker_cost": -0.8,
    },
    "capability_compounding": {
        "operator_impact": 1.2, "capability_gain": 1.8, "composition_gain": 1.6,
        "dependency_unlocking": 1.5, "differentiation": 1.2, "evidence_strength": 1.0,
        "strategic_fit": 1.3, "reversibility": 0.8, "destructive_risk": -1.3,
        "blocker_cost": -0.8,
    },
    "recovery_resilience": {
        "operator_impact": 1.3, "recovery_value": 1.8, "prior_gain_preservation": 1.7,
        "success_likelihood": 1.4, "evidence_strength": 1.3, "reversibility": 1.2,
        "time_to_value": 0.8, "destructive_risk": -1.8, "blocker_cost": -1.2,
    },
}

@dataclass(frozen=True)
class IntelligentRestorationCandidate:
    base: RestorationCandidate
    market_demand: float = 5.0
    differentiation: float = 5.0
    evidence_strength: float = 5.0
    strategic_fit: float = 5.0
    time_to_value: float = 5.0
    reversibility: float = 5.0
    estimated_effort: float = 1.0
    dependencies: tuple[str, ...] = ()
    conflicts: tuple[str, ...] = ()

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "IntelligentRestorationCandidate":
        base = RestorationCandidate.from_mapping(value)
        extras: dict[str, float] = {}
        for field in ("market_demand", "differentiation", "evidence_strength", "strategic_fit", "time_to_value", "reversibility"):
            raw = value.get(field, 5.0)
            if isinstance(raw, bool) or not isinstance(raw, (int, float)):
                raise RestorationRoutingError(f"{field} must be numeric")
            score = float(raw)
            if not 0 <= score <= 10:
                raise RestorationRoutingError(f"{field} must be within [0, 10]")
            extras[field] = score
        effort = float(value.get("estimated_effort", 1.0))
        if not 0 < effort <= 100:
            raise RestorationRoutingError("estimated_effort must be > 0 and <= 100")
        dependencies = tuple(str(x) for x in value.get("dependencies", ()))
        conflicts = tuple(str(x) for x in value.get("conflicts", ()))
        if base.candidate_id in dependencies or base.candidate_id in conflicts:
            raise RestorationRoutingError("candidate cannot depend on or conflict with itself")
        return cls(base=base, estimated_effort=effort, dependencies=dependencies, conflicts=conflicts, **extras)

    def metric(self, name: str) -> float:
        return float(getattr(self.base, name) if hasattr(self.base, name) else getattr(self, name))


def _scenario_score(candidate: IntelligentRestorationCandidate, weights: Mapping[str, float]) -> float:
    return sum(candidate.metric(field) * weight for field, weight in weights.items())


def rank_intelligent_restoration_queue(raw_candidates: list[Mapping[str, Any]], *, completed: tuple[str, ...] = ()) -> list[dict[str, Any]]:
    candidates = [IntelligentRestorationCandidate.from_mapping(row) for row in raw_candidates]
    if not candidates:
        raise RestorationRoutingError("at least one restoration candidate is required")
    ids = [row.base.candidate_id for row in candidates]
    if len(ids) != len(set(ids)):
        raise RestorationRoutingError("candidate_id values must be unique")
    known = set(ids) | set(completed)
    for row in candidates:
        unknown = set(row.dependencies) - known
        if unknown:
            raise RestorationRoutingError(f"{row.base.candidate_id} has unknown dependencies: {sorted(unknown)}")
    completed_set = set(completed)
    feasible = [row for row in candidates if not row.base.blocked and set(row.dependencies).issubset(completed_set)]
    if not feasible:
        raise RestorationRoutingError("no unblocked candidate has satisfied dependencies")
    tier_rank = {"P0": 0, "P1": 1, "P2": 2, "P3": 3, "P4": 4}
    best_tier = min(tier_rank[row.base.tier] for row in feasible)
    active = [row for row in feasible if tier_rank[row.base.tier] == best_tier]
    scores = {row.base.candidate_id: {name: _scenario_score(row, weights) for name, weights in SCENARIOS.items()} for row in active}
    best = {name: max(row[name] for row in scores.values()) for name in SCENARIOS}
    ranked: list[dict[str, Any]] = []
    for row in candidates:
        cid = row.base.candidate_id
        deps_ok = set(row.dependencies).issubset(completed_set)
        if row in active:
            scenario = scores[cid]
            regret = max(best[name] - scenario[name] for name in SCENARIOS)
            wins = sum(
                sum(scenario[name] > scores[other.base.candidate_id][name] for name in SCENARIOS) >= 2
                for other in active if other.base.candidate_id != cid
            )
            avg = mean(scenario.values())
            robust = avg - 0.35 * regret + 0.20 * wins
            reasons = ["active highest-priority executable tier", f"worst-case regret={regret:.3f}", f"pairwise outranking wins={wins}"]
        else:
            scenario = {name: _scenario_score(row, weights) for name, weights in SCENARIOS.items()}
            avg, regret, wins, robust = mean(scenario.values()), 0.0, 0, -10000.0
            reasons = ["blocked" if row.base.blocked else "dependencies unsatisfied" if not deps_ok else f"deferred behind P{best_tier}"]
        ranked.append({
            "candidate_id": cid, "title": row.base.title, "repository": row.base.repository,
            "tier": row.base.tier, "robust_score": round(robust, 4), "mean_utility": round(avg, 4),
            "worst_case_regret": round(regret, 4), "outranking_wins": wins,
            "scenario_scores": {k: round(v, 4) for k, v in scenario.items()},
            "dependencies_satisfied": deps_ok, "blocked": row.base.blocked, "reasons": reasons,
        })
    ranked.sort(key=lambda item: (-item["robust_score"], item["candidate_id"]))
    for index, item in enumerate(ranked, 1): item["rank"] = index
    return ranked


def compile_intelligent_restoration_decision(payload: Mapping[str, Any]) -> dict[str, Any]:
    raw = payload.get("candidates")
    if not isinstance(raw, list):
        raise RestorationRoutingError("payload.candidates must be a list")
    completed = tuple(str(x) for x in payload.get("completed", ()))
    ranking = rank_intelligent_restoration_queue(raw, completed=completed)
    result: dict[str, Any] = {
        "schema": "glaciereq.job-restore.megamind-routing.v2",
        "winner": ranking[0], "ranking": ranking,
        "mechanisms": ["priority_precedence", "scenario_analysis", "minimax_regret", "pairwise_outranking", "dependency_feasibility"],
        "donor": dict(MEGAMIND_V2_DONOR),
        "fallback": {"schema": "glaciereq.job-restore.megamind-routing.v1", "winner": rank_restoration_queue(raw)[0].candidate_id},
    }
    if "effort_budget" in payload:
        budget = float(payload["effort_budget"])
        if budget <= 0: raise RestorationRoutingError("effort_budget must be positive")
        pool = [IntelligentRestorationCandidate.from_mapping(row) for row in raw]
        selected: list[str] = []; spent = 0.0
        while True:
            eligible = [row for row in pool if row.base.candidate_id not in selected and not row.base.blocked and set(row.dependencies).issubset(set(completed) | set(selected)) and row.estimated_effort + spent <= budget and not (set(row.conflicts) & set(selected))]
            if not eligible: break
            eligible_raw = [next(item for item in raw if item["candidate_id"] == row.base.candidate_id) for row in eligible]
            winner = rank_intelligent_restoration_queue(eligible_raw, completed=tuple(set(completed) | set(selected)))[0]["candidate_id"]
            chosen = next(row for row in eligible if row.base.candidate_id == winner)
            selected.append(winner); spent += chosen.estimated_effort
        result["plan"] = {"selected_ids": selected, "effort_budget": budget, "effort_spent": round(spent, 4), "effort_remaining": round(budget-spent, 4)}
    return result
