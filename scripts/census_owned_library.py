from __future__ import annotations

import argparse
import json
import os
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Protocol

ROOT = Path(__file__).resolve().parents[1]
API_ROOT = "https://api.github.com"
DEFAULT_OUTPUT = ROOT / "artifacts" / "owned-library-census.json"
DEFAULT_PORTFOLIO = ROOT / "manifests" / "portfolio_repositories.json"
DEFAULT_SPINE = ROOT / "manifests" / "library_priority_spine.json"

PUBLIC_CANDIDATE_EXPANSION = {
    "GlacierEQ/Kimi-K3",
    "GlacierEQ/Attention-Residuals",
    "GlacierEQ/ECHO",
    "GlacierEQ/Template",
}


class CensusError(RuntimeError):
    pass


@dataclass(frozen=True)
class RepositoryRecord:
    position: int
    repository: str
    repository_id: int
    visibility: str
    default_branch: str
    archived: bool
    fork: bool
    classification: str


class RepositorySource(Protocol):
    def list_page(self, page: int, per_page: int) -> list[dict[str, Any]]: ...


class GitHubAPI:
    def __init__(self, owner: str, token: str) -> None:
        if not token:
            raise CensusError("GITHUB_TOKEN is required for an exact owner census")
        if not owner:
            raise CensusError("Repository owner is required")
        self.owner = owner
        self.token = token
        self._repository_endpoint: str | None = None
        self._account_type: str | None = None

    def _request_json(self, path: str) -> Any:
        request = urllib.request.Request(
            f"{API_ROOT}{path}",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.token}",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "job-app-helix-owned-library-census",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise CensusError(
                f"GitHub census request failed for {path} with HTTP {exc.code}"
            ) from exc
        except urllib.error.URLError as exc:
            raise CensusError(f"GitHub census request failed for {path}") from exc
        except json.JSONDecodeError as exc:
            raise CensusError(
                f"GitHub census returned malformed JSON for {path}"
            ) from exc

    def _resolve_repository_endpoint(self) -> str:
        if self._repository_endpoint is not None:
            return self._repository_endpoint
        quoted_owner = urllib.parse.quote(self.owner, safe="")
        account = self._request_json(f"/users/{quoted_owner}")
        if not isinstance(account, dict):
            raise CensusError(f"Unable to resolve GitHub account {self.owner}")
        account_type = account.get("type")
        if account_type == "Organization":
            self._repository_endpoint = f"/orgs/{quoted_owner}/repos"
            self._account_type = "Organization"
            return self._repository_endpoint
        if account_type != "User":
            raise CensusError(
                f"Unsupported GitHub account type for {self.owner}: {account_type}"
            )

        authenticated = self._request_json("/user")
        login = authenticated.get("login") if isinstance(authenticated, dict) else None
        if not isinstance(login, str) or login.casefold() != self.owner.casefold():
            raise CensusError(
                f"Exact private census requires authentication as {self.owner}"
            )
        self._repository_endpoint = "/user/repos"
        self._account_type = "User"
        return self._repository_endpoint

    def list_page(self, page: int, per_page: int) -> list[dict[str, Any]]:
        endpoint = self._resolve_repository_endpoint()
        query_values: dict[str, object] = {
            "sort": "created",
            "direction": "asc",
            "per_page": per_page,
            "page": page,
        }
        if self._account_type == "Organization":
            query_values["type"] = "all"
        else:
            query_values["affiliation"] = "owner"
            query_values["visibility"] = "all"
        path = f"{endpoint}?{urllib.parse.urlencode(query_values)}"
        payload = self._request_json(path)
        if not isinstance(payload, list):
            raise CensusError(f"GitHub census page {page} did not return a list")
        return [item for item in payload if isinstance(item, dict)]


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CensusError(f"Unable to load {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise CensusError(f"Expected JSON object at {path}")
    return payload


def _governed_sets(
    portfolio_path: Path,
    spine_path: Path,
    owner: str,
) -> tuple[set[str], set[str]]:
    portfolio = _load_json(portfolio_path)
    workspace = portfolio.get("workspace_repositories")
    if not isinstance(workspace, list):
        raise CensusError("Portfolio manifest has no workspace_repositories list")
    portfolio_repositories = {
        f"{owner}/{name}" for name in workspace if isinstance(name, str)
    }
    portfolio_repositories.add(f"{owner}/job-app-helix")

    spine = _load_json(spine_path)
    entries = spine.get("repositories")
    if not isinstance(entries, list):
        raise CensusError("Priority spine has no repositories list")
    spine_repositories = {
        str(entry.get("repository"))
        for entry in entries
        if isinstance(entry, dict) and isinstance(entry.get("repository"), str)
    }
    return portfolio_repositories, spine_repositories


def classify_repository(
    repository: str,
    *,
    visibility: str,
    archived: bool,
    fork: bool,
    recruiter_portfolio: set[str],
    priority_spine: set[str],
) -> str:
    name = repository.split("/", 1)[-1]
    lowered = name.lower()
    if repository in priority_spine:
        return "PRIORITY_SPINE"
    if repository in recruiter_portfolio:
        return "RECRUITER_PORTFOLIO"
    if archived or lowered.startswith("z-backup-") or lowered.endswith(
        "__public_fork_archive"
    ):
        return "ARCHIVE_BACKUP_OR_FORK"
    if fork:
        return "UPSTREAM_OR_FORK_REVIEW"
    if visibility == "private":
        return "PRIVATE_REVIEW_REQUIRED"
    if repository in PUBLIC_CANDIDATE_EXPANSION:
        return "CANDIDATE_EXPANSION"
    return "UNGOVERNED_PUBLIC_INVENTORY"


def discover(
    source: RepositorySource,
    *,
    owner: str,
    recruiter_portfolio: set[str],
    priority_spine: set[str],
    per_page: int = 100,
) -> list[RepositoryRecord]:
    if per_page < 1 or per_page > 100:
        raise CensusError("per_page must be between 1 and 100")
    owner_prefix = f"{owner}/"
    records: list[RepositoryRecord] = []
    seen: set[str] = set()
    page = 1
    while True:
        items = source.list_page(page, per_page)
        if not items:
            break
        for item in items:
            repository = item.get("full_name")
            repository_id = item.get("id")
            default_branch = item.get("default_branch")
            visibility = item.get("visibility")
            if not isinstance(repository, str) or not repository.startswith(
                owner_prefix
            ):
                raise CensusError(
                    f"Invalid owner repository identity on page {page}: {item}"
                )
            if repository in seen:
                raise CensusError(
                    f"Duplicate repository returned by GitHub: {repository}"
                )
            if not isinstance(repository_id, int):
                raise CensusError(f"Repository {repository} has no numeric id")
            if not isinstance(default_branch, str) or not default_branch:
                raise CensusError(f"Repository {repository} has no default branch")
            if visibility not in {"public", "private", "internal"}:
                raise CensusError(f"Repository {repository} has invalid visibility")
            archived = bool(item.get("archived", False))
            fork = bool(item.get("fork", False))
            seen.add(repository)
            records.append(
                RepositoryRecord(
                    position=len(records),
                    repository=repository,
                    repository_id=repository_id,
                    visibility=visibility,
                    default_branch=default_branch,
                    archived=archived,
                    fork=fork,
                    classification=classify_repository(
                        repository,
                        visibility=visibility,
                        archived=archived,
                        fork=fork,
                        recruiter_portfolio=recruiter_portfolio,
                        priority_spine=priority_spine,
                    ),
                )
            )
        if len(items) < per_page:
            break
        page += 1
    return records


def build_payload(records: list[RepositoryRecord], owner: str) -> dict[str, object]:
    classification_counts = Counter(record.classification for record in records)
    visibility_counts = Counter(record.visibility for record in records)
    native_records = [record for record in records if not record.fork]
    fork_records = [record for record in records if record.fork]
    native_visibility_counts = Counter(record.visibility for record in native_records)
    fork_visibility_counts = Counter(record.visibility for record in fork_records)
    active_native_count = sum(not record.archived for record in native_records)
    archived_native_count = sum(record.archived for record in native_records)
    return {
        "schema": "glaciereq.owned-library-census-receipt.v1",
        "owner": owner,
        "state": "VERIFIED_INVENTORY",
        "distribution": "INTERNAL_FULL_CENSUS",
        "repository_count": len(records),
        "native_repository_count": len(native_records),
        "fork_repository_count": len(fork_records),
        "active_native_repository_count": active_native_count,
        "archived_native_repository_count": archived_native_count,
        "classification_counts": dict(sorted(classification_counts.items())),
        "visibility_counts": dict(sorted(visibility_counts.items())),
        "native_visibility_counts": dict(sorted(native_visibility_counts.items())),
        "fork_visibility_counts": dict(sorted(fork_visibility_counts.items())),
        "archived_count": sum(record.archived for record in records),
        "fork_count": len(fork_records),
        "repositories": [asdict(record) for record in records],
        "nonclaims": [
            "Inventory does not establish authorship or originality.",
            "Inventory does not establish test, build, security, or deployment status.",
            "Native repository count excludes forks but does not itself establish original authorship.",
            "Only governed recruiter-portfolio entries may support resume claims.",
            "The full receipt can contain private names and is not a public artifact.",
        ],
    }


def _write_atomic(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        delete=False,
    ) as stream:
        temp_path = Path(stream.name)
        json.dump(payload, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp_path, path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create an authenticated, non-mutating repository census"
    )
    parser.add_argument("--owner", default="GlacierEQ")
    parser.add_argument("--token", default=os.environ.get("GITHUB_TOKEN", ""))
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--expected-count", type=int)
    parser.add_argument("--expected-native-count", type=int)
    parser.add_argument("--expected-fork-count", type=int)
    parser.add_argument("--portfolio", type=Path, default=DEFAULT_PORTFOLIO)
    parser.add_argument("--priority-spine", type=Path, default=DEFAULT_SPINE)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        recruiter_portfolio, priority_spine = _governed_sets(
            args.portfolio.resolve(),
            args.priority_spine.resolve(),
            args.owner,
        )
        records = discover(
            GitHubAPI(args.owner, args.token),
            owner=args.owner,
            recruiter_portfolio=recruiter_portfolio,
            priority_spine=priority_spine,
        )
        native_count = sum(not record.fork for record in records)
        fork_count = sum(record.fork for record in records)
        if args.expected_count is not None and len(records) != args.expected_count:
            raise CensusError(
                f"Owned-library count drifted: {len(records)} != {args.expected_count}"
            )
        if (
            args.expected_native_count is not None
            and native_count != args.expected_native_count
        ):
            raise CensusError(
                "Owned-library native count drifted: "
                f"{native_count} != {args.expected_native_count}"
            )
        if args.expected_fork_count is not None and fork_count != args.expected_fork_count:
            raise CensusError(
                "Owned-library fork count drifted: "
                f"{fork_count} != {args.expected_fork_count}"
            )
        _write_atomic(args.output.resolve(), build_payload(records, args.owner))
    except CensusError as exc:
        print(f"Owned-library census failed closed: {exc}")
        return 1
    print(
        "Owned-library census VERIFIED: "
        f"repositories={len(records)} native={native_count} forks={fork_count} "
        f"output={args.output.resolve()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
