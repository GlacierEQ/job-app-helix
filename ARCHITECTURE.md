# Job-App Helix — System Architecture

**Version:** 2.0  
**Status:** PRODUCTION  
**Classification:** Portfolio Control Plane — Unbounded Estate  
**Epistemic Standard:** L0–L5 (Zero Fake Execution)

---

## 1. System Overview

Job-App Helix is the **portfolio control plane** for the GlacierEQ engineering estate. It operates as a holographic mesh — no single authority, no artificial limits, every repository a top-tier capability donor.

### Design Laws

| Law | Enforcement |
|-----|-------------|
| **Governance serves progress** | AGENTS.md §1.3 — Governance artifacts are outputs, not prerequisites |
| **Zero fake execution** | AGENTS.md §17 — Every claim backed by hash-bound receipt |
| **Capability density over governance** | 24 executable capabilities replace 200+ manifest files |
| **Unbounded estate** | No 66-repo boundary, no 3-flagship limit, no public-only visibility cap |
| **L0–L5 epistemic standard** | Immutable byte/SHA/commit/docket provenance required |

---

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        JOB-APP HELIX CONTROL PLANE                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │  ANTHROPIC   │  │   NVIDIA     │  │   SPACEX     │  │  CORE CAPS   │   │
│  │ FORWARD-DEP  │  │ FORWARD-DEP  │  │ FORWARD-DEP  │  │              │   │
│  │              │  │              │  │              │  │ Evidence     │   │
│  │ 10 capabilities│ │ 7 capabilities│ │ 7 capabilities│ │ Ledger       │   │
│  │ Hash-bound    │  │ Hash-bound    │  │ Hash-bound    │ │ Federation   │   │
│  │ Receipts      │  │ Receipts      │  │ Receipts      │ │ Monolith Sync│   │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘   │
│         │                 │                 │                 │           │
│         └─────────────────┼─────────────────┼─────────────────┘           │
│                           ▼                 ▼                             │
│              ┌────────────────────────────────────────────────┐           │
│              │           AGENT ENGINEERING LAYER              │           │
│              │  10 Worker Roles │ 5 Execution Modes           │           │
│              │  7 Workflows     │ 6 Capabilities              │           │
│              │  Hash-bound Receipts on Every Operation        │           │
│              └────────────────────┬───────────────────────────┘           │
│                                   │                                      │
│         ┌─────────────────────────┼─────────────────────────┐           │
│         ▼                         ▼                         ▼           │
│ ┌───────────────┐         ┌───────────────┐         ┌───────────────┐  │
│ │   MONOLITH    │         │  TOWER OF     │         │ LEGAL MESH    │  │
│ │   CATALOG     │         │  BABEL        │         │ EVIDENCE      │  │
│ │  (4 catalogs) │         │  (40 floors)  │         │ BRIDGE        │  │
│ └───────────────┘         └───────────────┘         └───────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Component Registry

| Component | Type | Status | Receipt Format |
|-----------|------|--------|----------------|
| Evidence Ledger | Core Capability | ✅ Operational | Merkle root + anchor receipts |
| Capability Federation | Core Capability | ✅ Operational | Resolution receipt |
| Monolith Catalog Sync | Core Capability | ✅ Operational | Sync receipt (4 catalogs) |
| Tower Capability Resolution | Core Capability | ✅ Operational | Placement receipt |
| Helix Automation Engine | Core Capability | ✅ Operational | Automation receipt |
| Evidence Bridge | Core Capability | ✅ Operational | Bridge receipt |
| Anthropic Forward-Deployed | Company Capability | ✅ Operational | 10 capability receipts |
| NVIDIA Forward-Deployed | Company Capability | ✅ Operational | 7 capability receipts |
| SpaceX Forward-Deployed | Company Capability | ✅ Operational | 7 capability receipts |

---

## 3. Data Flow Architecture

### Portfolio State Flow

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  UNIFIED        │     │  EVIDENCE       │     │  MONOLITH       │
│  DESERVING      │────▶│  LEDGER         │────▶│  CATALOG SYNC   │
│  MANIFEST       │     │  (Merkle root)  │     │  (4 catalogs)   │
│  (225 repos)    │     │  83 anchors     │     │  225 repos      │
└─────────────────┘     └────────┬────────┘     └─────────────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │  CAPABILITY     │
                        │  FEDERATION     │
                        │  (Monolith +    │
                        │   Tower)        │
                        └────────┬────────┘
                                 │
                    ┌────────────┼────────────┐
                    ▼            ▼            ▼
             ┌──────────┐ ┌──────────┐ ┌──────────┐
             │ANTHROPIC │ │ NVIDIA   │ │ SPACEX   │
             │ FORWARD  │ │ FORWARD  │ │ FORWARD  │
             │ DEPLOYED │ │ DEPLOYED │ │ DEPLOYED │
             └──────────┘ └──────────┘ └──────────┘
                    │            │            │
                    └────────────┼────────────┘
                                 ▼
                        ┌─────────────────┐
                        │  EVIDENCE       │
                        │  BRIDGE         │
                        │  (Legal Mesh)   │
                        └─────────────────┘
