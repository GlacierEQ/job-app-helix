# Career proofs — BMC Software Principal AI Engineer, req 47640 (primary verified 2026-10-20)

Keyed to the JD's exact keywords. Convention: Claim / Evidence / Verified date. All systems are independently developed; no claim of enterprise-customer deployment track record, no BMC-internal production work, no certification claims. Agentic frameworks hand-rolled (deterministic DAG scheduler, **62/62** green) — LangGraph/LangChain/CrewAI not claimed.

---

## Proof: Orchestrate multi-agent systems integrating tools, APIs, enterprise apps

## Claim
"Develop multi-agent systems and orchestrate interactions between agents, tools, APIs, and enterprise applications." His practice: multi-agent systems with autonomous and semi-autonomous agents (plan, reason, decide, execute), orchestrated through typed handoff contracts, integrating **65** MCP tool/API connectors with evidence boundaries and audit receipts on every interaction.

## Evidence
- `anthropic-agent-coordinator` — deterministic DAG scheduler, **62/62** tests green; review-gated tool calls.
- `~/workspace/custom-skills/` MCP constellation — **65** integrations (kit allowlist number; lineage from his approved count).

## Verified
2026-10-08 (kit lineage); 2026-10-20 (pack provenance).

---

## Proof: Build and run agent evaluations — eval sets, behavior tests, iteration

## Claim
"Build and run agent evaluations — define eval sets, test behaviour, iterate on prompts, tools, and workflows." His eval discipline: eval sets with behavioral assertions, LLM-as-judge scoring with written rubrics, replay loops, explicit release thresholds — CI regression gates that block a regression from merging; failed evals diagnosed from evidence. The forge itself fails closed on unapproved claims.

## Evidence
- `~/workspace/job-app-helix/hire_package/resume-forge/cover.py` — `honesty_gate()`; README: "The engine **fails closed**."
- `~/workspace/custom-skills/local-mistral/SKILL.md` — LLM-as-judge path verified live 2026-10-06.
- Job-App Helix campaign engine — fail-closed **GO / NO-GO** decisions; no agent completion claim without independent provider readback.

## Verified
2026-10-06 (judge); 2026-10-20 (pack provenance).

---

## Proof: Observability, monitoring, guardrails, governance for production AI

## Claim
"Implement observability, monitoring, guardrails, and governance mechanisms for production AI systems." His governance surface: trace intelligence logging prompts, tool calls, and decisions on every run; per-task latency instrumentation; decision audit logs; human-in-the-loop approval gates typed into state transitions; policy controls; fail-closed recovery; safe rollout with rollback as default — production AI held to enterprise standards across a **1,398**-repo estate (live-verified 2026-10-20 via GraphQL totalCount).

## Evidence
- apex-control-plane — typed state transitions, bounded tool actions, approval gates, recoverable runs; circuit breakers, dead-letter capture, fail-closed startup, SHA-256 transport envelopes.
- Agent campaign engine — per-run success metrics, full reconstructability from traces.

## Verified
2026-10-13 (test counts); 2026-10-20 (estate count live re-verified).

---

## Proof: Enterprise-grade agentic AI with modern LLMs + RAG

## Claim
"Design, develop, and maintain enterprise-grade agentic AI applications using modern LLMs and AI frameworks" + "Build and deploy RAG solutions using vector databases and enterprise knowledge sources." Multi-provider LLM usage (Mistral verified live; equivalent-use experience), RAG with federated retrieval across Mem0, Supermemory, Supabase pgvector, Pinecone, Neo4j behind one MCP interface — content-hash dedup, provenance, structured outputs. Hand-rolled orchestration over framework claims.

## Evidence
- `unified-memory-mcp`, `mcp-iceberg-mansion` — federated retrieval behind MCP.
- `~/workspace/custom-skills/local-mistral/SKILL.md` — verified live 2026-10-06.

## Verified
2026-10-06 (Mistral); 2026-10-20 (pack provenance).

---

## Proof: Production packaging, deployment, and stack-wide diagnostics

## Claim
"Package and deploy solutions in production; apply strong diagnostics across the AI stack" + "Python; REST APIs, microservices, cloud, containers, CI/CD, and testing." TypeScript + Python production services: REST APIs, microservices, containers, Postgres/Supabase, GitHub Actions CI/CD, progressive delivery, monitoring and rollback — **20+ production repositories** maintained; failure-injection recovery (root-cause quarantine instead of silent retries); per-task latency instrumentation.

## Evidence
- `~/workspace/job-app-helix/hire_package/resume-forge/content/_candidate.yaml` — kit-number allowlist (20+ production repos, 989-test, 988-test).
- `~/workspace/stranded-files-move/worker.sh` — ledgered quarantining worker (observed in operation 2026-10-20).

## Verified
2026-10-13 (test counts); 2026-10-20 (pack provenance).

---

## Proof: Architecture, investment priorities, and measurable outcomes

## Claim
"Set applied AI architecture and investment priorities across products" + "make consequential tradeoffs among models, platforms, build-vs-buy, and risk controls" + "drive org-wide adoption of AI capabilities with measurable outcomes and managed risk." As founder/architect he sets the architecture and investment priorities across the estate — model/platform/build-vs-buy tradeoffs driven by telemetry, per-run success metrics tracked (adoption, quality, reliability), sharp edges from real daily usage turned into platform improvements. Boundary: his operation is his own shop — org/BU adoption evidence is bounded to that scale.

## Evidence
- Job-App Helix — telemetry-driven campaign engine; success metrics tracked per run.
- Per-task latency instrumentation and decision audit logs across agent runs.

## Verified
2026-10-20 (pack provenance).
