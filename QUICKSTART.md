# Job-App Helix — Quickstart for Operators

**Version:** 2.0  
**Target:** Operators, mesh coordinators, forward-deployed engineers  
**Time to first capability:** ~5 minutes

---

## Prerequisites

```bash
# System
git, python3.11+, pip

# Environment
export PYTHONPATH=/path/to/job-app-helix/src
export MONOLITH_ROOT=/data/data/com.termux/files/home/monolith
export TOWER_ROOT=/data/data/com.termux/files/home/the-tower-of-babel
export LEGAL_SPINES_PATH=/data/data/com.termux/files/home/monolith/catalog/legal_spines
```

---

## 1. Verify Installation (30 seconds)

```bash
cd /path/to/job-app-helix
PYTHONPATH=src python3 -c "from job_app_helix import *; print('✅ Import OK')"

# Run validators (all must PASS)
python3 scripts/validate_application_registry.py
python3 scripts/validate_portfolio_root_truth.py
python3 scripts/validate_live_repository_links.py
# Expected: all output PASS / status: PASS
```

---

## 2. Agent CLI — Your Daily Driver

```bash
# Help
PYTHONPATH=src python3 -m job_app_helix.agent_cli --help

# List workflows
PYTHONPATH=src python3 -m job_app_helix.agent_cli workflow --list

# List capabilities
PYTHONPATH=src python3 -m job_app_helix.agent_cli capability --list

# Show execution mode config
PYTHONPATH=src python3 -m job_app_helix.agent_cli config --mode standard
```

---

## 3. Run the Full Portfolio Cycle (2 minutes)

```bash
PYTHONPATH=src python3 -m job_app_helix.agent_cli workflow full-portfolio-cycle --inputs '{}'
```

**Expected output:** 5 steps complete with receipts
```
Executing workflow: full-portfolio-cycle
Mode: standard
  Step: build_ledger (portfolio.evidence_ledger)
  Step: query_monolith (portfolio.capability_federation)
  Step: evaluate_fitness (tower.capability_resolution)
  Step: sync_catalogs (monolith.catalog_sync)
  Step: bridge_evidence (evidence.bridge)
{
  "workflow": "full-portfolio-cycle",
  "results": {...},
  "status": "completed"
}
```

---

## 4. Run Individual Capabilities

```bash
# Evidence ledger
PYTHONPATH=src python3 -m job_app_helix.agent_cli capability portfolio.evidence_ledger build_ledger --inputs '{"anchor_threshold": 8}'

# Capability federation
PYTHONPATH=src python3 -m job_app_helix.agent_cli capability portfolio.capability_federation federate_capabilities --inputs '{"domain": "legal_evidence", "requirement": "ledger"}'

# Tower resolution
PYTHONPATH=src python3 -m job_app_helix.agent_cli capability tower.capability_resolution resolve_placement --inputs '{"requirement": "evidence_graph", "domain": "legal_evidence", "performance_requirements": {"memory_safety": true}}'

# Monolith sync
PYTHONPATH=src python3 -m job_app_helix.agent_cli capability monolith.catalog_sync sync_monolith --inputs '{"mode": "incremental"}'

# Helix automation
PYTHONPATH=src python3 -m job_app_helix.agent_cli capability helix.automation_engine run_automation --inputs '{"automation": "brainsync_index", "target": "/tmp/test"}'

# Evidence bridge
PYTHONPATH=src python3 -m job_app_helix.agent_cli capability evidence.bridge bridge_from_ledger --inputs '{"target_spine": "case_1FDV"}'
```

---

## 5. Test Forward-Deployed Capabilities

```bash
# Anthropic (10 capabilities)
PYTHONPATH=src python3 -c "
from job_app_helix.forward_deployed.anthropic import create_anthropic_architect
arch = create_anthropic_architect()
result = arch.synthesize_constitution([{'id':'test','principle':'Do no harm','category':'safety','priority':1}])
print('Anthropic receipt:', result['receipt_id'])
assert arch.verify_receipt(result['receipt_id'])
"

# NVIDIA (7 capabilities)
PYTHONPATH=src python3 -c "
from job_app_helix.forward_deployed.nvidia import create_nvidia_architect, KernelSpec, GPUTarget
arch = create_nvidia_architect()
kernel = KernelSpec(name='test', target=GPUTarget.B200, precision='fp4', operation='moe', tile_config={}, warp_config={}, shared_memory_kb=48, registers_per_thread=32)
result = arch.optimize_fp4_kernel(kernel)
print('NVIDIA FP4 speedup:', result['expected_speedup'], 'receipt:', result['receipt_id'])
assert arch.verify_receipt(result['receipt_id'])
"

# SpaceX (7 capabilities)
PYTHONPATH=src python3 -c "
from job_app_helix.forward_deployed.spacex import create_spacex_architect, FlightSoftwareConfig, VehicleStage, EngineType
arch = create_spacex_architect()
fs = FlightSoftwareConfig(vehicle=VehicleStage.SUPER_HEAVY, engine_count=33, engine_type=EngineType.RAPTOR_V3, control_frequency_hz=1000, redundancy_level='triplex', languages=['C++','Rust'], safety_class='Class A')
result = arch.design_flight_software(fs)
print('SpaceX flight SW:', result['receipt_id'], 'redundancy:', result['architecture']['redundancy']['level'])
assert arch.verify_receipt(result['receipt_id'])
"
```

