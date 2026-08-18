from __future__ import annotations

from datetime import UTC, datetime

from job_app_helix.opportunity_queue import (
    ApplicationExecutionQueue,
    ApplicationQueueItem,
)
from job_app_helix.outcome_calibration import (
    BASELINE_WEIGHTS,
    OutcomeExample,
    calibrate_queue,
    fit_outcome_calibration,
)


def _item(
    opening_id: str,
    *,
    lane: str,
    opportunity: float,
    fit: float | None,
    freshness: float | None,
    required: float = 1.0,
) -> ApplicationQueueItem:
    return ApplicationQueueItem(
        rank=1,
        opening_id=opening_id,
        company_id="example",
        company="Example",
        role="Engineer",
        lane=lane,
        priority_score=opportunity,
        opportunity_score=opportunity,
        opportunity_recommendation="APPLY_PRIORITY",
        required_coverage=required,
        hard_gap_count=0 if lane == "APPLY_NOW" else 2,
        company_fit_score=fit,
        company_freshness=freshness,
        fresh_signal_count=1 if freshness else 0,
        stale_signal_count=0,
        reasons=("base",),
    )


def test_sparse_outcomes_preserve_proven_baseline() -> None:
    rows = [
        OutcomeExample(f"app-{index}", 1.0, 90.0, 80.0, 1.0)
        for index in range(3)
    ]
    model = fit_outcome_calibration(rows)

    assert model.status == "INSUFFICIENT_OUTCOMES"
    assert model.shrinkage == 0.0
    assert model.learned_weights == BASELINE_WEIGHTS


def test_repeated_outcomes_shift_weights_but_remain_bounded() -> None:
    rows = []
    for index in range(20):
        strong = index >= 10
        rows.append(
            OutcomeExample(
                application_id=f"app-{index}",
                outcome_value=0.95 if strong else 0.10,
                opportunity_score=90.0 if strong else 55.0,
                company_fit_score=92.0 if strong else 45.0,
                freshness=1.0 if strong else 0.2,
            )
        )

    model = fit_outcome_calibration(rows)

    assert model.status == "CALIBRATED"
    assert model.shrinkage > 0
    assert abs(sum(model.learned_weights.values()) - 1.0) < 1e-6
    for key, baseline in BASELINE_WEIGHTS.items():
        assert abs(model.learned_weights[key] - baseline) <= 0.11


def test_calibration_never_lets_gap_lane_jump_apply_lane() -> None:
    examples = [
        OutcomeExample(
            f"app-{index}",
            index / 9,
            50 + index * 5,
            40 + index * 6,
            0.2 + index / 12,
        )
        for index in range(10)
    ]
    model = fit_outcome_calibration(examples)
    queue = ApplicationExecutionQueue(
        schema="glaciereq.application-execution-queue.v1",
        generated_at=datetime.now(UTC).isoformat(),
        candidate_count=2,
        apply_now_count=1,
        gap_work_count=1,
        items=(
            _item(
                "gap",
                lane="PREPARE_GAPS",
                opportunity=99.0,
                fit=100.0,
                freshness=1.0,
                required=0.5,
            ),
            _item(
                "apply",
                lane="APPLY_NOW",
                opportunity=60.0,
                fit=55.0,
                freshness=0.5,
            ),
        ),
    )

    calibrated = calibrate_queue(queue, model)

    assert calibrated.items[0].opening_id == "apply"
    assert calibrated.items[1].opening_id == "gap"
    assert calibrated.items[1].priority_score <= 45.0
    assert calibrated.schema.endswith("+outcome-calibration")


def test_calibration_reranks_inside_same_lane() -> None:
    rows = [
        OutcomeExample(
            f"app-{index}",
            0.95 if index >= 6 else 0.1,
            70.0,
            95.0 if index >= 6 else 30.0,
            1.0,
        )
        for index in range(12)
    ]
    model = fit_outcome_calibration(rows)
    queue = ApplicationExecutionQueue(
        schema="glaciereq.application-execution-queue.v1",
        generated_at="2026-08-18T00:00:00Z",
        candidate_count=2,
        apply_now_count=2,
        gap_work_count=0,
        items=(
            _item(
                "higher-fit",
                lane="APPLY_NOW",
                opportunity=80.0,
                fit=95.0,
                freshness=1.0,
            ),
            _item(
                "lower-fit",
                lane="APPLY_NOW",
                opportunity=82.0,
                fit=30.0,
                freshness=1.0,
            ),
        ),
    )

    calibrated = calibrate_queue(queue, model)

    assert calibrated.items[0].opening_id == "higher-fit"
    assert "outcome_calibration=CALIBRATED" in calibrated.items[0].reasons
