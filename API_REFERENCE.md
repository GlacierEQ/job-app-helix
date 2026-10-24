# Job-App Helix — API Reference

**Version:** 2.0  
**Status:** PRODUCTION  
**All interfaces produce hash-bound receipts (L0-L5 compliant)**

---

## Core Capabilities (6)

### 1. portfolio.evidence_ledger

**Module:** `src/job_app_helix/evidence_ledger.py`  
**Entry Point:** `build_ledger(anchor_threshold: int = 8) -> Ledger`  
**CLI:** `python3 -m job_app_helix.evidence_ledger --anchor-threshold 8 --output ledger.json`

#### Python API
```python
from job_app_helix import build_ledger, EvidenceEntry, Ledger, write_ledger

ledger = build_ledger(anchor_threshold=8)
print(f"Total repos: {ledger.total_repos}")
print(f"Verified anchors: {ledger.verified_anchors}")
print(f"Merkle root: {ledger.merkle_root}")

for entry in ledger.entries:
    print(f"  {entry.repo}: worthy={entry.worthy}, verified={entry.verified}, gates={entry.gate_status}")

write_ledger(ledger, Path("evidence_ledger.json"))
```

#### Data Structures
```python
@dataclass
class EvidenceEntry:
    repo: str
    family: str
    worthy: int
    source_state: str
    evidence_hash: str
    gate_status: str
    verified: bool
    timestamp: str
    receipt_id: str

@dataclass
class Ledger:
    generated_at: str
    total_repos: int
    verified_anchors: int
    entries: List[EvidenceEntry]
    merkle_root: str
```

#### CLI Options
| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--repo-path` | str | `/data/data/com.termux/files/home/job-app-helix` | Portfolio root |
| `--anchor-threshold` | int | 8 | Worthy threshold for VERIFIED anchors |
| `--output` | str | `evidence_ledger.json` | Output file |

---

### 2. portfolio.capability_federation

**Module:** `src/job_app_helix/capability_federation.py`  
**Entry Point:** `federate_capabilities(query, monolith_catalog, tower_registry)`  
**CLI:** `python3 -m job_app_helix.capability_federation --domain legal_evidence --requirement ledger`

#### Python API
```python
from job_app_helix import federate_capabilities, CapabilityQuery, FederatedCapability, ResolutionReceipt
from pathlib import Path

query = CapabilityQuery(
    domain="legal_evidence",
    requirement="ledger",
    constraints={"verified_only": True},
    prefer_verified=True
)

capabilities, receipt = federate_capabilities(
    query,
    Path("/data/data/com.termux/files/home/monolith/catalog"),
    Path("/data/data/com.termux/files/home/the-tower-of-babel")
)

print(f"Found {len(capabilities)} capabilities")
print(f"Receipt: {receipt.receipt_hash}")

for cap in capabilities:
    print(f"  {cap.id}: {cap.description} (verified={cap.verified})")
```

#### Data Structures
```python
@dataclass
class CapabilityQuery:
    domain: str
    requirement: str
    constraints: Dict[str, Any] = field(default_factory=dict)
    prefer_verified: bool = True

@dataclass
class FederatedCapability:
    id: str
    source: str  # "monolith" | "tower_of_babel"
    domain: str
    description: str
    entrypoint: str
    interface: str
    verified: bool
    confidence: str
    placement: Optional[Dict[str, Any]] = None
    fitness_scores: Optional[Dict[str, float]] = None

@dataclass
class ResolutionReceipt:
    query: CapabilityQuery
    timestamp: str
    capabilities_found: int
    monolith_matches: int
    tower_resolutions: int
    receipt_hash: str
```

#### CLI Options
| Option | Type | Required | Description |
|--------|------|----------|-------------|
| `--domain` | str | Yes | Capability domain |
| `--requirement` | str | Yes | Capability requirement |
| `--constraints` | JSON | No | Constraints object |
| `--monolith-catalog` | str | No | Monolith catalog path |
| `--tower-registry` | str | No | Tower registry path |
| `--output` | str | No | Output file |

---

### 3. monolith.catalog_sync

**Module:** `src/job_app_helix/monolith_sync.py`  
**Entry Point:** `sync_monolith()` (CLI main)  
**CLI:** `python3 -m job_app_helix.monolith_sync --mode incremental --output sync_receipt.json`

#### Python API
```python
import subprocess, sys

