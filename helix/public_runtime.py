#!/usr/bin/env python3
"""Self-contained public runtime for the Job-App Helix.

This module intentionally uses only the Python standard library. It provides a
deterministic fixture-mode proof of the repository's core contract:

    domain truth -> operational verification -> refinement -> final decision

The larger workspace runner remains available for Casey's multi-repository
environment. This public runtime exists so a fresh clone can be tested without
private repositories, local symlinks, or GlacierEQ_Swarm state.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Literal

Scenario = Literal["nominal", "recoverable", "terminal"]
Decision = Literal["GO", "NO-GO"]

MU_EARTH_M3_S2 = 3.986004418e14
EARTH_RADIUS_M = 6_378_137.0


@dataclass(frozen=True)
class PistonResult:
    """One deterministic unit of work in a helix strand."""

    name: str
    strand: Literal["alpha", "bridge", "omega", "meta"]
    status: str
    inputs: dict[str, Any]
    outputs: dict[str, Any]


@dataclass(frozen=True)
class PairResult:
    """One Alpha/Omega pair aimed at a single operational star."""

    pair: str
    star: str
    alpha: tuple[PistonResult, ...]
    bridge: tuple[PistonResult, ...]
    omega: tuple[PistonResult, ...]
    refinements: tuple[PistonResult, ...]
    initial_ok: bool
    final_ok: bool


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _stable_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _piston(
    name: str,
    strand: Literal["alpha", "bridge", "omega", "meta"],
    status: str,
    inputs: dict[str, Any],
    outputs: dict[str, Any],
) -> PistonResult:
    return PistonResult(name=name, strand=strand, status=status, inputs=inputs, outputs=outputs)


def _flight_pair(scenario: Scenario) -> PairResult:
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
    if scenario in {"recoverable", "terminal"}:
        sequences = [1, 2, 5, 6, 7]
    drops = sum(max(0, current - prior - 1) for prior, current in zip(sequences, sequences[1:]))
    telemetry = _piston(
        "telemetry_bridge",
        "bridge",
        "DEGRADED" if drops else "NOMINAL",
        {"orbit": orbit.outputs},
        {"sequences": sequences, "drops": drops, "accepted": len(sequences)},
    )

    severity = 4 if drops else 2
    console = _piston(
        "mission_gate",
        "omega",
        "HOLD" if severity >= 4 else "GO_PATH",
        {"telemetry": telemetry.outputs, "speed_m_s": orbit.outputs["speed_m_s"]},
        {"severity": severity, "hold": severity >= 4},
    )
    initial_ok = not console.outputs["hold"]

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
    elif not initial_ok and scenario == "terminal":
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
        pair="flight",
        star="flight awareness",
        alpha=(orbit,),
        bridge=(telemetry,),
        omega=(console,),
        refinements=tuple(refinements),
        initial_ok=initial_ok,
        final_ok=final_ok,
    )


def _propulsion_pair(scenario: Scenario) -> PairResult:
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
    sequencer = _piston(
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
        corrected = {"chamber_pressure_ratio": 0.99, "mixture_error": 0.01, "vibration_g": 2.0}
        refinements.append(
            _piston(
                "propulsion_refinement",
                "alpha",
                "GREEN",
                {"prior": sample, "action": "derate_and_rebalance"},
                {"sample": corrected, "health_score": 96.8, "status": "GREEN"},
            )
        )
        final_ok = True
    elif not initial_ok and scenario == "terminal":
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
        pair="propulsion",
        star="propulsion readiness",
        alpha=(assess,),
        bridge=(),
        omega=(sequencer,),
        refinements=tuple(refinements),
        initial_ok=initial_ok,
        final_ok=final_ok,
    )


def _ground_pair(scenario: Scenario) -> PairResult:
    stations = [
        {"name": "HAW", "capacity_mbps": 25.0, "available": True},
        {"name": "AUS", "capacity_mbps": 45.0, "available": True},
        {"name": "EU", "capacity_mbps": 20.0, "available": True},
    ]
    need_mbps = 55.0
    if scenario == "terminal":
        stations[1]["available"] = False

    selected: list[str] = []
    delivered = 0.0
    for station in sorted(stations, key=lambda item: item["capacity_mbps"], reverse=True):
        if station["available"] and delivered < need_mbps:
            selected.append(station["name"])
            delivered += station["capacity_mbps"]

    capacity_ok = delivered >= need_mbps
    plan = _piston(
        "ground_capacity",
        "alpha",
        "NOMINAL" if capacity_ok else "CAPACITY_SHORT",
        {"need_mbps": need_mbps, "stations": stations},
        {"selected": selected, "delivered_mbps": delivered, "capacity_ok": capacity_ok},
    )
    mesh = _piston(
        "mesh_route_gate",
        "omega",
        "NOMINAL" if capacity_ok else "NO_PATH",
        {"ground_plan": plan.outputs},
        {"route": ["S1", "S4", "GND"] if capacity_ok else [], "ready": capacity_ok},
    )

    refinements: list[PistonResult] = []
    if not capacity_ok:
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
        pair="ground",
        star="ground and mesh readiness",
        alpha=(plan,),
        bridge=(),
        omega=(mesh,),
        refinements=tuple(refinements),
        initial_ok=capacity_ok,
        final_ok=capacity_ok,
    )


PAIR_RUNNERS: dict[str, Callable[[Scenario], PairResult]] = {
    "flight": _flight_pair,
    "propulsion": _propulsion_pair,
    "ground": _ground_pair,
}


def run_pair(pair: str, scenario: Scenario = "nominal") -> dict[str, Any]:
    if pair not in PAIR_RUNNERS:
        raise ValueError(f"Unknown pair: {pair}")
    result = PAIR_RUNNERS[pair](scenario)
    payload = {
        "protocol": "job-app-helix/public-v1",
        "mode": "fixture",
        "scenario": scenario,
        "pair": asdict(result),
    }
    payload["proof_sha256"] = _stable_hash(payload)
    return payload


def run_launch_campaign(scenario: Scenario = "nominal") -> dict[str, Any]:
    pairs = [runner(scenario) for runner in PAIR_RUNNERS.values()]
    initial_decision: Decision = "GO" if all(pair.initial_ok for pair in pairs) else "NO-GO"
    final_decision: Decision = "GO" if all(pair.final_ok for pair in pairs) else "NO-GO"
    reasons = [pair.pair for pair in pairs if not pair.final_ok]

    payload: dict[str, Any] = {
        "protocol": "job-app-helix/public-v1",
        "mode": "fixture",
        "generated_at": _utc_now(),
        "scenario": scenario,
        "campaign": "launch",
        "invariant": "DONE iff proof(pain) is green",
        "initial_decision": initial_decision,
        "final_decision": final_decision,
        "final_reasons": reasons,
        "pairs": [asdict(pair) for pair in pairs],
        "summary": {
            "pairs_run": len(pairs),
            "initial_green": sum(pair.initial_ok for pair in pairs),
            "final_green": sum(pair.final_ok for pair in pairs),
            "refinements": sum(len(pair.refinements) for pair in pairs),
        },
    }
    payload["proof_sha256"] = _stable_hash(payload)
    return payload


def _write_receipt(payload: dict[str, Any], output: Path | None) -> None:
    rendered = json.dumps(payload, indent=2, sort_keys=True)
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


def _scenario(value: str) -> Scenario:
    allowed = {"nominal", "recoverable", "terminal"}
    if value not in allowed:
        raise argparse.ArgumentTypeError(f"scenario must be one of: {', '.join(sorted(allowed))}")
    return value  # type: ignore[return-value]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the self-contained Job-App Helix proof runtime")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list", help="List public fixture pairs and scenarios")
    demo = sub.add_parser("demo", help="Run the multi-star launch campaign")
    demo.add_argument("--scenario", type=_scenario, default="nominal")
    demo.add_argument("--output", type=Path)
    pair = sub.add_parser("pair", help="Run one public Alpha/Omega pair")
    pair.add_argument("pair", choices=sorted(PAIR_RUNNERS))
    pair.add_argument("--scenario", type=_scenario, default="nominal")
    pair.add_argument("--output", type=Path)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    if args.command == "list":
        _write_receipt(
            {
                "protocol": "job-app-helix/public-v1",
                "mode": "fixture",
                "pairs": sorted(PAIR_RUNNERS),
                "scenarios": ["nominal", "recoverable", "terminal"],
            },
            None,
        )
        return 0
    if args.command == "demo":
        payload = run_launch_campaign(args.scenario)
        _write_receipt(payload, args.output)
        return 0 if payload["final_decision"] == "GO" else 1
    payload = run_pair(args.pair, args.scenario)
    _write_receipt(payload, args.output)
    return 0 if payload["pair"]["final_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
