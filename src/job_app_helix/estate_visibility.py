from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .portfolio_models import PortfolioProgramError


@dataclass(frozen=True)
class EstateCandidate:
    position: int
    repository: str
    repository_id: int
    visibility: str
    default_branch: str
    archived: bool
    fork: bool
    admitted_job_rollout: bool
    route: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _read_object(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PortfolioProgramError(f"cannot load {label} {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise PortfolioProgramError(f"{label} must contain a JSON object")
    return payload


def _admitted_repositories(path: Path, owner: str) -> set[str]:
    payload = _read_object(path, "rollout projection")
    if payload.get("is_full_estate_inventory") is not False:
        raise PortfolioProgramError(
            "rollout projection must explicitly declare is_full_estate_inventory=false"
        )
    if payload.get("scope") != "ADMITTED_JOB_ENGINEERING_ROLLOUT_PROJECTION":
        raise PortfolioProgramError("rollout projection has an invalid scope declaration")
    workspace = payload.get("workspace_repositories")
    root = payload.get("portfolio_root")
    if not isinstance(workspace, list) or not isinstance(root, str):
        raise PortfolioProgramError("rollout projection is missing repository identities")
    repositories = {
        f"{owner}/{name}"
        for name in workspace
        if isinstance(name, str) and name.strip()
    }
    repositories.add(f"{owner}/{root}")
    expected = payload.get("total_repositories")
    if expected != len(repositories):
        raise PortfolioProgramError("rollout projection cardinality does not match identities")
    return repositories


def _route(row: dict[str, Any], admitted: bool) -> str:
    if admitted:
        return "ADMITTED_JOB_ROLLOUT"
    if bool(row.get("archived")):
        return "DISCOVERED_ARCHIVE_DONOR"
    if bool(row.get("fork")):
        return "DISCOVERED_UPSTREAM_DONOR"
    if row.get("visibility") == "private":
        return "DISCOVERED_PRIVATE_CANDIDATE"
    return "DISCOVERED_PUBLIC_CANDIDATE"


def compile_estate_visibility(
    *,
    census_path: Path,
    rollout_projection_path: Path,
) -> tuple[EstateCandidate, ...]:
    """Compile every discovered owner repository into a relevance-analysis queue.

    Discovery is authoritative for scope. Rollout membership only changes the route.
    No repository is dropped because it is private, archived, a fork, or outside the
    current job rollout projection.
    """

    census = _read_object(census_path, "full-estate census")
    if census.get("distribution") != "INTERNAL_FULL_CENSUS":
        raise PortfolioProgramError("full-estate census must be an internal receipt")
    if census.get("visibility_policy") != "DISCOVER_ALL_ROUTE_AFTER":
        raise PortfolioProgramError("full-estate census does not enforce discover-all routing")
    if census.get("hidden_repository_count") != 0:
        raise PortfolioProgramError("full-estate census reports hidden repositories")

    owner = census.get("owner")
    rows = census.get("repositories")
    declared_count = census.get("repository_count")
    if not isinstance(owner, str) or not owner:
        raise PortfolioProgramError("full-estate census is missing owner")
    if not isinstance(rows, list):
        raise PortfolioProgramError("full-estate census is missing repositories")
    if declared_count != len(rows):
        raise PortfolioProgramError("full-estate census cardinality does not match rows")

    admitted = _admitted_repositories(rollout_projection_path, owner)
    candidates: list[EstateCandidate] = []
    seen: set[str] = set()
    for index, raw in enumerate(rows):
        if not isinstance(raw, dict):
            raise PortfolioProgramError(f"census.repositories[{index}] must be an object")
        repository = raw.get("repository")
        repository_id = raw.get("repository_id")
        visibility = raw.get("visibility")
        default_branch = raw.get("default_branch")
        if not isinstance(repository, str) or not repository.startswith(f"{owner}/"):
            raise PortfolioProgramError(f"invalid repository identity at census row {index}")
        if repository in seen:
            raise PortfolioProgramError(f"duplicate repository in full-estate census: {repository}")
        if not isinstance(repository_id, int):
            raise PortfolioProgramError(f"{repository}: repository_id must be an integer")
        if visibility not in {"public", "private", "internal"}:
            raise PortfolioProgramError(f"{repository}: invalid visibility")
        if not isinstance(default_branch, str) or not default_branch:
            raise PortfolioProgramError(f"{repository}: default branch is missing")
        seen.add(repository)
        is_admitted = repository in admitted
        candidates.append(
            EstateCandidate(
                position=index,
                repository=repository,
                repository_id=repository_id,
                visibility=visibility,
                default_branch=default_branch,
                archived=bool(raw.get("archived")),
                fork=bool(raw.get("fork")),
                admitted_job_rollout=is_admitted,
                route=_route(raw, is_admitted),
            )
        )

    if len(candidates) != declared_count:
        raise PortfolioProgramError("estate visibility compiler dropped repositories")
    return tuple(candidates)


def estate_visibility_payload(candidates: tuple[EstateCandidate, ...]) -> dict[str, Any]:
    route_counts: dict[str, int] = {}
    for candidate in candidates:
        route_counts[candidate.route] = route_counts.get(candidate.route, 0) + 1
    return {
        "schema": "glaciereq.estate-visibility-queue.v1",
        "distribution": "INTERNAL_PRIVATE_STATE",
        "mission": "Expose the complete owned estate to relevance analysis before rollout admission.",
        "repository_count": len(candidates),
        "hidden_repository_count": 0,
        "route_counts": dict(sorted(route_counts.items())),
        "invariants": {
            "discovery_precedes_admission": True,
            "every_discovered_repository_has_a_route": True,
            "rollout_membership_is_not_existence": True,
            "private_archive_and_fork_states_do_not_hide_repositories": True,
        },
        "repositories": [candidate.to_dict() for candidate in candidates],
    }
