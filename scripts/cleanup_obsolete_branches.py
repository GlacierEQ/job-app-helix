from __future__ import annotations

import argparse
import base64
import json
import os
import tomllib
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "manifests" / "obsolete_branches.json"
API_ROOT = "https://api.github.com"


class CleanupError(RuntimeError):
    pass


@dataclass(frozen=True)
class BranchResult:
    branch: str
    policy: str
    reason: str
    ref_sha: str | None
    preflight: str
    outcome: str
    detail: str


class GitHubAPI:
    """Read-only GitHub adapter for historical branch-lineage inspection."""

    def __init__(self, repository: str, token: str | None) -> None:
        self.repository = repository
        self.token = token

    def request(
        self,
        method: str,
        path: str,
        *,
        expected: tuple[int, ...] = (200,),
    ) -> tuple[int, Any | None]:
        if method != "GET":
            raise CleanupError(
                "Branch-lineage audit is permanently read-only; mutation methods are forbidden"
            )
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "job-app-helix-branch-lineage-auditor",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        request = urllib.request.Request(
            f"{API_ROOT}{path}", headers=headers, method="GET"
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                status = response.status
                raw = response.read()
        except urllib.error.HTTPError as exc:
            status = exc.code
            raw = exc.read()
            if status not in expected:
                detail = raw.decode("utf-8", errors="replace")[-2000:]
                raise CleanupError(
                    f"GitHub API GET {path} returned {status}: {detail}"
                ) from exc
        except urllib.error.URLError as exc:
            raise CleanupError(f"GitHub API request failed for GET {path}: {exc}") from exc
        if status not in expected:
            raise CleanupError(f"GitHub API GET {path} returned unexpected {status}")
        if not raw:
            return status, None
        try:
            return status, json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise CleanupError("GitHub API returned malformed JSON") from exc

    def get_ref(self, branch: str) -> tuple[int, dict[str, Any] | None]:
        encoded = urllib.parse.quote(branch, safe="")
        status, payload = self.request(
            "GET",
            f"/repos/{self.repository}/git/ref/heads/{encoded}",
            expected=(200, 404),
        )
        return status, payload if isinstance(payload, dict) else None

    def get_pull(self, number: int) -> dict[str, Any]:
        _, payload = self.request("GET", f"/repos/{self.repository}/pulls/{number}")
        if not isinstance(payload, dict):
            raise CleanupError(f"Pull request #{number} returned no object")
        return payload

    def compare(self, base: str, head: str) -> dict[str, Any]:
        base_encoded = urllib.parse.quote(base, safe="")
        head_encoded = urllib.parse.quote(head, safe="")
        _, payload = self.request(
            "GET", f"/repos/{self.repository}/compare/{base_encoded}...{head_encoded}"
        )
        if not isinstance(payload, dict):
            raise CleanupError(f"Compare {base}...{head} returned no object")
        return payload

    def open_pulls_for_branch(self, branch: str) -> list[dict[str, Any]]:
        owner = self.repository.split("/", 1)[0]
        query = urllib.parse.urlencode({"state": "open", "head": f"{owner}:{branch}"})
        _, payload = self.request("GET", f"/repos/{self.repository}/pulls?{query}")
        if not isinstance(payload, list):
            raise CleanupError(f"Open-PR query returned no list for {branch}")
        return [item for item in payload if isinstance(item, dict)]

    def read_text_file(self, path: str, ref: str) -> str:
        encoded_path = "/".join(
            urllib.parse.quote(part, safe="") for part in path.split("/")
        )
        query = urllib.parse.urlencode({"ref": ref})
        _, payload = self.request(
            "GET", f"/repos/{self.repository}/contents/{encoded_path}?{query}"
        )
        if not isinstance(payload, dict) or payload.get("encoding") != "base64":
            raise CleanupError(f"Unable to decode {path}@{ref}")
        content = payload.get("content")
        if not isinstance(content, str):
            raise CleanupError(f"Missing file content for {path}@{ref}")
        return base64.b64decode(content).decode("utf-8")


def _load_manifest(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CleanupError(f"Unable to load branch manifest {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise CleanupError("Branch manifest must be a JSON object")
    if payload.get("schema") != "glaciereq.obsolete-branches.v1":
        raise CleanupError("Unsupported historical branch manifest schema")
    branches = payload.get("branches")
    if not isinstance(branches, list) or not branches:
        raise CleanupError("Branch manifest must declare branches")
    names = [entry.get("name") for entry in branches if isinstance(entry, dict)]
    if len(names) != len(set(names)):
        raise CleanupError("Branch manifest contains duplicate names")
    return payload


def _pull_head_sha(pull: dict[str, Any]) -> str:
    head = pull.get("head")
    if not isinstance(head, dict) or not isinstance(head.get("sha"), str):
        raise CleanupError(f"PR #{pull.get('number')} has no immutable head SHA")
    return head["sha"]


def _expected_sha(entry: dict[str, Any], key: str = "expected_head_sha") -> str:
    value = entry.get(key)
    if not isinstance(value, str) or len(value) != 40:
        raise CleanupError(f"Manifest entry requires a 40-character {key}")
    return value


def _ref_sha(api: GitHubAPI, branch: str) -> str:
    status, ref = api.get_ref(branch)
    if status != 200 or not isinstance(ref, dict):
        raise CleanupError(f"Branch {branch} is absent or malformed")
    obj = ref.get("object")
    sha = obj.get("sha") if isinstance(obj, dict) else None
    if not isinstance(sha, str):
        raise CleanupError(f"Branch {branch} has no commit SHA")
    return sha


def _require_ref_sha(ref_sha: str, expected_sha: str, branch: str) -> None:
    if ref_sha != expected_sha:
        raise CleanupError(
            f"Branch {branch} points to {ref_sha}, expected historical {expected_sha}"
        )


def _classify_entry(
    api: GitHubAPI,
    entry: dict[str, Any],
    *,
    default_branch: str,
    ref_sha: str,
) -> tuple[str, str]:
    branch = entry.get("name")
    policy = entry.get("policy")
    if not isinstance(branch, str) or not branch:
        raise CleanupError(f"Invalid branch entry: {entry}")
    if branch == default_branch:
        raise CleanupError("Default branch may never appear in the historical branch manifest")
    if not isinstance(policy, str):
        raise CleanupError(f"Missing historical policy for {branch}")

    if policy == "merged_pr":
        expected_sha = _expected_sha(entry)
        _require_ref_sha(ref_sha, expected_sha, branch)
        pull_number = entry.get("pull_request")
        if not isinstance(pull_number, int):
            raise CleanupError(f"merged_pr policy requires pull_request for {branch}")
        pull = api.get_pull(pull_number)
        if not pull.get("merged_at") or _pull_head_sha(pull) != expected_sha:
            raise CleanupError(f"PR #{pull_number} no longer matches historical merged state")
        return "OVERLAP_VERIFIED", f"PR #{pull_number} merged; donor remains preserved"

    if policy == "merge_candidate":
        pull_number = entry.get("pull_request")
        if not isinstance(pull_number, int):
            raise CleanupError(f"merge_candidate policy requires pull_request for {branch}")
        pull = api.get_pull(pull_number)
        if _pull_head_sha(pull) != ref_sha:
            raise CleanupError(f"PR #{pull_number} head does not match current donor ref")
        state = "merged" if pull.get("merged_at") else str(pull.get("state", "unknown"))
        return "OVERLAP_CANDIDATE", f"PR #{pull_number} is {state}; donor remains preserved"

    if policy == "superseded_pr":
        expected_sha = _expected_sha(entry)
        replacement_sha = _expected_sha(entry, "replacement_head_sha")
        _require_ref_sha(ref_sha, expected_sha, branch)
        closed_number = entry.get("closed_pull_request")
        replacement_number = entry.get("replacement_pull_request")
        if not isinstance(closed_number, int) or not isinstance(replacement_number, int):
            raise CleanupError(f"superseded_pr policy requires two PR numbers for {branch}")
        closed = api.get_pull(closed_number)
        replacement = api.get_pull(replacement_number)
        if closed.get("merged_at"):
            raise CleanupError(f"Historical superseded PR #{closed_number} unexpectedly merged")
        if _pull_head_sha(closed) != expected_sha:
            raise CleanupError(f"Closed PR #{closed_number} head changed")
        if not replacement.get("merged_at") or _pull_head_sha(replacement) != replacement_sha:
            raise CleanupError(f"Replacement PR #{replacement_number} no longer matches receipt")
        return (
            "PARTIAL_OVERLAP_VERIFIED",
            f"PR #{closed_number} has merged replacement #{replacement_number}; donor remains preserved",
        )

    if policy == "stale_dependency":
        expected_sha = _expected_sha(entry)
        _require_ref_sha(ref_sha, expected_sha, branch)
        open_pulls = api.open_pulls_for_branch(branch)
        if open_pulls:
            numbers = [pull.get("number") for pull in open_pulls]
            raise CleanupError(f"Historical stale-dependency branch now has open PRs: {numbers}")
        comparison = api.compare(default_branch, expected_sha)
        files = comparison.get("files")
        if not isinstance(files, list):
            raise CleanupError(f"Dependency comparison returned no files for {branch}")
        actual_files = sorted(
            file.get("filename") for file in files if isinstance(file, dict) and file.get("filename")
        )
        expected_files = sorted(entry.get("expected_files", []))
        if actual_files != expected_files:
            raise CleanupError(
                f"Historical stale-dependency file set changed: {actual_files} != {expected_files}"
            )
        pyproject_text = api.read_text_file("pyproject.toml", expected_sha)
        try:
            pyproject = tomllib.loads(pyproject_text)
        except tomllib.TOMLDecodeError as exc:
            raise CleanupError("Historical stale-dependency pyproject is malformed") from exc
        expected_version = entry.get("expected_version")
        actual_version = pyproject.get("project", {}).get("version")
        if actual_version != expected_version:
            raise CleanupError(
                f"Historical dependency version {actual_version} != {expected_version}"
            )
        return (
            "HISTORICAL_CLASSIFICATION_VERIFIED",
            "Historical stale-dependency classification reproduced; donor remains preserved",
        )

    raise CleanupError(f"Unsupported historical policy {policy!r} for {branch}")


def _write_receipt(output: Path, payload: dict[str, Any]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def audit(
    manifest_path: Path,
    *,
    repository: str,
    token: str | None,
    output: Path,
) -> list[BranchResult]:
    manifest = _load_manifest(manifest_path)
    if manifest.get("repository") != repository:
        raise CleanupError(
            f"Manifest repository {manifest.get('repository')} does not match {repository}"
        )
    default_branch = manifest.get("default_branch")
    if not isinstance(default_branch, str) or not default_branch:
        raise CleanupError("Manifest default_branch is missing")

    api = GitHubAPI(repository, token)
    results: list[BranchResult] = []
    failures: list[str] = []

    for raw_entry in manifest["branches"]:
        if not isinstance(raw_entry, dict):
            failures.append(f"Invalid manifest entry: {raw_entry}")
            continue
        branch = str(raw_entry.get("name", ""))
        policy = str(raw_entry.get("policy", ""))
        reason = str(raw_entry.get("reason", ""))
        try:
            status, _ = api.get_ref(branch)
            if status == 404:
                results.append(
                    BranchResult(
                        branch=branch,
                        policy=policy,
                        reason=reason,
                        ref_sha=None,
                        preflight="HISTORICALLY_ABSENT",
                        outcome="LINEAGE_POINTER_REQUIRED",
                        detail="Remote ref is absent; absence is historical fact, not retirement authority",
                    )
                )
                continue
            ref_sha = _ref_sha(api, branch)
            preflight, detail = _classify_entry(
                api, raw_entry, default_branch=default_branch, ref_sha=ref_sha
            )
            results.append(
                BranchResult(
                    branch=branch,
                    policy=policy,
                    reason=reason,
                    ref_sha=ref_sha,
                    preflight=preflight,
                    outcome="PRESERVE_ACTIVE_IN_MESH",
                    detail=detail,
                )
            )
        except CleanupError as exc:
            failures.append(f"{branch}: {exc}")
            results.append(
                BranchResult(
                    branch=branch,
                    policy=policy,
                    reason=reason,
                    ref_sha=None,
                    preflight="READBACK_UNRESOLVED",
                    outcome="PRESERVE_ACTIVE_IN_MESH",
                    detail=str(exc),
                )
            )

    payload = {
        "schema": "glaciereq.branch-lineage-audit-receipt.v2",
        "repository": repository,
        "default_branch": default_branch,
        "mode": "READ_ONLY_LINEAGE_AUDIT",
        "holographic_mesh_anti_replacement": True,
        "remote_ref_deletion_authorized": False,
        "unique_contribution_zero_proven": False,
        "results": [asdict(result) for result in results],
        "failures": failures,
        "conclusion": "READBACK_UNRESOLVED" if failures else "VERIFIED_READ_ONLY",
    }
    _write_receipt(output, payload)
    if failures:
        raise CleanupError("; ".join(failures))
    return results


def cleanup(
    manifest_path: Path,
    *,
    repository: str,
    token: str | None,
    apply: bool = False,
    output: Path,
) -> list[BranchResult]:
    """Compatibility entrypoint retained for callers; destructive apply is forbidden."""
    if apply:
        raise CleanupError(
            "--apply is retired: branch/ref deletion is forbidden; use read-only lineage audit"
        )
    return audit(manifest_path, repository=repository, token=token, output=output)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit historical branch classifications without mutating refs"
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--repository", default=os.environ.get("GITHUB_REPOSITORY", ""))
    parser.add_argument("--token", default=os.environ.get("GITHUB_TOKEN"))
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "artifacts" / "obsolete-branch-cleanup.json",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.repository:
        raise SystemExit("--repository or GITHUB_REPOSITORY is required")
    try:
        results = audit(
            args.manifest.resolve(),
            repository=args.repository,
            token=args.token,
            output=args.output.resolve(),
        )
    except CleanupError as exc:
        print(f"Branch lineage audit unresolved: {exc}")
        return 1
    preserved = sum(result.outcome == "PRESERVE_ACTIVE_IN_MESH" for result in results)
    absent = sum(result.preflight == "HISTORICALLY_ABSENT" for result in results)
    print(
        "Branch lineage audit verified: "
        f"preserved={preserved} historically_absent={absent} deleted=0"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
