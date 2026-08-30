"""Batch-rank job openings into an evidence-bound application execution queue.

The queue composes explicit requirement coverage with fresh company intelligence. It is
an execution surface, not a generic recommendation list: hard requirement gaps cap rank,
stale company intelligence loses leverage, and missing company intelligence remains
visible rather than being silently treated as current.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from .application_engine import CompanyTarget, find_target, load_targets
from .application_operations import (
    CandidateProfile,
    JobOpening,
    load_candidate_profile,
    load_job_opening,
)
from .company_fit import CompanyFitAssessment, assess_company_fit
from .company_intelligence import CompanyIntelligence, load_company_intelligence
from .opportunity_intelligence import OpportunityAssessment, assess_opportunity

QueueCandidate = tuple[
    JobOpening,
    CompanyTarget,
    CompanyIntelligence | None,
    str | None,
]
RankedCandidate = tuple[
    float,
    str,
    OpportunityAssessment,
    CompanyFitAssessment | None,
    JobOpening,
    CompanyTarget,
    tuple[str, ...],
]


@dataclass(frozen=True)
class QueueInput:
    company: str
    opening_path: Path
    intelligence_path: Path | None = None
    role: str | None = None


@dataclass(frozen=True)
class ApplicationQueueItem:
    rank: int
    opening_id: str
    company_id: str
    company: str
    role: str
    lane: str
    priority_score: float
    opportunity_score: float
    opportunity_recommendation: str
    required_coverage: float
    hard_gap_count: int
    company_fit_score: float | None
    company_freshness: float | None
    fresh_signal_count: int
    stale_signal_count: int
    reasons: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ApplicationExecutionQueue:
    schema: str
    generated_at: str
    candidate_count: int
    apply_now_count: int
    gap_work_count: int
    items: tuple[ApplicationQueueItem, ...]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _freshness(assessment: CompanyFitAssessment) -> float:
    total = assessment.fresh_signal_count + assessment.stale_signal_count
    return assessment.fresh_signal_count / total if total else 0.0


def _lane(opportunity: OpportunityAssessment) -> str:
    if opportunity.recommendation == "BLOCKED_NO_PUBLIC_PROOF":
        return "BLOCKED_PROOF"
    if opportunity.recommendation == "GAPS_TO_CLOSE":
        return "PREPARE_GAPS"
    if opportunity.recommendation == "APPLY_PRIORITY":
        return "APPLY_NOW"
    if opportunity.recommendation == "APPLY_VIABLE":
        return "APPLY_NEXT"
    return "DEFER"


def _hard_cap(opportunity: OpportunityAssessment) -> float:
    if opportunity.recommendation == "BLOCKED_NO_PUBLIC_PROOF":
        return 20.0
    if opportunity.recommendation == "GAPS_TO_CLOSE":
        return 45.0
    if opportunity.recommendation == "DEFER":
        return 59.0
    return 100.0


def score_queue_candidate(
    opening: JobOpening,
    target: CompanyTarget,
    profile: CandidateProfile,
    *,
    intelligence: CompanyIntelligence | None = None,
    role: str | None = None,
    now: datetime | None = None,
) -> tuple[float, OpportunityAssessment, CompanyFitAssessment | None, tuple[str, ...]]:
    """Compose requirement and company intelligence into one application-work score."""
    opportunity = assess_opportunity(opening, target, profile, mapped_role=role)
    company_fit: CompanyFitAssessment | None = None
    freshness: float | None = None

    if intelligence is not None:
        if intelligence.company_id != target.company_id:
            raise ValueError(
                "company intelligence does not match queue target: "
                f"{intelligence.company_id!r} != {target.company_id!r}"
            )
        company_fit = assess_company_fit(profile, intelligence, now=now)
        freshness = _freshness(company_fit)

    # Explicit role fit is dominant. Company fit multiplies leverage but cannot rescue
    # major hard gaps. Missing company intelligence incurs a small uncertainty penalty.
    if company_fit is None:
        raw_score = 0.95 * opportunity.score
    else:
        raw_score = (
            0.75 * opportunity.score
            + 0.20 * company_fit.score
            + 5.0 * float(freshness)
        )
    priority_score = round(min(raw_score, _hard_cap(opportunity)), 2)

    reasons = [
        f"opportunity={opportunity.score:.1f}",
        f"required_coverage={opportunity.required_coverage:.0%}",
        f"hard_gaps={len(opportunity.missing_requirements)}",
    ]
    if company_fit is None:
        reasons.append("company_intelligence=missing")
    else:
        reasons.extend(
            (
                f"company_fit={company_fit.score:.1f}",
                f"company_freshness={float(freshness):.0%}",
                f"fresh_signals={company_fit.fresh_signal_count}",
            )
        )
    cap = _hard_cap(opportunity)
    if raw_score > cap:
        reasons.append(f"hard_gap_cap={cap:.0f}")

    return priority_score, opportunity, company_fit, tuple(reasons)


def build_application_execution_queue(
    candidates: Sequence[QueueCandidate],
    profile: CandidateProfile,
    *,
    now: datetime | None = None,
) -> ApplicationExecutionQueue:
    """Rank a batch while preserving deterministic lane and score ordering."""
    rows: list[RankedCandidate] = []
    for opening, target, intelligence, role in candidates:
        score, opportunity, company_fit, reasons = score_queue_candidate(
            opening,
            target,
            profile,
            intelligence=intelligence,
            role=role,
            now=now,
        )
        rows.append(
            (
                score,
                _lane(opportunity),
                opportunity,
                company_fit,
                opening,
                target,
                reasons,
            )
        )

    lane_order = {
        "APPLY_NOW": 0,
        "APPLY_NEXT": 1,
        "PREPARE_GAPS": 2,
        "DEFER": 3,
        "BLOCKED_PROOF": 4,
    }
    rows.sort(
        key=lambda row: (
            lane_order[row[1]],
            -row[0],
            -row[2].required_coverage,
            row[4].opening_id,
        )
    )

    items: list[ApplicationQueueItem] = []
    for rank, row in enumerate(rows, start=1):
        score, lane, opportunity, company_fit, opening, target, reasons = row
        freshness = _freshness(company_fit) if company_fit is not None else None
        items.append(
            ApplicationQueueItem(
                rank=rank,
                opening_id=opening.opening_id,
                company_id=target.company_id,
                company=opening.company,
                role=opportunity.role,
                lane=lane,
                priority_score=score,
                opportunity_score=opportunity.score,
                opportunity_recommendation=opportunity.recommendation,
                required_coverage=opportunity.required_coverage,
                hard_gap_count=len(opportunity.missing_requirements),
                company_fit_score=(
                    company_fit.score if company_fit is not None else None
                ),
                company_freshness=(
                    round(freshness, 6) if freshness is not None else None
                ),
                fresh_signal_count=(
                    company_fit.fresh_signal_count if company_fit is not None else 0
                ),
                stale_signal_count=(
                    company_fit.stale_signal_count if company_fit is not None else 0
                ),
                reasons=reasons,
            )
        )

    clock = (now or datetime.now(UTC)).astimezone(UTC).replace(microsecond=0)
    return ApplicationExecutionQueue(
        schema="glaciereq.application-execution-queue.v1",
        generated_at=clock.isoformat().replace("+00:00", "Z"),
        candidate_count=len(items),
        apply_now_count=sum(item.lane in {"APPLY_NOW", "APPLY_NEXT"} for item in items),
        gap_work_count=sum(item.lane == "PREPARE_GAPS" for item in items),
        items=tuple(items),
    )


def _manifest_inputs(path: Path) -> tuple[QueueInput, ...]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError("queue manifest must be an object")
    raw = payload.get("candidates")
    if not isinstance(raw, list) or not raw:
        raise ValueError("queue manifest requires a non-empty candidates list")
    root = path.parent
    inputs: list[QueueInput] = []
    for index, item in enumerate(raw):
        if not isinstance(item, Mapping):
            raise ValueError(f"queue candidates[{index}] must be an object")
        opening = root / str(item["opening"])
        intelligence_value = item.get("company_intelligence")
        intelligence_path = (
            root / str(intelligence_value) if intelligence_value else None
        )
        inputs.append(
            QueueInput(
                company=str(item["company"]),
                opening_path=opening,
                intelligence_path=intelligence_path,
                role=(str(item["role"]) if item.get("role") else None),
            )
        )
    return tuple(inputs)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="job-app-helix-queue",
        description=(
            "Batch-rank real openings using requirement coverage, fresh company fit, "
            "freshness, and hard-gap caps."
        ),
    )
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    profile = load_candidate_profile(args.profile)
    targets = load_targets()
    candidates: list[QueueCandidate] = []
    for item in _manifest_inputs(args.manifest):
        target = find_target(item.company, targets)
        opening = load_job_opening(item.opening_path)
        intelligence = (
            load_company_intelligence(item.intelligence_path)
            if item.intelligence_path is not None
            else None
        )
        candidates.append((opening, target, intelligence, item.role))

    queue = build_application_execution_queue(candidates, profile)
    rendered = json.dumps(queue.as_dict(), indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if queue.apply_now_count else 2


if __name__ == "__main__":
    raise SystemExit(main())
