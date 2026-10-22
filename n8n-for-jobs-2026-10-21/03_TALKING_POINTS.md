# n8n Talking Points — interviews & application answers

Built 2026-10-21 from the workflow code itself (bundle `exports/`) and the dated
receipts in `01_INVENTORY.md`. Every line below can be backed live or by export.

## The one-line pitch
"I don't build automations that work on the happy path. I build the labs that break
them first — then the gates, the replay checks, and the immune system that catches
what still gets through."

## If asked: "What's the most interesting workflow you've built?"
**P1 — Accounts Payable Adversarial Laboratory.** It doesn't process invoices; it
attacks an AP pipeline. Feed it an invoice batch and it holds payment when it finds:
a duplicate invoice (same vendor, amount, currency, number), a tax amount that
doesn't match the rate, a PO whose amount conflicts with the invoice, an unverified
vendor bank-account change, approvals that don't cover the total, approvers without
finance-controller/CFO authority over the threshold, or an outright unsafe payment
attempt — which also blocks the `wire_payment` / `execute_payment` actions by name.
That's the fraud-and-error surface of AP, encoded as a deterministic gate.
(Follow-up ready: "the code is 60 lines — the value is the case list, not the size.")

## If asked: "Tell me about a failure."
**Execution 67.** A lead-routing suite failed on an email-regex escaping bug. The
failure was kept in the log — not deleted, not re-run into oblivion — diagnosed,
fixed in v1.1, and then the whole set of five suites was executed green
(executions 95–99). The quote-to-cash suite carries 28 cases. "Broke it, kept the
failure, fixed it, proved it" is the whole demo arc in one sentence.

## If asked: "How do you make automations reliable?"
Three layers, all built:
1. **Gates before effects** — P1-style deterministic checks decide pay/hold before
   any money-shaped action exists.
2. **Replay safety** — P5 scans an event log for duplicate idempotency keys and
   duplicate external effects; a replay that would double-charge or double-send
   fails the check before it runs.
3. **An immune system** — a workflow whose only job is other workflows' failures:
   error-trigger capture, classification (transient 429/timeout → retry; credential
   401/403 → stop; schema defect → stop), and a dead-letter record with a repair
   cursor (`REPAIR_WORKFLOW:<name>:<node>`) so the fix starts at the failed node,
   not from a blank page.

## If asked: "How do you evaluate AI-built workflows?"
**P4 — AI Failure Observatory** plus the master-prompt discipline: expected-vs-actual
trace diffing with a named failure taxonomy, and a builder prompt that demands the
full lifecycle, 10 failure classes, and a minimum of 20 adversarial cases per
element — each with a RED (fails as designed) and GREEN (passes after fix) pair.
Checker-not-maker: the thing that verifies is never the thing that built.

## If asked about scale / real usage
- Cloud workspace burned its **full 1,000-execution trial month** (n8n's own notices:
  800/1,000 at 10:00 UTC, 100% at 15:15 UTC, Oct 21).
- 7 OAuth integrations wired on the Cloud instance: Gmail, GitHub, Box, Notion,
  Google Sheets, Mistral, Vercel AI Gateway.
- The night of Oct 18 the execution log shows live iteration: APEX error → success,
  P1 error → error → success, 16:40–17:37 HST.

## If asked about security
- Audited the estate against **CVE-2026-21858 ("Ni8mare," CVSS 10.0)** on Oct 17:
  not affected (Cloud vendor-patched; second host vendor-managed), with the check
  documented route-by-route.
- A pre-rotation MCP token surfaced in a GitHub commit; GitGuardian flagged it;
  the token was rotated the same cycle. "My secrets discipline has a receipt,
  including the time it caught me."

## What NOT to claim (tripwires)
- Not production client automation — estate/founder work + failure-lab prototypes.
- Not integration-heavy node graphs — the P-series is webhook → gate code by design.
- Master Agent v2 is built, not live (one credential wire left, by design his step).
- Counts carry dates (4 active Oct 19 → 9 active Oct 20). Live list couldn't be
  re-pulled Oct 21 (Cloud data calls 500; self-hosted host dormant) — if an
  interviewer asks "how many today," the honest answer is the dated count plus
  exactly that sentence. It demonstrates the discipline better than a fresh number.
