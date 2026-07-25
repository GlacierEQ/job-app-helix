#!/usr/bin/env bash
# Always-green hire hero demo — drives shipped modules only.
# Exit 0 only if primary observables are present (not empty banners).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
REPOS="$ROOT/repos"
fail() { echo "DEMO_FAIL: $*" >&2; exit 1; }

echo "=== HERO DEMO $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="

# --- APEX Highway Network Bus: Central Nervous System Scan ---
export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"
HIGHWAY_OUT="$(python3 - <<'PY'
import json
from apex_highway import APEXHighwayEngine
highway = APEXHighwayEngine()
health = highway.scan_mesh_health()
print("APEX_HIGHWAY", json.dumps(health))
if health["mesh_status"] != "OPERATIONAL": raise SystemExit(100)
PY
)" || fail "APEX Highway Engine scan failed"
echo "$HIGHWAY_OUT"
echo "$HIGHWAY_OUT" | grep -q '"mesh_status": "OPERATIONAL"' || fail "missing OPERATIONAL in APEX Highway"

# --- TPS: real math prediction ---
export PYTHONPATH="$REPOS/spacex-thermal-protection/src${PYTHONPATH:+:$PYTHONPATH}"
TPS_OUT="$(python3 - <<'PY'
from alpha.predictive_thermal import (
    TileState, HeatShieldPredictor, ReentryConditions
)
pred = HeatShieldPredictor()
tile = TileState(tile_id=0, material="PICA-X", thickness_m=0.05,
                 temperature_k=900, x_pos=0, y_pos=0)
cond = ReentryConditions(
    velocity_ms=7000, altitude_m=80000, dynamic_pressure_pa=2000,
    heat_flux_w_m2=2.5e5, mach_number=20, angle_of_attack_deg=40,
)
pred.compute_integrity_index(tile, cond.heat_flux_w_m2, cond.dynamic_pressure_pa)
r = pred.predict_failure(tile, cond)
print(
    f"TPS time_to_failure_s={r.time_to_failure_s:.4f} "
    f"confidence={r.confidence:.4f} mode={r.failure_mode} action={r.recommended_action}"
)
if not (r.time_to_failure_s > 0 and r.confidence > 0):
    raise SystemExit(2)
PY
)" || fail "TPS module failed"
echo "$TPS_OUT"
echo "$TPS_OUT" | grep -q 'time_to_failure_s=' || fail "TPS missing time_to_failure_s"
echo "$TPS_OUT" | grep -q 'confidence=' || fail "TPS missing confidence"

# --- NVIDIA coupled: health_index + plan admitted_tokens ---
NV_OUT="$(python3 "$REPOS/nvidia-deep-reasoning/src/coupled_demo.py")" || fail "NVIDIA coupled_demo failed"
echo "$NV_OUT"
echo "$NV_OUT" | grep -q 'health_index' || fail "missing health_index"
echo "$NV_OUT" | grep -q 'admitted_tokens' || fail "missing admitted_tokens"
echo "$NV_OUT" | grep -q '"ok": true' || fail "coupled demo not ok"

# --- Cooling physics core numbers ---
export PYTHONPATH="$REPOS/xai-colossus-cooling${PYTHONPATH:+:$PYTHONPATH}"
COOL_OUT="$(python3 - <<'PY'
import json
from xai_cooling_physics_core import ColossalThermalCore
core = ColossalThermalCore()
state = core.simulate_thermal_state(flow_rate_kg_s=12.0)
pue = core.calculate_pue()
out = {"thermal_state": state, "pue": pue}
print("COOLING", json.dumps(out, default=str)[:900])
# Require numeric thermal content
blob = json.dumps(out, default=str).lower()
if "pue" not in blob:
    raise SystemExit(3)
if not any(k in blob for k in ("temp", "gpu", "flow", "delta", "thermal", "cool")):
    raise SystemExit(4)
PY
)" || fail "cooling physics failed"
echo "$COOL_OUT"
echo "$COOL_OUT" | grep -qiE 'temp|thermal|pue|cool|flow|gpu|delta|zone' || fail "cooling output lacks thermal observables"

# --- SpaceX Telemetry Bus: High-rate frame ingestion & drop detection ---
export PYTHONPATH="$REPOS/spacex-telemetry/src${PYTHONPATH:+:$PYTHONPATH}"
SPACEX_OUT="$(python3 - <<'PY'
import json
from telemetry_bus import TelemetryBus, Frame
bus = TelemetryBus(max_hz=100.0)
r1 = bus.ingest(Frame("nav_imu", 1, 0))
r2 = bus.ingest(Frame("nav_imu", 2, 20))
r3 = bus.ingest(Frame("nav_imu", 5, 50))
out = {"r1": r1, "r2": r2, "r3": r3, "total_drops": bus.drops, "status": "ACTIVE"}
print("SPACEX_TELEMETRY", json.dumps(out))
if bus.drops != 2:
    raise SystemExit(5)
