from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from job_app_helix.worker_science import (
    WorkerScienceContractError,
    compile_worker_science_series,
    derive_topology_preset,
    validate_experiment,
)
from job_app_helix.worker_science_schema import WORKER_SCIENCE_EXPERIMENT_SCHEMA

ROOT = Path(__file__).resolve().parents[1]
RUBRIC_REF = f"experiments/rubric-v1.md@{'9' * 40}"


def ref(path: str, char: str) -> str:
    return f"{path}@{char * 40}"


def worker(
    role: str,
    quality: float | None,
    *,
    marginal: float | None = None,
    leverage: float | None = None,
) -> dict[str, object]:
    return {
        "role": role,
        "quality": quality,
        "marginal_system_value": marginal,
        "outcome_leverage": leverage,
        "execution_time_seconds": 1.0,
        "overlap": None,
        "failure": None,
        "next_action": None,
    }


def baseline() -> dict[str, object]:
    return {
        "schema": "glaciereq.worker-science-experiment.v1",
        "experiment_id": "anthropic-baseline-zero",
        "source_repository": "GlacierEQ/make-it-heavy",
        "source_ref": ref("receipts/baseline.json", "a"),
        "mission_family": "flagship_employer_bottleneck",
        "comparison_key": "anthropic_agent_reliability_v1",
        "turn_index": 0,
        "experiment_type": "BASELINE",
        "parent_experiment_ref": None,
        "attempt": None,
        "performance_valid": True,
        "health_class": "HEALTHY",
        "provider": "Smithery SparkForge smart_summarize",
        "provider_diversity": 1,
        "scoring_rubric_ref": RUBRIC_REF,
        "topology": {
            "frozen": True,
            "roles": ["source_mapper", "proof_engineer"],
        },
        "template_changes": [],
        "ablated_role": None,
        "full_outcome_score": None,
        "ablated_outcome_score": None,
        "workers": [
            worker("source_mapper", 60.0),
            worker("proof_engineer", 70.0),
        ],
        "truth_boundary": (
            "Baseline structural quality is observational; "
            "causal metrics are unmeasured."
        ),
    }


def template_delta(
    *,
    valid: bool = True,
    infra: bool = False,
) -> dict[str, object]:
    return {
        "schema": "glaciereq.worker-science-experiment.v1",
        "experiment_id": (
            "anthropic-turn-1-valid" if valid else "anthropic-turn-1-a"
        ),
        "source_repository": "GlacierEQ/make-it-heavy",
        "source_ref": ref("receipts/turn1.json", "b"),
        "mission_family": "flagship_employer_bottleneck",
        "comparison_key": "anthropic_agent_reliability_v1",
        "turn_index": 1,
        "experiment_type": "TEMPLATE_DELTA",
        "parent_experiment_ref": ref("receipts/baseline.json", "a"),
        "attempt": "B" if valid else "A",
        "performance_valid": valid,
        "health_class": "INFRA_FAILURE" if infra else "HEALTHY",
        "provider": "Smithery SparkForge smart_summarize",
        "provider_diversity": 1,
        "scoring_rubric_ref": RUBRIC_REF,
        "topology": {
            "frozen": True,
            "roles": ["source_mapper", "proof_engineer"],
        },
        "template_changes": [
            {
                "role": "source_mapper",
                "change_axis": "nonclaim_preservation",
                "change_id": "source-v1",
                "hypothesis": "Evidence-state fidelity improves.",
            }
        ],
        "ablated_role": None,
        "full_outcome_score": None,
        "ablated_outcome_score": None,
        "workers": [
            worker("source_mapper", 80.0 if valid else None),
            worker("proof_engineer", 80.0 if valid else None),
        ],
        "truth_boundary": (
            "Matched quality delta is observational until ablation."
        ),
    }


