from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = ROOT / "ci_audit_portfolio.py"


def _load_audit_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("ci_audit_portfolio", AUDIT_PATH)
    if spec is None or spec.loader is None:
        raise AssertionError(f"Unable to load {AUDIT_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(spec.name, None)
    return module


def _stub_successful_audit(
    module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> Path:
    receipt_path = tmp_path / "portfolio_ci_receipt.json"
    repos = [tmp_path / "repo-a", tmp_path / "repo-b"]
    monkeypatch.setattr(module, "RECEIPT_PATH", receipt_path)
    monkeypatch.setattr(module, "require_workspace", lambda: repos)
    monkeypatch.setattr(
        module,
        "step_1_check_hash_coverage",
        lambda supplied: {"repositories_discovered": len(supplied)},
    )
    monkeypatch.setattr(module, "step_2_apex_highway", lambda: {"mesh_status": "OPERATIONAL"})
    monkeypatch.setattr(module, "step_3_validate_language_fit", lambda: {"entries_validated": 4})
    monkeypatch.setattr(
        module,
        "step_4_runtime_sample",
        lambda: [
            module.CommandResult(
                repository="repo-a",
                command=["test"],
                returncode=0,
                status="PASSED",
                timed_out=False,
                stdout_tail="",
                stderr_tail="",
            )
        ],
    )
    monkeypatch.setattr(
        module,
        "step_5_demo_runner",
        lambda: {"status": "PASSED", "receipt": {"conclusion": "VERIFIED"}},
    )
    monkeypatch.setattr(module, "step_6_link_verification", lambda: {"links_checked": 3})
    return receipt_path


def test_main_emits_evidence_bound_partial_receipt(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = _load_audit_module()
    receipt_path = _stub_successful_audit(module, monkeypatch, tmp_path)

    module.main()

    payload = json.loads(receipt_path.read_text(encoding="utf-8"))
    output = capsys.readouterr().out
    assert payload["conclusion"] == "PARTIALLY_VERIFIED"
    assert len(payload["runtime_results"]) == 1
    assert "PORTFOLIO CONCLUSION: PARTIALLY VERIFIED" in output
    assert "NO PORTFOLIO-WIDE DEPLOYABILITY CLAIM WAS MADE" in output
    assert "100% SOLID & DEPLOYABLE" not in output


def test_failed_rerun_overwrites_running_receipt_with_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _load_audit_module()
    receipt_path = _stub_successful_audit(module, monkeypatch, tmp_path)

    def fail_mesh() -> dict[str, object]:
        raise module.AuditStepError("mesh failed", {"mesh_status": "FAILED"})

    monkeypatch.setattr(module, "step_2_apex_highway", fail_mesh)

    with pytest.raises(module.AuditStepError):
        module.main()

    payload = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert payload["conclusion"] == "FAILED"
    assert payload["error"]["message"] == "mesh failed"
    assert payload["evidence"]["mesh"]["mesh_status"] == "FAILED"


def test_runtime_verification_scope_is_explicit_and_bounded() -> None:
    module = _load_audit_module()
    repositories = tuple(check.repository for check in module.RUNTIME_CHECKS)
    assert repositories == (
        "spacex-thermal-protection",
        "xai-colossus-cooling",
        "AKOS",
    )


def test_timeout_becomes_structured_failed_result(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _load_audit_module()
    check = module.CommandCheck(
        repository="hung",
        command=("python", "-m", "pytest"),
        cwd=tmp_path,
        timeout_seconds=1,
    )

    def time_out(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(cmd=["python"], timeout=1, output="partial")

    monkeypatch.setattr(module.subprocess, "run", time_out)
    result = module._run_command_check(check)
    assert result.status == "FAILED"
    assert result.timed_out is True
    assert result.returncode == 124


def test_language_fit_rejects_missing_boundary(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _load_audit_module()
    receipt = tmp_path / "receipt.md"
    receipt.write_text("proof", encoding="utf-8")
    manifest = tmp_path / "language_fit.json"
    manifest.write_text(
        json.dumps(
            {
                "schema": "glaciereq.language-fit.v1",
                "repository": "GlacierEQ/example",
                "entries": [
                    {
                        "name": "Rust",
                        "kind": "programming_language",
                        "responsibility": "safe concurrency",
                        "boundary": "",
                        "interface_contract": "FFI",
                        "build_command": "cargo build",
                        "test_command": "cargo test",
                        "evidence_receipt": str(receipt.relative_to(tmp_path)),
                        "verification_state": "VERIFIED",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(module, "ROOT", tmp_path)

    with pytest.raises(module.AuditStepError) as raised:
        module.step_3_validate_language_fit(manifest)

    assert "boundary" in json.dumps(raised.value.evidence)


def test_relative_markdown_links_are_checked(tmp_path: Path) -> None:
    module = _load_audit_module()
    (tmp_path / "README.md").write_text("# proof", encoding="utf-8")
    map_file = tmp_path / "MAP.md"
    map_file.write_text(
        "[Local](README.md)\n[External](https://example.com)\n",
        encoding="utf-8",
    )

    result = module.step_6_link_verification(map_file)

    assert result["links_checked"] == 1
    assert result["valid"] == 1
