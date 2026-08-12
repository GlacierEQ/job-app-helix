"""Authenticated, completeness-accounted GitHub estate source crawler.

The crawler establishes what was actually inspected. It never turns partial
coverage into a completion claim. Repository trees are enumerated in full;
recursive-tree truncation falls back to explicit subtree traversal; every blob
is recorded; requested text is inspected; binary and oversized files remain
explicitly accounted rather than silently disappearing.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any, Protocol

SCHEMA = "glaciereq.crystallization-source-crawl.v1"
ACCESSIBLE_AFFILIATIONS = "owner,collaborator,organization_member"

TEXT_EXTENSIONS = {
    ".bash",
    ".c",
    ".cc",
    ".cfg",
    ".conf",
    ".cpp",
    ".cs",
    ".css",
    ".csv",
    ".dockerfile",
    ".env",
    ".example",
    ".go",
    ".graphql",
    ".h",
    ".hpp",
    ".html",
    ".ini",
    ".java",
    ".js",
    ".json",
    ".jsx",
    ".kt",
    ".kts",
    ".md",
    ".mjs",
    ".mts",
    ".php",
    ".proto",
    ".ps1",
    ".py",
    ".rb",
    ".rs",
    ".scss",
    ".sh",
    ".sql",
    ".swift",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".xml",
    ".yaml",
    ".yml",
    ".zsh",
}
TEXT_BASENAMES = {
    "agents.md",
    "dockerfile",
    "gemfile",
    "license",
    "makefile",
    "package-lock.json",
    "pnpm-lock.yaml",
    "procfile",
    "rakefile",
    "readme",
    "yarn.lock",
}
SOURCE_EXTENSIONS = {
    ".c",
    ".cc",
    ".cpp",
    ".cs",
    ".go",
    ".java",
    ".js",
    ".jsx",
    ".kt",
    ".kts",
    ".php",
    ".py",
    ".rb",
    ".rs",
    ".swift",
    ".ts",
    ".tsx",
}
SCAFFOLD_MARKERS = (
    "scaffold stub",
    "scaffold_allow",
    "implementation is the next agent's job",
    "replace body with the real algorithm",
    "filling ai",
)
INCOMPLETE_MARKERS = (
    "notimplementederror",
    "placeholder implementation",
    "raise notimplemented",
    "todo implement",
    "todo: implement",
)
GATE_THEATER_PATHS = {
    "machine/excellence-scores.json",
    "machine/excellence-state.json",
    "machine/promotion_authority.json",
    "machine/proof_receipt.json",
    "machine/target-contract.json",
    "src/promotion_authority.py",
}
ENTRYPOINT_BASENAMES = {
    "app.py",
    "cli.py",
    "index.js",
    "index.ts",
    "main.py",
    "manage.py",
    "server.py",
}
DEPLOYMENT_NAMES = {
    "docker-compose.yaml",
    "docker-compose.yml",
    "dockerfile",
    "fly.toml",
    "netlify.toml",
    "railway.json",
    "render.yaml",
    "serverless.yml",
    "vercel.json",
}
MANIFEST_NAMES = {
    "build.gradle",
    "build.gradle.kts",
    "cargo.toml",
    "go.mod",
    "package.json",
    "pom.xml",
    "pyproject.toml",
    "requirements.txt",
    "setup.py",
}
FUNCTION_PATTERNS = (
    re.compile(r"(?m)^\s*(?:async\s+)?def\s+[A-Za-z_]\w*\s*\("),
    re.compile(
        r"(?m)^\s*(?:export\s+)?(?:async\s+)?function\s+"
        r"[A-Za-z_$][\w$]*\s*\("
    ),
    re.compile(r"(?m)^\s*func\s+(?:\([^)]*\)\s*)?[A-Za-z_]\w*\s*\("),
    re.compile(r"(?m)^\s*(?:pub\s+)?fn\s+[A-Za-z_]\w*\s*\("),
)


class CrawlError(RuntimeError):
    pass


class Api(Protocol):
    def get_json(self, path: str) -> Any: ...


@dataclass(frozen=True)
class Repository:
    position: int
    repository: str
    repository_id: int
    default_branch: str
    visibility: str
    archived: bool
    fork: bool
    can_push: bool
    can_admin: bool
    parent: str | None


class GitHubApi:
    def __init__(self, token: str, api_root: str = "https://api.github.com") -> None:
        if not token:
            raise CrawlError("GitHub token is required")
        self.token = token
        self.api_root = api_root.rstrip("/")

    def get_json(self, path: str) -> Any:
        request = urllib.request.Request(
            self.api_root + path,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.token}",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "job-app-helix-crystallization-crawler",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            message = f"GitHub HTTP {exc.code} for {path}: {detail[:300]}"
            raise CrawlError(message) from exc
        except urllib.error.URLError as exc:
            message = f"GitHub transport failure for {path}: {exc.reason}"
            raise CrawlError(message) from exc
        except json.JSONDecodeError as exc:
            raise CrawlError(f"GitHub returned invalid JSON for {path}") from exc


def _repo_from_api(item: dict[str, Any], position: int) -> Repository:
    full_name = item.get("full_name")
    repository_id = item.get("id")
    default_branch = item.get("default_branch")
    visibility = item.get("visibility")
    if visibility is None:
        visibility = "private" if item.get("private") else "public"

    if not isinstance(full_name, str) or "/" not in full_name:
        raise CrawlError(f"invalid repository identity at position {position}")
    if not isinstance(repository_id, int):
        raise CrawlError(f"{full_name}: missing numeric repository id")
    if not isinstance(default_branch, str) or not default_branch:
        raise CrawlError(f"{full_name}: missing default branch")

    permissions = item.get("permissions")
    if not isinstance(permissions, dict):
        permissions = {}
    parent = item.get("parent")
    if not isinstance(parent, dict):
        parent = {}

    return Repository(
        position=position,
        repository=full_name,
        repository_id=repository_id,
        default_branch=default_branch,
        visibility=str(visibility),
        archived=bool(item.get("archived")),
        fork=bool(item.get("fork")),
        can_push=bool(permissions.get("push")),
        can_admin=bool(permissions.get("admin")),
        parent=str(parent.get("full_name")) if parent.get("full_name") else None,
    )


def list_accessible_repositories(
    api: Api,
    *,
    per_page: int = 100,
) -> list[Repository]:
    if not 1 <= per_page <= 100:
        raise CrawlError("per_page must be between 1 and 100")

    repositories: list[Repository] = []
    seen: set[int] = set()
    page = 1
    while True:
        query = urllib.parse.urlencode(
            {
                "affiliation": ACCESSIBLE_AFFILIATIONS,
                "visibility": "all",
                "sort": "full_name",
                "direction": "asc",
                "per_page": per_page,
                "page": page,
            }
        )
        value = api.get_json(f"/user/repos?{query}")
        if not isinstance(value, list):
            raise CrawlError(f"accessible repository page {page} was not a list")
        if not value:
            break

        for item in value:
            if not isinstance(item, dict):
                message = f"accessible repository page {page} contained a non-object"
                raise CrawlError(message)
            repository = _repo_from_api(item, len(repositories))
            if repository.repository_id in seen:
                raise CrawlError(f"duplicate repository id {repository.repository_id}")
            seen.add(repository.repository_id)
            repositories.append(repository)

        if len(value) < per_page:
            break
        page += 1
    return repositories


def _quote_repository(repository: str) -> tuple[str, str]:
    owner, name = repository.split("/", 1)
    return urllib.parse.quote(owner, safe=""), urllib.parse.quote(name, safe="")


def _tree_path(repository: str, treeish: str, *, recursive: bool) -> str:
    owner, name = _quote_repository(repository)
    encoded = urllib.parse.quote(treeish, safe="")
    suffix = "?recursive=1" if recursive else ""
    return f"/repos/{owner}/{name}/git/trees/{encoded}{suffix}"


def _parse_tree(
    value: Any,
    repository: str,
) -> tuple[list[dict[str, Any]], bool, str | None]:
    if not isinstance(value, dict) or not isinstance(value.get("tree"), list):
        raise CrawlError(f"{repository}: malformed Git tree response")
    tree_sha = value.get("sha") if isinstance(value.get("sha"), str) else None
    entries = [item for item in value["tree"] if isinstance(item, dict)]
    return entries, bool(value.get("truncated")), tree_sha


def _walk_subtrees(
    api: Api,
    repository: Repository,
    root_entries: list[dict[str, Any]],
    root_sha: str | None,
) -> tuple[list[dict[str, Any]], int]:
    discovered: list[dict[str, Any]] = []
    stack: list[tuple[str, list[dict[str, Any]]]] = [("", root_entries)]
    visited_trees = {root_sha} if root_sha else set()

    while stack:
        prefix, entries = stack.pop()
        for item in entries:
            raw_path = str(item.get("path", ""))
            if not raw_path:
                raise CrawlError(f"{repository.repository}: tree entry missing path")
            path = f"{prefix}/{raw_path}" if prefix else raw_path
            copied = dict(item)
            copied["path"] = path
            discovered.append(copied)

            if item.get("type") != "tree":
                continue
            child_sha = item.get("sha")
            if not isinstance(child_sha, str) or not child_sha:
                raise CrawlError(f"{repository.repository}:{path}: tree missing sha")
            if child_sha in visited_trees:
                continue
            visited_trees.add(child_sha)
            value = api.get_json(
                _tree_path(repository.repository, child_sha, recursive=False)
            )
            child_entries, truncated, _ = _parse_tree(
                value,
                repository.repository,
            )
            if truncated:
                raise CrawlError(
                    f"{repository.repository}: subtree {child_sha} truncated"
                )
            stack.append((path, child_entries))

    return discovered, len(visited_trees)


def enumerate_tree(
    api: Api,
    repository: Repository,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Enumerate every tree entry, falling back when recursive output truncates."""
    recursive_path = _tree_path(
        repository.repository,
        repository.default_branch,
        recursive=True,
    )
    first = api.get_json(recursive_path)
    entries, truncated, root_sha = _parse_tree(first, repository.repository)
    if not truncated:
        normalized = sorted(entries, key=lambda item: str(item.get("path", "")))
        return normalized, {
            "strategy": "recursive_tree",
            "recursive_response_truncated": False,
            "root_tree_sha": root_sha,
        }

    root_path = _tree_path(
        repository.repository,
        repository.default_branch,
        recursive=False,
    )
    root = api.get_json(root_path)
    root_entries, root_truncated, root_sha = _parse_tree(
        root,
        repository.repository,
    )
    if root_truncated:
        message = (
            f"{repository.repository}: non-recursive root tree unexpectedly truncated"
        )
        raise CrawlError(message)

    discovered, visited_tree_count = _walk_subtrees(
        api,
        repository,
        root_entries,
        root_sha,
    )
    normalized = sorted(discovered, key=lambda item: str(item.get("path", "")))
    return normalized, {
        "strategy": "explicit_subtree_walk",
        "recursive_response_truncated": True,
        "root_tree_sha": root_sha,
        "visited_tree_count": visited_tree_count,
    }


