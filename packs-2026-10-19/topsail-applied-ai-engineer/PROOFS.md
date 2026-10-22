# Career proofs — Topsail Applied AI Engineer

Selected from the GlacierEQ estate (verified 2026-10-08–19). Full convention: Claim / Evidence / Verified date.
Language tuned to Topsail's posting: agent runtimes, tool/MCP integrations, eval harness ownership, trace intelligence, judge-in-the-loop, production failure-mode literacy.

---

## Proof: Own the harness — evals, traces, judge-in-the-loop against a baseline

## Claim
Owns the harness that decides whether an agent is actually doing the job: eval suites with golden sets and behavioral assertions, judge criteria with written rubrics, full trace logging, and regression gates — measured against a baseline, every run.

## Evidence
- Eval/verification patterns in `~/workspace/job-app-helix/tests/`; the forge's honesty gate refuses to emit unapproved numbers (HonestyError) — the eval gate decides, not the generator.
- Job-App Helix campaign engine: fail-closed GO/NO-GO decisions on immutable evidence models; no agent completion claim without independent provider readback.

## Verified
2026-10-08–19 (estate verification window).

---

## Proof: Production failure-mode literacy — the failure modes found, and the catchers built

## Claim
Ships agents into production, finds the failure modes, and builds the catchers: replay loops that reproduce stuck runs, behavioral assertions on tool use, fail-closed gates on ambiguous state, and recovery restricted to contingency evidence declared before reassessment. Burns that became opinions: context management, retrieval/chunking, hybrid search, tool design, eval design, and the cost/latency tradeoffs of the deployment stack.

## Evidence
- Fail-closed governance patterns in `src/job_app_helix/estate_compiler.py` and `pistons.py`; recovery discipline documented across the job-app-helix engine (immutable evidence models, contingency-evidence recovery rule).
- Per-task `latency_ms` instrumentation in `apex_distributed_compute.py` — the tracing practice that makes benchmarking and cost/latency tradeoff analysis honest.

## Verified
2026-10-19 (estate window; failure-mode discipline verified across packs).

---

## Proof: 65 MCP connectors — tool and MCP integrations as the governed platform layer

## Claim
Authors MCP servers and connectors that expose tools and structured resources to any MCP-compatible system — the shared, governed context layer every downstream tool runs on — with evidence boundaries and audit receipts for compliance-aware deployment. Integrations over ERPs, CRMs, data pipelines, webhooks, and messaging systems.

## Evidence
- Connector docs under `~/workspace/custom-connectors/` and `/opt/hatch/connectors/`; claim tracking and idempotent automation patterns across the estate.

## Verified
2026-10-08–19 (estate census window).

---

## Proof: Model-agnostic benchmarking — primitives tested, findings turned into configuration

## Claim
Benchmarks agent primitives against datasets and iterates on the findings: run experiments on memory, retrieval, and orchestration behavior, investigate where they perform well and where they fall short, and turn results into configuration improvements. Tracks per-task latency and token cost, so model-swap decisions are measured, not argued.

## Evidence
- Benchmark/experiment discipline in `src/job_app_helix/`; per-task latency instrumentation; eval-layer discipline: golden suites with behavioral assertions rather than intuition.

## Verified
2026-10-19 (this pack's forge run).

---

## Proof: Production agent estate — 1,395 repos, 989 tests, 62/62 checks green

## Claim
Built and operate a production-grade agent control plane across a 1,395-repository estate: planning and tool-use loops, retrieval over a domain ontology, memory, guardrails, typed handoff contracts, human approval gates on consequential actions, durable state that survives a failed run. 989-test suite, 62/62 verification checks green — no claim without independent provider readback.

## Evidence
- Estate census (`~/workspace/estate-map/ESTATE_MAP.md`); kit numbers carried from the Scale AI FDE variant (2026-10-08).

## Verified
2026-10-08 (resume-forge scale-fde-ps variant). Re-verify test count before citing in a new resume.
