from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "compile_live_repository_evidence.py"
OBSERVATION = ROOT / "observations" / "repositories" / (
    "GlacierEQ__AKOS__1607c0d27897ea963eb572062300342f1922b84c.json"
)


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
