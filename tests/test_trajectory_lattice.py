from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEDULE = ROOT / "machine" / "trajectory" / "2026_schedule.json"
SCRIPT = ROOT / "scripts" / "capture_trajectory_checkpoint.py"


def load_module():
    spec = importlib.util.spec_from_file_location("trajectory_capture", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_reference_2026_schedule_is_exact_and_ordered():
    schedule = json.loads(SCHEDULE.read_text(encoding="utf-8"))
    dates = [entry["date"] for entry in schedule["checkpoints"]]
    assert dates == [
        "2026-01-01",
        "2026-02-01",
        "2026-03-01",
        "2026-04-01",
        "2026-05-01",
        "2026-06-01",
        "2026-06-15",
        "2026-07-01",
        "2026-07-15",
        "2026-07-20",
        "2026-07-25",
        "2026-07-30",
        "2026-08-01",
        "2026-08-03",
        "2026-08-05",
        "2026-08-07",
        "2026-08-10",
        "2026-08-15",
        "2026-08-20",
    ]
    assert len(dates) == len(set(dates)) == 19
    assert schedule["timezone"] == "Pacific/Honolulu"
    assert schedule["capture_contract"]["state_and_delta_required"] is True
    assert schedule["capture_contract"]["source_heads_required"] is True
    assert schedule["capture_contract"]["fail_closed_on_missing_private_estate_authority"] is True
    assert schedule["phase_model"] == [
        "expansion",
        "acceleration",
        "composition",
        "rupture",
        "diagnosis",
        "counter-engineering",
        "recovery",
        "stronger expansion",
    ]
    assert [entry["capture_kind"] for entry in schedule["checkpoints"][-2:]] == [
        "contemporary",
        "contemporary",
    ]


def test_all_required_dimensions_are_present():
    schedule = json.loads(SCHEDULE.read_text(encoding="utf-8"))
    assert set(schedule["dimensions"]) == {
        "repository_inventory",
        "source_heads",
        "genealogy",
        "capability_ontology",
        "original_intent",
        "development_target",
        "implementation",
        "verification",
        "deployment_public_projection",
        "job_application_evolution",
        "company_coverage",
        "company_specific_inventions",
        "control_plane_topology",
        "receipts",
        "blockers",
        "experiments",
        "source_hashes",
    }


def test_delta_reports_repo_head_and_dimension_changes():
    module = load_module()
    previous = {
        "date": "2026-08-15",
        "state": {
            "repository_inventory": {"owned_repository_count": 2},
            "source_heads": [
                {"repository": "GlacierEQ/a", "head_sha": "aaa"},
                {"repository": "GlacierEQ/b", "head_sha": "bbb"},
            ],
            "dimensions": {
                "implementation": {"tree_sha256": "old"},
                "verification": {"tree_sha256": "same"},
            },
        },
    }
    current = {
        "state": {
            "repository_inventory": {"owned_repository_count": 3},
            "source_heads": [
                {"repository": "GlacierEQ/a", "head_sha": "ccc"},
                {"repository": "GlacierEQ/b", "head_sha": "bbb"},
                {"repository": "GlacierEQ/c", "head_sha": "ddd"},
            ],
            "dimensions": {
                "implementation": {"tree_sha256": "new"},
                "verification": {"tree_sha256": "same"},
            },
        }
    }
    delta = module.compute_delta(current, previous, "2026-08-15")
    assert delta["status"] == "computed"
    assert delta["repository_count_delta"] == 1
    assert delta["repositories_added"] == ["GlacierEQ/c"]
    assert delta["repositories_removed"] == []
    assert delta["source_head_changes"] == [
        {"repository": "GlacierEQ/a", "before": "aaa", "after": "ccc"}
    ]
    assert delta["dimension_changes"] == ["implementation"]


def test_missing_previous_checkpoint_fails_closed_without_fabricating_delta():
    module = load_module()
    current = {
        "state": {
            "repository_inventory": {"owned_repository_count": 1},
            "source_heads": [],
            "dimensions": {},
        }
    }
    delta = module.compute_delta(current, None, "2026-08-10")
    assert delta["status"] == "previous_checkpoint_not_materialized"
    assert delta["previous_checkpoint_expected"] == "2026-08-10"
    assert delta["repository_count_delta"] is None
