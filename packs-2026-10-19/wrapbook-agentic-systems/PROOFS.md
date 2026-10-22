# Career proofs — Wrapbook Senior Software Engineer II, Applied AI (Agentic Systems)

Selected from the GlacierEQ estate (verified 2026-10-08 – 2026-10-19). Full convention: Claim / Evidence / Verified date.
Language tuned to Wrapbook's posting: production-grade agents, evaluation/observability/guardrail frameworks, multi-agent orchestration, security-first with failure-mode thinking, reusable patterns, cost tracking, end-to-end ownership.

---

## Proof: Evaluation, observability, and guardrail frameworks — the team's core mandate

## Claim
Builds the evaluation, observability, and guardrail frameworks that decide whether an agent is actually doing the job: eval suites with golden sets and behavioral assertions, judge rubrics, full trace logging, regression gates — measured against a baseline, every run; humans kept in the loop where it matters via approval gates.

## Evidence
- Eval/verification patterns in `~/workspace/job-app-helix/tests/`; the forge's honesty gate refuses to emit unapproved numbers (HonestyError) — the eval gate decides, not the generator.
- Job-App Helix: fail-closed GO/NO-GO decisions on immutable evidence models; no agent completion claim without independent provider readback; recovery restricted to contingency evidence declared before reassessment.

## Verified
2026-10-08–19 (estate verification window).

---

## Proof: Multi-agent orchestration — hand-rolled loops, typed handoffs, human gates

## Claim
Designs and runs multi-agent orchestration end to end: planning and tool-use loops with retrieval, memory, guardrails, typed handoff contracts between agents, and human approval gates on consequential actions — durable state that survives a failed run. Establishes reusable patterns, shared tools, and best practices so every new agent ships on the same spine.

## Evidence
- Production multi-agent loops across the GlacierEQ estate (`src/job_app_helix/`, apex orchestration repos); claim tracking, evidence boundaries, and audit receipts as durable estate patterns.
- **Gap, flagged honestly:** orchestration is hand-rolled, not LangGraph. Same primitives (state, tools, memory, guardrails, checkpoints) — different library. No Bedrock AgentCore production use.

## Verified
2026-10-19 (estate window).

---

## Proof: Security-first with failure-mode thinking — agents that take real actions, safely

## Claim
Builds agents that take real actions with security-first design: evidence boundaries on every tool, typed handoff contracts, human approval gates on consequential actions, fail-closed on ambiguous state, decision audit receipts on every run. Thinks about data access, permissions, and failure modes in everything built.

## Evidence
- Fail-closed governance patterns in the job-app-helix campaign engine; nothing sends or submits without explicit approval — a standing operating rule verified across the estate.
- Per-run decision audit logs; claim tracking with evidence boundaries.

## Verified
2026-10-19 (estate window).

---

## Proof: Cost tracking — per-task latency and token-cost instrumentation

## Claim
Tracks what agents cost to run: per-task latency and token-cost instrumentation across runs, model-agnostic benchmarking on every model release — so scaling decisions are measured, not guessed.

## Evidence
- Per-task `latency_ms` instrumentation (e.g., `apex_distributed_compute.py`); cost/latency tradeoff analysis in the benchmark discipline across `src/job_app_helix/`.

## Verified
2026-10-19 (estate window).

---

## Proof: Python/TypeScript backend — production services, not demos

## Claim
Ships production backend systems in Python and TypeScript/Node.js: REST APIs, event-driven services, Supabase/Postgres data layers, containerized deployments with CI/CD — built for availability, performance, and observability.

## Evidence
- Estate services: backend API work across the GlacierEQ repos; Supabase/Postgres schemas; GitHub Actions CI pipelines; Vercel-deployed production surfaces.
- **Gap, flagged honestly:** his founder run is 3 years of evidence-grade agent systems (his approved number); the JD asks for 6+ years back-end. Not inflated in the resume.

## Verified
2026-10-19 (estate window).

---

## Proof: 65 MCP connectors — the integration layer agents act through

## Claim
Authors MCP servers and connectors that expose tools and structured resources to any MCP-compatible system — the shared, governed integration layer agents use to take real actions: ERPs, CRMs, data pipelines, webhooks, messaging — with evidence boundaries and audit receipts.

## Evidence
- Connector docs under `~/workspace/custom-connectors/` and `/opt/hatch/connectors/`; claim tracking and idempotent automation patterns across the estate.

## Verified
2026-10-08–19 (estate census window; his approved number).

---

## Proof: Production agent estate — 1,395 repos, 989 tests, 62/62 checks green

## Claim
Built and operate a production-grade agent control plane across a 1,395-repository estate: agent governance, MCP integrations, context externalization, document workflows. 989-test suite, 62/62 verification checks green — no claim without independent provider readback.

## Evidence
- Estate census (`~/workspace/estate-map/ESTATE_MAP.md`); kit numbers from `_candidate.yaml` (verified 2026-10-13).

## Verified
2026-10-13 (census). Re-verify test count before citing in a new resume.
