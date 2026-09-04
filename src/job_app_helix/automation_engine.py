#!/usr/bin/env python3
"""
Helix Automation Engine — Execute helix automations (brainsync, crystallization, evidence adaptation) as callable capabilities.

L1 Component: Atomic interface boundaries and deterministic input/output validation.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

HELIX_ROOT = Path("/data/data/com.termux/files/home/job-app-helix/helix")
AUTOMATIONS_DIR = HELIX_ROOT / "automations"
PROOFS_DIR = HELIX_ROOT / "proofs"


@dataclass
class AutomationResult:
    automation: str
    target: str
    success: bool
    output: Any
    receipt_hash: str
    duration_ms: int


AUTOMATIONS = {
    "brainsync_index": {
        "script": "brainsync_index_skills.py",
        "description": "Index skills into brainsync registry",
        "entrypoint": "main",
    },
    "brainsync_normalize": {
        "script": "brainsync_kind_normalize.py",
        "description": "Normalize skill kinds in brainsync",
        "entrypoint": "main",
    },
    "brainsync_sanitize": {
        "script": "brainsync_path_sanitize.py",
        "description": "Sanitize paths in brainsync",
        "entrypoint": "main",
    },
    "crystallization_crawl": {
        "script": "../src/job_app_helix/crystallization_crawler.py",
        "description": "Crawl and crystallize repository evidence",
        "entrypoint": "main",
    },
    "evidence_adapt": {
        "script": "../src/job_app_helix/live_evidence_adapter.py",
        "description": "Adapt live evidence for portfolio integration",
        "entrypoint": "main",
    },
}


def run_automation(automation: str, target: str, params: dict[str, Any]) -> AutomationResult:
    import time

    if automation not in AUTOMATIONS:
        return AutomationResult(
            automation=automation,
            target=target,
            success=False,
            output={"error": f"Unknown automation: {automation}"},
            receipt_hash="",
            duration_ms=0,
        )

    auto = AUTOMATIONS[automation]
    script_path = (AUTOMATIONS_DIR / auto["script"]).resolve()

    if not script_path.exists():
        return AutomationResult(
            automation=automation,
            target=target,
            success=False,
            output={"error": f"Script not found: {script_path}"},
            receipt_hash="",
            duration_ms=0,
        )

    start = time.time()
    try:
        cmd = [sys.executable, str(script_path), "--target", target]
        for k, v in params.items():
            cmd.extend([f"--{k}", str(v)])

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(HELIX_ROOT),
        )
        duration_ms = int((time.time() - start) * 1000)

        output = {
            "stdout": result.stdout[-5000:] if result.stdout else "",
            "stderr": result.stderr[-5000:] if result.stderr else "",
            "returncode": result.returncode,
        }

        success = result.returncode == 0
    except subprocess.TimeoutExpired:
        duration_ms = 120000
        output = {"error": "Timeout"}
        success = False
    except Exception as e:
        duration_ms = int((time.time() - start) * 1000)
        output = {"error": str(e)}
        success = False

    receipt_data = f"{automation}:{target}:{success}:{datetime.now(timezone.utc).isoformat()}"
    receipt_hash = hashlib.sha256(receipt_data.encode()).hexdigest()[:16]

    return AutomationResult(
        automation=automation,
        target=target,
        success=success,
        output=output,
        receipt_hash=receipt_hash,
        duration_ms=duration_ms,
    )


def run_proof(proof: str, target: str, params: dict[str, Any]) -> AutomationResult:
    import time

    proof_scripts = {
        "proof_brainsync_kind_normalize": "proof_brainsync_kind_normalize.py",
        "proof_brainsync_skill_index": "proof_brainsync_skill_index.py",
    }

    if proof not in proof_scripts:
        return AutomationResult(
            automation=proof,
            target=target,
            success=False,
            output={"error": f"Unknown proof: {proof}"},
            receipt_hash="",
            duration_ms=0,
        )

    script_path = (PROOFS_DIR / proof_scripts[proof]).resolve()

    if not script_path.exists():
        return AutomationResult(
            automation=proof,
            target=target,
            success=False,
            output={"error": f"Proof script not found: {script_path}"},
            receipt_hash="",
            duration_ms=0,
        )

    start = time.time()
    try:
        cmd = [sys.executable, str(script_path), "--target", target]
        for k, v in params.items():
            cmd.extend([f"--{k}", str(v)])

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(HELIX_ROOT),
        )
        duration_ms = int((time.time() - start) * 1000)

        output = {
            "stdout": result.stdout[-5000:] if result.stdout else "",
            "stderr": result.stderr[-5000:] if result.stderr else "",
            "returncode": result.returncode,
        }

        success = result.returncode == 0
    except subprocess.TimeoutExpired:
        duration_ms = 120000
        output = {"error": "Timeout"}
        success = False
    except Exception as e:
        duration_ms = int((time.time() - start) * 1000)
        output = {"error": str(e)}
        success = False

    receipt_data = f"{proof}:{target}:{success}:{datetime.now(timezone.utc).isoformat()}"
    receipt_hash = hashlib.sha256(receipt_data.encode()).hexdigest()[:16]

    return AutomationResult(
        automation=proof,
        target=target,
        success=success,
        output=output,
        receipt_hash=receipt_hash,
        duration_ms=duration_ms,
    )


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Execute helix automations as callable capabilities")
    parser.add_argument("--automation", required=True, help="Automation to run")
    parser.add_argument("--target", required=True, help="Target path or identifier")
    parser.add_argument("--params", default="{}", help="JSON parameters")
    parser.add_argument("--output", default="automation_result.json", help="Output file")
    args = parser.parse_args()

    params = json.loads(args.params)

    if args.automation.startswith("proof_"):
        result = run_proof(args.automation, args.target, params)
    else:
        result = run_automation(args.automation, args.target, params)

    Path(args.output).write_text(json.dumps(asdict(result), indent=2))

    status = "SUCCESS" if result.success else "FAILED"
    print(f"Automation {args.automation}: {status} ({result.duration_ms}ms)")
    print(f"Receipt: {result.receipt_hash}")
    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())