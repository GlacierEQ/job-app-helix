#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path.home()/"GlacierEQ_Swarm/automations"))
# prefer helix package copy
sys.path.insert(0, str(Path.home()/"job-app/helix/automations"))
import importlib.util
p = Path.home()/"GlacierEQ_Swarm/automations/jobapp_helix_spiral.py"
spec = importlib.util.spec_from_file_location("jobapp_helix_spiral", p)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
r = m.run_launch_campaign()
assert r.get("ok") is True, r
assert r.get("campaign_decision") in ("GO", "NO-GO")
assert "flight" in r.get("sub_results", {})
print("PROOF_OK launch_campaign", r.get("campaign_decision"))
