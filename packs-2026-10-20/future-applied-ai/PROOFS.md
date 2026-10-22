# Career proofs — Future Applied AI Engineer (Remote, USA)

Selected from the GlacierEQ estate (verified 2026-10-08–20). Full convention: Claim / Evidence / Verified date.
Language tuned to the posting: evaluation harnesses and quality scoring (safety, effectiveness, personalization), full agent lifecycle (prototype → evals → staging/prod → trace monitoring → iterate), tool-calling LLM systems with structured output and parallel API orchestration, Pydantic-style validation, token budgets / retry logic / observability, strong Python.

---

## Proof: Evaluation harnesses and quality scoring

## Claim
Designs and operates evaluation harnesses and quality scoring for LLM agents: golden datasets, behavioral assertions, and LLM-as-a-judge scoring with written rubrics covering safety, effectiveness, and task quality — with CI regression gates that block a regression from shipping. The resume-forge itself fails closed on unapproved claims (HonestyError) — the eval gate decides, not the generator.

## Evidence
- Eval/verification patterns in `~/workspace/job_app_helix/tests/`; resume-forge honesty gate (this pack's forge run, 2026-10-20).
- Judge criteria with written rubrics in estate verification loops (`~/workspace/job-app-helix/`); 989-test suite, 62/62 verification checks green.

## Verified
2026-10-08–20 (estate verification window); this pack's forge run 2026-10-20.

---

## Proof: Full agent lifecycle ownership

## Claim
Owns the full loop: prototype a new agent capability, validate it with evals, deploy to staging and production, monitor traces, and iterate on production evidence. Prompt and configuration changes are validated by eval harnesses before they touch production.

## Evidence
- Job-App Helix engine (`~/workspace/job-app-helix/src/job_app_helix/`) — per-run verification receipts; estate deployment patterns with GitHub Actions CI/CD.

## Verified
2026-10-08–20 (estate window).

---

## Proof: Tool-calling LLM systems with structured output

## Claim
Builds and ships tool-calling LLM systems with structured outputs, parallel API orchestration, typed schema validation on every tool contract (JSON Schema / Pydantic-style), bounded retries, token budgets, and per-call observability. Strict validation on tool arguments and responses; deterministic tool behavior where possible.

## Evidence
- Hand-rolled multi-agent DAG scheduler (62/62 deterministic verification checks green); typed handoff contracts across agent loops in the estate.
- 65 MCP connectors — the tools layer agents consume, with evidence boundaries and audit receipts.

## Verified
2026-10-08–20; 62/62 and 65 from kit lineage (Scale AI FDE variant, 2026-10-08).

---

## Proof: Trace intelligence and run reconstructability

## Claim
Full run traces so any execution can be reconstructed end to end: per-task latency and token-cost instrumentation on every run, decision audit logs, and trace analysis showing the slowest calls, redundant tool usage, and expensive prompt segments — findings turned into configuration improvements. Model selection per task complexity.

## Evidence
- Per-task latency instrumentation and decision audit logs across estate agent runs; recoverable-run patterns across `~/workspace/`.

## Verified
2026-10-08–20 (estate window).

---

## Proof: Design for failure (fail-closed recovery)

## Claim
Designs agent systems for failure: instruments the failure modes found in production — stuck loops, bad retrievals, tool misuse, context blowouts — and builds the catchers: replay loops, fail-closed gates, behavioral assertions, and recovery restricted to evidence declared before reassessment.

## Evidence
- Fail-closed GO/NO-GO decisions in the Job-App Helix campaign engine; fail-closed governance patterns in `src/job_app_helix/estate_compiler.py`.

## Verified
2026-10-08–20 (estate window).

---

## Honesty boundaries (JD-specific)
- Trace intelligence claimed, NOT Langfuse by name — no production Langfuse claim anywhere in the pack.
- Agent frameworks: hand-rolled multi-agent loops; LangChain/LangGraph NOT claimed by name (JD says "or similar").
- No Terraform/CDK, no AWS-native production ops claims, no Go/GCP/GraphQL/K8s, no data-science/statistics depth.
- No Future-internal production claims, no customer logos. Three years stated as "Three years" — never rounded up.
- Portfolio repos are independent work (boundary note on the resume).