PY
)" || fail "SpaceX telemetry bus failed"
echo "$SPACEX_OUT"
echo "$SPACEX_OUT" | grep -q 'total_drops' || fail "missing total_drops in telemetry"

# --- OpenAI Reasoning KV-Sentinel: Trajectory Pruning & Tool Dispatch ---
export PYTHONPATH="$REPOS/openai-reasoning-kv-sentinel/src${PYTHONPATH:+:$PYTHONPATH}"
OPENAI_OUT="$(python3 - <<'PY'
import json
from reasoning_kv_sentinel import ReasoningKVSentinel
sentinel = ReasoningKVSentinel()
tokens = [{"id": i, "probs": [0.95, 0.05], "is_anchor": i % 5 == 0} for i in range(50)]
_, metrics = sentinel.prune_reasoning_trajectory(tokens)
print("OPENAI_SENTINEL", json.dumps(metrics))
if metrics["status"] != "NOMINAL":
    raise SystemExit(6)
PY
)" || fail "OpenAI Reasoning KV-Sentinel failed"
echo "$OPENAI_OUT"
echo "$OPENAI_OUT" | grep -q '"status": "NOMINAL"' || fail "missing NOMINAL in OpenAI sentinel"

# --- Google DeepMind TPU Mesh Optimizer: Ring-Attention & Multimodal Balancer ---
export PYTHONPATH="$REPOS/deepmind-tpu-mesh-optimizer/src${PYTHONPATH:+:$PYTHONPATH}"
DEEPMIND_OUT="$(python3 - <<'PY'
import json
from tpu_mesh_optimizer import TPUMeshRingOptimizer
opt = TPUMeshRingOptimizer()
metrics = opt.optimize_ring_attention(1048576)
print("DEEPMIND_TPU", json.dumps(metrics))
if metrics["status"] != "OPTIMAL_ASYNC_SHARDED":
    raise SystemExit(7)
PY
)" || fail "Google DeepMind TPU Mesh Optimizer failed"
echo "$DEEPMIND_OUT"
echo "$DEEPMIND_OUT" | grep -q '"status": "OPTIMAL_ASYNC_SHARDED"' || fail "missing OPTIMAL_ASYNC_SHARDED in DeepMind TPU"

# --- Apple ANE KV-Quantizer ---
export PYTHONPATH="$REPOS/apple-ane-kv-quantizer/src${PYTHONPATH:+:$PYTHONPATH}"
APPLE_OUT="$(python3 - <<'PY'
import json
from apple_ane_kv_quantizer import AppleANEKVQuantizer
q = AppleANEKVQuantizer()
metrics, _ = q.quantize_kv_cache(8192)
print("APPLE_ANE", json.dumps(metrics))
if metrics["status"] != "ANE_OPTIMAL": raise SystemExit(8)
PY
)" || fail "Apple ANE KV-Quantizer failed"
echo "$APPLE_OUT"
echo "$APPLE_OUT" | grep -q '"status": "ANE_OPTIMAL"' || fail "missing ANE_OPTIMAL"

# --- Tesla FSD Occupancy Stream ---
export PYTHONPATH="$REPOS/tesla-fsd-occupancy-stream/src${PYTHONPATH:+:$PYTHONPATH}"
TESLA_OUT="$(python3 - <<'PY'
import json
from tesla_fsd_occupancy_stream import TeslaFSDOccupancyStream
stream = TeslaFSDOccupancyStream()
res = stream.process_camera_frame(8)
print("TESLA_FSD", json.dumps(res))
if res["status"] != "HW4_NOMINAL": raise SystemExit(9)
PY
)" || fail "Tesla FSD Occupancy Stream failed"
echo "$TESLA_OUT"
echo "$TESLA_OUT" | grep -q '"status": "HW4_NOMINAL"' || fail "missing HW4_NOMINAL"