def _is_likely_text(path: str) -> bool:
    pure = PurePosixPath(path)
    basename = pure.name.casefold()
    if basename in TEXT_BASENAMES or basename.startswith("readme"):
        return True
    return pure.suffix.casefold() in TEXT_EXTENSIONS


def _language(path: str) -> str | None:
    suffix = PurePosixPath(path).suffix.casefold()
    languages = {
        ".bash": "Shell",
        ".c": "C",
        ".cc": "C++",
        ".cpp": "C++",
        ".cs": "C#",
        ".go": "Go",
        ".java": "Java",
        ".js": "JavaScript",
        ".jsx": "JavaScript",
        ".kt": "Kotlin",
        ".kts": "Kotlin",
        ".php": "PHP",
        ".py": "Python",
        ".rb": "Ruby",
        ".rs": "Rust",
        ".sh": "Shell",
        ".sql": "SQL",
        ".swift": "Swift",
        ".ts": "TypeScript",
        ".tsx": "TypeScript",
    }
    return languages.get(suffix)


def _blob_path(repository: str, sha: str) -> str:
    owner, name = _quote_repository(repository)
    encoded_sha = urllib.parse.quote(sha, safe="")
    return f"/repos/{owner}/{name}/git/blobs/{encoded_sha}"


def fetch_blob_text(api: Api, repository: str, sha: str) -> str:
    value = api.get_json(_blob_path(repository, sha))
    if not isinstance(value, dict) or value.get("encoding") != "base64":
        raise CrawlError(f"{repository}:{sha}: unsupported blob response")
    content = value.get("content")
    if not isinstance(content, str):
        raise CrawlError(f"{repository}:{sha}: blob content missing")
    try:
        raw = base64.b64decode(content, validate=False)
    except (ValueError, binascii.Error) as exc:
        raise CrawlError(f"{repository}:{sha}: invalid base64 blob") from exc
    if b"\x00" in raw[:8192]:
        raise UnicodeError("binary content")
    return raw.decode("utf-8")


