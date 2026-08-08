#!/usr/bin/env python3
"""Build a deterministic, truth-bounded company analysis plan from canonical tracks."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
COMPANY_INDEX = ROOT / "manifests" / "company_dossiers.json"
TOPOLOGY_PROFILE = ROOT / "manifests" / "company_analysis_topology.json"
EXPECTED_PROFILE_SCHEMA = "glaciereq.company-analysis-topology.v2"
EXPECTED_INDEX_SCHEMA = "glaciereq.company-dossiers-index.v2"
CANONICAL_ORCHESTRATOR_ID = "D0"
CANONICAL_DOMAIN_LEAD_IDS = ("D1", "D2")
CANONICAL_SPECIALIST_IDS = tuple(f"S{index}" for index in range(1, 9))
CANONICAL_COORDINATOR_ID = "D11"
REQUIRED_QUALITY_GATES = frozenset(
    {
        "canonical_track_parity",
        "unique_track_assignment",
        "complete_specialist_matrix",
        "unique_task_identity",
        "contradiction_preservation",
        "observed_inferred_boundary",
        "non_affiliation_boundary",
        "zero_silent_omission",
        "deterministic_plan_digest",
    }
)
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")


class CompanyAnalysisPlanError(ValueError):
    """Raised when the deterministic company-analysis contract is invalid."""


def load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CompanyAnalysisPlanError(f"required file not found: {path}") from exc
    except OSError as exc:
        raise CompanyAnalysisPlanError(f"could not read {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise CompanyAnalysisPlanError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise CompanyAnalysisPlanError(f"JSON root must be an object: {path}")
    return payload


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_sha256(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def source_label(path: Path) -> str:
    resolved_root = ROOT.resolve()
    resolved_path = path.resolve()
    try:
        return resolved_path.relative_to(resolved_root).as_posix()
    except ValueError:
        return resolved_path.as_posix()


def _required_string(payload: dict[str, Any], field: str, source: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise CompanyAnalysisPlanError(f"{source}.{field} must be a non-empty string")
    return value


def _unique_string_list(value: Any, source: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise CompanyAnalysisPlanError(f"{source} must be a non-empty array")
    if not all(isinstance(item, str) and item.strip() for item in value):
        raise CompanyAnalysisPlanError(f"{source} contains an invalid string")
    normalized = [item.strip() for item in value]
    if len(normalized) != len(set(normalized)):
        raise CompanyAnalysisPlanError(f"{source} contains duplicate values")
    return normalized


def validate_company_index(index: dict[str, Any]) -> list[str]:
    if index.get("schema") != EXPECTED_INDEX_SCHEMA:
        raise CompanyAnalysisPlanError("unexpected company dossier index schema")
    tracks = _unique_string_list(
        index.get("required_company_tracks"),
        "company_dossiers.required_company_tracks",
    )
    return tracks


def _validate_nodes(nodes: Any, source: str) -> list[dict[str, str]]:
    if not isinstance(nodes, list) or not nodes:
        raise CompanyAnalysisPlanError(f"{source} must be a non-empty array")
    normalized: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            raise CompanyAnalysisPlanError(f"{source}[{index}] must be an object")
        node_id = _required_string(node, "id", f"{source}[{index}]")
        role = _required_string(node, "role", f"{source}[{index}]")
        responsibility = _required_string(
            node,
            "responsibility",
            f"{source}[{index}]",
        )
        if node_id in seen_ids:
            raise CompanyAnalysisPlanError(f"duplicate topology node id: {node_id}")
        seen_ids.add(node_id)
        normalized.append(
            {
                "id": node_id,
                "role": role,
                "responsibility": responsibility,
            }
        )
    return normalized


def _require_canonical_node_ids(
    orchestrator_id: str,
    domain_leads: list[dict[str, str]],
    specialists: list[dict[str, str]],
    coordinator_id: str,
) -> None:
    if orchestrator_id != CANONICAL_ORCHESTRATOR_ID:
        raise CompanyAnalysisPlanError(
            "topology orchestrator identity drift requires a schema version change"
        )
    domain_ids = tuple(node["id"] for node in domain_leads)
    if domain_ids != CANONICAL_DOMAIN_LEAD_IDS:
        raise CompanyAnalysisPlanError(
            "topology domain-lead identity drift requires a schema version change"
        )
    specialist_ids = tuple(node["id"] for node in specialists)
    if specialist_ids != CANONICAL_SPECIALIST_IDS:
        raise CompanyAnalysisPlanError(
            "topology specialist identity drift requires a schema version change"
        )
    if coordinator_id != CANONICAL_COORDINATOR_ID:
        raise CompanyAnalysisPlanError(
            "topology coordinator identity drift requires a schema version change"
        )


def validate_topology(profile: dict[str, Any]) -> dict[str, Any]:
    if profile.get("schema") != EXPECTED_PROFILE_SCHEMA:
        raise CompanyAnalysisPlanError("unexpected company analysis topology schema")
    if profile.get("visibility") != "internal_planning_only":
        raise CompanyAnalysisPlanError("company analysis topology must remain internal planning")
    if profile.get("execution_mode") != "deterministic_plan_generation":
        raise CompanyAnalysisPlanError("company analysis topology execution mode drift")

    wave_size = profile.get("wave_size")
    if isinstance(wave_size, bool) or not isinstance(wave_size, int) or wave_size <= 0:
        raise CompanyAnalysisPlanError("company analysis topology wave_size must be positive")

    orchestrator = profile.get("mission_orchestrator")
    if not isinstance(orchestrator, dict):
        raise CompanyAnalysisPlanError("mission_orchestrator must be an object")
    orchestrator_id = _required_string(orchestrator, "id", "mission_orchestrator")
    _required_string(orchestrator, "responsibility", "mission_orchestrator")

    domain_leads = _validate_nodes(profile.get("domain_leads"), "domain_leads")
    specialists = _validate_nodes(profile.get("specialists"), "specialists")

    coordinator = profile.get("integration_coordinator")
    if not isinstance(coordinator, dict):
        raise CompanyAnalysisPlanError("integration_coordinator must be an object")
    coordinator_id = _required_string(coordinator, "id", "integration_coordinator")
    _required_string(coordinator, "responsibility", "integration_coordinator")

    all_ids = [orchestrator_id, coordinator_id]
    all_ids.extend(node["id"] for node in domain_leads)
    all_ids.extend(node["id"] for node in specialists)
    if len(all_ids) != len(set(all_ids)):
        raise CompanyAnalysisPlanError("topology node ids must be globally unique")
    _require_canonical_node_ids(
        orchestrator_id,
        domain_leads,
        specialists,
        coordinator_id,
    )

    gates = _unique_string_list(profile.get("quality_gates"), "quality_gates")
    if not set(gates) >= REQUIRED_QUALITY_GATES:
        missing = sorted(REQUIRED_QUALITY_GATES - set(gates))
        raise CompanyAnalysisPlanError(f"topology is missing required quality gates: {missing}")

    boundary = profile.get("truth_boundary")
    if not isinstance(boundary, dict):
        raise CompanyAnalysisPlanError("truth_boundary must be an object")
    for field in (
        "plan_is_execution",
        "plan_is_model_consensus",
        "plan_is_company_affiliation",
        "plan_is_runtime_proof",
        "hosted_model_workers_invoked_by_planner",
    ):
        if boundary.get(field) is not False:
            raise CompanyAnalysisPlanError(f"truth_boundary.{field} must be false")
    if boundary.get("track_cardinality_source") != (
        "manifests/company_dossiers.json::required_company_tracks"
    ):
        raise CompanyAnalysisPlanError("track cardinality source drift")

    donor = profile.get("historical_donor")
    if not isinstance(donor, dict):
        raise CompanyAnalysisPlanError("historical_donor must be an object")
    donor_head = _required_string(donor, "head", "historical_donor")
    donor_topology_sha = _required_string(
        donor,
        "topology_sha256",
        "historical_donor",
    )
    if HEX40.fullmatch(donor_head) is None:
        raise CompanyAnalysisPlanError("historical donor head must be a commit SHA")
    if HEX64.fullmatch(donor_topology_sha) is None:
        raise CompanyAnalysisPlanError("historical donor topology digest must be SHA-256")

    return {
        "wave_size": wave_size,
        "orchestrator_id": orchestrator_id,
        "domain_leads": domain_leads,
        "specialists": specialists,
        "coordinator_id": coordinator_id,
        "quality_gates": gates,
    }


def validate_plan(
    plan: dict[str, Any],
    tracks: list[str],
    specialist_ids: list[str],
) -> None:
    waves = plan.get("waves")
    if not isinstance(waves, list) or not waves:
        raise CompanyAnalysisPlanError("plan must contain waves")

    assigned_tracks: list[str] = []
    task_ids: list[str] = []
    task_pairs: list[tuple[str, str]] = []
    integration_tracks: list[str] = []
    for expected_ordinal, wave in enumerate(waves, 1):
        if not isinstance(wave, dict) or wave.get("ordinal") != expected_ordinal:
            raise CompanyAnalysisPlanError("wave ordinals must be contiguous")
        company_ids = wave.get("company_ids")
        tasks = wave.get("specialist_tasks")
        integrations = wave.get("integrations")
        if (
            not isinstance(company_ids, list)
            or not isinstance(tasks, list)
            or not isinstance(integrations, list)
        ):
            raise CompanyAnalysisPlanError("wave payload is incomplete")
        assigned_tracks.extend(company_ids)
        for task in tasks:
            if not isinstance(task, dict):
                raise CompanyAnalysisPlanError("specialist task must be an object")
            task_id = task.get("task_id")
            company_id = task.get("company_id")
            specialist_id = task.get("specialist_id")
            task_identity = (task_id, company_id, specialist_id)
            if not all(isinstance(value, str) and value for value in task_identity):
                raise CompanyAnalysisPlanError("specialist task identity is invalid")
            if specialist_id not in specialist_ids:
                raise CompanyAnalysisPlanError(f"unknown specialist id: {specialist_id}")
            if task.get("status") != "PLANNED" or task.get("execution_claim") is not False:
                raise CompanyAnalysisPlanError("planner must not claim specialist execution")
            task_ids.append(task_id)
            task_pairs.append((company_id, specialist_id))
        for integration in integrations:
            if not isinstance(integration, dict):
                raise CompanyAnalysisPlanError("integration row must be an object")
            company_id = integration.get("company_id")
            if not isinstance(company_id, str) or not company_id:
                raise CompanyAnalysisPlanError("integration company identity is invalid")
            integration_is_unexecuted = (
                integration.get("status") == "PLANNED"
                and integration.get("execution_claim") is False
            )
            if not integration_is_unexecuted:
                raise CompanyAnalysisPlanError("planner must not claim integration execution")
            integration_tracks.append(company_id)

    if assigned_tracks != tracks:
        raise CompanyAnalysisPlanError("plan company-track ordering or parity drift")
    if len(task_ids) != len(set(task_ids)):
        raise CompanyAnalysisPlanError("duplicate specialist task identity")
    if len(task_pairs) != len(set(task_pairs)):
        raise CompanyAnalysisPlanError("duplicate company/specialist task pair")
    expected_pairs = {(track, specialist) for track in tracks for specialist in specialist_ids}
    if set(task_pairs) != expected_pairs:
        raise CompanyAnalysisPlanError("specialist matrix is incomplete")
    if integration_tracks != tracks:
        raise CompanyAnalysisPlanError("integration coverage does not match canonical tracks")

    counts = plan.get("counts")
    if not isinstance(counts, dict):
        raise CompanyAnalysisPlanError("plan counts are missing")
    expected = {
        "company_tracks": len(tracks),
        "specialists": len(specialist_ids),
        "waves": len(waves),
        "specialist_tasks": len(tracks) * len(specialist_ids),
        "integrations": len(tracks),
        "silent_omissions": 0,
    }
    if counts != expected:
        raise CompanyAnalysisPlanError(f"plan counts drift: {counts} != {expected}")


def build_plan(
    company_index: dict[str, Any],
    topology_profile: dict[str, Any],
    *,
    index_sha256: str,
    topology_sha256: str,
    company_index_source: str = "manifests/company_dossiers.json",
    topology_source: str = "manifests/company_analysis_topology.json",
) -> dict[str, Any]:
    tracks = validate_company_index(company_index)
    topology = validate_topology(topology_profile)
    wave_size = topology["wave_size"]
    specialists = topology["specialists"]
    specialist_ids = [node["id"] for node in specialists]
    coordinator_id = topology["coordinator_id"]

    waves: list[dict[str, Any]] = []
    for wave_index, start in enumerate(range(0, len(tracks), wave_size), 1):
        company_ids = tracks[start : start + wave_size]
        tasks = []
        integrations = []
        for company_id in company_ids:
            for specialist in specialists:
                specialist_id = specialist["id"]
                tasks.append(
                    {
                        "task_id": f"W{wave_index:02d}:{company_id}:{specialist_id}",
                        "company_id": company_id,
                        "specialist_id": specialist_id,
                        "role": specialist["role"],
                        "responsibility": specialist["responsibility"],
                        "status": "PLANNED",
                        "execution_claim": False,
                    }
                )
            integrations.append(
                {
                    "integration_id": f"W{wave_index:02d}:{company_id}:{coordinator_id}",
                    "company_id": company_id,
                    "coordinator_id": coordinator_id,
                    "status": "PLANNED",
                    "execution_claim": False,
                }
            )
        waves.append(
            {
                "ordinal": wave_index,
                "company_ids": company_ids,
                "specialist_tasks": tasks,
                "integrations": integrations,
            }
        )

    plan: dict[str, Any] = {
        "schema": "glaciereq.company-analysis-plan.v1",
        "authority": "GlacierEQ/job-app-helix",
        "source_identity": {
            "company_index": company_index_source,
            "company_index_sha256": index_sha256,
            "topology_profile": topology_source,
            "topology_profile_sha256": topology_sha256,
        },
        "execution_truth": {
            "status": "PLANNED_ONLY",
            "deterministic_planner_executed": True,
            "specialist_analysis_executed": False,
            "integrations_executed": False,
            "hosted_model_workers_invoked": False,
        },
        "topology": {
            "orchestrator_id": topology["orchestrator_id"],
            "domain_lead_ids": [node["id"] for node in topology["domain_leads"]],
            "specialist_ids": specialist_ids,
            "integration_coordinator_id": coordinator_id,
            "wave_size": wave_size,
        },
        "counts": {
            "company_tracks": len(tracks),
            "specialists": len(specialist_ids),
            "waves": math.ceil(len(tracks) / wave_size),
            "specialist_tasks": len(tracks) * len(specialist_ids),
            "integrations": len(tracks),
            "silent_omissions": 0,
        },
        "quality_gates": topology["quality_gates"],
        "waves": waves,
    }
    validate_plan(plan, tracks, specialist_ids)
    plan["plan_sha256"] = canonical_sha256(plan)
    return plan


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--company-index", type=Path, default=COMPANY_INDEX)
    parser.add_argument("--topology", type=Path, default=TOPOLOGY_PROFILE)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        company_index = load_json(args.company_index)
        topology_profile = load_json(args.topology)
        plan = build_plan(
            company_index,
            topology_profile,
            index_sha256=file_sha256(args.company_index),
            topology_sha256=file_sha256(args.topology),
            company_index_source=source_label(args.company_index),
            topology_source=source_label(args.topology),
        )
    except (CompanyAnalysisPlanError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if args.output:
        write_json(args.output, plan)
    else:
        print(json.dumps(plan, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
