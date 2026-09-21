# Anthropic 5390966008 — Claudification Live Demo Runbook

**Candidate:** Casey Del Carpio Barton / GlacierEQ  
**Role:** Staff Software Engineer, GTM AI Engineering (Claudification)  
**Demo objective:** prove one complete GTM agent motion through the existing GlacierEQ architecture without turning the interview into a repository tour.

## First interaction

Run:

`Motions → Outbound → Anthropic · Claudification → Start motion`

Do not begin in GitHub. Do not begin with an architecture slide. Do not begin with repository count.

The interviewer should see a GTM workflow move through the operating system.

## The invariant to make visible

**Model output does not silently become external action.**

The system may research, plan, draft, propose tools, and evaluate autonomously. A materially external action crosses an explicit authority boundary.

## Expected interaction

```text
1. Start outbound motion
2. Recover role/account/workflow context
3. Build the agent/tool plan
4. Execute bounded research/drafting work
5. Emit proposed outbound action
6. Hit SEND GATE
7. Show approve / escalate / reject
8. Approve the bounded action
9. Show provider receipt / readback
10. Open eval / telemetry / business-measurement surface
11. Show the reusable Estate capabilities behind the motion
```

## What to narrate at each stage

### 1. Motion selection

**Show:** Outbound motion selected for `Anthropic · Claudification`.

**Say:** The unit of work is a GTM motion, not a free-form chat. The motion has a goal, context, tool access, authority boundary, expected output, and evaluation contract.

### 2. Context

**Show:** the role/evidence context recovered for the motion.

**Say:** The agent should not invent CRM or account truth. GlacierEQ skills explicitly route to authoritative source categories — CRM, email, transcripts, calendar, files, intelligence — and preserve gaps when a lane is unavailable.

### 3. Agent plan

**Show:** planned work / dependency order.

**Say:** The coordinator does not call deferred work complete. Dependency and resource failure remain explicit states. Tool proposals are bound to assigned work rather than emitted from an ungrounded plan.

### 4. MCP / tool proposal

**Show:** the proposed tool or connector action.

**Say:** Registration is not execution authority. The MCP/tool layer separates capability availability from permission to execute, and mutation can be independently gated.

### 5. Human-control boundary

**Show:** SEND GATE and the available **approve / escalate / reject** paths.

**Say:** This is not a decorative confirmation modal. Human authority is a first-class system state. The Safety Monitor's underlying policy model emits ALLOW / CONFIRM / DENY without executing the proposed action.

### 6. Approved bounded action

**Show:** action begins only after approval.

**Say:** The action is preflighted and idempotent. The system separates proposed, approved, executing, executed, and verified states instead of collapsing them into “done.”

### 7. Receipt / readback

**Show:** provider result / receipt / returned state.

**Say:** An API call returning is not enough. Promotion depends on provider-native state or a durable execution receipt at the correct evidence layer.

### 8. Evals

**Show:** behavior bench / ship-hold gate / regression or telemetry surface.

**Say:** Evaluation is not only offline benchmark scoring. The estate includes behavioral contracts, adversarial/regression patterns, repeated-run reliability concepts, and production-trace replay guidance. For this role, the same evaluation layer should connect actions to seller outcomes and business metrics.

### 9. Business measurement

**Show:** pipeline / ROI surface where available.

**Say:** The architecture is ready to bind agent actions to pipeline and revenue, but I do not invent those outcomes. Real ROI claims start only when the desk is operating against authoritative revenue-system data.

### 10. Estate

Only now open the underlying Estate.

**Show these proof surfaces first:**
1. Mega-Sales / GTM skill family
2. Anthropic Safety Monitor
3. Anthropic Agent Coordinator
4. GlacierEQ MCP Stack
5. APEX Control Plane
6. Agent Evaluation / Mega Pipeline
7. Job-App Helix

**Say:** Claudification is composition, not duplication. The GTM desk reuses existing capability layers that were built to be independently useful and interoperable.

## Proof details worth memorizing

### Safety Monitor

- Deterministic proposed-tool review.
- ALLOW / CONFIRM / DENY.
- Canonical promotion: `c7ab52e0e70a5cd449f9335f90030059d254325f`.
- 51 tests on each of Python 3.11, 3.12, 3.13.
- 153 total executions, zero reported failures/errors/skips.
- Confirmation is not authorization; it does not execute tools.

### Agent Coordinator

- Dependency-aware deterministic scheduling.
- Shared global budget + aggregate role capacity.
- Cycle and malformed dependency refusal.
- Structured deferrals; deferred prerequisites do not unlock downstream work.
- Assignment-bound, plan-hashed tool proposals.
- Historical exact-revision receipt: 62/62 tests at `87438f57bdfd2cb380730cf51140611963d7c95b`.
- Do not transfer that test proof to an unverified later head.

### MCP Stack

- Local allow-list router is the verified plane.
- Registration and execution authority are separate.
- Mutation has its own gate.
- Fail-closed dispatch.
- Credential-gated packages exist for GitHub, Asana, Confluence, Supabase, Neo4j.
- Do not call it a deployed estate-wide multi-tenant MCP cloud.

### APEX

- Context/continuity recovery.
- Explicit evidence states.
- Retries, circuit breakers, dead-letter capture.
- Idempotent outbound preparation and state transition.
- Provider receipt/readback.
- Mission-outcome verification rather than assistant-activity-as-progress.

## Likely interviewer challenges

### “You have a lot of components. What did you actually build?”

Answer with the motion first. Then identify the exact code-owning systems behind each transition. Avoid saying “the whole estate” when one repository owns the mechanism.

### “Have you run this against a real sales organization?”

Do not blur the line.

**Answer:** The GTM composition and integration contracts exist, and the desk is the role-specific composition I built on GlacierEQ. I have not operated Anthropic's seller/RevOps production environment and I do not claim production revenue attribution. That is exactly the frontier I want to take on in this role.

### “Where is the human actually in control?”

Return to the send gate and explicit action states. Demonstrate reject or escalate if time permits.

### “What does production eval mean to you?”

Explain the loop:

`seed scenario → behavior contract → repeated/regression execution → production traces → failure classification → repair → replay → ship/hold decision → outcome measurement`

Then distinguish behavior quality, reliability, latency/cost, and revenue/user impact.

### “Why is this a platform instead of a demo?”

Show shared skills, common action/evidence contracts, common authority model, reusable evaluation patterns, and multiple consumers. The platform claim is the reusable interfaces, not the number of repositories.

## Demo failure recovery

If the live UI path is unavailable during the interview:

1. State the failure exactly.
2. Open the source-backed system map.
3. Walk one motion using the owning repositories and contracts.
4. Show the Safety Monitor and Agent Coordinator receipts.
5. Show the APEX outbound transaction/state code.
6. Return to the role crosswalk.

Do not pretend an unavailable runtime is live.

## Stop condition

A successful demo leaves the interviewer with one simple model:

**Casey has already built the engineering substrate for governed GTM agents; Claudification is that substrate composed around a seller workflow, with human control, evals, receipts, and reusable platform primitives.**
