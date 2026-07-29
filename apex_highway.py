#!/usr/bin/env python3
"""
APEX Highway Mesh Health Engine (apex_highway.py).
Scans 62 sidecar nodes across portfolio repositories.
"""
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent
PILLARS_FILE = ROOT / "docs" / "PORTFOLIO_PILLARS.json"

class APEXHighwayEngine:
    def __init__(self, root_dir: Path = None):
        self.root_dir = root_dir or (ROOT / "repos")
        self.pillars = self._load_pillars()
        self.nodes = {}

    def _load_pillars(self) -> dict:
        if PILLARS_FILE.exists():
            try:
                return json.loads(PILLARS_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass
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

    def _integrity_ok(self, path: Path) -> dict:
        integ = path / ".integrity"
        watchdog = integ / "watchdog_daemon.py"
        hashes = integ / "file_hashes.json"
        return {
            "integrity_dir": integ.is_dir(),
            "watchdog": watchdog.is_file(),
            "baseline": hashes.is_file(),
        }

    def scan_mesh_health(self) -> dict:
        start = time.perf_counter()
        self.discover_nodes()
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

        n = len(self.nodes)
        return {
            "mesh_status": "OPERATIONAL" if healthy == n and n > 0 else "DEGRADED",
            "total_nodes_discovered": n,
            "healthy_nodes": healthy,
            "mesh_coverage_percent": round(100.0 * healthy / max(n, 1), 2),
            "scan_latency_ms": round((time.perf_counter() - start) * 1000.0, 3),
            "sample_nodes": reports[:12],
        }

if __name__ == "__main__":
    engine = APEXHighwayEngine()
    print(json.dumps(engine.scan_mesh_health(), indent=2))
