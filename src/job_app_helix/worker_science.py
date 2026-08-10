from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
from math import isclose, isfinite
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from job_app_helix.worker_science_schema import WORKER_SCIENCE_EXPERIMENT_SCHEMA

WORKER_SCIENCE_SCHEMA = "glaciereq.worker-science-experiment.v1"
INFRA_FAILURE = "INFRA_FAILURE"
INVALID_HEALTH = "INVALID"
CAUSAL_EXPERIMENT = "ABLATION"
OBSERVATIONAL_EXPERIMENTS = {"BASELINE", "TEMPLATE_DELTA"}
MATCHED_EXPERIMENTS = {"BASELINE", "TEMPLATE_DELTA", "ABLATION"}


class WorkerScienceContractError(ValueError):
    """Raised when longitudinal worker-science evidence violates a Helix invariant."""


@dataclass(frozen=True)
class SeriesDecision:
    mission_family: str
    comparison_key: str
    state: str
    next_action: str
    latest_experiment_id: str
    baseline_quality: float | None
    latest_quality: float | None
    quality_delta: float | None
    ablations_completed: int
    topology_preset_eligible: bool


def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def schema_path(root: Path | None = None) -> Path:
    base = root or repository_root()
    return base / "schemas" / "estate" / "worker-science-experiment.schema.json"


def _load_schema(root: Path | None = None) -> dict[str, Any]:
    packaged = deepcopy(WORKER_SCIENCE_EXPERIMENT_SCHEMA)
    if root is None:
        Draft202012Validator.check_schema(packaged)
        return packaged

    path = schema_path(root)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload != packaged:
        raise WorkerScienceContractError(
            "packaged worker-science schema differs from canonical estate schema"
        )
    Draft202012Validator.check_schema(payload)
    return payload


