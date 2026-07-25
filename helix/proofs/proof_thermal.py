#!/usr/bin/env python3
import importlib.util, sys
from pathlib import Path
p = Path.home()/"job-app/repos/xai-colossus-cooling/connectors/cooling-plant/thermal_reality.py"
spec = importlib.util.spec_from_file_location("thermal_reality", p)
m = importlib.util.module_from_spec(spec)
sys.modules["thermal_reality"] = m
spec.loader.exec_module(m)
# energy identity
st = m.ThermalState(0.004184, 1.0, 25.0, 26.0, 0.001)
assert abs(st.heat_reject_mw - 0.004184) < 1e-6
crit = m.assess_loop(50.0, 10.0, 25.0, 26.0, 1.0)
assert crit["status"] == "CRITICAL", crit
ok = m.assess_loop(0.5, 5000.0, 25.0, 30.0, 0.05, 0.01)
assert ok["status"] == "NOMINAL", ok
print("PROOF_OK thermal", ok["heat_margin_mw"])
