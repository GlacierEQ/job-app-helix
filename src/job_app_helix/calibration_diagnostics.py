"""Adversarial diagnostics for learned application-ranking calibration.

The outcome learner intentionally moves ranking weights only inside existing safety lanes.
This module answers the separate operational question: is the learned signal healthy enough
to trust at scale? It measures optional-feature coverage, temporal signal drift, learned-weight
drift, and pairwise ranking instability without mutating candidate evidence or application
state.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

from .outcome_calibration import (
    BASELINE_WEIGHTS,
    OutcomeCalibration,
    OutcomeExample,
    fit_outcome_calibration,
    load_outcome_examples,
)


@dataclass(frozen=True)
class FeatureCoverage:
    feature: str
    observed_count: int
    sample_count: int
    ratio: float
    blind_spot: bool


@dataclass(frozen=True)
class CalibrationDiagnostics:
    schema: str
    sample_count: int
    reference_count: int
    recent_count: int
    status: str
    feature_coverage: tuple[FeatureCoverage, ...]
    sparse_features: tuple[str, ...]
    signal_drift: Mapping[str, float]
    max_signal_drift: float
    learned_weight_drift_l1: float
    ranking_pair_count: int
    ranking_flip_count: int
    ranking_instability: float
    thresholds: Mapping[str, float]
    reasons: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _feature_value(row: OutcomeExample, feature: str) -> float | None:
    if feature == "opportunity":
        return row.opportunity_score / 100.0
    if feature == "company_fit":
        return None if row.company_fit_score is None else row.company_fit_score / 100.0
    if feature == "freshness":
        return row.freshness
    raise KeyError(feature)


def _score(row: OutcomeExample, weights: Mapping[str, float]) -> float:
    opportunity = row.opportunity_score / 100.0
    company_fit = (
        row.company_fit_score / 100.0
        if row.company_fit_score is not None
        else opportunity
    )
    freshness = row.freshness if row.freshness is not None else 0.0
    return (
        float(weights["opportunity"]) * opportunity
        + float(weights["company_fit"]) * company_fit
        + float(weights["freshness"]) * freshness
    )


def _pairwise_instability(
    rows: Sequence[OutcomeExample],
    baseline_weights: Mapping[str, float],
    learned_weights: Mapping[str, float],
) -> tuple[int, int, float]:
    """Return comparable pairs, flipped pairs, and deterministic pairwise flip rate."""
    baseline = {row.application_id: _score(row, baseline_weights) for row in rows}
    learned = {row.application_id: _score(row, learned_weights) for row in rows}
    pair_count = 0
    flip_count = 0
    for left_index, left in enumerate(rows):
        for right in rows[left_index + 1 :]:
            baseline_delta = baseline[left.application_id] - baseline[right.application_id]
            learned_delta = learned[left.application_id] - learned[right.application_id]
            if abs(baseline_delta) <= 1e-12 or abs(learned_delta) <= 1e-12:
                continue
            pair_count += 1
            if baseline_delta * learned_delta < 0:
                flip_count += 1
    rate = flip_count / pair_count if pair_count else 0.0
    return pair_count, flip_count, rate


def diagnose_outcome_calibration(
    examples: Sequence[OutcomeExample],
    calibration: OutcomeCalibration | None = None,
    *,
    recent_window: int = 20,
    minimum_feature_coverage: float = 0.70,
    maximum_signal_drift: float = 0.60,
    maximum_weight_drift_l1: float = 0.12,
    maximum_ranking_instability: float = 0.20,
) -> CalibrationDiagnostics:
    """Diagnose blind spots and instability before learned ranking is trusted at scale.

    The most recent rows are inferred from input order, which is stable for application-store
    extraction. Drift compares the recent cohort with the immediately preceding reference
    cohort of equal maximum size. With too little reference history, drift is reported as
    zero and the status is WARN until enough temporal evidence exists.
    """
    if recent_window < 2:
        raise ValueError("recent_window must be at least 2")
    for name, value in {
        "minimum_feature_coverage": minimum_feature_coverage,
        "maximum_signal_drift": maximum_signal_drift,
        "maximum_weight_drift_l1": maximum_weight_drift_l1,
        "maximum_ranking_instability": maximum_ranking_instability,
    }.items():
        if not 0.0 <= value <= 1.0:
            raise ValueError(f"{name} must be in [0, 1]")

    rows = tuple(row for row in examples if 0.0 <= row.outcome_value <= 1.0)
    model = calibration or fit_outcome_calibration(rows)
    recent = rows[-recent_window:]
    reference_end = max(0, len(rows) - len(recent))
    reference_start = max(0, reference_end - recent_window)
    reference = rows[reference_start:reference_end]

    coverage: list[FeatureCoverage] = []
    for feature in ("company_fit", "freshness"):
        observed = sum(_feature_value(row, feature) is not None for row in rows)
        ratio = observed / len(rows) if rows else 0.0
        coverage.append(
            FeatureCoverage(
                feature=feature,
                observed_count=observed,
                sample_count=len(rows),
                ratio=round(ratio, 8),
                blind_spot=ratio < minimum_feature_coverage,
            )
        )

    sparse_features = tuple(item.feature for item in coverage if item.blind_spot)
    signal_drift = {key: 0.0 for key in BASELINE_WEIGHTS}
    weight_drift_l1 = 0.0
    has_temporal_reference = len(reference) >= 2 and len(recent) >= 2
    if has_temporal_reference:
        reference_model = fit_outcome_calibration(reference, minimum_samples=2)
        recent_model = fit_outcome_calibration(recent, minimum_samples=2)
        signal_drift = {
            key: round(
                abs(
                    float(reference_model.feature_signal[key])
                    - float(recent_model.feature_signal[key])
                ),
                8,
            )
            for key in BASELINE_WEIGHTS
        }
        weight_drift_l1 = sum(
            abs(
                float(reference_model.learned_weights[key])
                - float(recent_model.learned_weights[key])
            )
            for key in BASELINE_WEIGHTS
        )

    pair_count, flip_count, instability = _pairwise_instability(
        rows,
        model.baseline_weights,
        model.learned_weights,
    )
    max_drift = max(signal_drift.values(), default=0.0)

    reasons: list[str] = []
    blocking = False
    if sparse_features:
        reasons.append("sparse_optional_features=" + ",".join(sparse_features))
    if has_temporal_reference and max_drift > maximum_signal_drift:
        blocking = True
        reasons.append(f"signal_drift={max_drift:.4f}")
    if has_temporal_reference and weight_drift_l1 > maximum_weight_drift_l1:
        blocking = True
        reasons.append(f"weight_drift_l1={weight_drift_l1:.4f}")
    if instability > maximum_ranking_instability:
        blocking = True
        reasons.append(f"ranking_instability={instability:.4f}")
    if not has_temporal_reference:
        reasons.append("insufficient_temporal_reference")

    if blocking:
        status = "BLOCK_LEARNED_RANKING"
    elif sparse_features or not has_temporal_reference:
        status = "WARN"
    else:
        status = "PASS"

    return CalibrationDiagnostics(
        schema="glaciereq.outcome-calibration-diagnostics.v1",
        sample_count=len(rows),
        reference_count=len(reference),
        recent_count=len(recent),
        status=status,
        feature_coverage=tuple(coverage),
        sparse_features=sparse_features,
        signal_drift=signal_drift,
        max_signal_drift=round(max_drift, 8),
        learned_weight_drift_l1=round(weight_drift_l1, 8),
        ranking_pair_count=pair_count,
        ranking_flip_count=flip_count,
        ranking_instability=round(instability, 8),
        thresholds={
            "minimum_feature_coverage": minimum_feature_coverage,
            "maximum_signal_drift": maximum_signal_drift,
            "maximum_weight_drift_l1": maximum_weight_drift_l1,
            "maximum_ranking_instability": maximum_ranking_instability,
        },
        reasons=tuple(reasons),
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m job_app_helix.calibration_diagnostics")
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--recent-window", type=int, default=20)
    args = parser.parse_args(argv)

    rows = load_outcome_examples(args.database)
    model = fit_outcome_calibration(rows)
    diagnostics = diagnose_outcome_calibration(
        rows,
        model,
        recent_window=args.recent_window,
    )
    rendered = json.dumps(diagnostics.as_dict(), indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 3 if diagnostics.status == "BLOCK_LEARNED_RANKING" else 0


if __name__ == "__main__":
    raise SystemExit(main())
