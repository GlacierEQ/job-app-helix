# Job-App Helix — Agent Engineering Framework

**Version:** 2.0  
**Status:** PRODUCTION  
**Framework:** Holographic Mesh / Diamond Grid Topology  
**Epistemic Standard:** L0–L5 (Zero Fake Execution)

---

## Overview

The Agent Engineering Framework transforms Job-App Helix from a governance-heavy repository into a **capability-executing control plane**. It provides:

- **10 specialized worker roles** for parallel execution
- **5 execution modes** for different operational postures
- **7 workflows** for complex multi-step operations
- **6 capabilities** + **24 forward-deployed modules** as callable functions
- **Hash-bound receipts** on every operation (L0-L5 compliant)

---

## Worker Roles (10)

### Role Registry

| Role ID | Skill Composition | Persona | Trigger | Output Artifact |
|---------|-------------------|---------|---------|-----------------|
| `repo-cartographer` | `apex-specialist-registry` | Mapper | Portfolio discovery, estate mapping | `capability_manifest.yaml` |
| `capability-miner` | `apex-mega-skills` | Archaeologist | New capability requirement | `capability_assessment.json` |
| `connector-broker` | `apex-connector-mesh` | Diplomat | External capability needed | `connector_result.json` |
| `systems-architect` | `apex-orchestration` | Architect | Cross-repo integration | `integration_design.yaml` |
| `implementation-engineer` | `apex-engineering-excellence` | Builder | Capability build | `implementation + tests + receipt` |
| `reliability-engineer` | `verification` | Guardian | Pre-deployment | `reliability_report.json` |
| `performance-engineer` | `benchmark-suite` | Optimizer | Performance requirement | `benchmark_results.json` |
| `evidence-authenticator` | `apex-legal-intelligence` | Forensicist | Evidence integration | `evidence_authenticity.json` |
| `contradiction-hunter` | `apex-legal-intelligence` | Adversary | Pre-legal filing | `contradiction_matrix.json` |
| `verification-agent` | `verification` | Auditor | Post-execution | `verification_receipt.json` |

### Role Invocation

Each role receives a **focused packet**:
```yaml
objective: "Specific task description"
scope: "Bounded context"
available_sources: ["file paths", "connectors", "memory layers"]
expected_output_schema: "JSON schema"
dependencies: ["other role outputs"]
stop_condition: "Clear completion criteria"
verification_requirement: "Receipt + test"
```

---

## Execution Modes (5)

### Mode Comparison

| Mode | Parallelism | Verification | Blast Radius | Fail-Safe | Use Case |
|------|-------------|--------------|--------------|-----------|----------|
| **standard** | Bounded (4) | Per-phase | Scoped | `apex-fail-safe-governor` | Default portfolio operations |
| **aggressive** | Max | Terminal-only | Scoped | `apex-fail-safe-governor` | Well-specified reversible builds |
| **conservative** | Serial | Per-step | Minimal | Governor + explicit confirm | Evidence/legal operations |
| **capability-build** | Serial | Full ladder (syntax→unit→int→e2e→receipt) | Scoped | Governor | New capability modules |
| **portfolio-sync** | Bounded | Per-phase | Scoped | Governor | Monolith catalog sync |

### Mode Selection Logic

```python
def select_mode(task: Task) -> ExecutionMode:
    if task.irreversible or task.legal:
        return ExecutionMode.CONSERVATIVE
    elif task.new_capability:
        return ExecutionMode.CAPABILITY_BUILD
    elif task.monolith_sync:
        return ExecutionMode.PORTFOLIO_SYNC
    elif task.well_specified and task.reversible:
        return ExecutionMode.AGGRESSIVE
    return ExecutionMode.STANDARD
```

---

## Composite Modes (4)

### Pre-Configured Role + Mode Compositions

| Composite | Mode | Workers | Trigger |
|-----------|------|---------|---------|
| **portfolio-sync** | standard | cartographer, miner, engineer, verifier | Monolith catalog sync |
| **capability-federation** | aggressive | broker, architect, miner, verifier | Monolith + Tower federation |
| **evidence-integration** | conservative | authenticator, hunter, verifier | Legal spine operations |
| **helix-automation** | capability-build | engineer, reliability, verifier | Brainsync, crystallization |

---

## Workflows (7)

### Workflow Definitions

| Workflow ID | Name | Mode | Steps | Receipt |
|-------------|------|------|-------|---------|
| `portfolio-evidence-ledger` | Build Portfolio Evidence Ledger | capability-build | 1. load_manifest → 2. verify_ledger | Required |
| `capability-federation-query` | Federate Monolith + Tower | capability-federation | 1. query_monolith → 2. verify_federation | Required |
| `tower-capability-resolution` | Resolve Tech Placement | capability-build | 1. evaluate_fitness → 2. verify_resolution | Required |
| `monolith-catalog-sync` | Sync to Monolith | portfolio-sync | 1. sync_catalogs → 2. verify_sync | Required |
| `helix-automation-execution` | Run Helix Automations | helix-automation | 1. run_automation → 2. verify_automation | Required |
| `evidence-legal-bridge` | Bridge to Legal Spines | evidence-integration | 1. bridge_evidence → 2. verify_bridge | Required |
| `full-portfolio-cycle` | Complete Pipeline | standard | ledger → federation → resolution → sync → bridge | Required |

