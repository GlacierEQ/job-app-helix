from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Iterable, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .readme_estate import (
    ClassificationEvidence,
    EstateReadmeError,
    ReadmeAction,
    parse_machine_contract,
    plan_readme,
)

API = "https://api.github.com"
DEFAULT_ORG = "GlacierEQ"
DEFAULT_MONOLITH = "GlacierEQ/monolith"


class GitHubApiError(RuntimeError):
    pass


class GitHubApi:
    def __init__(self, token: str, *, timeout: float = 30.0) -> None:
        if not token:
            raise GitHubApiError("GitHub token is required")
        self.token = token
        self.timeout = timeout

    def request(
        self,
        method: str,
        url: str,
        payload: dict[str, Any] | None = None,
        *,
        attempts: int = 4,
    ) -> tuple[Any, MappingHeaders]:
        body = None
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self.token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "glaciereq-job-app-helix-readme-estate",
        }
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        for attempt in range(attempts):
            request = urllib.request.Request(url, data=body, headers=headers, method=method)
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    raw = response.read()
                    data = json.loads(raw.decode("utf-8")) if raw else None
                    return data, MappingHeaders(dict(response.headers.items()))
            except urllib.error.HTTPError as exc:
                raw = exc.read().decode("utf-8", errors="replace")
                if exc.code in {403, 429, 502, 503, 504} and attempt + 1 < attempts:
                    retry_after = exc.headers.get("Retry-After")
                    delay = float(retry_after) if retry_after else min(2**attempt, 8)
                    time.sleep(delay)
                    continue
                raise GitHubApiError(f"{method} {url} -> {exc.code}: {raw[:500]}") from exc
            except urllib.error.URLError as exc:
                if attempt + 1 < attempts:
                    time.sleep(min(2**attempt, 8))
                    continue
                raise GitHubApiError(f"{method} {url}: {exc}") from exc
        raise GitHubApiError(f"request attempts exhausted: {method} {url}")

    def get(self, url: str) -> Any:
        return self.request("GET", url)[0]

    def list_org_repositories(self, org: str) -> list[dict[str, Any]]:
        repositories: list[dict[str, Any]] = []
        page = 1
        while True:
            query = urllib.parse.urlencode(
                {"type": "all", "per_page": 100, "page": page, "sort": "full_name"}
            )
            rows = self.get(f"{API}/orgs/{org}/repos?{query}")
            if not isinstance(rows, list):
                raise GitHubApiError("organization repository response is not a list")
            repositories.extend(row for row in rows if isinstance(row, dict))
            if len(rows) < 100:
                break
            page += 1
        return repositories

    def contents(self, repository: str, path: str = "") -> Any:
        encoded_path = "/".join(urllib.parse.quote(part, safe="") for part in path.split("/"))
        suffix = f"/contents/{encoded_path}" if encoded_path else "/contents"
        return self.get(f"{API}/repos/{repository}{suffix}")

    def optional_contents(self, repository: str, path: str) -> Any | None:
        try:
            return self.contents(repository, path)
        except GitHubApiError as exc:
            if "-> 404:" in str(exc):
                return None
            raise

    @staticmethod
    def decode_content(record: dict[str, Any]) -> str:
        encoded = record.get("content")
        if not isinstance(encoded, str):
            raise GitHubApiError("contents record does not contain inline base64 content")
        return base64.b64decode(encoded).decode("utf-8")

    def put_readme(
        self,
        repository: str,
        *,
        content: str,
        branch: str,
        current_sha: str | None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "message": "docs: add GlacierEQ estate machine README contract",
            "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
            "branch": branch,
        }
        if current_sha:
            payload["sha"] = current_sha
        result, _ = self.request(
            "PUT",
            f"{API}/repos/{repository}/contents/README.md",
            payload,
        )
        if not isinstance(result, dict):
            raise GitHubApiError("README write returned non-object result")
        return result


class MappingHeaders(dict[str, str]):
    pass


