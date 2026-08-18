"""Apply calibration diagnostics to decide whether learned ranking may execute.

This policy layer is intentionally small and deterministic. It never mutates application
history or candidate evidence. It converts the diagnostics verdict into the calibration
that downstream ranking is allowed to consume, while preserving a machine-readable reason
for any fallback.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from typing import Mapping

from .calibration_diagnostics import CalibrationDiagnostics
from .outcome_calibration import OutcomeCalibration


@dataclass(frozen=True)
class CalibrationGuardDecision:
    schema: str
    mode: str
    diagnostics_status: str
    source_calibration_status: str
    applied_calibration_status: str
    source_learned_weights: Mapping[str, float]
    applied_weights: Mapping[str, float]
    reasons: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def apply_calibration_guard(
    calibration: OutcomeCalibration,
    diagnostics: CalibrationDiagnostics,
) -> tuple[OutcomeCalibration, CalibrationGuardDecision]:
    """Return the ranking calibration permitted by diagnostics and an audit decision.

    PASS and WARN preserve the fitted model. BLOCK_LEARNED_RANKING deterministically
    replaces learned weights with the proven baseline weights while keeping the original
    fit metadata available in the decision receipt.
    """
    if diagnostics.status not in {"PASS", "WARN", "BLOCK_LEARNED_RANKING"}:
        raise ValueError(f"unsupported calibration diagnostics status: {diagnostics.status}")

    if diagnostics.status == "BLOCK_LEARNED_RANKING":
        guarded = replace(
            calibration,
            status="DIAGNOSTIC_BASELINE_FALLBACK",
            learned_weights=dict(calibration.baseline_weights),
        )
        mode = "BASELINE_FALLBACK"
    else:
        guarded = calibration
        mode = "LEARNED_ALLOWED"

    decision = CalibrationGuardDecision(
        schema="glaciereq.calibration-guard-decision.v1",
        mode=mode,
        diagnostics_status=diagnostics.status,
        source_calibration_status=calibration.status,
        applied_calibration_status=guarded.status,
        source_learned_weights=dict(calibration.learned_weights),
        applied_weights=dict(guarded.learned_weights),
        reasons=tuple(diagnostics.reasons),
    )
    return guarded, decision
