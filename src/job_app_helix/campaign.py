from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from .models import CampaignDecision, CampaignReport, Refinement, StageResult
from .pistons import (
    FlightInputs,
    GroundInputs,
    PropulsionInputs,
    assess_flight,
    assess_ground,
    assess_propulsion,
    refine_flight,
    refine_ground,
    refine_propulsion,
)


@dataclass(frozen=True, slots=True)
class CampaignPolicy:
    """Controls whether one transparent contingency stroke may be applied."""

    allow_refinement: bool = True


@dataclass(frozen=True, slots=True)
class LaunchScenario:
    """All evidence required for a deterministic campaign decision."""

    name: str
    flight: FlightInputs
    propulsion: PropulsionInputs
    ground: GroundInputs

    @classmethod
    def nominal(cls) -> LaunchScenario:
        return cls(
            name="nominal",
            flight=FlightInputs(),
            propulsion=PropulsionInputs(),
            ground=GroundInputs(),
        )

    @classmethod
    def recoverable(cls) -> LaunchScenario:
        return cls(
            name="recoverable",
            flight=FlightInputs(received_frames=900, backup_frames=95),
            propulsion=PropulsionInputs(
                chamber_pressure_ratio=0.89,
                mixture_ratio_error=0.03,
                vibration_g=8.6,
                derated_chamber_pressure_ratio=0.97,
                derated_vibration_g=4.1,
            ),
            ground=GroundInputs(
                available_mbps=40.0,
                route_available=False,
                backup_capacity_mbps=35.0,
                alternate_route_available=True,
            ),
        )

    @classmethod
    def hard_no_go(cls) -> LaunchScenario:
        return cls(
            name="hard-no-go",
            flight=FlightInputs(received_frames=700, max_event_severity=5),
            propulsion=PropulsionInputs(
                chamber_pressure_ratio=0.84,
                mixture_ratio_error=0.12,
                vibration_g=10.0,
            ),
            ground=GroundInputs(available_mbps=20.0, route_available=False),
        )


def _assess(scenario: LaunchScenario) -> tuple[StageResult, ...]:
    return (
        assess_flight(scenario.flight),
        assess_propulsion(scenario.propulsion),
        assess_ground(scenario.ground),
    )


def _decision(results: tuple[StageResult, ...]) -> CampaignDecision:
    if all(result.acceptable for result in results):
        return CampaignDecision.GO
    return CampaignDecision.NO_GO


def _refine(
    scenario: LaunchScenario,
    initial_results: tuple[StageResult, ...],
) -> tuple[LaunchScenario, tuple[Refinement, ...]]:
    flight, flight_refinement = refine_flight(scenario.flight, initial_results[0])
    propulsion, propulsion_refinement = refine_propulsion(
        scenario.propulsion,
        initial_results[1],
    )
    ground, ground_refinement = refine_ground(scenario.ground, initial_results[2])

    refinements = tuple(
        refinement
        for refinement in (flight_refinement, propulsion_refinement, ground_refinement)
        if refinement is not None
    )
    return (
        LaunchScenario(
            name=scenario.name,
            flight=flight,
            propulsion=propulsion,
            ground=ground,
        ),
        refinements,
    )


def run_campaign(
    scenario: LaunchScenario,
    policy: CampaignPolicy | None = None,
) -> CampaignReport:
    """Run build, verification, one evidence-backed refinement stroke, and final decision.

    No stage is allowed to tune itself until it passes. A refinement can consume only
    contingency evidence explicitly present in the input scenario.
    """

    active_policy = policy or CampaignPolicy()
    initial_results = _assess(scenario)
    final_results = initial_results
    refinements: tuple[Refinement, ...] = ()

    if _decision(initial_results) is CampaignDecision.NO_GO and active_policy.allow_refinement:
        refined_scenario, refinements = _refine(scenario, initial_results)
        if refinements:
            final_results = _assess(refined_scenario)

    return CampaignReport(
        scenario=scenario.name,
        initial_results=initial_results,
        final_results=final_results,
        decision=_decision(final_results),
        refinements=refinements,
        metadata={
            "engine": "job-app-helix",
            "engine_version": "0.1.0",
            "generated_at": datetime.now(UTC).isoformat(),
        },
    )
