#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path.home()/"job-app/repos/spacex-ground-network/src"))
from ground_net import Station, plan
ok = plan([Station("A", True, 12, 40), Station("B", True, 9, 30)], 50)
short = plan([Station("A", True, 12, 10)], 50)
assert ok["ok"] and not short["ok"]
print("PROOF_OK ground", ok["mbps"])
