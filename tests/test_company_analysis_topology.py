import copy
import importlib.util
import math
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = ROOT / "manifests" / "company_dossiers.json"
TOPOLOGY_PATH = ROOT / "manifests" / "company_analysis_topology.json"
PLANNER_PATH = ROOT / "scripts" / "build_company_analysis_plan.py"

SPEC = importlib.util.spec_from_file_location("company_analysis_plan", PLANNER_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"could not load company analysis planner: {PLANNER_PATH}")
planner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(planner)

CompanyAnalysisPlanError = planner.CompanyAnalysisPlanError
build_plan = planner.build_plan
reference_sha256 = planner.reference_sha256
load_json = planner.load_json
source_label = planner.source_label
validate_company_index = planner.validate_company_index
validate_plan = planner.validate_plan
validate_topology = planner.validate_topology


def reference_inputs():
    return load_json(INDEX_PATH), load_json(TOPOLOGY_PATH)


def build_current_plan():
    index, topology = reference_inputs()
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
    assigned = [company for wave in plan["waves"] for company in wave["company_ids"]]
    assert assigned == tracks
    assert "fixed 48-track cardinality" in topology["historical_donor"]["not_carried_forward"]


def test_plan_is_deterministic_and_digest_bound():
    _, _, first = build_current_plan()
    _, _, second = build_current_plan()

    assert first == second
    digest = first["plan_sha256"]
    body = copy.deepcopy(first)
    body.pop("plan_sha256")
    assert reference_sha256(body) == digest


def test_track_growth_changes_counts_without_topology_code_change():
    index, topology = reference_inputs()
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
    index, topology = reference_inputs()
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
    index, topology = reference_inputs()
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


def test_v2_topology_requires_all_eight_reference_specialist_lanes():
    index, topology = reference_inputs()
    broken = copy.deepcopy(topology)
    broken["specialists"].pop()

    with pytest.raises(CompanyAnalysisPlanError, match="specialist identity drift"):
        build_plan(
            index,
            broken,
            index_sha256="9" * 64,
            topology_sha256="a" * 64,
        )


def test_v2_topology_requires_reference_coordinator_identity():
    index, topology = reference_inputs()
    broken = copy.deepcopy(topology)
    broken["integration_coordinator"]["id"] = "D12"

    with pytest.raises(CompanyAnalysisPlanError, match="coordinator identity drift"):
        build_plan(
            index,
            broken,
            index_sha256="b" * 64,
            topology_sha256="c" * 64,
        )


def test_v2_topology_requires_every_truth_and_integrity_gate():
    index, topology = reference_inputs()
    broken = copy.deepcopy(topology)
    broken["quality_gates"].remove("non_affiliation_boundary")

    with pytest.raises(CompanyAnalysisPlanError, match="non_affiliation_boundary"):
        build_plan(
            index,
            broken,
            index_sha256="d" * 64,
            topology_sha256="e" * 64,
        )


def test_integrations_bind_the_validated_coordinator_identity():
    _, topology, plan = build_current_plan()
    coordinator_id = topology["integration_coordinator"]["id"]

    for wave in plan["waves"]:
        for integration in wave["integrations"]:
            assert integration["coordinator_id"] == coordinator_id
            assert integration["integration_id"].endswith(f":{coordinator_id}")


def test_source_receipt_preserves_configured_input_paths(tmp_path):
    index, topology = reference_inputs()
    custom_index = tmp_path / "custom-index.json"
    custom_topology = tmp_path / "custom-topology.json"
    custom_index.write_text("{}", encoding="utf-8")
    custom_topology.write_text("{}", encoding="utf-8")

    plan = build_plan(
        index,
        topology,
        index_sha256="f" * 64,
        topology_sha256="0" * 64,
        company_index_source=source_label(custom_index),
        topology_source=source_label(custom_topology),
    )

    assert plan["source_identity"]["company_index"] == custom_index.resolve().as_posix()
    assert plan["source_identity"]["topology_profile"] == custom_topology.resolve().as_posix()
    assert source_label(INDEX_PATH) == "manifests/company_dossiers.json"
