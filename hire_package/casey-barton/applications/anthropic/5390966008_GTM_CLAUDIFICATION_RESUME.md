# Casey Del Carpio Barton

**Applied AI Systems Architect · Forward-Deployed AI Engineer · Agent Systems Engineer**  
Honolulu, Hawaii · Portfolio: https://casey-barton-glaciereq.vercel.app/roles/anthropic-gtm-ai-engineering/ · GitHub: https://github.com/GlacierEQ

**Target:** Anthropic — Staff Software Engineer, GTM AI Engineering (Claudification) — Job 5390966008

## Summary

Applied AI systems architect and technical founder building the operating layer between frontier models and dependable organizational work. GlacierEQ already contains the system class this role describes: GTM workflow skills, agent orchestration, Model Context Protocol and governed tool access, explicit human approval boundaries, evaluation/regression machinery, provider receipts and readback, deterministic state, failure recovery, and reusable shared capability contracts.

My strongest work is not a collection of isolated demos. It is an interconnected estate in which workflows recover context, agents plan bounded work, tools operate under explicit authority, external actions remain human-controlled where required, execution is receipted and read back, behavior is evaluated, and successful patterns become reusable skills or platform primitives.

## Claudification-Relevant Systems

### GTM workflow and seller-system capability

- Built and composed a reusable Sales capability layer spanning account signals and prioritization, lead/company research and enrichment, deal strategy, forecast and pipeline-risk review, meeting preparation, transcript analysis, rep feedback, competitive briefs, customer evidence, email sequences, and CRM-specific workflows.
- Encoded Salesforce and HubSpot operating contracts that keep authoritative CRM facts separate from supporting evidence, preserve read-versus-write boundaries, and require explicit approval before supported external writes.
- Designed GTM workflows around real source categories — CRM, email, calendar, meeting transcripts, internal messaging, knowledge/files, and sales intelligence — with explicit source authority and evidence-gap semantics rather than invented context.

### Agent orchestration and human control

- Built **Anthropic Agent Coordinator**, a deterministic dependency-aware task scheduler with global budgets, aggregate role capacity, cycle validation, structured deferrals, and assignment-bound tool proposals. Historical exact-revision evidence records **62/62 tests passed**; current-head claims remain separately bounded.
- Built **Anthropic Safety Monitor**, a deterministic policy boundary for proposed agent tool calls that emits **ALLOW / CONFIRM / DENY** decisions, stable rule identifiers, reasons, severity, and human-confirmation requirements without executing the proposed action. Canonical promotion records **153 test executions** across Python 3.11, 3.12, and 3.13 with zero reported failures, errors, or skips.
- Treat approval, escalation, rejection, handoff, and non-completion as explicit operating states rather than implicit prompt behavior.

### MCP, tools, and external-action infrastructure

- Built **GlacierEQ MCP Stack** with registration separated from execution authority, explicit allow-list dispatch, mutation gates, fail-closed behavior, and credential-gated stdio MCP packages for GitHub, Asana, Confluence, Supabase, and Neo4j.
- Built APEX control-plane mechanisms for context recovery, retries, circuit breakers, dead-letter capture, immutable receipts, provider-readback validation, idempotency, and evidence-bound execution-state promotion.
- Implemented outbound transaction semantics that bind a context packet to preflight, idempotency, approved/executing states, provider references, receipts, and readback rather than treating model output as a completed external action.

### Evals, observability, and shared platform patterns

- Built agent-evaluation capabilities around behavioral contracts, adversarial/regression testing, repeated-run reliability analysis, production-trace replay guidance, and multi-dimensional quality/latency/cost/user-impact measurement.
- Built release and evidence pipelines that distinguish inventory, implementation, test, integration, deployment, and observed-operation evidence instead of allowing lower-level proof to inherit stronger production claims.
- Built reusable Mega-Skills and pipeline contracts so successful architecture can be consumed by other workers and workflows instead of remaining trapped in one prompt, repo, or one-off implementation.
- Operate an evidence-bound job/application control plane where requirements map to source implementations, verification, receipts, claim ceilings, and public recruiter projections.

## Selected Proof

