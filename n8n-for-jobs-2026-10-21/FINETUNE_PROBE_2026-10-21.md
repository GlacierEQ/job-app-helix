# n8n Fine-Tune Probe — 2026-10-21 (READ-ONLY)

Probe run: **2026-10-21 22:43:48Z–22:44:09Z UTC (12:43–12:44 HST)** via the sanctioned
MCP client (`local-n8n-operator/bin/n8n-mcp`) and a plain HTTPS GET on the self-hosted host.
**Nothing was changed**: no workflow, setting, or account was touched; no trial or
account was created; no workflow was executed or triggered. One GET on the dormant
host's root page only — no wake attempt, no API call against it.

## 1. Cloud MCP — live state now

| Call | Result |
|---|---|
| `initialize` (22:43:48Z) | ✅ OK — n8n MCP Server **1.2.0**, protocol 2024-11-05 |
| `tools/list` | ✅ OK — **58 tools** |
| `search_workflows` | ❌ HTTP 500 — body is an HTML error page: `<pre>Internal Server Error</pre>` (client reports `ok:false, error:"unparseable"`) |
| `search_workflows` (retry) | ❌ Identical HTTP 500 |
| `search_workflow_executions` | ❌ Identical HTTP 500 |
| `list_credentials` | ❌ Identical HTTP 500 |
| `get_instance_context` | ❌ Identical HTTP 500 |

**No workflow list, execution history, or usage data is readable through the MCP data
plane right now.** The handshake layer works; every data call fails server-side.

## 2. Changed vs the ~10:00 HST probe (2026-10-21)

**Nothing changed.** Identical profile ~2¾ hours later: initialize OK (server 1.2.0),
tools/list OK (58 tools), every data call HTTP 500. Self-hosted host: still dormant
(same as at 10:00 HST; it was live earlier that morning — hosts sleep; both are dated
observations).

No causal claim is made between the trial's 100%-executions state (provider emails
2026-10-21 10:00 UTC = 80%, 15:15 UTC = 100%) and the MCP 500s. The 500 pattern dates
to the Oct 16 key rotation, predating the quota exhaustion.

## 3. Self-hosted instance — glaciereq1.n8n-host.com

`GET https://glaciereq1.n8n-host.com/` at 22:44:09Z → **HTTP 200, "Instance Dormant —
n8n AI Assistant" page.** Dormant, not live. No REST API call was attempted (the page
shows the instance asleep, and per the operator skill the stored REST key belongs to
this host whose REST route is dead). Master Agent v2 (instance id 9gJckBvPvx2JJhW1)
lives on this host and was **not activated** — it cannot be a quota suspect.

## 4. The ~5-minute suspects — CANNOT DETERMINE from readable data

Direct answer: **no live workflow data is readable from either instance**, so no
workflow can be confirmed or cleared as a 5-minute poller from live state. What the
local evidence does establish:

**Cleared by export (event-driven, no timer exists in the file):**

| Workflow | Trigger (from export) | Can it poll? |
|---|---|---|
| P1 Accounts Payable Adversarial Laboratory | Webhook POST `p1-accounts-payable-adversarial-laboratory` → Code | No — executes only when called |
| P4 AI Failure Observatory | Webhook POST `p4-ai-failure-observatory` → Code | No |
| P5 Replay Recovery Regression Factory | Webhook POST `p5-replay-recovery-regression-factory` → Code | No |
| GlacierEQ // Workflow Immune System v1.0 | Error Trigger → Code → Code | No — fires only on another workflow's failure |
| Master Agent v2 (not activated) | Chat Trigger → LangChain Agent | No — on-demand chat only |

**Unverifiable — no export exists, trigger type unknown:**

P2 Quote-to-Cash State Machine · P3 Lead Routing CRM Integrity · APEX Mission
Continuity Network · **Career Acquisition Intelligence Network** · **Assistant**

9 active workflows were read back on 2026-10-20; exports exist for only 4 of them.
**If a ~5-minute poll exists in this estate, it lives in one of these five** — a
schedule/polling trigger cannot hide inside P1/P4/P5/Immune System as exported.
Two names fit the polling pattern on their face (a career-intelligence network that
watches job boards; an always-on "Assistant" — and n8n emailed Oct 19 that "n8n
Assistant is out of credits," showing the Assistant consumes metered usage), but that
is pattern-matching, **not evidence**. The Operator's "I fixed 3 that were firing
every 5" fix location is still unconfirmed — if it was in n8n Cloud, these five are
where to look first; 3 workflows × every 5 min ≈ 864 executions/day ≈ the trial's
whole 1,000-execution month in ~28 hours.

Caveat: exports reflect build-time state (Oct 15–19); a workflow could have gained a
schedule trigger after export. Only a live read settles it.

## 5. Fine-tuning pass — concrete first steps

1. **Restore a readable surface (the blocker for everything else).** The MCP data
   plane has returned HTTP 500 on every data call since the Oct 16 key rotation.
   Options, in order: (a) Operator opens the Cloud UI (glaciereq.app.n8n.cloud) —
   the UI shows each workflow's triggers and the executions view directly, no MCP
   needed; (b) re-issue/rotate the MCP access token in the UI and update
   `~/.config/muse/keys.env`, then re-probe; (c) if the 500s persist with a fresh
   token, it's an n8n-side instance fault — support ticket with timestamps from the
   two probes (2026-10-21 ~19:50Z and 22:43Z).
2. **Enumerate-then-classify the full set.** Once readable: pull every workflow with
   active state + trigger inventory, and the executions list for the last 7 days
   grouped by workflow. The burn source is arithmetic: whichever workflows own the
   execution count own the quota. Diff that list against the 9 known actives.
3. **Interrogate the five unexported workflows first** (P2, P3, APEX, Career
   Acquisition, Assistant): any Schedule Trigger / polling node (Gmail/RSS/HTTP
   poll) at ≤5-min cadence gets re-cadenced to hourly or converted to
   webhook/event-driven where the source supports push.
4. **Export everything.** Pull full JSON exports of all 9+ workflows into this
   bundle so the estate is inspectable offline — today only 4 of 9 actives have
   exports, which is why this probe had to stop at "cannot determine."
5. **Then the actual fine-tune** (needs his go-ahead per action, per the operator
   skill): re-cadence or pause the pollers, confirm the Immune System's error
   workflow wiring, and set a monthly execution budget checkpoint (~80% alert) so
   the next burn is caught before the wall.
6. **Fresh-trial idea — hold.** A new trial on a clean workspace would give clean
   execution records, but nothing should be created until the poll source is
   identified; otherwise the new trial burns the same way and the records are
   dirty from day one. Sequence: identify → fix cadence → then decide whether a
   fresh trial is still needed. (No trial or account was created by this probe.)

## Bottom line

Live state is **unchanged from 10:00 HST**: Cloud MCP handshake healthy, data plane
500 on every call; self-hosted dormant. The four exported active workflows are
provably event-driven and cannot be the 5-minute burn. The suspects are the five
active workflows with no exports — and naming them guilty or innocent requires one
readable surface: the Cloud UI, or a repaired MCP token.
