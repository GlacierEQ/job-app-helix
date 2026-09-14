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
    """Read-only provider adapter used for historical lineage classification."""

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
                "Holographic mesh hard lock: this adapter is read-only and may not mutate refs"
            )
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "job-app-helix-branch-lineage-auditor",
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

    def get_pull(self, number: int) -> dict[str, Any]:
        _, payload = self.request("GET", f"/repos/{self.repository}/pulls/{number}")
        if not isinstance(payload, dict):
            raise CleanupError(f"PR #{number} returned no object")
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
        raise CleanupError(f"PR #{pull.get('number')} does not belong to {branch}")
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
    ref_sha: str,
) -> tuple[str, str]:
    """Verify historical overlap evidence without inferring donor exhaustion."""

    branch = entry.get("name")
    policy = entry.get("policy")
    if not isinstance(branch, str) or not branch:
        raise CleanupError(f"Invalid branch entry: {entry}")
    if branch == default_branch:
        raise CleanupError("Default branch may never appear in the historical audit manifest")
    if not isinstance(policy, str):
        raise CleanupError(f"Missing historical policy for {branch}")

    if policy == "merged_pr":
        expected_sha = _expected_sha(entry)
        _require_ref_sha(ref_sha, expected_sha, branch)
        pull_number = entry.get("pull_request")
        if not isinstance(pull_number, int):
            raise CleanupError(f"merged_pr requires pull_request for {branch}")
        pull = api.get_pull(pull_number)
        _validate_pull_branch(
            pull,
            branch=branch,
            default_branch=default_branch,
            merged=True,
        )
        if _pull_head_sha(pull) != expected_sha:
            raise CleanupError(f"PR #{pull_number} head does not match manifest")
        return (
            "VERIFIED_OVERLAP",
            f"PR #{pull_number} merged at {pull['merged_at']}; merge status is not donor-exhaustion proof",
        )

    if policy == "merge_candidate":
        pull_number = entry.get("pull_request")
        if not isinstance(pull_number, int):
            raise CleanupError(f"merge_candidate requires pull_request for {branch}")
        pull = api.get_pull(pull_number)
        head = pull.get("head")
        base = pull.get("base")
        if not isinstance(head, dict) or head.get("ref") != branch:
            raise CleanupError(f"PR #{pull_number} does not belong to {branch}")
        if not isinstance(base, dict) or base.get("ref") != default_branch:
            raise CleanupError(f"PR #{pull_number} does not target {default_branch}")
        _require_ref_sha(ref_sha, _pull_head_sha(pull), branch)
        if pull.get("merged_at"):
            return (
                "VERIFIED_OVERLAP",
                f"PR #{pull_number} merged at {pull['merged_at']}; branch remains lineage-bearing",
            )
        if pull.get("state") != "open":
            raise CleanupError(f"PR #{pull_number} is neither open nor merged")
        return "PENDING_MERGE", f"PR #{pull_number} is an open merge candidate"

    if policy == "superseded_pr":
        expected_sha = _expected_sha(entry)
        replacement_sha = _expected_sha(entry, "replacement_head_sha")
        _require_ref_sha(ref_sha, expected_sha, branch)
        closed_number = entry.get("closed_pull_request")
        replacement_number = entry.get("replacement_pull_request")
        if not isinstance(closed_number, int) or not isinstance(replacement_number, int):
            raise CleanupError(f"superseded_pr requires two PR numbers for {branch}")
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
        if not isinstance(replacement_base, dict) or replacement_base.get("ref") != default_branch:
            raise CleanupError(f"Replacement PR #{replacement_number} does not target {default_branch}")
        if _pull_head_sha(replacement) != replacement_sha:
            raise CleanupError(f"Replacement PR #{replacement_number} head does not match manifest")
        return (
            "VERIFIED_OVERLAP",
            f"PR #{closed_number} closed and replacement PR #{replacement_number} merged; replacement is partial-overlap evidence only",
        )

    if policy == "stale_dependency":
        expected_sha = _expected_sha(entry)
        _require_ref_sha(ref_sha, expected_sha, branch)
        open_pulls = api.open_pulls_for_branch(branch)
        if open_pulls:
            numbers = [pull.get("number") for pull in open_pulls]
            raise CleanupError(f"Historical dependency branch still has open PRs: {numbers}")
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
            raise CleanupError(
                f"Historical dependency file set changed for {branch}: {actual_files} != {expected_files}"
            )
        pyproject_text = api.read_text_file("pyproject.toml", expected_sha)
        try:
            pyproject = tomllib.loads(pyproject_text)
        except tomllib.TOMLDecodeError as exc:
            raise CleanupError("Historical dependency pyproject is malformed") from exc
        expected_version = entry.get("expected_version")
        actual_version = pyproject.get("project", {}).get("version")
        if actual_version != expected_version:
            raise CleanupError(
                f"Historical dependency version {actual_version} != {expected_version}"
            )
        return (
            "VERIFIED_OVERLAP",
            "Historical patch shape verified; staleness/file equivalence is not donor-exhaustion proof",
        )

    raise CleanupError(f"Unsupported historical policy {policy!r} for {branch}")


