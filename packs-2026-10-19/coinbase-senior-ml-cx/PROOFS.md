# Career proofs — Coinbase Senior ML Engineer, CX Intelligence Engineering

Selected from the GlacierEQ estate (verified 2026-10-08–19). Full convention: Claim / Evidence / Verified date.
Language tuned to the posting: unified orchestration layer, agent assist, secure LLM-powered actions, compliant at scale.

---

## Proof: Unified orchestration layer for multi-agent CX

## Claim
Builds the unified orchestration layer for multi-agent systems: hand-rolled multi-agent loops with function calling, structured outputs, and typed handoff contracts — every decision receipted, every action reconstructable from its trace.

## Evidence
- Agent systems under `~/workspace/` (memory gateway helper, estate compiler, job-app-helix engine); estate census `~/workspace/estate-map/ESTATE_MAP.md` (1,395 repos).
- Typed handoff contracts on hand-rolled multi-agent loops; fail-closed governance patterns in `src/job_app_helix/estate_compiler.py`.

## Verified
2026-10-08 (estate census window).

---

## Proof: Agent assist with human-in-the-loop control

## Claim
Agent-assist systems where consequential actions carry typed human approval gates: approval gates typed into state transitions, recoverable runs with durable state that survives failure — a human stays in the loop by architecture, not by policy doc.

## Evidence
- Human approval gates on consequential actions in `src/job_app_helix/estate_compiler.py`; recoverable-run patterns across the estate; fail-closed GO/NO-GO decisions in the campaign engine.

## Verified
2026-10-08–19 (estate verification window).

---

## Proof: Secure LLM-powered actions, gated by evaluation

## Claim
LLM-powered actions that are secure because they're gated: golden suites with behavioral assertions, judge criteria with written rubrics, and CI regression gates that block a regression from merging — before anything touches a real customer. Fail-closed by default, never guess.

## Evidence
- Eval/verification patterns in `~/workspace/job_app_helix/tests/`; the forge's honesty gate refuses to emit unapproved numbers (HonestyError) — the eval gate decides, not the generator.
- Job-App Helix campaign engine: verification gates on every agent action; no agent completion claim without independent provider readback.

## Verified
2026-10-19 (this pack's forge run).

---

## Proof: Compliant at scale — governance as architecture

## Claim
Compliance built into the system, not bolted on: evidence boundaries, decision audit logs on every action, audit receipts, per-task latency instrumentation — the auditability and observability primitives a regulated-scale multi-agent platform requires.

## Evidence
- Evidence boundaries on 65 MCP connectors; decision audit logs across agent runs; claim-tracking patterns across the full estate; connector docs under `~/workspace/custom-connectors/` and `/opt/hatch/connectors/`.

## Verified
2026-10-08–19 (estate verification window).

---

## Proof: Production agent estate — 1,395 repos, 989 tests, 62/62 checks green, 65 MCP connectors

## Claim
Built and operate a production-grade agent control plane across a 1,395-repository estate: 989-test suite, 62/62 verification checks green, 65 MCP connectors — authoring integrations that expose tools and structured resources to any MCP-compatible system. No agent completion claim without independent provider readback.

## Evidence
- Estate census (`~/workspace/estate-map/ESTATE_MAP.md`); kit numbers carried from the Scale AI FDE variant (2026-10-08).

## Verified
2026-10-08 (resume-forge scale-fde-ps variant). Re-verify test count before citing in a new resume.
