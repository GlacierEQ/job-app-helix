from __future__ import annotations

from job_app_helix.internal_discovery import (
    SCHEMA,
    build_estate_internal_inventory,
    build_repository_inventory,
    classify_path,
    summarize_repository,
)


def _file(path: str, flags: list[str] | None = None):
    return {
        "path": path,
        "blob_sha": ("a" * 40),
        "surface_flags": flags or [],
        "content_state": "ACCOUNTED_NOT_REQUESTED",
    }


def test_hidden_harness_in_unusual_path_is_discovered() -> None:
    item = classify_path(
        "src/strange_corner/anthropic_refusal_replay_harness/runner.py",
        surface_flags=["source"],
    )

    assert "verification_harness" in item["semantic_roles"]
    assert "replay" in item["semantic_roles"]
    assert "MIND_CAPABILITY" in item["architecture_structure_hints"]
    assert item["top_level_group"] == "src"
    assert item["unusual_high_value_location"] is True


def test_repository_inventory_preserves_groups_categories_and_every_path() -> None:
    repo = {
        "repository": "GlacierEQ/demo",
        "position": 7,
        "file_count": 7,
        "all_files_accounted": True,
        "files": [
            _file("README.md", ["readme"]),
            _file("src/core.py", ["source"]),
            _file("src/labs/red_team_harness.py", ["source"]),
            _file("odd/place/evals/judge.py", ["source"]),
            _file("packages/mcp/connector_adapter.ts", ["source"]),
            _file("legal/case/evidence/receipt.json"),
            _file("infra/observability/metrics.py", ["source"]),
        ],
    }

    inventory = build_repository_inventory(repo)

    assert inventory["schema"] == SCHEMA
    assert inventory["structural_discovery_complete"] is True
    assert inventory["classified_path_count"] == 7
    assert len(inventory["files"]) == 7
    assert inventory["group_count"] >= 7
    assert inventory["harness_count"] == 1
    assert inventory["harness_paths"] == ["src/labs/red_team_harness.py"]
    assert inventory["category_counts"]["verification"] >= 2
    assert inventory["category_counts"]["integration"] >= 1
    assert inventory["category_counts"]["domain"] >= 1
    assert inventory["architecture_structure_hint_counts"]["MIND_CAPABILITY"] >= 2
    assert inventory["architecture_structure_hint_counts"]["REALITY_SOURCE"] >= 1
    assert inventory["architecture_structure_hint_counts"]["MATTER_MISSION"] >= 1

    group_paths = {group["path"] for group in inventory["groups"]}
    assert "src/labs" in group_paths
    assert "odd/place/evals" in group_paths
    assert "packages/mcp" in group_paths


def test_compact_summary_keeps_hidden_paths_without_full_private_inventory() -> None:
    repo = {
        "repository": "GlacierEQ/demo",
        "position": 0,
        "file_count": 3,
        "all_files_accounted": True,
        "files": [
            _file("weird/runtime/safety_harness.py", ["source"]),
            _file("tools/agent/runner.py", ["source"]),
            _file("plain.txt"),
        ],
    }

    summary = summarize_repository(repo)

    assert summary["structural_discovery_complete"] is True
    assert summary["harness_count"] == 1
    assert summary["unusual_high_value_count"] >= 1
    assert any(
        item["path"] == "weird/runtime/safety_harness.py"
        for item in summary["high_value_internal_paths"]
    )
    assert "files" not in summary
    assert summary["complete_private_inventory"] == (
        "private crystallization internal-inventory artifact"
    )


def test_estate_inventory_reports_selected_structural_completion() -> None:
    receipt = {
        "schema": "glaciereq.crystallization-source-crawl.v1",
        "receipt_digest": "abc123",
        "accessible_repository_count": 1290,
        "selected_repository_count": 2,
        "selection_start": 100,
        "selection_limit": 2,
        "hourly_shard_index": 2,
        "repositories": [
            {
                "repository": "GlacierEQ/a",
                "position": 100,
                "file_count": 1,
                "all_files_accounted": True,
                "files": [_file("deep/eval/harness.py", ["source"])],
            },
            {
                "repository": "GlacierEQ/b",
                "position": 101,
                "file_count": 1,
                "all_files_accounted": True,
                "files": [_file("src/main.py", ["source"])],
            },
        ],
    }

    inventory = build_estate_internal_inventory(receipt)

    assert inventory["repository_inventory_count"] == 2
    assert inventory["structural_discovery_complete_for_selected_repositories"] is True
    assert inventory["source_receipt_digest"] == "abc123"
    assert inventory["repositories"][0]["harness_count"] == 1


def test_path_labels_are_explicitly_not_behavior_proof() -> None:
    repo = {
        "repository": "GlacierEQ/demo",
        "file_count": 1,
        "all_files_accounted": True,
        "files": [_file("super_powerful_harness.py", ["source"])],
    }
    inventory = build_repository_inventory(repo)
    proof = inventory["proof_boundary"]

    assert proof["path_classification_is_discovery_not_behavior_proof"] is True
    assert proof["architecture_structure_values_are_routing_hints_not_primary_placement"] is True
    assert proof["repository_native_source_remains_implementation_authority"] is True