def _receipt(
    *,
    repository: str,
    default_branch: str,
    conclusion: str,
    results: list[BranchResult],
    failures: list[str],
) -> dict[str, Any]:
    return {
        "schema": "glaciereq.branch-lineage-audit-receipt.v2",
        "repository": repository,
        "default_branch": default_branch,
        "mode": "READ_ONLY_LINEAGE_AUDIT",
        "anti_replacement": {
            "latest_is_routing_cursor_only": True,
            "overlap_is_not_zero_unique_contribution": True,
            "remote_ref_deletion_authority": False,
            "drained_terminal_state": "PRESERVE_DRAINED_LINEAGE",
        },
        "conclusion": conclusion,
        "results": [asdict(result) for result in results],
        "failures": failures,
    }


def _ref_sha(payload: dict[str, Any] | None) -> str | None:
    if not isinstance(payload, dict):
        return None
    obj = payload.get("object")
    if not isinstance(obj, dict):
        return None
    sha = obj.get("sha")
    return sha if isinstance(sha, str) else None


def audit(
    manifest_path: Path,
    *,
    repository: str | None,
    token: str | None,
    output: Path | None,
) -> list[BranchResult]:
    manifest = _load_manifest(manifest_path)
    repo = repository or manifest.get("repository")
    default_branch = manifest.get("default_branch")
    if not isinstance(repo, str) or not repo:
        raise CleanupError("Repository must be provided by argument or manifest")
    if not isinstance(default_branch, str) or not default_branch:
        raise CleanupError("Manifest requires default_branch")

    api = GitHubAPI(repo, token)
    results: list[BranchResult] = []
    failures: list[str] = []

    for raw_entry in manifest["branches"]:
        if not isinstance(raw_entry, dict):
            failures.append(f"Invalid branch entry: {raw_entry!r}")
            continue
        branch = raw_entry.get("name")
        policy = raw_entry.get("policy")
        reason = raw_entry.get("reason", "")
        if not isinstance(branch, str) or not isinstance(policy, str):
            failures.append(f"Invalid branch entry: {raw_entry!r}")
            continue

        status, ref_payload = api.get_ref(branch)
        if status == 404:
            results.append(
                BranchResult(
                    branch=branch,
                    policy=policy,
                    reason=str(reason),
                    ref_sha=None,
                    preflight="REF_ABSENT",
                    outcome="PRESERVE_HISTORICAL_LINEAGE_POINTER",
                    detail=(
                        "Remote ref is absent at readback. Absence is recorded as historical state; "
                        "it does not prove prior retirement was semantically valid."
                    ),
                )
            )
            continue

        ref_sha = _ref_sha(ref_payload)
        if ref_sha is None:
            failures.append(f"Branch {branch} returned no SHA")
            continue

        try:
            preflight, detail = _preflight_entry(
                api,
                raw_entry,
                default_branch=default_branch,
                ref_sha=ref_sha,
            )
        except CleanupError as exc:
            failures.append(f"{branch}: {exc}")
            results.append(
                BranchResult(
                    branch=branch,
                    policy=policy,
                    reason=str(reason),
                    ref_sha=ref_sha,
                    preflight="FAILED",
                    outcome="ACTIVE_IN_MESH",
                    detail=f"Historical classification could not be verified: {exc}",
                )
            )
            continue

        results.append(
            BranchResult(
                branch=branch,
                policy=policy,
                reason=str(reason),
                ref_sha=ref_sha,
                preflight=preflight,
                outcome="ACTIVE_IN_MESH",
                detail=(
                    f"{detail}. No whole-donor UNIQUE_CONTRIBUTION=0 proof is established; "
                    "the ref remains preserved."
                ),
            )
        )

    conclusion = "VERIFIED_READ_ONLY" if not failures else "READ_ONLY_WITH_FINDINGS"
    payload = _receipt(
        repository=repo,
        default_branch=default_branch,
        conclusion=conclusion,
        results=results,
        failures=failures,
    )
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return results


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only historical branch-lineage audit. This command cannot delete, restore, "
            "archive, close, merge, or otherwise mutate branch refs."
        )
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--repository")
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    token = os.environ.get("GITHUB_TOKEN")
    try:
        audit(
            args.manifest,
            repository=args.repository,
            token=token,
            output=args.output,
        )
    except CleanupError as exc:
        raise SystemExit(str(exc)) from exc
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
