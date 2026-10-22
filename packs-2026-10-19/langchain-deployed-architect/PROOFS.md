# Career proofs — LangChain Deployed Architect, Professional Services (Remote)

Selected from the GlacierEQ estate (verified 2026-08-30 – 2026-10-19). Full convention: Claim / Evidence / Verified date.
Language tuned to LangChain's posting: multi-agent system architecture, comprehensive evaluation frameworks, production agent applications (LangChain/LangGraph patterns), prompt optimization with A/B testing, state management, tool integration, enterprise customer engagement.

HONESTY FRAMING (carried into every claim below): his production agent systems are hand-rolled, not framework-built. Where LangGraph appears, it is stated exactly as verified — design concepts adopted, portfolio repos touching the ecosystem — never a production LangGraph deployment at customer scale.

---

## Proof: Designs multi-agent system architectures that are allowed to ship

## Claim
Designs multi-agent systems with deterministic coordination and governed tool access: assignment-bound task proposals, fail-closed handoffs where only fully-assigned tasks may emit a tool call, plan-hash binding, and a typed safety-review boundary between proposal and execution.

## Evidence
- GlacierEQ/anthropic-agent-coordinator: deterministic dependency-aware coordinator; assignment-bound tool-proposal handoff — deferred, unknown, duplicate, oversized, or malformed proposals fail closed; proposal batches bind to exact plan SHA-256; payloads shaped for independent safety-monitor review without executing tools (`~/workspace/job-app-helix/solidify_records/anthropic-agent-coordinator.json`).
- Behavioral suite: **62/62** candidate proof receipt, junit_sha256-bound (`coordinator_candidate_receipt.json`, verified 2026-08-30).

## Verified
2026-08-30 (solidify record, live source head 21d118e) – 2026-10-19 (estate window).

---

## Proof: Builds the evaluation framework that decides whether an agent is production-ready

## Claim
Builds comprehensive evaluation frameworks: assessment composition into fail-closed GO/NO-GO decisions over immutable evidence models, stable finding codes, and recovery restricted to pre-declared contingency evidence — the engine never silently tunes values until they pass. Includes rubric-based scoring of the evaluators themselves.

## Evidence
- Job-App Helix campaign engine: attributable GO/NO-GO with immutable evidence models; fail-closed decisions; no completion claim without independent readback (`~/workspace/job-app-helix/src/job_app_helix/`).
- Genius engine scoring (`src/job_app_helix/genius_engine.py`): honesty/novelty scoring judges problem/cause/mechanism only, explicitly excluding self-scored implementation boilerplate — evaluation of the evaluator.
- Forge honesty gate: the document pipeline refuses to emit any unapproved number (HonestyError) — the eval gate decides, not the generator.

## Verified
2026-10-08–19 (estate verification window).

---

## Proof: Works the LangChain/LangGraph patterns, in production code

## Claim
Works the agent-framework patterns the LangChain posting names — agent logic over LLM frameworks, state management with short-term and long-term memory, checkpoint/recovery semantics — in hand-rolled production code, with portfolio systems that reach the LangChain/LangGraph ecosystem directly.

## Evidence
- Portfolio repo `GlacierEQ/ai-pdf-chatbot-langchain`: "AI PDF chatbot agent built with LangChain & LangGraph" — exists in his GitHub estate, pushed 2026-09-13 (repo description verified via gh API 2026-10-19; dependency-level depth not read back — stated as such).
- Portfolio repo `Z-BACKUP-apex-memory-agent`: "APEX persistent memory agent — LangGraph + LangMem + Supabase pgvector with multi-tier context" (estate registry description).
- Control-plane upstream adoption matrix (`~/workspace/estate-deep/apex-control-plane/docs/operator-administration/UPSTREAM_ADOPTION_MATRIX.md`): "selected LangGraph checkpoint concepts" adopted as design discipline — wrap/adapt upstream, do not fork distributed internals.

## Verified
2026-10-19 (gh API + estate registry readback; depth-limited, flagged honestly).

---

## Proof: State management, memory patterns, and recoverable runs

## Claim
Implements explicit state management: typed state transitions, bounded tool actions, approval gates, and recoverable runs — the control-plane discipline the Deployed Architect role needs when guiding customers from PoV to production operations.

## Evidence
- APEX control plane (`~/workspace/estate-deep/apex-control-plane/`): continuity as an operator surface built on adapted LangGraph checkpoint concepts; typed transitions and recoverable-run discipline across the estate.
- Control-plane test surface: **988** test functions (verified 2026-10-13, +91 in 6 days); helix test surface **989** (verified 2026-10-13).

## Verified
2026-10-13 (estate census) – 2026-10-19.

---

## Proof: 65 MCP connectors — tool integration, API design, error handling at the platform boundary

## Claim
Builds the governed tool-integration layer the role describes: MCP servers and connectors exposing tools and structured resources with claim tracking, evidence boundaries, idempotent automation, and error handling — the boundary between customer environments and the platform.

## Evidence
- Connector docs under `~/workspace/custom-connectors/` and `/opt/hatch/connectors/`; claim-tracking and idempotent automation patterns across the estate. 65 MCP connectors integrated (his approved number).

## Verified
2026-10-08–19 (estate census window).

---

## Proof: Customer-embedded delivery — assessment, recommendations, adoption

## Claim
Practices the consultative, customer-facing pattern: technical maturity assessments, operator-embedded scoping, recommendations non-technical stakeholders act on the same day, and end-to-end ownership from PoV-shaped narrow proof to hardened production load.

## Evidence
- Standing delivery doctrine across the estate: scope with the operator, build the narrow end-to-end proof, harden the components that carry real load — documented in prior FDE packs (Scale FDE Public Sector, ClickUp, Cresta) built 2026-10-19.
- Served as the technical point of contact for operators and stakeholders across the GlacierEQ portfolio.

## Verified
2026-10-19 (prior pack evidence, estate window).

---

## Numbers traceability
- **62/62** — coordinator behavioral suite (candidate receipt, junit_sha256-bound, verified 2026-08-30; re-verification flagged before any submit)
- **989** — job-app-helix test functions (fresh-clone verification 2026-10-13)
- **988** — apex-control-plane test functions (verified 2026-10-13)
- **65** — MCP connectors integrated (his approved number; re-verification pending)
- **1,395** — estate repos (GraphQL census 2026-10-13; estate map shows 1,396 in raw census — re-verify before submit)
- **20+** — production repositories maintained (kit allowlist)
