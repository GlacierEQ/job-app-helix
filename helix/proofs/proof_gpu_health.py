#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path.home()/"job-app/repos/nvidia-gpu-health/src"))
from gpu_health import GpuSample, health_index
good = health_index(GpuSample(temp_c=40, power_w=200, sm_util=0.5, mem_util=0.4))
bad = health_index(GpuSample(temp_c=90, power_w=800, sm_util=0.99, mem_util=0.99, ecc_count=20))
assert good["status"] in ("OPTIMAL", "NOMINAL"), good
assert bad["status"] == "CRITICAL", bad
assert good["health_index"] > bad["health_index"]
print("PROOF_OK gpu_health", good["status"], bad["status"])
