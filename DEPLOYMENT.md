# Job-App Helix — Deployment Guide

**Version:** 2.0  
**Status:** PRODUCTION  
**Environments:** Development → Staging → Production  
**Deployment Unit:** Forward-deployed capabilities + Agent framework

---

## Overview

This guide covers deployment of Job-App Helix forward-deployed capabilities to target company environments (Anthropic, NVIDIA, SpaceX) and the agent engineering framework.

### Deployment Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DEPLOYMENT PIPELINE                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  DEV (local)          STAGING                  PRODUCTION                   │
│  ──────────           ─────────                ───────────                  │
│                                                                             │
│  ┌──────────┐       ┌──────────┐            ┌──────────┐                  │
│  │ Code +   │  ──▶  │ Full     │    ──▶     │ Deploy   │                  │
│  │ Tests    │       │ Validators│           │ Capability│                 │
│  └──────────┘       └──────────┘            └──────────┘                  │
│       │                   │                      │                        │
│       ▼                   ▼                      ▼                        │
│  Receipt Chain       Receipt Chain          Live Receipts               │
│  Verified            Verified              Continuous Verification      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Prerequisites

### System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| Python | 3.11+ | 3.12+ |
| Memory | 4 GB | 16 GB |
| Disk | 10 GB | 50 GB |
| Network | HTTPS to GitHub | Low latency to target APIs |

### Required Services

| Service | Purpose | Config |
|---------|---------|--------|
| GitHub API | Repository access | `GITHUB_TOKEN` |
| Monolith | Catalog sync | `MONOLITH_ROOT` |
| Tower of Babel | Capability resolution | `TOWER_ROOT` |
| Legal Spines | Evidence bridge | `LEGAL_SPINES_PATH` |
| Pointer Index | O(1) lookups | `ASPEN_GROVE_INDEX` |

### Environment Variables

```bash
export MONOLITH_ROOT="/data/data/com.termux/files/home/monolith"
export TOWER_ROOT="/data/data/com.termux/files/home/the-tower-of-babel"
export LEGAL_SPINES_PATH="/data/data/com.termux/files/home/monolith/catalog/legal_spines"
export ASPEN_GROVE_INDEX="/tmp/aspen_grove_pointer_index.json"
export PYTHONPATH="/data/data/com.termux/files/home/job-app-helix/src"
export GITHUB_TOKEN="ghp_..."  # For monolith sync
```

---

## Development Environment

### Local Setup

```bash
# Clone
git clone https://github.com/GlacierEQ/job-app-helix.git
cd job-app-helix

# Install dependencies
pip install -r requirements.txt  # or pip install -e .

# Verify installation
PYTHONPATH=src python3 -c "from job_app_helix import *; print('OK')"

# Run validators
python3 scripts/validate_application_registry.py
python3 scripts/validate_portfolio_root_truth.py
python3 scripts/validate_live_repository_links.py

# Run tests
PYTHONPATH=src python3 -m pytest tests/ -q

# Test agent CLI
PYTHONPATH=src python3 -m job_app_helix.agent_cli --help
```

### IDE Configuration

```json
// .vscode/settings.json
{
  "python.defaultInterpreterPath": "/usr/bin/python3",
  "python.analysis.extraPaths": ["src"],
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": ["tests"]
}
```

---

## Forward-Deployed Capability Deployment

### Anthropic Deployment

#### Target Environment
- **Integration:** Constitutional AI pipeline, MCP ecosystem
- **Security:** Dual-isolation sandbox (process + VM)
- **Access:** Anthropic internal APIs, Claude models

#### Deployment Steps

```bash
# 1. Configure
cat > config/anthropic.json << 'EOF'
{
  "model_family": "claude",
  "constitution_version": "2026.1",
  "interpretability_methods": ["attribution_graphs", "autoencoders", "persona_vectors"],
  "containment_verification": "dafny",
  "eval_framework": "adversarial_browsecomp",
  "mcp_ecosystem": true,
  "sandbox_mode": "dual_isolation"
}
EOF

# 2. Test capability
PYTHONPATH=src python3 -c "
from job_app_helix.forward_deployed.anthropic import create_anthropic_architect
arch = create_anthropic_architect(Path('config/anthropic.json'))
result = arch.synthesize_constitution([
    {'id': 'no_harm', 'principle': 'Do not help with harmful activities', 'category': 'safety', 'priority': 1}
])
print('Receipt:', result['receipt_id'])
assert arch.verify_receipt(result['receipt_id'])
"

# 3. Deploy to Anthropic MCP registry
# (Internal Anthropic process - register skill manifest)
python3 -m job_app_helix.agent_cli capability anthropic.agent_skill design_agent_skill --inputs '{
  "skill_name": "constitutional_ai_feedback",
  "capability": "constitutional_ai_scaling",
  "security_level": "high"
}'

# 4. Verify deployment
python3 -m job_app_helix.agent_cli receipt <receipt_id>
```

