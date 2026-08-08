from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def _load_exporter() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "export_public_experience_graph",
        SCRIPTS / "export_public_experience_graph.py",
    )
    if spec is None or spec.loader is None:
        raise AssertionError("Unable to load public experience graph exporter")
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(SCRIPTS))
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(spec.name, None)
        sys.path.remove(str(SCRIPTS))
    return module


def _graph() -> dict[str, object]:
    return {
        "snapshot_id": "internal-snapshot",
        "source_digests": {"census": "a" * 64},
        "truth_boundary": {
            "private_repository_names_omitted_from_public_graph": True
        },
        "companies": [
            {
                "company_id": "example",
                "display_name": "Example",
                "catalog_repository_count": 2,
                "observed_repository_count": 2,
                "observed_repositories": [
                    "GlacierEQ/public-system",
                    "GlacierEQ/private-system",
                ],
            }
        ],
        "flagships": [
            {
                "system_id": "public",
                "repository": "GlacierEQ/public-system",
                "public_surface": "PUBLIC",
            },
            {
                "system_id": "private",
                "repository": "GlacierEQ/private-system",
                "public_surface": "SANITIZED_CARD_ONLY",
            },
        ],
        "paradigms": [
            {
                "paradigm_id": "example",
                "display_name": "Example",
                "repository_count": 2,
                "repositories": [
                    "GlacierEQ/public-system",
                    "GlacierEQ/private-system",
                ],
            }
        ],
        "family_candidates": [
            {
                "family_id": "system",
                "repository_count": 2,
                "repositories": [
                    "GlacierEQ/public-system",
                    "GlacierEQ/private-system",
                ],
            }
        ],
        "graph": {
            "internal": {
                "nodes": [
                    {
                        "id": "repo:GlacierEQ/public-system",
                        "kind": "repository",
                        "repository": "GlacierEQ/public-system",
                        "visibility": "public",
                    },
                    {
                        "id": "repo:GlacierEQ/private-system",
                        "kind": "repository",
                        "repository": "GlacierEQ/private-system",
                        "visibility": "private",
                    },
                ],
                "edges": [],
            },
            "public": {
                "nodes": [
                    {
                        "id": "repo:GlacierEQ/public-system",
                        "kind": "repository",
                        "repository": "GlacierEQ/public-system",
                        "visibility": "public",
                    }
                ],
                "edges": [],
            },
        },
    }


def test_public_export_removes_private_repository_names_everywhere() -> None:
    module = _load_exporter()
    projection = module.build_public_projection(_graph())
    serialized = json.dumps(projection, sort_keys=True)

    assert "GlacierEQ/private-system" not in serialized
    assert "GlacierEQ/public-system" in serialized
    assert projection["companies"][0]["observed_repository_count"] == 1
    assert projection["paradigms"][0]["repository_count"] == 1
    assert projection["family_candidates"][0]["repository_count"] == 1
    private_flagship = next(
        item for item in projection["flagships"] if item["system_id"] == "private"
    )
    assert "repository" not in private_flagship


def test_public_export_fails_closed_when_private_identity_survives() -> None:
    module = _load_exporter()
    graph = _graph()
    graph["companies"][0]["display_name"] = "GlacierEQ/private-system"

    with pytest.raises(module.ExperienceGraphError, match="identity leaked"):
        module.build_public_projection(graph)
