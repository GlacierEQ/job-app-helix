"""Run one featured portfolio verification contract without shell interpolation."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import timezone, datetime
UTC = timezone.utc
from pathlib import Path
from typing import Any

PYTHON = sys.executable
PASSED_COUNT = re.compile(r"(?P<count>\d+) passed(?:,|\s)")
RAN_COUNT = re.compile(r"Ran (?P<count>\d+) tests?")
COLLECTED_COUNT = re.compile(r"(?P<count>\d+) tests? collected", re.IGNORECASE)
GIT_SHA = re.compile(r"^[0-9a-f]{40}$")

PYTHON_CONTRACTS: dict[str, list[list[str]]] = {
    "job-app-helix": [
        [PYTHON, "-m", "pip", "install", "-e", ".[dev]"],
        [PYTHON, "-m", "pytest", "-q"],
    ],
    "AKOS": [[PYTHON, "-m", "pytest", "-q"]],
    "anthropic-agent-coordinator": [[PYTHON, "-m", "pytest", "-q"]],
    "anthropic-safety-monitor": [[PYTHON, "-m", "pytest", "-q"]],
    "spacex-autonomy": [[PYTHON, "-m", "pytest", "-q"]],
    "spacex-conjunction-sentinel": [[PYTHON, "-m", "pytest", "-q"]],
    "spacex-cryogenics": [[PYTHON, "-m", "pytest", "-q"]],
    "spacex-ground-network": [[PYTHON, "-m", "pytest", "-q"]],
    "spacex-launch-sequencer": [[PYTHON, "-m", "pytest", "-q"]],
    "spacex-mission-control": [[PYTHON, "-m", "pytest", "-q"]],
    "spacex-orbital-mechanics": [[PYTHON, "-m", "pytest", "-q"]],
    "spacex-pad-weather-gate": [[PYTHON, "-m", "pytest", "-q"]],
    "spacex-propulsion-monitor": [[PYTHON, "-m", "pytest", "-q"]],
    "spacex-satellite-mesh": [[PYTHON, "-m", "pytest", "-q"]],
    "spacex-telemetry": [[PYTHON, "-m", "pytest", "-q"]],
    "spacex-thermal-protection": [[PYTHON, "-m", "pytest", "-q"]],
    "the-tower-of-babel": [
        [PYTHON, "-m", "pip", "install", "-e", ".[dev]"],
        [PYTHON, "-m", "pytest", "-q"],
        ["tower", "validate"],
        ["tower", "generate", "--check"],
    ],
    "xai-colossus-cooling-alpha": [[PYTHON, "-m", "pytest", "-q"]],
    "xai-colossus-cooling-omega": [[PYTHON, "-m", "pytest", "-q"]],
    "xai-colossus-energy-alpha": [[PYTHON, "-m", "pytest", "-q"]],
    "xai-colossus-energy-omega": [[PYTHON, "-m", "pytest", "-q"]],
    "xai-colossus-servers": [[PYTHON, "-m", "pytest", "-q"]],
}

NATIVE_CONTRACTS: dict[str, dict[str, Any]] = {
    "telemetry-go": {
        "technology": "Go",
        "tool": "go",
        "commands": [["go", "run", "src/telemetry_decoder.go"]],
    },
    "autonomy-go": {
        "technology": "Go",
        "tool": "go",
        "commands": [["go", "run", "src/flight_fsm.go"]],
    },
    "launch-sequencer-go": {
        "technology": "Go",
        "tool": "go",
        "commands": [["go", "run", "src/countdown_timer.go"]],
    },
    "pad-weather-go": {
        "technology": "Go",
        "tool": "go",
        "commands": [["go", "test", "src/electric_field_monitor.go"]],
        "environment": {"GO111MODULE": "off"},
    },
    "orbital-cpp": {
        "technology": "C++",
        "tool": "g++",
        "commands": [
            [
                "g++",
                "-std=c++17",
                "-Wall",
                "-Wextra",
                "-pedantic",
                "src/lambert_solver.cpp",
                "-o",
                "/tmp/lambert",
            ],
            ["/tmp/lambert"],
        ],
    },
    "thermal-odin": {
        "technology": "Odin",
        "tool": "odin",
        "commands": [["odin", "check", "src"]],
    },
}


def now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--ref", required=True)
    parser.add_argument("--path", type=Path, required=True)
    parser.add_argument("--surface", choices=("python", "native"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=600)
    return parser.parse_args()


def resolve_commit_sha(cwd: Path) -> str | None:
    """Resolve the exact commit checked out for execution, or fail closed."""

    try:
        process = subprocess.run(
            ["git", "rev-parse", "--verify", "HEAD^{commit}"],
            cwd=cwd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=30,
            check=False,
            shell=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None

    resolved = (process.stdout or "").strip().lower()
    if process.returncode != 0 or GIT_SHA.fullmatch(resolved) is None:
        return None
    return resolved


def observed_test_count(output: str) -> int | None:
    for pattern in (PASSED_COUNT, RAN_COUNT, COLLECTED_COUNT):
        match = pattern.search(output)
        if match:
            return int(match.group("count"))
    return None


def is_pytest_command(argv: list[str]) -> bool:
    return "pytest" in argv


def command_requires_test_proof(argv: list[str]) -> bool:
    joined = " ".join(argv)
    return is_pytest_command(argv) or "unittest" in argv or " test" in f" {joined}"


def pytest_collection_command(argv: list[str]) -> list[str]:
    """Build a deterministic collection command independent of quiet addopts."""

    pytest_index = argv.index("pytest")
    prefix = argv[: pytest_index + 1]
    suffix = [arg for arg in argv[pytest_index + 1 :] if arg not in {"-q", "--quiet"}]
    return [*prefix, "--collect-only", "-q", "-o", "addopts=", *suffix]


def count_collected_pytest_nodes(output: str) -> int:
    """Count collected pytest node ids, falling back to pytest's collection summary."""

    node_ids = {
        line.strip()
        for line in output.splitlines()
        if "::" in line and not line.lstrip().startswith(("=", "<"))
    }
    if node_ids:
        return len(node_ids)
    return observed_test_count(output) or 0


