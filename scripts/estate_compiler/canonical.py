from __future__ import annotations

from typing import Any

from discover_experience_graph import digest

from .common import (
    backup_like,
    canonical_assertions,
    flagship_map,
    lineage_graph,
    namespace_assertions,
    restricted_candidate,
    system_id,
)

EXPERIMENT_STATES = {"EXPERIMENT", "PRIVATE_EXPERIMENT"}


def build_canonical_registry(
    native: list[dict[str, Any]],
    flagships: dict[str, Any],
    lineage: dict[str, Any],
    policy: dict[str, Any],
    repository_metadata: dict[str, dict[str, Any]] | None = None,
) -> tuple[dict[str, Any], dict[str, str]]:
    native_names = {str(item.get("repository")) for item in native}
    collapse_roots, support_roots, relationships = lineage_graph(lineage, native_names)
    flagship_by_repo = flagship_map(flagships)
    verified_canonical = canonical_assertions(lineage, native_names)
    verified_namespaces = namespace_assertions(lineage, native_names)
    repo_meta = repository_metadata or {}

    asserted_roots = (
        set(collapse_roots.values())
        | set(support_roots.values())
        | verified_canonical
        | set(flagship_by_repo)
    )
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
        metadata = repo_meta.get(repo, {})
        namespace = verified_namespaces.get(repo)
        promotion_state = metadata.get("promotion_state")

        if namespace == "RESTRICTED_LEGAL":
            disposition, canonical = "RESTRICTED_NAMESPACE", None
        elif repo in collapse_roots:
            disposition, canonical = "LINEAGE_MEMBER", collapse_roots[repo]
        elif repo in support_roots:
            disposition, canonical = "DEPENDENCY_REFERENCE", support_roots[repo]
        elif bool(record.get("archived")) or namespace == "HISTORY":
            disposition, canonical = "HISTORICAL_PROVENANCE", None
        elif backup_like(repo):
            disposition, canonical = "HISTORICAL_PROVENANCE_CANDIDATE", None
        elif promotion_state in EXPERIMENT_STATES:
            disposition, canonical = "EXPERIMENT", None
        elif record.get("visibility") != "public" and restricted_candidate(repo, policy):
            disposition, canonical = "RESTRICTED_NAMESPACE_CANDIDATE", None
        elif repo in asserted_roots:
            disposition, canonical = "DECLARED_CANONICAL_SYSTEM", repo
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
                    "namespace": namespace or "ENGINEERING",
                    "visibility": record.get("visibility"),
                    "declaration_state": disposition,
                    "flagship_level": flagship.get("level") if flagship else None,
                    "flagship_state": flagship.get("state") if flagship else None,
                    "public_surface": flagship.get("public_surface") if flagship else None,
                    "role": flagship.get("role") if flagship else None,
                    "lineage_member_count": sum(
                        1 for root in collapse_roots.values() if root == repo
                    ),
                    "support_reference_count": sum(
                        1 for root in support_roots.values() if root == repo
                    ),
                }
            )
        dispositions.append(
            {
                "repository": repo,
                "namespace": namespace,
                "visibility": record.get("visibility"),
                "disposition": disposition,
                "canonical_repository": canonical,
            }
        )

    for member, root in collapse_roots.items():
        if root in repo_to_system:
            repo_to_system[member] = repo_to_system[root]

    unresolved = [
        item for item in dispositions if item["disposition"] in unresolved_states
    ]
    experiments = [
        item for item in dispositions if item["disposition"] == "EXPERIMENT"
    ]
    restricted = [
        item
        for item in dispositions
        if item["disposition"] in {"RESTRICTED_NAMESPACE", "RESTRICTED_NAMESPACE_CANDIDATE"}
    ]
    result = {
        "schema": "glaciereq.canonical-system-registry.v2",
        "reconciliation_complete": not unresolved,
        "current_declared_canonical_system_count": len(systems),
        "unresolved_native_repository_count": len(unresolved),
        "experiment_repository_count": len(experiments),
        "restricted_namespace_repository_count": len(restricted),
        "truth_boundary": {
            "final_system_count_requires_complete_reconciliation": True,
            "candidate_lineage_never_collapses_repositories": True,
            "dependency_reference_edges_do_not_collapse_lineage": True,
            "history_and_backups_are_provenance_not_accomplishments": True,
            "restricted_namespaces_never_enter_public_projection": True,
        },
        "systems": systems,
        "repository_dispositions": dispositions,
        "lineage_relationships": relationships,
    }
    result["registry_id"] = digest(result)
    return result, repo_to_system
