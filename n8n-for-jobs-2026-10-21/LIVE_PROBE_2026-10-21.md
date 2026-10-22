# Live Probe Receipt — 2026-10-21 ~09:50–10:05 HST

Purpose: fresh readback before citing any n8n number in a job application.
Method: both known routes, read-only calls only. Nothing activated, executed,
created, or modified.

## Route 1 — n8n Cloud MCP gateway (glaciereq.app.n8n.cloud/mcp-server/http)
Client: `~/workspace/custom-skills/local-n8n-operator/bin/n8n-mcp` (token from
keys.env at runtime; value never printed or logged).

| Call | Result |
|------|--------|
| initialize | OK — serverInfo "n8n MCP Server" v1.2.0, protocol 2024-11-05 |
| tools/list | OK — **58 tools** (surface grew from ~34 recorded 2026-10-16/17) |
| get_instance_context | HTTP 500 Internal Server Error (HTML error page) |
| search_workflows {"limit":100} | HTTP 500 — tried 3× across ~10 min, same result |
| list_credentials | HTTP 500 |
| list_workflow_tags | HTTP 500 |
| search_agents {"limit":20} | HTTP 500 |
| search_data_tables {"limit":20} | HTTP 500 |

Classification: dated observation. Handshake healthy, data plane failing — the same
failure class recorded since the 2026-10-16 key rotation ("initialize/list succeed,
calls sometimes drop"). NOT evidence about the key, the account, or the workflows
themselves. Not retried further this session; no alternate route attempted against
this instance (its REST key on file belongs to the other host and 401s on Cloud —
recorded 2026-10-17, not re-tested today).

## Route 2 — Self-hosted REST (glaciereq1.n8n-host.com/api/v1)
Client: `~/workspace/skills/n8n/bin/n8n-api` (X-N8N-API-KEY from Postman Muse Keys).

| Call | Result |
|------|--------|
| GET /workflows?limit=100 | HTTP 200, body = "Instance Dormant - n8n AI Assistant" HTML page — the host's dormant landing page, not API JSON |

Classification: dated observation. The host was live with API readback on 2026-10-20
(9 active workflows) and live-UI on the 2026-10-21 05:46 HST wake-up watch; at this
probe it answers dormant. Hosts on this plan sleep; no wake action was taken (a wake
would run real automation surface — outside a read-only gather).

## Provider mail the same morning (context, not causation)
- 10:00 UTC — Cloud workspace at 80% of monthly executions (800/1,000, trial).
- 15:15 UTC — 100% reached; "workflows will stop running unless you upgrade."
Recorded alongside the probe because both are true today. No causal claim is made
between the quota state and the MCP 500s.

## Net effect on the bundle
No fresh workflow/execution list was obtained today. All counts in
`01_INVENTORY.md` / `02_PROOF_SHEET.md` carry their observation dates. Refresh path
when the data plane answers again: `n8n-mcp call search_workflows {"limit":100}`,
`list_credentials {}`, `search_workflow_executions` per workflow — then update the
Verified date on the proof sheet, never the numbers without the new readback.