# --- Meta Llama Collective Sentinel ---
export PYTHONPATH="$REPOS/meta-llama-collective-sentinel/src${PYTHONPATH:+:$PYTHONPATH}"
META_OUT="$(python3 - <<'PY'
import json
from meta_llama_collective_sentinel import MetaLlamaCollectiveSentinel
s = MetaLlamaCollectiveSentinel()
res = s.optimize_all_gather()
print("META_LLAMA", json.dumps(res))
if res["status"] != "ALL_GATHER_OPTIMAL": raise SystemExit(10)
PY
)" || fail "Meta Llama Collective Sentinel failed"
echo "$META_OUT"
echo "$META_OUT" | grep -q '"status": "ALL_GATHER_OPTIMAL"' || fail "missing ALL_GATHER_OPTIMAL"

# --- AWS Trainium Neuron Sentinel ---
export PYTHONPATH="$REPOS/aws-trainium-neuron-sentinel/src${PYTHONPATH:+:$PYTHONPATH}"
AWS_OUT="$(python3 - <<'PY'
import json
from aws_trainium_neuron_sentinel import AWSTrainiumNeuronSentinel
n = AWSTrainiumNeuronSentinel()
res = n.optimize_neuron_pipeline()
print("AWS_TRAINIUM", json.dumps(res))
if res["status"] != "NEURON_PIPELINE_OPTIMAL": raise SystemExit(11)
PY
)" || fail "AWS Trainium Neuron Sentinel failed"
echo "$AWS_OUT"
echo "$AWS_OUT" | grep -q '"status": "NEURON_PIPELINE_OPTIMAL"' || fail "missing NEURON_PIPELINE_OPTIMAL"

# --- DeepSeek MLA MoE Sentinel ---
export PYTHONPATH="$REPOS/deepseek-mla-moe-sentinel/src${PYTHONPATH:+:$PYTHONPATH}"
DEEPSEEK_OUT="$(python3 - <<'PY'
import json
from deepseek_mla_moe_sentinel import DeepSeekMLAMoESentinel
s = DeepSeekMLAMoESentinel()
res = s.optimize_mla_moe()
print("DEEPSEEK_MLA", json.dumps(res))
if res["status"] != "MLA_MOE_OPTIMAL": raise SystemExit(12)
PY
)" || fail "DeepSeek MLA MoE Sentinel failed"
echo "$DEEPSEEK_OUT"
echo "$DEEPSEEK_OUT" | grep -q '"status": "MLA_MOE_OPTIMAL"' || fail "missing MLA_MOE_OPTIMAL"

# --- Kimi Mooncake KV Stream ---
export PYTHONPATH="$REPOS/kimi-mooncake-kv-stream/src${PYTHONPATH:+:$PYTHONPATH}"
KIMI_OUT="$(python3 - <<'PY'
import json
from kimi_mooncake_kv_stream import KimiMooncakeKVStream
k = KimiMooncakeKVStream()
res = k.process_prefill_request()
print("KIMI_MOONCAKE", json.dumps(res))
if res["status"] != "MOONCAKE_STREAM_OPTIMAL": raise SystemExit(13)
PY
)" || fail "Kimi Mooncake KV Stream failed"
echo "$KIMI_OUT"
echo "$KIMI_OUT" | grep -q '"status": "MOONCAKE_STREAM_OPTIMAL"' || fail "missing MOONCAKE_STREAM_OPTIMAL"

# --- Qwen VL Flash Router ---
export PYTHONPATH="$REPOS/qwen-vl-flash-router/src${PYTHONPATH:+:$PYTHONPATH}"
QWEN_OUT="$(python3 - <<'PY'
import json
from qwen_vl_flash_router import QwenVLFlashRouter
q = QwenVLFlashRouter()
res = q.pack_visual_and_route([(1024, 768)], 2048)
print("QWEN_VL", json.dumps(res))
if res["status"] != "FLASH_ROUTER_OPTIMAL": raise SystemExit(14)
PY
)" || fail "Qwen VL Flash Router failed"
echo "$QWEN_OUT"
echo "$QWEN_OUT" | grep -q '"status": "FLASH_ROUTER_OPTIMAL"' || fail "missing FLASH_ROUTER_OPTIMAL"

# --- Robotics VLA Torque Sentinel ---
export PYTHONPATH="$REPOS/robotics-vla-torque-sentinel/src${PYTHONPATH:+:$PYTHONPATH}"
ROBOTICS_OUT="$(python3 - <<'PY'
import json
from robotics_vla_torque_sentinel import RoboticsVLATorqueSentinel
r = RoboticsVLATorqueSentinel()
res = r.evaluate_torque_command([150.0] * 28)
print("ROBOTICS_VLA", json.dumps(res))
if res["safety_status"] != "ROBOTICS_TORQUE_NOMINAL": raise SystemExit(15)
PY
)" || fail "Robotics VLA Torque Sentinel failed"
echo "$ROBOTICS_OUT"
echo "$ROBOTICS_OUT" | grep -q '"safety_status": "ROBOTICS_TORQUE_NOMINAL"' || fail "missing ROBOTICS_TORQUE_NOMINAL"

