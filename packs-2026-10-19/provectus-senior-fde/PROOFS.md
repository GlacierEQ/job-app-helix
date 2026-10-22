# Career proofs — Provectus Senior Forward Deployed AI Engineer (GenAI, AWS)

Selected from the GlacierEQ estate (verified 2026-10-08–19). Full convention: Claim / Evidence / Verified date.
Language tuned to the posting's "evaluation harness before the feature" and FDE operating model.

---

## Proof: Eval harness built before the feature — defined, instrumented, design-driving

## Claim
For non-deterministic systems, "it looked good in testing" is not an answer. He defines what working means, instruments it, and lets the evals drive the design. Prompt and configuration changes are validated by eval harnesses with replay loops before anything touches production.

## Evidence
- Eval/verification patterns in `~/workspace/job-app-helix/tests/`; "replay-buffered-telemetry" mechanism in `src/job_app_helix/pistons.py`; the forge's honesty gate refuses to emit unapproved numbers (HonestyError) — the discipline is automated, not aspirational.
- Job-App Helix composes assessments into campaign-level GO / NO-GO with immutable evidence models and fail-closed decisions; recovery restricted to contingency evidence declared before reassessment.

## Verified
2026-10-19 (this pack's forge run).

---

## Proof: Failure-mode reasoning for non-deterministic systems

## Claim
He understands what the models do well enough to reason about failure modes, not just call the API: guardrails live in the orchestration layer — typed state transitions, approval gates on consequential actions, fail-closed recovery. "Cannot determine" is a first-class answer: the agent halts and escalates, never guesses.

## Evidence
- Fail-closed governance patterns in `src/job_app_helix/estate_compiler.py`; typed handoff contracts on hand-rolled multi-agent loops.

## Verified
2026-10-08–19 (estate verification window).

---

## Proof: Production GenAI systems — structured extraction, retrieval, structured outputs

## Claim
Ships structured facts out of messy inputs: structured extraction and retrieval pipelines, structured outputs, function calling with typed tool schemas, RAG over his own estate — backed by a 989-test control plane with 62/62 verification checks green.

## Evidence
- Agent systems under `~/workspace/` (memory gateway helper, estate compiler, job-app-helix engine); `~/workspace/estate-map/ESTATE_MAP.md` (1,395-repo census).

## Verified
2026-10-08 (estate census window).

---

## Proof: 65 MCP connectors — integration surface into environments he doesn't own

## Claim
65 MCP connectors plus APIs, webhooks, and data pipelines, with evidence boundaries and audit receipts built for compliance-aware deployment regimes. He chooses tools to fit the customer, not the résumé.

## Evidence
- Connector docs under `~/workspace/custom-connectors/` and `/opt/hatch/connectors/`; claim tracking and idempotent automation patterns in the estate.

## Verified
2026-10-08–19 (estate census window).

---

## Proof: Embedded delivery — scope with operators, prove end to end, hand over runnable systems

## Claim
Embedded-style delivery is the standing operating mode: learn the workflow from the inside, build the narrow end-to-end proof, measure against a written story (KPIs, baselines, instrumentation agreed before deployment), hand over something the operator's team can run.

## Evidence
- Dropbox → Google Drive migration worker: 6,000+ files moved with md5+size verification per file, idempotent JSONL ledger resume, per-file root-cause quarantine; nothing deleted from source (`~/workspace/stranded-files-move/worker.sh`).
- Job-App Helix itself — the agent-built application pipeline with verification gates (this pack is the evidence: researched, tailored, forged end-to-end in one run).

## Verified
2026-10-19 (live runs today).

---

## Proof: Production agent estate — 1,395 repos, 989 tests, 62/62 checks green

## Claim
Built and operate a production-grade agent control plane across a 1,395-repository estate: typed state transitions, human approval gates on consequential actions, recoverable runs. 989-test suite, 62/62 verification checks green — no agent completion claim without independent provider readback.

## Evidence
- Estate census (`~/workspace/estate-map/ESTATE_MAP.md`); test suite from the estate's own test runs.
- Kit numbers carried from the Scale AI FDE variant (2026-10-08).

## Verified
2026-10-08 (resume-forge scale-fde-ps variant). Re-verify test count before citing in a new resume.