# Uses CLI internally
cmd = [sys.executable, "-m", "job_app_helix.monolith_sync", "--mode", "incremental"]
result = subprocess.run(cmd, capture_output=True, text=True, cwd="/data/data/com.termux/files/home/job-app-helix")

if result.returncode == 0:
    print("Sync completed")
    print(result.stdout)
```

#### CLI Options
| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--monolith-root` | str | `/data/data/com.termux/files/home/monolith` | Monolith root |
| `--portfolio-manifest` | str | `manifests/unified_deserving_manifest.json` | Portfolio manifest |
| `--mode` | str | `incremental` | `full` \| `incremental` \| `verify` |
| `--output` | str | `sync_receipt.json` | Output receipt |

#### Sync Modes
| Mode | Description |
|------|-------------|
| `full` | Full rebuild of all 4 catalogs |
| `incremental` | Update only changed entries |
| `verify` | Validate without writing |

#### Updated Catalogs
1. `capabilities_3layer.json` — Layered capability index
2. `runtime_power_spine.json` — Source spines
3. `library.json` — Family index
4. `repo_excellence_state_machine.json` — Portfolio state

---

### 4. tower.capability_resolution

**Module:** `src/job_app_helix/tower_resolution.py`  
**Entry Point:** `resolve_placement(requirement)`  
**CLI:** `python3 -m job_app_helix.tower_resolution --requirement evidence_graph --domain legal_evidence`

#### Python API
```python
from job_app_helix import resolve_placement, CapabilityRequirement, PlacementDecision
from pathlib import Path

req = CapabilityRequirement(
    name="evidence_graph",
    domain="legal_evidence",
    performance_requirements={"memory_safety": True},
    constraints={"latency_ms": 100}
)

placement, candidates = resolve_placement(req, tower_root=Path("/data/data/com.termux/files/home/the-tower-of-babel"))

print(f"Selected: {placement.technology} (floor {placement.floor})")
print(f"Fitness: {placement.fitness_scores}")
print(f"Rationale: {placement.rationale}")

for c in candidates[:3]:
    print(f"  {c['technology']}: composite={c['fitness']['composite']:.4f}")
```

#### Data Structures
```python
@dataclass
class CapabilityRequirement:
    name: str
    domain: str
    performance_requirements: Dict[str, Any] = field(default_factory=dict)
    constraints: Dict[str, Any] = field(default_factory=dict)
    prefer_verified: bool = True

@dataclass
class PlacementDecision:
    technology: str
    floor: int
    capability: str
    entrypoint: str
    interface: str
    verified: bool
    fitness_scores: Dict[str, float]
    rationale: str
```

#### Fitness Dimensions (10)
| Dimension | Weight | Description |
|-----------|--------|-------------|
| `domain_match` | 1.0 | Domain alignment |
| `requirement_match` | 1.0 | Requirement keyword match |
| `floor_relevance` | 1.0 | Floor / 40.0 |
| `verified_bonus` | 1.0 | Verified technology |
| `memory_safety` | 1.0 | Rust/Zig/eBPF for memory safety |
| `concurrency` | 1.0 | Rust/Go/Erlang for concurrency |
| `determinism` | 1.0 | Rust/Coq/Lean for determinism |
| `composite` | — | Average of all |

#### CLI Options
| Option | Type | Required | Description |
|--------|------|----------|-------------|
| `--requirement` | str | Yes | Capability requirement name |
| `--domain` | str | Yes | Capability domain |
| `--perf` | JSON | No | Performance requirements |
| `--constraints` | JSON | No | Constraints object |
| `--tower-root` | str | No | Tower root path |
| `--output` | str | No | Output file |

---

### 5. helix.automation_engine