**Anthropic Safety Monitor — Python**
- Human-control boundary for proposed tool actions: ALLOW / CONFIRM / DENY.
- Canonical TEST evidence: 51 tests × Python 3.11/3.12/3.13 = **153 executions**, zero reported failures/errors/skips.
- Tamper-evident review/transcript receipts and explicit non-authorization semantics.

**Anthropic Agent Coordinator — Python**
- Typed DAG scheduling with dependency waves, global token budgets, per-role capacity, stable priority, cycle refusal, and explicit deferrals.
- Assignment-bound tool proposal batches tied to the exact plan hash.
- Historical exact-revision receipt: **62/62 passed**.

**GlacierEQ MCP Stack — Python / TypeScript**
- Policy-gated local tool routing plus credential-gated stdio MCP packages.
- Registration does not imply execution authority; mutation is separately gated; dispatch fails closed.
- Integration packages for GitHub, Asana, Confluence, Supabase, and Neo4j.

**APEX Control Plane — Python / SQL**
- Context recovery, deterministic execution-state semantics, retries, circuit breakers, dead letters, receipts, provider readback, and continuity.
- SQL-backed outbound preparation and state transitions with preflight, idempotency, context binding, and receipt generation.

**Mega-Skills / Mega-Sales — Python / workflow contracts**
- Reusable GTM and engineering capability estate covering Sales, CRM, enrichment, deal strategy, pipeline/forecast review, meetings, conversation analysis, email, evals, analytics, and orchestration.
- Shared conventions for source selection, authority boundaries, reviewed writes, failure visibility, and handoffs.

## Experience

### GlacierEQ — Founder / Applied AI Systems Architect
**January 2025–Present · Honolulu, Hawaii**

- Architect and implement agent, memory/context, MCP/tool, browser, data, evaluation, deployment, provenance, and control-plane systems across a federated engineering estate.
- Turn ambiguous operator goals into explicit workflows, typed interfaces, bounded authority, executable components, acceptance criteria, tests, receipts, and resumable continuation state.
- Build cross-system automation that separates proposal from authorization and attempted action from provider-verified completion.
- Convert repeated successful implementations into reusable capabilities, skills, contracts, and platform primitives.
- Maintain source-backed claim ceilings so recruiter and public surfaces do not outrun repository-native evidence.

### Diamond Head Home Inspections — Certified Home Inspector
**2020–2024 · Honolulu, Hawaii**

- Diagnosed interconnected structural, electrical, plumbing, roofing, safety, and environmental systems under field constraints and incomplete evidence.
- Converted complex observations into prioritized findings and clear client communication.
- Developed the whole-system inspection discipline now applied to software and AI operations: recover actual state, trace dependencies, identify failure paths, preserve evidence, and communicate uncertainty precisely.

### HI-Class Home Services / HI CLASS MAINTENANCE OAHU LLC — Owner-Operator
**2017–Present · Honolulu, Hawaii**

- Operate an independent service business across customer intake, diagnosis, scheduling, field execution, vendor/material coordination, communication, and delivery.
- Bring direct operator experience with real workflows, handoffs, customer expectations, and outcome accountability into applied-AI system design.

## Technical Capabilities

**Languages / data:** Python, TypeScript/JavaScript, SQL, Bash  
**Applications / APIs:** Node.js, FastAPI, React/Next.js, REST, JSON-RPC, JSON Schema, Protocol Buffers  
**Agent systems:** orchestration, context engineering, MCP, tool use, approval gates, multi-agent coordination, skills, retrieval/memory, transcript analysis  
**Reliability / trust:** deterministic state, idempotency, retries, circuit breakers, dead letters, immutable receipts, provenance, hashing, least privilege, replay containment, fail-closed execution  
**Delivery:** discovery under ambiguity, system architecture, implementation, integration, evals, verification, CI/CD, technical communication, operator handoff, reusable platform extraction

## Education

**University of Hawaii at Manoa** — B.S., Marine Biology, 2016  
**AWS Cloud Institute** — Cloud Application Developer curriculum, 2025–2026

## Evidence Boundary

Independent GlacierEQ work. No Anthropic employment, affiliation, endorsement, proprietary access, internal GTM deployment, unsupported revenue attribution, or production Claude Agent SDK deployment is claimed.
