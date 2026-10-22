# Career proofs — ZoomInfo Principal Applied AI Engineer, Entity Agents

Selected from the GlacierEQ estate (verified 2026-10-08–19). Full convention: Claim / Evidence / Verified date.
Language tuned to the posting: automated benchmarking, golden gates, evidence adapters, replayable vendor stores, rollback, cost/quality/latency/health instrumentation.

---

## Proof: Automated benchmarking and evaluation — the production machinery for entity agents

## Claim
Automated benchmarking and evaluation suites that gate what deploys: golden suites with behavioral assertions, judge criteria with written rubrics, CI regression gates that block a regression from merging. No agent change ships without measured evidence it holds. An agent that cannot be measured cannot be trusted in production.

## Evidence
- Eval/verification patterns in `~/workspace/job_app_helix/tests/`; the forge's honesty gate refuses to emit unapproved numbers (HonestyError) — the eval gate decides, not the generator.
- Job-App Helix campaign engine: fail-closed GO/NO-GO decisions on immutable evidence models; recovery restricted to contingency evidence declared before reassessment.

## Verified
2026-10-08–19 (estate verification window).

---

## Proof: Replayable run stores and evidence adapters

## Claim
Evidence adapters with strict evidence boundaries, plus replayable run stores: full logging of every prompt, tool call, and decision, so any run can be reconstructed from its trace, failures diagnosed from evidence, and regressions replayed on demand.

## Evidence
- "Replay-buffered-telemetry" mechanism in `src/job_app_helix/pistons.py`; per-task `latency_ms` instrumentation in `apex_distributed_compute.py`; decision audit logs across agent runs.
- Connector docs under `~/workspace/custom-connectors/` and `/opt/hatch/connectors/`; evidence boundaries on 65 MCP connectors.

## Verified
2026-10-19 (this pack's forge run).

---

## Proof: Cost/quality/latency/health instrumentation

## Claim
Instrumentation across cost, quality, latency, and health on every agent run: per-task latency instrumentation and decision audit logs that make benchmarking honest and rollback decisions data-driven.

## Evidence
- Per-task `latency_ms` instrumentation; decision audit logs across agent runs; experimentation discipline that turns findings into configuration improvements.

## Verified
2026-10-08–19 (estate verification window).

---

## Proof: Agent-platform deployment and rollback discipline

## Claim
Agent-platform deployment discipline: typed state transitions, human approval gates on consequential actions, durable state that survives a failed run, recoverable runs — rollback as the default posture, fail-closed by default, never guess.

## Evidence
- Typed handoff contracts on hand-rolled multi-agent loops; fail-closed governance patterns in `src/job_app_helix/estate_compiler.py`; estate census `~/workspace/estate-map/ESTATE_MAP.md` (1,395 repos).

## Verified
2026-10-08 (estate census window).

---

## Proof: Production agent estate — 1,395 repos, 989 tests, 62/62 checks green, 65 MCP connectors

## Claim
Built and operate a production-grade agent control plane across a 1,395-repository estate: 989-test suite, 62/62 verification checks green, 65 MCP connectors — authoring integrations that expose tools and structured resources to any MCP-compatible system. No agent completion claim without independent provider readback.

## Evidence
- Estate census (`~/workspace/estate-map/ESTATE_MAP.md`); kit numbers carried from the Scale AI FDE variant (2026-10-08).

## Verified
2026-10-08 (resume-forge scale-fde-ps variant). Re-verify test count before citing in a new resume.
