from __future__ import annotations

from job_app_helix.calibration_diagnostics import CalibrationDiagnostics, FeatureCoverage
from job_app_helix.calibration_guard import apply_calibration_guard
from job_app_helix.outcome_calibration import OutcomeCalibration


def _calibration() -> OutcomeCalibration:
    return OutcomeCalibration(
        schema="glaciereq.outcome-calibration.v1",
        sample_count=40,
        effective_sample_count=40,
        status="CALIBRATED",
        baseline_weights={"opportunity": 0.75, "company_fit": 0.20, "freshness": 0.05},
        learned_weights={"opportunity": 0.67, "company_fit": 0.27, "freshness": 0.06},
        feature_signal={"opportunity": -0.8, "company_fit": 0.9, "freshness": 0.2},
        shrinkage=1.0,
        max_weight_shift=0.10,
    )


def _diagnostics(status: str) -> CalibrationDiagnostics:
    reasons = ("signal_drift=0.9000",) if status == "BLOCK_LEARNED_RANKING" else ()
    return CalibrationDiagnostics(
        schema="glaciereq.outcome-calibration-diagnostics.v1",
        sample_count=40,
        reference_count=20,
        recent_count=20,
        status=status,
        feature_coverage=(
            FeatureCoverage("company_fit", 40, 40, 1.0, False),
            FeatureCoverage("freshness", 40, 40, 1.0, False),
        ),
        sparse_features=(),
        signal_drift={"opportunity": 0.9, "company_fit": 0.1, "freshness": 0.05},
        max_signal_drift=0.9,
        learned_weight_drift_l1=0.16,
        ranking_pair_count=100,
        ranking_flip_count=35,
        ranking_instability=0.35,
        thresholds={
            "minimum_feature_coverage": 0.70,
            "maximum_signal_drift": 0.60,
            "maximum_weight_drift_l1": 0.12,
            "maximum_ranking_instability": 0.20,
        },
        reasons=reasons,
    )


def test_blocking_diagnostics_force_exact_baseline_weights() -> None:
    source = _calibration()
    guarded, decision = apply_calibration_guard(source, _diagnostics("BLOCK_LEARNED_RANKING"))

    assert guarded.status == "DIAGNOSTIC_BASELINE_FALLBACK"
    assert guarded.learned_weights == source.baseline_weights
    assert guarded.learned_weights != source.learned_weights
    assert decision.mode == "BASELINE_FALLBACK"
    assert decision.diagnostics_status == "BLOCK_LEARNED_RANKING"
    assert decision.source_learned_weights == source.learned_weights
    assert decision.applied_weights == source.baseline_weights
    assert decision.reasons == ("signal_drift=0.9000",)


def test_pass_and_warn_preserve_fitted_weights() -> None:
    source = _calibration()
    for status in ("PASS", "WARN"):
        guarded, decision = apply_calibration_guard(source, _diagnostics(status))
        assert guarded is source
        assert guarded.learned_weights == source.learned_weights
        assert decision.mode == "LEARNED_ALLOWED"
        assert decision.applied_calibration_status == "CALIBRATED"


def test_unknown_diagnostic_status_is_rejected() -> None:
    source = _calibration()
    broken = _diagnostics("PASS")
    object.__setattr__(broken, "status", "UNKNOWN")

    try:
        apply_calibration_guard(source, broken)
    except ValueError as exc:
        assert "unsupported calibration diagnostics status" in str(exc)
    else:
        raise AssertionError("unknown diagnostics status must fail closed")
