from __future__ import annotations

from job_app_helix.calibration_diagnostics import diagnose_outcome_calibration
from job_app_helix.outcome_calibration import OutcomeExample, fit_outcome_calibration


def _row(
    index: int,
    outcome: float,
    opportunity: float,
    fit: float | None,
    freshness: float | None,
) -> OutcomeExample:
    return OutcomeExample(
        application_id=f"app-{index:03d}",
        outcome_value=outcome,
        opportunity_score=opportunity,
        company_fit_score=fit,
        freshness=freshness,
    )


def test_diagnostics_exposes_sparse_feature_blind_spots() -> None:
    rows = tuple(
        _row(index, index / 9, 55 + index, None if index < 8 else 80.0, None)
        for index in range(10)
    )

    diagnostics = diagnose_outcome_calibration(rows, recent_window=4)

    assert diagnostics.status == "WARN"
    assert diagnostics.sparse_features == ("company_fit", "freshness")
    coverage = {item.feature: item.ratio for item in diagnostics.feature_coverage}
    assert coverage == {"company_fit": 0.2, "freshness": 0.0}


def test_diagnostics_blocks_temporal_signal_reversal() -> None:
    rows = []
    for index in range(12):
        high = index >= 6
        rows.append(
            _row(
                index,
                0.95 if high else 0.05,
                90.0 if high else 50.0,
                90.0 if high else 50.0,
                0.9 if high else 0.2,
            )
        )
    for index in range(12, 24):
        high = index < 18
        rows.append(
            _row(
                index,
                0.05 if high else 0.95,
                90.0 if high else 50.0,
                90.0 if high else 50.0,
                0.9 if high else 0.2,
            )
        )

    diagnostics = diagnose_outcome_calibration(
        rows,
        recent_window=12,
        maximum_signal_drift=0.5,
    )

    assert diagnostics.status == "BLOCK_LEARNED_RANKING"
    assert diagnostics.max_signal_drift > 1.0
    assert any(reason.startswith("signal_drift=") for reason in diagnostics.reasons)


def test_diagnostics_measures_pairwise_ranking_instability() -> None:
    rows = tuple(
        _row(
            index,
            0.95 if index >= 6 else 0.05,
            70.0,
            98.0 if index >= 6 else 20.0,
            1.0,
        )
        for index in range(12)
    )
    calibration = fit_outcome_calibration(rows, max_weight_shift=0.25)

    diagnostics = diagnose_outcome_calibration(
        rows,
        calibration,
        recent_window=6,
        maximum_ranking_instability=0.0,
    )

    assert diagnostics.ranking_pair_count > 0
    assert diagnostics.ranking_flip_count >= 0
    assert 0.0 <= diagnostics.ranking_instability <= 1.0


def test_stable_complete_history_passes() -> None:
    rows = []
    for index in range(40):
        high = index % 10 >= 5
        rows.append(
            _row(
                index,
                0.9 if high else 0.1,
                88.0 if high else 52.0,
                86.0 if high else 48.0,
                0.9 if high else 0.3,
            )
        )

    diagnostics = diagnose_outcome_calibration(
        rows,
        recent_window=20,
        maximum_signal_drift=0.2,
        maximum_weight_drift_l1=0.2,
        maximum_ranking_instability=0.5,
    )

    assert diagnostics.status == "PASS"
    assert diagnostics.sparse_features == ()
    assert diagnostics.max_signal_drift == 0.0
    assert diagnostics.learned_weight_drift_l1 == 0.0