def analyze_text(path: str, text: str) -> dict[str, Any]:
    lowered = text.casefold()
    scaffold = sorted(marker for marker in SCAFFOLD_MARKERS if marker in lowered)
    incomplete = sorted(
        marker for marker in INCOMPLETE_MARKERS if marker in lowered
    )
    function_count = sum(
        len(pattern.findall(text)) for pattern in FUNCTION_PATTERNS
    )
    heading = None
    if PurePosixPath(path).name.casefold().startswith("readme"):
        for line in text.splitlines():
            if line.startswith("# ") and line[2:].strip():
                heading = line[2:].strip()[:200]
                break
    return {
        "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "line_count": text.count("\n") + (1 if text else 0),
        "function_definition_count": function_count,
        "scaffold_markers": scaffold,
        "incomplete_markers": incomplete,
        "readme_heading": heading,
    }


def _is_test_path(lower: str, base: str) -> bool:
    return bool(
        "/test" in lower
        or lower.startswith("test")
        or base.startswith("test_")
        or base.endswith(".test.ts")
    )


def _path_surface_flags(path: str) -> list[str]:
    lower = path.casefold()
    pure = PurePosixPath(lower)
    base = pure.name
    flags: list[str] = []

    if base.startswith("readme"):
        flags.append("readme")
    if base in MANIFEST_NAMES:
        flags.append("package_manifest")
    if lower.startswith(".github/workflows/"):
        flags.append("workflow")
    if _is_test_path(lower, base):
        flags.append("test")
    if pure.suffix in SOURCE_EXTENSIONS:
        flags.append("source")
    if lower.startswith("scripts/") or base in ENTRYPOINT_BASENAMES:
        flags.append("execution")
    if base in DEPLOYMENT_NAMES or lower.startswith("supabase/functions/"):
        flags.append("deployment")
    if lower in GATE_THEATER_PATHS:
        flags.append("legacy_gate_artifact")
    return flags


