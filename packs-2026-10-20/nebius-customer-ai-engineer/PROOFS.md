# Career proofs — Nebius Senior Customer AI Engineer, Token Factory (Remote US)

Selected from the GlacierEQ estate (verified 2026-10-08–20). Full convention: Claim / Evidence / Verified date.
Language tuned to the posting: PoC→production transition ownership; technical success in production (latency, throughput, cost, reliability); trusted technical partner to customer engineering teams; risk/incident management; structured feedback to product/infrastructure.

---

## Proof: Own the production journey — PoC to production

## Claim
Owns the production journey: leads AI workloads from proof-of-concept to production — deployed, stable, scalable — and drives time-to-production and time-to-value with the teams that operate them.

## Evidence
- Job-App Helix campaign engine (`~/workspace/job-app-helix/src/job_app_helix/`) — scoped narrow proofs, gated on evidence before shipping; per-run verification receipts.
- Founder/operator delivery practice across the estate: prototype → harden → production path, with eval gates deciding what ships.

## Verified
2026-10-08–20; JD verified live 2026-10-20 (GH board `nebius`, req 5000064101, updated 2026-10-14).

---

## Proof: Technical success in production — measure everything

## Claim
Ensures technical success in production by measuring it: per-task latency and token-cost instrumentation on every run; trace intelligence naming the slowest calls, redundant tool use, and expensive segments; bottlenecks identified and resolved before they become incidents.

## Evidence
- Per-task latency/token-cost instrumentation across estate runs; trace intelligence over agent and retrieval pipelines; fail-closed GO/NO-GO decisions gating what ships.

## Verified
2026-10-08–20.

---

## Proof: Trusted technical partner to customer engineering teams

## Claim
Works directly with technical counterparts: understands architectures and use cases, provides guidance on best practices and optimization, and translates technical challenges into actionable solutions — clearly, under pressure.

## Evidence
- Founder/operator delivery: customer discovery → scoping → prototype → production path, communicated to non-trivial technical audiences; incident-resolution posture with documented resolution paths.

## Verified
2026-10-08–20. Customer-facing depth is founder/operator (three years), not enterprise accounts — stated honestly.

---

## Proof: Risk and incident management

## Claim
Manages risks and incidents like production work: fail-closed gates, behavioral assertions, recovery restricted to evidence declared before reassessment — calm communication and documented resolution paths when it matters.

## Evidence
- Fail-closed governance patterns in `src/job_app_helix/estate_compiler.py`; **989-test** suite, **62/62** verification checks green; failure-injection recovery as standing estate discipline.

## Verified
2026-10-08–20.

---

## Proof: Continuous improvement — structured field feedback

## Claim
Drives continuous improvement: structured feedback from field evidence to product iteration — identifies opportunities to optimize and expand usage, shapes better solutions from real needs.

## Evidence
- Trace and run evidence feeding prompt and configuration iteration across the estate; decision audit logs as the evidence base for product-layer changes.

## Verified
2026-10-08–20.

---

## Proof: Inference-pipeline integration, honestly bounded

## Claim
Integration-side experience with inference pipelines (fal.ai + Whisper pipeline, estate-verified) — client-side integration, eval-gated, not GPU-infrastructure operations. Eval/trace engineering is the transferable production muscle: measure latency, cost, quality; gate on evidence; recover by design.

## Evidence
- fal.ai + Whisper pipeline estate-verified 2026-09-25 / 2026-10-13; eval regression gates and trace intelligence across agent pipelines.

## Verified
2026-09-25, 2026-10-13 (estate verification); 2026-10-08–20 (pack proofs).

---

## Proof: Governed integration layer — 65 authored MCP connectors

## Claim
Authored **65** MCP connectors — governed API integrations with typed contracts, structured validation on every tool boundary, evidence boundaries, and audit receipts. The tool layer behind every production deployment the role would steward.

## Evidence
- **65** MCP connectors (his approved kit number); typed handoff contracts across agent loops in the estate.

## Verified
2026-10-08–20; kit number **65** is the standing approved figure.

---

## Honesty boundaries (JD-specific)
- **INFERENCE-FRAMEWORK STRETCH — flagged, not papered:** JD expects "practical knowledge of inference frameworks (e.g. vLLM, TensorRT, or similar)" and solid distributed/high-load systems understanding. The pack claims transferable eval/trace engineering + integration-side inference-pipeline experience ONLY — no vLLM/TensorRT production depth, no GPU-infra/neocloud ops, no Kubernetes depth. Flag for his judgment in REVIEW_REQUIRED.txt. Do not let the interviewer hear infra-side GPU ops.
- **SENIOR TITLE STRETCH — flagged:** JD is Senior; bridge is Founder / Applied AI Systems Architect with three years of ownership. Not papered into a tenure count.
- Customer-facing depth is founder/operator (three years), not enterprise accounts.
- "Three years" stated as "Three years" — never rounded up.
- No Nebius-internal claims; no neocloud production claims.
- Comp undisclosed — pack does not specify; salary default 220000 only if the form requires a number.
- Portfolio repos are independent work (boundary note on the resume).
