"""Bound-surface contracts: hash integrity, CI references, machine-path hygiene."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

from scripts.check_public_surface import (
    MACHINE_PATH_CONTENT,
    MACHINE_PATH_EXEMPT_PREFIXES,
    SELF_REFERENTIAL_POLICY_PATHS,
)

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
MACHINE_PATH_NEEDLES = tuple(MACHINE_PATH_CONTENT)
PYTHON_SCRIPT_REF = re.compile(r"python3?\s+(?:-[A-Za-z]+\s+)*([\w./-]+\.py)\b")


def _tracked_files() -> list[str]:
    completed = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return [item.decode() for item in completed.stdout.split(b"\0") if item]


def test_helix_integrity_manifest_matches_files() -> None:
    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "verify_helix_integrity.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_every_workflow_script_reference_resolves() -> None:
    missing: list[str] = []
    for workflow in sorted(WORKFLOWS.glob("*.yml")):
        for reference in PYTHON_SCRIPT_REF.findall(workflow.read_text(encoding="utf-8")):
            if "$" in reference or "{{" in reference:
                continue
            if not (ROOT / reference).exists():
                missing.append(f"{workflow.name}: {reference}")
    assert missing == [], missing


def test_no_machine_paths_on_the_live_surface() -> None:
    offenders: list[str] = []
    for relative in _tracked_files():
        if relative.startswith(MACHINE_PATH_EXEMPT_PREFIXES):
            continue
        if relative in SELF_REFERENTIAL_POLICY_PATHS:
            continue
        path = ROOT / relative
        if not path.is_file() or path.suffix.lower() not in {".py", ".md", ".yaml", ".yml", ".toml", ".json", ".sh"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for needle in MACHINE_PATH_NEEDLES:
            if needle in text:
                offenders.append(f"{relative}: {needle}")
    assert offenders == [], offenders
