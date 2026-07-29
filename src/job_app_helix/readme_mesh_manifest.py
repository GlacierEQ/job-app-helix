from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

from google.protobuf import json_format

from . import readme_mesh_pb2
from .readme_mesh import ReadmeMeshError, validate_mesh


def load_mesh(path: Path) -> readme_mesh_pb2.ReadmeMesh:
    """Load an indexed seed manifest and expand it into the Protobuf graph."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("manifest_kind") == "readme_mesh_index":
        payload = _load_index(path, payload)
    if payload.get("manifest_kind") == "readme_mesh_seed":
        payload = _expand_seed(payload)
    mesh = readme_mesh_pb2.ReadmeMesh()
    json_format.ParseDict(payload, mesh, ignore_unknown_fields=False)
    validate_mesh(mesh)
    return mesh


def _load_index(path: Path, index: Mapping[str, object]) -> dict[str, object]:
    seed: dict[str, object] = {
        "manifest_kind": "readme_mesh_seed",
        "schema_version": index["schema_version"],
        "generated_at": index["generated_at"],
        "canonical_repo": index["canonical_repo"],
        "repositories": [],
        "edges": [],
    }
    repositories = seed["repositories"]
    edges = seed["edges"]
    if not isinstance(repositories, list) or not isinstance(edges, list):
        raise ReadmeMeshError("invalid manifest accumulator")
    for relative in index.get("fragments", []):
        fragment_path = path.parent / str(relative)
        fragment = json.loads(fragment_path.read_text(encoding="utf-8"))
        repositories.extend(fragment.get("repositories", []))
        edges.extend(fragment.get("edges", []))
    return seed


def _expand_seed(seed: Mapping[str, object]) -> dict[str, object]:
    repositories = []
    for raw_node in seed.get("repositories", []):
        if not isinstance(raw_node, dict):
            raise ReadmeMeshError("repository seed entries must be objects")
        repository = str(raw_node["repository"])
        branch = str(raw_node.get("default_branch", "main"))
        capabilities = [str(value) for value in raw_node.get("capabilities", [])]
        evidence = list(raw_node.get("evidence", []))
        if not capabilities or not evidence:
            raise ReadmeMeshError(
                f"{repository} seed requires capabilities and evidence"
            )
        purpose = str(raw_node["one_line_purpose"])
        innovation = str(raw_node["innovation"])
        evolution = str(raw_node["evolution"])
        repositories.append(
            {
                "repository": repository,
                "display_name": str(raw_node["display_name"]),
                "one_line_purpose": purpose,
                "innovation": innovation,
                "evolution": evolution,
                "capabilities": capabilities,
                "sections": _sections(
                    repository=repository,
                    branch=branch,
                    purpose=purpose,
                    innovation=innovation,
                    evolution=evolution,
                    capabilities=capabilities,
                    evidence=evidence,
                    canonical_repo=str(seed["canonical_repo"]),
                ),
                "run_commands": list(
                    raw_node.get("run_commands", ["python -m pytest -q"])
                ),
                "readme_url": str(
                    raw_node.get(
                        "readme_url", f"https://github.com/{repository}#readme"
                    )
                ),
                "default_branch": branch,
                "public_portfolio_eligible": bool(
                    raw_node.get("public_portfolio_eligible", True)
                ),
            }
        )
    return {
        "schema_version": seed["schema_version"],
        "generated_at": seed["generated_at"],
        "repositories": repositories,
        "edges": seed.get("edges", []),
        "canonical_repo": seed["canonical_repo"],
    }


def _sections(
    *,
    repository: str,
    branch: str,
    purpose: str,
    innovation: str,
    evolution: str,
    capabilities: list[str],
    evidence: list[object],
    canonical_repo: str,
) -> list[dict[str, object]]:
    return [
        {
            "audience": "RECRUITER",
            "title": "What this project accomplishes",
            "summary": purpose,
            "highlights": [
                (
                    f"It turns {capabilities[0].lower()} into a concrete, "
                    "reviewable software capability."
                ),
                (
                    "The project is small enough to understand quickly and "
                    "structured enough to connect into a larger system."
                ),
                "Claims link to source or tests instead of resume language alone.",
            ],
            "evidence": evidence[:1],
        },
        {
            "audience": "EXPERT",
            "title": "Engineering depth, innovation, and evolution",
            "summary": f"{innovation} {evolution}",
            "highlights": [
                f"Primary engineering capabilities: {', '.join(capabilities)}.",
                (
                    "The repository owns an explicit mesh responsibility rather "
                    "than pretending to be an entire platform."
                ),
                (
                    "Constraints and handoffs are visible through source structure "
                    "and executable tests."
                ),
            ],
            "evidence": evidence[:3],
        },
        {
            "audience": "AI_AGENT",
            "title": "Machine contract and mesh role",
            "summary": (
                f"This repository is a typed node in the {canonical_repo} README "
                "Mesh and uses the glaciereq.readme.v1 Protobuf contract."
            ),
            "highlights": [
                f"Canonical repository identity: {repository}.",
                f"Default branch: {branch}.",
                (
                    "Typed edges describe composition; evidence URLs remain "
                    "stable machine inputs."
                ),
            ],
            "evidence": evidence[-2:],
        },
    ]
