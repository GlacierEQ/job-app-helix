# Career proofs — Mastra AI Engineer

Selected from the GlacierEQ estate (verified 2026-10-08–19). Full convention: Claim / Evidence / Verified date.
Language tuned to Mastra's posting: agent evaluation, trace intelligence, benchmarking, autoevals/rollouts, shipped-production agents.

---

## Proof: Eval harnesses on every agent — the machine that decides whether an agent ships

## Claim
Designs evaluations, not spot checks: golden suites with behavioral assertions, judge criteria with written rubrics, replay loops, and CI regression gates that block a regression from merging. Prompt and configuration changes are validated by eval harnesses before anything touches production. An agent that cannot be measured cannot be trusted with anything beyond reading.

## Evidence
- Eval/verification patterns in `~/workspace/job-app-helix/tests/`; the forge's honesty gate refuses to emit unapproved numbers (HonestyError) — the eval gate decides, not the generator.
- Job-App Helix campaign engine: fail-closed GO/NO-GO decisions on immutable evidence models; recovery restricted to contingency evidence declared before reassessment.

## Verified
2026-10-08–19 (estate verification window).

---

## Proof: Trace intelligence — every run reconstructable from its trace

## Claim
Full logging of every prompt, tool call, and decision across agent runs, so any run can be reconstructed and debugged from its trace. Failed evals are diagnosed from evidence, not argued about. Per-task latency instrumentation and decision audit logs make benchmarking honest.

## Evidence
- "Replay-buffered-telemetry" mechanism in `src/job_app_helix/pistons.py`; per-task `latency_ms` instrumentation in `apex_distributed_compute.py`; decision audit logs across agent runs.
- Eval layer discipline: golden suites with behavioral assertions rather than intuition; safety cases that must pass on every run.

## Verified
2026-10-19 (this pack's forge run).

---

## Proof: Shipped production agents, tuned for accuracy against datasets

## Claim
Shipped agents and agentic applications into production, then tuned them to improve accuracy — benchmarking agent primitives against datasets, investigating where they perform well and where they fall short, and turning findings into configuration improvements. Hand-rolled multi-agent loops with function calling, structured outputs, and typed handoff contracts; durable state so work survives a failed run.

## Evidence
- Agent systems under `~/workspace/` (memory gateway helper, estate compiler, job-app-helix engine); estate census `~/workspace/estate-map/ESTATE_MAP.md` (1,395 repos).
- Typed handoff contracts on hand-rolled multi-agent loops; fail-closed governance patterns in `src/job_app_helix/estate_compiler.py`.

## Verified
2026-10-08 (estate census window).

---

## Proof: 65 MCP connectors — authoring integrations any MCP-compatible system can use

## Claim
65 MCP connectors plus APIs, webhooks, and data pipelines, built as authoring work: integrations that expose tools and structured resources to any MCP-compatible system, with evidence boundaries and audit receipts for compliance-aware deployment.

## Evidence
- Connector docs under `~/workspace/custom-connectors/` and `/opt/hatch/connectors/`; claim tracking and idempotent automation patterns across the estate.

## Verified
2026-10-08–19 (estate census window).

---

## Proof: Production agent estate — 1,395 repos, 989 tests, 62/62 checks green

## Claim
Built and operate a production-grade agent control plane across a 1,395-repository estate: typed state transitions, human approval gates on consequential actions, recoverable runs. 989-test suite, 62/62 verification checks green — no agent completion claim without independent provider readback.

## Evidence
- Estate census (`~/workspace/estate-map/ESTATE_MAP.md`); kit numbers carried from the Scale AI FDE variant (2026-10-08).

## Verified
2026-10-08 (resume-forge scale-fde-ps variant). Re-verify test count before citing in a new resume.
