#!/usr/bin/env python3
"""Run one featured portfolio verification contract without shell interpolation."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PY = sys.executable

PYTHON_CONTRACTS: dict[str, list[list[str]]] = {
    "job-app-helix": [[PY, "-m", "pip", "install", "-e", ".[dev]"], [PY, "-m", "pytest", "-q"]],
    "AKOS": [[PY, "-m", "pytest", "-q"]],
    "spacex-telemetry": [[PY, "-m", "pytest", "-q"]],
    "spacex-propulsion-monitor": [[PY, "-m", "pytest", "-q"]],
    "spacex-ground-network": [[PY, "-m", "pytest", "-q"]],
    "spacex-launch-sequencer": [[PY, "-m", "pytest", "-q"]],
    "spacex-mission-control": [[PY, "-m", "pytest", "-q"]],
    "spacex-satellite-mesh": [[PY, "-m", "pytest", "-q"]],
    "spacex-autonomy": [[PY, "-m", "pytest", "-q"]],
    "spacex-cryogenics": [[PY, "-m", "pytest", "-q"]],
    "spacex-conjunction-sentinel": [[PY, "-m", "pytest", "-q"]],
    "spacex-pad-weather-gate": [[PY, "-m", "pytest", "-q"]],
    "spacex-orbital-mechanics": [[PY, "-m", "pytest", "-q"]],
    "spacex-thermal-protection": [[PY, "-m", "pytest", "-q"]],
    "anthropic-agent-coordinator": [[PY, "-m", "pytest", "-q"]],
    "anthropic-safety-monitor": [[PY, "-m", "pytest", "-q"]],
    "xai-colossus-cooling-alpha": [[PY, "-m", "pytest", "-q"]],
    "xai-colossus-cooling-omega": [[PY, "-m", "pytest", "-q"]],
    "xai-colossus-energy-alpha": [[PY, "-m", "pytest", "-q"]],
    "xai-colossus-energy-omega": [[PY, "-m", "pytest", "-q"]],
    "xai-colossus-servers": [[PY, "-m", "pytest", "-q"]],
    "the-tower-of-babel": [
        [PY, "-m", "pip", "install", "-e", ".[dev]"],
        [PY, "-m", "pytest", "-q"],
        ["tower", "validate"],
        ["tower", "generate", "--check"],
    ],
    "Megamind": [
        [PY, "-m", "pip", "install", "-e", ".[dev]"],
        [PY, "-m", "pytest", "-q"],
        ["megamind", "validate"],
    ],
}

NATIVE_CONTRACTS: dict[str, dict[str, Any]] = {
    "telemetry-go": {"technology": "Go", "tool": "go", "commands": [["go", "run", "src/telemetry_decoder.go"]]},
    "autonomy-go": {"technology": "Go", "tool": "go", "commands": [["go", "run", "src/flight_fsm.go"]]},
    "launch-sequencer-go": {"technology": "Go", "tool": "go", "commands": [["go", "run", "src/countdown_timer.go"]]},
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
            ["g++", "-std=c++17", "-Wall", "-Wextra", "-pedantic", "src/lambert_solver.cpp", "-o", "/tmp/lambert"],
            ["/tmp/lambert"],
        ],
    },
    "thermal-odin": {"technology": "Odin", "tool": "odin", "commands": [["odin", "check", "src"]]},
}


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


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


def run_commands(commands: list[list[str]], cwd: Path, timeout: int, extra_env: dict[str, str] | None = None) -> tuple[int, str]:
    lines: list[str] = []
    env = {**os.environ, **(extra_env or {})}
    for argv in commands:
        lines.append(f"$ {json.dumps(argv)}")
        try:
            proc = subprocess.run(
                argv,
                cwd=cwd,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=timeout,
                shell=False,
            )
        except subprocess.TimeoutExpired as exc:
            output = exc.stdout if isinstance(exc.stdout, str) else ""
            lines.append(output)
            lines.append(f"TIMEOUT after {timeout}s")
            return 124, "\n".join(lines)
        except OSError as exc:
            lines.append(f"EXECUTION ERROR: {exc}")
            return 126, "\n".join(lines)
        lines.append(proc.stdout or "")
        if proc.returncode != 0:
            return proc.returncode, "\n".join(lines)
    return 0, "\n".join(lines)


def main() -> int:
    args = parse_args()
    started = now()
    if args.surface == "python":
        commands = PYTHON_CONTRACTS.get(args.name)
        technology = "Python"
        tool = None
        environment: dict[str, str] = {}
    else:
        contract = NATIVE_CONTRACTS.get(args.name)
        if contract is None:
            commands = None
            technology = "unknown"
            tool = None
            environment = {}
        else:
            commands = contract["commands"]
            technology = contract["technology"]
            tool = contract["tool"]
            environment = contract.get("environment", {})

    if not commands:
        status = "INVALID_CONTRACT"
        exit_code = 2
        log = f"No bounded execution contract for {args.name}.\n"
    elif tool and shutil.which(tool) is None:
        status = "BLOCKED_TOOLCHAIN"
        exit_code = 127
        log = f"Required toolchain is unavailable: {tool}\n"
    else:
        exit_code, log = run_commands(commands, args.path, args.timeout, environment)
        status = "VERIFIED" if exit_code == 0 else "FAILED"

    payload = {
        "schema": "glaciereq.portfolio.verification.v1",
        "repository": args.repository,
        "ref": args.ref,
        "name": args.name,
        "surface": f"{args.surface}:{technology}",
        "commands": commands,
        "exit_code": exit_code,
        "status": status,
        "started_at": started,
        "finished_at": now(),
    }
    args.log.write_text(log, encoding="utf-8")
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(log)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