def collect_pytest_count(
    argv: list[str],
    cwd: Path,
    timeout: int,
    env: dict[str, str],
) -> tuple[int, str, int]:
    """Collect pytest tests before execution so proof does not depend on console prose."""

    collection_argv = pytest_collection_command(argv)
    try:
        process = subprocess.run(
            collection_argv,
            cwd=cwd,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            check=False,
            shell=False,
        )
    except subprocess.TimeoutExpired as exc:
        output = exc.stdout if isinstance(exc.stdout, str) else ""
        return 124, output, 0
    except OSError as exc:
        return 126, f"COLLECTION EXECUTION ERROR: {exc}", 0

    output = process.stdout or ""
    return process.returncode, output, count_collected_pytest_nodes(output)


def run_commands(
    commands: list[list[str]],
    cwd: Path,
    timeout: int,
    extra_env: dict[str, str] | None = None,
) -> tuple[int, str, int | None]:
    lines: list[str] = []
    env = {**os.environ, **(extra_env or {})}
    maximum_test_count: int | None = None

    for argv in commands:
        collection_count: int | None = None
        if is_pytest_command(argv):
            collection_argv = pytest_collection_command(argv)
            lines.append(f"$ {json.dumps(collection_argv)}")
            collection_code, collection_output, collection_count = collect_pytest_count(
                argv,
                cwd,
                timeout,
                env,
            )
            lines.append(collection_output)
            if collection_code != 0:
                lines.append("UNVERIFIED: pytest collection failed")
                return collection_code, "\n".join(lines), maximum_test_count
            if collection_count <= 0:
                lines.append("UNVERIFIED: pytest collected zero tests")
                return 3, "\n".join(lines), 0
            maximum_test_count = max(maximum_test_count or 0, collection_count)

        lines.append(f"$ {json.dumps(argv)}")
        try:
            process = subprocess.run(
                argv,
                cwd=cwd,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=timeout,
                check=False,
                shell=False,
            )
        except subprocess.TimeoutExpired as exc:
            output = exc.stdout if isinstance(exc.stdout, str) else ""
            lines.extend((output, f"TIMEOUT after {timeout}s"))
            return 124, "\n".join(lines), maximum_test_count
        except OSError as exc:
            lines.append(f"EXECUTION ERROR: {exc}")
            return 126, "\n".join(lines), maximum_test_count

        output = process.stdout or ""
        lines.append(output)
        count = observed_test_count(output)
        if count is not None:
            maximum_test_count = max(maximum_test_count or 0, count)

        if process.returncode != 0:
            return process.returncode, "\n".join(lines), maximum_test_count
        if command_requires_test_proof(argv) and count == 0:
            lines.append("UNVERIFIED: test command reported zero tests")
            return 3, "\n".join(lines), 0
        if is_pytest_command(argv) and collection_count is None:
            lines.append("UNVERIFIED: pytest execution lacked collection proof")
            return 3, "\n".join(lines), 0

    return 0, "\n".join(lines), maximum_test_count


def resolve_contract(
    name: str,
    surface: str,
) -> tuple[list[list[str]] | None, str, str | None, dict[str, str]]:
    if surface == "python":
        return PYTHON_CONTRACTS.get(name), "Python", None, {}

    contract = NATIVE_CONTRACTS.get(name)
    if contract is None:
        return None, "unknown", None, {}
    return (
        contract["commands"],
        contract["technology"],
        contract["tool"],
        contract.get("environment", {}),
    )


def main() -> int:
    args = parse_args()
    started = now()
    commands, technology, tool, environment = resolve_contract(
        args.name,
        args.surface,
    )
    resolved_commit_sha = resolve_commit_sha(args.path)

    if resolved_commit_sha is None:
        status = "BLOCKED_IDENTITY"
        exit_code = 4
        log = (
            "Unable to resolve an exact Git commit for the checked-out execution path. "
            "No verification state may be promoted without content identity.\n"
        )
        test_count = None
    elif not commands:
        status = "INVALID_CONTRACT"
        exit_code = 2
        log = f"No bounded execution contract for {args.name}.\n"
        test_count = None
    elif tool and shutil.which(tool) is None:
        status = "BLOCKED_TOOLCHAIN"
        exit_code = 127
        log = f"Required toolchain is unavailable: {tool}\n"
        test_count = None
    else:
        exit_code, log, test_count = run_commands(
            commands,
            args.path,
            args.timeout,
            environment,
        )
        status = "VERIFIED" if exit_code == 0 else "FAILED"

    payload = {
        "schema": "glaciereq.portfolio.verification.v1",
        "repository": args.repository,
        "ref": args.ref,
        "resolved_commit_sha": resolved_commit_sha,
        "identity_status": "RESOLVED" if resolved_commit_sha else "UNRESOLVED",
        "name": args.name,
        "surface": f"{args.surface}:{technology}",
        "commands": commands,
        "exit_code": exit_code,
        "observed_test_count": test_count,
        "status": status,
        "started_at": started,
        "finished_at": now(),
    }
    args.log.parent.mkdir(parents=True, exist_ok=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.log.write_text(log, encoding="utf-8")
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(log)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