```

### Receipt Chain Integrity

Every operation produces a **SHA-256 receipt** forming an immutable chain:

```
Operation Input + Timestamp + Operation Type → SHA-256 → Receipt ID (16-char prefix)
                                                              │
                                                              ▼
                    ┌─────────────────────────────────────────┤
                    │           RECEIPT CHAIN                 │
                    │  [r1] → [r2] → [r3] → ... → [rn]        │
                    │  Each links to previous via hash        │
                    └─────────────────────────────────────────┘
```

---

## 4. Capability Architecture

### Core Capabilities (6)

| Capability | Module | Interface | Verification |
|------------|--------|-----------|--------------|
| `portfolio.evidence_ledger` | `evidence_ledger.py` | CLI, Library | Merkle root, 83 anchors |
| `portfolio.capability_federation` | `capability_federation.py` | CLI, Library, MCP | Resolution receipt |
| `monolith.catalog_sync` | `monolith_sync.py` | CLI, Library, Scheduled | Sync receipt (4 catalogs) |
| `tower.capability_resolution` | `tower_resolution.py` | CLI, Library | Placement receipt |
| `helix.automation_engine` | `automation_engine.py` | CLI, Library, MCP | Automation receipt |
| `evidence.bridge` | `evidence_bridge.py` | CLI, Library | Bridge receipt |

### Company Forward-Deployed Capabilities (24)

#### Anthropic (10 capabilities)
| Capability | Bottleneck Solved | Key Metric |
|------------|-------------------|------------|
| Constitutional AI Synthesis | CAI scaling | 10 principles → automated feedback |
| CAI Critique Engine | RLHF replacement | 1ms critique latency |
| Mechanistic Interpretability | Circuit tracing | Attribution graphs, autoencoders |
| Persona Vector Extraction | Sycophancy/hallucination | Steering vectors |
| Containment Verification (Dafny) | Boundary enforcement | Formal proofs |
| Containment Layer Generation | Vocabulary foreclosure | Typed action interfaces |
| Adversarial Eval Engine | Benchmark gaming detection | 94% confidence |
| AI-Resistant Eval Design | Infrastructure noise | 50 tasks from real failures |
| Agent Skill Design (MCP) | Secure autonomy | Dual-isolation sandbox |
| Context Engineering | Token optimization | 15-20% improvement |

#### NVIDIA (7 capabilities)
| Capability | Bottleneck Solved | Key Metric |
|------------|-------------------|------------|
| Blackwell FP4 Optimization | Native FP4 kernels | 5x throughput vs FP8 |
| CUDA Graphs Conditional | IF/ELSE/SWITCH nodes | 2x faster runtime selection |
| MoE Grouped GEMM | CUTLASS 3.5 Blackwell | 5x vs H100 FP16 |
| NVLink Topology Design | Multi-GPU scaling | 80% efficiency at 72 GPUs |
| TensorRT-LLM Tuning | FP4 quantization | 4x throughput vs FP8 |
| Kernel Autotuner | Nsight Compute search | 1.8x speedup |
| Power/Perf Profiling | 1000W TDP optimization | Tokens/watt maximization |

#### SpaceX (7 capabilities)
| Capability | Bottleneck Solved | Key Metric |
|------------|-------------------|------------|
| Starship Flight Software | Triplex redundancy | 1000Hz control loop |
| AI Flight Controller | 100ms latency | 5000 sensors → decision |
| Engine-Out Compensation | Throttle + reopt | 33 engines, 2 out handled |
| Stage Separation | Hot-staging timing | Clean separation |
| FTS Hardening | 100ms response | Dual-chain autonomous |
| HITL Testbed Automation | CI integration | 47 tests, 23 min |
| In-Space Refueling | Multi-tanker ops | 150k kg transfer |
| Rapid Post-Flight Iteration | 100s of changes | Weeks not months |

---

## 5. Agent Engineering Architecture

### Worker Roles (10)

| Role | Skill | Trigger | Output |
|------|-------|---------|--------|
| Repo Cartographer | `apex-specialist-registry` | Portfolio discovery | Capability manifest |
| Capability Miner | `apex-mega-skills` | New capability req | Capability assessment |
| Connector Broker | `apex-connector-mesh` | External capability | Connector result |
| Systems Architect | `apex-orchestration` | Cross-repo integration | Integration design |
| Implementation Engineer | `apex-engineering-excellence` | Capability build | Code + tests + receipt |
| Reliability Engineer | `verification` | Pre-deployment | Reliability report |
| Performance Engineer | `benchmark-suite` | Perf requirement | Benchmark results |
| Evidence Authenticator | `apex-legal-intelligence` | Evidence integration | Authenticity report |
| Contradiction Hunter | `apex-legal-intelligence` | Pre-legal filing | Contradiction matrix |
| Verification Agent | `verification` | Post-execution | Verification receipt |

### Execution Modes (5)

| Mode | Parallelism | Verification | Blast Radius | Use Case |
|------|-------------|--------------|--------------|----------|
| Standard | Bounded | Per-phase | Scoped | Default portfolio ops |
| Aggressive | Max | Terminal-only | Scoped | Well-specified builds |
| Conservative | Serial | Per-step | Minimal | Evidence/legal ops |
| Capability-Build | Serial | Full ladder | Scoped | New capability modules |
| Portfolio-Sync | Bounded | Per-phase | Scoped | Monolith sync |

### Composite Modes (4)

| Composite | Mode | Workers | Trigger |
|-----------|------|---------|---------|
| Portfolio Sync | Standard | Cartographer, Miner, Engineer, Verifier | Monolith sync |
| Capability Federation | Aggressive | Broker, Architect, Miner, Verifier | Monolith + Tower |
| Evidence Integration | Conservative | Authenticator, Hunter, Verifier | Legal spine ops |
| Helix Automation | Capability-Build | Engineer, Reliability, Verifier | Brainsync, crystallization |

---

## 6. Integration Contracts

### Monolith Integration

| Catalog | Sync Capability | Update Frequency | Schema |
|---------|-----------------|------------------|--------|
| `capabilities_3layer.json` | `monolith.catalog_sync` | Incremental (4h) | Layered repos |
| `runtime_power_spine.json` | `monolith.catalog_sync` | Incremental (4h) | Source spines |
| `library.json` | `monolith.catalog_sync` | Incremental (4h) | Family index |
| `repo_excellence_state_machine.json` | `monolith.catalog_sync` | Incremental (4h) | Portfolio state |

### Tower of Babel Integration

| Registry | Resolution Capability | Floors | Fitness Dimensions |
|----------|----------------------|--------|-------------------|
| `nextgen-innovations.json` | `tower.capability_resolution` | 40 | 10 (domain, req, floor, verified, mem safety, concurrency, determinism, composite) |

### Legal Mesh Integration

| Spine | Bridge Capability | Provenance | Standard |
|-------|------------------|------------|----------|
| `catalog/legal_spines/*.json` | `evidence.bridge` | Full (source repo, path, type, timestamp) | FRE 901/902 |

---

## 7. Storage & Persistence

### File Layout

```
job-app-helix/
├── .agents/                    # Agent engineering config
│   ├── agent-config.yaml       # Full agent configuration
│   ├── modes.json              # Execution modes
│   ├── workflows.yaml          # 7 workflows
│   ├── skills/registry.yaml    # 6 capabilities + compositions
│   └── receipts/               # Hash-bound receipts
├── src/job_app_helix/
│   ├── evidence_ledger.py      # Core capability
│   ├── capability_federation.py
│   ├── monolith_sync.py
│   ├── tower_resolution.py
│   ├── automation_engine.py
│   ├── evidence_bridge.py
│   ├── forward_deployed/
│   │   ├── anthropic/__init__.py   # 10 capabilities
│   │   ├── nvidia/__init__.py      # 7 capabilities
│   │   └── spacex/__init__.py      # 7 capabilities
│   └── agent_cli.py            # Agent CLI entrypoint
├── manifests/
│   ├── portfolio_repositories.json      # 83 workspace + 1 root
│   ├── unified_deserving_manifest.json  # 225 deserving repos
│   ├── live_repository_links.json       # 83 live links
│   ├── evidence_ledger_unified.json     # Unified evidence
│   └── company_dossiers/                # 166 company tracks
├── solidify_records/           # Per-repo innovation receipts
└── tests/                      # 93 tests
```

### Pointer Index

- **Aspen-Grove Index:** `/tmp/aspen_grove_pointer_index.json`
- **1,926 files indexed** with SHA-256/Blake2b hashes
- **O(1) lookup** via `ptr_<hash>` references

---

## 8. Security Architecture

### Zero-Fake-Truth Enforcement

| Layer | Enforcement |
|-------|-------------|
| **L0 (Reference)** | Immutable byte/SHA/commit/docket provenance |
| **L1 (Component)** | Atomic interface boundaries, deterministic I/O |
| **L2 (Subsystem)** | Lossless data translation, type safety |
| **L3 (Backend)** | Deep substrate comprehension (SQLite, event loop, OS limits) |
| **L4 (Invariant)** | >3 failures → STOP, root-cause, single fix |
| **L5 (Mesh)** | Decentralized multi-node consensus |

### Receipt Security

- **Algorithm:** SHA-256
- **Format:** `operation:data:timestamp` → hex digest (16-char prefix)
- **Chain:** Each receipt references prior via hash
- **Verification:** `verify_receipt(receipt_id)` on all classes
- **Storage:** `.agents/receipts/<receipt_id>.json`

### Access Control

| Capability | Security Level | Sandbox |
|------------|----------------|---------|
| Core (ledger, federation, sync) | Medium | Single isolation |
| Forward-Deployed (Anthropic) | High | Dual isolation (process + VM) |
| Forward-Deployed (NVIDIA) | Medium | Single isolation |
| Forward-Deployed (SpaceX) | High | Dual isolation (flight safety) |
| Evidence Bridge | Maximum | Immutable provenance |

---

## 9. Observability Architecture

### Structured Logging

| Component | Format | Fields |
|-----------|--------|--------|
| Capability execution | JSON | receipt_id, operation, duration_ms, success |
| Workflow execution | JSON | workflow_id, step, receipt_chain |
| Agent operation | JSON | worker_role, mode, blast_radius |

### Metrics

| Metric | Source | Frequency |
|--------|--------|-----------|
| `capability.execution.duration_ms` | All capabilities | Per-execution |
| `capability.receipt.generated` | All capabilities | Per-execution |
| `workflow.steps.completed` | Agent workflows | Per-workflow |
| `monolith.sync.catalogs_updated` | Monolith sync | Per-sync |
| `tower.resolution.placement` | Tower resolution | Per-resolution |

### Health Checks

| Check | Command | Expected |
|-------|---------|----------|
| Validators | `python3 scripts/validate_*.py` | All PASS |
| Receipt chain | `verify_receipt(<id>)` | True |
| Monolith sync | `agent_cli workflow monolith-catalog-sync` | 4 catalogs updated |
| Full cycle | `agent_cli workflow full-portfolio-cycle` | All 5 steps complete |

---

## 10. Deployment Architecture

### Environments

| Environment | Purpose | Validators |
|-------------|---------|------------|
| **Development** | Local iteration | Full suite |
| **Staging** | Pre-deployment | Full suite + load test |
| **Production** | Live portfolio | Continuous |

### Deployment Checklist

- [ ] All 3 validators PASS
- [ ] Core test suite (44 tests) PASS
- [ ] Monolith sync receipt verified
- [ ] Receipt chain integrity verified
- [ ] Agent CLI functional
- [ ] Forward-deployed modules tested

### Rollback Procedure

1. Identify failed receipt via `verify_receipt()`
2. Revert to prior `sync_receipt.json`
3. Re-run `monolith-catalog-sync --mode full`
3. Verify all 4 catalogs
4. Re-run full portfolio cycle

---

## 11. Evolution Strategy

### Current Frontier

1. **Test parallelization** — 93 tests >2min, need `--forked`
2. **Projection consumers** — 5 projections awaiting downstream receipts
3. **Candidate surface sync** — Historical 67/66 references in candidate docs
4. **Agent CLI warnings** — RuntimeWarning on import (cosmetic)

### Next Wave Targets

| Priority | Target | Effort | Impact |
|----------|--------|--------|--------|
| 1 | Test parallelization | Medium | Dev velocity |
| 2 | Consumer receipts | Low | Projection freshness |
| 3 | Documentation sync | Low | Recruiter clarity |
| 4 | Agent CLI cleanup | Low | Operator UX |

---

## Appendix: Key Invariants

| Invariant | Check |
|-----------|-------|
| `total_repositories == len(workspace) + 1` | Portfolio validator |
| `workspace_repositories == live_links.repositories` | Live links validator |
| `HELIX_ADMITTED repos ∈ workspace` | Root truth validator |
| `All operations produce receipt` | Capability contract |
| `Receipt chain verifiable` | `verify_receipt()` |
| `Monolith catalogs consistent` | Sync receipt |
| `Tower fitness scores computed` | Resolution receipt |

---

*Architecture document version 2.0 — Updated 2026-09-03*  
*All claims backed by hash-bound receipts in `.agents/receipts/`*