**Module:** `src/job_app_helix/automation_engine.py`  
**Entry Point:** `run_automation(automation, target, params)`  
**CLI:** `python3 -m job_app_helix.automation_engine --automation brainsync_index --target /path`

#### Python API
```python
from job_app_helix import run_automation, run_proof, AutomationResult

result = run_automation(
    automation="brainsync_index",
    target="/path/to/target",
    params={"verbose": True}
)

print(f"Success: {result.success}")
print(f"Receipt: {result.receipt_hash}")
print(f"Duration: {result.duration_ms}ms")
print(f"Output: {result.output}")

# Run proofs
proof_result = run_proof("proof_brainsync_kind_normalize", "/target", {})
```

#### Available Automations
| Automation | Script | Description |
|------------|--------|-------------|
| `brainsync_index` | `brainsync_index_skills.py` | Index skills into registry |
| `brainsync_normalize` | `brainsync_kind_normalize.py` | Normalize skill kinds |
| `brainsync_sanitize` | `brainsync_path_sanitize.py` | Sanitize paths |
| `crystallization_crawl` | `crystallization_crawler.py` | Crawl & crystallize evidence |
| `evidence_adapt` | `live_evidence_adapter.py` | Adapt live evidence |

#### Available Proofs
| Proof | Script | Description |
|-------|--------|-------------|
| `proof_brainsync_kind_normalize` | `proof_brainsync_kind_normalize.py` | Verify kind normalization |
| `proof_brainsync_skill_index` | `proof_brainsync_skill_index.py` | Verify skill indexing |

#### Data Structures
```python
@dataclass
class AutomationResult:
    automation: str
    target: str
    success: bool
    output: Any
    receipt_hash: str
    duration_ms: int
```

#### CLI Options
| Option | Type | Required | Description |
|--------|------|----------|-------------|
| `--automation` | str | Yes | Automation name |
| `--target` | str | Yes | Target path |
| `--params` | JSON | No | Parameters |
| `--output` | str | No | Output file |

---

### 6. evidence.bridge

**Module:** `src/job_app_helix/evidence_bridge.py`  
**Entry Point:** `bridge_evidence(evidence, target_spine, monolith_legal_path)`  
**CLI:** `python3 -m job_app_helix.evidence_bridge --all-from-ledger --target-spine case_1FDV`

#### Python API
```python
from job_app_helix import bridge_evidence, bridge_from_ledger, EvidenceItem, SpineEntry, BridgeReceipt
from pathlib import Path

# Bridge single evidence
evidence = EvidenceItem(
    id="evidence_001",
    source_repo="job-app-helix",
    source_path="manifests/evidence_ledger_unified.json",
    content_hash="abc123...",
    evidence_type="portfolio_evidence",
    timestamp="2026-09-04T05:30:00Z",
    metadata={"worthy": 9, "verified": True}
)

receipt = bridge_evidence(evidence, "case_1FDV", Path("/data/data/com.termux/files/home/monolith/catalog/legal_spines"))
print(f"Bridge receipt: {receipt.receipt_hash}")

# Bridge all from ledger
receipts = bridge_from_ledger("case_1FDV", Path("/data/data/com.termux/files/home/monolith/catalog/legal_spines"))
print(f"Bridged {len(receipts)} items")
```

#### Data Structures
```python
@dataclass
class EvidenceItem:
    id: str
    source_repo: str
    source_path: str
    content_hash: str
    evidence_type: str
    timestamp: str
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SpineEntry:
    spine_id: str
    case_id: str
    evidence_id: str
    content_hash: str
    bridge_hash: str
    timestamp: str
    provenance: Dict[str, Any] = field(default_factory=dict)

@dataclass
class BridgeReceipt:
    evidence_item: EvidenceItem
    target_spine: str
    spine_entry: SpineEntry
    timestamp: str
    receipt_hash: str
```

#### CLI Options
| Option | Type | Required | Description |
|--------|------|----------|-------------|
| `--evidence-id` | str | No | Specific evidence ID |
| `--target-spine` | str | Yes | Target legal spine |
| `--monolith-legal-path` | str | No | Legal spines path |
| `--all-from-ledger` | flag | No | Bridge all from ledger |
| `--output` | str | No | Output file |

