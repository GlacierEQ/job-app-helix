#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path.home()/"job-app/repos/spacex-propulsion-monitor/src"))
from prop_health import Sample, health
g = health(Sample(0.98, 0.02, 3.0))
r = health(Sample(0.55, 0.2, 18.0))
assert g["status"] == "GREEN", g
assert r["status"] == "RED", r
assert "answer" not in g
print("PROOF_OK prop", g["health"], r["status"])
