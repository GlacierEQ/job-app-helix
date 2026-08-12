from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "manifests/repo_excellence/apex-github-worker.json"
API = "https://api.github.com"
PUBLIC_REPO = "GlacierEQ/public-actions-runner-host"
EXPECTED_FILES = {
    "merge-authority.mjs": ".github/verification/apex-evolution/merge-authority.mjs",
    "merge-authority.test.mjs": ".github/verification/apex-evolution/merge-authority.test.mjs",
    "evolution-benchmark.test.mjs": (
        ".github/verification/apex-evolution/evolution-benchmark.test.mjs"
    ),
}


def _fail(message: str) -> None:
    raise SystemExit(message)


def _get(path: str) -> dict[str, Any]:
    request = urllib.request.Request(
        f"{API}{path}",
        headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "GlacierEQ-apex-evolution-admission/1.0",
        },
    )
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            value = json.load(response)
    except (urllib.error.URLError, json.JSONDecodeError) as exc:
        _fail(f"GitHub proof readback failed for {path}: {exc}")
    if not isinstance(value, dict):
        _fail(f"GitHub proof readback was not an object: {path}")
    return value


def main() -> None:
    record = json.loads(RECORD.read_text(encoding="utf-8"))
    pointer = record["evolution_receipt"]
    receipt_path = ROOT / pointer["path"]
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    proof = receipt["proof"]
    exact_blobs = proof["exact_git_blobs"]

    if proof["public_host_repository"] != PUBLIC_REPO:
        _fail("public proof host repository drift")

    run_id = proof["workflow_run_id"]
    run = _get(f"/repos/{PUBLIC_REPO}/actions/runs/{run_id}")
    if run.get("id") != run_id:
        _fail("public proof run identity drift")
    if run.get("status") != "completed" or run.get("conclusion") != "success":
        _fail("public proof run is not completed/success")
    if run.get("head_sha") != proof["workflow_run_head_sha"]:
        _fail("public proof run head drift")
    pull_numbers = [item.get("number") for item in run.get("pull_requests", [])]
    if proof["public_host_pull_request"] not in pull_numbers:
        _fail("public proof PR is not bound to the admitted workflow run")

    artifact_id = proof["artifact_id"]
    artifact = _get(f"/repos/{PUBLIC_REPO}/actions/artifacts/{artifact_id}")
    if artifact.get("id") != artifact_id:
        _fail("public proof artifact identity drift")
    if artifact.get("expired") is not False:
        _fail("public proof artifact is expired")
    if artifact.get("digest") != proof["artifact_digest"]:
        _fail("public proof artifact digest drift")
    artifact_run = artifact.get("workflow_run", {})
    if artifact_run.get("id") != run_id:
        _fail("public proof artifact is not bound to the admitted run")
    if artifact_run.get("head_sha") != proof["workflow_run_head_sha"]:
        _fail("public proof artifact head drift")

    ref = urllib.parse.quote(proof["workflow_run_head_sha"], safe="")
    for name, path in EXPECTED_FILES.items():
        encoded_path = urllib.parse.quote(path, safe="/")
        content = _get(f"/repos/{PUBLIC_REPO}/contents/{encoded_path}?ref={ref}")
        if content.get("type") != "file":
            _fail(f"public proof source is not a file: {name}")
        if content.get("sha") != exact_blobs[name]:
            _fail(f"public proof Git blob drift: {name}")

    print(
        json.dumps(
            {
                "status": "PASS",
                "repository": record["identity"]["repository"],
                "state": record["state"],
                "public_proof_run_id": run_id,
                "public_proof_artifact_id": artifact_id,
                "public_proof_artifact_digest": artifact["digest"],
                "public_proof_head": run["head_sha"],
                "verified_git_blobs": exact_blobs,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
