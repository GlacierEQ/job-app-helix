# Proof: n8n automation estate — failure-first workflow engineering

Convention: Claim / Evidence / Verified — same as `GlacierEQ/job-application/career-proofs/`.
This sheet supersedes the 2026-10-17 `n8n-estate.md` proof (4 live workflows) with the
fuller enumerated record. Numbers are quoted exactly as they stand in their receipts.

## Claim
Builds and operates an n8n automation estate across two instances (self-hosted +
n8n Cloud) organized around one discipline: automation that survives failure.
9 active workflows on the self-hosted estate (2026-10-20 API readback), including an
accounts-payable adversarial laboratory, a quote-to-cash state machine, lead-routing
CRM integrity, an AI failure observatory, a replay/recovery regression factory, and a
workflow immune system that classifies other workflows' failures and quarantines them
with a repair cursor. Failure suites are run RED→GREEN with the failures kept:
execution 67 failed on an email-regex escaping bug, the failure was retained, v1.1
fixed it, and the five GREEN suites then executed clean (executions 95–99; the
quote-to-cash suite alone carries 28 test cases). The Cloud workspace consumed its
full 1,000-execution trial month (n8n's own 80% and 100% notices, 2026-10-21).
7 OAuth integrations wired (Gmail, GitHub, Box, Notion, Google Sheets, Mistral,
Vercel AI Gateway). Estate audited clean against CVE-2026-21858 (CVSS 10.0).

## Evidence
- Workflow exports (byte-verified, SHA-256 manifest): this bundle, `exports/` —
  P1, P4, P5, Workflow Immune System, Master Agent v2.
- Estate enumeration + execution log: Massive recovery-email working notes,
  2026-10-20 (`~/workspace/job-app-helix/drafts-2026-10-20/massive-chien-recovery-email.md`).
- Failure-lab audit + executions 67 / 95–99: session record 2026-10-15
  (`~/memory/2026-10-15.md`).
- Usage notices: Gmail ids 1a15de7d98d02498 (800/1,000) and 1a15f084c55ed79e (100%),
  glacier.equilibrium inbox, 2026-10-21.
- Credential inventory: MCP readback 2026-10-16.
- CVE audit: `~/workspace/.jarvis/idea-executions/c7794c9a-d0b3-45ff-8b9c-de64da564199/scratch/audit-result.md`, 2026-10-17.
- Master Agent prompt v1 + v2 architecture: this bundle `exports/`; session records
  2026-10-18 / 2026-10-19.

## Verified
2026-10-21 — exports re-hashed and re-scanned (no credentials, no keys, no pinned
data); live probe attempted same day (see Limitations).

## Resume bullets (each maps to a receipt above — use verbatim or not at all)
- Operate a two-instance n8n estate (self-hosted + Cloud); 9 active workflows
  spanning AP, quote-to-cash, lead routing, failure observation, and replay recovery.
- Built an accounts-payable adversarial lab that holds payment on duplicate invoices,
  tax/PO mismatches, unverified bank changes, and insufficient approval authority —
  the fraud-shaped cases, not the happy path.
- Run failure suites RED→GREEN with failures retained as evidence: a regex-escaping
  failure (execution 67) kept, fixed in v1.1, and re-proven across 5 suites /
  28 quote-to-cash cases (executions 95–99).
- Built a workflow immune system: error-trigger capture, failure classification
  (transient vs credential vs schema defect, with retry policy per class), and
  dead-letter quarantine carrying a repair cursor.
- Consumed a full 1,000-execution n8n Cloud trial month; 7 OAuth integrations wired.
- Audited the estate against CVE-2026-21858 (CVSS 10.0) and practiced credential
  rotation after a GitGuardian-flagged token exposure.

## Honesty boundaries (do not cross in any application)
- The P-series evaluators are **code-node logic inside n8n** (webhook ingest →
  deterministic gate code), not integration-heavy production automation with many
  third-party nodes. Say "failure-injection and gate-logic prototypes that run in
  n8n," not "production client automations."
- The GREEN suites run **synthetic cases** (invented invoices/leads) — that is the
  Massive role's own stated method (10+ invented test cases per workflow), and it is
  framed that way.
- No client or employer is claimed for this work. It is founder/operator estate work,
  2023–present framing rules apply as in every other pack.
- Master Agent v2 is **built, not activated** — one credential wire remains, and it
  is the Operator's UI step. Never present it as running.
- Workflow counts are dated: 4 active (Oct 19 brief) → 9 active (Oct 20 readback).
  Cite with the date or don't cite.

## Limitations
- 2026-10-21 live re-verification of the workflow list could not be completed: Cloud
  MCP data calls returned HTTP 500 across six tools (handshake and tool list healthy,
  58 tools), and the self-hosted host answered with its dormant page. Both are dated
  observations in `LIVE_PROBE_2026-10-21.md`. Re-pull before any submission that
  cites a current count.

## Used in
- Massive / Eric Chien recovery email, sent 2026-10-20 (4 exports attached).
- This bundle (2026-10-21) — not yet cited in any submitted pack. As of this date,
  no pack PROOFS.md in the Oct 20–21 waves mentions n8n; this sheet is the source
  to cite from when an n8n-relevant role (automation, FDE, AI platform) is targeted.