def ablation(
    role: str,
    full: float,
    ablated: float,
    leverage: float,
    char: str,
) -> dict[str, object]:
    rows = [
        worker("source_mapper", 80.0),
        worker("proof_engineer", 80.0),
    ]
    target = next(row for row in rows if row["role"] == role)
    target["marginal_system_value"] = full - ablated
    target["outcome_leverage"] = leverage
    return {
        "schema": "glaciereq.worker-science-experiment.v1",
        "experiment_id": f"anthropic-ablation-{role}",
        "source_repository": "GlacierEQ/make-it-heavy",
        "source_ref": ref(f"receipts/ablation-{role}.json", char),
        "mission_family": "flagship_employer_bottleneck",
        "comparison_key": "anthropic_agent_reliability_v1",
        "turn_index": 2 if role == "source_mapper" else 3,
        "experiment_type": "ABLATION",
        "parent_experiment_ref": ref("receipts/turn1.json", "b"),
        "attempt": None,
        "performance_valid": True,
        "health_class": "HEALTHY",
        "provider": "Smithery SparkForge smart_summarize",
        "provider_diversity": 1,
        "scoring_rubric_ref": RUBRIC_REF,
        "topology": {
            "frozen": True,
            "roles": ["source_mapper", "proof_engineer"],
        },
        "template_changes": [],
        "ablated_role": role,
        "full_outcome_score": full,
        "ablated_outcome_score": ablated,
        "workers": rows,
        "truth_boundary": (
            "Ablation compares the matched full result against "
            "full-minus-one-worker."
        ),
    }


def test_packaged_schema_matches_reference_estate_contract() -> None:
    reference = json.loads(
        (
            ROOT
            / "schemas"
            / "estate"
            / "worker-science-experiment.schema.json"
        ).read_text(encoding="utf-8")
    )
    assert reference == WORKER_SCIENCE_EXPERIMENT_SCHEMA


def test_default_validation_uses_packaged_runtime_schema() -> None:
    validate_experiment(baseline())


def test_baseline_accepts_observational_quality_and_null_causal_metrics() -> None:
    validate_experiment(baseline(), ROOT)


def test_unpinned_scoring_rubric_is_rejected() -> None:
    payload = baseline()
    payload["scoring_rubric_ref"] = "experiments/rubric-v1.md"
    with pytest.raises(
        WorkerScienceContractError,
        match="worker-science validation failed",
    ):
        validate_experiment(payload)


def test_worker_rows_must_exactly_cover_declared_topology() -> None:
    payload = template_delta()
    payload["workers"] = payload["workers"][:-1]
    with pytest.raises(
        WorkerScienceContractError,
        match="must exactly cover the declared topology",
    ):
        validate_experiment(payload)


def test_non_ablation_cannot_publish_causal_worker_metrics() -> None:
    payload = baseline()
    payload["workers"][0]["marginal_system_value"] = 0.2
    with pytest.raises(
        WorkerScienceContractError,
        match="causal worker metrics remain null",
    ):
        validate_experiment(payload)


def test_shared_infrastructure_failure_cannot_be_performance_valid() -> None:
    payload = template_delta(valid=True, infra=True)
    with pytest.raises(
        WorkerScienceContractError,
        match="non-reviewable health state cannot be performance-valid",
    ):
        validate_experiment(payload)


def test_invalid_health_cannot_be_performance_valid() -> None:
    payload = template_delta()
    payload["health_class"] = "INVALID"
    with pytest.raises(
        WorkerScienceContractError,
        match="non-reviewable health state cannot be performance-valid",
    ):
        validate_experiment(payload)


def test_invalid_provider_attempt_is_excluded_and_holds_matched_turn() -> None:
    projection = compile_worker_science_series(
        [baseline(), template_delta(valid=False, infra=True)]
    )
    series = projection["series"][0]
    assert series["state"] == "PROVIDER_BLOCKED"
    assert (
        series["next_action"]
        == "REPEAT_MATCHED_TURN_AFTER_HEALTHY_PROVIDER_PROBE"
    )
    assert series["baseline_quality"] == 65.0
    assert series["latest_quality"] == 65.0
    assert series["quality_delta"] == 0.0
    assert series["causal_metrics_present"] is False


