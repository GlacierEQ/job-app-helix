from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


class EstateCompilerError(RuntimeError):
    pass


COLLAPSE_RELATIONS = {
    "SUCCESSOR_OF",
    "DUPLICATE_OF",
    "BACKUP_OF",
    "ARCHIVE_OF",
    "COMPONENT_OF",
}
SUPPORT_RELATIONS = {"DEPENDENCY_OF", "REFERENCE_OF"}


def load_json(path: Path, *, optional: bool = False) -> dict[str, Any]:
    if optional and not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EstateCompilerError(f"Unable to load {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise EstateCompilerError(f"Expected object at {path}")
    return value


def native_records(census: dict[str, Any]) -> list[dict[str, Any]]:
    records = census.get("repositories")
    if not isinstance(records, list) or any(not isinstance(item, dict) for item in records):
        raise EstateCompilerError("Census repositories are invalid")
    native = [item for item in records if item.get("fork") is False]
    forks = [item for item in records if item.get("fork") is True]
    expected = (
        census.get("repository_count"),
        census.get("native_repository_count"),
        census.get("fork_repository_count"),
    )
    observed = (len(records), len(native), len(forks))
    if expected != observed:
        raise EstateCompilerError(
            f"Census arithmetic does not close: expected={expected} observed={observed}"
        )
    return native


def latest_assessments(path: Path) -> dict[str, dict[str, Any]]:
    latest: dict[str, tuple[str, dict[str, Any]]] = {}
    if not path.exists():
        return {}
    for candidate in sorted(path.glob("*.json")):
        payload = load_json(candidate)
        record = payload.get("assessment", payload)
        if not isinstance(record, dict):
            continue
        repo = record.get("repository")
        observed = record.get("observed_at", "")
        if not isinstance(repo, str) or not isinstance(observed, str):
            continue
        if repo not in latest or observed > latest[repo][0]:
            latest[repo] = (observed, record)
    return {repo: value for repo, (_, value) in latest.items()}


def flagship_map(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = payload.get("flagships")
    if not isinstance(rows, list):
        raise EstateCompilerError("Flagship registry is invalid")
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise EstateCompilerError("Flagship row is invalid")
        repo = row.get("repository")
        if repo is None:
            continue
        if not isinstance(repo, str) or repo in result:
            raise EstateCompilerError(f"Invalid or duplicate flagship repository: {repo}")
        result[repo] = row
    return result


def _assert_native(repository: str, native: set[str], context: str) -> None:
    if repository not in native:
        raise EstateCompilerError(f"{context} leaves native census: {repository}")


def lineage_graph(
    payload: dict[str, Any],
    native: set[str],
) -> tuple[dict[str, str], dict[str, str], list[dict[str, Any]]]:
    rows = payload.get("relationships", [])
    if not isinstance(rows, list):
        raise EstateCompilerError("Lineage relationships must be a list")
    collapse_roots: dict[str, str] = {}
    support_roots: dict[str, str] = {}
    normalized: list[dict[str, Any]] = []
    allowed = COLLAPSE_RELATIONS | SUPPORT_RELATIONS

    for row in rows:
        if not isinstance(row, dict):
            raise EstateCompilerError("Lineage row is invalid")
        member = row.get("member_repository")
        root = row.get("canonical_repository")
        relation = row.get("relation")
        state = row.get("state")
        if relation not in allowed or state not in {
            "VERIFIED",
            "CANDIDATE_REVIEW_REQUIRED",
        }:
            raise EstateCompilerError(f"Unsupported lineage row: {row}")
        if not isinstance(member, str) or not isinstance(root, str) or member == root:
            raise EstateCompilerError(f"Invalid lineage identity: {row}")
        if state == "VERIFIED":
            _assert_native(member, native, "Verified relationship")
            _assert_native(root, native, "Verified relationship")
            target = collapse_roots if relation in COLLAPSE_RELATIONS else support_roots
            if member in target and target[member] != root:
                raise EstateCompilerError(f"Multiple canonical roots for {member}")
            target[member] = root
        normalized.append(dict(row))

    for member in list(collapse_roots):
        seen: set[str] = set()
        cursor = member
        while cursor in collapse_roots:
            if cursor in seen:
                raise EstateCompilerError(f"Lineage cycle at {cursor}")
            seen.add(cursor)
            cursor = collapse_roots[cursor]
        collapse_roots[member] = cursor

    for member, root in list(support_roots.items()):
        seen: set[str] = {member}
        cursor = root
        while cursor in collapse_roots:
            if cursor in seen:
                raise EstateCompilerError(f"Support relationship enters cycle at {cursor}")
            seen.add(cursor)
            cursor = collapse_roots[cursor]
        support_roots[member] = cursor

    return collapse_roots, support_roots, normalized


def canonical_assertions(payload: dict[str, Any], native: set[str]) -> set[str]:
    rows = payload.get("canonical_assertions", [])
    if not isinstance(rows, list):
        raise EstateCompilerError("canonical_assertions must be a list")
    verified: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            raise EstateCompilerError("Canonical assertion is invalid")
        repo = row.get("repository")
        state = row.get("state")
        refs = row.get("evidence_refs", [])
        if not isinstance(repo, str) or state not in {
            "VERIFIED",
            "CANDIDATE_REVIEW_REQUIRED",
        }:
            raise EstateCompilerError(f"Invalid canonical assertion: {row}")
        if not isinstance(refs, list) or any(not isinstance(item, str) for item in refs):
            raise EstateCompilerError(f"Invalid canonical evidence refs: {repo}")
        if state == "VERIFIED":
            _assert_native(repo, native, "Verified canonical assertion")
            if not refs:
                raise EstateCompilerError(
                    f"Verified canonical assertion requires evidence refs: {repo}"
                )
            verified.add(repo)
    return verified


def namespace_assertions(payload: dict[str, Any], native: set[str]) -> dict[str, str]:
    rows = payload.get("namespace_assertions", [])
    if not isinstance(rows, list):
        raise EstateCompilerError("namespace_assertions must be a list")
    namespaces: dict[str, str] = {}
    allowed = {"ENGINEERING", "RESTRICTED_LEGAL", "REFERENCE", "HISTORY"}
    for row in rows:
        if not isinstance(row, dict):
            raise EstateCompilerError("Namespace assertion is invalid")
        repo = row.get("repository")
        namespace = row.get("namespace")
        state = row.get("state")
        refs = row.get("evidence_refs", [])
        if (
            not isinstance(repo, str)
            or namespace not in allowed
            or state not in {"VERIFIED", "CANDIDATE_REVIEW_REQUIRED"}
        ):
            raise EstateCompilerError(f"Invalid namespace assertion: {row}")
        if not isinstance(refs, list) or any(not isinstance(item, str) for item in refs):
            raise EstateCompilerError(f"Invalid namespace evidence refs: {repo}")
        if state == "VERIFIED":
            _assert_native(repo, native, "Verified namespace assertion")
            if not refs:
                raise EstateCompilerError(
                    f"Verified namespace assertion requires evidence refs: {repo}"
                )
            if repo in namespaces and namespaces[repo] != namespace:
                raise EstateCompilerError(f"Conflicting namespace assertions: {repo}")
            namespaces[repo] = namespace
    return namespaces


def backup_like(repo: str) -> bool:
    name = repo.split("/", 1)[-1].casefold()
    return (
        name.startswith("z-backup-")
        or name.endswith(("-backup", "_backup"))
        or "snapshot" in name
        or "archive" in name
    )


def restricted_candidate(repo: str, policy: dict[str, Any]) -> bool:
    name = re.sub(r"[^a-z0-9]+", "-", repo.split("/", 1)[-1].casefold())
    tokens = policy.get("restricted_namespace_tokens", [])
    if not isinstance(tokens, list) or not all(isinstance(item, str) for item in tokens):
        raise EstateCompilerError("restricted_namespace_tokens must be strings")
    return any(
        re.search(rf"(^|-){re.escape(token.casefold())}(-|$)", name)
        for token in tokens
    )


def system_id(repo: str, flagship: dict[str, Any] | None) -> str:
    if flagship and isinstance(flagship.get("system_id"), str):
        return str(flagship["system_id"])
    return re.sub(
        r"[^a-z0-9._-]+", "-", repo.split("/", 1)[-1].casefold()
    ).strip("-")
