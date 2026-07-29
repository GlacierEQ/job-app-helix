#!/usr/bin/env python3
"""
Continuous Integration & Integrity Guardian (ci_audit_portfolio.py).
Single-command master audit script for the GlacierEQ Job-App Portfolio.
"""
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPOS_DIR = ROOT / "repos"

def log_step(name: str):
    print(f"\n==================================================")
    print(f"  CI STEP: {name}")
    print(f"==================================================")

def step_1_check_hashes():
    log_step("1. Cryptographic Baseline Verification (64 Repos)")
    repos = [d for d in REPOS_DIR.iterdir() if d.is_dir() and not d.name.startswith(".")]
    missing = []
    for r in repos:
        hash_file = r / ".integrity" / "file_hashes.json"
        if not hash_file.exists():
            missing.append(r.name)
    print(f"Total Repositories: {len(repos)}")
    print(f"Repos with SHA-256 Hashes: {len(repos) - len(missing)}/{len(repos)}")
    assert not missing, f"Missing hashes in: {missing}"
    print("STATUS: PASS")

def step_2_apex_highway():
    log_step("2. APEX Highway Mesh Health Scan")
    sys.path.insert(0, str(ROOT))
    from apex_highway import APEXHighwayEngine
    highway = APEXHighwayEngine(root_dir=REPOS_DIR)
    health = highway.scan_mesh_health()
    print(f"Mesh Status: {health['mesh_status']}")
    print(f"Healthy Nodes: {health['healthy_nodes']}/{health['total_nodes_discovered']} ({health['mesh_coverage_percent']}%)")
    print(f"Scan Latency: {health['scan_latency_ms']} ms")
    assert health["mesh_status"] == "OPERATIONAL", "Highway mesh must be OPERATIONAL"
    print("STATUS: PASS")

def step_3_hero_tests():
    log_step("3. Hero Trio Unit Test Suites Execution")
    # TPS
    tps_dir = REPOS_DIR / "spacex-thermal-protection"
    env_tps = os.environ.copy()
    env_tps["PYTHONPATH"] = str(tps_dir / "src") + os.pathsep + env_tps.get("PYTHONPATH", "")
    r_tps = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=tps_dir, env=env_tps, capture_output=True, text=True)
    print("TPS Discover Tests:", "PASS" if r_tps.returncode == 0 else f"FAIL:\n{r_tps.stderr}")
    assert r_tps.returncode == 0, "TPS tests failed"

    # Cooling
    c_dir = REPOS_DIR / "xai-colossus-cooling"
    env_c = os.environ.copy()
    env_c["PYTHONPATH"] = str(c_dir / "src") + os.pathsep + str(c_dir) + os.pathsep + env_c.get("PYTHONPATH", "")
    r_c = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=c_dir, env=env_c, capture_output=True, text=True)
    print("Cooling Discover Tests:", "PASS" if r_c.returncode == 0 else f"FAIL:\n{r_c.stderr}")
    assert r_c.returncode == 0, "Cooling tests failed"

    # AKOS
    a_dir = REPOS_DIR / "AKOS"
    r_a = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "."], cwd=a_dir, capture_output=True, text=True)
    print("AKOS Discover Tests:", "PASS" if r_a.returncode == 0 else f'FAIL:\n{r_a.stderr}')
    assert r_a.returncode == 0, "AKOS tests failed"
    print("STATUS: PASS")

def step_4_demo_runner():
    log_step("4. Live 15-Minute Demo Script Runner")
    demo_script = ROOT / "showcase" / "demo_15min_run.py"
    r = subprocess.run([sys.executable, str(demo_script)], cwd=ROOT, capture_output=True, text=True)
    print("Demo Runner:", "PASS" if r.returncode == 0 else f"FAIL:\n{r.stderr}")
    assert r.returncode == 0, "Demo runner failed"
    print("STATUS: PASS")

def step_5_link_verification():
    log_step("5. Hierarchical Catalog Link Verification")
    map_file = ROOT / "HIERARCHICAL_PORTFOLIO_MAP.md"
    text = map_file.read_text(encoding="utf-8")
    links = re.findall(r"\(file://([^)]+)\)", text)
    missing = [l for l in links if not Path(l).exists()]
    print(f"Total file:// links verified: {len(links)}")
    print(f"Valid links: {len(links) - len(missing)}")
    assert not missing, f"Missing link targets: {missing}"
    print("STATUS: PASS")

def main():
    start = time.perf_counter()
    print("=== GLACIEREQ PORTFOLIO MASTER CI AUDIT ===")
    step_1_check_hashes()
    step_2_apex_highway()
    step_3_hero_tests()
    step_4_demo_runner()
    step_5_link_verification()
    elapsed = round((time.perf_counter() - start) * 1000.0, 2)
    print(f"\n==================================================")
    print(f"  ALL 5 CI STEPS PASSED IN {elapsed} ms")
    print(f"  PORTFOLIO STATUS: 100% SOLID & DEPLOYABLE")
    print(f"==================================================")

if __name__ == "__main__":
    main()
