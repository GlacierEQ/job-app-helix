import copy
import math
from pathlib import Path

import pytest

from scripts.build_company_analysis_plan import (
    CompanyAnalysisPlanError,
    build_plan,
    canonical_sha256,
    load_json,
    validate_company_index,
    validate_plan,
    validate_topology,
)

ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = ROOT / "manifests" / "company_dossiers.json"
TOPOLOGY_PATH = ROOT / "manifests" / "company_analysis_topology.json"


def canonical_inputs():
    return load_json(INDEX_PATH), load_json(TOPOLOGY_PATH)


def build_current_plan():
    index, topology = canonical_inputs()
    plan = build_plan(
        index,
        topology,
        index_sha256="1" * 64,
        topology_sha256="2" * 64,
    )
    return index, topology, plan


def test_current_company_tracks_drive_wave_and_task_counts_without_fixed_48():
    index, topology, plan = build_current_plan()
    tracks = validate_company_index(index)
    profile = validate_topology(topology)
    specialist_count = len(profile["specialists"])
    wave_size = profile["wave_size"]

    assert plan["counts"] == {
        "company_tracks": len(tracks),
        "specialists": specialist_count,
        "waves": math.ceil(len(tracks) / wave_size),
        "specialist_tasks": len(tracks) * specialist_count,
        "integrations": len(tracks),
        "silent_omissions": 0,
    }
    assert [company for wave in plan["waves"] for company in wave["company_ids"]] == tracks
    assert "fixed 48-track cardinality" in topology["historical_donor"]["not_carried_forward"]


def test_plan_is_deterministic_and_digest_bound():
    _, _, first = build_current_plan()
    _, _, second = build_current_plan()

    assert first == second
    digest = first["plan_sha256"]
    body = copy.deepcopy(first)
    body.pop("plan_sha256")
    assert canonical_sha256(body) == digest


def test_track_growth_changes_counts_without_topology_code_change():
    index, topology = canonical_inputs()
    expanded = copy.deepcopy(index)
    expanded["required_company_tracks"] = [
        *expanded["required_company_tracks"],
        "future_target_for_test",
    ]

    plan = build_plan(
        expanded,
        topology,
        index_sha256="3" * 64,
        topology_sha256="4" * 64,
    )
    tracks = expanded["required_company_tracks"]
    specialists = topology["specialists"]

    assert plan["counts"]["company_tracks"] == len(tracks)
    assert plan["counts"]["specialist_tasks"] == len(tracks) * len(specialists)
    assert plan["counts"]["waves"] == math.ceil(len(tracks) / topology["wave_size"])
    assert plan["waves"][-1]["company_ids"][-1] == "future_target_for_test"


def test_duplicate_company_track_fails_closed():
    index, topology = canonical_inputs()
    broken = copy.deepcopy(index)
    broken["required_company_tracks"].append(broken["required_company_tracks"][0])

    with pytest.raises(CompanyAnalysisPlanError, match="duplicate"):
        build_plan(
            broken,
            topology,
            index_sha256="5" * 64,
            topology_sha256="6" * 64,
        )


def test_topology_cannot_claim_execution_or_model_consensus():
    index, topology = canonical_inputs()
    broken = copy.deepcopy(topology)
    broken["truth_boundary"]["plan_is_execution"] = True

    with pytest.raises(CompanyAnalysisPlanError, match="plan_is_execution"):
        build_plan(
            index,
            broken,
            index_sha256="7" * 64,
            topology_sha256="8" * 64,
        )


def test_missing_specialist_task_is_detected_as_omission():
    index, topology, plan = build_current_plan()
    tracks = validate_company_index(index)
    specialist_ids = [node["id"] for node in validate_topology(topology)["specialists"]]
    plan["waves"][0]["specialist_tasks"].pop()

    with pytest.raises(CompanyAnalysisPlanError, match="specialist matrix is incomplete"):
        validate_plan(plan, tracks, specialist_ids)