---

## Forward-Deployed Capabilities

### Anthropic (10) — `job_app_helix.forward_deployed.anthropic`

```python
from job_app_helix.forward_deployed.anthropic import (
    create_anthropic_architect, ContainmentPredicate
)

arch = create_anthropic_architect(config_path=Path("config/anthropic.json"))

# Constitutional AI
result = arch.synthesize_constitution([
    {"id": "no_harm", "principle": "Do not help with harmful activities", "category": "safety", "priority": 1}
])

# CAI Critique
critique = arch.run_cai_critique("I can help with that.", {})

# Containment
p = ContainmentPredicate(id="no_exfil", boundary_action="network_egress", 
    state_precondition={"data": "sensitive"}, state_postcondition={"network_egress": "blocked"})
containment = arch.verify_containment_predicate(p)

# Adversarial Eval
eval_result = arch.run_adversarial_eval(None, "eval_awareness_browsecomp", [])

# Agent Skill
skill = arch.design_agent_skill("analyzer", "static_analysis", "high")

# Dual Sandbox
sandbox = arch.deploy_dual_sandbox({"agent": "analyzer"})

# All return: {"receipt_id": "...", ...}
# Verify: arch.verify_receipt(receipt_id)
```

### NVIDIA (7) — `job_app_helix.forward_deployed.nvidia`

```python
from job_app_helix.forward_deployed.nvidia import (
    create_nvidia_architect, KernelSpec, GPUTarget, MoEConfig, NVLinkTopology
)

arch = create_nvidia_architect(config_path=Path("config/nvidia.json"))

# FP4 Optimization
kernel = KernelSpec(name="moe_gemm", target=GPUTarget.B200, precision="fp4", 
    operation="moe", tile_config={}, warp_config={}, shared_memory_kb=48, registers_per_thread=32)
fp4 = arch.optimize_fp4_kernel(kernel)  # 5x speedup

# MoE Grouped GEMM
moe = MoEConfig(num_experts=8, expert_parallelism=2, token_parallelism=4, grouped_gemm=True, fp4_enabled=True)
moe_result = arch.optimize_moe_grouped_gemm(moe)  # 5x vs H100 FP16

# CUDA Graphs Conditional
graph = arch.auto_generate_cuda_graph([
    {"kernel": "mlp", "type": "conditional", "condition": "seq_len > 4096"}
])
cg = arch.build_cuda_graph_conditional(graph)

# TensorRT-LLM
trt = arch.tune_tensorrt_llm("llama-3.1-70b", GPUTarget.B200, "fp4")

# NVLink
nvlink = NVLinkTopology(gpus_per_node=8, nodes=1, nvlink_gen=5, nvlink_switch=False, bandwidth_tbps=1.8)
nl = arch.design_nvlink_topology(nvlink)

# Autotune
autotune = arch.autotune_kernel("moe_gemm", GPUTarget.B200, {"tile_m": [64,128]})

# Power/Perf
power = arch.profile_power_performance("moe", GPUTarget.B200, 60)

# All return: {"receipt_id": "...", ...}
# Verify: arch.verify_receipt(receipt_id)
```

### SpaceX (7) — `job_app_helix.forward_deployed.spacex`

