from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "discover_experience_graph.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("discover_experience_graph", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(spec.name, None)
    return module


def _graph():
    module = _load()
    census = {
        "repositories": [
            {"repository": "GlacierEQ/openai-reasoning-kv-sentinel", "visibility": "public", "classification": "PUBLIC"},
            {"repository": "GlacierEQ/futuregrid-control", "visibility": "public", "classification": "PUBLIC"},
            {"repository": "GlacierEQ/futuregrid-mesh", "visibility": "public", "classification": "PUBLIC"},
            {"repository": "GlacierEQ/APEX-control-plane", "visibility": "public", "classification": "PUBLIC"},
            {"repository": "GlacierEQ/apex-secret", "visibility": "private", "classification": "PRIVATE"},
        ]
    }
    companies = {
        "openai": {
            "company_id": "openai",
            "display_name": "OpenAI",
            "track_state": "MAPPED",
            "non_affiliation": "Independent work; no affiliation is claimed.",
            "repositories": [{"repository": "GlacierEQ/openai-reasoning-kv-sentinel"}],
        }
    }
    metadata = {
        "GlacierEQ/openai-reasoning-kv-sentinel": {
            "repository": "GlacierEQ/openai-reasoning-kv-sentinel",
            "company_id": "openai",
            "promotion_state": "REFERENCE_ONLY",
            "skill_innovation_level": "L3",
            "provenance_state": "ORIGINAL_CANDIDATE",
        }
    }
    flagships = {
        "flagships": [
            {"system_id": "private-authority", "repository": "GlacierEQ/apex-secret", "level": "L4", "state": "PRIVATE_REFERENCE", "public_surface": "SANITIZED_CARD_ONLY", "role": "Private architecture"}
        ]
    }
    policy = {
        "minimum_family_size": 2,
        "generic_prefixes": ["ai", "agent", "project", "the"],
        "company_alias_overrides": {"openai": ["openai"]},
        "personal_paradigm_overrides": {"apex": {"display_name": "APEX", "aliases": ["apex"]}},
        "unknown_family_policy": "DISCOVERED_UNCLASSIFIED_REVIEW_REQUIRED",
    }
    return module, module.build_experience_graph(census=census, companies=companies, repository_metadata=metadata, flagships=flagships, policy=policy)


def test_discovers_unseen_repository_family_without_code_change() -> None:
    _, graph = _graph()
    candidates = {item["family_id"]: item for item in graph["family_candidates"]}
    assert candidates["futuregrid"]["repository_count"] == 2


def test_public_projection_omits_private_repository_identity() -> None:
    _, graph = _graph()
    rendered = str(graph["graph"]["public"])
    assert "GlacierEQ/apex-secret" not in rendered
    private_flagship = next(node for node in graph["graph"]["public"]["nodes"] if node["id"] == "flagship:private-authority")
    assert "repository" not in private_flagship


def test_company_and_paradigm_edges_are_independent() -> None:
    _, graph = _graph()
    edges = graph["graph"]["internal"]["edges"]
    assert any(edge["target"] == "company:openai" for edge in edges)
    assert any(edge["target"] == "paradigm:apex" for edge in edges)


def test_snapshot_is_deterministic() -> None:
    module, first = _graph()
    _, second = _graph()
    assert first == second
    assert first["snapshot_id"] == module.digest({key: value for key, value in first.items() if key != "snapshot_id"})
