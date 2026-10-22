# n8n Estate — Inventory for Job Applications

Gathered 2026-10-21 (Kai, at the Operator's direction). Method: enumerate-then-classify.
Every set below is labeled with its source and the date it was observed. Sets are NOT
blended — the estate changed across Oct 15–20 because it was being actively built.

---

## Set A — Workflow exports in hand (5 files, byte-verified)

Copies in `exports/`; SHA-256 in `SHA256SUMS.txt`. All five scanned 2026-10-21:
zero credential blocks, zero API keys, zero pinned data. Safe to attach to applications.

| # | Workflow | Instance ID | Active | Ver. | Nodes | What it actually does (from its own code) |
|---|----------|-------------|--------|------|-------|--------------------------------------------|
| A1 | P1 Accounts Payable Adversarial Laboratory | 7ba402D0rKyaWTAC | yes | 3 | Webhook → Code | AP gate: duplicate-invoice detection (vendor+amount+currency+number), tax-discrepancy check vs rate, PO amount conflict, unverified vendor bank-change flag, approval-authority threshold (finance_controller/CFO), partial-approval check, unsafe-payment-attempt detection. Any hit → decision `hold` + blocked actions (`wire_payment`, `execute_payment`). Created 2026-10-17, updated 2026-10-19. |
| A2 | P4 AI Failure Observatory | uKjInufuSj5gt1Hj | yes | 1 | Webhook → Code | Expected-vs-actual trace differ: field-level diff, emits failure taxonomy (`trace_mismatch`, severity high) and pass/fail verdict per scenario. Created 2026-10-17. |
| A3 | P5 Replay Recovery Regression Factory | 0FVCNaeG3Eqo7PUC | yes | 1 | Webhook → Code | Replay-safety checker: duplicate idempotency keys and duplicate external-effect IDs across an event log → `replay_safe` true/false with named errors. Created 2026-10-17. |
| A4 | GlacierEQ // Workflow Immune System (v1.0) | dUpTkUyIHhE4EHnG | yes | 1 | Error Trigger → Code → Code | Estate self-monitoring: captures any workflow failure, classifies it (TRANSIENT 429/timeout → retry allowed; AUTH_CREDENTIAL_DEFECT 401/403/token → no retry; STRUCTURAL_SCHEMA_DEFECT → no retry), then formats a dead-letter-queue record with quarantine status and a `REPAIR_WORKFLOW:<name>:<node>` continuation cursor. Created 2026-10-15. |
| A5 | GlacierEQ // Master Agent v2 — Exhaustive Workflow Element Builder | (local build; instance id 9gJckBvPvx2JJhW1 on the self-hosted host) | not activated | — | Chat Trigger → LangChain Agent + window memory + OpenRouter chat model | AI agent that builds exhaustive n8n workflow elements (full lifecycle, failure-first). One wire left: the Chat Model credential, attached in the n8n UI. Local JSON 12,948 B; builder script `build_master_v2.py`. |

Supporting documents in hand:
- `exports/n8n-master-agent-prompt-v1.md` (12,487 B) — the paste-ready master prompt
  (exhaustiveness standard, 10 failure classes, min 20 adversarial cases each with a
  RED/GREEN pair, truth discipline, completion gate). v2 (2026-10-19) restructured it:
  static system message for provider caching + task prompt, measurable acceptance
  criteria, checker-not-maker verification, capped self-critique loop, exact JSON
  output schema, seven-stage architecture.

## Set B — Self-hosted estate enumeration (most recent full count)

Source: API readback 2026-10-20 (glaciereq1.n8n-host.com, HTTP 200), recorded in the
Massive recovery-email working notes. **9 active workflows:**

1. P1 Accounts Payable Adversarial Laboratory — export in hand (A1)
2. P2 Quote-to-Cash State Machine — no export in hand
3. P3 Lead Routing CRM Integrity — no export in hand
4. P4 AI Failure Observatory — export in hand (A2)
5. P5 Replay Recovery Regression Factory — export in hand (A3)
6. GlacierEQ Workflow Immune System — export in hand (A4)
7. APEX Mission Continuity Network — no export in hand
8. Career Acquisition Intelligence Network — no export in hand
9. Assistant — no export in hand

Execution-log receipt from the same readback (night of Sun Oct 18 HST): APEX updated
16:49, P1 updated 17:36; runs 16:40–17:37 HST incl. APEX webhook runs (one error, then
success) and a P1 sequence of error → error → success. No hosted executions the morning
of Oct 19 (work was local on the Mac that failed).

Earlier snapshot (2026-10-19 call brief): 4 active workflows named — APEX Mission
Continuity, Career Acquisition Intelligence, Workflow Immune System, Assistant.
The count grew 4 → 9 across Oct 19–20 as the P-series labs were activated. Both
snapshots are dated observations, not a contradiction to smooth over.

## Set C — Failure-lab suites, executed (2026-10-15, cloud MCP gateway)

Source: session record 2026-10-15 (`~/memory/2026-10-15.md`). 7 workflows audited at
the Operator's order ("are they bullshit"), then the 5 synthetic GREEN suites executed:

| Execution | Suite | Result |
|-----------|-------|--------|
| 67 | (RED run) | **Failed** — email-regex escaping bug. Failure retained, not deleted; fixed in v1.1. |
| 95 | Quote-to-Cash | success — 28 test cases |
| 96 | Lead Routing v1.1 | success |
| 97 | AP Failure Evaluator | success |
| 98 | AP Durable Intake | success |
| 99 | Lead Durable Intake | success |

Skipped by design: RED regression suite (marked DO NOT USE) and Gold Standard Consumer
(READ ONLY). Audit verdict at the time, kept verbatim in the proof sheet's honesty
boundaries: real gate/assertion logic and a genuine RED→GREEN story; the suites are
code-node evaluators inside n8n, not integration-heavy production automation.

## Credentials (types only — values never leave the vault)

7 OAuth credentials verified live on the Cloud instance 2026-10-16, personal project
"casey b <glacier.equilibrium@gmail.com>": **Gmail, GitHub, Box, Notion, Google Sheets,
Mistral Cloud, Vercel AI Gateway.** Google Drive has no standalone credential (needs UI
wiring). MCP key rotated 2026-10-16 as post-exposure hygiene; the pre-rotation token's
appearance in a GitHub commit (GlacierEQ/n8n-automation 508722d) was caught by
GitGuardian and the token rotated — the incident is part of the evidence, not hidden.

## Usage volume (provider's own emails, glacier.equilibrium inbox)

- Cloud workspace is on a **trial plan: 1,000 executions/month**.
- 2026-10-21 10:00 UTC — n8n email: 80% used (800 of 1,000). Gmail id 1a15de7d98d02498.
- 2026-10-21 15:15 UTC — n8n email: **100% of monthly executions used**; workflows
  will stop unless the plan is upgraded. Gmail id 1a15f084c55ed79e.
- Oct 19: "n8n Assistant is out of credits" notice (Gmail id 1a15295be44e9783).

Citable line: the workspace consumed its full 1,000-execution trial month.

## Security posture

Full audit 2026-10-17 against CVE-2026-21858 ("Ni8mare," CVSS 10.0, self-hosted RCE):
**not affected** — Cloud instances are vendor-patched; the second host is
vendor-managed hosting. Report: `~/workspace/.jarvis/idea-executions/c7794c9a-…/scratch/audit-result.md`.
Version is not exposed on any unauthenticated route on either host (checked).

## Live probe — today, 2026-10-21 ~09:50–10:00 HST (full receipt in LIVE_PROBE_2026-10-21.md)

- Cloud MCP gateway: initialize OK (n8n MCP Server 1.2.0), tools/list OK — **58 tools**
  (surface has grown since the ~34 recorded Oct 16/17).
- Cloud MCP data calls: **HTTP 500 Internal Server Error on every tool tried**
  (search_workflows ×3, list_credentials, get_instance_context, list_workflow_tags,
  search_agents, search_data_tables). Same failure class as the flakiness recorded
  since the Oct 16 key rotation. Reported as today's observation, not a verdict on
  the key or the account.
- Self-hosted host REST: HTTP 200 but body is the **"Instance Dormant"** page — no API
  data. (It was live with a real UI on the Oct 20 readback; it sleeps.)
- Consequence for this bundle: today's fresh workflow/execution pull could not be
  completed. Everything above rests on the dated receipts named per set. When a data
  call lands again, refresh Set B/C counts and re-verify before citing.