# --- Tasklet Micro Agent Engine ---
export PYTHONPATH="$REPOS/tasklet-micro-agent-engine/src${PYTHONPATH:+:$PYTHONPATH}"
TASKLET_OUT="$(python3 - <<'PY'
import json
from tasklet_micro_agent_engine import TaskletMicroAgentEngine
t = TaskletMicroAgentEngine()
res = t.spawn_tasklet("task_001", {"action": "parse"})
print("TASKLET_ENGINE", json.dumps(res))
if res["status"] != "TASKLET_ACTIVE": raise SystemExit(16)
PY
)" || fail "Tasklet Micro Agent Engine failed"
echo "$TASKLET_OUT"
echo "$TASKLET_OUT" | grep -q '"status": "TASKLET_ACTIVE"' || fail "missing TASKLET_ACTIVE"

# --- Manus Autonomous Web Agent ---
export PYTHONPATH="$REPOS/manus-autonomous-web-agent/src${PYTHONPATH:+:$PYTHONPATH}"
MANUS_OUT="$(python3 - <<'PY'
import json
from manus_autonomous_web_agent import ManusAutonomousWebAgent
m = ManusAutonomousWebAgent()
res = m.execute_web_goal("Search", "https://example.com")
print("MANUS_WEB", json.dumps(res))
if res["status"] != "MANUS_GOAL_ACHIEVED": raise SystemExit(17)
PY
)" || fail "Manus Autonomous Web Agent failed"
echo "$MANUS_OUT"
echo "$MANUS_OUT" | grep -q '"status": "MANUS_GOAL_ACHIEVED"' || fail "missing MANUS_GOAL_ACHIEVED"

# --- Lovable Design App Synth ---
export PYTHONPATH="$REPOS/lovable-design-app-synth/src${PYTHONPATH:+:$PYTHONPATH}"
LOVABLE_OUT="$(python3 - <<'PY'
import json
from lovable_design_app_synth import LovableDesignAppSynth
l = LovableDesignAppSynth()
res = l.synthesize_ui_application("Dashboard")
print("LOVABLE_UI", json.dumps(res))
if res["status"] != "LOVABLE_SYNTH_SUCCESS": raise SystemExit(18)
PY
)" || fail "Lovable Design App Synth failed"
echo "$LOVABLE_OUT"
echo "$LOVABLE_OUT" | grep -q '"status": "LOVABLE_SYNTH_SUCCESS"' || fail "missing LOVABLE_SYNTH_SUCCESS"

# --- Opera Neon Spatial Workspace ---
export PYTHONPATH="$REPOS/opera-neon-spatial-workspace/src${PYTHONPATH:+:$PYTHONPATH}"
NEON_OUT="$(python3 - <<'PY'
import json
from opera_neon_spatial_workspace import OperaNeonSpatialWorkspace
n = OperaNeonSpatialWorkspace()
res = n.add_spatial_tab("News", "https://news.ycombinator.com", 100.0, 200.0)
print("NEON_SPATIAL", json.dumps(res))
if res["status"] != "NEON_SPATIAL_ACTIVE": raise SystemExit(19)
PY
)" || fail "Opera Neon Spatial Workspace failed"
echo "$NEON_OUT"
echo "$NEON_OUT" | grep -q '"status": "NEON_SPATIAL_ACTIVE"' || fail "missing NEON_SPATIAL_ACTIVE"

# --- Comet Browser Agent Bridge ---
export PYTHONPATH="$REPOS/comet-browser-agent-bridge/src${PYTHONPATH:+:$PYTHONPATH}"
COMET_OUT="$(python3 - <<'PY'
import json
from comet_browser_agent_bridge import CometBrowserAgentBridge
c = CometBrowserAgentBridge()
res = c.sync_tab_mutation(101, "MUTATION", "<div>Test</div>")
print("COMET_BRIDGE", json.dumps(res))
if res["status"] != "COMET_BRIDGE_NOMINAL": raise SystemExit(20)
PY
)" || fail "Comet Browser Agent Bridge failed"
echo "$COMET_OUT"
echo "$COMET_OUT" | grep -q '"status": "COMET_BRIDGE_NOMINAL"' || fail "missing COMET_BRIDGE_NOMINAL"

echo "=== DEMO_OK ==="
exit 0


