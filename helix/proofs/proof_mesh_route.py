#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path.home()/"job-app/repos/spacex-satellite-mesh/src"))
from mesh_route import shortest_path
g = {"A": {"B": 1}, "B": {"C": 1}, "C": {}}
p = shortest_path(g, "A", "C")
assert p["ok"] and p["path"][0] == "A" and p["path"][-1] == "C"
none = shortest_path({"A": {}}, "A", "Z")
assert not none["ok"]
print("PROOF_OK mesh", p["path"], p["cost"])
