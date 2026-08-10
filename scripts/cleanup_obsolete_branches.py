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
import tomllib

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "manifests" / "obsolete_branches.json"
API_ROOT = "https://api.github.com"


class CleanupError(RuntimeError):
    pass


@dataclass(frozen=True)
class BranchCandidate:
    branch: str
    expected_sha: str
    reason: str


@dataclass(frozen=True)
class PreflightResult:
    branch: str
    expected_sha: str
    live_sha: str | None
    ref_sha: str | None
    cleanup_pr: int
    reason: str
    open_pull_requests: tuple[int, ...]
    dependency_pull_requests: tuple[int, ...]
    open_pr_heads: tuple[str, ...]
    dependency_heads: tuple[str, ...]
    cleanup_pr_closed: bool
    cleanup_pr_merged: bool
    default_branch: str
    allowed: bool
    blockers: tuple[str, ...]


@dataclass(frozen=True)
class DeleteResult:
    branch: str
    expected_sha: str
    observed_sha: str | None
    decision: str
    reason: str
    restore_attempted: bool = False
    restore_succeeded: bool | None = None
    restore_error: str | None = None


class GitHubClient:
    def __init__(self, token: str | None) -> None:
        self.token = token

    def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
    ) -> tuple[int, dict[str, Any] | list[Any] | None]:
        url = f"{API_ROOT}{path}"
        data = None
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "job-app-helix-obsolete-branch-cleanup",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request) as response:
                body = response.read()
                decoded = json.loads(body.decode("utf-8")) if body else None
                return response.status, decoded
        except urllib.error.HTTPError as exc:
            body = exc.read()
            try:
                decoded = json.loads(body.decode("utf-8")) if body else None
            except json.JSONDecodeError:
                decoded = None
            return exc.code, decoded

    def get_json(self, path: str) -> dict[str, Any] | list[Any]:
        status, data = self._request("GET", path)
        if status != 200 or not isinstance(data, dict | list):
            raise CleanupError(f"GET {path} failed with status {status}")
        return data

    def delete_ref(self, owner: str, repo: str, branch: str) -> None:
        encoded = urllib.parse.quote(branch, safe="")
        status, _ = self._request("DELETE", f"/repos/{owner}/{repo}/git/refs/heads/{encoded}")
        if status != 204:
            raise CleanupError(f"DELETE ref {branch} failed with status {status}")

    def create_ref(self, owner: str, repo: str, branch: str, sha: str) -> None:
        status, _ = self._request(
            "POST",
            f"/repos/{owner}/{repo}/git/refs",
            {"ref": f"refs/heads/{branch}", "sha": sha},
        )
        if status != 201:
            raise CleanupError(f"CREATE ref {branch} failed with status {status}")


