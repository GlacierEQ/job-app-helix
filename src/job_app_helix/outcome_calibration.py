"""Learn bounded queue-weight adjustments from persisted application outcomes.

Outcome learning is deliberately isolated from factual candidate evidence. The model
consumes only persisted application lifecycle outcomes and already-computed assessment
scores, then adjusts queue ordering within existing safety lanes. Hard requirement caps,
public-proof blocks, and source evidence remain owned by the existing queue/strategy stack.
"""

from __future__ import annotations

import argparse
import json
import math
import sqlite3
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, replace
from pathlib import Path

from .application_engine import find_target, load_targets
from .application_operations import load_candidate_profile, load_job_opening
from .company_intelligence import load_company_intelligence
from .opportunity_queue import (
    ApplicationExecutionQueue,
    ApplicationQueueItem,
    QueueCandidate,
    build_application_execution_queue,
)

BASELINE_WEIGHTS = {
    "opportunity": 0.75,
    "company_fit": 0.20,
    "freshness": 0.05,
}
LANE_ORDER = {
    "APPLY_NOW": 0,
    "APPLY_NEXT": 1,
    "PREPARE_GAPS": 2,
    "DEFER": 3,
    "BLOCKED_PROOF": 4,
}
LANE_CAPS = {
    "APPLY_NOW": 100.0,
    "APPLY_NEXT": 100.0,
    "PREPARE_GAPS": 45.0,
    "DEFER": 59.0,
    "BLOCKED_PROOF": 20.0,
}


@dataclass(frozen=True)
class OutcomeExample:
    application_id: str
    outcome_value: float
    opportunity_score: float
    company_fit_score: float | None
    freshness: float | None


@dataclass(frozen=True)
class OutcomeCalibration:
    schema: str
    sample_count: int
    effective_sample_count: int
    status: str
    baseline_weights: Mapping[str, float]
    learned_weights: Mapping[str, float]
    feature_signal: Mapping[str, float]
    shrinkage: float
    max_weight_shift: float

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _bounded(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _weighted_signal(values: Sequence[float], outcomes: Sequence[float]) -> float:
    if len(values) < 2 or len(values) != len(outcomes):
        return 0.0
    mean_x = sum(values) / len(values)
    mean_y = sum(outcomes) / len(outcomes)
    covariance = sum((x - mean_x) * (y - mean_y) for x, y in zip(values, outcomes, strict=True))
    var_x = sum((x - mean_x) ** 2 for x in values)
    var_y = sum((y - mean_y) ** 2 for y in outcomes)
    if var_x <= 1e-12 or var_y <= 1e-12:
        return 0.0
    return _bounded(covariance / math.sqrt(var_x * var_y), -1.0, 1.0)


def fit_outcome_calibration(
    examples: Sequence[OutcomeExample],
    *,
    minimum_samples: int = 6,
    full_strength_samples: int = 30,
    max_weight_shift: float = 0.10,
) -> OutcomeCalibration:
    """Fit a conservative, deterministic weight adjustment from observed outcomes.

    Correlation is used only as a directional signal. Shrinkage prevents a handful of
    outcomes from rewriting ranking behavior, and each dimension is bounded around the
    proven baseline before normalization.
    """
    if minimum_samples < 2 or full_strength_samples < minimum_samples:
        raise ValueError("invalid calibration sample thresholds")
    if not 0 < max_weight_shift <= 0.25:
        raise ValueError("max_weight_shift must be in (0, 0.25]")

    eligible = [row for row in examples if 0.0 <= row.outcome_value <= 1.0]
    effective = len(eligible)
    signals = {
        "opportunity": _weighted_signal(
            [row.opportunity_score / 100.0 for row in eligible],
            [row.outcome_value for row in eligible],
        ),
        "company_fit": _weighted_signal(
            [float(row.company_fit_score) / 100.0 for row in eligible if row.company_fit_score is not None],
            [row.outcome_value for row in eligible if row.company_fit_score is not None],
        ),
        "freshness": _weighted_signal(
            [float(row.freshness) for row in eligible if row.freshness is not None],
            [row.outcome_value for row in eligible if row.freshness is not None],
        ),
    }

    if effective < minimum_samples:
        shrinkage = 0.0
        learned = dict(BASELINE_WEIGHTS)
        status = "INSUFFICIENT_OUTCOMES"
    else:
        shrinkage = _bounded(
            (effective - minimum_samples + 1) / max(1, full_strength_samples - minimum_samples + 1),
            0.0,
            1.0,
        )
        provisional: dict[str, float] = {}
        for key, baseline in BASELINE_WEIGHTS.items():
            shift = signals[key] * max_weight_shift * shrinkage
            provisional[key] = _bounded(
                baseline + shift,
                max(0.01, baseline - max_weight_shift),
                baseline + max_weight_shift,
            )
        total = sum(provisional.values())
        learned = {key: value / total for key, value in provisional.items()}
        status = "CALIBRATED"

    return OutcomeCalibration(
        schema="glaciereq.outcome-calibration.v1",
        sample_count=len(examples),
        effective_sample_count=effective,
        status=status,
        baseline_weights=dict(BASELINE_WEIGHTS),
        learned_weights={key: round(value, 8) for key, value in learned.items()},
        feature_signal={key: round(value, 8) for key, value in signals.items()},
        shrinkage=round(shrinkage, 8),
        max_weight_shift=max_weight_shift,
    )


def _outcome_value(status: str, events: Sequence[Mapping[str, object]]) -> float | None:
    normalized = status.upper()
    if normalized == "OFFER":
        return 1.0
    if normalized == "INTERVIEW":
        return 0.70
    if normalized == "REJECTED":
        return 0.10
    if normalized in {"WITHDRAWN", "CLOSED"}:
        saw_interview = any(
            row.get("event_type") == "STATUS_CHANGED"
            and isinstance(row.get("payload"), Mapping)
            and row["payload"].get("to") == "INTERVIEW"
            for row in events
        )
        return 0.55 if saw_interview else 0.20
    return None


def _load_json(path: Path) -> Mapping[str, object] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, Mapping) else None


