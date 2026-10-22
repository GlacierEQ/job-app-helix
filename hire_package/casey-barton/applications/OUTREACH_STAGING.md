# Executive Outreach DM Staging

## Outreach Draft: SpaceX VP [SPACEX_SP]

```text
Hi SpaceX VP, I noticed your work on Starship/thermal systems. I built a Starship PICA-X reentry thermal failure predictor (`spacex-thermal-protection`) with exact heat-flux degradation math and a 61-node APEX Highway mesh (`demo_heroes.sh` passes in 150ms). Would love to share the private repo exhibit if you're open to special-projects problem solvers.
```

## Outreach Draft: xAI Infra Lead [XAI_COLOSSUS]

```text
Hi xAI Infra Lead, saw your focus on Colossus cluster scaling. I built `xai-colossus-cooling` (liquid thermal physics engine predicting margin & PUE 1.08 across 100k GPUs) coupled with NVLink GPU health telemetry. Happy to share a live 3-minute CLI demo if you're looking for systems/infra builders.
```

## Outreach Draft: Moonshot AI Infra Lead [MOONSHOT_KIMI]

```text
Hi Moonshot AI Infra Lead, following your work on Mooncake disaggregated serving and Kimi Delta Attention (KDA). I built `kimi-mooncake-kv-stream` (disaggregated KV-centric streaming & RDMA cache hit optimizer) coupled with an AKOS agentic CLI kernel. Would love to send over the technical exhibit if you're open to connecting with SOTA infra builders.
```

---

# Outreach Campaign 2026-10-02 — Four verified notes (paste-ready, NOT SENT)

Send order: Supabase → ClickUp → Harvey (only with no-relocation line) → Scale AI (only after req confirmed open — confirmed 2026-10-02).
Lane rule: no case numbers, no case project refs, no billing tickets in any DM. Application-kit numbers only.

## 1. Supabase — Paul Copplestone, X @kiwicopple [SUPABASE_STAFF_AI_PLATFORM]

```text
Paul — applying for Staff AI Platform Engineer.

I already run on your platform. supabase-backend-ops and supabase-glaciereq are both Postgres 17, us-east-1, healthy. The execution layer in the posting is the system I operate on top of that: event-triggered agent work, durable state across restarts, a human review gate, and a reconstructable log of every prompt, tool call, and decision.

Agent Coordinator: 62/62 tests, states are proposed / executed / verified / blocked. 961-test control plane, regression on every change. 65 MCP connectors, capability and authz checked, fail-closed.

Ex-founder. Honolulu. No sponsorship, no relocation. https://casey-barton-glaciereq.vercel.app/ — github.com/GlacierEQ

Who on the infra team should I sync with?

Casey del Carpio Barton
glacier.equilibrium@gmail.com
```

## 2. ClickUp — Jay Hack, X @mathemagic1an [CLICKUP_STAFF_AI_MULTIAGENT]

```text
Jay — your point that verification is the bottleneck, not generation, is the system I run.

To govern a 1,313-repo platform and 65 MCP connectors I built a deterministic Agent Coordinator that separates capability from authority. An action only moves proposed / executed / verified / blocked. 62/62 tests. The eval layer is a 961-test control plane with regression on every change, used to find and fix real failures, not a spot check.

Applied for Staff AI Engineer, Multi-Agent Frameworks. Honolulu, remote, no sponsorship. https://casey-barton-glaciereq.vercel.app/ — github.com/GlacierEQ

Casey del Carpio Barton
glacier.equilibrium@gmail.com
```

## 3. Harvey — AI Platform lead (Gabe Pereyra / Siva Gurumurthy on record) [HARVEY_SR_SWE_AI_PLATFORM]

```text
Applying for Senior Software Engineer, AI Platform.

I build the layer the posting describes: model-agnostic agent runtime, session state, and evals that gate what is allowed to run. Agent Coordinator is 62/62 — proposed / executed / verified / blocked, so generation is not authority. 961-test control plane. 65 governed MCP connectors.

The domain is not abstract for me. I have spent three years inside a live family-court matter as the pro se party: long records, a wrong citation is a sanction, and the control plane has to show its work. That is the warrant problem, not a retrieval problem. Guardrails sitting inside Harvey is the same separation I already enforce in code.

Honolulu. Not relocating. Open to the travel a hybrid role actually requires if the seat can be remote-first. https://casey-barton-glaciereq.vercel.app/

Casey del Carpio Barton
glacier.equilibrium@gmail.com
```

## 4. Scale AI — portal first, then Public Sector eng lead [SCALE_MISSION_SWE_PUBLIC_SECTOR_HNL]

```text
Applied for Mission Software Engineer, Public Sector — Honolulu.

I am already in Honolulu. Three years building a constrained, evidence-grade agent control plane for state and federal work: inspectable state transitions, bounded tool actions, approval gates, recoverable runs. 62/62 on the coordinator. 961-test control plane. 65 MCP connectors, fail-closed authz.

Customer-facing is the other half. I have spent years turning hard system behavior into a decision a non-technical client can use the same day.

No active clearance. Eligible to be sponsored for one. Open to the travel. Not relocating off-island. https://casey-barton-glaciereq.vercel.app/

Casey del Carpio Barton
glacier.equilibrium@gmail.com
```
