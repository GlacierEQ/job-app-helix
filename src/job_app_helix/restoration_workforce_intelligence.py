"""Evidence-aware workforce composition for intelligent JOB_RESTORE decisions.

This layer compounds Megamind v2 strategy selection with Make-It-Heavy's
longitudinal exploration/exploitation worker selection. It does not treat
historical correlation as causal evidence: causal uplift is used only when an
explicit marginal-system-value or outcome-leverage observation exists.
"""
from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from statistics import mean
from typing import Any

from .restoration_decision_intelligence import compile_intelligent_restoration_decision
from .restoration_strategy_router import RestorationRoutingError

MAKE_IT_HEAVY_DONOR = {
    "repository": "GlacierEQ/make-it-heavy",
    "commit": "47d11a98a1c15c7be714a46877175d0efb34ec73",
    "path": "worker_portfolio_optimizer.py",
    "blob_sha": "46b490c30e60768c6287a0b9101b4af0d773ed03",
}

CAPABILITY_POLICY = (
    ("recovery_value", 7.0, "source_mapping"),
    ("destructive_risk", 5.0, "adversarial_validation"),
    ("composition_gain", 7.0, "systems_architecture"),
    ("differentiation", 7.0, "innovation"),
    ("recruiter_leverage", 7.0, "presentation_strategy"),
)


def _finite(value: Any, default: float = 0.0) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return default
    return numeric if math.isfinite(numeric) else default


def _observational_value(row: Mapping[str, Any]) -> float:
    quality = max(0.0, min(1.0, _finite(row.get("quality_score")) / 100.0))
    benefit = max(0.0, min(1.0, _finite(row.get("benefit_score"))))
    unique = max(0.0, min(1.0, _finite(row.get("unique_contribution"), 0.5)))
    return 0.45 * benefit + 0.40 * quality + 0.15 * unique


def _causal_signal(history: Sequence[Mapping[str, Any]]) -> float:
    values: list[float] = []
    for row in history:
        marginal = row.get("marginal_system_value")
        leverage = row.get("outcome_leverage")
        if marginal is None and leverage is None:
            continue
        marginal_value = (
            max(-1.0, min(1.0, _finite(marginal))) if marginal is not None else 0.0
        )
        leverage_value = (
            max(0.0, min(1.0, _finite(leverage))) if leverage is not None else 0.0
        )
        values.append(0.65 * marginal_value + 0.35 * leverage_value)
    return mean(values) if values else 0.0


def _trend(history: Sequence[Mapping[str, Any]]) -> float:
    values = [_observational_value(row) for row in history]
    if len(values) < 2:
        return 0.0
    newest = mean(values[: min(2, len(values))])
    oldest = mean(values[-min(2, len(values)) :])
    return max(-0.20, min(0.20, newest - oldest))


@dataclass(frozen=True)
class WorkforceSignal:
    role: str
    capabilities: tuple[str, ...]
    current_value: float
    historical_value: float
    exploration_bonus: float
    trend_bonus: float
    failure_penalty: float
    causal_bonus: float
    portfolio_score: float
    history_samples: int


def _worker_signal(
    worker: Mapping[str, Any],
    history: Sequence[Mapping[str, Any]],
    *,
    total_history_samples: int,
) -> WorkforceSignal:
    role = str(worker.get("role", "")).strip()
    if not role:
        raise RestorationRoutingError("worker role is required")
    capabilities = tuple(dict.fromkeys(str(item) for item in worker.get("capabilities", ())))
    if not capabilities:
        raise RestorationRoutingError(f"worker {role} must declare at least one capability")

    current = _observational_value(worker)
    valid_history = [
        row
        for row in history
        if str(row.get("runtime_status", "model_inference")) not in {"timeout", "error"}
        and bool(row.get("performance_valid", True))
    ]
    historical_values = [_observational_value(row) for row in valid_history]
    historical = mean(historical_values) if historical_values else current
    sample_count = len(valid_history)
    exploration = min(
        0.22,
        0.12 * math.sqrt(math.log(max(2, total_history_samples + 1)) / (sample_count + 1)),
    )
    trend_bonus = 0.35 * _trend(valid_history)
    failed = sum(
        1
        for row in history
        if str(row.get("runtime_status", "")) in {"timeout", "error"}
        or row.get("performance_valid") is False
    )
    failure_penalty = min(0.30, 0.08 * failed)
    causal_bonus = 0.18 * _causal_signal(valid_history)
    score = 0.50 * current + 0.34 * historical + exploration + trend_bonus + causal_bonus
    score -= failure_penalty
    return WorkforceSignal(
        role=role,
        capabilities=capabilities,
        current_value=round(current, 6),
        historical_value=round(historical, 6),
        exploration_bonus=round(exploration, 6),
        trend_bonus=round(trend_bonus, 6),
        failure_penalty=round(failure_penalty, 6),
        causal_bonus=round(causal_bonus, 6),
        portfolio_score=round(score, 6),
        history_samples=sample_count,
    )


def _required_capabilities(candidate: Mapping[str, Any]) -> tuple[str, ...]:
    required = list(
        dict.fromkeys(str(item) for item in candidate.get("required_capabilities", ()))
    )
    for field, threshold, capability in CAPABILITY_POLICY:
        if _finite(candidate.get(field)) >= threshold and capability not in required:
            required.append(capability)
    if (
        _finite(candidate.get("evidence_strength"), 5.0) < 8.0
        and "proof_engineering" not in required
    ):
        required.append("proof_engineering")
    return tuple(required)


