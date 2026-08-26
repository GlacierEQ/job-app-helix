from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "frontier_innovation_engine.py"


def authorization(target_state: str) -> dict[str, str]:
    return {
        "authorization_id": "operator-authorization-cli-1",
        "operator_intent_id": "operator-intent-cli-1",
        "status": "APPROVED",
        "target_state": target_state,
        "repository": "GlacierEQ/high",
        "expected_head": "abc123",
        "observed_head": "abc123",
    }


def run_payload(state: str, *, approved: bool = False) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema": "glaciereq.engineering-run.v1",
        "run_id": "cli-authority-fixture",
        "repository": "GlacierEQ/high",
        "expected_head": "abc123",
        "observed_head": "abc123",
        "state": state,
        "history": [],
    }
    if approved:
        payload["operator_authorization"] = authorization(state)
    return payload


def invoke(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def write_payload(tmp_path: Path, name: str, payload: dict[str, object]) -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_cli_validate_rejects_forged_operator_only_state(tmp_path: Path) -> None:
    run_path = write_payload(tmp_path, "forged.json", run_payload("ARCHIVED"))

    result = invoke("validate", "engineering-run", str(run_path))

    assert result.returncode != 0
    assert "operator_authorization" in result.stderr


def test_cli_transition_cannot_self_assign_operator_only_state(tmp_path: Path) -> None:
    run = run_payload("PROMOTION_READY")
    run["operator_authorization"] = authorization("SOURCE_BOUND")
    run_path = write_payload(tmp_path, "promotion-ready.json", run)

    result = invoke(
        "transition",
        str(run_path),
        "SOURCE_BOUND",
        "--evidence-ref",
        "operator:authorization",
    )

    assert result.returncode != 0
    assert "operator-only status" in result.stderr


def test_cli_allows_monitored_reentry_from_operator_authorized_state(tmp_path: Path) -> None:
    run_path = write_payload(
        tmp_path,
        "operator-authorized.json",
        run_payload("SOURCE_BOUND", approved=True),
    )

    result = invoke(
        "transition",
        str(run_path),
        "MONITORED",
        "--evidence-ref",
        "operator:authorization",
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["state"] == "MONITORED"
