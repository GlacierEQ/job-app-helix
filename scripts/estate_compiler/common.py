from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


class EstateCompilerError(RuntimeError):
    pass


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


def lineage_roots(
    payload: dict[str, Any],
    native: set[str],
) -> tuple[dict[str, str], list[dict[str, Any]]]:
    rows = payload.get("relationships", [])
    if not isinstance(rows, list):
        raise EstateCompilerError("Lineage relationships must be a list")
    roots: dict[str, str] = {}
    allowed = {
        "SUCCESSOR_OF",
        "DUPLICATE_OF",
        "BACKUP_OF",
        "ARCHIVE_OF",
        "DEPENDENCY_OF",
        "REFERENCE_OF",
        "COMPONENT_OF",
    }
    normalized: list[dict[str, Any]] = []
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
            if member not in native or root not in native:
                raise EstateCompilerError(
                    f"Verified lineage leaves native census: {member} -> {root}"
                )
            if member in roots and roots[member] != root:
                raise EstateCompilerError(f"Multiple canonical roots for {member}")
            roots[member] = root
        normalized.append(dict(row))
    for member in list(roots):
        seen: set[str] = set()
        cursor = member
        while cursor in roots:
            if cursor in seen:
                raise EstateCompilerError(f"Lineage cycle at {cursor}")
            seen.add(cursor)
            cursor = roots[cursor]
        roots[member] = cursor
    return roots, normalized


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