def _finite_or_none(value: Any, label: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise WorkerScienceContractError(f"{label} must be numeric or null")
    numeric = float(value)
    if not isfinite(numeric):
        raise WorkerScienceContractError(f"{label} must be finite")
    return numeric


def validate_experiment(
    payload: Mapping[str, Any],
    root: Path | None = None,
) -> None:
    schema = _load_schema(root)
    validator = Draft202012Validator(schema)
    errors = sorted(
        validator.iter_errors(dict(payload)),
        key=lambda item: list(item.path),
    )
    if errors:
        rendered = "; ".join(error.message for error in errors)
        raise WorkerScienceContractError(
            f"worker-science validation failed: {rendered}"
        )

    if payload.get("schema") != WORKER_SCIENCE_SCHEMA:
        raise WorkerScienceContractError("worker-science schema identity mismatch")

    topology = payload["topology"]
    roles = tuple(topology["roles"])
    worker_roles = [worker["role"] for worker in payload["workers"]]
    if len(worker_roles) != len(set(worker_roles)):
        raise WorkerScienceContractError(
            "worker roles must be unique inside an experiment"
        )
    if set(worker_roles) != set(roles):
        missing = sorted(set(roles) - set(worker_roles))
        extra = sorted(set(worker_roles) - set(roles))
        raise WorkerScienceContractError(
            "worker rows must exactly cover the declared topology: "
            f"missing={missing}, extra={extra}"
        )

    changes = list(payload.get("template_changes") or [])
    change_roles = [change["role"] for change in changes]
    if len(change_roles) != len(set(change_roles)):
        raise WorkerScienceContractError(
            "a matched turn may change at most one axis per worker"
        )
    if set(change_roles) - set(roles):
        raise WorkerScienceContractError(
            "template changes must target active topology roles"
        )

    experiment_type = payload["experiment_type"]
    parent = payload.get("parent_experiment_ref")
    performance_valid = bool(payload["performance_valid"])
    health_class = payload["health_class"]
    rubric_ref = payload.get("scoring_rubric_ref")

    if health_class in {INFRA_FAILURE, INVALID_HEALTH} and performance_valid:
        raise WorkerScienceContractError(
            "non-reviewable health state cannot be performance-valid"
        )
    if experiment_type in MATCHED_EXPERIMENTS and not isinstance(
        rubric_ref,
        str,
    ):
        raise WorkerScienceContractError(
            "matched worker experiments require an immutable scoring rubric ref"
        )

    if experiment_type == "BASELINE":
        if parent is not None:
            raise WorkerScienceContractError(
                "BASELINE must not declare a parent experiment"
            )
        if changes:
            raise WorkerScienceContractError(
                "BASELINE must not mutate worker templates"
            )
        if payload["turn_index"] != 0:
            raise WorkerScienceContractError("BASELINE must use turn_index=0")
        if topology["frozen"] is not True:
            raise WorkerScienceContractError(
                "matched BASELINE topology must be frozen"
            )

    if experiment_type == "TEMPLATE_DELTA":
        if not parent:
            raise WorkerScienceContractError(
                "TEMPLATE_DELTA requires immutable parent lineage"
            )
        if not changes:
            raise WorkerScienceContractError(
                "TEMPLATE_DELTA requires at least one template change"
            )
        if topology["frozen"] is not True:
            raise WorkerScienceContractError(
                "matched TEMPLATE_DELTA topology must be frozen"
            )

    ablated_role = payload.get("ablated_role")
    for worker in payload["workers"]:
        role = str(worker["role"])
        _finite_or_none(worker.get("quality"), f"{role}.quality")
        marginal = _finite_or_none(
            worker.get("marginal_system_value"),
            f"{role}.marginal_system_value",
        )
        leverage = _finite_or_none(
            worker.get("outcome_leverage"),
            f"{role}.outcome_leverage",
        )
        if experiment_type != CAUSAL_EXPERIMENT and (
            marginal is not None or leverage is not None
        ):
            raise WorkerScienceContractError(
                "causal worker metrics remain null until an ABLATION receipt"
            )
        if not performance_valid and (
            marginal is not None or leverage is not None
        ):
            raise WorkerScienceContractError(
                "invalid experiments cannot carry causal worker metrics"
            )
        if (
            experiment_type == CAUSAL_EXPERIMENT
            and role != ablated_role
            and (marginal is not None or leverage is not None)
        ):
            raise WorkerScienceContractError(
                "non-ablated worker rows cannot carry causal metrics"
            )

    if experiment_type == CAUSAL_EXPERIMENT:
        if not parent:
            raise WorkerScienceContractError(
                "ABLATION requires immutable parent lineage"
            )
        if not isinstance(ablated_role, str) or ablated_role not in roles:
            raise WorkerScienceContractError(
                "ABLATION requires an active ablated_role"
            )
        if topology["frozen"] is not True:
            raise WorkerScienceContractError(
                "ABLATION requires a frozen matched topology"
            )
        if changes:
            raise WorkerScienceContractError(
                "ABLATION cannot mutate worker templates"
            )

        full = _finite_or_none(
            payload.get("full_outcome_score"),
            "full_outcome_score",
        )
        ablated = _finite_or_none(
            payload.get("ablated_outcome_score"),
            "ablated_outcome_score",
        )
        target = next(
            (
                worker
                for worker in payload["workers"]
                if worker["role"] == ablated_role
            ),
            None,
        )
        if target is None:
            raise WorkerScienceContractError(
                "ABLATION must include the ablated worker row"
            )
        recorded = _finite_or_none(
            target.get("marginal_system_value"),
            f"{ablated_role}.marginal_system_value",
        )
        leverage = _finite_or_none(
            target.get("outcome_leverage"),
            f"{ablated_role}.outcome_leverage",
        )

        if not performance_valid:
            if full is not None or ablated is not None:
                raise WorkerScienceContractError(
                    "invalid ABLATION cannot carry outcome scores"
                )
            if recorded is not None or leverage is not None:
                raise WorkerScienceContractError(
                    "invalid ABLATION cannot publish causal metrics"
                )
        else:
            if full is None or ablated is None:
                raise WorkerScienceContractError(
                    "valid ABLATION requires full and ablated outcome scores"
                )
            expected = full - ablated
            if recorded is None or not isclose(
                recorded,
                expected,
                rel_tol=1e-9,
                abs_tol=1e-9,
            ):
                raise WorkerScienceContractError(
                    "marginal_system_value must equal "
                    "full_outcome_score - ablated_outcome_score"
                )
            if leverage is None:
                raise WorkerScienceContractError(
                    "valid ABLATION requires normalized outcome_leverage"
                )


def _mean_quality(experiment: Mapping[str, Any]) -> float | None:
    if not experiment.get("performance_valid"):
        return None
    values = [
        float(worker["quality"])
        for worker in experiment["workers"]
        if worker.get("quality") is not None
    ]
    if not values:
        return None
    return round(sum(values) / len(values), 4)


def _series_key(experiment: Mapping[str, Any]) -> tuple[str, str]:
    return str(experiment["mission_family"]), str(experiment["comparison_key"])


def _latest_valid_delta(rows: Sequence[Mapping[str, Any]]) -> Mapping[str, Any] | None:
    return next(
        (
            row
            for row in reversed(rows)
            if row["experiment_type"] == "TEMPLATE_DELTA"
            and row["performance_valid"]
        ),
        None,
    )


def _active_valid_ablations(
    rows: Sequence[Mapping[str, Any]],
    active_delta: Mapping[str, Any] | None,
) -> list[Mapping[str, Any]]:
    if active_delta is None:
        return []
    parent_ref = active_delta["source_ref"]
    return [
        row
        for row in rows
        if row["experiment_type"] == "ABLATION"
        and row["performance_valid"]
        and row.get("parent_experiment_ref") == parent_ref
    ]


def _validate_series_lineage(
    rows: Sequence[Mapping[str, Any]],
    baseline: Mapping[str, Any],
    all_by_source_ref: Mapping[str, Mapping[str, Any]],
    key: tuple[str, str],
) -> None:
    baseline_ref = baseline["source_ref"]
    seen_ablation_keys: set[tuple[str, str]] = set()

    for row in rows:
        experiment_type = row["experiment_type"]
        parent_ref = row.get("parent_experiment_ref")

        if (
            experiment_type == "TEMPLATE_DELTA"
            and parent_ref != baseline_ref
        ):
            raise WorkerScienceContractError(
                f"matched series {key!r} TEMPLATE_DELTA must descend "
                "directly from its baseline receipt"
            )

        if experiment_type != "ABLATION":
            continue

        parent = all_by_source_ref.get(str(parent_ref))
        if parent is None:
            raise WorkerScienceContractError(
                f"matched series {key!r} ABLATION parent receipt is unknown"
            )
        if _series_key(parent) != key:
            raise WorkerScienceContractError(
                f"matched series {key!r} ABLATION parent crosses comparison series"
            )
        if (
            parent["experiment_type"] != "TEMPLATE_DELTA"
            or not parent["performance_valid"]
        ):
            raise WorkerScienceContractError(
                f"matched series {key!r} ABLATION parent must be a "
                "performance-valid TEMPLATE_DELTA"
            )
        if int(parent["turn_index"]) >= int(row["turn_index"]):
            raise WorkerScienceContractError(
                f"matched series {key!r} ABLATION must follow its full-system parent"
            )

        if row["performance_valid"]:
            ablation_key = (str(parent_ref), str(row["ablated_role"]))
            if ablation_key in seen_ablation_keys:
                raise WorkerScienceContractError(
                    "duplicate performance-valid ablation for the same "
                    "full-system parent and worker role"
                )
            seen_ablation_keys.add(ablation_key)


def compile_worker_science_series(
    experiments: Sequence[Mapping[str, Any]],
    root: Path | None = None,
) -> dict[str, Any]:
    if not experiments:
        raise WorkerScienceContractError(
            "worker science requires at least one experiment"
        )

    normalized: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    all_by_source_ref: dict[str, dict[str, Any]] = {}
    comparison_owners: dict[str, str] = {}
    for raw in experiments:
        experiment = dict(raw)
        validate_experiment(experiment, root)
        experiment_id = str(experiment["experiment_id"])
        source_ref = str(experiment["source_ref"])
        comparison_key = str(experiment["comparison_key"])
        mission_family = str(experiment["mission_family"])
        if experiment_id in seen_ids:
            raise WorkerScienceContractError(
                f"duplicate experiment_id: {experiment_id}"
            )
        if source_ref in all_by_source_ref:
            raise WorkerScienceContractError(
                f"duplicate immutable source_ref: {source_ref}"
            )
        prior_owner = comparison_owners.get(comparison_key)
        if prior_owner is not None and prior_owner != mission_family:
            raise WorkerScienceContractError(
                f"comparison_key {comparison_key!r} is already bound to "
                f"mission_family {prior_owner!r}"
            )
        comparison_owners[comparison_key] = mission_family
        seen_ids.add(experiment_id)
        all_by_source_ref[source_ref] = experiment
        normalized.append(experiment)

    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for experiment in normalized:
        grouped[_series_key(experiment)].append(experiment)

    series_payloads: list[dict[str, Any]] = []
    for key in sorted(grouped):
        rows = sorted(
            grouped[key],
            key=lambda item: (
                int(item["turn_index"]),
                str(item.get("attempt") or ""),
                str(item["experiment_id"]),
            ),
        )
        baselines = [
            row for row in rows if row["experiment_type"] == "BASELINE"
        ]
        if len(baselines) != 1:
            raise WorkerScienceContractError(
                f"series {key!r} requires exactly one BASELINE"
            )
        baseline = baselines[0]
        baseline_roles = tuple(baseline["topology"]["roles"])
        baseline_provider = baseline.get("provider")
        baseline_provider_diversity = baseline.get("provider_diversity")
        baseline_rubric = baseline.get("scoring_rubric_ref")

        _validate_series_lineage(rows, baseline, all_by_source_ref, key)

        for row in rows:
            if row["experiment_type"] in {"TEMPLATE_DELTA", "ABLATION"}:
                if tuple(row["topology"]["roles"]) != baseline_roles:
                    raise WorkerScienceContractError(
                        f"matched series {key!r} changed topology "
                        "before causal comparison"
                    )
                if row.get("provider") != baseline_provider:
                    raise WorkerScienceContractError(
                        f"matched series {key!r} changed provider "
                        "inside the comparison"
                    )
                if (
                    row.get("provider_diversity")
                    != baseline_provider_diversity
                ):
                    raise WorkerScienceContractError(
                        f"matched series {key!r} changed provider diversity "
                        "inside the comparison"
                    )
                if row.get("scoring_rubric_ref") != baseline_rubric:
                    raise WorkerScienceContractError(
                        f"matched series {key!r} changed scoring rubric "
                        "inside the comparison"
                    )

        valid_deltas = [
            row
            for row in rows
            if row["experiment_type"] == "TEMPLATE_DELTA"
            and row["performance_valid"]
        ]
        invalid_deltas = [
            row
            for row in rows
            if row["experiment_type"] == "TEMPLATE_DELTA"
            and not row["performance_valid"]
        ]
        active_delta = _latest_valid_delta(rows)
        active_ablations = _active_valid_ablations(rows, active_delta)

        baseline_quality = _mean_quality(baseline)
        observational_rows = [
            row
            for row in rows
            if row["experiment_type"] in OBSERVATIONAL_EXPERIMENTS
            and row["performance_valid"]
        ]
        latest_observational = observational_rows[-1]
        latest_quality = _mean_quality(latest_observational)
        quality_delta = None
        if baseline_quality is not None and latest_quality is not None:
            quality_delta = round(latest_quality - baseline_quality, 4)

        ablated_roles = {
            str(row["ablated_role"]) for row in active_ablations
        }
        topology_preset_eligible = (
            active_delta is not None
            and bool(baseline_roles)
            and set(baseline_roles).issubset(ablated_roles)
        )

        latest = rows[-1]
        if not valid_deltas:
            if invalid_deltas and latest["health_class"] == INFRA_FAILURE:
                state = "PROVIDER_BLOCKED"
                next_action = (
                    "REPEAT_MATCHED_TURN_AFTER_HEALTHY_PROVIDER_PROBE"
                )
            else:
                state = "BASELINE_READY"
                next_action = "RUN_MATCHED_TEMPLATE_DELTA"
        elif not topology_preset_eligible:
            state = "DELTA_MEASURED"
            next_action = "RUN_WORKER_ABLATIONS"
        else:
            state = "CAUSAL_TOPOLOGY_READY"
            next_action = "DERIVE_LEARNED_TOPOLOGY_PRESET"

        decision = SeriesDecision(
            mission_family=key[0],
            comparison_key=key[1],
            state=state,
            next_action=next_action,
            latest_experiment_id=str(latest["experiment_id"]),
            baseline_quality=baseline_quality,
            latest_quality=latest_quality,
            quality_delta=quality_delta,
            ablations_completed=len(active_ablations),
            topology_preset_eligible=topology_preset_eligible,
        )
        series_payloads.append(
            {
                "mission_family": decision.mission_family,
                "comparison_key": decision.comparison_key,
                "state": decision.state,
                "next_action": decision.next_action,
                "latest_experiment_id": decision.latest_experiment_id,
                "baseline_quality": decision.baseline_quality,
                "latest_quality": decision.latest_quality,
                "quality_delta": decision.quality_delta,
                "ablations_completed": decision.ablations_completed,
                "topology_preset_eligible": (
                    decision.topology_preset_eligible
                ),
                "baseline_topology": list(baseline_roles),
                "active_full_system_ref": (
                    active_delta["source_ref"] if active_delta else None
                ),
                "causal_metrics_present": bool(active_ablations),
            }
        )

    return {
        "schema": "glaciereq.worker-science-projection.v1",
        "series": series_payloads,
        "truth_boundary": (
            "Quality deltas are observational matched-turn measurements. "
            "Marginal system value and outcome leverage become causal evidence "
            "only through performance-valid worker ablation receipts bound to "
            "the active matched full-system turn. Infrastructure-invalid turns "
            "never teach topology."
        ),
    }


def derive_topology_preset(
    experiments: Sequence[Mapping[str, Any]],
    *,
    min_quality: float = 78.0,
    min_marginal_system_value: float = 0.0,
    min_outcome_leverage: float = 0.1,
    root: Path | None = None,
) -> dict[str, Any]:
    projection = compile_worker_science_series(experiments, root)
    if len(projection["series"]) != 1:
        raise WorkerScienceContractError(
            "topology preset derivation requires exactly one matched comparison series"
        )
    series = projection["series"][0]
    if not series["topology_preset_eligible"]:
        raise WorkerScienceContractError(
            "topology preset requires a valid ablation for every baseline worker"
        )

    rows = sorted(
        (dict(item) for item in experiments),
        key=lambda item: (
            int(item["turn_index"]),
            str(item.get("attempt") or ""),
            str(item["experiment_id"]),
        ),
    )
    baseline = next(
        row for row in rows if row["experiment_type"] == "BASELINE"
    )
    active_delta = _latest_valid_delta(rows)
    if active_delta is None:
        raise WorkerScienceContractError(
            "topology preset requires an active valid TEMPLATE_DELTA"
        )
    active_ablations = _active_valid_ablations(rows, active_delta)

    latest_quality_by_role: dict[str, float] = {}
    for row in rows:
        if (
            not row["performance_valid"]
            or row["experiment_type"] not in OBSERVATIONAL_EXPERIMENTS
        ):
            continue
        for worker in row["workers"]:
            if worker.get("quality") is not None:
                latest_quality_by_role[str(worker["role"])] = float(
                    worker["quality"]
                )

    causal_by_role: dict[str, tuple[float, float]] = {}
    evidence_refs: dict[str, str] = {}
    for row in active_ablations:
        role = str(row["ablated_role"])
        worker = next(
            item for item in row["workers"] if item["role"] == role
        )
        causal_by_role[role] = (
            float(worker["marginal_system_value"]),
            float(worker["outcome_leverage"]),
        )
        evidence_refs[role] = str(row["source_ref"])

    keep: list[str] = []
    repurpose_or_retire: list[str] = []
    evidence: list[dict[str, Any]] = []
    for role in baseline["topology"]["roles"]:
        if role not in causal_by_role or role not in evidence_refs:
            raise WorkerScienceContractError(
                f"baseline role {role!r} lacks active valid ablation evidence"
            )
        quality = latest_quality_by_role.get(role)
        marginal, leverage = causal_by_role[role]
        selected = (
            quality is not None
            and quality >= min_quality
            and marginal > min_marginal_system_value
            and leverage >= min_outcome_leverage
        )
        (keep if selected else repurpose_or_retire).append(role)
        evidence.append(
            {
                "role": role,
                "quality": quality,
                "marginal_system_value": marginal,
                "outcome_leverage": leverage,
                "decision": (
                    "KEEP" if selected else "REPURPOSE_OR_RETIRE"
                ),
                "evidence_ref": evidence_refs[role],
            }
        )

    if not keep:
        raise WorkerScienceContractError(
            "derived topology would remove every worker; thresholds require review"
        )

    return {
        "schema": "glaciereq.learned-worker-topology.v1",
        "mission_family": series["mission_family"],
        "comparison_key": series["comparison_key"],
        "full_system_ref": active_delta["source_ref"],
        "roles": keep,
        "repurpose_or_retire": repurpose_or_retire,
        "evidence": evidence,
        "thresholds": {
            "min_quality": min_quality,
            "min_marginal_system_value": min_marginal_system_value,
            "min_outcome_leverage": min_outcome_leverage,
        },
        "truth_boundary": (
            "This preset is learned only from the supplied matched series and "
            "the active full-system turn's ablations. It does not prove the "
            "same topology is optimal for other mission families, providers, "
            "models, or evidence fields."
        ),
    }
