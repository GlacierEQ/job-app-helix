"""Regression tests for CI gates left stale by capability and receipt evolution."""
from __future__ import annotations

import importlib.util
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def module_for(path: str):
    spec = importlib.util.spec_from_file_location("ci_regression_under_test_" + Path(path).stem, ROOT / path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_tracked_preserved_readiness_receipt_is_not_blocked_as_private_state():
    checker = module_for("scripts/check_public_surface.py")
    present = ROOT / ("state/PRODUCTION_READINESS" "_VERDICT.md")
    assert present.exists()
    assert checker.check_paths([present]) == []
    forbidden = ROOT / "state/private-credentials.json"
    assert any("forbidden tracked path" in issue for issue in checker.check_paths([forbidden]))


def test_queue_runtime_probe_keeps_lanes_separate_from_uncapped_scores():
    workflow = (ROOT / ".github/workflows/application-execution-queue-proof.yml").read_text()
    assert "assert second.lane == \"PREPARE_GAPS\"" in workflow
    assert "assert second.priority_score <= 45.0" not in workflow
    assert "assert second.priority_score > 45.0" in workflow


def _external_module():
    return module_for("scripts/validate_apex_evolution_external_proof.py")


def _run_and_pr(proof):
    sha = proof["workflow_run_head_sha"]
    run = {
        "id": proof.get("workflow_run_id", 1),
        "status": "completed", "conclusion": "success",
        "head_sha": sha, "event": "pull_request", "pull_requests": [],
        "created_at": "2026-08-12T14:57:02Z",
        "repository": {"full_name": "GlacierEQ/public-actions-runner-host", "private": False},
    }
    pr = {"number": proof["public_host_pull_request"],
          "head": {"sha": sha, "repo": {"full_name": "GlacierEQ/public-actions-runner-host"}}}
    return run, pr


def test_pr_binding_accepts_exact_native_pr_head_when_run_array_empty(monkeypatch):
    module = _external_module()
    proof = {"public_host_pull_request": 269, "workflow_run_head_sha": "a" * 40}
    run, pr = _run_and_pr(proof)
    monkeypatch.setattr(module, "_get", lambda path: pr)
    module.verify_run_pr_association(run, proof)


def test_pr_binding_rejects_unrelated_native_pr_head(monkeypatch):
    module = _external_module()
    proof = {"public_host_pull_request": 269, "workflow_run_head_sha": "a" * 40}
    run, pr = _run_and_pr(proof)
    pr["head"]["sha"] = "b" * 40
    monkeypatch.setattr(module, "_get", lambda path: pr)
    with pytest.raises(SystemExit, match="public proof PR head does not match"):
        module.verify_run_pr_association(run, proof)


def test_retired_historical_artifact_is_not_misreported_as_live(monkeypatch, capsys):
    module = _external_module()
    record = json.loads(module.RECORD.read_text())
    receipt = json.loads((module.ROOT / record["evolution_receipt"]["path"]).read_text())
    proof = receipt["proof"]
    run, pr = _run_and_pr(proof)
    def fake_get(path):
        if "/actions/runs/" in path:
            return run
        if "/pulls/" in path:
            return pr
        if "/actions/artifacts/" in path:
            raise SystemExit("GitHub proof readback failed: HTTP 404")
        if "/contents/" in path:
            for key, expected_path in module.EXPECTED_FILES.items():
                if expected_path in path:
                    return {"type": "file", "sha": proof["exact_git_blobs"][key]}
        raise AssertionError(f"Unexpected API path: {path}")
    monkeypatch.setattr(module, "_get", fake_get)
    module.main()
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "HISTORICAL_PROOF_ONLY"
    assert result["proof_current"] is False
    assert result["public_source_blobs_verified"] is True


def test_recent_missing_artifact_still_fails():
    module = _external_module()
    recent = {"created_at": datetime.now(UTC).isoformat()}
    with pytest.raises(SystemExit, match="artifact"):
        module.classify_missing_artifact(recent, "GitHub proof readback failed: HTTP 404")