def _load_jsonl(text: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            row = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise GitHubApiError(f"invalid Monolith ledger JSONL line {line_no}: {exc}") from exc
        if isinstance(row, dict):
            records.append(row)
    return records


def load_monolith_classifications(
    api: GitHubApi,
    monolith: str,
    *,
    workers: int,
) -> dict[str, ClassificationEvidence]:
    paths = ["catalog/RECLASSIFICATION_LEDGER.jsonl"]
    directory = api.contents(monolith, "catalog/reclassification-ledger")
    if isinstance(directory, list):
        paths.extend(
            str(item["path"])
            for item in directory
            if isinstance(item, dict)
            and item.get("type") == "file"
            and str(item.get("name", "")).endswith(".jsonl")
        )
    paths = sorted(set(paths), key=str.casefold)

    def fetch(path: str) -> tuple[str, str]:
        record = api.contents(monolith, path)
        if not isinstance(record, dict):
            raise GitHubApiError(f"ledger path is not a file: {path}")
        return path, api.decode_content(record)

    texts: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        futures = {executor.submit(fetch, path): path for path in paths}
        for future in as_completed(futures):
            path, text = future.result()
            texts[path] = text

    result: dict[str, ClassificationEvidence] = {}
    for path in paths:
        for row in _load_jsonl(texts[path]):
            repository = row.get("repository")
            if not isinstance(repository, str) or not repository:
                continue
            if repository in result:
                raise GitHubApiError(f"duplicate logical Monolith ledger identity: {repository}")
            evidence = row.get("evidence") if isinstance(row.get("evidence"), dict) else {}
            result[repository] = ClassificationEvidence(
                primary_home=(
                    str(row["new_primary_path"])
                    if isinstance(row.get("new_primary_path"), str)
                    else None
                ),
                evidence_path=(
                    str(evidence["path"]) if isinstance(evidence.get("path"), str) else None
                ),
                evidence_blob_sha=(
                    str(evidence["blob_sha"])
                    if isinstance(evidence.get("blob_sha"), str)
                    else None
                ),
                status=str(row["status"]) if isinstance(row.get("status"), str) else None,
            )
    return result


def _root_paths(api: GitHubApi, repository: str) -> list[str]:
    root = api.contents(repository)
    if not isinstance(root, list):
        return []
    return sorted(
        str(item["name"])
        for item in root
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    )


def _inspect_repository(
    api: GitHubApi,
    repo: dict[str, Any],
    classifications: dict[str, ClassificationEvidence],
) -> tuple[dict[str, Any], str | None, str | None, list[str]]:
    full_name = str(repo["full_name"])
    readme_record = api.optional_contents(full_name, "README.md")
    readme = None
    readme_sha = None
    if isinstance(readme_record, dict):
        readme = api.decode_content(readme_record)
        readme_sha = str(readme_record.get("sha") or "") or None
    root_paths = _root_paths(api, full_name)
    return repo, readme, readme_sha, root_paths


def _receipt_row(
    *,
    repository: str,
    action: ReadmeAction,
    reason: str,
    mode: str,
    commit_sha: str | None = None,
    readback_blob_sha: str | None = None,
    verified: bool = False,
) -> dict[str, Any]:
    return {
        "repository": repository,
        "action": action.value,
        "reason": reason,
        "mode": mode,
        "commit_sha": commit_sha,
        "readback_blob_sha": readback_blob_sha,
        "verified": verified,
    }


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="job-app-helix-readme-estate",
        description="Plan or execute the universal GlacierEQ README machine-contract rollout.",
    )
    parser.add_argument("--org", default=DEFAULT_ORG)
    parser.add_argument("--monolith", default=DEFAULT_MONOLITH)
    parser.add_argument("--token-env", default="GITHUB_TOKEN")
    parser.add_argument("--workers", type=int, default=16)
    parser.add_argument("--repo", action="append", default=[])
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--limit", type=int, help="Debug/testing limit; never a completion boundary")
    parser.add_argument(
        "--receipt",
        type=Path,
        default=Path("artifacts/readme-estate/rollout.jsonl"),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    token = os.environ.get(args.token_env, "")
    if not token:
        print(f"missing token environment variable: {args.token_env}", file=sys.stderr)
        return 2
    api = GitHubApi(token)
    classifications = load_monolith_classifications(
        api,
        args.monolith,
        workers=args.workers,
    )
    repos = api.list_org_repositories(args.org)
    if args.repo:
        wanted = set(args.repo)
        repos = [repo for repo in repos if repo.get("full_name") in wanted]
        missing = sorted(wanted - {str(repo.get("full_name")) for repo in repos})
        if missing:
            print("requested repositories not found: " + ", ".join(missing), file=sys.stderr)
            return 2
    if args.limit is not None:
        repos = repos[: max(0, args.limit)]

    inspections: list[tuple[dict[str, Any], str | None, str | None, list[str]]] = []
    errors: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
        futures = {
            executor.submit(_inspect_repository, api, repo, classifications): repo
            for repo in repos
        }
        for future in as_completed(futures):
            repo = futures[future]
            try:
                inspections.append(future.result())
            except Exception as exc:  # noqa: BLE001 - provider failures become durable rows
                errors.append(
                    {
                        "repository": str(repo.get("full_name")),
                        "action": "INSPECTION_FAILED",
                        "reason": str(exc),
                        "mode": "write" if args.write else "plan",
                        "verified": False,
                    }
                )

    rows: list[dict[str, Any]] = list(errors)
    counts: dict[str, int] = {}
    for repo, readme, readme_sha, root_paths in sorted(
        inspections,
        key=lambda item: str(item[0].get("full_name", "")).casefold(),
    ):
        repository = str(repo["full_name"])
        default_branch = str(repo.get("default_branch") or "main")
        archived = bool(repo.get("archived", False))
        fork = bool(repo.get("fork", False))
        plan = plan_readme(
            repository=repository,
            current_readme=readme,
            default_branch=default_branch,
            root_paths=root_paths,
            classification=classifications.get(repository, ClassificationEvidence()),
            repository_url=str(repo.get("html_url") or f"https://github.com/{repository}"),
            archived=archived,
            fork=fork,
        )
        counts[plan.action.value] = counts.get(plan.action.value, 0) + 1

        if not args.write or plan.action in {
            ReadmeAction.ADOPT,
            ReadmeAction.NO_CHANGE,
            ReadmeAction.REPAIR_REQUIRED,
            ReadmeAction.ARCHIVED_READ_ONLY,
        }:
            rows.append(
                _receipt_row(
                    repository=repository,
                    action=plan.action,
                    reason=plan.reason,
                    mode="plan" if not args.write else "write",
                    verified=plan.action == ReadmeAction.ADOPT,
                )
            )
            continue

        if plan.readme is None:
            rows.append(
                _receipt_row(
                    repository=repository,
                    action=ReadmeAction.REPAIR_REQUIRED,
                    reason="write action did not produce README content",
                    mode="write",
                )
            )
            continue

        try:
            result = api.put_readme(
                repository,
                content=plan.readme,
                branch=default_branch,
                current_sha=readme_sha,
            )
            commit = result.get("commit") if isinstance(result.get("commit"), dict) else {}
            commit_sha = str(commit.get("sha") or "") or None
            readback_record = api.contents(repository, "README.md")
            if not isinstance(readback_record, dict):
                raise GitHubApiError("README readback is not a file")
            readback = api.decode_content(readback_record)
            parse_machine_contract(readback, expected_repository=repository)
            rows.append(
                _receipt_row(
                    repository=repository,
                    action=plan.action,
                    reason=plan.reason,
                    mode="write",
                    commit_sha=commit_sha,
                    readback_blob_sha=str(readback_record.get("sha") or "") or None,
                    verified=True,
                )
            )
        except (GitHubApiError, EstateReadmeError) as exc:
            rows.append(
                _receipt_row(
                    repository=repository,
                    action=ReadmeAction.REPAIR_REQUIRED,
                    reason=f"write/readback failed: {exc}",
                    mode="write",
                )
            )

    _write_jsonl(args.receipt, rows)
    summary = {
        "schema": "glaciereq.readme-estate-rollout.v1",
        "organization": args.org,
        "mode": "write" if args.write else "plan",
        "repository_count": len(repos),
        "classification_count": len(classifications),
        "actions": dict(sorted(counts.items())),
        "inspection_failures": len(errors),
        "receipt": str(args.receipt),
        "source_exhausted": args.limit is None and not args.repo,
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
