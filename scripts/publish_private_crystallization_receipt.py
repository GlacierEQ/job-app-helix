#!/usr/bin/env python3
"""Publish a private crystallization receipt to a private GitHub control repository."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path, PurePosixPath


class PublishError(RuntimeError):
    pass


def _safe_path(value: str) -> str:
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise PublishError("destination path must be a safe repository-relative POSIX path")
    return path.as_posix()


def _request(token: str, method: str, url: str, body: dict | None = None):
    data = None if body is None else json.dumps(body, separators=(",", ":")).encode()
    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
            "User-Agent": "job-app-helix-private-crystallization-publisher",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            raw = response.read()
            return json.loads(raw.decode()) if raw else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        if exc.code == 404 and method == "GET":
            return None
        raise PublishError(f"GitHub HTTP {exc.code}: {detail[:500]}") from exc
    except urllib.error.URLError as exc:
        raise PublishError(f"GitHub transport error: {exc.reason}") from exc


def publish(
    *,
    token: str,
    repository: str,
    destination: str,
    content: bytes,
    branch: str = "main",
    api_root: str = "https://api.github.com",
) -> dict:
    if not token:
        raise PublishError("token required")
    if "/" not in repository:
        raise PublishError("repository must use owner/name form")
    destination = _safe_path(destination)
    owner, name = repository.split("/", 1)
    base = (
        f"{api_root.rstrip('/')}/repos/{urllib.parse.quote(owner, safe='')}/"
        f"{urllib.parse.quote(name, safe='')}/contents/"
        f"{urllib.parse.quote(destination, safe='/')}"
    )
    query = urllib.parse.urlencode({"ref": branch})
    current = _request(token, "GET", f"{base}?{query}")
    sha = current.get("sha") if isinstance(current, dict) else None
    body = {
        "message": f"Update private crystallization receipt: {destination}",
        "content": base64.b64encode(content).decode(),
        "branch": branch,
    }
    if sha:
        body["sha"] = sha
    result = _request(token, "PUT", base, body)
    if not isinstance(result, dict) or not isinstance(result.get("commit"), dict):
        raise PublishError("GitHub did not return a commit after private receipt publication")
    return {
        "repository": repository,
        "destination": destination,
        "branch": branch,
        "content_sha256": hashlib.sha256(content).hexdigest(),
        "commit_sha": result["commit"].get("sha"),
        "updated_existing": bool(sha),
    }


def parse_args() -> argparse.Namespace:
    description = "Publish a receipt into a private control repository"
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("receipt", type=Path)
    parser.add_argument(
        "--token",
        default=os.environ.get("GLACIEREQ_ESTATE_TOKEN", ""),
    )
    parser.add_argument("--repository", default="GlacierEQ/monolith")
    parser.add_argument("--destination", required=True)
    parser.add_argument("--branch", default="main")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        content = args.receipt.read_bytes()
        # Validate JSON before publishing so a truncated local write cannot poison private state.
        json.loads(content.decode("utf-8"))
        result = publish(
            token=args.token,
            repository=args.repository,
            destination=args.destination,
            content=content,
            branch=args.branch,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, PublishError) as exc:
        print(json.dumps({"state": "ERROR", "error": str(exc)}, indent=2))
        return 2
    print(
        "Private crystallization receipt published: "
        f"repository={result['repository']} destination={result['destination']} "
        f"content_sha256={result['content_sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