#### Security Checklist

- [ ] Dual-isolation sandbox configured (inner: process+seccomp, outer: VM)
- [ ] MCP permissions minimal (read_files, code_execution only)
- [ ] DAFNY proofs verified for containment predicates
- [ ] Adversarial eval framework deployed
- [ ] Audit logging enabled on all tool calls

### NVIDIA Deployment

#### Target Environment
- **Integration:** CUDA/TensorRT pipeline, Blackwell GPUs
- **Security:** Single isolation (GPU workloads)
- **Access:** NVIDIA internal clusters, H100/B200/GB200

#### Deployment Steps

```bash
# 1. Configure
cat > config/nvidia.json << 'EOF'
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
EOF

# 2. Test capability
PYTHONPATH=src python3 -c "
from job_app_helix.forward_deployed.nvidia import create_nvidia_architect, KernelSpec, GPUTarget
arch = create_nvidia_architect(Path('config/nvidia.json'))
kernel = KernelSpec(name='moe_gemm', target=GPUTarget.B200, precision='fp4', operation='moe', tile_config={}, warp_config={}, shared_memory_kb=48, registers_per_thread=32)
result = arch.optimize_fp4_kernel(kernel)
print('FP4 speedup:', result['expected_speedup'], 'receipt:', result['receipt_id'])
assert arch.verify_receipt(result['receipt_id'])
"

# 3. Run benchmarks
python3 -m job_app_helix.agent_cli capability nvidia.benchmark benchmark --inputs '{
  "target": "./build",
  "metrics": ["throughput", "latency", "memory"],
  "baseline": "baseline.json"
}'

# 4. Deploy kernels to NVIDIA internal registry
# (Internal process - push optimized kernels)
```

#### Hardware Requirements

| GPU | FP4 Support | Tensor Cores | Power |
|-----|-------------|--------------|-------|
| H100 | No | 4th gen | 700W |
| H200 | No | 4th gen | 700W |
| B200 | Yes | 5th gen | 1000W |
| GB200 | Yes | 5th gen | 1000W |
| GB200 NVL72 | Yes | 5th gen | 1000W × 72 |

#### Cooling & Power

- **B200/GB200:** Direct liquid cooling required (20°C inlet, 45°C outlet, 2.5 LPM/GPU)
- **PDU:** 3-phase 415V/240V, N+1 redundancy
- **Floor loading:** Reinforced for 1000W/GPU

### SpaceX Deployment

#### Target Environment
- **Integration:** Starship flight software, HITL testbeds
- **Security:** Dual-isolation (flight safety critical)
- **Access:** SpaceX internal network, Falcon/Starship hardware

#### Deployment Steps

```bash
# 1. Configure
cat > config/spacex.json << 'EOF'
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
EOF

# 2. Test capability
PYTHONPATH=src python3 -c "
from job_app_helix.forward_deployed.spacex import create_spacex_architect, FlightSoftwareConfig, VehicleStage, EngineType
arch = create_spacex_architect(Path('config/spacex.json'))
fs = FlightSoftwareConfig(vehicle=VehicleStage.SUPER_HEAVY, engine_count=33, engine_type=EngineType.RAPTOR_V3, control_frequency_hz=1000, redundancy_level='triplex', languages=['C++','Rust'], safety_class='Class A')
result = arch.design_flight_software(fs)
print('Flight SW:', result['receipt_id'], 'redundancy:', result['architecture']['redundancy']['level'])
assert arch.verify_receipt(result['receipt_id'])
"

# 3. Run HITL regression
python3 -m job_app_helix.agent_cli workflow helix-automation-execution --inputs '{
  "automation": "hitl_regression",
  "target": "starship",
  "params": {"commit": "abc123"}
}'

# 4. Deploy to SpaceX flight software pipeline
# (Internal process - integrate with flight software build)
```

#### Safety Requirements

| Requirement | Standard |
|-------------|----------|
| Flight software | DO-178C Level A / NASA Class A |
| AI controller | Formal verification (model checking + reachability) |
| FTS | Dual-chain, 100ms response, linear shaped charge |
| HITL | Real flight computers, 6DOF physics |
| Engine-out | Monte Carlo 10,000 runs validated |

---

## Agent Framework Deployment

### Core Deployment