### DAG Dependencies

```
portfolio-evidence-ledger (no deps)
    │
    ├───▶ capability-federation-query (no deps)
    │
    ├───▶ tower-capability-resolution (no deps)
    │
    ├───▶ monolith-catalog-sync (depends: ledger)
    │
    └───▶ evidence-legal-bridge (depends: ledger)

full-portfolio-cycle: [ledger, federation, resolution, sync, bridge] (parallel where possible)
```

### Workflow Execution

```bash
# CLI
python3 -m job_app_helix.agent_cli workflow full-portfolio-cycle --inputs '{}'

# Or via Python
from job_app_helix.agent_cli import run_workflow
result = run_workflow("full-portfolio-cycle", {})
```

---

## Capability Registry (6 Core + 24 Forward-Deployed)

### Core Capabilities (6)

| Capability ID | Module | Interface | Verification Gates |
|---------------|--------|-----------|-------------------|
| `portfolio.evidence_ledger` | `evidence_ledger.py` | CLI, Library | Syntax, Unit, Integration, Receipt |
| `portfolio.capability_federation` | `capability_federation.py` | CLI, Library, MCP | Syntax, Unit, Integration, Receipt |
| `monolith.catalog_sync` | `monolith_sync.py` | CLI, Library, Scheduled | Syntax, Unit, Integration, E2E, Receipt |
| `tower.capability_resolution` | `tower_resolution.py` | CLI, Library | Syntax, Unit, Integration, Receipt |
| `helix.automation_engine` | `automation_engine.py` | CLI, Library, MCP | Syntax, Unit, Receipt |
| `evidence.bridge` | `evidence_bridge.py` | CLI, Library | Syntax, Unit, Integration, Receipt |

### Forward-Deployed Capabilities (24)

| Company | Capabilities | Module |
|---------|--------------|--------|
| Anthropic | 10 | `forward_deployed.anthropic` |
| NVIDIA | 7 | `forward_deployed.nvidia` |
| SpaceX | 7 | `forward_deployed.spacex` |

### Capability Invocation

```python
# Direct Python
from job_app_helix import federate_capabilities, CapabilityQuery
result = federate_capabilities(query, monolith_path, tower_path)

# Agent CLI
python3 -m job_app_helix.agent_cli capability portfolio.capability_federation federate_capabilities --inputs '{"domain": "legal_evidence", "requirement": "ledger"}'
```

---

## Skill Registry

### Registry Location

```
.agents/skills/registry.yaml
```

### Skill Definition Schema

```yaml
skills:
  - name: portfolio-evidence-ledger
    version: 1.0.0
    description: Hash-bound evidence ledger
    capability_id: portfolio.evidence_ledger
    entrypoint: src/job_app_helix/evidence_ledger.py
    interface: cli|library
    category: portfolio
    dependencies:
      - aspen_grove_pointer_index
    verification_gates:
      - syntax
      - unit
      - integration
      - receipt
```

### Skill Compositions

```yaml
compositions:
  - name: portfolio-capability-cycle
    description: Complete pipeline
    skills:
      - portfolio-evidence-ledger
      - capability-federation
      - tower-capability-resolution
      - monolith-catalog-sync
      - evidence-bridge
    orchestration: sequential
    verification: all_gates

  - name: automation-suite
    description: Parallel automations
    skills:
      - helix-automation-engine
    orchestration: parallel
    verification: receipt
```

### Discovery

```yaml
discovery:
  local_path: .agents/skills/
  remote_sources:
    - monolith: /data/data/com.termux/files/home/monolith/catalog
    - tower: /data/data/com.termux/files/home/the-tower-of-babel
  auto_refresh: true
  refresh_interval_hours: 6
```

---

## Agent CLI Reference

### Installation

```bash
cd /data/data/com.termux/files/home/job-app-helix
PYTHONPATH=src python3 -m job_app_helix.agent_cli --help
```

### Commands

| Command | Description | Example |
|---------|-------------|---------|
| `workflow --list` | List all workflows | `agent_cli workflow --list` |
| `workflow <id> --inputs '{}'` | Execute workflow | `agent_cli workflow full-portfolio-cycle --inputs '{}'` |
| `capability --list` | List capabilities | `agent_cli capability --list` |
| `capability <id> <action> --inputs '{}'` | Run capability | `agent_cli capability portfolio.evidence_ledger build_ledger --inputs '{"anchor_threshold": 8}'` |
| `receipt <hash>` | Verify receipt | `agent_cli receipt abc123def456` |
| `config --mode <mode>` | Show mode config | `agent_cli config --mode capability-build` |

### Example Session