```python
from job_app_helix.forward_deployed.spacex import (
    create_spacex_architect, FlightSoftwareConfig, VehicleStage, EngineType,
    AIFlightControllerConfig, EngineOutScenario, StageSeparationEvent, HITLTestbedConfig
)

arch = create_spacex_architect(config_path=Path("config/spacex.json"))

# Flight Software
fs = FlightSoftwareConfig(vehicle=VehicleStage.SUPER_HEAVY, engine_count=33, 
    engine_type=EngineType.RAPTOR_V3, control_frequency_hz=1000, 
    redundancy_level="triplex", languages=["C++","Rust"], safety_class="Class A")
fs_result = arch.design_flight_software(fs)

# AI Flight Controller
ai = AIFlightControllerConfig(sensor_inputs=5000, decision_latency_ms=100,
    attitude_adjustment_rate_hz=1000, human_intervention_reduction=10000,
    fault_tolerance="triplex_with_fallback")
ai_result = arch.design_ai_flight_controller(ai)

# Engine-Out
eo = EngineOutScenario(failed_engines=2, total_engines=33,
    compensation_strategy="throttle_up_remaining + trajectory_reopt",
    throttle_adjustment_pct=10, burn_time_extension_sec=5, mission_success=True)
eo_result = arch.design_engine_out_compensation(eo)

# Stage Separation
ss = StageSeparationEvent(separation_time_sec=165.0, impulse_vector=(1000,0,500),
    debris_risk=0.15, clean_separation=True, software_adjustments=["adaptive_timing"])
ss_result = arch.optimize_stage_separation(ss)

# FTS
fts = arch.harden_flight_termination(VehicleStage.STARSHIP, 100)

# HITL
hitl = HITLTestbedConfig(vehicle=VehicleStage.STARSHIP, 
    hardware_components=["flight_computer","avionics","telemetry","actuators"],
    simulation_fidelity="high", ci_integration=True, automated_regression=True, test_duration_minutes=30)
hitl_result = arch.configure_hitl_testbed(hitl)

# Refueling
refuel = arch.plan_in_space_refueling("Artemis III", "LEO", 1200000)

# All return: {"receipt_id": "...", ...}
# Verify: arch.verify_receipt(receipt_id)
```

---

## Agent CLI

**Module:** `src/job_app_helix/agent_cli.py`  
**Entry Point:** `agent_main()`

```bash
# List workflows
python3 -m job_app_helix.agent_cli workflow --list

# Execute workflow
python3 -m job_app_helix.agent_cli workflow full-portfolio-cycle --inputs '{}'

# List capabilities
python3 -m job_app_helix.agent_cli capability --list

# Execute capability
python3 -m job_app_helix.agent_cli capability portfolio.evidence_ledger build_ledger --inputs '{"anchor_threshold": 8}'

# Verify receipt
python3 -m job_app_helix.agent_cli receipt abc123def456

# Show config
python3 -m job_app_helix.agent_cli config --mode capability-build
```

---

## Configuration Schemas

### Anthropic Config (`config/anthropic.json`)
```json
{
  "model_family": "claude",
  "constitution_version": "2026.1",
  "interpretability_methods": ["attribution_graphs", "autoencoders", "persona_vectors"],
  "containment_verification": "dafny",
  "eval_framework": "adversarial_browsecomp",
  "mcp_ecosystem": true,
  "sandbox_mode": "dual_isolation"
}
```

### NVIDIA Config (`config/nvidia.json`)
```json
{
  "target_architecture": "blackwell",
  "cuda_version": "12.9",
  "cutlass_version": "3.5",
  "tensorrt_llm_version": "0.12",
  "nsight_version": "2025.1",
  "default_precision": "fp4",
  "fp4_enabled": true,
  "power_limit_watts": 1000
}
```

### SpaceX Config (`config/spacex.json`)
```json
{
  "default_vehicle": "starship",
  "default_engine": "raptor_v3",
  "control_frequency_hz": 1000,
  "redundancy": "triplex",
  "languages": ["C++", "Rust"],
  "safety_class": "Class A",
  "ai_latency_target_ms": 100,
  "hitl_automation": true
}
```

---

## Receipt Verification

```python
# All capability classes have:
arch.verify_receipt(receipt_id)  # Returns True/False
arch.get_receipt_chain()  # Returns list of receipt_ids

# Agent CLI
python3 -m job_app_helix.agent_cli receipt <receipt_id>

# Portfolio root receipt verification
import hashlib, json
with open("receipt.json") as f: r = json.load(f)
rc = r.copy(); del rc["receipt_sha256"]
assert hashlib.sha256(json.dumps(rc, sort_keys=True).encode()).hexdigest() == r["receipt_sha256"]
```

---

*API Reference v2.0 — All interfaces produce verifiable hash-bound receipts*