def load_outcome_examples(database: Path) -> tuple[OutcomeExample, ...]:
    """Extract trainable rows without mutating the application database."""
    connection = sqlite3.connect(database)
    connection.row_factory = sqlite3.Row
    try:
        applications = connection.execute(
            "SELECT application_id,status,packet_dir FROM applications ORDER BY application_id"
        ).fetchall()
        rows: list[OutcomeExample] = []
        for application in applications:
            packet_dir = application["packet_dir"]
            if not packet_dir:
                continue
            event_rows = connection.execute(
                "SELECT event_type,payload_json FROM events WHERE application_id=? ORDER BY id",
                (application["application_id"],),
            ).fetchall()
            events = [
                {
                    "event_type": event["event_type"],
                    "payload": json.loads(event["payload_json"]),
                }
                for event in event_rows
            ]
            outcome = _outcome_value(str(application["status"]), events)
            if outcome is None:
                continue
            root = Path(str(packet_dir))
            opportunity = _load_json(root / "OPPORTUNITY_ASSESSMENT.json")
            if opportunity is None:
                continue
            raw_score = opportunity.get("score")
            if not isinstance(raw_score, (int, float)):
                continue
            company_fit = _load_json(root / "COMPANY_FIT_ASSESSMENT.json")
            fit_score: float | None = None
            freshness: float | None = None
            if company_fit is not None:
                raw_fit = company_fit.get("score")
                fresh = company_fit.get("fresh_signal_count")
                stale = company_fit.get("stale_signal_count")
                if isinstance(raw_fit, (int, float)):
                    fit_score = float(raw_fit)
                if isinstance(fresh, int) and isinstance(stale, int) and fresh + stale > 0:
                    freshness = fresh / (fresh + stale)
            rows.append(
                OutcomeExample(
                    application_id=str(application["application_id"]),
                    outcome_value=outcome,
                    opportunity_score=float(raw_score),
                    company_fit_score=fit_score,
                    freshness=freshness,
                )
            )
        return tuple(rows)
    finally:
        connection.close()


