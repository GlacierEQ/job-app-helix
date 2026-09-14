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
from collections.abc import Iterable, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
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
DEFAULT_OWNER = "GlacierEQ"
DEFAULT_MONOLITH = "GlacierEQ/monolith"


class GitHubApiError(RuntimeError):
    pass


class MappingHeaders(dict[str, str]):
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

    def repository(self, repository: str) -> dict[str, Any]:
        value = self.get(f"{API}/repos/{repository}")
        if not isinstance(value, dict):
            raise GitHubApiError(f"repository metadata is not an object: {repository}")
        return value

    def list_public_user_repositories(self, owner: str) -> list[dict[str, Any]]:
        repositories: list[dict[str, Any]] = []
        page = 1
        while True:
            query = urllib.parse.urlencode(
                {"type": "owner", "per_page": 100, "page": page, "sort": "full_name"}
            )
            rows = self.get(f"{API}/users/{owner}/repos?{query}")
            if not isinstance(rows, list):
                raise GitHubApiError("user repository response is not a list")
            repositories.extend(row for row in rows if isinstance(row, dict))
            if len(rows) < 100:
                break
            page += 1
        return repositories

    def list_authenticated_owned_repositories(self, owner: str) -> list[dict[str, Any]]:
        repositories: list[dict[str, Any]] = []
        page = 1
        try:
            while True:
                query = urllib.parse.urlencode(
                    {
                        "affiliation": "owner",
                        "visibility": "all",
                        "per_page": 100,
                        "page": page,
                        "sort": "full_name",
                    }
                )
                rows = self.get(f"{API}/user/repos?{query}")
                if not isinstance(rows, list):
                    return repositories
                repositories.extend(
                    row
                    for row in rows
                    if isinstance(row, dict)
                    and isinstance(row.get("owner"), dict)
                    and row["owner"].get("login") == owner
                )
                if len(rows) < 100:
                    break
                page += 1
        except GitHubApiError:
            return repositories
        return repositories

    def list_installation_repositories(self, owner: str) -> list[dict[str, Any]]:
        repositories: list[dict[str, Any]] = []
        page = 1
        try:
            while True:
                query = urllib.parse.urlencode({"per_page": 100, "page": page})
                payload = self.get(f"{API}/installation/repositories?{query}")
                if not isinstance(payload, dict):
                    return repositories
                rows = payload.get("repositories")
                if not isinstance(rows, list):
                    return repositories
                repositories.extend(
                    row
                    for row in rows
                    if isinstance(row, dict)
                    and isinstance(row.get("owner"), dict)
                    and row["owner"].get("login") == owner
                )
                if len(rows) < 100:
                    break
                page += 1
        except GitHubApiError:
            return repositories
        return repositories

    def contents(self, repository: str, path: str = "") -> Any:
        encoded_path = "/".join(urllib.parse.quote(part, safe="") for part in path.split("/"))
        suffix = f"/contents/{encoded_path}" if encoded_path else "/contents"
        return self.get(f"{API}/repos/{repository}{suffix}")

    def decode_content(self, repository: str, record: dict[str, Any]) -> str:
        encoded = record.get("content")
        if isinstance(encoded, str):
            return base64.b64decode(encoded).decode("utf-8")
        sha = record.get("sha")
        if not isinstance(sha, str) or not sha:
            raise GitHubApiError("contents record has neither inline content nor blob SHA")
        blob = self.get(f"{API}/repos/{repository}/git/blobs/{sha}")
        if not isinstance(blob, dict) or not isinstance(blob.get("content"), str):
            raise GitHubApiError(f"unable to fetch text blob {sha} from {repository}")
        encoding = blob.get("encoding")
        if encoding == "base64":
            return base64.b64decode(blob["content"]).decode("utf-8")
        if encoding == "utf-8":
            return str(blob["content"])
        raise GitHubApiError(f"unsupported blob encoding {encoding!r} for {repository}:{sha}")

    def put_readme(
        self,
        repository: str,
        *,
        path: str,
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
        encoded_path = "/".join(urllib.parse.quote(part, safe="") for part in path.split("/"))
        result, _ = self.request(
            "PUT",
            f"{API}/repos/{repository}/contents/{encoded_path}",
            payload,
        )
        if not isinstance(result, dict):
            raise GitHubApiError("README write returned non-object result")
        return result


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


def _qualified(owner: str, repository: str) -> str:
    return repository if "/" in repository else f"{owner}/{repository}"


def extract_legacy_repository_ids(payload: Mapping[str, Any], owner: str) -> set[str]:
    """Read only repository arrays from functional_heads.*.subcategories.*.domains.*."""
    heads = payload.get("functional_heads")
    if not isinstance(heads, dict):
        return set()
    repositories: set[str] = set()
    for head in heads.values():
        if not isinstance(head, dict):
            continue
        subcategories = head.get("subcategories")
        if not isinstance(subcategories, dict):
            continue
        for subcategory in subcategories.values():
            if not isinstance(subcategory, dict):
                continue
            domains = subcategory.get("domains")
            if not isinstance(domains, dict):
                continue
            for values in domains.values():
                if not isinstance(values, list):
                    continue
                for value in values:
                    if isinstance(value, str) and value:
                        repositories.add(_qualified(owner, value))
    return repositories


def extract_library_repository_ids(payload: Mapping[str, Any], owner: str) -> set[str]:
    entries = payload.get("entries")
    if not isinstance(entries, list):
        return set()
    repositories: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name") or entry.get("repository") or entry.get("full_name")
        if isinstance(name, str) and name:
            repositories.add(_qualified(owner, name))
    return repositories


def load_monolith_estate(
    api: GitHubApi,
    monolith: str,
    *,
    owner: str,
    workers: int,
) -> tuple[dict[str, ClassificationEvidence], set[str]]:
    ledger_paths = ["catalog/RECLASSIFICATION_LEDGER.jsonl"]
    directory = api.contents(monolith, "catalog/reclassification-ledger")
    if isinstance(directory, list):
        ledger_paths.extend(
            str(item["path"])
            for item in directory
            if isinstance(item, dict)
            and item.get("type") == "file"
            and str(item.get("name", "")).endswith(".jsonl")
        )
    ledger_paths = sorted(set(ledger_paths), key=str.casefold)
    source_paths = ledger_paths + ["catalog/HIERARCHICAL_MESH_MAP.json", "catalog/library.json"]

    def fetch(path: str) -> tuple[str, str]:
        record = api.contents(monolith, path)
        if not isinstance(record, dict):
            raise GitHubApiError(f"Monolith source path is not a file: {path}")
        return path, api.decode_content(monolith, record)

    texts: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        futures = {executor.submit(fetch, path): path for path in source_paths}
        for future in as_completed(futures):
            path, text = future.result()
            texts[path] = text

    classifications: dict[str, ClassificationEvidence] = {}
    repositories: set[str] = set()
    for path in ledger_paths:
        for row in _load_jsonl(texts[path]):
            repository = row.get("repository")
            if not isinstance(repository, str) or not repository:
                continue
            repository = _qualified(owner, repository)
            if repository in classifications:
                raise GitHubApiError(f"duplicate logical Monolith ledger identity: {repository}")
            evidence = row.get("evidence") if isinstance(row.get("evidence"), dict) else {}
            classifications[repository] = ClassificationEvidence(
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
            repositories.add(repository)

    legacy = json.loads(texts["catalog/HIERARCHICAL_MESH_MAP.json"])
    library = json.loads(texts["catalog/library.json"])
    if isinstance(legacy, dict):
        repositories.update(extract_legacy_repository_ids(legacy, owner))
    if isinstance(library, dict):
        repositories.update(extract_library_repository_ids(library, owner))
    return classifications, repositories


def discover_provider_repositories(api: GitHubApi, owner: str) -> dict[str, dict[str, Any]]:
    discovered: dict[str, dict[str, Any]] = {}
    sources = [api.list_public_user_repositories(owner)]
    private_user = api.list_authenticated_owned_repositories(owner)
    if private_user:
        sources.append(private_user)
    installation = api.list_installation_repositories(owner)
    if installation:
        sources.append(installation)
    for rows in sources:
        for row in rows:
            full_name = row.get("full_name")
            if isinstance(full_name, str) and full_name:
                discovered[full_name] = row
    return discovered


def _root_index(api: GitHubApi, repository: str) -> tuple[list[str], str | None, dict[str, Any] | None]:
    root = api.contents(repository)
    if not isinstance(root, list):
        return [], None, None
    names = sorted(
        str(item["name"])
        for item in root
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    )
    readme_item = next(
        (
            item
            for item in root
            if isinstance(item, dict)
            and item.get("type") == "file"
            and isinstance(item.get("name"), str)
            and str(item["name"]).casefold() == "readme.md"
        ),
        None,
    )
    readme_path = str(readme_item["name"]) if isinstance(readme_item, dict) else None
    return names, readme_path, readme_item if isinstance(readme_item, dict) else None


def _inspect_repository(
    api: GitHubApi,
    repo: dict[str, Any],
) -> tuple[dict[str, Any], str | None, str | None, str, list[str]]:
    full_name = str(repo["full_name"])
    root_paths, readme_path, readme_record = _root_index(api, full_name)
    readme = None
    readme_sha = None
    if isinstance(readme_record, dict):
        readme = api.decode_content(full_name, readme_record)
        readme_sha = str(readme_record.get("sha") or "") or None
    return repo, readme, readme_sha, readme_path or "README.md", root_paths


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
    parser.add_argument("--owner", default=DEFAULT_OWNER)
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
    classifications, monolith_repositories = load_monolith_estate(
        api,
        args.monolith,
        owner=args.owner,
        workers=args.workers,
    )
    provider_repositories = discover_provider_repositories(api, args.owner)
    universe = set(monolith_repositories) | set(provider_repositories)
    if args.repo:
        requested = {_qualified(args.owner, value) for value in args.repo}
        unknown = requested - universe
        if unknown:
            print(
                "requested repositories not found in estate/provider universe: "
                + ", ".join(sorted(unknown)),
                file=sys.stderr,
            )
            return 2
        universe &= requested
    ordered_universe = sorted(universe, key=str.casefold)
    if args.limit is not None:
        ordered_universe = ordered_universe[: max(0, args.limit)]

    metadata: dict[str, dict[str, Any]] = dict(provider_repositories)
    errors: list[dict[str, Any]] = []
    missing_metadata = [repository for repository in ordered_universe if repository not in metadata]
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
        futures = {executor.submit(api.repository, repository): repository for repository in missing_metadata}
        for future in as_completed(futures):
            repository = futures[future]
            try:
                metadata[repository] = future.result()
            except Exception as exc:
                errors.append(
                    {
                        "repository": repository,
                        "action": "METADATA_UNAVAILABLE",
                        "reason": str(exc),
                        "mode": "write" if args.write else "plan",
                        "verified": False,
                    }
                )

    inspectable = [metadata[name] for name in ordered_universe if name in metadata]
    inspections: list[tuple[dict[str, Any], str | None, str | None, str, list[str]]] = []
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
        futures = {executor.submit(_inspect_repository, api, repo): repo for repo in inspectable}
        for future in as_completed(futures):
            repo = futures[future]
            try:
                inspections.append(future.result())
            except Exception as exc:
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
    for repo, readme, readme_sha, readme_path, root_paths in sorted(
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
                path=readme_path,
                content=plan.readme,
                branch=default_branch,
                current_sha=readme_sha,
            )
            commit = result.get("commit") if isinstance(result.get("commit"), dict) else {}
            commit_sha = str(commit.get("sha") or "") or None
            readback_record = api.contents(repository, readme_path)
            if not isinstance(readback_record, dict):
                raise GitHubApiError("README readback is not a file")
            readback = api.decode_content(repository, readback_record)
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
        "owner": args.owner,
        "mode": "write" if args.write else "plan",
        "monolith_repository_count": len(monolith_repositories),
        "provider_discovered_count": len(provider_repositories),
        "repository_universe_count": len(universe),
        "selected_repository_count": len(ordered_universe),
        "classification_count": len(classifications),
        "actions": dict(sorted(counts.items())),
        "provider_access_failures": len(errors),
        "receipt": str(args.receipt),
        "source_exhausted": args.limit is None and not args.repo,
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
