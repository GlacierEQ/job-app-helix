#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path.home()/"job-app/repos/deepmind-tpu-mesh-optimizer/src"))
from tpu_mesh_optimizer import TPUMeshRingOptimizer
r = TPUMeshRingOptimizer(64, 4800.0).optimize_ring_attention(65536)
assert "transfer_ms" in r and "compute_ms" in r
assert r.get("status")
assert "answer" not in r
print("PROOF_OK tpu", r["status"], r.get("ici_hide_percent"))
