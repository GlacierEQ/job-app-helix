from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Final

from .portfolio_discovery import readme_contract
from .portfolio_models import (
    CommandReceipt,
    CommandSpec,
    EvidenceLevel,
    ProofMode,
    RepositoryPlan,
    RepositoryReceipt,
    RolloutProgram,
    VerificationState,
)

TAIL_LIMIT: Final = 4000
TEST_COUNT_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"Ran\s+(\d+)\s+tests?", re.IGNORECASE),
    re.compile(r"(\d+)\s+passed(?:\s|,|$)", re.IGNORECASE),
    re.compile(r"Tests:\s+(\d+)\s+passed", re.IGNORECASE),
    re.compile(r"(\d+)\s+passing", re.IGNORECASE),
    re.compile(r"test result:\s+ok\.\s+(\d+)\s+passed", re.IGNORECASE),
)


def _tail(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        value = value.decode(errors="replace")
    return value[-TAIL_LIMIT:]


def extract_test_count(
    stdout: str,
    stderr: str,
    argv: tuple[str, ...],
) -> int | None:
    combined = f"{stdout}\n{stderr}"
    counts = [
        int(match.group(1))
        for pattern in TEST_COUNT_PATTERNS
        for match in pattern.finditer(combined)
    ]
    if counts:
        return max(counts)

    if argv[:2] == ("go", "test"):
        package_successes = len(re.findall(r"(?m)^ok\s+\S+", combined))
        return package_successes or None

    if argv and argv[0] in {"mvn", "./gradlew", "dotnet", "swift"}:
        success_markers = (
            "BUILD SUCCESS",
            "BUILD SUCCESSFUL",
            "Test Run Successful",
            "Executed 1 test",
            "passed after",
        )
        return 1 if any(marker in combined for marker in success_markers) else None

    return None


def _internal_receipt(
    plan: RepositoryPlan,
    command: CommandSpec,
) -> CommandReceipt:
    start = time.perf_counter()
    readme_ok, errors = readme_contract(plan.path)
    elapsed_ms = round((time.perf_counter() - start) * 1000.0, 2)
    return CommandReceipt(
        id=command.id,
        evidence_level=command.evidence_level,
        argv=command.argv,
        required=command.required,
        status=VerificationState.VERIFIED if readme_ok else VerificationState.FAILED,
        returncode=0 if readme_ok else 1,
        elapsed_ms=elapsed_ms,
        timed_out=False,
        observed_count=None,
        stdout_tail="README contract satisfied" if readme_ok else "",
        stderr_tail="; ".join(errors),
    )


def run_command(
    plan: RepositoryPlan,
    command: CommandSpec,
    *,
    allow_mutating: bool,
) -> CommandReceipt:
    if command.proof_mode is ProofMode.INTERNAL:
        return _internal_receipt(plan, command)

    if command.mutates_workspace and not allow_mutating:
        return CommandReceipt(
            id=command.id,
            evidence_level=command.evidence_level,
            argv=command.argv,
            required=command.required,
            status=VerificationState.BLOCKED,
            returncode=None,
            elapsed_ms=0.0,
            timed_out=False,
            observed_count=None,
            stdout_tail="",
            stderr_tail="mutating command blocked; rerun with explicit authorization",
        )

    executable = command.argv[0]
    executable_exists = shutil.which(executable) is not None
    if executable.startswith("./"):
        executable_exists = (plan.path / executable).is_file()
    if not executable_exists:
        return CommandReceipt(
            id=command.id,
            evidence_level=command.evidence_level,
            argv=command.argv,
            required=command.required,
            status=VerificationState.BLOCKED,
            returncode=None,
            elapsed_ms=0.0,
            timed_out=False,
            observed_count=None,
            stdout_tail="",
            stderr_tail=f"required executable is unavailable: {executable}",
        )

    env = os.environ.copy()
    env.update({"CI": "1", "PYTHONUNBUFFERED": "1"})
    start = time.perf_counter()
    try:
        completed = subprocess.run(
            list(command.argv),
            cwd=plan.path,
            env=env,
            capture_output=True,
            text=True,
            check=False,
            timeout=command.timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        return CommandReceipt(
            id=command.id,
            evidence_level=command.evidence_level,
            argv=command.argv,
            required=command.required,
            status=VerificationState.FAILED,
            returncode=124,
            elapsed_ms=round((time.perf_counter() - start) * 1000.0, 2),
            timed_out=True,
            observed_count=None,
            stdout_tail=_tail(exc.stdout),
            stderr_tail=(
                f"timed out after {command.timeout_seconds}s; {_tail(exc.stderr)}"
            ).strip(),
        )

    elapsed_ms = round((time.perf_counter() - start) * 1000.0, 2)
    stdout = _tail(completed.stdout)
    stderr = _tail(completed.stderr)
    count = extract_test_count(stdout, stderr, command.argv)

    if completed.returncode != 0:
        status = VerificationState.FAILED
    elif command.proof_mode is ProofMode.POSITIVE_TEST_COUNT and (
        count is None or count < command.minimum_count
    ):
        status = VerificationState.UNVERIFIED
        stderr = (
            f"command exited zero but positive proof count was {count!r}; "
            f"minimum required is {command.minimum_count}. {stderr}"
        ).strip()
    else:
        status = VerificationState.VERIFIED

    return CommandReceipt(
        id=command.id,
        evidence_level=command.evidence_level,
        argv=command.argv,
        required=command.required,
        status=status,
        returncode=completed.returncode,
        elapsed_ms=elapsed_ms,
        timed_out=False,
        observed_count=count,
        stdout_tail=stdout,
        stderr_tail=stderr,
    )


def execute_plan(
    plans: tuple[RepositoryPlan, ...],
    *,
    allow_mutating: bool = False,
) -> tuple[RepositoryReceipt, ...]:
    receipts: list[RepositoryReceipt] = []

    for plan in plans:
        command_receipts = tuple(
            run_command(plan, command, allow_mutating=allow_mutating)
            for command in plan.commands
        )
        verified_levels = [
            receipt.evidence_level
            for receipt in command_receipts
            if receipt.status is VerificationState.VERIFIED
        ]
        achieved = max(verified_levels, default=EvidenceLevel.INVENTORY)
        required_statuses = {
            receipt.status for receipt in command_receipts if receipt.required
        }

        if plan.blockers:
            conclusion = VerificationState.BLOCKED
        elif VerificationState.FAILED in required_statuses:
            conclusion = VerificationState.FAILED
        elif VerificationState.BLOCKED in required_statuses:
            conclusion = VerificationState.BLOCKED
        elif VerificationState.UNVERIFIED in required_statuses:
            conclusion = VerificationState.UNVERIFIED
        elif achieved >= plan.target_evidence:
            conclusion = VerificationState.VERIFIED
        else:
            conclusion = VerificationState.PARTIALLY_VERIFIED

        receipts.append(
            RepositoryReceipt(
                repository=plan.repository,
                wave_id=plan.wave_id,
                conclusion=conclusion,
                achieved_evidence=achieved,
                target_evidence=plan.target_evidence,
                blockers=plan.blockers,
                commands=command_receipts,
            )
        )

    return tuple(receipts)


def atomic_write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temp_path = Path(handle.name)
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()


def plan_payload(plans: tuple[RepositoryPlan, ...]) -> dict[str, object]:
    return {
        "schema": "glaciereq.portfolio.execution-plan.v1",
        "repositories": [plan.to_dict() for plan in plans],
        "summary": {
            "repositories": len(plans),
            "blocked": sum(bool(plan.blockers) for plan in plans),
            "readme_contract_satisfied": sum(
                plan.readme_contract_satisfied for plan in plans
            ),
            "waves": sorted({plan.wave_id for plan in plans}),
        },
    }


def receipt_payload(
    receipts: tuple[RepositoryReceipt, ...],
    *,
    started_at_epoch_ms: int,
) -> dict[str, object]:
    conclusions = [receipt.conclusion for receipt in receipts]
    if any(state is VerificationState.FAILED for state in conclusions):
        conclusion = VerificationState.FAILED
    elif any(state is VerificationState.BLOCKED for state in conclusions):
        conclusion = VerificationState.BLOCKED
    elif any(state is VerificationState.UNVERIFIED for state in conclusions):
        conclusion = VerificationState.UNVERIFIED
    elif receipts and all(
        state is VerificationState.VERIFIED for state in conclusions
    ):
        conclusion = VerificationState.VERIFIED
    else:
        conclusion = VerificationState.PARTIALLY_VERIFIED

    return {
        "schema": "glaciereq.portfolio.execution-receipt.v1",
        "started_at_epoch_ms": started_at_epoch_ms,
        "completed_at_epoch_ms": int(time.time() * 1000),
        "conclusion": conclusion.value,
        "repositories": [receipt.to_dict() for receipt in receipts],
        "summary": {
            state.value: sum(receipt.conclusion is state for receipt in receipts)
            for state in VerificationState
        },
    }


def render_plan_markdown(plans: tuple[RepositoryPlan, ...]) -> str:
    lines = [
        "# Portfolio Verification Execution Plan",
        "",
        "This document is generated from the exact inventory and rollout contract.",
        "It is a plan, not a runtime receipt.",
        "",
        "| Priority | Wave | Repository | Mode | Current | Target | Stack | Blockers |",
        "|---:|---|---|---|---|---|---|---|",
    ]

    for plan in plans:
        blockers = "<br>".join(plan.blockers) if plan.blockers else "None detected"
        stacks = ", ".join(plan.stacks) if plan.stacks else "Undetected"
        lines.append(
            f"| {plan.priority} | `{plan.wave_id}` | `{plan.repository}` | "
            f"{plan.mode.value} | {plan.current_evidence.name} | "
            f"{plan.target_evidence.name} | {stacks} | {blockers} |"
        )

    lines.extend(
        [
            "",
            "## Promotion rule",
            "",
            "A repository is promoted only when its required README contract, build/test "
            "commands, positive proof counts, and target evidence level are all satisfied. "
            "Missing tools, missing tests, timeouts, and zero-test exits remain visible as "
            "BLOCKED, FAILED, or UNVERIFIED states.",
            "",
        ]
    )
    return "\n".join(lines)


def render_program_markdown(program: RolloutProgram) -> str:
    lines = [
        "# Portfolio Rollout Program",
        "",
        f"Schema: `{program.schema}`",
        "",
        "## Global promotion policy",
        "",
        "- Evidence ladder: "
        + " → ".join(level.name for level in program.promotion_path),
        f"- Fail closed: `{program.fail_closed}`",
        f"- Atomic receipts: `{program.require_atomic_receipts}`",
        "- Positive test counts required: "
        f"`{program.require_positive_test_count_for_test_evidence}`",
        "",
    ]

    for wave in program.waves:
        lines.extend(
            [
                f"## {wave.id}",
                "",
                f"**Priority:** {wave.priority}  ",
                f"**Mode:** {wave.mode.value}  ",
                f"**Evidence:** {wave.current_evidence.name} → "
                f"{wave.target_evidence.name}  ",
                f"**Current state:** {wave.current_state.value}",
                "",
                wave.objective,
                "",
                f"Repositories: **{len(wave.repositories)}**",
                "",
                *[f"- `{repository}`" for repository in wave.repositories],
                "",
            ]
        )

    return "\n".join(lines)
