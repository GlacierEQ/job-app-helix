"""Self-contained public proof runtime recovered from the retired PR #1 lineage.

The July 2026 donor implemented a fresh-clone fixture runtime but its branch was
retired without merge. This module composes that useful mechanism into the
current package while preserving later Helix architecture. The evidence digest
is deterministic: observation time is metadata and never changes proof bytes.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
from collections.abc import Callable, Iterable, Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

Scenario = Literal["nominal", "recoverable", "terminal"]
Decision = Literal["GO", "NO-GO"]
Strand = Literal["alpha", "bridge", "omega", "meta"]

DONOR = {
    "repository": "GlacierEQ/job-app-helix",
    "branch_head": "34370b44d9d4d44d93b6364a946454687ece2a75",
    "path": "helix/public_runtime.py",
    "blob_sha": "7cfc559616746fcb5314ca2fa7481acc3c1c9367",
    "pull_request": 1,
    "recovery_ref": "recovered/2026-07-29/public-reproducible-runtime",
}
PROTOCOL = "job-app-helix/public-proof-v2"
MU_EARTH_M3_S2 = 3.986004418e14
EARTH_RADIUS_M = 6_378_137.0


class PublicProofError(ValueError):
    """Raised when a proof runtime request or receipt violates its contract."""


@dataclass(frozen=True)
class PistonResult:
    name: str
    strand: Strand
    status: str
    inputs: dict[str, Any]
    outputs: dict[str, Any]


@dataclass(frozen=True)
class PairResult:
    pair: str
    capability: str
    alpha: tuple[PistonResult, ...]
    bridge: tuple[PistonResult, ...]
    omega: tuple[PistonResult, ...]
    refinements: tuple[PistonResult, ...]
    initial_ok: bool
    final_ok: bool


def _stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256(value: Any) -> str:
    return hashlib.sha256(_stable_json(value).encode()).hexdigest()


def _piston(
    name: str,
    strand: Strand,
    status: str,
    inputs: Mapping[str, Any],
    outputs: Mapping[str, Any],
) -> PistonResult:
    return PistonResult(name, strand, status, dict(inputs), dict(outputs))


def _flight(scenario: Scenario) -> PairResult:
    altitude_m = 400_000.0
    radius_m = EARTH_RADIUS_M + altitude_m
    speed_m_s = math.sqrt(MU_EARTH_M3_S2 / radius_m)
    period_s = 2.0 * math.pi * math.sqrt(radius_m**3 / MU_EARTH_M3_S2)
    orbit = _piston(
        "orbital_truth",
        "alpha",
        "NOMINAL",
        {"altitude_m": altitude_m},
        {
            "radius_m": round(radius_m, 3),
            "speed_m_s": round(speed_m_s, 3),
            "period_s": round(period_s, 3),
        },
    )
    sequences = [1, 2, 3, 4, 5]
    if scenario != "nominal":
        sequences = [1, 2, 5, 6, 7]
    drops = sum(max(0, current - prior - 1) for prior, current in itertools.pairwise(sequences))
    telemetry = _piston(
        "telemetry_bridge",
        "bridge",
        "DEGRADED" if drops else "NOMINAL",
        {"orbit": orbit.outputs},
        {"sequences": sequences, "drops": drops, "accepted": len(sequences)},
    )
    severity = 4 if drops else 2
    gate = _piston(
        "mission_gate",
        "omega",
        "HOLD" if severity >= 4 else "GO_PATH",
        {"telemetry": telemetry.outputs, "speed_m_s": orbit.outputs["speed_m_s"]},
        {"severity": severity, "hold": severity >= 4},
    )
    initial_ok = not gate.outputs["hold"]
    refinements: list[PistonResult] = []
    final_ok = initial_ok
    if not initial_ok and scenario == "recoverable":
        refinements.append(
            _piston(
                "telemetry_refinement",
                "alpha",
                "NOMINAL",
                {"prior_drops": drops, "action": "restore_sequence_continuity"},
                {"sequences": [1, 2, 3, 4, 5], "drops": 0},
            )
        )
        final_ok = True
    elif not initial_ok:
        refinements.append(
            _piston(
                "telemetry_refinement",
                "alpha",
                "FAILED",
                {"prior_drops": drops, "action": "restore_sequence_continuity"},
                {"drops": drops, "reason": "source_unavailable"},
            )
        )
    return PairResult(
        "flight",
        "flight awareness",
        (orbit,),
        (telemetry,),
        (gate,),
        tuple(refinements),
        initial_ok,
        final_ok,
    )


def _propulsion(scenario: Scenario) -> PairResult:
    sample = {"chamber_pressure_ratio": 0.98, "mixture_error": 0.02, "vibration_g": 2.5}
    if scenario == "recoverable":
        sample = {"chamber_pressure_ratio": 0.89, "mixture_error": 0.08, "vibration_g": 5.8}
    elif scenario == "terminal":
        sample = {"chamber_pressure_ratio": 0.72, "mixture_error": 0.18, "vibration_g": 9.0}
    penalty = (
        abs(1.0 - sample["chamber_pressure_ratio"]) * 100.0
        + sample["mixture_error"] * 120.0
        + max(0.0, sample["vibration_g"] - 2.0) * 4.0
    )
    health = max(0.0, 100.0 - penalty)
    status = "GREEN" if health >= 85.0 else "YELLOW" if health >= 65.0 else "RED"
    assess = _piston(
        "propulsion_health",
        "alpha",
        status,
        sample,
        {"health_score": round(health, 2), "status": status},
    )
    hold = status != "GREEN"
    gate = _piston(
        "launch_sequencer",
        "omega",
        "HOLD" if hold else "GO_PATH",
        {"propulsion": assess.outputs},
        {"holds": [f"propulsion_{status.lower()}"] if hold else []},
    )
    initial_ok = not hold
    refinements: list[PistonResult] = []
    final_ok = initial_ok
    if not initial_ok and scenario == "recoverable":
        refinements.append(
            _piston(
                "propulsion_refinement",
                "alpha",
                "GREEN",
                {"prior": sample, "action": "derate_and_rebalance"},
                {
                    "sample": {
                        "chamber_pressure_ratio": 0.99,
                        "mixture_error": 0.01,
                        "vibration_g": 2.0,
                    },
                    "health_score": 96.8,
                    "status": "GREEN",
                },
            )
        )
        final_ok = True
    elif not initial_ok:
        refinements.append(
            _piston(
                "propulsion_refinement",
                "alpha",
                "FAILED",
                {"prior": sample, "action": "derate_and_rebalance"},
                {"status": "RED", "reason": "persistent_vibration"},
            )
        )
    return PairResult(
        "propulsion",
        "propulsion readiness",
        (assess,),
        (),
        (gate,),
        tuple(refinements),
        initial_ok,
        final_ok,
    )


def _ground(scenario: Scenario) -> PairResult:
    stations = [
        {"name": "HAW", "capacity_mbps": 25.0, "available": True},
        {"name": "AUS", "capacity_mbps": 45.0, "available": True},
        {"name": "EU", "capacity_mbps": 20.0, "available": True},
    ]
    if scenario == "terminal":
        stations[1]["available"] = False
    need_mbps = 55.0
    selected: list[str] = []
    delivered = 0.0
    for station in sorted(stations, key=lambda item: item["capacity_mbps"], reverse=True):
        if station["available"] and delivered < need_mbps:
            selected.append(station["name"])
            delivered += station["capacity_mbps"]
    ready = delivered >= need_mbps
    plan = _piston(
        "ground_capacity",
        "alpha",
        "NOMINAL" if ready else "CAPACITY_SHORT",
        {"need_mbps": need_mbps, "stations": stations},
        {"selected": selected, "delivered_mbps": delivered, "capacity_ok": ready},
    )
    gate = _piston(
        "mesh_route_gate",
        "omega",
        "NOMINAL" if ready else "NO_PATH",
        {"ground_plan": plan.outputs},
        {"route": ["S1", "S4", "GND"] if ready else [], "ready": ready},
    )
    refinements: list[PistonResult] = []
    if not ready:
        refinements.append(
            _piston(
                "ground_refinement",
                "alpha",
                "FAILED",
                {"action": "add_capacity", "shortfall_mbps": need_mbps - delivered},
                {"reason": "no_fixture_capacity_remaining"},
            )
        )
    return PairResult(
        "ground",
        "ground and mesh readiness",
        (plan,),
        (),
        (gate,),
        tuple(refinements),
        ready,
        ready,
    )


PAIR_RUNNERS: dict[str, Callable[[Scenario], PairResult]] = {
    "flight": _flight,
    "propulsion": _propulsion,
    "ground": _ground,
}


def _validate_scenario(value: str) -> Scenario:
    if value not in {"nominal", "recoverable", "terminal"}:
        raise PublicProofError(f"unknown scenario: {value}")
    return value  # type: ignore[return-value]


def _evidence_envelope(scenario: Scenario, pairs: Iterable[PairResult]) -> dict[str, Any]:
    rows = list(pairs)
    initial: Decision = "GO" if all(row.initial_ok for row in rows) else "NO-GO"
    final: Decision = "GO" if all(row.final_ok for row in rows) else "NO-GO"
    return {
        "protocol": PROTOCOL,
        "mode": "fixture",
        "scenario": scenario,
        "campaign": "launch",
        "invariant": "DONE iff every required capability is green after bounded refinement",
        "initial_decision": initial,
        "final_decision": final,
        "final_reasons": [row.pair for row in rows if not row.final_ok],
        "pairs": [asdict(row) for row in rows],
        "summary": {
            "pairs_run": len(rows),
            "initial_green": sum(row.initial_ok for row in rows),
            "final_green": sum(row.final_ok for row in rows),
            "refinements": sum(len(row.refinements) for row in rows),
        },
        "recovery_lineage": dict(DONOR),
    }


def run_launch_campaign(
    scenario: Scenario = "nominal",
    *,
    observed_at: str | None = None,
) -> dict[str, Any]:
    scenario = _validate_scenario(scenario)
    evidence = _evidence_envelope(scenario, (runner(scenario) for runner in PAIR_RUNNERS.values()))
    return {
        **evidence,
        "evidence_sha256": _sha256(evidence),
        "observed_at": observed_at,
    }


def run_pair(pair: str, scenario: Scenario = "nominal") -> dict[str, Any]:
    scenario = _validate_scenario(scenario)
    runner = PAIR_RUNNERS.get(pair)
    if runner is None:
        raise PublicProofError(f"unknown pair: {pair}")
    result = runner(scenario)
    evidence = {
        "protocol": PROTOCOL,
        "mode": "fixture",
        "scenario": scenario,
        "pair": asdict(result),
        "recovery_lineage": dict(DONOR),
    }
    return {**evidence, "evidence_sha256": _sha256(evidence)}


def verify_receipt(receipt: Mapping[str, Any]) -> tuple[bool, tuple[str, ...]]:
    errors: list[str] = []
    if receipt.get("protocol") != PROTOCOL:
        errors.append("protocol_mismatch")
    digest = receipt.get("evidence_sha256")
    if not isinstance(digest, str) or len(digest) != 64:
        errors.append("missing_evidence_sha256")
    evidence = {
        key: value
        for key, value in receipt.items()
        if key not in {"evidence_sha256", "observed_at"}
    }
    if isinstance(digest, str) and _sha256(evidence) != digest:
        errors.append("evidence_digest_mismatch")
    lineage = receipt.get("recovery_lineage")
    if not isinstance(lineage, Mapping) or lineage.get("branch_head") != DONOR["branch_head"]:
        errors.append("donor_lineage_mismatch")
    if receipt.get("campaign") == "launch":
        pairs = receipt.get("pairs")
        if not isinstance(pairs, list) or len(pairs) != 3:
            errors.append("pair_cardinality")
        decision = receipt.get("final_decision")
        if decision not in {"GO", "NO-GO"}:
            errors.append("invalid_final_decision")
    return not errors, tuple(errors)


def _write(payload: Mapping[str, Any], output: Path | None) -> None:
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the recovered, self-contained Job-App Helix public proof runtime"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list")
    demo = sub.add_parser("demo")
    demo.add_argument("--scenario", choices=("nominal", "recoverable", "terminal"), default="nominal")
    demo.add_argument("--output", type=Path)
    pair = sub.add_parser("pair")
    pair.add_argument("pair", choices=sorted(PAIR_RUNNERS))
    pair.add_argument("--scenario", choices=("nominal", "recoverable", "terminal"), default="nominal")
    pair.add_argument("--output", type=Path)
    verify = sub.add_parser("verify")
    verify.add_argument("receipt", type=Path)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    if args.command == "list":
        _write(
            {
                "protocol": PROTOCOL,
                "pairs": sorted(PAIR_RUNNERS),
                "scenarios": ["nominal", "recoverable", "terminal"],
                "recovery_lineage": DONOR,
            },
            None,
        )
        return 0
    if args.command == "demo":
        payload = run_launch_campaign(args.scenario)
        _write(payload, args.output)
        return 0 if payload["final_decision"] == "GO" else 1
    if args.command == "pair":
        payload = run_pair(args.pair, args.scenario)
        _write(payload, args.output)
        return 0 if payload["pair"]["final_ok"] else 1
    payload = json.loads(args.receipt.read_text(encoding="utf-8"))
    valid, errors = verify_receipt(payload)
    _write({"status": "PASS" if valid else "FAIL", "errors": errors}, None)
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