def select_restoration_workforce(
    candidate: Mapping[str, Any],
    workers: Sequence[Mapping[str, Any]],
    *,
    worker_history: Mapping[str, Sequence[Mapping[str, Any]]] | None = None,
    worker_budget: int = 4,
    mandatory_roles: Sequence[str] = (),
) -> dict[str, Any]:
    """Select a compact worker team using evidence and marginal capability coverage."""
    if worker_budget <= 0:
        raise RestorationRoutingError("worker_budget must be positive")
    roles = [str(worker.get("role", "")).strip() for worker in workers]
    if any(not role for role in roles):
        raise RestorationRoutingError("every worker must have a role")
    if len(set(roles)) != len(roles):
        raise RestorationRoutingError("worker roles must be unique")
    if worker_budget > len(workers):
        raise RestorationRoutingError("worker_budget exceeds configured workers")
    missing_mandatory = set(mandatory_roles) - set(roles)
    if missing_mandatory:
        raise RestorationRoutingError(
            f"mandatory worker roles are not configured: {sorted(missing_mandatory)}"
        )

    history = worker_history or {}
    total_history = sum(len(rows) for rows in history.values())
    signals = {
        str(worker["role"]): _worker_signal(
            worker,
            tuple(history.get(str(worker["role"]), ())),
            total_history_samples=total_history,
        )
        for worker in workers
    }
    required = _required_capabilities(candidate)
    selected: list[str] = []
    covered: set[str] = set()

    for role in mandatory_roles:
        selected.append(role)
        covered.update(signals[role].capabilities)

    while len(selected) < worker_budget:
        remaining = [role for role in roles if role not in selected]
        if not remaining:
            break

        def marginal_value(role: str) -> tuple[float, float, float, str]:
            signal = signals[role]
            newly_covered = set(signal.capabilities) & (set(required) - covered)
            coverage_gain = len(newly_covered) / max(1, len(required))
            # Coverage dominates once a task has an unmet requirement; longitudinal
            # evidence then breaks ties without suppressing useful exploration.
            combined = 1.35 * coverage_gain + signal.portfolio_score
            return combined, coverage_gain, signal.causal_bonus, role

        winner = max(remaining, key=marginal_value)
        selected.append(winner)
        covered.update(signals[winner].capabilities)
        if set(required).issubset(covered):
            # Once all required capabilities are covered, do not spend the full
            # budget merely because capacity exists. Add another worker only when
            # it has strong longitudinal value or explicit causal uplift.
            remaining = [role for role in roles if role not in selected]
            if not remaining:
                break
            best_extra = max(remaining, key=lambda role: signals[role].portfolio_score)
            if (
                signals[best_extra].portfolio_score < 0.82
                and signals[best_extra].causal_bonus <= 0
            ):
                break

    uncovered = sorted(set(required) - covered)
    return {
        "candidate_id": str(candidate["candidate_id"]),
        "required_capabilities": list(required),
        "selected_roles": selected,
        "covered_capabilities": sorted(set(required) & covered),
        "uncovered_capabilities": uncovered,
        "coverage_ratio": round(
            1.0 if not required else (len(set(required) & covered) / len(required)), 6
        ),
        "signals": {
            role: {
                "capabilities": list(signal.capabilities),
                "current_value": signal.current_value,
                "historical_value": signal.historical_value,
                "exploration_bonus": signal.exploration_bonus,
                "trend_bonus": signal.trend_bonus,
                "failure_penalty": signal.failure_penalty,
                "causal_bonus": signal.causal_bonus,
                "portfolio_score": signal.portfolio_score,
                "history_samples": signal.history_samples,
            }
            for role, signal in sorted(signals.items())
        },
    }


def compile_staffed_restoration_decision(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Rank restoration work with Megamind v2, then staff its executable plan."""
    decision = compile_intelligent_restoration_decision(payload)
    workers = payload.get("workers")
    if workers is None:
        return decision
    if not isinstance(workers, list) or not workers:
        raise RestorationRoutingError("payload.workers must be a non-empty list when provided")
    worker_history = payload.get("worker_history", {})
    if not isinstance(worker_history, Mapping):
        raise RestorationRoutingError("payload.worker_history must be an object")
    worker_budget = int(payload.get("worker_budget", min(4, len(workers))))
    mandatory_roles = tuple(str(item) for item in payload.get("mandatory_roles", ()))

    candidates = {
        str(row["candidate_id"]): row for row in payload.get("candidates", ())
    }
    selected_ids = decision.get("plan", {}).get(
        "selected_ids", [decision["winner"]["candidate_id"]]
    )
    workforce = []
    for candidate_id in selected_ids:
        workforce.append(
            select_restoration_workforce(
                candidates[candidate_id],
                workers,
                worker_history=worker_history,
                worker_budget=worker_budget,
                mandatory_roles=mandatory_roles,
            )
        )
    decision["schema"] = "glaciereq.job-restore.staffed-intelligence.v1"
    decision["workforce_plan"] = workforce
    decision["workforce_donor"] = dict(MAKE_IT_HEAVY_DONOR)
    decision["mechanisms"] = [
        *decision["mechanisms"],
        "longitudinal_worker_value",
        "exploration_exploitation",
        "marginal_capability_coverage",
        "explicit_causal_uplift_only",
    ]
    return decision