def _should_fetch_text(
    *,
    likely_text: bool,
    content_mode: str,
    flags: list[str],
    priority_surfaces: set[str],
) -> bool:
    if not likely_text:
        return False
    if content_mode == "all-text":
        return True
    if content_mode == "priority":
        return bool(priority_surfaces.intersection(flags))
    return False


def _record_text_analysis(
    *,
    path: str,
    analysis: dict[str, Any],
    scaffold_findings: list[dict[str, Any]],
    incomplete_findings: list[dict[str, Any]],
    readme_headings: list[str],
) -> None:
    heading = analysis["readme_heading"]
    if heading:
        readme_headings.append(str(heading))
    if analysis["scaffold_markers"]:
        scaffold_findings.append(
            {"path": path, "markers": analysis["scaffold_markers"]}
        )
    if analysis["incomplete_markers"]:
        incomplete_findings.append(
            {"path": path, "markers": analysis["incomplete_markers"]}
        )


def crawl_repository(
    api: Api,
    repository: Repository,
    *,
    content_mode: str = "all-text",
    max_text_bytes: int = 1_000_000,
) -> dict[str, Any]:
    if content_mode not in {"tree-only", "priority", "all-text"}:
        raise CrawlError(f"unsupported content_mode {content_mode}")
    if max_text_bytes <= 0:
        raise CrawlError("max_text_bytes must be positive")

    entries, tree_receipt = enumerate_tree(api, repository)
    blobs = [entry for entry in entries if entry.get("type") == "blob"]
    files: list[dict[str, Any]] = []
    language_counts: Counter[str] = Counter()
    surface_counts: Counter[str] = Counter()
    scaffold_findings: list[dict[str, Any]] = []
    incomplete_findings: list[dict[str, Any]] = []
    readme_headings: list[str] = []
    inspected_text = 0
    accounted_binary = 0
    oversized_text = 0
    text_fetch_failures = 0
    total_function_definitions = 0

    priority_surfaces = {
        "deployment",
        "execution",
        "package_manifest",
        "readme",
        "test",
        "workflow",
    }

    for entry in blobs:
        path = str(entry.get("path", ""))
        sha = entry.get("sha")
        size = entry.get("size")
        if not path or not isinstance(sha, str):
            raise CrawlError(f"{repository.repository}: blob entry missing path/sha")
        if not isinstance(size, int) or size < 0:
            size = 0

        flags = _path_surface_flags(path)
        surface_counts.update(flags)
        language = _language(path)
        if language:
            language_counts[language] += 1

        likely_text = _is_likely_text(path)
        should_fetch = _should_fetch_text(
            likely_text=likely_text,
            content_mode=content_mode,
            flags=flags,
            priority_surfaces=priority_surfaces,
        )
        record: dict[str, Any] = {
            "path": path,
            "blob_sha": sha,
            "size": size,
            "likely_text": likely_text,
            "surface_flags": flags,
            "content_state": "ACCOUNTED_NOT_REQUESTED",
        }

        if not likely_text:
            record["content_state"] = "ACCOUNTED_BINARY_OR_UNKNOWN"
            accounted_binary += 1
        elif size > max_text_bytes:
            record["content_state"] = "ACCOUNTED_OVERSIZED_TEXT"
            oversized_text += 1
        elif should_fetch:
            try:
                text = fetch_blob_text(api, repository.repository, sha)
                analysis = analyze_text(path, text)
                record["content_state"] = "TEXT_INSPECTED"
                record["analysis"] = analysis
                inspected_text += 1
                total_function_definitions += int(
                    analysis["function_definition_count"]
                )
                _record_text_analysis(
                    path=path,
                    analysis=analysis,
                    scaffold_findings=scaffold_findings,
                    incomplete_findings=incomplete_findings,
                    readme_headings=readme_headings,
                )
            except UnicodeError:
                record["content_state"] = "ACCOUNTED_BINARY_DETECTED"
                accounted_binary += 1
            except CrawlError as exc:
                record["content_state"] = "TEXT_FETCH_FAILED"
                record["error"] = str(exc)
                text_fetch_failures += 1
        files.append(record)

    all_files_accounted = len(files) == len(blobs)
    requested_text = sum(
        1
        for file in files
        if file["likely_text"]
        and file["size"] <= max_text_bytes
        and _should_fetch_text(
            likely_text=True,
            content_mode=content_mode,
            flags=file["surface_flags"],
            priority_surfaces=priority_surfaces,
        )
    )
    requested_text_complete = (
        text_fetch_failures == 0 and inspected_text == requested_text
    )
    unresolved_content_count = oversized_text + text_fetch_failures

    if scaffold_findings or incomplete_findings or unresolved_content_count:
        status = "INCOMPLETE"
    elif content_mode != "all-text":
        status = "UNDERSTOOD_PARTIAL_SOURCE"
    else:
        status = "SOURCE_INSPECTED_NEEDS_PURPOSE_ADJUDICATION"

    legacy_gate_artifacts = sorted(
        file["path"]
        for file in files
        if "legacy_gate_artifact" in file["surface_flags"]
    )
    return {
        "repository": repository.repository,
        "repository_id": repository.repository_id,
        "position": repository.position,
        "default_branch": repository.default_branch,
        "visibility": repository.visibility,
        "archived": repository.archived,
        "fork": repository.fork,
        "parent": repository.parent,
        "can_push": repository.can_push,
        "can_admin": repository.can_admin,
        "tree": tree_receipt,
        "tree_entry_count": len(entries),
        "file_count": len(blobs),
        "all_files_accounted": all_files_accounted,
        "content_mode": content_mode,
        "text_inspected_count": inspected_text,
        "binary_or_unknown_accounted_count": accounted_binary,
        "oversized_text_count": oversized_text,
        "text_fetch_failure_count": text_fetch_failures,
        "unresolved_content_count": unresolved_content_count,
        "requested_text_complete": requested_text_complete,
        "language_file_counts": dict(sorted(language_counts.items())),
        "surface_counts": dict(sorted(surface_counts.items())),
        "function_definition_count": total_function_definitions,
        "readme_headings": sorted(set(readme_headings)),
        "scaffold_findings": scaffold_findings,
        "incomplete_findings": incomplete_findings,
        "legacy_gate_artifacts": legacy_gate_artifacts,
        "status": status,
        "files": files,
    }


