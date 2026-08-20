#!/usr/bin/env python3
"""Evidence-bound portfolio audit for the GlacierEQ job-application workspace.

This command audits inventory integrity and portfolio wiring, validates declared
language boundaries, and executes a small, explicit set of repository-native
checks. It does *not* infer that every repository is deployable from hashes,
filenames, README text, or a passing sample.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Final
from urllib.parse import unquote, urlsplit

ROOT: Final = Path(__file__).resolve().parent
REPOS_DIR: Final = ROOT / "repos"
RECEIPT_PATH = ROOT / "artifacts" / "portfolio_ci_receipt.json"
LANGUAGE_FIT_PATH: Final = ROOT / "manifests" / "language_fit.json"
PORTFOLIO_INVENTORY_PATH: Final = ROOT / "manifests" / "portfolio_repositories.json"
DEMO_RECEIPT_PATH: Final = ROOT / "artifacts" / "demo_15min_receipt.json"


def _positive_int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    value = int(raw)
    if value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


PROCESS_TIMEOUT_SECONDS: Final = _positive_int_env("PORTFOLIO_CHECK_TIMEOUT_SECONDS", 300)
DEMO_TIMEOUT_SECONDS: Final = _positive_int_env("PORTFOLIO_DEMO_TIMEOUT_SECONDS", 600)
LOCAL_LINK_RE: Final = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")


class AuditStepError(RuntimeError):
    """Audit failure carrying structured evidence for the failure receipt."""

    def __init__(self, message: str, evidence: object) -> None:
        super().__init__(message)
        self.evidence = evidence


@dataclass(frozen=True)
class CommandCheck:
    repository: str
    command: tuple[str, ...]
    cwd: Path
    env: dict[str, str] | None = None
    timeout_seconds: int = PROCESS_TIMEOUT_SECONDS
    minimum_tests: int = 1


@dataclass(frozen=True)
class CommandResult:
    repository: str
    command: list[str]
    returncode: int
    status: str
    timed_out: bool
    test_count: int | None
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
            "Run this command from the reference job-app workspace containing repos/."
        )
    return sorted(
        path for path in REPOS_DIR.iterdir() if path.is_dir() and not path.name.startswith(".")
    )


def step_1_check_hash_coverage(
    repos: list[Path],
    inventory_path: Path = PORTFOLIO_INVENTORY_PATH,
) -> dict[str, object]:
    log_step("1. Exact portfolio inventory and integrity coverage")
    payload = json.loads(inventory_path.read_text(encoding="utf-8"))
    expected_raw = payload.get("workspace_repositories")
    if not isinstance(expected_raw, list) or not all(
        isinstance(name, str) and name.strip() for name in expected_raw
    ):
        raise AuditStepError(
            "Portfolio inventory must declare workspace_repositories",
            {"manifest": str(inventory_path), "errors": ["invalid workspace_repositories"]},
        )

    expected = set(expected_raw)
    discovered = {repo.name for repo in repos}
    declared_total = payload.get("total_repositories")
    root_repository = payload.get("portfolio_root")
    missing_repositories = sorted(expected - discovered)
    unexpected_repositories = sorted(discovered - expected)
    duplicate_declarations = sorted(
        name for name in expected if expected_raw.count(name) > 1
    )
    count_is_consistent = (
        isinstance(declared_total, int)
        and declared_total == len(expected) + 1
        and isinstance(root_repository, str)
        and bool(root_repository.strip())
    )
    missing_integrity = sorted(
        repo.name
        for repo in repos
        if repo.name in expected and not (repo / ".integrity" / "file_hashes.json").exists()
    )
    covered = len(expected) - len(missing_integrity)
    evidence = {
        "manifest": str(inventory_path),
        "portfolio_root": root_repository,
        "portfolio_total_declared": declared_total,
        "workspace_repositories_expected": len(expected),
        "workspace_repositories_discovered": len(discovered),
        "missing_repositories": missing_repositories,
        "unexpected_repositories": unexpected_repositories,
        "duplicate_declarations": duplicate_declarations,
        "inventory_count_consistent": count_is_consistent,
        "integrity_manifests": covered,
        "missing_integrity_manifests": missing_integrity,
    }
    print(
        "Workspace repositories: "
        f"{len(discovered)}/{len(expected)} expected; portfolio total={declared_total}"
    )
    print(f"Repositories with integrity manifests: {covered}/{len(expected)}")
    if (
        missing_repositories
        or unexpected_repositories
        or duplicate_declarations
        or not count_is_consistent
        or missing_integrity
    ):
        raise AuditStepError("Portfolio inventory or integrity coverage is incomplete", evidence)
    print("STATUS: PASS — exact 66-repository scope and child integrity coverage")
    return evidence


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
        raise AuditStepError("Highway mesh must be OPERATIONAL", health)
    print("STATUS: PASS — mesh metadata/health scope")
    return health


def step_3_validate_language_fit(
    manifest_path: Path = LANGUAGE_FIT_PATH,
) -> dict[str, object]:
    log_step("3. Language responsibility and evidence contract")
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = payload.get("entries")
    if not isinstance(entries, list) or not entries:
        raise AuditStepError(
            "Language-fit manifest must contain at least one entry",
            {"manifest": str(manifest_path), "errors": ["entries must be a non-empty list"]},
        )

    required_fields = (
        "name",
        "kind",
        "responsibility",
        "boundary",
        "interface_contract",
        "build_command",
        "test_command",
        "evidence_receipt",
        "verification_state",
    )
    allowed_states = {"VERIFIED", "PARTIALLY_VERIFIED", "BLOCKED", "UNVERIFIED", "FAILED"}
    errors: list[str] = []
    validated: list[dict[str, str]] = []

    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            errors.append(f"entry {index}: must be an object")
            continue
        entry_errors: list[str] = []
        missing = [
            field
            for field in required_fields
            if not isinstance(entry.get(field), str) or not entry[field].strip()
        ]
        if missing:
            entry_errors.append(f"missing non-empty fields {missing}")
        if not missing and entry["verification_state"] not in allowed_states:
            entry_errors.append(
                f"invalid verification_state={entry['verification_state']!r}"
            )
        if not missing:
            receipt_path = ROOT / entry["evidence_receipt"]
            if not receipt_path.is_file():
                entry_errors.append(
                    f"evidence receipt does not exist: {entry['evidence_receipt']}"
                )
        if entry_errors:
            errors.extend(f"entry {index}: {message}" for message in entry_errors)
            continue
        validated.append({field: entry[field] for field in required_fields})

    evidence: dict[str, object] = {
        "manifest": str(manifest_path),
        "schema": payload.get("schema"),
        "repository": payload.get("repository"),
        "entries_declared": len(entries),
        "entries_validated": len(validated),
        "languages": [entry["name"] for entry in validated],
        "errors": errors,
    }
    if errors:
        raise AuditStepError("Language-fit contract validation failed", evidence)
    print(f"Language/format boundaries validated: {len(validated)}")
    print("STATUS: PASS — every declared boundary is representable and evidence-linked")
    return evidence


def _tail(value: str | bytes | None, limit: int = 2000) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        value = value.decode(errors="replace")
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


def _extract_unittest_count(stdout: str | bytes | None, stderr: str | bytes | None) -> int | None:
    combined = f"{_tail(stdout, 10000)}\n{_tail(stderr, 10000)}"
    matches = re.findall(r"Ran\s+(\d+)\s+tests?", combined)
    return int(matches[-1]) if matches else None


def _run_command_check(check: CommandCheck) -> CommandResult:
    try:
        completed = subprocess.run(
            list(check.command),
            cwd=check.cwd,
            env=_runtime_env(check),
            capture_output=True,
            text=True,
            check=False,
            timeout=check.timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        return CommandResult(
            repository=check.repository,
            command=list(check.command),
            returncode=124,
            status="FAILED",
            timed_out=True,
            test_count=None,
            stdout_tail=_tail(exc.stdout),
            stderr_tail=f"Timed out after {check.timeout_seconds}s. {_tail(exc.stderr)}".strip(),
        )
    test_count = _extract_unittest_count(completed.stdout, completed.stderr)
    if completed.returncode != 0:
        status = "FAILED"
        stderr_tail = _tail(completed.stderr)
    elif test_count is None or test_count < check.minimum_tests:
        status = "UNVERIFIED"
        stderr_tail = (
            f"Command exited zero but executed-test count was "
            f"{test_count!r}; minimum required is {check.minimum_tests}. "
            f"{_tail(completed.stderr)}"
        ).strip()
    else:
        status = "PASSED"
        stderr_tail = _tail(completed.stderr)
    return CommandResult(
        repository=check.repository,
        command=list(check.command),
        returncode=completed.returncode,
        status=status,
        timed_out=False,
        test_count=test_count,
        stdout_tail=_tail(completed.stdout),
        stderr_tail=stderr_tail,
    )


def step_4_runtime_sample() -> list[CommandResult]:
    log_step("4. Explicit repository-native runtime sample")
    results: list[CommandResult] = []
    for check in RUNTIME_CHECKS:
        if not check.cwd.is_dir():
            result = CommandResult(
                repository=check.repository,
                command=list(check.command),
                returncode=127,
                status="BLOCKED",
                timed_out=False,
                test_count=None,
                stdout_tail="",
                stderr_tail=f"Runtime-check repository missing: {check.cwd}",
            )
        else:
            result = _run_command_check(check)
        results.append(result)
        print(f"{check.repository}: {result.status} ({result.test_count} tests)")
    failures = [result for result in results if result.status != "PASSED"]
    if failures:
        raise AuditStepError(
            "One or more repository-native runtime checks failed or were unverified",
            [asdict(result) for result in results],
        )
    print(f"STATUS: PASS — {len(results)} repositories runtime-checked with nonzero tests")
    return results


def step_5_demo_runner() -> dict[str, object]:
    log_step("5. Portfolio demonstration runner")
    demo_script = ROOT / "showcase" / "demo_15min_run.py"
    try:
        completed = subprocess.run(
            [sys.executable, str(demo_script)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
            timeout=DEMO_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        evidence = {
            "command": [sys.executable, str(demo_script)],
            "returncode": 124,
            "status": "FAILED",
            "timed_out": True,
            "stdout_tail": _tail(exc.stdout),
            "stderr_tail": f"Timed out after {DEMO_TIMEOUT_SECONDS}s. {_tail(exc.stderr)}".strip(),
        }
        raise AuditStepError("Demo runner timed out", evidence) from exc

    evidence: dict[str, object] = {
        "command": [sys.executable, str(demo_script)],
        "returncode": completed.returncode,
        "status": "PASSED" if completed.returncode == 0 else "FAILED",
        "timed_out": False,
        "stdout_tail": _tail(completed.stdout),
        "stderr_tail": _tail(completed.stderr),
    }
    if DEMO_RECEIPT_PATH.is_file():
        try:
            evidence["receipt"] = json.loads(DEMO_RECEIPT_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            evidence["receipt_error"] = str(exc)
    else:
        evidence["receipt_error"] = f"Missing demo receipt: {DEMO_RECEIPT_PATH}"

    receipt = evidence.get("receipt")
    receipt_is_verified = (
        isinstance(receipt, dict)
        and receipt.get("conclusion") == "VERIFIED"
        and isinstance(receipt.get("results"), list)
        and bool(receipt["results"])
        and all(
            result.get("status") == "PASSED"
            and isinstance(result.get("test_count"), int)
            and result["test_count"] > 0
            for result in receipt["results"]
            if isinstance(result, dict)
        )
        and all(isinstance(result, dict) for result in receipt["results"])
    )
    if completed.returncode != 0 or not receipt_is_verified:
        raise AuditStepError("Demo runner did not produce verified per-demo evidence", evidence)
    print("STATUS: PASS — every declared demo executed at least one test and passed")
    return evidence


def _resolve_local_link(map_file: Path, raw_target: str) -> Path | None:
    target = raw_target.strip()
    if not target:
        return None
    if " " in target and not target.startswith("<"):
        target = target.split(maxsplit=1)[0]
    target = target.strip("<>")
    parsed = urlsplit(target)
    if parsed.scheme in {"http", "https", "mailto"} or target.startswith("#"):
        return None
    if parsed.scheme == "file":
        return Path(unquote(parsed.path))
    if parsed.scheme:
        return None
    relative_path = unquote(parsed.path)
    if not relative_path:
        return None
    return (map_file.parent / relative_path).resolve()


def step_6_link_verification(
    map_file: Path | None = None,
) -> dict[str, object]:
    log_step("6. Hierarchical catalog local-link verification")
    map_path = map_file or ROOT / "HIERARCHICAL_PORTFOLIO_MAP.md"
    text = map_path.read_text(encoding="utf-8")
    resolved = [
        path
        for target in LOCAL_LINK_RE.findall(text)
        if (path := _resolve_local_link(map_path, target)) is not None
    ]
    missing = [str(path) for path in resolved if not path.exists()]
    evidence = {
        "map": str(map_path),
        "links_checked": len(resolved),
        "valid": len(resolved) - len(missing),
        "missing": missing,
    }
    print(f"Local links checked: {len(resolved)}")
    print(f"Valid local links: {len(resolved) - len(missing)}")
    if not resolved:
        raise AuditStepError("No local Markdown links were discovered", evidence)
    if missing:
        raise AuditStepError(f"Missing link targets: {missing}", evidence)
    print("STATUS: PASS — file URLs and relative Markdown links")
    return evidence


def write_receipt(payload: dict[str, object]) -> None:
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
    print(f"Receipt: {RECEIPT_PATH}")


def _base_receipt(conclusion: str, elapsed_ms: float = 0.0) -> dict[str, object]:
    return {
        "schema": "glaciereq.portfolio.ci-receipt.v1",
        "conclusion": conclusion,
        "scope_note": (
            "Inventory coverage, language declarations, mesh health, runtime samples, and "
            "demos are distinct evidence scopes. Every repository process executed by this "
            "audit is listed in runtime_results or demo.receipt.results."
        ),
        "elapsed_ms": elapsed_ms,
    }


def main() -> None:
    start = time.perf_counter()
    print("=== GLACIEREQ EVIDENCE-BOUND PORTFOLIO AUDIT ===")
    evidence: dict[str, object] = {}
    write_receipt(_base_receipt("RUNNING"))

    try:
        repos = require_workspace()
        evidence["workspace"] = {
            "path": str(REPOS_DIR),
            "repositories_discovered": len(repos),
        }
        steps = (
            ("inventory", lambda: step_1_check_hash_coverage(repos)),
            ("mesh", step_2_apex_highway),
            ("language_fit", step_3_validate_language_fit),
            ("runtime_results", step_4_runtime_sample),
            ("demo", step_5_demo_runner),
            ("links", step_6_link_verification),
        )
        for key, step in steps:
            try:
                result = step()
            except AuditStepError as exc:
                evidence[key] = exc.evidence
                raise
            evidence[key] = (
                [asdict(item) for item in result]
                if isinstance(result, list) and all(isinstance(item, CommandResult) for item in result)
                else result
            )
    except Exception as exc:
        elapsed_ms = round((time.perf_counter() - start) * 1000.0, 2)
        failed = _base_receipt("FAILED", elapsed_ms)
        failed.update(
            {
                "error": {"type": type(exc).__name__, "message": str(exc)},
                "evidence": evidence,
            }
        )
        write_receipt(failed)
        print(f"PORTFOLIO AUDIT FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise

    elapsed_ms = round((time.perf_counter() - start) * 1000.0, 2)
    runtime_results = evidence["runtime_results"]
    if not isinstance(runtime_results, list):
        raise AssertionError("runtime_results must be a list")
    executed_repositories = {
        result["repository"]
        for result in runtime_results
        if isinstance(result, dict) and result.get("returncode") is not None
    }
    demo = evidence.get("demo")
    if isinstance(demo, dict):
        demo_receipt = demo.get("receipt")
        if isinstance(demo_receipt, dict) and isinstance(demo_receipt.get("results"), list):
            executed_repositories.update(
                result["repository"]
                for result in demo_receipt["results"]
                if isinstance(result, dict)
                and isinstance(result.get("repository"), str)
                and result.get("returncode") is not None
            )
    evidence["executed_repositories"] = sorted(executed_repositories)
    receipt = _base_receipt("PARTIALLY_VERIFIED", elapsed_ms)
    receipt.update(evidence)
    write_receipt(receipt)

    print("\n==================================================")
    print(f"  ALL DEFINED AUDIT STEPS PASSED IN {elapsed_ms} ms")
    print(f"  RUNTIME-SAMPLE REPOSITORIES: {len(runtime_results)}/{len(repos)}")
    print(f"  ALL EXECUTED REPOSITORIES: {len(executed_repositories)}")
    print("  PORTFOLIO CONCLUSION: PARTIALLY VERIFIED")
    print("  NO PORTFOLIO-WIDE DEPLOYABILITY CLAIM WAS MADE")
    print("==================================================")


if __name__ == "__main__":
    main()
