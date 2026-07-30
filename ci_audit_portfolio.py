#!/usr/bin/env python3
"""Evidence-bound portfolio audit for the GlacierEQ job-application workspace.

This command audits inventory integrity and portfolio wiring, then executes a
small, explicit set of repository-native checks. It does *not* infer that every
repository is deployable from hashes, filenames, or a passing sample.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Final

ROOT: Final = Path(__file__).resolve().parent
REPOS_DIR: Final = ROOT / "repos"
RECEIPT_PATH: Final = ROOT / "artifacts" / "portfolio_ci_receipt.json"


@dataclass(frozen=True, slots=True)
class CommandCheck:
    repository: str
    command: tuple[str, ...]
    cwd: Path
    env: dict[str, str] | None = None


@dataclass(frozen=True, slots=True)
class CommandResult:
    repository: str
    command: list[str]
    returncode: int
    status: str
    stdout_tail: str
    stderr_tail: str


RUNTIME_CHECKS: Final[tuple[CommandCheck, ...]] = (
    CommandCheck(
        repository="spacex-thermal-protection",
        command=(sys.executable, "-m", "unittest", "discover", "-s", "tests"),
        cwd=REPOS_DIR / "spacex-thermal-protection",
    ),
    CommandCheck(
        repository="xai-colossus-cooling",
        command=(sys.executable, "-m", "unittest", "discover", "-s", "tests"),
        cwd=REPOS_DIR / "xai-colossus-cooling",
    ),
    CommandCheck(
        repository="AKOS",
        command=(sys.executable, "-m", "unittest", "discover", "-s", "."),
        cwd=REPOS_DIR / "AKOS",
    ),
)


def log_step(name: str) -> None:
    print("\n==================================================")
    print(f"  CI STEP: {name}")
    print("==================================================")


def require_workspace() -> list[Path]:
    if not REPOS_DIR.is_dir():
        raise FileNotFoundError(
            f"Portfolio workspace not found: {REPOS_DIR}. "
            "Run this command from the canonical job-app workspace containing repos/."
        )
    return sorted(
        path for path in REPOS_DIR.iterdir() if path.is_dir() and not path.name.startswith(".")
    )


def step_1_check_hash_coverage(repos: list[Path]) -> dict[str, object]:
    log_step("1. Inventory integrity coverage (not runtime verification)")
    missing = [repo.name for repo in repos if not (repo / ".integrity" / "file_hashes.json").exists()]
    covered = len(repos) - len(missing)
    print(f"Repositories discovered: {len(repos)}")
    print(f"Repositories with integrity manifests: {covered}/{len(repos)}")
    if missing:
        raise AssertionError(f"Missing integrity manifests: {missing}")
    print("STATUS: PASS — inventory coverage only")
    return {
        "repositories_discovered": len(repos),
        "integrity_manifests": covered,
        "missing_integrity_manifests": missing,
    }


def step_2_apex_highway() -> dict[str, object]:
    log_step("2. APEX Highway mesh health scan")
    sys.path.insert(0, str(ROOT))
    from apex_highway import APEXHighwayEngine

    health = APEXHighwayEngine(root_dir=REPOS_DIR).scan_mesh_health()
    print(f"Mesh status: {health['mesh_status']}")
    print(
        "Healthy nodes: "
        f"{health['healthy_nodes']}/{health['total_nodes_discovered']} "
        f"({health['mesh_coverage_percent']}%)"
    )
    print(f"Scan latency: {health['scan_latency_ms']} ms")
    if health["mesh_status"] != "OPERATIONAL":
        raise AssertionError("Highway mesh must be OPERATIONAL")
    print("STATUS: PASS — mesh metadata/health scope")
    return health


def _tail(value: str, limit: int = 2000) -> str:
    return value[-limit:]


def _runtime_env(check: CommandCheck) -> dict[str, str]:
    env = os.environ.copy()
    if check.repository == "spacex-thermal-protection":
        env["PYTHONPATH"] = str(check.cwd / "src") + os.pathsep + env.get("PYTHONPATH", "")
    elif check.repository == "xai-colossus-cooling":
        env["PYTHONPATH"] = (
            str(check.cwd / "src")
            + os.pathsep
            + str(check.cwd)
            + os.pathsep
            + env.get("PYTHONPATH", "")
        )
    if check.env:
        env.update(check.env)
    return env


def step_3_runtime_sample() -> list[CommandResult]:
    log_step("3. Explicit repository-native runtime sample")
    results: list[CommandResult] = []
    for check in RUNTIME_CHECKS:
        if not check.cwd.is_dir():
            raise FileNotFoundError(f"Runtime-check repository missing: {check.cwd}")
        completed = subprocess.run(
            list(check.command),
            cwd=check.cwd,
            env=_runtime_env(check),
            capture_output=True,
            text=True,
            check=False,
        )
        result = CommandResult(
            repository=check.repository,
            command=list(check.command),
            returncode=completed.returncode,
            status="PASSED" if completed.returncode == 0 else "FAILED",
            stdout_tail=_tail(completed.stdout),
            stderr_tail=_tail(completed.stderr),
        )
        results.append(result)
        print(f"{check.repository}: {result.status}")
        if completed.returncode != 0:
            raise AssertionError(
                f"{check.repository} runtime check failed\n{result.stderr_tail}"
            )
    print(f"STATUS: PASS — {len(results)} repositories runtime-checked")
    return results


def step_4_demo_runner() -> dict[str, object]:
    log_step("4. Portfolio demonstration runner")
    demo_script = ROOT / "showcase" / "demo_15min_run.py"
    completed = subprocess.run(
        [sys.executable, str(demo_script)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(f"Demo runner failed\n{_tail(completed.stderr)}")
    print("STATUS: PASS — demonstration scope")
    return {"command": [sys.executable, str(demo_script)], "returncode": completed.returncode}


def step_5_link_verification() -> dict[str, object]:
    log_step("5. Hierarchical catalog local-link verification")
    map_file = ROOT / "HIERARCHICAL_PORTFOLIO_MAP.md"
    text = map_file.read_text(encoding="utf-8")
    links = re.findall(r"\(file://([^)]+)\)", text)
    missing = [link for link in links if not Path(link).exists()]
    print(f"Local file links checked: {len(links)}")
    print(f"Valid local file links: {len(links) - len(missing)}")
    if missing:
        raise AssertionError(f"Missing link targets: {missing}")
    print("STATUS: PASS — local catalog links only")
    return {"links_checked": len(links), "missing": missing}


def write_receipt(payload: dict[str, object]) -> None:
    RECEIPT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RECEIPT_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Receipt: {RECEIPT_PATH}")


def main() -> None:
    start = time.perf_counter()
    print("=== GLACIEREQ EVIDENCE-BOUND PORTFOLIO AUDIT ===")
    repos = require_workspace()
    inventory = step_1_check_hash_coverage(repos)
    mesh = step_2_apex_highway()
    runtime_results = step_3_runtime_sample()
    demo = step_4_demo_runner()
    links = step_5_link_verification()
    elapsed_ms = round((time.perf_counter() - start) * 1000.0, 2)

    receipt: dict[str, object] = {
        "schema": "glaciereq.portfolio.ci-receipt.v1",
        "conclusion": "PARTIALLY_VERIFIED",
        "scope_note": (
            "Integrity coverage and mesh health are not runtime verification. "
            "Only repositories listed in runtime_results were executed by this command."
        ),
        "elapsed_ms": elapsed_ms,
        "inventory": inventory,
        "mesh": mesh,
        "runtime_results": [asdict(result) for result in runtime_results],
        "demo": demo,
        "links": links,
    }
    write_receipt(receipt)

    print("\n==================================================")
    print(f"  ALL DEFINED AUDIT STEPS PASSED IN {elapsed_ms} ms")
    print(f"  RUNTIME-VERIFIED REPOSITORIES: {len(runtime_results)}/{len(repos)}")
    print("  PORTFOLIO CONCLUSION: PARTIALLY VERIFIED")
    print("  NO PORTFOLIO-WIDE DEPLOYABILITY CLAIM WAS MADE")
    print("==================================================")


if __name__ == "__main__":
    main()
