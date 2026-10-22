# Career proofs — Reddit Lead Forward Deployed Engineer (AI Enablement) (req 8301736, primary-verified 2026-10-20)

Keyed to the JD keyword set. Convention: Claim / Evidence / Verified date. Leadership claims describe architecture direction, design/code review mentoring, and practice-setting across his own estate — NO formal people-management or corporate reporting lines claimed. No claim of Reddit-platform deployment; no internal-enterprise FDE track record claimed.

---

## Proof: Technical leadership — architecture direction adopted estate-wide

## Claim
The JD requires "demonstrated technical leadership and product judgment through architecture decisions, reviews, mentoring, and influence across teams" and "create a component, engineering practice, or architectural pattern adopted beyond your own project." He set the technical direction for a 1,395-repository applied-AI estate: platform patterns — claim tracking, evidence boundaries, audit receipts, structured run-state observability, approval gates — that every project in the estate inherits. The patterns were adopted beyond any single project by design: that's how the estate compounds.

## Evidence
- Estate-wide platform patterns: claim tracking, evidence boundaries, audit receipts, run-state observability (resume competencies; estate architecture).
- Forward-Deployed-Agentic-Powerhouse — delivery practice (DISCOVER→FRAME→BUILD→INTEGRATE→EVALUATE→PROVE→DEPLOY) documented and executed hourly in this pipeline.

## Verified
2026-10-20 (pack provenance).

---

## Proof: Mentoring through design and code review — review gates with teeth

## Claim
"Organize and sequence engineers' work… mentor engineers and technical leads through design and code reviews, strengthening applied AI, system design, evals, and production judgment." His mentoring surface is the review-gate system itself: the document forge's honesty gate raises HonestyError instead of rendering a bold number not on the kit allowlist; the campaign engine's GO/NO-GO gate vetoes composition; tool calls in the agent coordinator are proposed for review, never executed blind. Reviews that can veto are what strengthen production judgment — in his work and in anyone working with it.

## Evidence
- `~/workspace/job-app-helix/hire_package/resume-forge/cover.py` — `honesty_gate()`.
- `anthropic-agent-coordinator` — **62/62** tests green; review-gated tool calls.
- `~/workspace/job-app-helix/AGENTS.md` §6 — adversarial review lane as practice.

## Verified
2026-10-08 (kit lineage); 2026-10-20 (pack provenance).

---

## Proof: Strategy → roadmap → investment priorities — the AI Enablement loop

## Claim
The Lead JD: "stay current with advances in AI models, agents, tools, and deployment practices; translate promising capabilities into strategy, roadmap, and investment priorities." His hourly pipeline is that translation in operation: every run sweeps Greenhouse/Ashby boards by publish window, classifies kills (GEO/COMP/SENIORITY/DOMAIN) and carries, tracks watchlist state across runs, and feeds a delivery rule that escalates only what needs a decision — strategy from evidence, updated every hour, with receipts.

## Evidence
- `~/workspace/job-app-helix/sweep-raw/sweep-2026-10-20-*.json` — hourly sweeps with kill/carry classification and source trust notes (live artifacts).
- This pack: Reddit's own board was a coverage gap across all prior runs; this run identified the gap and added `reddit` to the sweep sources.

## Verified
2026-10-20 (live operation).

---

## Proof: Evals, review gates, HITL controls, observability, evidence — the JD's five

## Claim
Same as the Senior posting: define evals, review gates, human-in-the-loop controls, observability, and evidence. His operating standard is the evidence state machine (nominal / recoverable / hard-no-go) with a **989-test** control plane; evals with explicit release thresholds, gold sets, and LLM-as-judge; review gates with real veto power; audit receipts on every run.

## Evidence
- Job-App Helix control plane: 989-test suite; evidence state machine.
- LLM-as-judge over local Mistral API, verified live 2026-10-06 (`~/workspace/custom-skills/local-mistral/SKILL.md`).

## Verified
2026-10-06 (judge); 2026-10-20 (pack provenance).

---

## Proof: Hands-on in consequential work — failure analysis with root-cause quarantine

## Claim
"Remain hands-on in the most consequential work." His consequential-work practice: failure analysis with root-cause quarantine instead of silent retries — the stranded-files worker classifies every failure (6,000+ files, per-file md5+size verification, idempotent resume, parked/quarantine ledgers); the campaign engine restricts recovery to contingency evidence declared before reassessment; apex-control-plane runs circuit breakers, dead-letter capture, fail-closed startup.

## Evidence
- `~/workspace/stranded-files-move/worker.sh` — ledgered, quarantining worker (observed in operation 2026-10-20).

## Verified
2026-10-20 (live operation receipts).

---

## Proof: MCP integrations + enterprise identity/access — 65 connectors

## Claim
"Experience with MCP, reusable tool integrations, and enterprise identity and access patterns." 65 MCP connectors integrated with claim tracking and idempotent automation; access controls, approval gates on consequential actions, and audit receipts as the estate's identity/access surface.

## Evidence
- Estate integration surface: 65 MCP connectors (resume kit numbers, carried lineage 2026-10-08+).

## Verified
2026-10-20 (pack provenance).

---

## Proof: Business-critical workflows with auditability — GO/NO-GO evidence models

## Claim
Preferred: "experience delivering business-critical workflows with auditability, sensitive data, or consequential automated actions." The attributable campaign engine composes assessments into GO / NO-GO with immutable evidence models, stable finding codes, and fail-closed decisions — consequential automated decisions with named accountability, reversibility, and a full evidence trail. Auditability is the product, not a checkbox.

## Evidence
- Job-App Helix campaign engine (this pack researched, tailored, forged, and verified by that engine).

## Verified
2026-10-20 (pack provenance).

---

## Proof: Measuring gains — quantify quality/speed/capacity/cost

## Claim
Preferred: "experience measuring workflow gains in quality, speed, capacity, or cost." The pipeline measures itself: per-run sweep receipts with enumerated-vs-classified counts, kill/carry tallies, source trust notes, and estate receipts (1527 staged files verified zero-failure; quarantined-failure recovery ledger). Success/failure metrics distinguished per run — planned / started / succeeded / failed / verified.

## Evidence
- `~/workspace/job-app-helix/sweep-raw/sweep-2026-10-20-0542.json` (this run's receipt).
- Stranded-files move scoreboard: step1 ok=1527 failed=0 (observed in operation).

## Verified
2026-10-20 (live operation).
