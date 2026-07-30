#!/usr/bin/env python3
"""Run the bounded portfolio hero demonstrations and emit per-demo evidence."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Final

ROOT: Final = Path(__file__).resolve().parent.parent
REPOS: Final = ROOT / "repos"
RECEIPT_PATH: Final = ROOT / "artifacts" / "demo_15min_receipt.json"


def _positive_int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    value = int(raw)
    if value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


DEMO_TIMEOUT_SECONDS: Final = _positive_int_env("PORTFOLIO_DEMO_CHECK_TIMEOUT_SECONDS", 180)


@dataclass(frozen=True, slots=True)
class DemoCheck:
    name: str
    repository: str
    command: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DemoResult:
    name: str
    repository: str
    command: list[str]
    status: str
    returncode: int | None
    timed_out: bool
    elapsed_ms: float
    stdout_tail: str
    stderr_tail: str


DEMO_CHECKS: Final[tuple[DemoCheck, ...]] = (
    DemoCheck(
        "Starship PICA-X Thermal Reentry",
        "spacex-thermal-protection",
        (sys.executable, "-m", "unittest", "discover", "-s", "tests"),
    ),
    DemoCheck(
        "xAI Colossus 100k GPU Liquid Cooling",
        "xai-colossus-cooling",
        (sys.executable, "-m", "unittest", "discover", "-s", "tests"),
    ),
    DemoCheck(
        "AKOS Autonomous Agentic Kernel",
        "AKOS",
        (sys.executable, "-m", "unittest", "discover", "-s", "."),
    ),
    DemoCheck(
        "Kimi K3 2.8T KDA Attention Engine",
        "kimi-mooncake-kv-stream",
        (sys.executable, "-m", "unittest", "discover", "-s", "tests"),
    ),
)


def _tail(value: str | bytes | None, limit: int = 2000) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        value = value.decode(errors="replace")
    return value[-limit:]


def _write_receipt(payload: dict[str, object]) -> None:
    RECEIPT_PATH.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=RECEIPT_PATH.parent,
            prefix=f".{RECEIPT_PATH.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temp_path = Path(handle.name)
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, RECEIPT_PATH)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()


def _run_demo(check: DemoCheck) -> DemoResult:
    repo_path = REPOS / check.repository
    start = time.perf_counter()
    if not repo_path.is_dir():
        return DemoResult(
            name=check.name,
            repository=check.repository,
            command=list(check.command),
            status="BLOCKED",
            returncode=None,
            timed_out=False,
            elapsed_ms=round((time.perf_counter() - start) * 1000.0, 2),
            stdout_tail="",
            stderr_tail=f"Repository missing: {repo_path}",
        )
    if "tests" in check.command and not (repo_path / "tests").is_dir():
        return DemoResult(
            name=check.name,
            repository=check.repository,
            command=list(check.command),
            status="UNVERIFIED",
            returncode=None,
            timed_out=False,
            elapsed_ms=round((time.perf_counter() - start) * 1000.0, 2),
            stdout_tail="",
            stderr_tail=f"Required tests directory missing: {repo_path / 'tests'}",
        )

    try:
        completed = subprocess.run(
            list(check.command),
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=False,
            timeout=DEMO_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        return DemoResult(
            name=check.name,
            repository=check.repository,
            command=list(check.command),
            status="FAILED",
            returncode=124,
            timed_out=True,
            elapsed_ms=round((time.perf_counter() - start) * 1000.0, 2),
            stdout_tail=_tail(exc.stdout),
            stderr_tail=f"Timed out after {DEMO_TIMEOUT_SECONDS}s. {_tail(exc.stderr)}".strip(),
        )

    return DemoResult(
        name=check.name,
        repository=check.repository,
        command=list(check.command),
        status="PASSED" if completed.returncode == 0 else "FAILED",
        returncode=completed.returncode,
        timed_out=False,
        elapsed_ms=round((time.perf_counter() - start) * 1000.0, 2),
        stdout_tail=_tail(completed.stdout),
        stderr_tail=_tail(completed.stderr),
    )


def run_hero_demos() -> int:
    print("=== BOUNDED PORTFOLIO HERO DEMO RUNNER ===")
    started = time.perf_counter()
    results = [_run_demo(check) for check in DEMO_CHECKS]
    for result in results:
        print(
            f"[{result.status}] {result.name} "
            f"({result.repository}) — {result.elapsed_ms} ms"
        )

    all_passed = bool(results) and all(result.status == "PASSED" for result in results)
    elapsed_ms = round((time.perf_counter() - started) * 1000.0, 2)
    receipt: dict[str, object] = {
        "schema": "glaciereq.portfolio.demo-receipt.v1",
        "conclusion": "VERIFIED" if all_passed else "FAILED",
        "elapsed_ms": elapsed_ms,
        "results": [asdict(result) for result in results],
    }
    _write_receipt(receipt)

    print("==========================================")
    print(
        f"DEMO CONCLUSION: {receipt['conclusion']} — "
        f"{sum(result.status == 'PASSED' for result in results)}/{len(results)} passed"
    )
    print(f"Receipt: {RECEIPT_PATH}")
    print("==========================================")
    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(run_hero_demos())
