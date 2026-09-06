# AI Architect Capability Proof Matrix

> Source-bound hiring proof surface for senior AI architecture roles. This file separates **verified mechanisms**, **current proof limits**, and **next promotion gates**. It is not a technology inventory.

## Positioning

Primary role family:

1. Forward-Deployed AI Architect
2. Principal Agentic Systems Architect
3. Principal AI Platform / Automation Architect
4. Staff / Principal Applied AI Engineer

The recurring system pattern is:

```text
state -> interfaces -> orchestration -> intelligence -> execution -> verification -> persistence
```

The portfolio claim is therefore architecture ownership across model/tool/data/security/evaluation/operations boundaries, not narrow model research.

---

## Proof Pillar 1 — Evaluation and Agent Science

### VERIFIED

**Make-It-Heavy longitudinal worker science is merged to `main`.**

Evidence anchors:

- `GlacierEQ/make-it-heavy#35` — merged longitudinal experiment substrate.
- Merge commit: `1e90366b53e808ea11549096afabedf9d07b53cb`.
- Supports matched `BASELINE`, `TEMPLATE_DELTA`, `ABLATION`, and `OBSERVATION` experiments.
- Freezes topology for controlled comparisons.
- Prevents unrelated prompt/template state from contaminating experiments.
- Separates structural worker quality, legacy heuristic benefit, causal marginal system value, and outcome leverage.
- Persists predecessor matching only inside the same mission family + comparison key.

**A real eight-worker baseline specimen is also merged.**

- `GlacierEQ/make-it-heavy#36` — merged Baseline Zero specimen.
- Merge commit: `256b68be3f71117d58dd7ef5eaab3cf5b3ab8d3c`.
- 8/8 workers completed and were reviewable.
- Average supervisory quality: **77.7375/100**.
- The receipt records material evidence-state errors, overreach failures, calibration gaps, and pass-with-limits outcomes instead of flattening them into a success claim.

### CURRENT CLAIM CEILING

Safe external claim:

> Built a longitudinal evaluation substrate for multi-agent workers with matched experiments, topology freezing, prompt isolation, persisted comparison state, explicit ablation support, and a reproducible eight-worker baseline.

Do **not** yet claim that the worker system has causally improved. `marginal_system_value` and `outcome_leverage` remain unmeasured until matched reruns and ablation populate them.

### NEXT PROMOTION GATE

1. Complete a matched template-delta rerun against Baseline Zero.
2. Run at least one ablation that populates causal marginal system value and outcome leverage.
3. Persist worker timing / overlap measurements rather than leaving them NULL.
4. Add provider diversity before generalizing behavior across model providers.

---

## Proof Pillar 2 — Production Reliability and Recovery

### VERIFIED

**Sigma Glue has a merged, adversarially tested at-most-once transport-entry and recovery architecture.**

Evidence anchors:

- `GlacierEQ/sigma-glue#13` — merged exact-envelope dispatch recovery hardening.
- Merge commit: `80f6ca8f3fb7dd54cbbe261f867ca1d9bd22a99b`.
- Exact-head verification: **109/109 tests passed**, 0 failed, 0 skipped on Node 22.23.1.
- Durable `started` evidence binds permit, request identity, and immutable envelope fingerprint before transport.
- Timeouts, malformed receipts, or persistence uncertainty prohibit unsafe automatic replay.
- Concurrency proof includes eight independent processes competing for one persisted permit.
- Legacy uncertain state is migrated fail-closed rather than upgraded into false certainty.

**Provider-aware recovery is also merged.**

- `GlacierEQ/sigma-glue#14` — merged provider-outcome recovery.
- Merge commit: `4a1ca8e5c88a62e8a94a43213b2c509af6afcea3`.
- Conditional SHA-bound GitHub Contents writes.
- Exact desired/baseline fingerprints.
- Read-after-write provider observation.
- Explicit states: `confirmed_applied`, `confirmed_not_applied`, `still_unknown`.
- Retry is forbidden after confirmed application or unresolved ambiguity.
- Provider identity and target scope are bound into durable recovery evidence.

### CURRENT CLAIM CEILING

Safe external claim:

> Designed durable idempotency, concurrency fencing, recovery-required states, provider reconciliation, and fail-closed retry semantics around external AI/tool execution paths.

Do **not** describe this as distributed consensus or provider-transactional exactly-once execution. The proven boundary is at-most-once transport entry plus provider-aware reconciliation under explicit evidence conditions.

### NEXT PROMOTION GATE

The remaining portfolio gap is **operational SLO evidence**, not basic recovery mechanics:

1. sustained live-load latency distributions;
2. error / recovery / replay rates over time;
3. throughput and concurrency under bounded production-like load;
4. cost-per-successful-operation;
5. operator-facing reliability dashboard and incident / recovery receipts.

Until receipts exist, do not publish unsupported latency, throughput, or scale claims.

---

## Proof Pillar 3 — Security Architecture and Bounded Capability Execution

### VERIFIED

**FileBoss has a merged lease-gated remote MCP capability fabric.**

Evidence anchor:

- `GlacierEQ/fileboss-whisperx-processor#166` — merged Smithery capability fabric.
- Merge commit: `ee732b304301bbf401f086d95cd6f86e0977358f`.

