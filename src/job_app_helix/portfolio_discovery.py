from __future__ import annotations

import json
import re
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any, Final

from .portfolio_contract import validate_program
from .portfolio_models import (
    CommandSpec,
    EvidenceLevel,
    ExecutionMode,
    PortfolioProgramError,
    ProofMode,
    RepositoryPlan,
)

README_HEADINGS: Final[tuple[str, ...]] = (
    "## For recruiters and non-technical reviewers",
    "## For senior engineers and domain experts",
    "## For AI systems and toolchains",
)
FILE_URL_PREFIX: Final = "file:" + "/" * 3
MAC_USER_PREFIX: Final = "/" + "Users" + "/"
LOCAL_PATH_RE: Final = re.compile(
    "|".join(
        (
            re.escape(FILE_URL_PREFIX),
            re.escape(MAC_USER_PREFIX),
            r"[A-Za-z]:\\\\Users\\\\",
        )
    )
)


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def readme_contract(path: Path) -> tuple[bool, tuple[str, ...]]:
    readme = path / "README.md"
    if not readme.is_file():
        return False, ("missing README.md",)

    text = readme.read_text(encoding="utf-8", errors="replace")
    missing = tuple(heading for heading in README_HEADINGS if heading not in text)
    positions = [text.index(heading) for heading in README_HEADINGS if heading in text]
    ordered = len(positions) == len(README_HEADINGS) and positions == sorted(positions)

    errors = list(missing)
    if not ordered and not missing:
        errors.append("README audience sections are out of order")
    if LOCAL_PATH_RE.search(text):
        errors.append("README exposes a machine-local path")
    return not errors, tuple(errors)


def _python_commands(path: Path, timeout: int) -> list[CommandSpec]:
    commands = [
        CommandSpec(
            id="python-compile",
            evidence_level=EvidenceLevel.STATIC_ANALYSIS,
            argv=(sys.executable, "-m", "compileall", "-q", "."),
            timeout_seconds=timeout,
        )
    ]
    has_tests = (path / "tests").is_dir() or any(path.glob("test_*.py"))
    if not has_tests:
        return commands

    pyproject_text = ""
    pyproject = path / "pyproject.toml"
    if pyproject.is_file():
        pyproject_text = pyproject.read_text(encoding="utf-8", errors="replace")

    if (
        "pytest" in pyproject_text
        or (path / "pytest.ini").is_file()
        or (path / "conftest.py").is_file()
    ):
        argv = (sys.executable, "-m", "pytest", "-q")
    else:
        start = "tests" if (path / "tests").is_dir() else "."
        argv = (sys.executable, "-m", "unittest", "discover", "-s", start)

    commands.append(
        CommandSpec(
            id="python-tests",
            evidence_level=EvidenceLevel.TEST,
            argv=argv,
            timeout_seconds=timeout,
            proof_mode=ProofMode.POSITIVE_TEST_COUNT,
            minimum_count=1,
        )
    )
    return commands


def _node_runner(path: Path) -> tuple[str, ...]:
    if (path / "pnpm-lock.yaml").is_file():
        return ("pnpm",)
    if (path / "yarn.lock").is_file():
        return ("yarn",)
    return ("npm", "run")


def _node_commands(path: Path, timeout: int) -> list[CommandSpec]:
    package = _read_json(path / "package.json") or {}
    scripts = package.get("scripts")
    if not isinstance(scripts, dict):
        return []

    runner = _node_runner(path)
    commands: list[CommandSpec] = []
    for script, level, proof_mode, minimum, mutates in (
        ("lint", EvidenceLevel.STATIC_ANALYSIS, ProofMode.EXIT_CODE, 0, False),
        ("typecheck", EvidenceLevel.STATIC_ANALYSIS, ProofMode.EXIT_CODE, 0, False),
        ("build", EvidenceLevel.BUILD, ProofMode.EXIT_CODE, 0, True),
        ("test", EvidenceLevel.TEST, ProofMode.POSITIVE_TEST_COUNT, 1, False),
    ):
        if not isinstance(scripts.get(script), str):
            continue
        commands.append(
            CommandSpec(
                id=f"node-{script}",
                evidence_level=level,
                argv=(*runner, script),
                timeout_seconds=timeout,
                proof_mode=proof_mode,
                minimum_count=minimum,
                mutates_workspace=mutates,
            )
        )
    return commands


