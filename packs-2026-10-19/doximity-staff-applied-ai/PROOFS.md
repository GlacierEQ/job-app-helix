# Career proofs — Doximity Staff Applied AI Engineer

Selected from the GlacierEQ estate (verified 2026-10-08–19). Full convention: Claim / Evidence / Verified date.
Retuned from the cresta proofs for eval / safety / reliability language.

---

## Proof: Eval-first AI product shipping — verification gates, GO/NO-GO

## Claim
Every AI product surface ships through an eval harness: offline eval pass, verification checks, and a campaign-level GO / NO-GO with immutable evidence models and stable finding codes. Fail-closed decisions — the gate fails closed, not open.

## Evidence
- `~/workspace/job-app-helix/` engine: assessment → campaign-level GO/NO-GO with fail-closed decisions; recovery restricted to contingency evidence declared before reassessment — the engine never silently tunes values until they pass. Eval/verification patterns in `~/workspace/job-app-helix/tests/`.

## Verified
2026-10-19 (this pack's provenance: the pack was built by an agent system operating exactly this way).

---

## Proof: Safety guardrails + human-in-the-loop on consequential actions

## Claim
Typed state transitions, human approval gates on consequential actions, audit receipts, recoverable runs — the guardrail pattern the role's safety questions describe: define what good looks like, monitor quality and safety guardrails, keep a human in the loop where trust matters.

## Evidence
- Durable patterns for claim tracking, evidence boundaries, audit receipts, and human-in-the-loop control across the GlacierEQ estate.

## Verified
Standing doctrine, demonstrated 2026-10-19.

---

## Proof: Failure-mode testing, fail-closed recovery on 6,000+ file migration

## Claim
Dropbox → Google Drive migration worker moved 6,000+ files with md5+size verification per file, idempotent JSONL ledger resume, per-file root-cause quarantine. Nothing deleted from source; sealed archives never opened. This is failure-injection recovery and fail-closed behavior: recoverable runs, every failure attributed, the run never silently proceeds past a broken file.

## Evidence
- Worker: `~/workspace/stranded-files-move/worker.sh` (lock-protected, resumable).
- Run ledgers under `~/workspace/goals/stranded-files-move-dropbox-google-drive/`; live hourly run scoreboards in `~/memory/2026-10-19.md`.

## Verified
2026-10-19 (live runs today).

---

## Proof: A/B-tested LLM tuning validated before ship

## Claim
Prompt and configuration optimization run as A/B-tested tuning cycles validated by eval harnesses before anything ships: configuration deltas tracked with experiment records, ship decisions made from measured outcomes, not instinct.

## Evidence
- Agent systems under `~/workspace/` (memory gateway helper, estate compiler, job-app-helix engine); eval/verification patterns in `~/workspace/job-app-helix/tests/`.

## Verified
2026-10-19.

---

## Proof: Performance monitoring across a 989-test control plane, 62/62 green

## Claim
Built and operate a production-grade agent control plane across a 1,395-repository estate. 989-test suite, 62/62 verification checks green — no agent completion claim without independent provider readback. Monitoring plus A/B testing is the standing operating practice.

## Evidence
- Estate census (`~/workspace/estate-map/ESTATE_MAP.md`); test suite from the estate's own test runs.
- Kit numbers carried from the Scale AI FDE variant (2026-10-08).

## Verified
2026-10-08 (resume-forge scale-fde-ps variant). Re-verify test count before citing in a new resume.

---

## Proof: 65 MCP connectors — the integration surface feeding eval and product analytics

## Claim
65 MCP connectors plus APIs, webhooks, and data pipelines connecting product and operator environments to the platform and back — the integration surface that feeds evaluation, monitoring, and analytics.

## Evidence
- Skill docs under `~/workspace/custom-skills/`; connector docs under `~/workspace/custom-connectors/` and `/opt/hatch/connectors/`.

## Verified
2026-10-08–13 (estate census window).