def test_valid_template_delta_yields_observational_quality_delta_then_ablation_gate(
) -> None:
    projection = compile_worker_science_series([baseline(), template_delta()])
    series = projection["series"][0]
    assert series["state"] == "DELTA_MEASURED"
    assert series["next_action"] == "RUN_WORKER_ABLATIONS"
    assert series["baseline_quality"] == 65.0
    assert series["latest_quality"] == 80.0
    assert series["quality_delta"] == 15.0
    assert series["topology_preset_eligible"] is False


def test_matched_series_rejects_provider_drift() -> None:
    delta = template_delta()
    delta["provider"] = "Different provider"
    with pytest.raises(WorkerScienceContractError, match="changed provider"):
        compile_worker_science_series([baseline(), delta])


def test_matched_series_rejects_provider_diversity_drift() -> None:
    delta = template_delta()
    delta["provider_diversity"] = 2
    with pytest.raises(
        WorkerScienceContractError,
        match="changed provider diversity",
    ):
        compile_worker_science_series([baseline(), delta])


def test_comparison_key_cannot_cross_mission_families() -> None:
    foreign = deepcopy(baseline())
    foreign["experiment_id"] = "foreign-baseline"
    foreign["source_ref"] = ref("receipts/foreign-baseline.json", "f")
    foreign["mission_family"] = "different_mission_family"
    with pytest.raises(
        WorkerScienceContractError,
        match="is already bound to mission_family",
    ):
        compile_worker_science_series([baseline(), foreign])


def test_template_delta_must_descend_from_series_baseline() -> None:
    delta = template_delta()
    delta["parent_experiment_ref"] = ref("receipts/foreign.json", "f")
    with pytest.raises(
        WorkerScienceContractError,
        match="must descend directly from its baseline",
    ):
        compile_worker_science_series([baseline(), delta])


def test_ablation_parent_must_resolve_to_valid_matched_full_system_turn() -> None:
    payload = ablation("source_mapper", 0.8, 0.6, 0.25, "c")
    payload["parent_experiment_ref"] = baseline()["source_ref"]
    with pytest.raises(
        WorkerScienceContractError,
        match="parent must be a performance-valid TEMPLATE_DELTA",
    ):
        compile_worker_science_series([baseline(), template_delta(), payload])


def test_ablation_rejects_unknown_parent_receipt() -> None:
    payload = ablation("source_mapper", 0.8, 0.6, 0.25, "c")
    payload["parent_experiment_ref"] = ref("receipts/missing.json", "e")
    with pytest.raises(
        WorkerScienceContractError,
        match="parent receipt is unknown",
    ):
        compile_worker_science_series([baseline(), template_delta(), payload])


def test_ablation_requires_frozen_topology() -> None:
    payload = ablation("source_mapper", 0.8, 0.6, 0.25, "c")
    payload["topology"]["frozen"] = False
    with pytest.raises(
        WorkerScienceContractError,
        match="requires a frozen matched topology",
    ):
        validate_experiment(payload)


def test_ablation_cannot_mutate_worker_templates() -> None:
    payload = ablation("source_mapper", 0.8, 0.6, 0.25, "c")
    payload["template_changes"] = [
        {"role": "source_mapper", "change_axis": "forbidden_confound"}
    ]
    with pytest.raises(
        WorkerScienceContractError,
        match="cannot mutate worker templates",
    ):
        validate_experiment(payload)


def test_non_target_ablation_worker_cannot_publish_causal_metrics() -> None:
    payload = ablation("source_mapper", 0.8, 0.6, 0.25, "c")
    payload["workers"][1]["marginal_system_value"] = 0.1
    payload["workers"][1]["outcome_leverage"] = 0.2
    with pytest.raises(
        WorkerScienceContractError,
        match="non-ablated worker rows cannot carry causal metrics",
    ):
        validate_experiment(payload)