```bash
# 1. Deploy agent configuration
cp -r .agents/ /target/deployment/path/

# 2. Verify agent CLI
PYTHONPATH=/target/deployment/path/src python3 -m job_app_helix.agent_cli --help

# 3. Test workflow
PYTHONPATH=/target/deployment/path/src python3 -m job_app_helix.agent_cli workflow full-portfolio-cycle --inputs '{}'

# 4. Verify all capabilities registered
PYTHONPATH=/target/deployment/path/src python3 -m job_app_helix.agent_cli capability --list
```

### Configuration Files

| File | Target Path | Purpose |
|------|-------------|---------|
| `.agents/agent-config.yaml` | `/etc/job-app-helix/agent-config.yaml` | Full agent config |
| `.agents/modes.json` | `/etc/job-app-helix/modes.json` | Execution modes |
| `.agents/workflows.yaml` | `/etc/job-app-helix/workflows.yaml` | Workflow definitions |
| `.agents/skills/registry.yaml` | `/etc/job-app-helix/skills/registry.yaml` | Capability registry |

### Service Installation

```bash
# systemd service
cat > /etc/systemd/system/job-app-helix-agent.service << 'EOF'
[Unit]
Description=Job-App Helix Agent Framework
After=network.target

[Service]
Type=simple
User=job-app-helix
WorkingDirectory=/opt/job-app-helix
Environment=PYTHONPATH=/opt/job-app-helix/src
Environment=MONOLITH_ROOT=/data/monolith
Environment=TOWER_ROOT=/data/tower-of-babel
ExecStart=/usr/bin/python3 -m job_app_helix.agent_cli workflow full-portfolio-cycle --inputs '{}'
Restart=on-failure
RestartSec=30

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable job-app-helix-agent
systemctl start job-app-helix-agent
```

---

## Monolith & Tower Integration

### Monolith Catalog Sync

```bash
# Full sync (initial deployment)
python3 -m job_app_helix.agent_cli workflow monolith-catalog-sync --inputs '{"mode": "full"}'

# Incremental sync (scheduled every 4h)
python3 -m job_app_helix.agent_cli workflow monolith-catalog-sync --inputs '{"mode": "incremental"}'

# Verify
python3 -m job_app_helix.agent_cli workflow monolith-catalog-sync --inputs '{"mode": "verify"}'
```

### Tower of Babel Resolution

```bash
# Resolve capability placement
python3 -m job_app_helix.agent_cli capability tower.capability_resolution resolve_placement --inputs '{
  "requirement": "evidence_graph",
  "domain": "legal_evidence",
  "performance_requirements": {"memory_safety": true}
}'
```

### Legal Mesh Bridge

```bash
# Bridge evidence to legal spines
python3 -m job_app_helix.agent_cli capability evidence.bridge bridge_from_ledger --inputs '{
  "target_spine": "case_1FDV",
  "monolith_legal_path": "/data/monolith/catalog/legal_spines"
}'
```

---

## Scheduling

### Cron Jobs

```bash
# Monolith incremental sync (every 4 hours)
0 */4 * * * cd /opt/job-app-helix && PYTHONPATH=src python3 -m job_app_helix.agent_cli workflow monolith-catalog-sync --inputs '{"mode": "incremental"}' >> /var/log/job-app-helix/sync.log 2>&1

# Full portfolio cycle (daily 2AM)
0 2 * * * cd /opt/job-app-helix && PYTHONPATH=src python3 -m job_app_helix.agent_cli workflow full-portfolio-cycle --inputs '{}' >> /var/log/job-app-helix/full_cycle.log 2>&1

# Evidence ledger (every 6 hours)
0 */6 * * * cd /opt/job-app-helix && PYTHONPATH=src python3 -m job_app_helix.agent_cli workflow portfolio-evidence-ledger --inputs '{}' >> /var/log/job-app-helix/ledger.log 2>&1
```

### Systemd Timers (Alternative)

```bash
# /etc/systemd/system/job-app-helix-sync.timer
[Unit]
Description=Job-App Helix Monolith Sync Timer
Requires=job-app-helix-sync.service

[Timer]
OnCalendar=*:0/4
Persistent=true

[Install]
WantedBy=timers.target
```

---

## Monitoring & Observability

### Health Checks

```bash
# All validators
python3 scripts/validate_application_registry.py && python3 scripts/validate_portfolio_root_truth.py && python3 scripts/validate_live_repository_links.py

# Agent health
python3 -m job_app_helix.agent_cli config --mode standard

# Receipt chain
python3 -m job_app_helix.agent_cli receipt <latest_receipt_id>
```

### Log Aggregation

```bash
# Structured logs (JSON)
tail -f /var/log/job-app-helix/*.log | jq '. | select(.level == "ERROR")'

# Key metrics to alert on
# - validator_failures_total > 0
# - receipt_verification_failures > 0
# - workflow_duration_seconds > threshold
# - monolith_sync_catalogs_updated == 0
```

