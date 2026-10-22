# Career proofs — ElevenLabs Full-Stack Engineer, Creative Agents

Selected from the GlacierEQ estate (verified 2026-09-25 – 2026-10-19). Full convention: Claim / Evidence / Verified date.
Language tuned to ElevenLabs' posting: agent-powered creative features, model orchestration, agent capabilities/integrations, reliable async workflows for audio/image/video, evals/monitoring/testing, end-to-end ownership.

---

## Proof: Reliable async workflows for audio, image, and video generation

## Claim
Builds agent workflows that generate audio, image, and video reliably: durable asynchronous jobs with state persistence, evaluation gates on output, observability across the pipeline, and cost/latency instrumentation per task.

## Evidence
- fal.ai connector integration: 600+ generative media models (text-to-image, image-to-video, audio) behind one REST API, queued async endpoints for durable media jobs (`~/workspace/custom-skills/local-fal-ai/SKILL.md`).
- Offline faster-whisper transcription pipeline (WhisperX lineage): isolated venv, pinned deps, clean CLI, idempotent batch Box-folder processing (`~/workspace/custom-skills/local-audio-transcribe/SKILL.md`).
- Podcast/narration pipelines under the generate_podcast / spoken-audio skills — research, script, produce, deliver.

## Verified
2026-09-25 (fal.ai connector live check) – 2026-10-13 (audio-transcribe build).

---

## Proof: Own the harness — evals, traces, judge-in-the-loop, monitoring, testing

## Claim
Owns the harness that decides whether an agent is actually doing the job: eval suites with golden sets and behavioral assertions, judge criteria with written rubrics, full trace logging, regression gates, and monitoring that catches regressions in a live product — measured against a baseline, every run.

## Evidence
- Eval/verification patterns in `~/workspace/job-app-helix/tests/`; the forge's honesty gate refuses to emit unapproved numbers (HonestyError) — the eval gate decides, not the generator.
- Job-App Helix: fail-closed GO/NO-GO decisions on immutable evidence models; no agent completion claim without independent provider readback.

## Verified
2026-10-08–19 (estate verification window).

---

## Proof: Debugging a failing async pipeline — the failure modes found, and the catchers built

## Claim
Traces runs through structured logs, persisted job state, queue behavior, and per-task latency instrumentation; diagnoses stuck loops, bad retrievals, tool misuse, context blowouts, retry pathology, and provider latency — fixes the root cause, builds the catcher (replay loops, fail-closed gates, behavioral assertions), and adds the alert so it cannot recur.

## Evidence
- Fail-closed governance patterns in `src/job_app_helix/` (estate_compiler, campaign engine); per-task `latency_ms` instrumentation — the tracing practice that makes debugging honest.

## Verified
2026-10-19 (estate window; failure-mode discipline verified across packs).

---

## Proof: 65 MCP connectors — agent capabilities and integrations as the governed platform layer

## Claim
Authors MCP servers and connectors that expose tools and structured resources to any MCP-compatible system — the shared, governed context layer every downstream agent feature runs on — with evidence boundaries and audit receipts. Integrations over ERPs, CRMs, data pipelines, webhooks, and messaging systems.

## Evidence
- Connector docs under `~/workspace/custom-connectors/` and `/opt/hatch/connectors/`; claim tracking and idempotent automation patterns across the estate.

## Verified
2026-10-08–19 (estate census window; his approved number).

---

## Proof: End-to-end ownership — discovery to deployment to operation

## Claim
Takes ambiguous problems from technical design through shipping and ongoing operation: narrow measurable prototypes with early boundaries (feature flags, telemetry, error handling, rollback), then hardens architecture based on real usage; uses customer feedback to guide what gets built next.

## Evidence
- Hourly Job-App Helix production pipeline: launched as prototype, hardened into a fail-closed production system running from his own operations — the same prototype→harden→operate discipline the JD asks for.
- Vercel-deployed production surfaces (casey-barton-glaciereq.vercel.app) plus backend services on Supabase/Postgres.

## Verified
2026-10-19 (estate window).

---

## Proof: Production agent estate — 1,395 repos, 989 tests, 62/62 checks green

## Claim
Built and operate a production-grade agent control plane across a 1,395-repository estate: planning and tool-use loops, retrieval over a domain ontology, memory, guardrails, typed handoff contracts, human approval gates on consequential actions. 989-test suite, 62/62 verification checks green — no claim without independent provider readback.

## Evidence
- Estate census (`~/workspace/estate-map/ESTATE_MAP.md`); kit numbers from `_candidate.yaml` (verified 2026-10-13).

## Verified
2026-10-13 (census). Re-verify test count before citing in a new resume.