def load_manifest(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        data = tomllib.load(handle)
    if not isinstance(data, dict):
        raise CleanupError("manifest must decode to an object")
    return data


def _repo_parts(manifest: dict[str, Any]) -> tuple[str, str]:
    repository = manifest.get("repository")
    if not isinstance(repository, str) or repository.count("/") != 1:
        raise CleanupError("manifest.repository must be owner/repo")
    return tuple(repository.split("/", 1))  # type: ignore[return-value]


def _candidate_from_row(row: dict[str, Any]) -> BranchCandidate:
    branch = row.get("branch")
    expected_sha = row.get("expected_sha")
    reason = row.get("reason")
    if not all(isinstance(value, str) and value for value in (branch, expected_sha, reason)):
        raise CleanupError("each candidate requires branch, expected_sha, and reason")
    return BranchCandidate(branch=branch, expected_sha=expected_sha, reason=reason)


def load_candidates(manifest: dict[str, Any]) -> list[BranchCandidate]:
    raw = manifest.get("branches")
    if not isinstance(raw, list):
        raise CleanupError("manifest.branches must be a list")
    return [_candidate_from_row(row) for row in raw if isinstance(row, dict)]


def _pr_numbers(items: list[dict[str, Any]]) -> tuple[int, ...]:
    values = sorted({int(item["number"]) for item in items if isinstance(item.get("number"), int)})
    return tuple(values)


def _pr_heads(items: list[dict[str, Any]]) -> tuple[str, ...]:
    values: set[str] = set()
    for item in items:
        head = item.get("head")
        if isinstance(head, dict) and isinstance(head.get("ref"), str):
            values.add(head["ref"])
    return tuple(sorted(values))


def _extract_live_sha(ref_payload: dict[str, Any]) -> str | None:
    obj = ref_payload.get("object")
    if not isinstance(obj, dict):
        return None
    sha = obj.get("sha")
    return sha if isinstance(sha, str) else None


def _extract_branch_sha(branch_payload: dict[str, Any]) -> str | None:
    commit = branch_payload.get("commit")
    if not isinstance(commit, dict):
        return None
    sha = commit.get("sha")
    return sha if isinstance(sha, str) else None


def _preflight_candidate(
    client: GitHubClient,
    owner: str,
    repo: str,
    candidate: BranchCandidate,
    cleanup_pr: int,
    default_branch: str,
    open_prs: list[dict[str, Any]],
    dependency_prs: list[dict[str, Any]],
) -> PreflightResult:
    encoded = urllib.parse.quote(candidate.branch, safe="")
    branch_payload = client.get_json(f"/repos/{owner}/{repo}/branches/{encoded}")
    ref_payload = client.get_json(f"/repos/{owner}/{repo}/git/ref/heads/{encoded}")
    if not isinstance(branch_payload, dict) or not isinstance(ref_payload, dict):
        raise CleanupError(f"unexpected branch payload for {candidate.branch}")
    live_sha = _extract_branch_sha(branch_payload)
    ref_sha = _extract_live_sha(ref_payload)

    blockers: list[str] = []
    if candidate.branch == default_branch:
        blockers.append("default_branch")
    if live_sha != candidate.expected_sha:
        blockers.append("branch_sha_mismatch")
    if ref_sha != candidate.expected_sha:
        blockers.append("ref_sha_mismatch")

    branch_open_prs = [
        item
        for item in open_prs
        if isinstance(item.get("head"), dict) and item["head"].get("ref") == candidate.branch
    ]
    branch_dependency_prs = [
        item
        for item in dependency_prs
        if isinstance(item.get("head"), dict) and item["head"].get("ref") == candidate.branch
    ]
    if branch_open_prs:
        blockers.append("open_pull_request")
    if branch_dependency_prs:
        blockers.append("open_dependency_pull_request")

    cleanup_payload = client.get_json(f"/repos/{owner}/{repo}/pulls/{cleanup_pr}")
    if not isinstance(cleanup_payload, dict):
        raise CleanupError("cleanup PR payload must be an object")
    cleanup_pr_closed = cleanup_payload.get("state") == "closed"
    cleanup_pr_merged = bool(cleanup_payload.get("merged"))
    if not cleanup_pr_closed:
        blockers.append("cleanup_pr_open")
    if not cleanup_pr_merged:
        blockers.append("cleanup_pr_not_merged")

    return PreflightResult(
        branch=candidate.branch,
        expected_sha=candidate.expected_sha,
        live_sha=live_sha,
        ref_sha=ref_sha,
        cleanup_pr=cleanup_pr,
        reason=candidate.reason,
        open_pull_requests=_pr_numbers(branch_open_prs),
        dependency_pull_requests=_pr_numbers(branch_dependency_prs),
        open_pr_heads=_pr_heads(branch_open_prs),
        dependency_heads=_pr_heads(branch_dependency_prs),
        cleanup_pr_closed=cleanup_pr_closed,
        cleanup_pr_merged=cleanup_pr_merged,
        default_branch=default_branch,
        allowed=not blockers,
        blockers=tuple(blockers),
    )


def preflight_manifest(
    client: GitHubClient,
    manifest: dict[str, Any],
    candidates: list[BranchCandidate],
) -> list[PreflightResult]:
    owner, repo = _repo_parts(manifest)
    cleanup_pr = manifest.get("cleanup_pr")
    if not isinstance(cleanup_pr, int):
        raise CleanupError("manifest.cleanup_pr must be an integer")

    repo_payload = client.get_json(f"/repos/{owner}/{repo}")
    if not isinstance(repo_payload, dict) or not isinstance(repo_payload.get("default_branch"), str):
        raise CleanupError("repository default_branch missing")
    default_branch = repo_payload["default_branch"]

    open_prs_raw = client.get_json(f"/repos/{owner}/{repo}/pulls?state=open&per_page=100")
    if not isinstance(open_prs_raw, list):
        raise CleanupError("open pull request list malformed")
    open_prs = [item for item in open_prs_raw if isinstance(item, dict)]

    dependency_prs_raw = client.get_json(
        f"/repos/{owner}/{repo}/pulls?state=open&per_page=100&base={urllib.parse.quote(default_branch)}"
    )
    if not isinstance(dependency_prs_raw, list):
        raise CleanupError("dependency pull request list malformed")
    dependency_prs = [item for item in dependency_prs_raw if isinstance(item, dict)]

    return [
        _preflight_candidate(
            client,
            owner,
            repo,
            candidate,
            cleanup_pr,
            default_branch,
            open_prs,
            dependency_prs,
        )
        for candidate in candidates
    ]


def _delete_candidate(
    client: GitHubClient,
    owner: str,
    repo: str,
    result: PreflightResult,
) -> DeleteResult:
    if not result.allowed:
        return DeleteResult(
            branch=result.branch,
            expected_sha=result.expected_sha,
            observed_sha=result.live_sha,
            decision="SKIPPED_PREFLIGHT",
            reason=",".join(result.blockers),
        )

    encoded = urllib.parse.quote(result.branch, safe="")
    branch_payload = client.get_json(f"/repos/{owner}/{repo}/branches/{encoded}")
    if not isinstance(branch_payload, dict):
        raise CleanupError(f"branch payload malformed for {result.branch}")
    current_sha = _extract_branch_sha(branch_payload)
    if current_sha != result.expected_sha:
        return DeleteResult(
            branch=result.branch,
            expected_sha=result.expected_sha,
            observed_sha=current_sha,
            decision="SKIPPED_CHANGED_REF",
            reason="branch_sha_changed_after_preflight",
        )

    client.delete_ref(owner, repo, result.branch)
    status, data = client._request("GET", f"/repos/{owner}/{repo}/branches/{encoded}")
    if status == 404:
        return DeleteResult(
            branch=result.branch,
            expected_sha=result.expected_sha,
            observed_sha=current_sha,
            decision="DELETED",
            reason="deleted_and_verified_absent",
        )

    restore_attempted = True
    restore_succeeded: bool | None = None
    restore_error: str | None = None
    try:
        client.create_ref(owner, repo, result.branch, result.expected_sha)
        restore_succeeded = True
    except CleanupError as exc:
        restore_succeeded = False
        restore_error = str(exc)

    return DeleteResult(
        branch=result.branch,
        expected_sha=result.expected_sha,
        observed_sha=current_sha,
        decision="DELETE_VERIFY_FAILED",
        reason=f"post_delete_status={status};body={data!r}",
        restore_attempted=restore_attempted,
        restore_succeeded=restore_succeeded,
        restore_error=restore_error,
    )


def apply_manifest(
    client: GitHubClient,
    manifest: dict[str, Any],
    candidates: list[BranchCandidate],
    preflights: list[PreflightResult],
) -> list[DeleteResult]:
    owner, repo = _repo_parts(manifest)
    if any(not item.allowed for item in preflights):
        return [
            DeleteResult(
                branch=item.branch,
                expected_sha=item.expected_sha,
                observed_sha=item.live_sha,
                decision="SKIPPED_BATCH_PREFLIGHT",
                reason=",".join(item.blockers),
            )
            for item in preflights
        ]

    results: list[DeleteResult] = []
    for item in preflights:
        results.append(_delete_candidate(client, owner, repo, item))
    return results


def _b64_sha256(payload: bytes) -> str:
    return hashlib.sha256(base64.b64decode(payload)).hexdigest()


def build_receipt(
    manifest_path: Path,
    manifest: dict[str, Any],
    preflights: list[PreflightResult],
    deletes: list[DeleteResult] | None,
    *,
    mode: str,
) -> dict[str, Any]:
    owner, repo = _repo_parts(manifest)
    body: dict[str, Any] = {
        "schema": "glaciereq.obsolete-branch-cleanup-receipt.v1",
        "repository": f"{owner}/{repo}",
        "mode": mode,
        "manifest": str(manifest_path),
        "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "cleanup_pr": manifest.get("cleanup_pr"),
        "preflight": [asdict(item) for item in preflights],
        "result": "PASS" if all(item.allowed for item in preflights) else "BLOCKED",
    }
    if deletes is not None:
        body["deletes"] = [asdict(item) for item in deletes]
        body["result"] = (
            "PASS"
            if all(item.decision == "DELETED" for item in deletes)
            else "PARTIAL_OR_BLOCKED"
        )
    return body


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--output", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    manifest = load_manifest(args.manifest)
    candidates = load_candidates(manifest)
    token = os.environ.get("GITHUB_TOKEN")
    client = GitHubClient(token)
    preflights = preflight_manifest(client, manifest, candidates)
    deletes = apply_manifest(client, manifest, candidates, preflights) if args.apply else None
    receipt = build_receipt(
        args.manifest,
        manifest,
        preflights,
        deletes,
        mode="apply" if args.apply else "dry-run",
    )
    rendered = json.dumps(receipt, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)
    return 0 if receipt["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
