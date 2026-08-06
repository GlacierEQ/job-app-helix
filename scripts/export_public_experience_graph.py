from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from discover_experience_graph import (
    ExperienceGraphError,
    _load_json,
    digest,
    write_atomic,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "artifacts" / "discovery" / "live-experience-graph.json"
DEFAULT_OUTPUT = ROOT / "artifacts" / "discovery" / "public-experience-graph.json"


def build_public_projection(graph: dict[str, Any]) -> dict[str, Any]:
    graph_data = graph.get("graph")
    if not isinstance(graph_data, dict) or not isinstance(graph_data.get("public"), dict):
        raise ExperienceGraphError("Experience graph has no public projection")
    public_graph = graph_data["public"]
    nodes = public_graph.get("nodes")
    if not isinstance(nodes, list):
        raise ExperienceGraphError("Public graph has no nodes")
    public_repositories = {
        node["repository"]
        for node in nodes
        if isinstance(node, dict)
        and node.get("kind") == "repository"
        and isinstance(node.get("repository"), str)
    }

    companies = []
    for company in graph.get("companies", []):
        if not isinstance(company, dict):
            raise ExperienceGraphError("Invalid company in experience graph")
        safe = dict(company)
        observed = safe.get("observed_repositories", [])
        if not isinstance(observed, list):
            raise ExperienceGraphError("Invalid observed company repositories")
        safe_repositories = sorted(
            repository for repository in observed if repository in public_repositories
        )
        safe["observed_repositories"] = safe_repositories
        safe["observed_repository_count"] = len(safe_repositories)
        companies.append(safe)

    paradigms = []
    for paradigm in graph.get("paradigms", []):
        if not isinstance(paradigm, dict):
            raise ExperienceGraphError("Invalid paradigm in experience graph")
        safe = dict(paradigm)
        repositories = safe.get("repositories", [])
        if not isinstance(repositories, list):
            raise ExperienceGraphError("Invalid paradigm repositories")
        safe_repositories = sorted(
            repository for repository in repositories if repository in public_repositories
        )
        safe["repositories"] = safe_repositories
        safe["repository_count"] = len(safe_repositories)
        paradigms.append(safe)

    families = []
    for family in graph.get("family_candidates", []):
        if not isinstance(family, dict):
            raise ExperienceGraphError("Invalid family candidate")
        safe = dict(family)
        repositories = safe.get("repositories", [])
        if not isinstance(repositories, list):
            raise ExperienceGraphError("Invalid family repositories")
        safe_repositories = sorted(
            repository for repository in repositories if repository in public_repositories
        )
        if not safe_repositories:
            continue
        safe["repositories"] = safe_repositories
        safe["repository_count"] = len(safe_repositories)
        families.append(safe)

    flagships = []
    for flagship in graph.get("flagships", []):
        if not isinstance(flagship, dict):
            raise ExperienceGraphError("Invalid flagship in experience graph")
        safe = dict(flagship)
        repository = safe.get("repository")
        if repository not in public_repositories or safe.get("public_surface") != "PUBLIC":
            safe.pop("repository", None)
        flagships.append(safe)

    payload: dict[str, Any] = {
        "schema": "glaciereq.public-experience-graph.v1",
        "source_snapshot_id": graph.get("snapshot_id"),
        "source_digests": graph.get("source_digests", {}),
        "truth_boundary": graph.get("truth_boundary", {}),
        "counts": {
            "public_repositories": len(public_repositories),
            "companies": len(companies),
            "flagships": len(flagships),
            "paradigms": len(paradigms),
            "family_candidates": len(families),
        },
        "companies": companies,
        "flagships": flagships,
        "paradigms": paradigms,
        "family_candidates": families,
        "graph": public_graph,
    }
    serialized = json.dumps(payload, sort_keys=True)
    forbidden = [
        node.get("repository")
        for node in graph_data.get("internal", {}).get("nodes", [])
        if isinstance(node, dict)
        and node.get("kind") == "repository"
        and node.get("visibility") != "public"
        and isinstance(node.get("repository"), str)
    ]
    leaked = sorted(repository for repository in forbidden if repository in serialized)
    if leaked:
        raise ExperienceGraphError(
            f"Private repository identity leaked into public projection: {leaked}"
        )
    payload["snapshot_id"] = digest(payload)
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export a public-safe projection from the internal experience graph"
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        graph = _load_json(args.input.resolve())
        projection = build_public_projection(graph)
        write_atomic(args.output.resolve(), projection)
    except ExperienceGraphError as exc:
        print(f"Public experience graph export failed closed: {exc}")
        return 1
    print(
        "Public experience graph exported: "
        f"snapshot={projection['snapshot_id']} "
        f"repositories={projection['counts']['public_repositories']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
