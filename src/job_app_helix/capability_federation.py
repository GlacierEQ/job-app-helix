#!/usr/bin/env python3
"""
Capability Federation — Federate capabilities across monolith catalog and Tower of Babel resolution.

L2 Subsystem: Lossless data translation, type safety, and schema preservation across module boundaries.
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

MONOLITH_ROOT = Path("/data/data/com.termux/files/home/monolith")
TOWER_ROOT = Path("/data/data/com.termux/files/home/the-tower-of-babel")


@dataclass
class CapabilityQuery:
    domain: str
    requirement: str
    constraints: dict[str, Any] = field(default_factory=dict)
    prefer_verified: bool = True


@dataclass
class FederatedCapability:
    id: str
    source: str
    domain: str
    description: str
    entrypoint: str
    interface: str
    verified: bool
    confidence: str
    placement: Optional[dict[str, Any]] = None
    fitness_scores: Optional[dict[str, float]] = None


@dataclass
class ResolutionReceipt:
    query: CapabilityQuery
    timestamp: str
    capabilities_found: int
    monolith_matches: int
    tower_resolutions: int
    receipt_hash: str


def load_monolith_catalog(catalog_path: Path) -> dict[str, Any]:
    capabilities_3layer = catalog_path / "capabilities_3layer.json"
    if capabilities_3layer.exists():
        return json.loads(capabilities_3layer.read_text())
    return {}


def load_tower_registry(registry_path: Path) -> dict[str, Any]:
    registry_file = registry_path / "registry" / "tower.d" / "nextgen-innovations.json"
    if registry_file.exists():
        return json.loads(registry_file.read_text())
    return {}


def load_runtime_power_spine(spine_path: Path) -> dict[str, Any]:
    if spine_path.exists():
        return json.loads(spine_path.read_text())
    return {}


def query_monolith_catalog(query: CapabilityQuery, catalog: dict[str, Any]) -> list[FederatedCapability]:
    results = []
    layers = catalog.get("layers", {})

    for layer_name, layer_data in layers.items():
        if isinstance(layer_data, dict) and "repositories" in layer_data:
            for repo in layer_data["repositories"]:
                if isinstance(repo, dict):
                    repo_domain = repo.get("domain", "")
                    if query.domain.lower() in repo_domain.lower() or query.requirement.lower() in repo.get("description", "").lower():
                        results.append(FederatedCapability(
                            id=f"monolith:{layer_name}:{repo.get('name', 'unknown')}",
                            source="monolith",
                            domain=repo_domain,
                            description=repo.get("description", ""),
                            entrypoint=repo.get("entrypoint", ""),
                            interface=repo.get("interface", "unknown"),
                            verified=repo.get("verified", False),
                            confidence="high" if repo.get("verified") else "medium",
                        ))
    return results


def query_tower_registry(query: CapabilityQuery, registry: dict[str, Any]) -> list[FederatedCapability]:
    results = []
    innovations = registry.get("innovations", [])

    for innovation in innovations:
        if isinstance(innovation, dict):
            tech = innovation.get("technology", "")
            capability = innovation.get("capability", "")
            if query.requirement.lower() in capability.lower() or query.domain.lower() in tech.lower():
                results.append(FederatedCapability(
                    id=f"tower:{tech}:{capability[:32]}",
                    source="tower_of_babel",
                    domain=tech,
                    description=capability,
                    entrypoint=innovation.get("entrypoint", ""),
                    interface=innovation.get("interface", "unknown"),
                    verified=innovation.get("verified", False),
                    confidence="high" if innovation.get("verified") else "medium",
                    placement={"technology": tech, "floor": innovation.get("floor", 0)},
                ))
    return results


def federate_capabilities(query: CapabilityQuery, monolith_catalog: Path, tower_registry: Path) -> tuple[list[FederatedCapability], ResolutionReceipt]:
    monolith_data = load_monolith_catalog(monolith_catalog)
    tower_data = load_tower_registry(tower_registry)

    monolith_caps = query_monolith_catalog(query, monolith_data)
    tower_caps = query_tower_registry(query, tower_data)

    all_caps = monolith_caps + tower_caps

    receipt_data = f"{query.domain}:{query.requirement}:{len(all_caps)}:{datetime.now(timezone.utc).isoformat()}"
    import hashlib
    receipt_hash = hashlib.sha256(receipt_data.encode()).hexdigest()[:16]

    receipt = ResolutionReceipt(
        query=query,
        timestamp=datetime.now(timezone.utc).isoformat(),
        capabilities_found=len(all_caps),
        monolith_matches=len(monolith_caps),
        tower_resolutions=len(tower_caps),
        receipt_hash=receipt_hash,
    )

    return all_caps, receipt


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Federate capabilities across monolith and Tower of Babel")
    parser.add_argument("--monolith-catalog", default=str(MONOLITH_ROOT / "catalog"), help="Monolith catalog path")
    parser.add_argument("--tower-registry", default=str(TOWER_ROOT), help="Tower of Babel registry path")
    parser.add_argument("--domain", required=True, help="Capability domain")
    parser.add_argument("--requirement", required=True, help="Capability requirement")
    parser.add_argument("--constraints", default="{}", help="JSON constraints")
    parser.add_argument("--output", default="federation_result.json", help="Output file")
    args = parser.parse_args()

    query = CapabilityQuery(
        domain=args.domain,
        requirement=args.requirement,
        constraints=json.loads(args.constraints),
    )

    caps, receipt = federate_capabilities(query, Path(args.monolith_catalog), Path(args.tower_registry))

    result = {
        "query": asdict(query),
        "capabilities": [asdict(c) for c in caps],
        "receipt": asdict(receipt),
    }

    Path(args.output).write_text(json.dumps(result, indent=2))

    print(f"Federated {len(caps)} capabilities ({receipt.monolith_matches} monolith, {receipt.tower_resolutions} tower)")
    print(f"Receipt: {receipt.receipt_hash}")
    return 0


if __name__ == "__main__":
    sys.exit(main())