from __future__ import annotations

from typing import Any

from discover_experience_graph import digest

from .common import (
    backup_like,
    flagship_map,
    lineage_roots,
    restricted_candidate,
    system_id,
)


def build_canonical_registry(
    native: list[dict[str, Any]],
    flagships: dict[str, Any],
    lineage: dict[str, Any],
    policy: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, str]]:
    native_names = {str(item.get("repository")) for item in native}
    roots, relationships = lineage_roots(lineage, native_names)
    flagship_by_repo = flagship_map(flagships)
    asserted_roots = set(roots.values())
    repo_to_system: dict[str, str] = {}
    systems: list[dict[str, Any]] = []
    dispositions: list[dict[str, Any]] = []
    unresolved_states = {
        "HISTORICAL_PROVENANCE_CANDIDATE",
        "RESTRICTED_NAMESPACE_CANDIDATE",
        "GOVERNED_UNRECONCILED",
        "UNRESOLVED_REVIEW",
    }
    for record in sorted(native, key=lambda item: str(item.get("repository"))):
        repo = str(record.get("repository"))
        if repo in roots:
            disposition, canonical = "LINEAGE_MEMBER", roots[repo]
        elif bool(record.get("archived")):
            disposition, canonical = "HISTORICAL_PROVENANCE", None
        elif backup_like(repo):
            disposition, canonical = "HISTORICAL_PROVENANCE_CANDIDATE", None
        elif record.get("visibility") != "public" and restricted_candidate(repo, policy):
            disposition, canonical = "RESTRICTED_NAMESPACE_CANDIDATE", None
        elif repo in flagship_by_repo:
            disposition, canonical = "DECLARED_CANONICAL_SYSTEM", repo
        elif repo in asserted_roots:
            disposition, canonical = "LINEAGE_ASSERTED_CANONICAL_SYSTEM", repo
        elif record.get("classification") in {"PRIORITY_SPINE", "RECRUITER_PORTFOLIO"}:
            disposition, canonical = "GOVERNED_UNRECONCILED", None
        else:
            disposition, canonical = "UNRESOLVED_REVIEW", None

        if canonical == repo:
            flagship = flagship_by_repo.get(repo)
            sid = system_id(repo, flagship)
            repo_to_system[repo] = sid
            systems.append(
                {
                    "system_id": sid,
                    "canonical_repository": repo,
                    "visibility": record.get("visibility"),
                    "declaration_state": disposition,
                    "flagship_level": flagship.get("level") if flagship else None,
                    "flagship_state": flagship.get("state") if flagship else None,
                    "public_surface": flagship.get("public_surface") if flagship else None,
                    "role": flagship.get("role") if flagship else None,
                    "lineage_member_count": sum(
                        1 for root in roots.values() if root == repo
                    ),
                }
            )
        dispositions.append(
            {
                "repository": repo,
                "visibility": record.get("visibility"),
                "disposition": disposition,
                "canonical_repository": canonical,
            }
        )

    for member, root in roots.items():
        if root in repo_to_system:
            repo_to_system[member] = repo_to_system[root]
    unresolved = [
        item for item in dispositions if item["disposition"] in unresolved_states
    ]
    result = {
        "schema": "glaciereq.canonical-system-registry.v1",
        "reconciliation_complete": not unresolved,
        "current_declared_canonical_system_count": len(systems),
        "unresolved_native_repository_count": len(unresolved),
        "truth_boundary": {
            "final_system_count_requires_complete_reconciliation": True,
            "candidate_lineage_never_collapses_repositories": True,
            "history_and_backups_are_provenance_not_accomplishments": True,
        },
        "systems": systems,
        "repository_dispositions": dispositions,
        "lineage_relationships": relationships,
    }
    result["registry_id"] = digest(result)
    return result, repo_to_system
