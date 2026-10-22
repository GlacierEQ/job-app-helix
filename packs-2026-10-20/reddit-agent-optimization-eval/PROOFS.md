# Career proofs — Reddit Software Engineer, Agent Optimization & Evaluation (req 8275745, primary-verified 2026-10-20)

Keyed to the JD keyword set. Convention: Claim / Evidence / Verified date. Domain-edge-first ordering. Evaluation depth comes from his own agent systems estate — no Reddit-platform production depth claimed; no large-scale corporate production systems track record claimed. No invented numbers.

---

## Proof: Evaluation-first delivery — release thresholds, gold sets, LLM-as-judge

## Claim
The JD requires "systems for offline replay, automated evaluation, synthetic task generation, regression detection" and "metrics and experimentation frameworks." He ships measure-first: a 989-test agent control plane with evals carrying explicit release thresholds, gold sets, and LLM-as-judge; an evidence state machine (nominal / recoverable / hard-no-go) whose hard-failure path exits non-zero with CI asserting it — offline regression gating before anything promotes.

## Evidence
- `job-app-helix` — 989-test agent control plane; evidence state machine; CI-asserted hard-failure exit.
- `~/workspace/job-app-helix/hire_package/resume-forge/content/reddit-agent-opt-eval.yaml` — experience bullet (primary source for the tailored resume).

## Verified
2026-10-20 (pack provenance; estate census re-verified live same day: `gh api /user` = 695 public + 703 private = 1,398 repos).

---

## Proof: Agent-behavior tooling — failure investigation and iteration speed

## Claim
The JD requires "tooling to analyze agent behavior, investigate failures, and accelerate iteration." His agent coordinator is a deterministic DAG scheduler with 62/62 tests green; tool calls are proposed for review, never executed blind; run-state observability is structured by design — typed states and receipts that an experimentation framework can measure.

## Evidence
- `anthropic-agent-coordinator` — deterministic DAG scheduler; 62/62 tests green; review-gated tool calls (estate lineage, carried from prior pack runs).

## Verified
2026-10-20 (pack provenance).

---

## Proof: Model-agnostic routing and orchestration — quality / latency / cost

## Claim
The JD requires "model routing and orchestration strategies that optimize for quality, latency, and cost" and a "flexible, model-agnostic agent platform." He federates Mem0, Supermemory, Supabase pgvector, Pinecone, and Neo4j behind one MCP interface — routing across models and providers with provenance and structured outputs; parallel fan-out with content-hash dedup.

## Evidence
- `unified-memory-mcp`, `mcp-iceberg-mansion` — federated memory behind one MCP interface (estate lineage).

## Verified
2026-10-20 (pack provenance).

---

## Proof: Production feedback loops — root-cause quarantine, not silent retries

## Claim
The JD's harness "incorporates production feedback" and "learns from production usage." His control plane runs cloud deployment with access controls, SHA-256 transport envelopes, idempotency keys, circuit breakers, dead-letter capture, and fail-closed startup; failure analysis uses root-cause quarantine instead of silent retries — production runs feeding back into iteration.

## Evidence
- `apex-control-plane` — deployment hardening, transport envelopes, dead-letter capture, fail-closed startup (estate lineage).

## Verified
2026-10-20 (pack provenance).

---

## Proof: Human-in-the-loop controls — feedback built into the orchestration layer

## Claim
The JD requires "human-in-the-loop feedback." His controls are not bolted on: review gates with real veto power (the forge's honesty gate raises HonestyError rather than render an unverified bold number; the campaign engine's GO/NO-GO gate vetoes composition); recovery restricted to contingency evidence declared before reassessment — the engine never silently tunes values until they pass.

## Evidence
- `~/workspace/job-app-helix/hire_package/resume-forge/cover.py` — `honesty_gate()`.
- `job-app-helix` — GO/NO-GO composition gate with veto power.

## Verified
2026-10-20 (pack provenance).

---

## Proof: Platform/infra partnership surface — 65 MCP connectors

## Claim
The JD requires partnering "closely with Platform Engineering, Infrastructure, and Developer Productivity teams to integrate agent capabilities into engineering workflows." His integration surface: 65 MCP connectors integrated with claim tracking and idempotent automation — a portfolio-wide connector practice, not one-off wiring.

## Evidence
- GlacierEQ estate connector inventory (estate lineage, carried from prior pack runs).

## Verified
2026-10-20 (pack provenance; connector count carried — re-verify before submit if material to the pitch).

---

## Numbers provenance
- **1,398 repos (695 public + 703 private):** live-verified 2026-10-20 via `gh api /user` — NOT carried, verified this run.
- **989-test control plane, 62/62 tests, 65 MCP connectors, 20+ production repos:** estate lineage carried from prior pack runs (kit lineage; primary-verified in earlier runs, not re-run here).
- **Comp $109,800–$325,000 base + RSUs:** read on the primary Greenhouse page 2026-10-20.
- **Req 8275745 / published 2026-10-18 / Remote - United States:** read on the primary Greenhouse page 2026-10-20.
