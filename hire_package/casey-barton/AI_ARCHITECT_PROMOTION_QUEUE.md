# AI Architect Promotion Queue

This queue exists to prevent repeated rediscovery. Work is ordered by the strongest next receipt, not by novelty.

## P0 — Anthropic Forward Deployed Engineer: post-submission response receipt

**Source-bound sources:**

- Anthropic / Greenhouse role `5302966008` — Forward Deployed Engineer
- `evidence/applications/anthropic/5302966008-application-received-2026-09-01.json`
- prior-conversation user-supplied Anthropic Careers receipt screenshot dated September 1, 2026
- `evidence/company_intelligence/anthropic-2026-09-07-source-receipt.json`
- `manifests/company_intelligence/anthropic.json`
- existing Casey Barton hire package and application lifecycle

Current state:

- Anthropic acknowledged receipt of Casey's application for Forward Deployed Engineer `5302966008` in the prior user-supplied receipt screenshot on September 1, 2026;
- the current connected Gmail accounts do not contain that message because the screenshot displayed delivery to `caseybarton.ab@gmail.com`, which is not connected in this runtime;
- the live Anthropic Forward Deployed Engineer opening was provider-verified again on September 7, 2026;
- the current role explicitly maps to strategic-customer deployment of production Claude applications and technical artifacts including MCP servers, sub-agents, and agent skills;
- the September 7 generated `READY_FOR_MANUAL_SUBMISSION` packet was post-hoc and must not trigger a duplicate application;
- `evidence/applications/anthropic/5302966008-application-received-2026-09-01.json` now carries the durable `APPLICATION_RECEIVED` state and duplicate-submission guard;
- Anthropic's current Applied AI Architect, Strategic Enterprise Tech opening remains a separate high-fit acquisition lane.

**Next durable receipt:** a new provider-side lifecycle event for FDE `5302966008`: recruiter contact, interview/assessment request, provider status update, rejection/closure, offer, or another explicit employer-side state transition.

**Execution order:**

1. **do not resubmit** FDE `5302966008`;
2. preserve any new Anthropic/provider response against the existing application receipt;
3. transition beyond `SUBMITTED` only on new provider-side evidence;
4. use the current source-bounded proof set for recruiter/hiring-team follow-up or interview preparation when a real contact/event exists;
5. advance the verified Applied AI Architect route in parallel rather than returning to generic proof generation.

**Acquisition invariant:** once an employer has acknowledged receipt, regenerated readiness artifacts cannot demote the application back to `READY` or authorize a duplicate submission.

---

## P0 — Evaluation causal proof

**Source-bound source:** `GlacierEQ/make-it-heavy`

Current state:

- matched longitudinal experiment substrate is merged;
- 8/8-worker Baseline Zero is recorded at 77.7375/100 average supervisory quality;
- the exact Turn-1 template-delta spec already exists;
- Attempt A is quarantined as `SHARED_PROVIDER_RUNTIME_FAILURE` and excluded from learning;
- `receipts/ai-architect-proof-readiness-2026-08-08.json` fixes the next valid experiment to an exact matched rerun under healthy provider conditions;
- current Make-It-Heavy `main` includes Turn-9 semantic claim gating.

**Next durable receipt:** successful exact Turn-1 rerun scored against the frozen rubric.  
**Then:** controlled ablation populating marginal system value / outcome leverage.

Do not redesign the experiment unless a new verified defect invalidates the existing spec.

## P0 — Live capability-security proof

**Source-bound source:** `GlacierEQ/fileboss-whisperx-processor`

Current state: lease-gated Smithery capability mechanics are merged and regression-tested.

**Next durable receipt:** credential-bearing bounded live sequence:

`doctor -> ready lease -> allowlisted read-only call -> durable success receipt -> deny non-allowlisted tool -> deny expired/released lease -> verify scoped token, not master key`

## P1 — Reliability SLO proof

**Source-bound source:** `GlacierEQ/sigma-glue`

Current state: exact recovery identity, concurrency fencing, unsafe-retry prevention, and provider-aware reconciliation are already proven.

**Next durable receipt set:** latency distribution, throughput/concurrency, error rate, recovery rate, unresolved-ambiguity rate, and cost per successful operation under bounded production-like load.

## P1 — Operating-scale proof

**Source-bound source:** `GlacierEQ/job-app-helix`

Current state: the living estate and public recruiter projection are manifest-backed and continue to expand; exact repository/system counts must be read from the current manifests rather than hard-coded into this queue. AKOS multi-version tests, README Mesh, required company tracks, and recruiter-facing estate surfaces remain source-bound proof inputs.

**Next durable ledger:** executed workflow count, integrations by proof state, event/document volumes, successful operations, recovery operations, and verified performance/cost measurements.

## P2 — Forward-deployed outcome proof

Convert technical receipts into operator/business receipts:

- baseline workflow burden;
- post-deployment workflow burden;
- task completion / error / intervention changes;
- adoption or repeated use;
- operator recovery quality;
- attributable time or cost reduction only when measured.

## Promotion invariant

```text
mechanism -> test -> execution -> receipt -> bounded claim -> recruiter projection -> external application -> provider receipt -> response learning
```

A gate is complete only when the relevant external or technical receipt exists. Once a role-specific application is externally received, later internal readiness generation cannot substitute for or erase that provider-side state.