def test_invalid_ablation_can_be_recorded_without_outcome_scores() -> None:
    payload = ablation("source_mapper", 0.8, 0.6, 0.25, "c")
    payload["performance_valid"] = False
    payload["health_class"] = "INFRA_FAILURE"
    payload["full_outcome_score"] = None
    payload["ablated_outcome_score"] = None
    for row in payload["workers"]:
        row["quality"] = None
        row["marginal_system_value"] = None
        row["outcome_leverage"] = None
    validate_experiment(payload)


def test_invalid_ablation_cannot_carry_partial_outcome_scores() -> None:
    payload = ablation("source_mapper", 0.8, 0.6, 0.25, "c")
    payload["performance_valid"] = False
    payload["health_class"] = "INFRA_FAILURE"
    payload["ablated_outcome_score"] = None
    for row in payload["workers"]:
        row["marginal_system_value"] = None
        row["outcome_leverage"] = None
    with pytest.raises(
        WorkerScienceContractError,
        match="invalid ABLATION cannot carry outcome scores",
    ):
        validate_experiment(payload)


def test_ablation_requires_exact_signed_marginal_delta() -> None:
    payload = ablation("source_mapper", 0.8, 0.6, 0.25, "c")
    payload["workers"][0]["marginal_system_value"] = 0.3
    with pytest.raises(WorkerScienceContractError, match="must equal"):
        validate_experiment(payload)


def test_duplicate_valid_ablation_for_same_parent_and_role_is_rejected() -> None:
    first = ablation("source_mapper", 0.8, 0.5, 0.40, "c")
    duplicate = ablation("source_mapper", 0.8, 0.55, 0.35, "d")
    duplicate["experiment_id"] = "anthropic-ablation-source-mapper-retry"
    duplicate["turn_index"] = 3
    with pytest.raises(
        WorkerScienceContractError,
        match="duplicate performance-valid ablation",
    ):
        compile_worker_science_series(
            [baseline(), template_delta(), first, duplicate]
        )


def test_ablation_does_not_replace_observational_quality_delta() -> None:
    delta = template_delta()
    projection = compile_worker_science_series(
        [
            baseline(),
            delta,
            ablation("source_mapper", 0.8, 0.5, 0.40, "c"),
            ablation("proof_engineer", 0.8, 0.79, 0.05, "d"),
        ]
    )
    series = projection["series"][0]
    assert series["latest_quality"] == 80.0
    assert series["quality_delta"] == 15.0
    assert series["active_full_system_ref"] == delta["source_ref"]


def test_topology_preset_requires_ablation_for_every_baseline_worker() -> None:
    rows = [
        baseline(),
        template_delta(),
        ablation("source_mapper", 0.8, 0.5, 0.40, "c"),
    ]
    projection = compile_worker_science_series(rows)
    assert projection["series"][0]["topology_preset_eligible"] is False
    with pytest.raises(
        WorkerScienceContractError,
        match="valid ablation for every",
    ):
        derive_topology_preset(rows)


def test_topology_preset_keeps_only_workers_that_clear_quality_and_causal_floors(
) -> None:
    source_ablation = ablation(
        "source_mapper",
        0.8,
        0.5,
        0.40,
        "c",
    )
    proof_ablation = ablation(
        "proof_engineer",
        0.8,
        0.79,
        0.05,
        "d",
    )
    delta = template_delta()
    preset = derive_topology_preset(
        [baseline(), delta, source_ablation, proof_ablation],
        min_quality=78.0,
        min_marginal_system_value=0.05,
        min_outcome_leverage=0.10,
    )
    assert preset["full_system_ref"] == delta["source_ref"]
    assert preset["roles"] == ["source_mapper"]
    assert preset["repurpose_or_retire"] == ["proof_engineer"]
    assert preset["evidence"][0]["decision"] == "KEEP"
    assert preset["evidence"][1]["decision"] == "REPURPOSE_OR_RETIRE"
