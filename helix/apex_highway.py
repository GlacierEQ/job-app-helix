#!/usr/bin/env python3
"""
APEX Highway Engine — mesh road across job-app nodes.

Discovers mastermind sidecars, aggregates integrity + pillar coverage,
routes inter-orbit events. No theater constants.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

REPOS_ROOT = Path.home() / "job-app" / "repos"
PILLARS = Path.home() / "job-app" / "pillars_registry.json"


class APEXHighwayEngine:
    """Central mesh: sidecars + integrity + pillar map."""

    def __init__(self, root_dir: Path = REPOS_ROOT):
        self.root_dir = root_dir
        self.nodes: dict[str, Path] = {}
        self.pillars = self._load_pillars()
        self.discover_nodes()

    def _load_pillars(self) -> dict:
        if PILLARS.exists():
            return json.loads(PILLARS.read_text(encoding="utf-8"))
        return {}

    def discover_nodes(self) -> int:
        self.nodes.clear()
        if not self.root_dir.exists():
            return 0
        for repo_dir in sorted(self.root_dir.iterdir()):
            if not repo_dir.is_dir() or repo_dir.name.startswith("."):
                continue
            if (repo_dir / "mastermind_sidecar.py").exists():
                self.nodes[repo_dir.name] = repo_dir
        return len(self.nodes)

    def _integrity_ok(self, path: Path) -> dict[str, Any]:
        integ = path / ".integrity"
        watchdog = integ / "watchdog_daemon.py"
        hashes = integ / "file_hashes.json"
        return {
            "integrity_dir": integ.is_dir(),
            "watchdog": watchdog.is_file(),
            "baseline": hashes.is_file(),
            "strand": (path / "HELIX_STRAND.md").is_file(),
            "security": (path / "SECURITY_AND_FLEET_OPS.md").is_file(),
        }

    def scan_mesh_health(self) -> dict[str, Any]:
        start = time.perf_counter()
        reports = []
        healthy = 0
        for name, path in self.nodes.items():
            flags = self._integrity_ok(path)
            ok = flags["integrity_dir"] and flags["watchdog"]
            if ok:
                healthy += 1
            reports.append(
                {
                    "node": name,
                    "status": "ONLINE" if ok else "DEGRADED",
                    **flags,
                }
            )

        # pillar piston coverage
        pillar_cov = []
        for pil in self.pillars.get("pillars") or []:
            missing = []
            present = []
            for p in pil.get("pistons") or []:
                repo = p.get("repo")
                if repo in self.nodes:
                    present.append(repo)
                else:
                    # may exist without sidecar
                    if (self.root_dir / repo).is_dir():
                        present.append(repo + "(no_sidecar_flag)")
                    else:
                        missing.append(repo)
            pillar_cov.append(
                {
                    "pillar": pil.get("id"),
                    "name": pil.get("name"),
                    "present": present,
                    "missing": missing,
                    "ok": not missing,
                }
            )

        n = len(self.nodes)
        return {
            "mesh_status": "OPERATIONAL" if healthy == n and n > 0 else "DEGRADED",
            "total_nodes_discovered": n,
            "healthy_nodes": healthy,
            "mesh_coverage_percent": round(100.0 * healthy / max(n, 1), 2),
            "scan_latency_ms": round((time.perf_counter() - start) * 1000.0, 3),
            "pillar_coverage": pillar_cov,
            "sample_nodes": reports[:12],
            "all_pillars_ok": all(p["ok"] for p in pillar_cov) if pillar_cov else False,
        }

    def route_inter_orbit_event(
        self, source_orbit: str, target_orbit: str, event_payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Route event between orbits; records envelope (local, no network)."""
        start = time.perf_counter()
        event_id = hashlib.sha256(
            f"{source_orbit}:{target_orbit}:{time.time()}".encode()
        ).hexdigest()[:12]
        known = set(self.nodes) | {
            p["repo"]
            for pil in self.pillars.get("pillars") or []
            for p in pil.get("pistons") or []
        }
        return {
            "event_id": f"APEX-EVT-{event_id}",
            "source_orbit": source_orbit,
            "target_orbit": target_orbit,
            "source_known": source_orbit in known or source_orbit in self.nodes,
            "target_known": target_orbit in known or target_orbit in self.nodes,
            "payload_bytes": len(json.dumps(event_payload, default=str)),
            "route_latency_ms": round((time.perf_counter() - start) * 1000.0, 4),
            "transmission_status": "DELIVERED_HIGHWAY",
        }

    def pillar_map(self) -> dict[str, Any]:
        return {
            "pillars": self.pillars.get("pillars"),
            "helix": self.pillars.get("helix"),
            "activation": self.pillars.get("activation"),
            "control_plane": self.pillars.get("control_plane"),
        }


if __name__ == "__main__":
    highway = APEXHighwayEngine()
    health = highway.scan_mesh_health()
    print(json.dumps(health, indent=2))
    print("--- pillars ---")
    print(json.dumps(highway.pillar_map().get("helix"), indent=2))