Security mechanisms include:

- declared capabilities and exact tool allowlists;
- durable lease state before remote execution;
- registry SHA-256 and complete-plan binding;
- exact connection and metadata guards;
- conservative interpretation of MCP tool annotations;
- explicit local gates for write/destructive actions;
- fresh short-lived service tokens scoped to namespace, execution capability, binding metadata, `tools/call`, and exact tool name;
- master API key separation from actual tool execution;
- hash-only persisted/surfaced error evidence to reduce secret leakage;
- request/response size bounds and verified TLS;
- no blind automatic retry after execution uncertainty.

Verification recorded in the merged PR:

- **22 focused baseline Smithery assertions passed** during implementation.
- **16/16 post-review regression assertions passed** after protocol hardening.

### CURRENT CLAIM CEILING

Safe external claim:

> Built capability-governed MCP execution patterns using leases, exact allowlists, attenuated short-lived tokens, master-key separation, hash-bound plans, conservative annotations, audit receipts, and fail-closed uncertainty handling.

### NEXT PROMOTION GATE

The merged PR explicitly did **not** claim a real credential-bearing Smithery execution. Promotion requires a bounded live proof that records:

1. real `doctor`/connection verification;
2. ready lease;
3. one allowlisted read-only call;
4. durable started/succeeded receipts;
5. non-allowlisted rejection;
6. expired/released lease rejection;
7. proof that the MCP POST used the scoped service token rather than the master API key.

Do not upgrade the claim until those live receipts exist.

---

## Proof Pillar 4 — Scale and Systems Breadth

### VERIFIED

Current hiring package claims are bounded by an exact register while separating present estate size from historical audit scope:

- **Current source-exhaustive estate:** 225 deserving repositories across 21 families.
- **Historical governed Helix boundary:** 67 repositories — one control-plane root plus 66 children — preserved as a dated recruiter/audit scope, not a present portfolio cap.
- **Verified trust anchors:** 8 repository-level anchors in the current estate evidence surface.
- **AKOS: 94/94 tests** across 12 modules on Python 3.11–3.13.
- **21-node README Mesh rollout** verified.
- One governed public APEX Action Face execution path is verified; this is intentionally not generalized to every route or workload.

Source: `hire_package/casey-barton/CLAIM_REGISTER.md`.

Current company-analysis topology also demonstrates orchestration breadth without pretending that planning equals execution:

- `manifests/company_dossiers.json` currently enumerates **76 required company tracks**, including `glaciereq_core`.
- `manifests/company_analysis_topology.json` defines one mission orchestrator, two domain leads, eight specialists, and one integration coordinator with an eight-task wave size and explicit quality gates.
- The topology's own truth boundary says deterministic planning is **not** runtime proof, model consensus, or company affiliation.

### CURRENT CLAIM CEILING

Safe external claim:

> Operates an evidence-bound AI systems estate of 225 deserving repositories across 21 families, preserves a historical 67-repository governed audit boundary for receipt integrity, maintains 8 verified trust anchors, cross-version AKOS verification, a 21-node human/machine documentation mesh, and a deterministic company-analysis control plane spanning 76 target tracks.

The number is secondary. Lead with what the systems coordinate, verify, and govern.

### NEXT PROMOTION GATE

Convert breadth into harder operating evidence:

1. exact active integrations by type and proof state;
2. executed workflow count, not planned workflow count;
3. document / event volumes processed with reproducible receipts;
4. successful operation and failure-recovery counts;
5. measurable user/operator impact;
6. verified performance and cost metrics.

Unsupported scale claims remain excluded.

---

## Consolidated Senior-Role Signal

The current evidence supports this positioning:

> **Forward-Deployed AI Architect / Principal Agentic Systems Architect** who designs and builds control planes around probabilistic AI: evaluation, orchestration, capability security, durable execution, provider reconciliation, provenance, and multi-system integration.

The missing layer is no longer "can this architecture be built?" The evidence already shows substantial architecture and verification. The remaining promotion work is to accumulate **causal evaluation results, live security receipts, longitudinal SLOs, and user-impact scale evidence**.

---

## Highest-Value Proof Queue

| Priority | Gate | Why it matters | Promotion effect |
|---|---|---|---|
| P0 | Matched worker delta + ablation | Converts evaluation framework into causal outcome evidence | Agentic Systems Architect |
| P0 | Live lease-gated Smithery proof | Converts security architecture into credential-bearing integration proof | Forward-Deployed / Platform Architect |
| P1 | Reliability SLO receipt set | Converts adversarial correctness into operating reliability evidence | Principal AI Platform Architect |
| P1 | Scale telemetry ledger | Converts portfolio breadth into measurable systems scale | Principal / Staff leveling |
| P2 | User-impact receipts | Connects technical architecture to business/operator outcomes | Forward-Deployed AI Architect |

## Governing Rule

Every future portfolio promotion should satisfy:

```text
mechanism -> test -> live/realistic execution -> receipt -> bounded claim -> recruiter projection
```

If one stage is missing, preserve the stronger engineering work but keep the external claim at the last verified stage.
