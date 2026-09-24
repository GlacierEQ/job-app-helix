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
DEFAULT_OUTPUT = ROOT / "artifacts" / "obsolete-branch-cleanup.json"
API_ROOT = "https://api.github.com"
PRESERVATION_BUCKETS = (
    "blocked_refs",
    "restored_refs_after_failed_transaction",
    "preserved_active_refs",
    "retired_refs",
)


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
    """Read-only provider adapter for historical branch-lineage inspection."""

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
                "Read-only lineage audit: provider mutation methods are prohibited"
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
            raise CleanupError(f"PR #{number} returned no object")
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
            f"Branch {branch} points to {ref_sha}, expected historical {expected_sha}"
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


def _normalize_entry(raw: dict[str, Any], bucket: str) -> dict[str, Any]:
    entry = dict(raw)
    if bucket != "branches":
        entry["policy"] = f"manifest_{bucket.removesuffix('_refs')}"
        entry["reason"] = (
            entry.get("reason") or entry.get("blocker") or entry.get("state") or bucket
        )
    return entry


def _audit_entries(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    by_name: dict[str, int] = {}

    def add_bucket(bucket: str) -> None:
        raw_entries = manifest.get(bucket, [])
        if not isinstance(raw_entries, list):
            raise CleanupError(f"Manifest field {bucket} must be a list")
        for raw in raw_entries:
            if not isinstance(raw, dict):
                raise CleanupError(f"Manifest field {bucket} contains a non-object entry")
            name = raw.get("name")
            if not isinstance(name, str) or not name:
                raise CleanupError(f"Manifest field {bucket} contains an entry without a name")
            entry = _normalize_entry(raw, bucket)
            if name in by_name:
                existing = entries[by_name[name]]
                old_sha = existing.get("expected_head_sha")
                new_sha = entry.get("expected_head_sha")
                if isinstance(old_sha, str) and isinstance(new_sha, str) and old_sha != new_sha:
                    raise CleanupError(
                        f"Manifest carries conflicting expected SHAs for {name}: {old_sha} != {new_sha}"
                    )
                if "expected_head_sha" not in existing and "expected_head_sha" in entry:
                    existing["expected_head_sha"] = entry["expected_head_sha"]
                if not existing.get("reason") and entry.get("reason"):
                    existing["reason"] = entry["reason"]
                continue
            by_name[name] = len(entries)
            entries.append(entry)

    for bucket in (
        "preserved_active_refs",
        "restored_refs_after_failed_transaction",
        "blocked_refs",
        "branches",
        "retired_refs",
    ):
        add_bucket(bucket)
    if not entries:
        raise CleanupError("Historical branch manifest declares no auditable lineage entries")
    return entries


def _preflight_entry(
    api: GitHubAPI,
    entry: dict[str, Any],
    *,
    default_branch: str,
    ref_sha: str,
) -> tuple[str, str]:
    """Verify overlap/history only; never infer donor exhaustion."""
    branch = entry.get("name")
    policy = entry.get("policy")
    if not isinstance(branch, str) or not branch:
        raise CleanupError(f"Invalid branch entry: {entry}")
    if branch == default_branch:
        raise CleanupError("Default branch may never appear in the historical audit manifest")
    if not isinstance(policy, str):
        raise CleanupError(f"Missing historical policy for {branch}")

    if policy.startswith("manifest_"):
        expected = entry.get("expected_head_sha")
        if expected is not None:
            _require_ref_sha(ref_sha, _expected_sha(entry), branch)
            return "LIVE_LINEAGE_CONFIRMED", f"Current ref matches lineage SHA {expected}"
        return (
            "LIVE_LINEAGE_OBSERVED_UNPINNED",
            f"Current ref observed at {ref_sha}; manifest carries no immutable expected SHA",
        )

    if policy == "merged_pr":
        expected_sha = _expected_sha(entry)
        _require_ref_sha(ref_sha, expected_sha, branch)
        pull_number = entry.get("pull_request")
        if not isinstance(pull_number, int):
            raise CleanupError(f"merged_pr requires pull_request for {branch}")
        pull = api.get_pull(pull_number)
        _validate_pull_branch(
            pull, branch=branch, default_branch=default_branch, merged=True
        )
        if _pull_head_sha(pull) != expected_sha:
            raise CleanupError(f"PR #{pull_number} head does not match manifest")
        return "VERIFIED_OVERLAP", f"PR #{pull_number} merged; merge state is overlap evidence"

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
            return "VERIFIED_OVERLAP", f"PR #{pull_number} merged; branch remains lineage-bearing"
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
            closed, branch=branch, default_branch=default_branch, merged=False
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
            f"PR #{closed_number} closed and replacement PR #{replacement_number} merged",
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
            if isinstance(file, dict) and isinstance(file.get("filename"), str)
        )
        expected_files = entry.get("expected_files")
        if not isinstance(expected_files, list) or not all(isinstance(item, str) for item in expected_files):
            raise CleanupError(f"Historical dependency {branch} has malformed expected_files")
        if actual_files != sorted(expected_files):
            raise CleanupError(
                f"Historical dependency file set changed for {branch}: {actual_files} != {sorted(expected_files)}"
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
        scripts = pyproject.get("project", {}).get("scripts", {})
        if isinstance(scripts, dict) and "job-app-helix-portfolio" in scripts:
            raise CleanupError(
                "Historical dependency branch unexpectedly contains the current portfolio CLI"
            )
        return (
            "VERIFIED_OVERLAP",
            "Historical patch shape verified; staleness/file equivalence is overlap evidence only",
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
            "unique_contribution_zero_proven": False,
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


def _write_receipt(output: Path | None, payload: dict[str, Any]) -> None:
    if output is None:
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def audit(
    manifest_path: Path,
    *,
    repository: str | None,
    token: str | None,
    output: Path | None,
) -> list[BranchResult]:
    manifest = _load_manifest(manifest_path)
    manifest_repository = manifest.get("repository")
    default_branch = manifest.get("default_branch")
    if not isinstance(manifest_repository, str) or not manifest_repository:
        raise CleanupError("Manifest requires repository")
    if repository is not None and repository != manifest_repository:
        raise CleanupError(
            f"Manifest repository {manifest_repository} does not match {repository}"
        )
    if not isinstance(default_branch, str) or not default_branch:
        raise CleanupError("Manifest requires default_branch")

    entries = _audit_entries(manifest)
    api = GitHubAPI(manifest_repository, token)
    results: list[BranchResult] = []
    failures: list[str] = []

    for raw_entry in entries:
        branch = raw_entry["name"]
        policy = raw_entry["policy"]
        reason = str(raw_entry.get("reason", ""))
        try:
            status, ref_payload = api.get_ref(branch)
        except CleanupError as exc:
            failures.append(f"{branch}: provider ref read failed: {exc}")
            results.append(
                BranchResult(
                    branch=branch,
                    policy=policy,
                    reason=reason,
                    ref_sha=None,
                    preflight="READBACK_UNRESOLVED",
                    outcome="ACTIVE_IN_MESH",
                    detail=f"Provider ref read failed; no absence inference permitted: {exc}",
                )
            )
            continue

        if status == 404:
            expected_live = policy in {
                "manifest_preserved_active",
                "manifest_restored_refs_after_failed_transaction",
                "manifest_blocked",
            }
            if expected_live:
                failures.append(f"{branch}: expected preserved ref is absent")
            results.append(
                BranchResult(
                    branch=branch,
                    policy=policy,
                    reason=reason,
                    ref_sha=None,
                    preflight="REF_ABSENT",
                    outcome="PRESERVE_HISTORICAL_LINEAGE_POINTER",
                    detail=(
                        "Remote ref is absent at provider readback. Historical lineage is preserved; "
                        "absence does not validate prior retirement."
                    ),
                )
            )
            continue

        ref_sha = _ref_sha(ref_payload)
        if ref_sha is None:
            failures.append(f"{branch}: branch returned no SHA")
            results.append(
                BranchResult(
                    branch=branch,
                    policy=policy,
                    reason=reason,
                    ref_sha=None,
                    preflight="FAILED",
                    outcome="ACTIVE_IN_MESH",
                    detail="Historical classification could not be verified: branch returned no SHA",
                )
            )
            continue

        try:
            preflight, detail = _preflight_entry(
                api, raw_entry, default_branch=default_branch, ref_sha=ref_sha
            )
        except (CleanupError, TypeError, ValueError) as exc:
            failures.append(f"{branch}: {exc}")
            results.append(
                BranchResult(
                    branch=branch,
                    policy=policy,
                    reason=reason,
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
                reason=reason,
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
        repository=manifest_repository,
        default_branch=default_branch,
        conclusion=conclusion,
        results=results,
        failures=failures,
    )
    _write_receipt(output, payload)
    if failures:
        raise CleanupError(
            f"Lineage audit completed with {len(failures)} finding(s); receipt was preserved"
        )
    return results


def cleanup(
    manifest_path: Path,
    *,
    repository: str | None,
    token: str | None,
    apply: bool = False,
    output: Path | None,
) -> list[BranchResult]:
    """Compatibility entrypoint; destructive apply semantics are permanently retired."""
    if apply:
        raise CleanupError(
            "Legacy apply mode is retired: branch/ref deletion is forbidden; use read-only lineage audit"
        )
    return audit(
        manifest_path,
        repository=repository,
        token=token,
        output=output,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read-only historical branch-lineage audit; remote refs are preserved"
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--repository", default=os.environ.get("GITHUB_REPOSITORY"))
    parser.add_argument("--token", default=os.environ.get("GITHUB_TOKEN"))
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    token = args.token or os.environ.get("GITHUB_TOKEN")
    try:
        audit(
            args.manifest.resolve(),
            repository=args.repository,
            token=token,
            output=args.output.resolve(),
        )
    except CleanupError as exc:
        print(f"Branch lineage audit unresolved: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
