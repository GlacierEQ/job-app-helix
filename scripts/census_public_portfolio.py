#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
API_ROOT = "https://api.github.com"
DEFAULT_PORTFOLIO = ROOT / "manifests" / "portfolio_repositories.json"
DEFAULT_OUTPUT = ROOT / "artifacts" / "public-portfolio-census.json"


class PublicPortfolioCensusError(RuntimeError):
    pass


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PublicPortfolioCensusError(f"Unable to load {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise PublicPortfolioCensusError(f"Expected JSON object at {path}")
    return value


def _governed_repositories(manifest: dict[str, Any], owner: str) -> set[str]:
    workspace = manifest.get("workspace_repositories")
    if not isinstance(workspace, list) or not workspace:
        raise PublicPortfolioCensusError(
            "Portfolio manifest requires workspace_repositories"
        )
    names = {
        f"{owner}/{name}"
        for name in workspace
        if isinstance(name, str) and name.strip()
    }
    names.add(f"{owner}/job-app-helix")
    expected = manifest.get("total_repositories")
    if not isinstance(expected, int) or expected != len(names):
        raise PublicPortfolioCensusError(
            "Portfolio manifest cardinality does not match governed identities"
        )
    return names


def _normalize_repository(row: dict[str, Any], owner: str) -> dict[str, Any]:
    repository = row.get("full_name")
    repository_id = row.get("id")
    default_branch = row.get("default_branch")
    visibility = row.get("visibility")
    if visibility is None and row.get("private") is False:
        visibility = "public"
    if not isinstance(repository, str) or not repository.startswith(f"{owner}/"):
        raise PublicPortfolioCensusError(f"Invalid repository identity: {repository}")
    if not isinstance(repository_id, int):
        raise PublicPortfolioCensusError(f"{repository}: missing numeric repository id")
    if not isinstance(default_branch, str) or not default_branch:
        raise PublicPortfolioCensusError(f"{repository}: missing default branch")
    if visibility != "public":
        raise PublicPortfolioCensusError(
            f"{repository}: public fallback refuses non-public visibility"
        )
    return {
        "repository": repository,
        "repository_id": repository_id,
        "visibility": "public",
        "default_branch": default_branch,
        "archived": bool(row.get("archived", False)),
        "fork": bool(row.get("fork", False)),
        "classification": "RECRUITER_PORTFOLIO",
    }


def build_census(
    *,
    manifest: dict[str, Any],
    owner: str,
    repositories: Iterable[dict[str, Any]],
    generated_at: str | None = None,
) -> dict[str, Any]:
    governed = _governed_repositories(manifest, owner)
    rows_by_name: dict[str, dict[str, Any]] = {}
    for raw in repositories:
        if not isinstance(raw, dict):
            continue
        repository = raw.get("full_name")
        if repository not in governed:
            continue
        if repository in rows_by_name:
            raise PublicPortfolioCensusError(
                f"Duplicate public repository returned: {repository}"
            )
        rows_by_name[str(repository)] = _normalize_repository(raw, owner)

    missing = sorted(governed - set(rows_by_name))
    if missing:
        raise PublicPortfolioCensusError(
            "Governed public portfolio is incomplete: " + ", ".join(missing)
        )

    rows = [rows_by_name[name] for name in sorted(rows_by_name)]
    native_count = sum(not row["fork"] for row in rows)
    fork_count = len(rows) - native_count
    return {
        "schema": "glaciereq.public-portfolio-census.v1",
        "state": "VERIFIED_INVENTORY",
        "scope": "PUBLIC_ADMITTED_PORTFOLIO_ONLY",
        "authority": "manifests/portfolio_repositories.json + GitHub public metadata",
        "owner": owner,
        "generated_at": generated_at
        or datetime.now(UTC).isoformat(timespec="seconds"),
        "repository_count": len(rows),
        "native_repository_count": native_count,
        "fork_repository_count": fork_count,
        "public_repository_count": len(rows),
        "private_repository_count": 0,
        "repositories": rows,
        "boundary": {
            "authenticated_private_estate_not_queried": True,
            "private_repository_identities_omitted": True,
            "legal_private_records_omitted": True,
            "raw_owned_estate_cardinality_not_inferred": True,
        },
    }


class GitHubPublicPortfolioSource:
    def __init__(self, owner: str, token: str = "") -> None:
        if not owner:
            raise PublicPortfolioCensusError("Repository owner is required")
        self.owner = owner
        self.token = token.strip()

    def _request_json(self, path: str) -> Any:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "job-app-helix-public-portfolio-census",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        request = urllib.request.Request(f"{API_ROOT}{path}", headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise PublicPortfolioCensusError(
                f"GitHub public census failed with HTTP {exc.code}"
            ) from exc
        except urllib.error.URLError as exc:
            raise PublicPortfolioCensusError("GitHub public census failed") from exc
        except json.JSONDecodeError as exc:
            raise PublicPortfolioCensusError(
                "GitHub public census returned malformed JSON"
            ) from exc

    def list_all(self) -> list[dict[str, Any]]:
        quoted_owner = urllib.parse.quote(self.owner, safe="")
        rows: list[dict[str, Any]] = []
        page = 1
        while True:
            query = urllib.parse.urlencode(
                {
                    "type": "owner",
                    "sort": "full_name",
                    "direction": "asc",
                    "per_page": 100,
                    "page": page,
                }
            )
            payload = self._request_json(
                f"/users/{quoted_owner}/repos?{query}"
            )
            if not isinstance(payload, list):
                raise PublicPortfolioCensusError(
                    f"GitHub public census page {page} was not a list"
                )
            page_rows = [row for row in payload if isinstance(row, dict)]
            rows.extend(page_rows)
            if len(page_rows) < 100:
                break
            page += 1
        return rows


def _atomic_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        delete=False,
    ) as stream:
        temporary = Path(stream.name)
        json.dump(payload, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build a verified census of only the governed public recruiter "
            "portfolio for compiler fallback use."
        )
    )
    parser.add_argument("--owner", default="GlacierEQ")
    parser.add_argument("--token", default=os.getenv("GITHUB_TOKEN", ""))
    parser.add_argument("--portfolio", type=Path, default=DEFAULT_PORTFOLIO)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        manifest = _load_json(args.portfolio)
        source = GitHubPublicPortfolioSource(args.owner, args.token)
        payload = build_census(
            manifest=manifest,
            owner=args.owner,
            repositories=source.list_all(),
        )
        _atomic_write(args.output, payload)
    except PublicPortfolioCensusError as exc:
        print(f"Public portfolio census failed closed: {exc}")
        return 1
    print(
        json.dumps(
            {
                "state": payload["state"],
                "scope": payload["scope"],
                "repository_count": payload["repository_count"],
                "output": str(args.output),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
