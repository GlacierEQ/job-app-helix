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


@dataclass(frozen=True)
class DeletionCandidate:
    branch: str
    policy: str
    reason: str
    ref_sha: str
    preflight: str
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
        payload: dict[str, Any] | None = None,
    ) -> tuple[int, Any | None]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "job-app-helix-branch-cleaner",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        body = None
        if payload is not None:
            headers["Content-Type"] = "application/json"
            body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            f"{API_ROOT}{path}",
            headers=headers,
            data=body,
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
                message = f"GitHub API {method} {path} returned {status}: {detail}"
                raise CleanupError(message) from exc
        except urllib.error.URLError as exc:
            message = f"GitHub API request failed for {method} {path}: {exc}"
            raise CleanupError(message) from exc

        if status not in expected:
            raise CleanupError(f"GitHub API {method} {path} returned unexpected {status}")
        if not raw:
            return status, None
        try:
            return status, json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            message = f"GitHub API returned malformed JSON for {method} {path}"
            raise CleanupError(message) from exc

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

    def create_ref(self, branch: str, sha: str) -> None:
        if not self.token:
            raise CleanupError("A GitHub token is required to restore branches")
        self.request(
            "POST",
            f"/repos/{self.repository}/git/refs",
            expected=(201,),
            payload={"ref": f"refs/heads/{branch}", "sha": sha},
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
        encoded_path = "/".join(
            urllib.parse.quote(part, safe="") for part in path.split("/")
        )
        query = urllib.parse.urlencode({"ref": ref})
        _, payload = self.request(
            "GET",
            f"/repos/{self.repository}/contents/{encoded_path}?{query}",
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
        message = f"Unable to load obsolete branch manifest {path}: {exc}"
        raise CleanupError(message) from exc
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


def _require_ref_sha(ref_sha: str, expected_sha: str, branch: str) -> None:
    if ref_sha != expected_sha:
        raise CleanupError(
            f"Branch {branch} points to {ref_sha}, expected immutable {expected_sha}"
        )


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
        number = pull.get("number")
        raise CleanupError(f"PR #{number} does not belong to branch {branch}")
    if not isinstance(base, dict) or base.get("ref") != default_branch:
        number = pull.get("number")
        raise CleanupError(f"PR #{number} does not target {default_branch}")
    if merged and not pull.get("merged_at"):
        raise CleanupError(f"PR #{pull.get('number')} is not merged")
    if not merged and pull.get("state") != "closed":
        raise CleanupError(f"PR #{pull.get('number')} is not closed")


def _preflight_entry(
    api: GitHubAPI,
    entry: dict[str, Any],
    *,
    default_branch: str,
    ref_sha: str,
    apply: bool,
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
        expected_sha = _expected_sha(entry)
        _require_ref_sha(ref_sha, expected_sha, branch)
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
        if _pull_head_sha(pull) != expected_sha:
            raise CleanupError(f"PR #{pull_number} head does not match manifest")
        return "VERIFIED", f"PR #{pull_number} merged at {pull['merged_at']}"

    if policy == "merge_candidate":
        pull_number = entry.get("pull_request")
        if not isinstance(pull_number, int):
            raise CleanupError(
                f"merge_candidate policy requires pull_request for {branch}"
            )
        pull = api.get_pull(pull_number)
        head = pull.get("head")
        base = pull.get("base")
        if not isinstance(head, dict) or head.get("ref") != branch:
            raise CleanupError(f"PR #{pull_number} does not belong to {branch}")
        if not isinstance(base, dict) or base.get("ref") != default_branch:
            raise CleanupError(f"PR #{pull_number} does not target {default_branch}")
        pull_head_sha = _pull_head_sha(pull)
        _require_ref_sha(ref_sha, pull_head_sha, branch)
        if pull.get("merged_at"):
            return "VERIFIED", f"PR #{pull_number} merged at {pull['merged_at']}"
        if apply:
            raise CleanupError(f"PR #{pull_number} is not merged")
        if pull.get("state") != "open":
            raise CleanupError(f"PR #{pull_number} is neither open nor merged")
        return "PENDING_MERGE", f"PR #{pull_number} is the current merge candidate"

    if policy == "superseded_pr":
        expected_sha = _expected_sha(entry)
        replacement_sha = _expected_sha(entry, "replacement_head_sha")
        _require_ref_sha(ref_sha, expected_sha, branch)
        closed_number = entry.get("closed_pull_request")
        replacement_number = entry.get("replacement_pull_request")
        if not isinstance(closed_number, int) or not isinstance(
            replacement_number, int
        ):
            raise CleanupError(
                f"superseded_pr policy requires two PR numbers for {branch}"
            )
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
        if _pull_head_sha(closed) != expected_sha:
            raise CleanupError(f"Closed PR #{closed_number} head does not match manifest")
        replacement_base = replacement.get("base")
        if not replacement.get("merged_at"):
            raise CleanupError(f"Replacement PR #{replacement_number} is not merged")
        if not isinstance(replacement_base, dict):
            raise CleanupError(f"Replacement PR #{replacement_number} has no base")
        if replacement_base.get("ref") != default_branch:
            raise CleanupError(
                f"Replacement PR #{replacement_number} does not target {default_branch}"
            )
        if _pull_head_sha(replacement) != replacement_sha:
            raise CleanupError(
                f"Replacement PR #{replacement_number} head does not match manifest"
            )
        detail = (
            f"PR #{closed_number} closed at {expected_sha}; replacement "
            f"PR #{replacement_number} merged from {replacement_sha}"
        )
        return "VERIFIED", detail

    if policy == "stale_dependency":
        expected_sha = _expected_sha(entry)
        _require_ref_sha(ref_sha, expected_sha, branch)
        open_pulls = api.open_pulls_for_branch(branch)
        if open_pulls:
            numbers = [pull.get("number") for pull in open_pulls]
            raise CleanupError(f"Stale dependency branch still has open PRs: {numbers}")
        comparison = api.compare(default_branch, expected_sha)
        files = comparison.get("files")
        if not isinstance(files, list):
            raise CleanupError(f"Dependency comparison returned no files for {branch}")
        actual_files = sorted(
            file.get("filename")
            for file in files
            if isinstance(file, dict) and file.get("filename")
        )
        expected_files = sorted(entry.get("expected_files", []))
        if actual_files != expected_files:
            message = (
                f"Stale dependency file set changed for {branch}: "
                f"{actual_files} != {expected_files}"
            )
            raise CleanupError(message)
        pyproject_text = api.read_text_file("pyproject.toml", expected_sha)
        try:
            pyproject = tomllib.loads(pyproject_text)
        except tomllib.TOMLDecodeError as exc:
            raise CleanupError("Stale dependency pyproject is malformed") from exc
        expected_version = entry.get("expected_version")
        actual_version = pyproject.get("project", {}).get("version")
        if actual_version != expected_version:
            raise CleanupError(
                f"Stale dependency version {actual_version} != {expected_version}"
            )
        scripts = pyproject.get("project", {}).get("scripts", {})
        if "job-app-helix-portfolio" in scripts:
            raise CleanupError(
                "Stale dependency branch unexpectedly contains the current portfolio CLI"
            )
        return (
            "VERIFIED",
            "No open PR; immutable patch is limited to pyproject.toml and uv.lock",
        )

    raise CleanupError(f"Unsupported cleanup policy {policy!r} for {branch}")


def _receipt(
    *,
    repository: str,
    default_branch: str,
    apply: bool,
    conclusion: str,
    results: list[BranchResult],
    failures: list[str],
) -> dict[str, Any]:
    return {
        "schema": "glaciereq.obsolete-branch-cleanup-receipt.v1",
        "repository": repository,
        "default_branch": default_branch,
        "mode": "APPLY" if apply else "DRY_RUN",
        "conclusion": conclusion,
        "results": [asdict(result) for result in results],
        "failures": failures,
    }


def _write_receipt(output: Path, payload: dict[str, Any]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _ref_sha(api: GitHubAPI, branch: str) -> str:
    status, ref = api.get_ref(branch)
    if status != 200 or not isinstance(ref, dict):
        raise CleanupError(f"Branch {branch} is absent or malformed")
    obj = ref.get("object")
    sha = obj.get("sha") if isinstance(obj, dict) else None
    if not isinstance(sha, str):
        raise CleanupError(f"Branch {branch} has no commit SHA")
    return sha


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
        message = f"Manifest repository {manifest.get('repository')} does not match {repository}"
        raise CleanupError(message)
    default_branch = manifest.get("default_branch")
    if not isinstance(default_branch, str) or not default_branch:
        raise CleanupError("Manifest default_branch is missing")

    api = GitHubAPI(repository, token)
    preflight_results: list[BranchResult] = []
    candidates: list[DeletionCandidate] = []
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
                preflight_results.append(
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
            ref_sha = _ref_sha(api, branch)
            preflight, detail = _preflight_entry(
                api,
                raw_entry,
                default_branch=default_branch,
                ref_sha=ref_sha,
                apply=apply,
            )
            candidates.append(
                DeletionCandidate(
                    branch=branch,
                    policy=policy,
                    reason=reason,
                    ref_sha=ref_sha,
                    preflight=preflight,
                    detail=detail,
                )
            )
            preflight_results.append(
                BranchResult(
                    branch=branch,
                    policy=policy,
                    reason=reason,
                    ref_sha=ref_sha,
                    preflight=preflight,
                    outcome="READY" if apply else "DRY_RUN",
                    detail=detail,
                )
            )
        except CleanupError as exc:
            failures.append(f"{branch}: {exc}")
            preflight_results.append(
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

    if failures:
        payload = _receipt(
            repository=repository,
            default_branch=default_branch,
            apply=apply,
            conclusion="FAILED_PREFLIGHT",
            results=preflight_results,
            failures=failures,
        )
        _write_receipt(output, payload)
        raise CleanupError("; ".join(failures))

    if not apply:
        payload = _receipt(
            repository=repository,
            default_branch=default_branch,
            apply=False,
            conclusion="VERIFIED",
            results=preflight_results,
            failures=[],
        )
        _write_receipt(output, payload)
        return preflight_results

    deleted: list[DeletionCandidate] = []
    attempted: list[DeletionCandidate] = []
    final_results: list[BranchResult] = [
        result for result in preflight_results if result.preflight == "ALREADY_ABSENT"
    ]
    deletion_failure: str | None = None
    for candidate in candidates:
        try:
            current_sha = _ref_sha(api, candidate.branch)
            if current_sha != candidate.ref_sha:
                raise CleanupError(
                    f"Branch changed after preflight: {candidate.ref_sha} -> {current_sha}"
                )
            api.delete_ref(candidate.branch)
            attempted.append(candidate)
            after_status, _ = api.get_ref(candidate.branch)
            if after_status != 404:
                raise CleanupError(
                    f"Branch {candidate.branch} still exists after delete"
                )
            deleted.append(candidate)
            final_results.append(
                BranchResult(
                    branch=candidate.branch,
                    policy=candidate.policy,
                    reason=candidate.reason,
                    ref_sha=candidate.ref_sha,
                    preflight=candidate.preflight,
                    outcome="DELETED",
                    detail=candidate.detail,
                )
            )
        except CleanupError as exc:
            deletion_failure = f"{candidate.branch}: {exc}"
            break

    if deletion_failure is None:
        payload = _receipt(
            repository=repository,
            default_branch=default_branch,
            apply=True,
            conclusion="VERIFIED",
            results=final_results,
            failures=[],
        )
        _write_receipt(output, payload)
        return final_results

    rollback_failures: list[str] = []
    rolled_back: set[str] = set()
    for candidate in reversed(attempted):
        try:
            api.create_ref(candidate.branch, candidate.ref_sha)
            restored_sha = _ref_sha(api, candidate.branch)
            if restored_sha != candidate.ref_sha:
                raise CleanupError(
                    f"Branch {candidate.branch} did not restore to {candidate.ref_sha}"
                )
            rolled_back.add(candidate.branch)
        except CleanupError as exc:
            rollback_failures.append(f"{candidate.branch}: {exc}")

    attempted_names = {candidate.branch for candidate in attempted}
    results_after_rollback: list[BranchResult] = []
    for result in preflight_results:
        if result.branch in rolled_back:
            outcome = "ROLLED_BACK"
            detail = "Deletion was reversed after a later failure"
        elif result.branch in attempted_names:
            outcome = "ROLLBACK_FAILED"
            detail = "Deletion was attempted and restoration was not verified"
        elif result.preflight == "ALREADY_ABSENT":
            outcome = "NO_ACTION"
            detail = result.detail
        else:
            outcome = "PRESERVED"
            detail = "Branch was not deleted because the transaction failed"
        results_after_rollback.append(
            BranchResult(
                branch=result.branch,
                policy=result.policy,
                reason=result.reason,
                ref_sha=result.ref_sha,
                preflight=result.preflight,
                outcome=outcome,
                detail=detail,
            )
        )

    all_failures = [deletion_failure, *rollback_failures]
    conclusion = "FAILED_ROLLED_BACK" if not rollback_failures else "FAILED_ROLLBACK"
    payload = _receipt(
        repository=repository,
        default_branch=default_branch,
        apply=True,
        conclusion=conclusion,
        results=results_after_rollback,
        failures=all_failures,
    )
    _write_receipt(output, payload)
    raise CleanupError("; ".join(all_failures))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify and remove explicitly obsolete branches"
    )
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
    print(
        "Branch cleanup verified: "
        f"deleted={deleted} dry_run={dry_run} already_absent={absent}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
