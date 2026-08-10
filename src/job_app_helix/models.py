from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


class StageStatus(StrEnum):
    """Operational state of one campaign stage."""

    GO = "GO"
    WARN = "WARN"
    NO_GO = "NO-GO"


class CampaignDecision(StrEnum):
    """Final campaign-level decision."""

    GO = "GO"
    NO_GO = "NO-GO"


@dataclass(frozen=True)
class Finding:
    """Human-readable evidence explaining a stage decision."""

    code: str
    message: str
    severity: StageStatus


@dataclass(frozen=True)
class StageResult:
    """One deterministic build-or-verify piston result."""

    name: str
    status: StageStatus
    summary: str
    metrics: dict[str, float | int | bool | str]
    findings: tuple[Finding, ...] = ()

    @property
    def acceptable(self) -> bool:
        return self.status is not StageStatus.NO_GO

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["status"] = self.status.value
        payload["findings"] = [
            {
                "code": finding.code,
                "message": finding.message,
                "severity": finding.severity.value,
            }
            for finding in self.findings
        ]
        return payload


@dataclass(frozen=True)
class Refinement:
    """A transparent response applied between the first and final campaign stroke."""

    stage: str
    action: str
    rationale: str


@dataclass(frozen=True)
class CampaignReport:
    """Complete proof receipt for a campaign run."""

    scenario: str
    initial_results: tuple[StageResult, ...]
    final_results: tuple[StageResult, ...]
    decision: CampaignDecision
    refinements: tuple[Refinement, ...] = ()
    protocol: str = "build -> verify -> refine -> decide"
    metadata: dict[str, str] = field(default_factory=dict)

    @property
    def recovered(self) -> bool:
        initial_failed = any(not result.acceptable for result in self.initial_results)
        return initial_failed and self.decision is CampaignDecision.GO

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario": self.scenario,
            "protocol": self.protocol,
            "decision": self.decision.value,
            "recovered": self.recovered,
            "initial_results": [result.to_dict() for result in self.initial_results],
            "refinements": [asdict(refinement) for refinement in self.refinements],
            "final_results": [result.to_dict() for result in self.final_results],
            "metadata": dict(self.metadata),
        }
