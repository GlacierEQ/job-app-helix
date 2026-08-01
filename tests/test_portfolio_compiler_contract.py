from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_compiler_is_link_and_generate_only() -> None:
    compiler = load("manifests/portfolio_compiler.json")
    assert compiler["source_of_truth"] == "canonical_child_repository"
    assert compiler["copy_policy"] == "link_and_generate_only"
    assert compiler["stale_on_head_change"] is True
    assert compiler["fail_closed_on_unsupported_claim"] is True


def test_live_links_match_portfolio_inventory() -> None:
    inventory = load("manifests/portfolio_repositories.json")
    links = load("manifests/live_repository_links.json")
    assert set(inventory["workspace_repositories"]) == set(links["repositories"])
    assert len(links["repositories"]) + 1 == inventory["total_repositories"]


def test_forbidden_copy_payloads_are_explicit() -> None:
    compiler = load("manifests/portfolio_compiler.json")
    forbidden = set(compiler["forbidden_current_truth_payloads"])
    assert "copied_child_source_tree" in forbidden
    assert "copied_child_repository_archive" in forbidden
    assert "manually_duplicated_child_readme" in forbidden
    assert "unversioned_child_code_excerpt" in forbidden


def test_required_projection_fields_preserve_quality_separation() -> None:
    compiler = load("manifests/portfolio_compiler.json")
    fields = set(compiler["required_projection_fields"])
    assert "connector_quality_score" in fields
    assert "data_quality_score" in fields
    assert "head_sha" in fields
    assert "provenance_coverage" in fields
