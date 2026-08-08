from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "discover_experience_graph.py"


def _load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("discover_experience_graph", SCRIPT)
    if spec is None or spec.loader is None:
        raise AssertionError(f"Unable to load {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(spec.name, None)
    return module


def _record(
    repository: str,
    *,
    visibility: str = "public",
    classification: str = "UNGOVERNED_PUBLIC_INVENTORY",
) -> dict[str, Any]:
    return {
        "repository": repository,
        "visibility": visibility,
        "classification": classification,
    }


def _policy() -> dict[str, Any]:
    return {
        "schema": "glaciereq.experience-graph-policy.v1",
        "minimum_family_size": 2,
        "generic_prefixes": ["ai", "agent", "project", "the"],
        "company_alias_overrides": {"openai": ["openai"]},
        "personal_paradigm_overrides": {
            "apex": {
                "display_name": "APEX",
                "aliases": ["apex"],
            }
        },
        "unknown_family_policy": "DISCOVERED_UNCLASSIFIED_REVIEW_REQUIRED",
    }


def _companies() -> dict[str, dict[str, Any]]:
    return {
        "openai": {
            "company_id": "openai",
            "display_name": "OpenAI",
            "track_state": "MAPPED_NOT_RECRUITER_READY",
            "non_affiliation": "Independent work; no affiliation is claimed.",
            "repositories": [
                {
                    "repository": "GlacierEQ/openai-reasoning-kv-sentinel",
                    "skill_innovation_level": "L3",
                    "promotion_state": "REFERENCE_ONLY",
                    "visibility": "public",
                    "inventory_scope": "HELIX_ADMITTED",
                    "provenance_state": "ORIGINAL_CANDIDATE",
                    "company_id": "openai",
                }
            ],
        },
        "nasa": {
            "company_id": "nasa",
            "display_name": "NASA",
            "track_state": "MAPPED_NOT_RECRUITER_READY",
            "non_affiliation": "Independent work; no affiliation is claimed.",
            "repositories": [],
        },
    }


def _repository_metadata() -> dict[str, dict[str, Any]]:
    return {
        "GlacierEQ/openai-reasoning-kv-sentinel": {
            "repository": "GlacierEQ/openai-reasoning-kv-sentinel",
            "skill_innovation_level": "L3",
            "promotion_state": "REFERENCE_ONLY",
            "visibility": "public",
            "inventory_scope": "HELIX_ADMITTED",
            "provenance_state": "ORIGINAL_CANDIDATE",
            "company_id": "openai",
        }
    }


def _flagships() -> dict[str, Any]:
    return {
        "schema": "glaciereq.flagship-registry.v2",
        "flagships": [
            {
                "system_id": "akos",
                "repository": "GlacierEQ/AKOS",
                "level": "L5",
                "state": "PROMOTED",
                "public_surface": "PUBLIC",
                "role": "Authority runtime",
            },
            {
                "system_id": "private_authority",
                "repository": "GlacierEQ/apex-secret",
                "level": "L2",
                "state": "PRIVATE_REFERENCE",
                "public_surface": "SANITIZED_CARD_ONLY",
                "role": "Private architecture",
            },
        ],
    }


def _census() -> dict[str, Any]:
    return {
        "schema": "glaciereq.owned-library-census-receipt.v1",
        "repositories": [
            _record("GlacierEQ/openai-reasoning-kv-sentinel"),
            _record("GlacierEQ/futuregrid-control"),
            _record("GlacierEQ/futuregrid-mesh"),
            _record("GlacierEQ/APEX-control-plane"),
            _record(
                "GlacierEQ/apex-secret",
                visibility="private",
                classification="PRIVATE_REVIEW_REQUIRED",
            ),
            _record(
                "GlacierEQ/AKOS",
                classification="PRIORITY_SPINE",
            ),
        ],
    }


def test_unseen_repository_family_is_discovered_without_code_change() -> None:
    module = _load_module()
    graph = module.build_experience_graph(
        census=_census(),
        companies=_companies(),
        repository_metadata=_repository_metadata(),
        flagships=_flagships(),
        policy=_policy(),
    )

    candidates = {item["family_id"]: item for item in graph["family_candidates"]}
    assert candidates["futuregrid"]["repository_count"] == 2
    assert candidates["futuregrid"]["state"] == (
        "DISCOVERED_UNCLASSIFIED_REVIEW_REQUIRED"
    )


def test_existing_company_catalog_is_reproduced_and_zero_repo_target_survives() -> None:
    module = _load_module()
    graph = module.build_experience_graph(
        census=_census(),
        companies=_companies(),
        repository_metadata=_repository_metadata(),
        flagships=_flagships(),
        policy=_policy(),
    )

    companies = {item["company_id"]: item for item in graph["companies"]}
    assert companies["openai"]["observed_repository_count"] == 1
    assert companies["openai"]["catalog_repository_count"] == 1
    assert companies["nasa"]["observed_repository_count"] == 0
    assert graph["truth_boundary"]["company_mapping_does_not_imply_affiliation"]


def test_personal_paradigm_is_independent_from_company_mapping() -> None:
    module = _load_module()
    graph = module.build_experience_graph(
        census=_census(),
        companies=_companies(),
        repository_metadata=_repository_metadata(),
        flagships=_flagships(),
        policy=_policy(),
    )

    paradigms = {item["paradigm_id"]: item for item in graph["paradigms"]}
    assert paradigms["apex"]["repository_count"] == 2
    edges = graph["graph"]["internal"]["edges"]
    assert {
        edge["source"]
        for edge in edges
        if edge["target"] == "paradigm:apex"
    } == {
        "repo:GlacierEQ/APEX-control-plane",
        "repo:GlacierEQ/apex-secret",
    }


def test_public_graph_omits_private_repository_identity() -> None:
    module = _load_module()
    graph = module.build_experience_graph(
        census=_census(),
        companies=_companies(),
        repository_metadata=_repository_metadata(),
        flagships=_flagships(),
        policy=_policy(),
    )

    public_json = json.dumps(graph["graph"]["public"], sort_keys=True)
    assert "GlacierEQ/apex-secret" not in public_json
    assert "private_authority" in public_json
    private_flagship = next(
        node
        for node in graph["graph"]["public"]["nodes"]
        if node["id"] == "flagship:private_authority"
    )
    assert "repository" not in private_flagship


def test_snapshot_is_deterministic_for_same_sources() -> None:
    module = _load_module()
    kwargs = {
        "census": _census(),
        "companies": _companies(),
        "repository_metadata": _repository_metadata(),
        "flagships": _flagships(),
        "policy": _policy(),
    }
    first = module.build_experience_graph(**kwargs)
    second = module.build_experience_graph(**kwargs)

    assert first == second
    assert first["snapshot_id"] == module.digest(
        {key: value for key, value in first.items() if key != "snapshot_id"}
    )


def test_company_catalog_loader_rejects_duplicate_cross_company_mapping(
    tmp_path: Path,
) -> None:
    module = _load_module()
    first = {
        "schema": "glaciereq.company-dossiers-shard.v2",
        "companies": [
            {
                "company_id": "one",
                "display_name": "One",
                "repositories": [["GlacierEQ/shared", "L2", "REFERENCE_ONLY"]],
            }
        ],
    }
    second = {
        "schema": "glaciereq.company-dossiers-shard.v2",
        "companies": [
            {
                "company_id": "two",
                "display_name": "Two",
                "repositories": [["GlacierEQ/shared", "L2", "REFERENCE_ONLY"]],
            }
        ],
    }
    (tmp_path / "one.json").write_text(json.dumps(first), encoding="utf-8")
    (tmp_path / "two.json").write_text(json.dumps(second), encoding="utf-8")
    index = {
        "repository_record_columns": [
            "repository",
            "skill_innovation_level",
            "promotion_state",
        ],
        "dossier_files": ["one.json", "two.json"],
    }

    with pytest.raises(module.ExperienceGraphError, match="multiple companies"):
        module.load_company_catalog(tmp_path, index)
