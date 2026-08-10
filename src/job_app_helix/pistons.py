from __future__ import annotations

from dataclasses import dataclass, replace

from .models import Finding, Refinement, StageResult, StageStatus


@dataclass(frozen=True)
class FlightInputs:
    expected_frames: int = 1_000
    received_frames: int = 995
    max_event_severity: int = 2
    backup_frames: int = 0


@dataclass(frozen=True)
class PropulsionInputs:
    chamber_pressure_ratio: float = 0.98
    mixture_ratio_error: float = 0.02
    vibration_g: float = 3.2
    derated_chamber_pressure_ratio: float | None = None
    derated_vibration_g: float | None = None


@dataclass(frozen=True)
class GroundInputs:
    required_mbps: float = 55.0
    available_mbps: float = 72.0
    route_available: bool = True
    backup_capacity_mbps: float = 0.0
    alternate_route_available: bool = False


def _status_from_findings(findings: list[Finding]) -> StageStatus:
    if any(finding.severity is StageStatus.NO_GO for finding in findings):
        return StageStatus.NO_GO
    if findings:
        return StageStatus.WARN
    return StageStatus.GO


def assess_flight(inputs: FlightInputs) -> StageResult:
    if inputs.expected_frames <= 0:
        raise ValueError("expected_frames must be positive")
    if inputs.received_frames < 0:
        raise ValueError("received_frames cannot be negative")

    completeness = min(inputs.received_frames / inputs.expected_frames, 1.0)
    findings: list[Finding] = []

    if completeness < 0.95:
        findings.append(
            Finding(
                code="FLIGHT_TELEMETRY_INCOMPLETE",
                message=f"Telemetry completeness is {completeness:.1%}; minimum is 95%.",
                severity=StageStatus.NO_GO,
            )
        )
    elif completeness < 0.99:
        findings.append(
            Finding(
                code="FLIGHT_TELEMETRY_DEGRADED",
                message=(
                    f"Telemetry completeness is {completeness:.1%}; "
                    "investigate dropped frames."
                ),
                severity=StageStatus.WARN,
            )
        )

    if inputs.max_event_severity >= 4:
        findings.append(
            Finding(
                code="FLIGHT_CRITICAL_EVENT",
                message=f"A severity-{inputs.max_event_severity} flight event requires a hold.",
                severity=StageStatus.NO_GO,
            )
        )
    elif inputs.max_event_severity == 3:
        findings.append(
            Finding(
                code="FLIGHT_ELEVATED_EVENT",
                message="A severity-3 event requires operator acknowledgement.",
                severity=StageStatus.WARN,
            )
        )

    status = _status_from_findings(findings)
    summary = {
        StageStatus.GO: "Flight telemetry and event state support launch progression.",
        StageStatus.WARN: "Flight state is usable with explicit operator acknowledgement.",
        StageStatus.NO_GO: "Flight evidence does not support launch progression.",
    }[status]
    return StageResult(
        name="flight-awareness",
        status=status,
        summary=summary,
        metrics={
            "expected_frames": inputs.expected_frames,
            "received_frames": inputs.received_frames,
            "telemetry_completeness": round(completeness, 6),
            "max_event_severity": inputs.max_event_severity,
        },
        findings=tuple(findings),
    )


def assess_propulsion(inputs: PropulsionInputs) -> StageResult:
    findings: list[Finding] = []

    if not 0.92 <= inputs.chamber_pressure_ratio <= 1.06:
        findings.append(
            Finding(
                code="PROP_CHAMBER_PRESSURE",
                message=(
                    "Chamber pressure ratio is outside the demonstrated operating envelope "
                    f"({inputs.chamber_pressure_ratio:.3f})."
                ),
                severity=StageStatus.NO_GO,
            )
        )
    elif not 0.95 <= inputs.chamber_pressure_ratio <= 1.03:
        findings.append(
            Finding(
                code="PROP_CHAMBER_MARGIN",
                message="Chamber pressure is inside the envelope but close to a limit.",
                severity=StageStatus.WARN,
            )
        )

    if inputs.mixture_ratio_error > 0.08:
        findings.append(
            Finding(
                code="PROP_MIXTURE_RATIO",
                message=f"Mixture-ratio error {inputs.mixture_ratio_error:.3f} exceeds 0.08.",
                severity=StageStatus.NO_GO,
            )
        )
    elif inputs.mixture_ratio_error > 0.05:
        findings.append(
            Finding(
                code="PROP_MIXTURE_MARGIN",
                message="Mixture-ratio error is approaching the demonstrated limit.",
                severity=StageStatus.WARN,
            )
        )

    if inputs.vibration_g > 8.0:
        findings.append(
            Finding(
                code="PROP_VIBRATION",
                message=f"Vibration {inputs.vibration_g:.2f} g exceeds the 8.0 g hold threshold.",
                severity=StageStatus.NO_GO,
            )
        )
    elif inputs.vibration_g > 6.0:
        findings.append(
            Finding(
                code="PROP_VIBRATION_MARGIN",
                message="Vibration is elevated and requires trending.",
                severity=StageStatus.WARN,
            )
        )

    status = _status_from_findings(findings)
    summary = {
        StageStatus.GO: "Propulsion health remains inside the demonstrated envelope.",
        StageStatus.WARN: "Propulsion is inside hard limits with reduced margin.",
        StageStatus.NO_GO: "Propulsion evidence requires a launch hold.",
    }[status]
    return StageResult(
        name="propulsion-health",
        status=status,
        summary=summary,
        metrics={
            "chamber_pressure_ratio": round(inputs.chamber_pressure_ratio, 6),
            "mixture_ratio_error": round(inputs.mixture_ratio_error, 6),
            "vibration_g": round(inputs.vibration_g, 6),
        },
        findings=tuple(findings),
    )


