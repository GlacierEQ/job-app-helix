from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import IntEnum

try:
    from enum import StrEnum
except ImportError:
    from enum import Enum

    class StrEnum(str, Enum):
        pass
from pathlib import Path


class PortfolioProgramError(RuntimeError):
    """Raised when the portfolio program contract is invalid or unsafe to execute."""


class VerificationState(StrEnum):
    VERIFIED = "VERIFIED"
    PARTIALLY_VERIFIED = "PARTIALLY_VERIFIED"
    BLOCKED = "BLOCKED"
    UNVERIFIED = "UNVERIFIED"
    FAILED = "FAILED"


class ExecutionMode(StrEnum):
    """What the portfolio runner is trying to make true for a repository.

    ``CONSOLIDATE_OR_ARCHIVE`` remains parseable only so historical rollout
    manifests can be read without losing provenance. Current execution code
    compiles that retired mode to ``PRODUCTIZE`` before a plan is emitted.
    """

    VERIFY = "VERIFY"
    PRODUCTIZE = "PRODUCTIZE"
    INTEGRATE = "INTEGRATE"
    DEPLOY = "DEPLOY"
    OPERATE = "OPERATE"
    EVOLVE = "EVOLVE"
    CONSOLIDATE_OR_ARCHIVE = "CONSOLIDATE_OR_ARCHIVE"

    @property
    def is_active(self) -> bool:
        return self is not ExecutionMode.CONSOLIDATE_OR_ARCHIVE


class EvidenceLevel(IntEnum):
    INVENTORY = 10
    DOCUMENTATION = 20
    STATIC_ANALYSIS = 30
    BUILD = 40
    TEST = 50
    INTEGRATION = 60
    DEPLOYMENT = 70

    @classmethod
    def parse(cls, value: str) -> EvidenceLevel:
        try:
            return cls[value]
        except KeyError as exc:
            raise PortfolioProgramError(f"unknown evidence level: {value!r}") from exc


class ProofMode(StrEnum):
    EXIT_CODE = "EXIT_CODE"
    POSITIVE_TEST_COUNT = "POSITIVE_TEST_COUNT"
    INTERNAL = "INTERNAL"


@dataclass(frozen=True)
class CommandSpec:
    id: str
    evidence_level: EvidenceLevel
    argv: tuple[str, ...]
    timeout_seconds: int
    proof_mode: ProofMode = ProofMode.EXIT_CODE
    minimum_count: int = 0
    mutates_workspace: bool = False
    required: bool = True

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["evidence_level"] = self.evidence_level.name
        payload["proof_mode"] = self.proof_mode.value
        payload["argv"] = list(self.argv)
        payload["continuation"] = (
            self.continuation.to_dict() if self.continuation is not None else None
        )
        return payload


@dataclass(frozen=True)
class Wave:
    id: str
    priority: int
    mode: ExecutionMode
    objective: str
    current_state: VerificationState
    current_evidence: EvidenceLevel
    target_evidence: EvidenceLevel
    repositories: tuple[str, ...]
    require_readme_contract: bool
    require_positive_test_count: bool
    require_build_receipt: bool
    historical_mode: str | None = None


@dataclass(frozen=True)
class RolloutProgram:
    schema: str
    portfolio_root: str
    default_timeout_seconds: int
    promotion_path: tuple[EvidenceLevel, ...]
    fail_closed: bool
    require_atomic_receipts: bool
    require_positive_test_count_for_test_evidence: bool
    waves: tuple[Wave, ...]

    @property
    def repositories(self) -> tuple[str, ...]:
        return tuple(repository for wave in self.waves for repository in wave.repositories)


@dataclass(frozen=True)
class RepositoryPlan:
    repository: str
    wave_id: str
    priority: int
    mode: ExecutionMode
    current_state: VerificationState
    current_evidence: EvidenceLevel
    target_evidence: EvidenceLevel
    path: Path
    stacks: tuple[str, ...]
    commands: tuple[CommandSpec, ...]
    blockers: tuple[str, ...]
    readme_contract_satisfied: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "repository": self.repository,
            "wave_id": self.wave_id,
            "priority": self.priority,
            "mode": self.mode.value,
            "current_state": self.current_state.value,
            "current_evidence": self.current_evidence.name,
            "target_evidence": self.target_evidence.name,
            "path": str(self.path),
            "stacks": list(self.stacks),
            "commands": [command.to_dict() for command in self.commands],
            "blockers": list(self.blockers),
            "readme_contract_satisfied": self.readme_contract_satisfied,
        }


@dataclass(frozen=True)
class CommandContinuation:
    """A capability-recovery program for a command that did not yet verify.

    Continuations preserve the original receipt and never assert that a command
    executed, passed, or mutated a workspace. They turn an observable execution
    state into a concrete next operational path.
    """

    command_id: str
    capability: str
    reason: str
    next_actions: tuple[str, ...]
    explicit_authorization_required: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "command_id": self.command_id,
            "capability": self.capability,
            "reason": self.reason,
            "next_actions": list(self.next_actions),
            "explicit_authorization_required": self.explicit_authorization_required,
        }


@dataclass(frozen=True)
class CommandReceipt:
    id: str
    evidence_level: EvidenceLevel
    argv: tuple[str, ...]
    required: bool
    status: VerificationState
    returncode: int | None
    elapsed_ms: float
    timed_out: bool
    observed_count: int | None
    stdout_tail: str
    stderr_tail: str
    continuation: CommandContinuation | None = None

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["evidence_level"] = self.evidence_level.name
        payload["status"] = self.status.value
        payload["argv"] = list(self.argv)
        return payload


@dataclass(frozen=True)
class RepositoryReceipt:
    repository: str
    wave_id: str
    conclusion: VerificationState
    achieved_evidence: EvidenceLevel
    target_evidence: EvidenceLevel
    blockers: tuple[str, ...]
    commands: tuple[CommandReceipt, ...]
    continuations: tuple[CommandContinuation, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "repository": self.repository,
            "wave_id": self.wave_id,
            "conclusion": self.conclusion.value,
            "achieved_evidence": self.achieved_evidence.name,
            "target_evidence": self.target_evidence.name,
            "blockers": list(self.blockers),
            "commands": [command.to_dict() for command in self.commands],
            "continuations": [continuation.to_dict() for continuation in self.continuations],
        }
