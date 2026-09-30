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


def _request(path: str, token: str | None) -> dict[str, Any]:
    request = urllib.request.Request(
        f"{API}{path}",
        headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "GlacierEQ-apex-evolution-admission/1.0",
        },
    )
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(request, timeout=20) as response:
        value = json.load(response)
    if not isinstance(value, dict):
        _fail(f"GitHub proof readback was not an object: {path}")
    return value


def _get(path: str) -> dict[str, Any]:
    token = os.environ.get("GITHUB_TOKEN")
    try:
        return _request(path, token)
    except urllib.error.HTTPError as exc:
        if token and exc.code in {403, 404}:
            try:
                return _request(path, None)
            except (urllib.error.URLError, json.JSONDecodeError) as fallback_exc:
                _fail(f"GitHub public proof fallback failed for {path}: {fallback_exc}")
        _fail(f"GitHub proof readback failed for {path}: HTTP {exc.code}")
    except (urllib.error.URLError, json.JSONDecodeError) as exc:
        _fail(f"GitHub proof readback failed for {path}: {exc}")


def main() -> None:
    record = json.loads(RECORD.read_text(encoding="utf-8"))
    pointer = record["evolution_receipt"]
    receipt_path = ROOT / pointer["path"]
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    proof = receipt["proof"]
    exact_blobs = proof["exact_git_blobs"]
    disclosure = proof["disclosure"]

    if proof["public_host_repository"] != PUBLIC_REPO:
        _fail("public proof host repository drift")
    if disclosure["source_repository_visibility"] != "private":
        _fail("reference repository visibility boundary drift")
    if disclosure["bounded_evolution_source_slice_publicly_disclosed"] is not True:
        _fail("public evolution source-slice disclosure is not truthful")
    if set(disclosure["public_slice_files"]) != set(EXPECTED_FILES):
        _fail("public evolution source-slice file set drift")

    run_id = proof["workflow_run_id"]
    run = _get(f"/repos/{PUBLIC_REPO}/actions/runs/{run_id}")
    if run.get("id") != run_id:
        _fail("public proof run identity drift")
    if run.get("status") != "completed" or run.get("conclusion") != "success":
        _fail("public proof run is not completed/success")
    if run.get("head_sha") != proof["workflow_run_head_sha"]:
        _fail("public proof run head drift")
    repository = run.get("repository", {})
    if repository.get("full_name") != PUBLIC_REPO or repository.get("private") is not False:
        _fail("admitted proof host is not the expected public repository")
    public_pr_number = proof["public_host_pull_request"]
    pull_numbers = [item.get("number") for item in run.get("pull_requests", [])]
    if public_pr_number not in pull_numbers:
        # GitHub can return an empty workflow-run pull_requests array for a historical
        # pull_request run even though the owning PR still binds the exact head.
        # Preserve the stronger provider identity by reading the PR itself rather
        # than weakening provenance or rewriting the historical receipt.
        public_pr = _get(f"/repos/{PUBLIC_REPO}/pulls/{public_pr_number}")
        if public_pr.get("number") != public_pr_number:
            _fail("public proof PR identity drift")
        if public_pr.get("head", {}).get("sha") != run.get("head_sha"):
            _fail("public proof PR head is not bound to the admitted workflow run")
        if run.get("event") != "pull_request":
            _fail("public proof run is not a pull_request event")
    expected_location = f"{PUBLIC_REPO}#{public_pr_number}"
    if disclosure["public_location"] != expected_location:
        _fail("public evolution source-slice location drift")

    artifact_id = proof["artifact_id"]
    artifact = _get(f"/repos/{PUBLIC_REPO}/actions/artifacts/{artifact_id}")
    if artifact.get("id") != artifact_id:
        _fail("public proof artifact identity drift")
    artifact_expired = artifact.get("expired") is True
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
                "public_proof_artifact_expired": artifact_expired,
                "public_proof_head": run["head_sha"],
                "public_source_slice_disclosed": True,
                "verified_git_blobs": exact_blobs,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
