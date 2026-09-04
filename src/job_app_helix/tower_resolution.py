#!/usr/bin/env python3
"""
Tower Capability Resolution — Resolve optimal language/tech placement via Tower of Babel's 40-floor registry.

L4 Invariant & Causal: When >3 failures occur, STOP mutation. Map full data graph. Single root-cause hypothesis.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

TOWER_ROOT = Path("/data/data/com.termux/files/home/the-tower-of-babel")


@dataclass
class CapabilityRequirement:
    name: str
    domain: str
    performance_requirements: dict[str, Any] = field(default_factory=dict)
    constraints: dict[str, Any] = field(default_factory=dict)
    prefer_verified: bool = True


@dataclass
class PlacementDecision:
    technology: str
    floor: int
    capability: str
    entrypoint: str
    interface: str
    verified: bool
    fitness_scores: dict[str, float]
    rationale: str


@dataclass
class ResolutionReceipt:
    requirement: CapabilityRequirement
    timestamp: str
    candidates_evaluated: int
    selected: PlacementDecision
    receipt_hash: str


def load_tower_registry() -> dict[str, Any]:
    registry_file = TOWER_ROOT / "registry" / "tower.d" / "nextgen-innovations.json"
    if registry_file.exists():
        data = json.loads(registry_file.read_text())
        # Transform 'technologies' to 'innovations' for compatibility
        if "technologies" in data and "innovations" not in data:
            data["innovations"] = data["technologies"]
        return data
    return {}


def load_capability_resolution() -> dict[str, Any]:
    cap_file = TOWER_ROOT / "src" / "tower" / "capability_resolution.py"
    if cap_file.exists():
        return {"file": str(cap_file), "exists": True}
    return {"exists": False}


def evaluate_fitness(req: CapabilityRequirement, innovation: dict[str, Any]) -> dict[str, float]:
    scores = {}

    tech = innovation.get("name", "").lower()
    capability = innovation.get("what", "").lower() + " " + innovation.get("why", "").lower()
    category = innovation.get("category", "").lower()
    floor = innovation.get("floor", 0) if "floor" in innovation else 20
    verified = innovation.get("evidence_state", "") == "verified" or innovation.get("verified", False)

    scores["domain_match"] = 1.0 if req.domain.lower() in category or req.domain.lower() in capability else 0.0
    scores["requirement_match"] = 1.0 if req.name.lower() in capability else 0.0
    scores["floor_relevance"] = min(floor / 40.0, 1.0)
    scores["verified_bonus"] = 1.0 if verified else 0.0

    perf_req = req.performance_requirements
    if perf_req.get("memory_safety") and tech in ["rust", "zig", "ebpf"]:
        scores["memory_safety"] = 1.0
    elif perf_req.get("memory_safety"):
        scores["memory_safety"] = 0.5

    if perf_req.get("concurrency") and tech in ["rust", "go", "erlang"]:
        scores["concurrency"] = 1.0
    elif perf_req.get("concurrency"):
        scores["concurrency"] = 0.5

    if perf_req.get("determinism") and tech in ["rust", "coq", "lean"]:
        scores["determinism"] = 1.0
    elif perf_req.get("determinism"):
        scores["determinism"] = 0.5

    scores["composite"] = sum(scores.values()) / len(scores)
    return scores


def resolve_placement(req: CapabilityRequirement) -> tuple[PlacementDecision, list[dict[str, Any]]]:
    registry = load_tower_registry()
    innovations = registry.get("innovations", [])

    candidates = []
    for innovation in innovations:
        if isinstance(innovation, dict):
            fitness = evaluate_fitness(req, innovation)
            candidates.append({
                "innovation": innovation,
                "fitness": fitness,
            })

    candidates.sort(key=lambda x: x["fitness"]["composite"], reverse=True)

    if not candidates:
        raise ValueError("No candidates found in Tower registry")

    best = candidates[0]
    innovation = best["innovation"]
    fitness = best["fitness"]

    placement = PlacementDecision(
        technology=innovation.get("name", "unknown"),
        floor=innovation.get("floor", 20),
        capability=innovation.get("what", "unknown"),
        entrypoint=innovation.get("entrypoint", ""),
        interface=innovation.get("interface", "unknown"),
        verified=innovation.get("evidence_state", "") == "verified",
        fitness_scores=fitness,
        rationale=f"Selected {innovation.get('name')} (floor {innovation.get('floor', 20)}) with composite fitness {fitness['composite']:.4f}",
    )

    return placement, [{"technology": c["innovation"].get("name"), "fitness": c["fitness"]} for c in candidates[:5]]


def invoke_tower_capability_resolution(req: CapabilityRequirement) -> dict[str, Any]:
    cap_file = TOWER_ROOT / "src" / "tower" / "capability_resolution.py"
    if not cap_file.exists():
        return {"error": "capability_resolution.py not found"}

    try:
        result = subprocess.run(
            [sys.executable, str(cap_file), "--requirement", req.name, "--domain", req.domain],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(TOWER_ROOT),
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
        return {"error": result.stderr}
    except Exception as e:
        return {"error": str(e)}


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Resolve optimal language/tech placement via Tower of Babel")
    parser.add_argument("--requirement", required=True, help="Capability requirement name")
    parser.add_argument("--domain", required=True, help="Capability domain")
    parser.add_argument("--perf", default="{}", help="Performance requirements JSON")
    parser.add_argument("--constraints", default="{}", help="Constraints JSON")
    parser.add_argument("--tower-root", default="/data/data/com.termux/files/home/the-tower-of-babel", help="Tower of Babel root")
    parser.add_argument("--output", default="tower_resolution.json", help="Output file")
    args = parser.parse_args()

    global TOWER_ROOT
    TOWER_ROOT = Path(args.tower_root)

    req = CapabilityRequirement(
        name=args.requirement,
        domain=args.domain,
        performance_requirements=json.loads(args.perf),
        constraints=json.loads(args.constraints),
    )

    placement, top_candidates = resolve_placement(req)

    tower_result = invoke_tower_capability_resolution(req)

    receipt_data = f"{req.name}:{req.domain}:{placement.technology}:{datetime.now(timezone.utc).isoformat()}"
    receipt_hash = hashlib.sha256(receipt_data.encode()).hexdigest()[:16]

    receipt = ResolutionReceipt(
        requirement=req,
        timestamp=datetime.now(timezone.utc).isoformat(),
        candidates_evaluated=len(top_candidates),
        selected=placement,
        receipt_hash=receipt_hash,
    )

    result = {
        "requirement": asdict(req),
        "placement": asdict(placement),
        "top_candidates": top_candidates,
        "tower_native_result": tower_result,
        "receipt": asdict(receipt),
    }

    Path(args.output).write_text(json.dumps(result, indent=2))

    print(f"Resolved: {placement.technology} (floor {placement.floor}) - fitness {placement.fitness_scores['composite']:.4f}")
    print(f"Receipt: {receipt_hash}")
    return 0


if __name__ == "__main__":
    sys.exit(main())