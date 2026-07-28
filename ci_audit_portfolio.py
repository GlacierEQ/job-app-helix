#!/usr/bin/env python3
"""Operator-workspace integration audit, separate from public GitHub CI."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPOS_DIR = Path(os.environ.get("JOB_APP_REPOS_ROOT", ROOT / "repos")).expanduser().resolve()


def require_workspace() -> list[Path]:
    if not REPOS_DIR.is_dir():
        raise SystemExit(
            "Workspace root missing. Set JOB_APP_REPOS_ROOT or populate ./repos. "
            "For fresh-clone verification run `python -m helix.public_runtime demo`."
        )
    return [path for path in REPOS_DIR.iterdir() if path.is_dir() and not path.name.startswith(".")]


def check_hashes(repos: list[Path]) -> None:
    missing = [repo.name for repo in repos if not (repo / ".integrity" / "file_hashes.json").is_file()]
    print(f"repositories={len(repos)} manifests={len(repos) - len(missing)}")
    if missing:
        raise AssertionError(f"Missing integrity manifests: {missing}")


def check_highway() -> None:
    sys.path.insert(0, str(ROOT))
    from apex_highway import APEXHighwayEngine

    health = APEXHighwayEngine(root_dir=REPOS_DIR).scan_mesh_health()
    print(f"mesh={health['mesh_status']} coverage={health['mesh_coverage_percent']}%")
    if health["mesh_status"] != "OPERATIONAL":
        raise AssertionError("workspace mesh is not OPERATIONAL")


def check_hero_tests() -> None:
    for name in ("spacex-thermal-protection", "xai-colossus-cooling", "AKOS"):
        repo = REPOS_DIR / name
        if not repo.is_dir():
            raise AssertionError(f"required hero repository missing: {name}")
        env = os.environ.copy()
        env["PYTHONPATH"] = os.pathsep.join(
            value for value in (str(repo / "src"), str(repo), env.get("PYTHONPATH", "")) if value
        )
        completed = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", "." if name == "AKOS" else "tests"],
            cwd=repo,
            env=env,
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode:
            raise AssertionError(f"{name} tests failed\n{completed.stdout}\n{completed.stderr}")
        print(f"{name}: PASS")


def main() -> int:
    started = time.perf_counter()
    repos = require_workspace()
    check_hashes(repos)
    check_highway()
    check_hero_tests()
    completed = subprocess.run([sys.executable, "tools/public_surface_audit.py"], cwd=ROOT, check=False)
    if completed.returncode:
        raise AssertionError("public surface audit failed")
    print(f"WORKSPACE INTEGRATION AUDIT: PASS seconds={time.perf_counter() - started:.3f}")
    print("Local integration evidence; not a production deployment claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