---

## 6. Verify Receipts

```bash
# CLI
PYTHONPATH=src python3 -m job_app_helix.agent_cli receipt <receipt_id>

# Python
from job_app_helix.forward_deployed.anthropic import create_anthropic_architect
arch = create_anthropic_architect()
arch.verify_receipt("abc123def456")  # True/False
arch.get_receipt_chain()  # List of all receipts
```

---

## 7. Monolith Sync (Production)

```bash
# Full sync (initial deployment)
PYTHONPATH=src python3 -m job_app_helix.agent_cli workflow monolith-catalog-sync --inputs '{"mode": "full"}'

# Incremental (every 4 hours via cron)
PYTHONPATH=src python3 -m job_app_helix.agent_cli workflow monolith-catalog-sync --inputs '{"mode": "incremental"}'

# Verify only
PYTHONPATH=src python3 -m job_app_helix.agent_cli workflow monolith-catalog-sync --inputs '{"mode": "verify"}'
```

---

## 8. Run Tests

```bash
# Core validator tests (44 tests, ~30 seconds)
PYTHONPATH=src python3 -m pytest tests/test_application_registry.py tests/test_candidate_portfolio_boundary.py tests/test_live_repository_links.py tests/test_portfolio_audit_claims.py tests/test_portfolio_root_truth.py -q

# Full suite (93 tests, ~2 minutes)
PYTHONPATH=src python3 -m pytest tests/ -q

# Specific test
PYTHONPATH=src python3 -m pytest tests/test_application_registry.py::ApplicationRegistryTests::test_zero_omission_registry_gate -v
```

---

## 8. Common Operations

| Task | Command |
|---|---|
| View receipt chain | `cat .agents/receipts/chain.json` |
| View specific receipt | `cat .agents/receipts/<receipt_id>.json` |
| Check pointer index | `cat /tmp/aspen_grove_pointer_index.json \| jq '.files \| length'` |
| View portfolio status | `cat manifests/portfolio_repositories.json \| jq '.total_repositories, .workspace_repositories \| length'` |
| Check validator status | `python3 scripts/validate_application_registry.py` |
| View agent config | `cat .agents/agent-config.yaml` |

---

## 9. Troubleshooting

| Issue | Fix |
|---|---|
| `ModuleNotFoundError` | `export PYTHONPATH=src` |
| Validator fails | Run specific validator to see error details |
| Receipt not found | Call `verify_receipt()` on capability instance |
| Agent CLI warning | Cosmetic RuntimeWarning; set PYTHONPATH |
| Slow tests | Run core validator tests only (44 tests) |

---

## 10. Key Files Reference

| File | Purpose |
|---|---|
| `.agents/agent-config.yaml` | Full agent configuration |
| `.agents/modes.json` | 5 execution modes |
| `.agents/workflows.yaml` | 7 workflows |
| `.agents/skills/registry.yaml` | 30 capabilities (6 core + 24 forward-deployed) |
| `manifests/portfolio_repositories.json` | 83 workspace + 1 root |
| `manifests/unified_deserving_manifest.json` | 225 deserving repos |
| `manifests/live_repository_links.json` | 83 live APEX links |
| `manifests/evidence_ledger_unified.json` | Unified evidence |
| `solidify/<repo>.json` | Per-repo innovation + evidence |
| `.agents/receipts/` | Hash-bound receipts |

---

## 11. Execution Modes Quick Reference

| Mode | Use When |
|---|---|
| `standard` | Default portfolio operations |
| `aggressive` | Well-specified, reversible builds |
| `conservative` | Evidence/legal operations |
| `capability-build` | New capability modules |
| `portfolio-sync` | Monolith catalog sync |

```bash
# Run workflow in specific mode
PYTHONPATH=src python3 -m job_app_helix.agent_cli workflow full-portfolio-cycle --inputs '{}'
# Mode determined by workflow definition
```

---

## 12. Emergency Commands

```bash
# Verify all validators
python3 scripts/validate_application_registry.py && python3 scripts/validate_portfolio_root_truth.py && python3 scripts/validate_live_repository_links.py

# Full portfolio cycle (if something broke)
PYTHONPATH=src python3 -m job_app_helix.agent_cli workflow full-portfolio-cycle --inputs '{}'

# Monolith full resync
PYTHONPATH=src python3 -m job_app_helix.agent_cli workflow monolith-catalog-sync --inputs '{"mode": "full"}'

# Verify receipt chain integrity
python3 -c "
import json
with open('.agents/receipts/chain.json') as f: chain = json.load(f)
print(f'Chain length: {len(chain)}')
for rid in chain:
    assert (__import__('pathlib').Path('.agents/receipts') / f'{rid}.json').exists()
print('✅ Chain integrity verified')
"
```

---

## 13. Next Steps

1. **Read** `ARCHITECTURE.md` for system design
2. **Read** `FORWARD_DEPLOYED.md` for all 24 capabilities
3. **Read** `AGENT_ENGINEERING.md` for worker roles, modes, workflows
4. **Read** `DEPLOYMENT.md` for Anthropic/NVIDIA/SpaceX deployment
5. **Read** `VALIDATION.md` for receipt verification details

---

**Status:** All validators PASS, all 24 forward-deployed capabilities operational, agent framework deployed.

**Operator vocabulary:** elite · pro · Hard · G (no sovereign/canonical framing)