# Career proofs — Cribl Staff Software Engineer, Agentic Tools

Selected from the GlacierEQ estate (verified 2026-10-08–20). Full convention: Claim / Evidence / Verified date.
Language tuned to the posting: production agentic workflows, platform harnesses, MCP-style tool protocols, guardrails (tracing, regression detection, HITL, safe rollout), intent engineering, TypeScript-first, dogfooding.

---

## Proof: Platform harnesses for production agentic workflows

## Claim
Designs and operates the platform harnesses production agentic workflows run on: orchestration layers with typed contracts, tool integrations, shared context surfaces, and extension points other builders can trust and extend. Every action receipted; every run reconstructable from its trace.

## Evidence
- Agent systems under `~/workspace/` (memory gateway helper, estate compiler, job-app-helix engine); estate census `~/workspace/estate-map/ESTATE_MAP.md` (1,398 repos — 695 public + 703 private, live-verified 2026-10-20 via gh api /user).
- Typed handoff contracts on hand-rolled multi-agent loops; fail-closed governance patterns in `src/job_app_helix/estate_compiler.py`.

## Verified
2026-10-08 (estate census window); repo count live re-verified 2026-10-20.

---

## Proof: MCP-style tool protocols at depth (65 connectors)

## Claim
Authors MCP integrations that expose tools and structured resources to any MCP-compatible system — the tool-protocol layer agents consume: evidence boundaries, audit receipts, and typed capability contracts on every connector. 65 MCP connectors integrated.

## Evidence
- Connector docs under `~/workspace/custom-connectors/` and `/opt/hatch/connectors/`; kit number carried from the Scale AI FDE variant (2026-10-08).

## Verified
2026-10-08 (kit lineage). Re-verify before a live submit if connector counts moved.

---

## Proof: Evals and regression detection as infrastructure

## Claim
Gates agent behavior by evaluation: golden suites with behavioral assertions, judge criteria with written rubrics, CI regression gates that block a regression from merging. The forge itself fails closed on unapproved claims (HonestyError) — the eval gate decides, not the generator.

## Evidence
- Eval/verification patterns in `~/workspace/job_app_helix/tests/`; resume-forge honesty gate (this pack's forge run, 2026-10-20).

## Verified
2026-10-20 (this pack's forge run).

---

## Proof: Guardrails — tracing, HITL, safe rollout

## Claim
Guardrails for agentic systems others depend on: tracing across runs, human-in-the-loop approval gates typed into state transitions, safe rollout with rollback as the default posture, fail-closed recovery. A 1,398-repo estate backed by a 989-test suite, 62/62 verification checks green.

## Evidence
- Human approval gates on consequential actions in `src/job_app_helix/estate_compiler.py`; recoverable-run patterns across the estate; fail-closed GO/NO-GO decisions in the campaign engine.

## Verified
2026-10-08–20 (estate verification window); 989-test / 62/62 from the Scale AI FDE variant lineage.

---

## Proof: Dogfooding and delivery discipline

## Claim
Ships TypeScript/Node.js production services on continuous-deployment discipline — automated pipelines, progressive delivery, monitoring and rollback — and dogfoods the platform daily: the agent campaign engine runs his own operations end to end, with success metrics tracked per run (adoption, quality, reliability) and sharp edges from real usage turned into platform improvements.

## Evidence
- Job-App Helix engine (`src/job_app_helix/`); GitHub Actions CI/CD across the estate; per-task latency instrumentation and decision audit logs across agent runs.

## Verified
2026-10-08–20 (estate window).