```bash
# Full portfolio cycle
$ python3 -m job_app_helix.agent_cli workflow full-portfolio-cycle --inputs '{}'
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

# Single capability
$ python3 -m job_app_helix.agent_cli capability portfolio.evidence_ledger build_ledger --inputs '{"anchor_threshold": 8}'
{
  "ledger": {"total_repos": 225, "verified_anchors": 8, "merkle_root": "abc123..."}
}
```

---

## Memory Integration

### Pointer Index

- **Path:** `/tmp/aspen_grove_pointer_index.json`
- **Files:** 1,926 indexed
- **Lookup:** O(1) via SHA-256/Blake2b → `ptr_<hash>`

### Memory Layers

| Layer | Purpose | Access |
|-------|---------|--------|
| Mem0 | Episodic memory | `unified-memory_search_mem0_facts` |
| Supermemory | Knowledge layer | `unified-memory_search_supermemory_facts` |
| Pinecone | Legal/evidence vectors | `unified-memory_query_pinecone_vector` |
| Qdrant | Local vectors | `unified-memory_query_qdrant_vector` |
| Context7 | Documentation | `unified-memory_search_context7` |
| Memory Plugin | Cross-session | `unified-memory_search_memory_plugin` |

### Router

```python
from unified-memory import semantic_memory_router
result = semantic_memory_router("legal evidence anchoring")
# Routes to: Pinecone (legal), Context7 (docs), Mem0+SM (default)
```

---

## Token Optimization

### Tier Routing

| Tier | Name | Model | Savings | Trigger |
|------|------|-------|---------|---------|
| 0 | Local Fast | Python Script | 95% | Lookups, regex, pointer checks |
| 1 | Free Mesh | Fast Coder | 80% | Doc parsing, schema checks |
| 2 | Specialist Swarm | Flash Subagent | 65% | Multi-file edits, repo scouting |
| 3 | Heavy Reasoning | Pro | 0% | Architecture, legal forensics |

### Compression Rules

- Targeted range reads (< 250 lines)
- Surgical mutations over full overwrites
- Pointer index lookups over directory scans
- Subagent delegation for broad searches
- Disk offloading for heavy outputs

---

## Verification Ladder

Every capability must pass:

```bash
# G1: Syntax
python3 -m py_compile src/job_app_helix/*.py

# G2: Unit
PYTHONPATH=src python3 -m pytest tests/ -k "not integration" -q

# G3: Integration
PYTHONPATH=src python3 -m pytest tests/ -k "integration" -q

# G4: E2E
PYTHONPATH=src python3 -m job_app_helix.agent_cli workflow full-portfolio-cycle --inputs '{}'

# G5: Receipt
verify_receipt(<receipt_id>)  # Must return True
```

---

## Configuration Files

### Core Config

| File | Purpose |
|------|---------|
| `.agents/agent-config.yaml` | Full agent configuration |
| `.agents/modes.json` | Execution modes |
| `.agents/workflows.yaml` | Workflow definitions |
| `.agents/skills/registry.yaml` | Capability registry |

### Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `MONOLITH_ROOT` | `/data/data/com.termux/files/home/monolith` | Monolith catalog root |
| `TOWER_ROOT` | `/data/data/com.termux/files/home/the-tower-of-babel` | Tower of Babel root |
| `LEGAL_SPINES_PATH` | `/data/data/com.termux/files/home/monolith/catalog/legal_spines` | Legal spines |
| `ASPEN_GROVE_INDEX` | `/tmp/aspen_grove_pointer_index.json` | Pointer index |

---

## Troubleshooting

### Common Issues

| Issue | Diagnosis | Fix |
|-------|-----------|-----|
| `ModuleNotFoundError` | PYTHONPATH not set | `export PYTHONPATH=src` |
| `verify_receipt` returns False | Receipt not in chain | Check `.agents/receipts/` |
| Workflow step fails | Check step receipt | `agent_cli receipt <hash>` |
| Validator fails | Run specific validator | `python3 scripts/validate_*.py` |
| Agent CLI warnings | RuntimeWarning | Cosmetic, ignore or set PYTHONPATH |

### Debug Commands

```bash
# Check receipt chain
python3 -c "from job_app_helix import *; print(a.get_receipt_chain())"

# Validate specific capability
python3 -m job_app_helix.agent_cli capability portfolio.evidence_ledger build_ledger --inputs '{"anchor_threshold": 8}'

# Run single test
PYTHONPATH=src python3 -m pytest tests/test_application_registry.py -v

# Check pointer index
cat /tmp/aspen_grove_pointer_index.json | jq '.files | length'
```

---

## Best Practices

1. **Always use receipts** — Never claim execution without `verify_receipt()`
2. **Prefer surgical mutations** — Targeted range reads/writes over full files
3. **Delegate broad searches** — Use subagents for repo scans, web crawling
4. **Offload to disk** — Heavy outputs to files, summaries in chat
5. **Use pointer index** — O(1) lookup via `ptr_<hash>` instead of directory scans
6. **Select appropriate mode** — Conservative for legal, aggressive for well-specified builds
7. **Verify before claim** — `verify_receipt()` before reporting success

---

*Agent Engineering Framework v2.0 — All operations produce hash-bound receipts*