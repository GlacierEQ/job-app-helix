from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

from google.protobuf import json_format

from . import readme_mesh_pb2
from .readme_mesh import ReadmeMeshError, validate_mesh


def load_mesh(path: Path) -> readme_mesh_pb2.ReadmeMesh:
    """Load an indexed legacy seed manifest into a non-governing Protobuf graph."""
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
                    mesh_root=str(seed["canonical_repo"]),
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
        "edges": _migrate_legacy_edges(seed.get("edges", [])),
        "canonical_repo": seed["canonical_repo"],
    }


def _migrate_legacy_edges(raw_edges: object) -> list[object]:
    """Remove project-governor semantics before legacy mesh serialization.

    The v1 source fragments retain historical relation names for provenance. The
    active machine projection converts every historical GOVERNED_BY edge into a
    verification relationship before Protobuf/ProtoJSON generation, so structured
    consumers cannot receive the retired authority semantic.
    """
    if not isinstance(raw_edges, list):
        raise ReadmeMeshError("mesh edges must be a list")
    migrated: list[object] = []
    for raw_edge in raw_edges:
        if not isinstance(raw_edge, dict):
            migrated.append(raw_edge)
            continue
        edge = dict(raw_edge)
        if edge.get("relation") == "GOVERNED_BY":
            edge["relation"] = "VERIFIES"
            original = str(edge.get("value", "")).strip()
            edge["value"] = (
                "Legacy governance edge migrated to evidence/execution verification; "
                "this grants no project-direction authority. " + original
            ).strip()
        migrated.append(edge)
    return migrated


def _sections(
    *,
    repository: str,
    branch: str,
    purpose: str,
    innovation: str,
    evolution: str,
    capabilities: list[str],
    evidence: list[object],
    mesh_root: str,
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
                    "The project is structured for rapid inspection while remaining "
                    "free to expand into the strongest coherent architecture."
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
                    "The repository owns an explicit mesh responsibility while "
                    "remaining composable with the wider APEX system."
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
                f"This repository is a typed node in the legacy {mesh_root} README "
                "Mesh public projection and uses the glaciereq.readme.v1 Protobuf "
                "wire contract. Project direction remains operator-owned."
            ),
            "highlights": [
                f"Repository identity: {repository}.",
                f"Default branch: {branch}.",
                (
                    "Typed edges describe composition or verification; evidence URLs "
                    "remain stable machine inputs."
                ),
            ],
            "evidence": evidence[-2:],
        },
    ]
