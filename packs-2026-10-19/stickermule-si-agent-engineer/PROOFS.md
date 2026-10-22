# Career proofs — Sticker Mule SI Agent Engineer

Selected from the GlacierEQ estate (verified 2026-10-08–19). Full convention: Claim / Evidence / Verified date.

---

## Proof: Fleet of autonomous agents doing real work

## Claim
Operate a fleet of autonomous agents in production: hourly job-discovery worker (role discovery, pack building, application-status tracking), cross-inbox triage worker, multi-day file-migration worker, memory and continuity systems. Agents run on their own, do meaningful work, and report with receipts — quiet runs stay silent.

## Evidence
- Worker scripts and run ledgers under `~/workspace/` (stranded-files-move worker.sh, hourly job pipeline); scoreboards in `~/memory/2026-10-19.md`.

## Verified
2026-10-19 (live runs today).

---

## Proof: Measure results, remove agents that don't deliver — 62/62 checks green

## Claim
Every agent run is measured: 62/62 verification checks green, per-run receipts, idempotent JSONL ledgers, per-file root-cause quarantine. Fail-closed gates: no agent completion claim without independent provider readback. Underperforming designs are retired outright — never silently tuned until they pass.

## Evidence
- Estate census (`~/workspace/estate-map/ESTATE_MAP.md`); migration ledgers under `~/workspace/goals/stranded-files-move-dropbox-google-drive/`; job-app-helix attribution engine (GO / NO-GO with fail-closed decisions).

## Verified
2026-10-08–19.

---

## Proof: Agents wired to tools — 65 MCP connectors + APIs, webhooks, data pipelines

## Claim
65 MCP connectors plus REST APIs, webhooks, and data pipelines connect agents to third-party and internal systems through one governed control plane — typed state transitions, human approval gates on consequential actions, recoverable runs.

## Evidence
- Skill docs under `~/workspace/custom-skills/`; connector docs under `~/workspace/custom-connectors/` and `/opt/hatch/connectors/`.

## Verified
2026-10-08–13 (estate census window).

---

## Proof: Test new models and tools as they ship, adopt what works

## Claim
Model choice is a benchmarked decision: LLM evaluation harnesses, A/B testing, 20-pair RED/GREEN adversarial cases per build. Multi-model routing across Claude, OpenAI, and open-source/self-hosted models (local Whisper diarization verified: Silero VAD + ECAPA, 2 speakers across 28 segments). New tools evaluated against representative tasks before adoption.

## Evidence
- n8n master prompt v2 (20 RED/GREEN cases) in workspace; local-audio-transcribe pipeline (`~/workspace/custom-skills/local-audio-transcribe/`).

## Verified
2026-10-13–19.

---

## Proof: Advise others on capabilities — in writing

## Claim
The daily product is written counsel: case clocks, filing checklists, decision briefs, one-page consult briefs — translated into decisions non-technical operators use the same day. Three years of briefs, letters, and operating doctrine written for clarity first.

## Evidence
- `~/workspace/doctrine/`; goal briefs under `~/workspace/goals/*/briefs/`; casework correspondence.

## Verified
Standing, demonstrated 2026-10-19 (this pack is itself the evidence: researched, tailored, forged end-to-end in one run).

---

## Kit numbers (allowlisted)
1,395 repositories · 989 tests · 62/62 verification checks green · 65 MCP connectors — carried from the Cresta pack (2026-10-19). Re-verify estate counts before a live submit if they moved.