def assess_ground(inputs: GroundInputs) -> StageResult:
    if inputs.required_mbps <= 0:
        raise ValueError("required_mbps must be positive")
    if inputs.available_mbps < 0:
        raise ValueError("available_mbps cannot be negative")

    capacity_margin = inputs.available_mbps - inputs.required_mbps
    margin_ratio = capacity_margin / inputs.required_mbps
    findings: list[Finding] = []

    if not inputs.route_available:
        findings.append(
            Finding(
                code="GROUND_ROUTE_UNAVAILABLE",
                message="No verified ground-to-mesh route is available.",
                severity=StageStatus.NO_GO,
            )
        )

    if capacity_margin < 0:
        findings.append(
            Finding(
                code="GROUND_CAPACITY_SHORTFALL",
                message=f"Ground capacity is short by {abs(capacity_margin):.1f} Mbps.",
                severity=StageStatus.NO_GO,
            )
        )
    elif margin_ratio < 0.20:
        findings.append(
            Finding(
                code="GROUND_CAPACITY_MARGIN",
                message=f"Ground capacity margin is only {margin_ratio:.1%}.",
                severity=StageStatus.WARN,
            )
        )

    status = _status_from_findings(findings)
    summary = {
        StageStatus.GO: "Ground capacity and route evidence support campaign progression.",
        StageStatus.WARN: "Ground connectivity is available with limited reserve margin.",
        StageStatus.NO_GO: "Ground connectivity cannot support the campaign requirement.",
    }[status]
    return StageResult(
        name="ground-network",
        status=status,
        summary=summary,
        metrics={
            "required_mbps": round(inputs.required_mbps, 3),
            "available_mbps": round(inputs.available_mbps, 3),
            "capacity_margin_mbps": round(capacity_margin, 3),
            "capacity_margin_ratio": round(margin_ratio, 6),
            "route_available": inputs.route_available,
        },
        findings=tuple(findings),
    )


def refine_flight(
    inputs: FlightInputs,
    result: StageResult,
) -> tuple[FlightInputs, Refinement | None]:
    if result.status is not StageStatus.NO_GO or inputs.backup_frames <= 0:
        return inputs, None

    recovered_frames = min(inputs.expected_frames, inputs.received_frames + inputs.backup_frames)
    refined = replace(inputs, received_frames=recovered_frames, backup_frames=0)
    return refined, Refinement(
        stage=result.name,
        action="replay-buffered-telemetry",
        rationale="Use an explicitly supplied backup frame buffer; never invent missing evidence.",
    )


def refine_propulsion(
    inputs: PropulsionInputs,
    result: StageResult,
) -> tuple[PropulsionInputs, Refinement | None]:
    if result.status is not StageStatus.NO_GO:
        return inputs, None
    if inputs.derated_chamber_pressure_ratio is None or inputs.derated_vibration_g is None:
        return inputs, None

    refined = replace(
        inputs,
        chamber_pressure_ratio=inputs.derated_chamber_pressure_ratio,
        vibration_g=inputs.derated_vibration_g,
        derated_chamber_pressure_ratio=None,
        derated_vibration_g=None,
    )
    return refined, Refinement(
        stage=result.name,
        action="apply-predeclared-derated-profile",
        rationale=(
            "Reassess using a supplied contingency profile rather than silently tuning to pass."
        ),
    )


def refine_ground(
    inputs: GroundInputs,
    result: StageResult,
) -> tuple[GroundInputs, Refinement | None]:
    if result.status is not StageStatus.NO_GO:
        return inputs, None
    if inputs.backup_capacity_mbps <= 0 and not inputs.alternate_route_available:
        return inputs, None

    refined = replace(
        inputs,
        available_mbps=inputs.available_mbps + inputs.backup_capacity_mbps,
        route_available=inputs.route_available or inputs.alternate_route_available,
        backup_capacity_mbps=0.0,
        alternate_route_available=False,
    )
    return refined, Refinement(
        stage=result.name,
        action="activate-declared-ground-contingency",
        rationale="Add only the backup capacity and alternate route declared in the scenario.",
    )