def _rust_commands(timeout: int) -> tuple[CommandSpec, ...]:
    return (
        CommandSpec(
            id="rust-fmt",
            evidence_level=EvidenceLevel.STATIC_ANALYSIS,
            argv=("cargo", "fmt", "--all", "--", "--check"),
            timeout_seconds=timeout,
        ),
        CommandSpec(
            id="rust-clippy",
            evidence_level=EvidenceLevel.STATIC_ANALYSIS,
            argv=(
                "cargo",
                "clippy",
                "--all-targets",
                "--all-features",
                "--",
                "-D",
                "warnings",
            ),
            timeout_seconds=timeout,
        ),
        CommandSpec(
            id="rust-tests",
            evidence_level=EvidenceLevel.TEST,
            argv=("cargo", "test", "--all-targets", "--all-features"),
            timeout_seconds=timeout,
            proof_mode=ProofMode.POSITIVE_TEST_COUNT,
            minimum_count=1,
        ),
    )


def _go_commands(timeout: int) -> tuple[CommandSpec, ...]:
    return (
        CommandSpec(
            id="go-vet",
            evidence_level=EvidenceLevel.STATIC_ANALYSIS,
            argv=("go", "vet", "./..."),
            timeout_seconds=timeout,
        ),
        CommandSpec(
            id="go-tests",
            evidence_level=EvidenceLevel.TEST,
            argv=("go", "test", "-count=1", "./..."),
            timeout_seconds=timeout,
            proof_mode=ProofMode.POSITIVE_TEST_COUNT,
            minimum_count=1,
        ),
    )


def _cmake_commands(timeout: int) -> tuple[CommandSpec, ...]:
    return (
        CommandSpec(
            id="cmake-configure",
            evidence_level=EvidenceLevel.BUILD,
            argv=("cmake", "-S", ".", "-B", "build/portfolio-proof"),
            timeout_seconds=timeout,
            mutates_workspace=True,
        ),
        CommandSpec(
            id="cmake-build",
            evidence_level=EvidenceLevel.BUILD,
            argv=("cmake", "--build", "build/portfolio-proof"),
            timeout_seconds=timeout,
            mutates_workspace=True,
        ),
    )


def commands_for_stack(
    path: Path,
    timeout: int,
) -> tuple[tuple[str, ...], tuple[CommandSpec, ...]]:
    stacks: list[str] = []
    commands: list[CommandSpec] = []

    if any(
        (path / marker).is_file()
        for marker in ("pyproject.toml", "setup.py", "requirements.txt")
    ):
        stacks.append("python")
        commands.extend(_python_commands(path, timeout))

    if (path / "package.json").is_file():
        stacks.append("node")
        commands.extend(_node_commands(path, timeout))

    if (path / "Cargo.toml").is_file():
        stacks.append("rust")
        commands.extend(_rust_commands(timeout))

    if (path / "go.mod").is_file():
        stacks.append("go")
        commands.extend(_go_commands(timeout))

    if (path / "Package.swift").is_file():
        stacks.append("swift")
        commands.append(
            CommandSpec(
                id="swift-tests",
                evidence_level=EvidenceLevel.TEST,
                argv=("swift", "test"),
                timeout_seconds=timeout,
                proof_mode=ProofMode.POSITIVE_TEST_COUNT,
                minimum_count=1,
            )
        )

    if (path / "pom.xml").is_file():
        stacks.append("maven")
        commands.append(
            CommandSpec(
                id="maven-tests",
                evidence_level=EvidenceLevel.TEST,
                argv=("mvn", "--batch-mode", "test"),
                timeout_seconds=timeout,
                proof_mode=ProofMode.POSITIVE_TEST_COUNT,
                minimum_count=1,
            )
        )

    if (path / "gradlew").is_file():
        stacks.append("gradle")
        commands.append(
            CommandSpec(
                id="gradle-tests",
                evidence_level=EvidenceLevel.TEST,
                argv=("./gradlew", "--no-daemon", "test"),
                timeout_seconds=timeout,
                proof_mode=ProofMode.POSITIVE_TEST_COUNT,
                minimum_count=1,
            )
        )

    if (path / "CMakeLists.txt").is_file():
        stacks.append("cmake")
        commands.extend(_cmake_commands(timeout))

    if any(path.glob("*.csproj")) or any(path.glob("*.sln")):
        stacks.append("dotnet")
        commands.append(
            CommandSpec(
                id="dotnet-tests",
                evidence_level=EvidenceLevel.TEST,
                argv=("dotnet", "test", "--nologo"),
                timeout_seconds=timeout,
                proof_mode=ProofMode.POSITIVE_TEST_COUNT,
                minimum_count=1,
            )
        )

    deduplicated: dict[str, CommandSpec] = {}
    for command in commands:
        deduplicated.setdefault(command.id, command)
    return tuple(stacks), tuple(deduplicated.values())


