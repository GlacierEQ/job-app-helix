from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "compile_live_repository_evidence.py"
OBSERVATION = ROOT / "observations" / "repositories" / (
    "GlacierEQ__AKOS__1607c0d27897ea963eb572062300342f1922b84c.json"
)


def load_cli_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("compile_live_repository_evidence", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_output_failure_uses_json_error_contract() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            str(OBSERVATION),
            "--output",
            "/dev/null/assessment.json",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 2
    payload = json.loads(completed.stdout)
    assert payload["state"] == "ERROR"
    assert payload["error"]
    assert "Traceback" not in completed.stderr


def test_non_object_json_uses_json_error_contract(tmp_path: Path) -> None:
    observation = tmp_path / "null.json"
    observation.write_text("null\n", encoding="utf-8")

    completed = subprocess.run(
        [sys.executable, str(SCRIPT), str(observation)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 2
    payload = json.loads(completed.stdout)
    assert payload["state"] == "ERROR"
    assert "must be an object" in payload["error"]
    assert "Traceback" not in completed.stderr


def test_atomic_write_preserves_existing_file_on_replace_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = load_cli_module()
    target = tmp_path / "assessment.json"
    target.write_text("previous-valid-assessment\n", encoding="utf-8")

    def fail_replace(source: Path, destination: Path) -> None:
        raise OSError(f"cannot replace {source} with {destination}")

    monkeypatch.setattr(module.os, "replace", fail_replace)

    with pytest.raises(OSError, match="cannot replace"):
        module.atomic_write_text(target, "new-assessment\n")

    assert target.read_text(encoding="utf-8") == "previous-valid-assessment\n"
    assert list(tmp_path.glob(".assessment.json.*.tmp")) == []


def test_atomic_write_replaces_complete_file(tmp_path: Path) -> None:
    module = load_cli_module()
    target = tmp_path / "assessment.json"
    target.write_text("old\n", encoding="utf-8")

    module.atomic_write_text(target, "new-complete-assessment\n")

    assert target.read_text(encoding="utf-8") == "new-complete-assessment\n"
    assert list(tmp_path.glob(".assessment.json.*.tmp")) == []
