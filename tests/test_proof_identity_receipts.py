from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]


def load_verifier() -> ModuleType:
    path = ROOT / "scripts" / "run_featured_verification.py"
    spec = importlib.util.spec_from_file_location("run_featured_verification", path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"Unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def init_git_repository(path: Path) -> str:
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    subprocess.run(
        ["git", "config", "user.email", "proof@example.invalid"],
        cwd=path,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Proof Receipt Test"],
        cwd=path,
        check=True,
    )
    (path / "README.md").write_text("# proof identity\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=path, check=True)
    subprocess.run(["git", "commit", "-qm", "proof identity fixture"], cwd=path, check=True)
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=path,
        text=True,
    ).strip()


def test_resolve_commit_sha_binds_to_checked_out_content(tmp_path: Path) -> None:
    module = load_verifier()
    expected = init_git_repository(tmp_path)

    assert module.resolve_commit_sha(tmp_path) == expected


def test_resolve_commit_sha_fails_closed_outside_git(tmp_path: Path) -> None:
    module = load_verifier()

    assert module.resolve_commit_sha(tmp_path) is None


def test_receipt_records_resolved_commit_even_for_invalid_contract(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = load_verifier()
    expected = init_git_repository(tmp_path)
    output = tmp_path / "receipt.json"
    log = tmp_path / "audit.log"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_featured_verification.py",
            "--name",
            "unknown-contract",
            "--repository",
            "GlacierEQ/example",
            "--ref",
            "main",
            "--path",
            str(tmp_path),
            "--surface",
            "python",
            "--output",
            str(output),
            "--log",
            str(log),
        ],
    )

    assert module.main() == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["status"] == "INVALID_CONTRACT"
    assert payload["ref"] == "main"
    assert payload["resolved_commit_sha"] == expected


def test_receipt_blocks_promotion_when_commit_identity_is_missing(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = load_verifier()
    output = tmp_path / "receipt.json"
    log = tmp_path / "audit.log"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_featured_verification.py",
            "--name",
            "unknown-contract",
            "--repository",
            "GlacierEQ/example",
            "--ref",
            "main",
            "--path",
            str(tmp_path),
            "--surface",
            "python",
            "--output",
            str(output),
            "--log",
            str(log),
        ],
    )

    assert module.main() == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["status"] == "BLOCKED_IDENTITY"
    assert payload["resolved_commit_sha"] is None
    assert payload["exit_code"] == 4
