from __future__ import annotations

import argparse
import base64
import json
import os
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
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "job-app-helix-branch-cleaner",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        request = urllib.request.Request(
            f"{API_ROOT}{path}",
            headers=headers,
            method=method,
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
                raise CleanupError(f"GitHub API {method} {path} returned {status}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise CleanupError(f"GitHub API request failed for {method} {path}: {exc}") from exc

        if status not in expected:
            raise CleanupError(f"GitHub API {method} {path} returned unexpected {status}")
        if not raw:
            return status, None
        try:
            return status, json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise CleanupError(f"GitHub API returned malformed JSON for {method} {path}") from exc

    def get_ref(self, branch: str) -> tuple[int, dict[str, Any] | None]:
        encoded = urllib.parse.quote(branch, safe="")
        status, payload = self.request(
            "GET",
            f"/repos/{self.repository}/git/ref/heads/{encoded}",
            expected=(200, 404),
        )
        return status, payload if isinstance(payload, dict) else None

    def delete_ref(self, branch: str) -> None:
        if not self.token:
            raise CleanupError("A GitHub token is required to delete branches")
        encoded = urllib.parse.quote(branch, safe="")
        self.request(
            "DELETE",
            f"/repos/{self.repository}/git/refs/heads/{encoded}",
            expected=(204,),
        )

    def get_pull(self, number: int) -> dict[str, Any]:
        _, payload = self.request("GET", f"/repos/{self.repository}/pulls/{number}")
        if not isinstance(payload, dict):
            raise CleanupError(f"Pull request #{number} returned no object")
        return payload

    def compare(self, base: str, head: str) -> dict[str, Any]:
        base_encoded = urllib.parse.quote(base, safe="")
        head_encoded = urllib.parse.quote(head, safe="")
        _, payload = self.request(
            "GET",
            f"/repos/{self.repository}/compare/{base_encoded}...{head_encoded}",
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
        path_encoded = "/".join(urllib.parse.quote(part, safe="") for part in path.split("/"))
        query = urllib.parse.urlencode({"ref": ref})
        _, payload = self.request(
            "GET",
            f"/repos/{self.repository}/contents/{path_encoded}?{query}",
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
        raise CleanupError(f"Unable to load obsolete branch manifest {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise CleanupError("Obsolete branch manifest must be a JSON object")
    if payload.get("schema") != "glaciereq.obsolete-branches.v1":
        raise CleanupError("Unsupported obsolete branch manifest schema")
    branches = payload.get("branches")
    if not isinstance(branches, list) or not branches:
        raise CleanupError("Obsolete branch manifest must declare branches")
    names = [entry.get("name") for entry in branches if isinstance(entry, dict)]
    if len(names) != len(set(names)):
        raise CleanupError("Obsolete branch manifest contains duplicate names")
    return payload


def _validate_pull_branch(
    pull: dict[str, Any],
    *,
    branch: str,
    default_branch: str,
    merged: bool,
) -> None:
    head = pull.get("head")
    base = pull.get("base")
    if not isinstance(head, dict) or head.get("ref") != branch:
        raise CleanupError(f"PR #{pull.get('number')} does not belong to branch {branch}")
    if not isinstance(base, dict) or base.get("ref") != default_branch:
        raise CleanupError(f"PR #{pull.get('number')} does not target {default_branch}")
    if merged and not pull.get("merged_at"):
        raise CleanupError(f"PR #{pull.get('number')} is not merged")
    if not merged and pull.get("state") != "closed":
        raise CleanupError(f"PR #{pull.get('number')} is not closed")


def _preflight_entry(
    api: GitHubAPI,
    entry: dict[str, Any],
    *,
    default_branch: str,
) -> tuple[str, str]:
    branch = entry.get("name")
    policy = entry.get("policy")
    if not isinstance(branch, str) or not branch:
        raise CleanupError(f"Invalid branch entry: {entry}")
    if branch == default_branch:
        raise CleanupError("Default branch may never appear in the cleanup manifest")
    if not isinstance(policy, str):
        raise CleanupError(f"Missing cleanup policy for {branch}")

    if policy == "merged_pr":
        pull_number = entry.get("pull_request")
        if not isinstance(pull_number, int):
            raise CleanupError(f"merged_pr policy requires pull_request for {branch}")
        pull = api.get_pull(pull_number)
        _validate_pull_branch(
            pull,
            branch=branch,
            default_branch=default_branch,
            merged=True,
        )
        return "VERIFIED", f"PR #{pull_number} merged at {pull['merged_at']}"

    if policy == "superseded_pr":
        closed_number = entry.get("closed_pull_request")
        replacement_number = entry.get("replacement_pull_request")
        if not isinstance(closed_number, int) or not isinstance(replacement_number, int):
            raise CleanupError(f"superseded_pr policy requires two PR numbers for {branch}")
        closed = api.get_pull(closed_number)
        replacement = api.get_pull(replacement_number)
        _validate_pull_branch(
            closed,
            branch=branch,
            default_branch=default_branch,
            merged=False,
        )
        if closed.get("merged_at"):
            raise CleanupError(f"Superseded PR #{closed_number} unexpectedly merged")
        replacement_head = replacement.get("head")
        replacement_base = replacement.get("base")
        if not replacement.get("merged_at"):
            raise CleanupError(f"Replacement PR #{replacement_number} is not merged")
        if not isinstance(replacement_base, dict) or replacement_base.get("ref") != default_branch:
            raise CleanupError(f"Replacement PR #{replacement_number} does not target main")
        if not isinstance(replacement_head, dict):
            raise CleanupError(f"Replacement PR #{replacement_number} has no head metadata")
        return (
            "VERIFIED",
            f"PR #{closed_number} closed unmerged; replacement PR #{replacement_number} merged",
        )

    if policy == "stale_dependency":
        open_pulls = api.open_pulls_for_branch(branch)
        if open_pulls:
            numbers = [pull.get("number") for pull in open_pulls]
            raise CleanupError(f"Stale dependency branch still has open PRs: {numbers}")
        comparison = api.compare(default_branch, branch)
        files = comparison.get("files")
        if not isinstance(files, list):
            raise CleanupError(f"Dependency comparison returned no files for {branch}")
        actual_files = sorted(
            file.get("filename") for file in files if isinstance(file, dict) and file.get("filename")
        )
        expected_files = sorted(entry.get("expected_files", []))
        if actual_files != expected_files:
            raise CleanupError(
                f"Stale dependency file set changed for {branch}: {actual_files} != {expected_files}"
            )
        pyproject = api.read_text_file("pyproject.toml", branch)
        if 'version = "0.2.0"' not in pyproject:
            raise CleanupError("Stale dependency branch no longer carries the expected version downgrade")
        if "job-app-helix-portfolio" in pyproject:
            raise CleanupError("Stale dependency branch unexpectedly contains the current portfolio CLI")
        return (
            "VERIFIED",
            "No open PR; patch remains limited to pyproject.toml and uv.lock and is stale against 0.3.0",
        )

    raise CleanupError(f"Unsupported cleanup policy {policy!r} for {branch}")


def cleanup(
    manifest_path: Path,
    *,
    repository: str,
    token: str | None,
    apply: bool,
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
            status, ref = api.get_ref(branch)
            if status == 404:
                results.append(
                    BranchResult(
                        branch=branch,
                        policy=policy,
                        reason=reason,
                        ref_sha=None,
                        preflight="ALREADY_ABSENT",
                        outcome="NO_ACTION",
                        detail="Branch reference does not exist",
                    )
                )
                continue
            if ref is None:
                raise CleanupError(f"Branch {branch} returned no ref object")
            obj = ref.get("object")
            ref_sha = obj.get("sha") if isinstance(obj, dict) else None
            if not isinstance(ref_sha, str):
                raise CleanupError(f"Branch {branch} has no commit SHA")

            preflight, detail = _preflight_entry(
                api,
                raw_entry,
                default_branch=default_branch,
            )
            if apply:
                api.delete_ref(branch)
                after_status, _ = api.get_ref(branch)
                if after_status != 404:
                    raise CleanupError(f"Branch {branch} still exists after delete")
                outcome = "DELETED"
            else:
                outcome = "DRY_RUN"
            results.append(
                BranchResult(
                    branch=branch,
                    policy=policy,
                    reason=reason,
                    ref_sha=ref_sha,
                    preflight=preflight,
                    outcome=outcome,
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
                    preflight="FAILED",
                    outcome="PRESERVED",
                    detail=str(exc),
                )
            )

    receipt = {
        "schema": "glaciereq.obsolete-branch-cleanup-receipt.v1",
        "repository": repository,
        "default_branch": default_branch,
        "mode": "APPLY" if apply else "DRY_RUN",
        "conclusion": "FAILED" if failures else "VERIFIED",
        "results": [asdict(result) for result in results],
        "failures": failures,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if failures:
        raise CleanupError("; ".join(failures))
    return results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify and remove explicitly obsolete branches")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--repository", default=os.environ.get("GITHUB_REPOSITORY", ""))
    parser.add_argument("--token", default=os.environ.get("GITHUB_TOKEN"))
    parser.add_argument("--apply", action="store_true")
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
        results = cleanup(
            args.manifest.resolve(),
            repository=args.repository,
            token=args.token,
            apply=args.apply,
            output=args.output.resolve(),
        )
    except CleanupError as exc:
        print(f"Branch cleanup failed closed: {exc}")
        return 1
    deleted = sum(result.outcome == "DELETED" for result in results)
    dry_run = sum(result.outcome == "DRY_RUN" for result in results)
    absent = sum(result.preflight == "ALREADY_ABSENT" for result in results)
    print(f"Branch cleanup verified: deleted={deleted} dry_run={dry_run} already_absent={absent}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