def crawl_estate(
    api: Api,
    repositories: list[Repository],
    *,
    content_mode: str = "all-text",
    max_text_bytes: int = 1_000_000,
    workers: int = 4,
) -> dict[str, Any]:
    if workers < 1:
        raise CrawlError("workers must be positive")

    results: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        future_map = {
            pool.submit(
                crawl_repository,
                api,
                repository,
                content_mode=content_mode,
                max_text_bytes=max_text_bytes,
            ): repository
            for repository in repositories
        }
        for future in as_completed(future_map):
            repository = future_map[future]
            try:
                results.append(future.result())
            except Exception as exc:
                failures.append(
                    {
                        "repository": repository.repository,
                        "error_type": type(exc).__name__,
                        "error": str(exc)[:1000],
                    }
                )

    results.sort(key=lambda item: int(item["position"]))
    failures.sort(key=lambda item: item["repository"].casefold())
    accounted = sum(int(item["file_count"]) for item in results)
    inspected = sum(int(item["text_inspected_count"]) for item in results)
    unresolved = sum(int(item["unresolved_content_count"]) for item in results)
    tree_complete = not failures and all(
        bool(item["all_files_accounted"]) for item in results
    )
    semantic_text_complete = bool(
        content_mode == "all-text"
        and tree_complete
        and unresolved == 0
        and all(bool(item["requested_text_complete"]) for item in results)
    )

    receipt = {
        "schema": SCHEMA,
        "mandate": "CRYSTALLIZATION-MANDATE",
        "repository_input_count": len(repositories),
        "repository_crawled_count": len(results),
        "repository_failure_count": len(failures),
        "all_repository_trees_complete": tree_complete,
        "semantic_text_inspection_complete": semantic_text_complete,
        "file_accounted_count": accounted,
        "text_inspected_count": inspected,
        "unresolved_content_count": unresolved,
        "content_mode": content_mode,
        "repositories": results,
        "failures": failures,
    }
    serialized = json.dumps(
        receipt,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    receipt["receipt_digest"] = hashlib.sha256(serialized).hexdigest()
    return receipt
