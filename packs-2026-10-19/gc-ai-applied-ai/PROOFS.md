# Career proofs — GC AI Member of Technical Staff, Applied AI

Selected from the GlacierEQ estate (verified 2026-10-08–19). Full convention: Claim / Evidence / Verified date.
Language tuned to the posting: model evaluation, internal prototyping frameworks, applied AI.

---

## Proof: Model evaluation as owned work

## Claim
Owns model evaluation end to end: golden suites with behavioral assertions, judge criteria with written rubrics, automated benchmarking loops — the harness that decides whether a model or agent change ships. Prompt and configuration changes are validated by eval harnesses before anything touches production.

## Evidence
- Eval/verification patterns in `~/workspace/job_app_helix/tests/`; the forge's honesty gate refuses to emit unapproved numbers (HonestyError) — the eval gate decides, not the generator.
- Job-App Helix campaign engine: fail-closed GO/NO-GO decisions on immutable evidence models; verification gates on every agent action.

## Verified
2026-10-08–19 (estate verification window).

---

## Proof: Internal prototyping frameworks

## Claim
Builds internal prototyping frameworks: hand-rolled multi-agent loops with function calling, structured outputs, and typed handoff contracts — prototypes that run under the same eval discipline as production, so a prototype that survives is already proven.

## Evidence
- Agent systems under `~/workspace/` (memory gateway helper, estate compiler, job-app-helix engine); typed handoff contracts on hand-rolled multi-agent loops; fail-closed governance patterns in `src/job_app_helix/estate_compiler.py`.

## Verified
2026-10-08–19 (estate verification window).

---

## Proof: Trace intelligence — every run reconstructable

## Claim
Trace intelligence wired into every run: full logging of every prompt, tool call, and decision, so any execution is reconstructable and debuggable from its trace. Failed evals are diagnosed from evidence, not argued about.

## Evidence
- "Replay-buffered-telemetry" mechanism in `src/job_app_helix/pistons.py`; per-task `latency_ms` instrumentation in `apex_distributed_compute.py`; decision audit logs across agent runs.

## Verified
2026-10-19 (this pack's forge run).

---

## Proof: TypeScript + Python production engineering

## Claim
TypeScript + Python production work across the estate: REST APIs, containers, Postgres/Supabase, CI/CD — the full stack behind the eval systems. NO CLAIM of React-app-scale product experience — the pack is explicit about this gap.

## Evidence
- Production systems under `~/workspace/`; TypeScript and Python across the estate; evidence boundaries and audit receipts on deployed systems.

## Verified
2026-10-19 (this pack's forge run). Gap disclosure: TypeScript production work verified; React-app-scale experience NOT claimed.

---

## Proof: Production agent estate — 1,395 repos, 989 tests, 62/62 checks green, 65 MCP connectors

## Claim
Built and operate a production-grade agent control plane across a 1,395-repository estate: 989-test suite, 62/62 verification checks green, 65 MCP connectors — authoring integrations that expose tools and structured resources to any MCP-compatible system. Ships fast, measures everything.

## Evidence
- Estate census (`~/workspace/estate-map/ESTATE_MAP.md`); kit numbers carried from the Scale AI FDE variant (2026-10-08).

## Verified
2026-10-08 (resume-forge scale-fde-ps variant). Re-verify test count before citing in a new resume.