def calibrate_queue(
    queue: ApplicationExecutionQueue,
    calibration: OutcomeCalibration,
) -> ApplicationExecutionQueue:
    """Re-rank within existing safety lanes using bounded learned weights."""
    weights = calibration.learned_weights
    adjusted: list[ApplicationQueueItem] = []
    for item in queue.items:
        fit = item.company_fit_score if item.company_fit_score is not None else item.opportunity_score
        freshness = 100.0 * (item.company_freshness if item.company_freshness is not None else 0.0)
        raw = (
            float(weights["opportunity"]) * item.opportunity_score
            + float(weights["company_fit"]) * fit
            + float(weights["freshness"]) * freshness
        )
        score = round(min(raw, LANE_CAPS[item.lane]), 2)
        reasons = (*item.reasons, f"outcome_calibration={calibration.status}")
        adjusted.append(replace(item, priority_score=score, reasons=reasons))

    adjusted.sort(
        key=lambda item: (
            LANE_ORDER[item.lane],
            -item.priority_score,
            -item.required_coverage,
            item.opening_id,
        )
    )
    ranked = tuple(replace(item, rank=index) for index, item in enumerate(adjusted, start=1))
    return replace(queue, schema="glaciereq.application-execution-queue.v1+outcome-calibration", items=ranked)


def _load_calibration(path: Path) -> OutcomeCalibration:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping) or value.get("schema") != "glaciereq.outcome-calibration.v1":
        raise ValueError("invalid outcome calibration artifact")
    return OutcomeCalibration(
        schema=str(value["schema"]),
        sample_count=int(value["sample_count"]),
        effective_sample_count=int(value["effective_sample_count"]),
        status=str(value["status"]),
        baseline_weights=dict(value["baseline_weights"]),
        learned_weights=dict(value["learned_weights"]),
        feature_signal=dict(value["feature_signal"]),
        shrinkage=float(value["shrinkage"]),
        max_weight_shift=float(value["max_weight_shift"]),
    )


def _queue_from_manifest(manifest: Path, profile_path: Path) -> ApplicationExecutionQueue:
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    raw_candidates = payload.get("candidates") if isinstance(payload, Mapping) else None
    if not isinstance(raw_candidates, list) or not raw_candidates:
        raise ValueError("queue manifest requires non-empty candidates")
    root = manifest.parent
    targets = load_targets()
    candidates: list[QueueCandidate] = []
    for index, row in enumerate(raw_candidates):
        if not isinstance(row, Mapping):
            raise ValueError(f"queue candidate {index} must be an object")
        target = find_target(str(row["company"]), targets)
        opening = load_job_opening(root / str(row["opening"]))
        intelligence_value = row.get("company_intelligence")
        intelligence = (
            load_company_intelligence(root / str(intelligence_value))
            if intelligence_value
            else None
        )
        role = str(row["role"]) if row.get("role") else None
        candidates.append((opening, target, intelligence, role))
    return build_application_execution_queue(candidates, load_candidate_profile(profile_path))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="job-app-helix-outcomes")
    sub = parser.add_subparsers(dest="command", required=True)

    fit = sub.add_parser("fit", help="learn bounded queue weights from application outcomes")
    fit.add_argument("--database", type=Path, required=True)
    fit.add_argument("--output", type=Path, required=True)

    rank = sub.add_parser("rank", help="apply a calibration artifact to a live queue")
    rank.add_argument("--manifest", type=Path, required=True)
    rank.add_argument("--profile", type=Path, required=True)
    rank.add_argument("--calibration", type=Path, required=True)
    rank.add_argument("--output", type=Path)

    args = parser.parse_args(argv)
    if args.command == "fit":
        model = fit_outcome_calibration(load_outcome_examples(args.database))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(model.as_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(model.as_dict(), indent=2, sort_keys=True))
        return 0

    queue = _queue_from_manifest(args.manifest, args.profile)
    calibrated = calibrate_queue(queue, _load_calibration(args.calibration))
    rendered = json.dumps(calibrated.as_dict(), indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if calibrated.apply_now_count else 2


if __name__ == "__main__":
    raise SystemExit(main())