### Key Metrics

| Metric | Source | Alert Threshold |
|--------|--------|-----------------|
| `validator.status` | All validators | != PASS |
| `receipt.verification.failures` | Capability execution | > 0 |
| `workflow.duration_seconds` | Agent workflows | > 300s |
| `monolith.catalogs_updated` | Monolith sync | == 0 |
| `tower.resolution.placement` | Tower resolution | Missing |
| `projection.freshness` | Portfolio root | STALE |

---

## Rollback Procedures

### Capability Rollback

```bash
# 1. Identify failed receipt
python3 -m job_app_helix.agent_cli receipt <failed_receipt_id>

# 2. Revert to prior sync receipt
cp sync_receipt.json.prior sync_receipt.json

# 3. Re-run full sync
python3 -m job_app_helix.agent_cli workflow monolith-catalog-sync --inputs '{"mode": "full"}'

# 4. Verify all 4 catalogs
python3 -c "
import json
for cat in ['capabilities_3layer.json', 'runtime_power_spine.json', 'library.json', 'repo_excellence_state_machine.json']:
    data = json.load(open(f'/data/monolith/catalog/{cat}'))
    print(f'{cat}: {len(json.dumps(data))} bytes')
"
```

### Agent Framework Rollback

```bash
# 1. Stop service
systemctl stop job-app-helix-agent

# 2. Revert config
cp /etc/job-app-helix/agent-config.yaml.prior /etc/job-app-helix/agent-config.yaml

# 3. Revert code
cd /opt/job-app-helix && git checkout <prior_commit>

# 4. Restart
systemctl start job-app-helix-agent

# 5. Verify
python3 -m job_app_helix.agent_cli workflow full-portfolio-cycle --inputs '{}'
```

### Database/State Rollback

```bash
# Pointer index
cp /tmp/aspen_grove_pointer_index.json.prior /tmp/aspen_grove_pointer_index.json

# Receipt chain
cp .agents/receipts/chain.json.prior .agents/receipts/chain.json

# Verify chain integrity
python3 -c "
import json
with open('.agents/receipts/chain.json') as f: chain = json.load(f)
print(f'Chain length: {len(chain)}')
# Verify each receipt exists
for rid in chain:
    assert (Path('.agents/receipts') / f'{rid}.json').exists()
print('Chain integrity: OK')
"
```

---

## Security Hardening

### Network

- [ ] Restrict GitHub API to required repos only
- [ ] Monolith/Tower on private network
- [ ] Legal spines on isolated segment
- [ ] mTLS for all inter-service communication

### Secrets

```bash
# Use secret manager (not env vars in production)
# AWS Secrets Manager / HashiCorp Vault / GCP Secret Manager

# Example: Vault
export GITHUB_TOKEN=$(vault kv get -field=token secret/job-app-helix/github)
export MONOLITH_DB_PASSWORD=$(vault kv get -field=password secret/job-app-helix/monolith)
```

### Audit Logging

```bash
# Enable audit logging
export JOB_APP_HELIX_AUDIT_LOG=/var/log/job-app-helix/audit.log

# Log format: JSON with receipt_id, operation, user, timestamp, result
```

---

## Disaster Recovery

### RTO/RPO Targets

| Component | RTO | RPO |
|-----------|-----|-----|
| Monolith catalog | 1 hour | 4 hours |
| Agent framework | 30 min | 0 (code in git) |
| Receipt chain | 15 min | 0 (append-only) |
| Pointer index | 1 hour | 1 hour |

### Recovery Steps

1. **Infrastructure:** Provision from IaC (Terraform/Ansible)
2. **Code:** `git clone` from GitHub
3. **State:** Restore from backup (pointer index, receipt chain, sync receipt)
4. **Verify:** Run all validators
5. **Resume:** Re-enable cron timers

---

## Checklist Summary

### Pre-Deployment
- [ ] All validators PASS
- [ ] Core tests PASS (44 tests)
- [ ] Agent CLI functional
- [ ] Forward-deployed modules tested
- [ ] Config files validated
- [ ] Secrets configured
- [ ] Network policies applied

### Post-Deployment
- [ ] Monolith sync verified (4 catalogs)
- [ ] Tower resolution tested
- [ ] Evidence bridge tested
- [ ] Agent workflows execute
- [ ] Health checks green
- [ ] Monitoring alerts configured
- [ ] Rollback tested

### Ongoing
- [ ] Daily full portfolio cycle
- [ ] 4-hour incremental monolith sync
- [ ] Weekly validator audit
- [ ] Monthly receipt chain audit
- [ ] Quarterly disaster recovery drill

---

*Deployment Guide v2.0 — All deployments produce hash-bound receipts*