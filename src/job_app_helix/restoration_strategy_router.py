"""Priority-tier and Pareto restoration routing composed from Megamind.

This module adapts the proven GlacierEQ/megamind strategy tournament to Helix
restoration queues while keeping the donor lineage explicit and stable.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass
from math import isfinite
from typing import Any

MEGAMIND_DONOR = {
    "repository": "GlacierEQ/megamind",
    "commit": "2d56b95621fbf9d20012438d336bd53b1f4026e9",
    "path": "src/megamind/strategy_tournament.py",
    "blob_sha": "33b40ae0c38c3c9fab433ec12cf0bdc2b6c2f40d",
}

BENEFIT_FIELDS = (
    "operator_impact",
    "urgency",
    "capability_gain",
    "bottleneck_relief",
    "recruiter_leverage",
    "recovery_value",
    "composition_gain",
    "dependency_unlocking",
    "success_likelihood",
    "prior_gain_preservation",
)
COST_FIELDS = ("destructive_risk", "blocker_cost")
ALL_FIELDS = BENEFIT_FIELDS + COST_FIELDS
TIERS = {"P0": 0, "P1": 1, "P2": 2, "P3": 3, "P4": 4}

DEFAULT_WEIGHTS = {
    "operator_impact": 1.40,
    "urgency": 1.15,
    "capability_gain": 1.50,
    "bottleneck_relief": 1.35,
    "recruiter_leverage": 1.45,
    "recovery_value": 1.20,
    "composition_gain": 1.30,
    "dependency_unlocking": 1.15,
    "success_likelihood": 1.00,
    "prior_gain_preservation": 1.30,
    "destructive_risk": 1.45,
    "blocker_cost": 1.05,
}


class RestorationRoutingError(ValueError):
    """Raised when a restoration queue cannot be ranked safely."""


@dataclass(frozen=True)
class RestorationCandidate:
    candidate_id: str
    title: str
    repository: str
    tier: str
    operator_impact: float
    urgency: float
    capability_gain: float
    bottleneck_relief: float
    recruiter_leverage: float
    recovery_value: float
    composition_gain: float
    dependency_unlocking: float
    success_likelihood: float
    prior_gain_preservation: float
    destructive_risk: float
    blocker_cost: float
    blocked: bool = False
    blocker: str = ""

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> RestorationCandidate:
        required = ("candidate_id", "title", "repository", "tier", *ALL_FIELDS)
        missing = [name for name in required if name not in value]
        if missing:
            raise RestorationRoutingError(f"missing candidate fields: {', '.join(missing)}")

        tier = str(value["tier"]).upper()
        if tier not in TIERS:
            raise RestorationRoutingError(f"invalid priority tier: {tier}")

        numeric: dict[str, float] = {}
        for field in ALL_FIELDS:
            raw = value[field]
            if isinstance(raw, bool) or not isinstance(raw, (int, float)):
                raise RestorationRoutingError(f"{field} must be numeric")
            score = float(raw)
            if not isfinite(score) or not 0.0 <= score <= 10.0:
                raise RestorationRoutingError(f"{field} must be finite and within [0, 10]")
            numeric[field] = score

        identity = str(value["candidate_id"]).strip()
        repository = str(value["repository"]).strip()
        title = str(value["title"]).strip()
        if not identity or not repository or not title:
            raise RestorationRoutingError("candidate identity, title, and repository are required")

        return cls(
            candidate_id=identity,
            title=title,
            repository=repository,
            tier=tier,
            blocked=bool(value.get("blocked", False)),
            blocker=str(value.get("blocker", "")),
            **numeric,
        )


@dataclass(frozen=True)
class RankedRestorationCandidate:
    rank: int
    candidate_id: str
    title: str
    repository: str
    tier: str
    utility: float
    confidence_adjusted_utility: float
    pareto_front: bool
    dominated_by: tuple[str, ...]
    blocked: bool
    reasons: tuple[str, ...]


def _dominates(left: RestorationCandidate, right: RestorationCandidate) -> bool:
    benefits_not_worse = all(
        getattr(left, field) >= getattr(right, field) for field in BENEFIT_FIELDS
    )
    costs_not_worse = all(
        getattr(left, field) <= getattr(right, field) for field in COST_FIELDS
    )
    strictly_better = any(
        getattr(left, field) > getattr(right, field) for field in BENEFIT_FIELDS
    ) or any(getattr(left, field) < getattr(right, field) for field in COST_FIELDS)
    return benefits_not_worse and costs_not_worse and strictly_better


def _utility(candidate: RestorationCandidate, weights: Mapping[str, float]) -> float:
    benefit = sum(getattr(candidate, field) * weights[field] for field in BENEFIT_FIELDS)
    cost = sum(getattr(candidate, field) * weights[field] for field in COST_FIELDS)
    return benefit - cost


def rank_restoration_queue(
    raw_candidates: Iterable[Mapping[str, Any]],
    *,
    weights: Mapping[str, float] | None = None,
) -> tuple[RankedRestorationCandidate, ...]:
    """Rank a restoration queue with tier precedence, Pareto analysis, and confidence.

    P4 cannot outrank executable P0-P3 work because the best unblocked tier is
    selected before utility scoring. Blocked candidates remain visible but can
    never win.
    """

    candidates = [RestorationCandidate.from_mapping(value) for value in raw_candidates]
    if not candidates:
        raise RestorationRoutingError("at least one restoration candidate is required")
    ids = [candidate.candidate_id for candidate in candidates]
    if len(set(ids)) != len(ids):
        raise RestorationRoutingError("candidate_id values must be unique")

    active_weights = dict(DEFAULT_WEIGHTS)
    if weights:
        unknown = set(weights) - set(ALL_FIELDS)
        if unknown:
            raise RestorationRoutingError(f"unknown weight fields: {sorted(unknown)}")
        for field, raw in weights.items():
            value = float(raw)
            if not isfinite(value) or value < 0:
                raise RestorationRoutingError(
                    f"weight {field} must be finite and non-negative"
                )
            active_weights[field] = value

    unblocked = [candidate for candidate in candidates if not candidate.blocked]
    if not unblocked:
        raise RestorationRoutingError("all restoration candidates are blocked")
    best_tier = min(TIERS[candidate.tier] for candidate in unblocked)
    active_tier = [candidate for candidate in unblocked if TIERS[candidate.tier] == best_tier]

    dominators: dict[str, tuple[str, ...]] = {}
    for candidate in candidates:
        dominators[candidate.candidate_id] = tuple(
            sorted(
                other.candidate_id
                for other in active_tier
                if other.candidate_id != candidate.candidate_id and _dominates(other, candidate)
            )
        )

    rows: list[tuple[RestorationCandidate, float, float, bool]] = []
    for candidate in candidates:
        utility = _utility(candidate, active_weights)
        confidence = 0.55 + (candidate.success_likelihood / 10.0) * 0.45
        adjusted = utility * confidence
        pareto_front = (
            not candidate.blocked
            and TIERS[candidate.tier] == best_tier
            and not dominators[candidate.candidate_id]
        )
        rows.append((candidate, utility, adjusted, pareto_front))

    rows.sort(
        key=lambda row: (
            row[0].blocked,
            TIERS[row[0].tier],
            not row[3],
            -row[2],
            row[0].destructive_risk,
            row[0].blocker_cost,
            row[0].candidate_id,
        )
    )

    ranked: list[RankedRestorationCandidate] = []
    for index, (candidate, utility, adjusted, pareto_front) in enumerate(rows, 1):
        if candidate.blocked:
            reasons = (f"blocked: {candidate.blocker or 'unspecified blocker'}",)
        elif TIERS[candidate.tier] > best_tier:
            reasons = (f"deferred behind executable P{best_tier} work",)
        elif pareto_front:
            reasons = ("non-dominated on active priority tier",)
        else:
            reasons = (f"dominated by {', '.join(dominators[candidate.candidate_id])}",)
        ranked.append(
            RankedRestorationCandidate(
                rank=index,
                candidate_id=candidate.candidate_id,
                title=candidate.title,
                repository=candidate.repository,
                tier=candidate.tier,
                utility=round(utility, 4),
                confidence_adjusted_utility=round(adjusted, 4),
                pareto_front=pareto_front,
                dominated_by=dominators[candidate.candidate_id],
                blocked=candidate.blocked,
                reasons=reasons,
            )
        )
    return tuple(ranked)


def compile_restoration_decision(payload: Mapping[str, Any]) -> dict[str, Any]:
    raw = payload.get("candidates")
    if not isinstance(raw, list):
        raise RestorationRoutingError("payload.candidates must be a list")
    ranking = rank_restoration_queue(raw, weights=payload.get("weights"))
    winner = next(row for row in ranking if not row.blocked)
    return {
        "schema": "glaciereq.job-restore.megamind-routing.v1",
        "winner": asdict(winner),
        "ranking": [asdict(row) for row in ranking],
        "mechanisms": [
            "priority_tier",
            "pareto_dominance",
            "confidence_adjusted_utility",
        ],
        "donor": dict(MEGAMIND_DONOR),
    }
