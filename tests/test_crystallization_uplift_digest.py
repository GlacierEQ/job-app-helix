from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "build_crystallization_uplift_digest.py"
SPEC = importlib.util.spec_from_file_location("crystallization_uplift_digest", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _repo(name: str, position: int, **overrides):
    value = {
        "repository": name,
        "position": position,
        "status": "UNDERSTOOD_PARTIAL_SOURCE",
        "fork": False,
        "archived": False,
        "file_count": 10,
        "all_files_accounted": True,
        "text_inspected_count": 5,
        "unresolved_content_count": 0,
        "text_fetch_failure_count": 0,
        "function_definition_count": 4,
        "surface_counts": {},
        "scaffold_findings": [],
        "incomplete_findings": [],
        "files": [],
    }
    value.update(overrides)
    return value


def _file(path: str, flags: list[str] | None = None):
    return {
        "path": path,
        "blob_sha": "f" * 40,
        "size": 42,
        "likely_text": True,
        "surface_flags": flags or [],
        "content_state": "ACCOUNTED_NOT_REQUESTED",
    }


def test_digest_routes_implementation_gaps_before_cleaner_repositories():
    receipt = {
        "schema": MODULE.SOURCE_SCHEMA,
        "receipt_digest": "abc123",
        "content_mode": "priority",
        "accessible_repository_count": 2,
        "selected_repository_count": 2,
        "repository_crawled_count": 2,
        "repository_failure_count": 0,
        "selection_start": 50,
        "selection_limit": 50,
        "hourly_shard_index": 1,
        "repositories": [
            _repo(
                "GlacierEQ/lift-me",
                50,
                status="INCOMPLETE",
                unresolved_content_count=2,
                surface_counts={"execution": 2, "test": 1},
                scaffold_findings=[{"path": "src/core.py"}],
            ),
            _repo("GlacierEQ/inspect-me", 51),
        ],
    }

    digest = MODULE.build_digest(receipt)

    assert digest["queue_count"] == 2
    assert digest["queue"][0]["repository"] == "GlacierEQ/lift-me"
    assert digest["queue"][0]["lane"] == "LIFT_IMPLEMENTATION_GAPS"
    assert digest["raw_receipt_policy"]["promotion_to_monolith_main"] is False
    assert "files" not in digest["queue"][0]
    assert "internal_discovery" in digest["queue"][0]


def test_forks_and_archives_are_preserved_as_lineage_work_not_code_rewrites():
    receipt = {
        "schema": MODULE.SOURCE_SCHEMA,
        "repositories": [
            _repo("GlacierEQ/fork", 1, fork=True),
            _repo("GlacierEQ/archive", 2, archived=True),
        ],
    }

    digest = MODULE.build_digest(receipt)
    lanes = {item["repository"]: item["lane"] for item in digest["queue"]}

    assert lanes["GlacierEQ/fork"] == "VERIFY_FORK_DELTA_OR_UPSTREAM"
    assert lanes["GlacierEQ/archive"] == "VERIFY_ARCHIVE_OR_SUCCESSOR"


def test_digest_never_promotes_source_observation_to_runtime_proof():
    digest = MODULE.build_digest(
        {
            "schema": MODULE.SOURCE_SCHEMA,
            "repositories": [_repo("GlacierEQ/runtime", 3, surface_counts={"execution": 1})],
        }
    )

    assert digest["queue"][0]["lane"] == "VERIFY_RUNTIME_AND_LIFT"
    assert digest["proof_boundary"]["source_observation_is_not_runtime_proof"] is True
    assert digest["proof_boundary"]["path_classification_is_discovery_not_behavior_proof"] is True


def test_hidden_harness_and_unusual_internal_raise_discovery_signal():
    repo = _repo(
        "GlacierEQ/hidden-gems",
        9,
        file_count=4,
        files=[
            _file("README.md", ["readme"]),
            _file("src/ordinary.py", ["source"]),
            _file("weird/deep/red_team_harness/replay.py", ["source"]),
            _file("packages/agent/tools/mcp_adapter.py", ["source"]),
        ],
    )
    digest = MODULE.build_digest(
        {
            "schema": MODULE.SOURCE_SCHEMA,
            "receipt_digest": "discovery",
            "accessible_repository_count": 1290,
            "selected_repository_count": 1,
            "repository_crawled_count": 1,
            "repository_failure_count": 0,
            "repositories": [repo],
        }
    )

    item = digest["queue"][0]
    internal = item["internal_discovery"]
    assert "HARNESS_DISCOVERED" in item["signals"]
    assert "UNUSUAL_HIGH_VALUE_LOCATION" in item["signals"]
    assert internal["harness_count"] == 1
    assert internal["structural_discovery_complete"] is True
    assert any(
        path["path"] == "weird/deep/red_team_harness/replay.py"
        for path in internal["high_value_internal_paths"]
    )
    assert digest["internal_discovery_coverage"]["harness_count"] == 1
    assert digest["internal_discovery_coverage"]["repository_count"] == 1
