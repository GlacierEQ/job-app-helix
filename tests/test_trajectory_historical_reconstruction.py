from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "reconstruct_trajectory_checkpoint.py"
SCHEDULE = ROOT / "machine" / "trajectory" / "2026_schedule.json"
HST = ZoneInfo("Pacific/Honolulu")


def load_module():
    spec = importlib.util.spec_from_file_location("trajectory_reconstruction", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_historical_gate_rejects_contemporary_dates() -> None:
    module = load_module()
    schedule = json.loads(SCHEDULE.read_text(encoding="utf-8"))
    index, entry = module.scheduled_historical_entry(schedule, "2026-08-10")
    assert index == 16
    assert entry["capture_kind"] == "historical_reconstruction"
    with pytest.raises(SystemExit, match="contemporary"):
        module.scheduled_historical_entry(schedule, "2026-08-15")


def test_cutoff_is_explicit_hst_end_of_day_by_default() -> None:
    module = load_module()
    cutoff = module.cutoff_iso("2026-07-25", "23:59:59")
    assert cutoff == "2026-07-25T23:59:59-10:00"


def test_survivor_head_reconstruction_never_relabels_current_metadata() -> None:
    module = load_module()
    repositories = [
        {
            "nameWithOwner": "GlacierEQ/old",
            "visibility": "PRIVATE",
            "isArchived": True,
            "isFork": False,
            "createdAt": "2026-01-02T00:00:00Z",
            "updatedAt": "2026-08-01T00:00:00Z",
            "defaultBranchRef": {
                "name": "main",
                "target": {
                    "history": {
                        "nodes": [
                            {
                                "oid": "a" * 40,
                                "committedDate": "2026-07-01T05:00:00Z",
                            }
                        ]
                    }
                },
            },
        },
        {
            "nameWithOwner": "GlacierEQ/future",
            "visibility": "PUBLIC",
            "isArchived": False,
            "isFork": False,
            "createdAt": "2026-08-02T00:00:00Z",
            "updatedAt": "2026-08-02T00:00:00Z",
            "defaultBranchRef": None,
        },
    ]
    cutoff = datetime(2026, 7, 25, 23, 59, 59, tzinfo=HST)
    rows, excluded = module.reconstruct_survivor_heads(repositories, cutoff)
    assert [row["repository"] for row in rows] == ["GlacierEQ/old"]
    assert excluded == ["GlacierEQ/future"]
    assert rows[0]["head_sha"] == "a" * 40
    assert rows[0]["evidence_class"] == "bounded_current_default_branch_lineage"
    assert "current default-branch name" in rows[0]["branch_semantics"]
    assert "not asserted historical metadata" in rows[0]["metadata_semantics"]


def test_bounded_inventory_refuses_fake_exact_historical_counts() -> None:
    module = load_module()
    inventory = module.bounded_inventory(
        [
            {"visibility": "private"},
            {"visibility": "public"},
            {"visibility": "private"},
        ]
    )
    assert inventory["owned_repository_count"] is None
    assert inventory["archived_count"] is None
    assert inventory["bounded_survivor_repository_count"] == 3
    assert inventory["exact_historical_repository_count_known"] is False
    assert inventory["deleted_or_transferred_repository_gap_resolved"] is False
    assert inventory["visibility_counts"] == {"private": 2, "public": 1}


def test_path_scope_matching_does_not_confuse_prefixes() -> None:
    module = load_module()
    assert module.path_matches("status/a.json", "status")
    assert module.path_matches("README.md", "README.md")
    assert not module.path_matches("status-old/a.json", "status")


def test_authority_head_can_be_absent_before_helix_birth() -> None:
    module = load_module()
    assert module.authority_head([]) is None
    assert (
        module.authority_head(
            [
                {
                    "repository": "GlacierEQ/job-app-helix",
                    "head_sha": "f" * 40,
                }
            ]
        )
        == "f" * 40
    )


def test_unresolved_dimensions_are_stable_and_explicit() -> None:
    module = load_module()
    first, hashes = module.unresolved_dimensions()
    second, second_hashes = module.unresolved_dimensions()
    assert hashes == second_hashes == {}
    assert first == second
    assert set(first) == set(module.DIMENSION_SCOPES)
    for name, value in first.items():
        assert value["file_count"] == 0
        assert len(value["tree_sha256"]) == 64
        assert value["evidence_class"] == "unresolved_authority_not_yet_created"
        assert value["authority_commit"] is None
        assert value["authority_tree"] is None
        assert name in module.DIMENSION_SCOPES


def test_dimension_delta_separates_visibility_transition_from_change() -> None:
    module = load_module()
    unresolved, _ = module.unresolved_dimensions()
    exact = {
        name: {
            **value,
            "tree_sha256": "a" * 64,
            "evidence_class": "exact_authority_git_tree_at_cutoff",
            "authority_commit": "1" * 40,
            "authority_tree": "2" * 40,
        }
        for name, value in unresolved.items()
    }
    changes, transitions = module.dimension_delta(exact, unresolved)
    assert changes == []
    assert len(transitions) == len(module.DIMENSION_SCOPES)
    assert all(
        row["before"] == "unresolved_authority_not_yet_created"
        and row["after"] == "exact_authority_git_tree_at_cutoff"
        for row in transitions
    )


def test_dimension_delta_reports_changes_only_between_exact_states() -> None:
    module = load_module()
    previous = {
        "implementation": {
            "tree_sha256": "a" * 64,
            "evidence_class": "exact_authority_git_tree_at_cutoff",
        }
    }
    current = {
        "implementation": {
            "tree_sha256": "b" * 64,
            "evidence_class": "exact_authority_git_tree_at_cutoff",
        }
    }
    changes, transitions = module.dimension_delta(current, previous)
    assert changes == ["implementation"]
    assert transitions == []


def test_bounded_delta_marks_evidence_scope() -> None:
    module = load_module()
    previous = {
        "date": "2026-07-20",
        "state": {
            "canonical_heads": [
                {"repository": "GlacierEQ/a", "head_sha": "1" * 40}
            ],
            "dimensions": {
                "implementation": {
                    "tree_sha256": "a" * 64,
                    "evidence_class": "exact_authority_git_tree_at_cutoff",
                }
            },
        },
    }
    current = {
        "state": {
            "canonical_heads": [
                {"repository": "GlacierEQ/a", "head_sha": "2" * 40},
                {"repository": "GlacierEQ/b", "head_sha": "3" * 40},
            ],
            "dimensions": {
                "implementation": {
                    "tree_sha256": "b" * 64,
                    "evidence_class": "exact_authority_git_tree_at_cutoff",
                }
            },
        }
    }
    delta = module.bounded_delta(current, previous, "2026-07-20")
    assert delta["status"] == "bounded_historical_reconstruction"
    assert delta["repository_count_delta"] is None
    assert delta["repositories_added"] == ["GlacierEQ/b"]
    assert delta["canonical_head_changes"] == [
        {
            "repository": "GlacierEQ/a",
            "before": "1" * 40,
            "after": "2" * 40,
        }
    ]
    assert delta["dimension_changes"] == ["implementation"]
    assert delta["dimension_evidence_transitions"] == []
    assert "bounded" in delta["delta_semantics"]
