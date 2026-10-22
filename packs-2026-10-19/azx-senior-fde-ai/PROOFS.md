# Career proofs — AZX Senior Forward Deployed AI Engineer

Selected from the GlacierEQ estate (verified 2026-10-08–19). Full convention: Claim / Evidence / Verified date.
Language tuned to the posting's trust-machinery requirements.

---

## Proof: Eval harnesses + replay loops you can defend to a skeptic

## Claim
Ships nothing without an eval gate: prompt and configuration changes are validated by eval harnesses with replay loops before anything touches production. The forge itself enforces an honesty gate — unapproved numbers raise HonestyError and stop the build.

## Evidence
- Eval/verification patterns in `~/workspace/job-app-helix/tests/`; "replay-buffered-telemetry" mechanism in `src/job_app_helix/pistons.py`; fail-closed governance patterns in `src/job_app_helix/estate_compiler.py`.
- This pack's provenance: built by forge variant `azx-fde-ai`, which refused to emit anything outside verified kit numbers.

## Verified
2026-10-19 (this pack's forge run).

---

## Proof: Guardrails + the defined "what happens when it's unsure" path

## Claim
Guardrails live in the orchestration layer: typed state transitions, approval gates on consequential actions, fail-closed recovery. "Cannot determine" is a first-class answer — the agent halts and escalates, never guesses. This is the posting's exact ask.

## Evidence
- Fail-closed governance patterns in `src/job_app_helix/estate_compiler.py`; Job-App Helix composes assessments into campaign-level GO / NO-GO with immutable evidence models and fail-closed decisions; recovery restricted to contingency evidence declared before reassessment — the engine never silently tunes values until they pass.

## Verified
2026-10-08–19 (estate verification window).

---

## Proof: Monitoring + cost/latency budgets per run

## Claim
Every agent run is instrumented: per-task latency recorded, failure tracked, latency and token cost treated as first-class benchmarks measured and logged — priced into the eval discipline rather than discovered in production.

## Evidence
- Per-task `latency_ms` instrumentation in `src/job_app_helix/apex_distributed_compute.py`; performance monitoring with A/B testing as standing practice; estate benchmark contract tracks context/token efficiency and task latency (`~/workspace/job-app-helix/AGENTS.md` §28).

## Verified
2026-10-19 (source read during this pack's build).

---

## Proof: Structured outputs, tool use, retrieval — in production

## Claim
Hand-rolled multi-agent orchestration with function calling against typed tool schemas, structured outputs, typed handoff contracts, and retrieval-augmented generation over his own estate (memory mesh, estate map).

## Evidence
- Agent systems under `~/workspace/` (memory gateway helper, estate compiler, job-app-helix engine); 65 MCP connectors with claim tracking, evidence boundaries, and idempotent automation; connector docs under `~/workspace/custom-connectors/` and `/opt/hatch/connectors/`.

## Verified
2026-10-08–19 (estate census window). Framework claim is hand-rolled loops only — no production LangGraph claimed.

---

## Proof: Fail-closed on the 6,000+ file migration — the deterministic-gate pattern

## Claim
Dropbox → Google Drive migration worker moved 6,000+ files with md5+size verification per file, idempotent JSONL ledger resume, per-file root-cause quarantine. Nothing deleted from source; sealed archives never opened. This is the deterministic-check-gating-a-sensitive-operation pattern the posting describes for money/compliance answers.

## Evidence
- Worker: `~/workspace/stranded-files-move/worker.sh` (lock-protected, resumable); run ledgers under `~/workspace/goals/stranded-files-move-dropbox-google-drive/`; live hourly run scoreboards in `~/memory/2026-10-19.md`.

## Verified
2026-10-19 (live runs today).

---

## Proof: Client-embedded field pattern — discovery to measured handover

## Claim
Embedded-style delivery is the standing operating mode: map the operator's workflow, build the narrow end-to-end proof, run the demo, deepen the components that carry real load — then turn deployment learnings into platform capability. Measurement story (KPIs, baselines, instrumentation) agreed in writing before deployment.

## Evidence
- The estate's build history (`~/workspace/estate-map/ESTATE_MAP.md`); job-app-helix itself (agent-built application pipeline with verification gates).
- His standing job-hunt contract: fire-ready actions only, capability built FROM his actual work.

## Verified
Standing doctrine, demonstrated 2026-10-19 (this pack is itself the evidence: researched, tailored, forged end-to-end in one run).

---

## Proof: Production agent estate — 1,395 repos, 989 tests, 62/62 checks green

## Claim
Built and operate a production-grade agent control plane across a 1,395-repository estate: typed state transitions, human approval gates on consequential actions, recoverable runs. 989-test suite, 62/62 verification checks green — no agent completion claim without independent provider readback.

## Evidence
- Estate census (`~/workspace/estate-map/ESTATE_MAP.md`); test suite from the estate's own test runs.
- Kit numbers carried from the Scale AI FDE variant (2026-10-08).

## Verified
2026-10-08 (resume-forge scale-fde-ps variant). Re-verify test count before citing in a new resume.