def build_plan(
    *,
    workspace: Path,
    inventory_path: Path,
    rollout_path: Path,
    wave_ids: set[str] | None = None,
) -> tuple[RepositoryPlan, ...]:
    program = validate_program(inventory_path=inventory_path, rollout_path=rollout_path)
    workspace = workspace.resolve()

    selected_waves = [
        wave for wave in program.waves if wave_ids is None or wave.id in wave_ids
    ]
    if wave_ids is not None:
        unknown = wave_ids - {wave.id for wave in program.waves}
        if unknown:
            raise PortfolioProgramError(f"unknown rollout wave(s): {sorted(unknown)}")

    plans: list[RepositoryPlan] = []
    for wave in selected_waves:
        for repository in sorted(wave.repositories):
            path = (workspace / repository).resolve()
            if not path.is_relative_to(workspace):
                raise PortfolioProgramError(f"repository path escapes workspace: {repository}")

            blockers: list[str] = []
            if not path.is_dir():
                blockers.append("repository directory is missing")
                stacks: tuple[str, ...] = ()
                stack_commands: tuple[CommandSpec, ...] = ()
                readme_ok = False
            else:
                readme_ok, readme_errors = readme_contract(path)
                if wave.require_readme_contract:
                    blockers.extend(readme_errors)

                stacks, stack_commands = commands_for_stack(
                    path, program.default_timeout_seconds
                )
                if wave.mode.is_active and not stacks:
                    blockers.append("no supported executable stack was detected")

                has_positive_test = any(
                    command.evidence_level >= EvidenceLevel.TEST
                    and command.proof_mode is ProofMode.POSITIVE_TEST_COUNT
                    for command in stack_commands
                )
                if (
                    wave.require_positive_test_count
                    and wave.target_evidence >= EvidenceLevel.TEST
                    and not has_positive_test
                ):
                    blockers.append("no positive-count test command was discovered")

                has_build_or_higher = any(
                    command.evidence_level >= EvidenceLevel.BUILD
                    for command in stack_commands
                )
                if wave.require_build_receipt and not has_build_or_higher:
                    blockers.append("no build-or-higher command was discovered")

            normalized_commands: list[CommandSpec] = []
            for command in stack_commands:
                if command.evidence_level >= EvidenceLevel.TEST:
                    required = (
                        wave.require_positive_test_count
                        or wave.target_evidence >= EvidenceLevel.TEST
                    )
                elif command.evidence_level >= EvidenceLevel.BUILD:
                    required = wave.require_build_receipt
                else:
                    required = wave.mode.is_active
                normalized_commands.append(replace(command, required=required))

            commands = (
                CommandSpec(
                    id="readme-contract",
                    evidence_level=EvidenceLevel.DOCUMENTATION,
                    argv=("<internal:readme-contract>",),
                    timeout_seconds=program.default_timeout_seconds,
                    proof_mode=ProofMode.INTERNAL,
                    required=wave.require_readme_contract,
                ),
                *normalized_commands,
            )

            plans.append(
                RepositoryPlan(
                    repository=repository,
                    wave_id=wave.id,
                    priority=wave.priority,
                    mode=wave.mode,
                    current_state=wave.current_state,
                    current_evidence=wave.current_evidence,
                    target_evidence=wave.target_evidence,
                    path=path,
                    stacks=stacks,
                    commands=tuple(commands),
                    blockers=tuple(sorted(set(blockers))),
                    readme_contract_satisfied=readme_ok,
                )
            )

    return tuple(sorted(plans, key=lambda plan: (plan.priority, plan.repository)))
