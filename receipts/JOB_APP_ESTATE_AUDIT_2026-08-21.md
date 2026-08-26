# APEX Job Application Estate Audit — 2026-08-21 HST

## Decision

The job-application estate is not one repository and it is not accurately modeled as only `job-app-helix -> job-application`.

The current implementation has **four distinct application planes** with different trust boundaries:

1. `GlacierEQ/job-app-helix` — application intelligence, evidence control, target/opening analysis, Greenhouse preparation/finalization/submission planning, portfolio verification.
2. `GlacierEQ/job-app` — private application operations, lifecycle state, claims/artifacts, integrity ledger, external-receipt state transitions.
3. `GlacierEQ/JOB-RESUME-BUILDER-` — Resume Shapeshifter product, source-grounded resume/JD analysis, human-reviewed tailoring, application artifact compilation.
4. `GlacierEQ/job-application` — public recruiter distribution, portfolio/recruiter projections, public hire surface, Vercel deployment source.

They should compose. They should not be collapsed merely because capabilities overlap.

## Scope and counts

The authenticated Helix estate scope dated 2026-08-17 records 1,183 owned repositories. The admitted recruiter rollout is intentionally much smaller and is not the entire estate.

Current audit footprint:

- **66** live-linked public child repositories in `manifests/live_repository_links.json`.
- **+1** Helix control root = **67** admitted rollout repositories.
- **+5** directly evidenced job-system dependencies outside that rollout: `job-app`, `monolith`, `Pro_Code`, `megaminds-pdf`, `glaciereq-excellence-core`.
- **72** modeled current job-system repositories directly evidenced by this audit.
- `portfolio-organization-master` is retained as historical provenance, producing a **73-repository current+historical footprint**.

This is a modeled job-system footprint, not a claim that only 72 of the full 1,183-repository estate can ever contribute to hiring. Monolith also records private company-track candidates beyond the public 66.

## Executive grading

| Repository / plane | Role | Current grade | Keep / disposition | Main finding |
|---|---|---:|---|---|
| `job-app-helix` | Control + application intelligence | **B-** | KEEP / P0 repair | Powerful engine; current head `c397365e...` is red at Buildkite 923; primary branch unprotected. |
| `job-app` | Private application execution | **B** | KEEP / promote topology | Real integrity-backed flight deck exists; README verification posture is stale; hosted CI not authoritative; branch unprotected. |
| `JOB-RESUME-BUILDER-` | Resume Shapeshifter product | **B+** | KEEP / product flagship | Strong truth-constrained compiler and successful prior exact-head verification; production E2E/deploy remains unverified; branch unprotected. |
| `job-application` | Public recruiter distribution | **D** | KEEP / P0 production repair | Sophisticated source, but current production root is 404, recruiter routes are 404, source carries a private-repo redaction defect, Helix pin is stale, branch unprotected. |
| `monolith` | Private estate/catalog/provenance | **B** | KEEP as private support | Valuable zero-omission/company-track catalog; internal promotion ledgers conflict on Mastermind and contain stale governance language. |
| `AKOS` | Identity/governance/runtime proof | **B+** | KEEP / recruiter evidence | Active and high-value; exact-current CI status was not surfaced by the connector during this audit. |
| `the-tower-of-babel` | Polyglot/context integrity proof | **B+** | KEEP / reference evidence | Current context-integrity work; public projection correctly treats it as reference-only rather than application authority. |
| `pro-code` | Executable engineering/runtime proof | **B** | KEEP / reference evidence | Active proof surface; incomplete language planes remain bounded. |
| `Pro_Code` | Private operator doctrine/validator | **B-** | KEEP private support | Current authority-semantic work; should not become recruiter/application state authority. |
| `mastermind` | Historical/intelligence donor | **QUARANTINED** | DONOR / re-admit only with proof | Monolith application registry puts it at L0 while another flagship ledger still lists it, creating a governance conflict. |
| `megaminds-pdf` | Focused PDF viewer | **B+ product, C relevance** | KEEP as evidence satellite | Verified focused viewer, but not foundational application infrastructure; architecture currently overstates its job-app role. |
| `apex-control-plane` | Shared APEX execution/fidelity support | **B+** | KEEP shared dependency | Active startup/fidelity hardening; not an application-state owner. |
| `glaciereq-excellence-core` | Shared APEX objective math | **B** | KEEP shared dependency | Useful control extra outside the 66; not recruiter-facing application machinery. |
| `portfolio-organization-master` | 2025 estate-planning snapshot | **HISTORICAL** | PRESERVE / never current authority | README explicitly identifies it as historical and superseded by current Helix governance. |

## P0 findings

### P0-1 — Public production is currently broken

The newest Vercel production deployment for `casey-barton-glaciereq` is marked READY, but live readback returned:

- `/` -> **404**
- `/recruiter-review/` -> **404**
- `/data/recruiter-role-matrix.json` -> **404**

The deployment build downloaded only one deployment file, completed in roughly 73 ms, and reported that no files were prepared for cache. A READY deployment is therefore not a valid production-health receipt.

**Required action:** rebuild/deploy from the exact proven `job-application` source bundle, then require HTTP/readback checks before production promotion.

### P0-2 — Current public source contains a private-repository redaction regression

Current `job-application/main` contains the Microcode Governance record with repository URL `https://github.com/GlacierEQ/xai-colossus-microcode` even though the repair contract requires the private identity to be withheld.

Open PR #244 fixes this and the no-inline-style presentation violation, but it was cut from old base `5566a599...`, is currently unmerged, and is not a safe representation of current `main` without rebasing/reapplying the small delta.

**Required action:** reapply the three-line repair onto current `main`, run the complete public validation suite, then deploy exact proven output.

### P0-3 — Helix current `main` is red again

Helix was repaired to green Buildkite 920 at `2e47bd55...`. Three later opening-freshness commits advanced `main` to `c397365e...`, where Buildkite **923 fails**.

The audit therefore does not inherit the previous green claim. Current truth is red.

**Required action:** diagnose/fix 923 at the current head without reverting the new opening-freshness capability.

### P0-4 — All four application planes have unprotected primary branches

Verified branch metadata:

- `job-app-helix/main`: unprotected, no required status checks.
- `job-application/main`: unprotected, no required status checks.
- `job-app/master`: unprotected, no required status checks.
- `JOB-RESUME-BUILDER-/main`: unprotected, no required status checks.

This is a systemic integrity defect. A green exact head can be replaced immediately by a red direct push, and production can move without source/test gates.

**Required action:** establish primary-branch protection/rulesets with repository-specific required checks and an emergency path that remains explicit and auditable.

## Four-plane audit

### 1. `GlacierEQ/job-app-helix` — KEEP, repair current head

**Strong mechanisms currently present**

- CandidateProfile and resume compilation.
- target/company/opening intelligence.
- application-ready packet promotion.
- Greenhouse live field discovery.
- explicit applicant confirmation boundary.
- attachment SHA-256 and size binding.
- `GREENHOUSE_APPLICATION_FINAL.json` finalization.
- authorization-gated Greenhouse submission planning/execution boundary.
- idempotency and duplicate-attempt fencing.
- explicit handoff state when employer-issued Greenhouse API credentials are unavailable.
- estate compiler and recruiter evidence states.
- APEX exploration that treats the registry as an index rather than the capability boundary.

**Defects / debt**

- exact current head is Buildkite red.
- `STATUS.md` is dated 2026-08-18 and still presents the 66-repository rollout/wave framing as if it were current total progress.
- full-estate mass-recovery PR #197 is open, unmerged, and not mergeable against current main. Its 642-native-active census is therefore stranded branch evidence, not current runtime truth.
- direct pushes can bypass Buildkite because primary branch protection is absent.
- old open PRs create shadow state and need donor/supersession classification.

**Disposition:** strongest control/intelligence plane. Do not rebuild or shrink it. Repair exact head, protect main, refresh current status/estate receipt.

### 2. `GlacierEQ/job-app` — KEEP, elevate from hidden backstage to official execution plane

The current repository is no longer a document-only folder. Current source includes `tools/application_execution_engine.py`, repository tests, and a private-flight-deck workflow.

The integrated runtime composes `ApplicationFlightDeck` with `ApplicationIntegrityLedger`:

- lifecycle and integrity state advance together;
- prior event-chain integrity is checked before mutation;
- JSON state rolls back if integrity persistence fails;
- exact source/opening/package/receipt semantics remain fail-closed;
- later states require external receipts;
- external submission is not inferred.

The current APEX blueprint independently records 5/5 integration tests on reconstructed exact source, while hosted Actions failures were correctly not promoted as passing evidence.

**Defects / debt**

- README still says the repo exposes no repository-wide executable test suite, which is stale.
- hosted CI remains unresolved/weak as a current proof surface.
- open PRs #3/#4/#7 are shadow lineage relative to stronger current master.
- primary branch is unprotected.
- topology docs understate this repository's actual current execution role.

**Disposition:** active private execution authority. Keep separate from Helix and Resume Shapeshifter, but define explicit machine handoffs among all three.

### 3. `GlacierEQ/JOB-RESUME-BUILDER-` — KEEP as product flagship

The repository is a real truth-constrained application compiler, not a historical resume toy:

- source resume and JD parsing;
- fit/gap analysis;
- model proposals treated as untrusted input;
- deterministic truth checks;
- source-identity materialization;
- human side-by-side approval;
- ATS text, auditable JSON, printable HTML;
- IndexedDB private run lifecycle with revision/stale-write protection;
- exact Helix application-intelligence synchronization on a shared pinned revision.

Prior exact-head verification covered deterministic tests, lint, Helix evidence resolution, and Next.js production build.

**Defects / debt**

- production deployment unverified;
- browser E2E unverified;
- production identity/access, server retention, rate limiting, abuse protection, observability unverified;
- open PR #9 is lineage/shadow state relative to later default-branch commits;
- branch unprotected.

**Disposition:** retain as a separate transformation/product plane. Integrate contracts with `job-app`; do not merge its product responsibilities into Helix.

### 4. `GlacierEQ/job-application` — KEEP architecture, P0 repair distribution plane

The source repository contains strong mechanisms developed through recruiter-intelligence waves:

- role-specific recruiter proof matrix;
- freshness-aware proof briefs;
- recovery/gap/action packets;
- workflow topology and sealed deployment machinery;
- public/private truth boundaries;
- company-specific compiler/projection routes.

But present operational state is poor:

1. newest production root is 404;
2. recruiter review and machine recruiter matrix routes are 404;
3. current source exposes a private microcode repository identity;
4. presentation validator repair is stranded in stale PR #244;
5. compiler still pins Helix commit `8345955b...` from 2026-08-09 instead of current Helix;
6. main is unprotected;
7. many old open recovery PRs remain after stronger mechanisms reached main.

**Disposition:** public distribution architecture remains valuable, but operational grade is red until exact-source build, redaction, deployment, and readback are repaired.

## 66-repository recruiter evidence projection

### Core/runtime/control group

- `AEON-777`
- `AKOS`
- `ECHO`
- `GlacierEQ_Swarm`
- `JOB-RESUME-BUILDER-`
- `Pro-comet-agent`
- `apex-cli`
- `apex-control-plane`
- `glaciereq-mcp-stack`
- `grokodile`
- `job-application`
- `mastermind`
- `openclaw`
- `pro-code`
- `sigma-glue`
- `spiral-engine`
- `tasklet-micro-agent-engine`
- `the-tower-of-babel`
- `token_saver`

**Audit:** active and strategically useful as proof/runtime donors, but current exact-head verification is heterogeneous. Several changed after the 2026-08-16 audit, so that audit cannot certify their current heads. `mastermind` remains quarantined for recruiter admission until the conflicting registries are reconciled.

### Anthropic / agentic / browser / product group

- `anthropic-agent-coordinator`
- `anthropic-safety-monitor`
- `comet-browser-agent-bridge`
- `lovable-design-app-synth`
- `manus-autonomous-web-agent`
- `opera-neon-spatial-workspace`

**Audit:** admitted recruiter evidence candidates. Current exact-head green status was not comprehensively regenerated in this audit; treat August 16 evidence as baseline, not present-tense verification.

### Hardware / model / cloud / enterprise group

- `apple-ane-kv-quantizer`
- `aws-trainium-neuron-sentinel`
- `deepmind-tpu-mesh-optimizer`
- `deepseek-mla-moe-sentinel`
- `kimi-mooncake-kv-stream`
- `meta-llama-collective-sentinel`
- `microsoft-azure-ops`
- `microsoft-identity-zero-trust`
- `nvidia-deep-reasoning`
- `nvidia-gpu-health`
- `openai-reasoning-kv-sentinel`
- `qwen-vl-flash-router`
- `robotics-vla-torque-sentinel`
- `tesla-fsd-occupancy-stream`

**Audit:** admitted company/technical evidence family. Needs a refreshed generated verification registry against current default-branch heads before recruiter freshness scores can be considered current.

### Notion / workflow group

- `notion-mcp-empowerment-engine`
- `notion-workflow-intelligence`
- `notion-workspace-optimizer`

**Audit:** supporting workflow evidence. Keep as exhibits, not application authority.

### SpaceX family

- `spacex-autonomy`
- `spacex-conjunction-sentinel`
- `spacex-cryogenics`
- `spacex-ground-network`
- `spacex-launch-sequencer`
- `spacex-mission-control`
- `spacex-orbital-mechanics`
- `spacex-pad-weather-gate`
- `spacex-propulsion-monitor`
- `spacex-satellite-mesh`
- `spacex-telemetry`
- `spacex-thermal-protection`

**Audit:** high-value company-aligned proof family, but Helix STATUS still marks Wave 2 pending and the 2026-08-16 audit specifically identified neutralization pressure on orbital/launch/pad/propulsion/telemetry. Keep the family; refresh exact-head proof and company projection before strong current recruiter claims.

### xAI / Colossus family

- `colossus-gateway`
- `colossus-training-flux`
- `xai-colossus-2`
- `xai-colossus-cooling`
- `xai-colossus-cooling-alpha`
- `xai-colossus-cooling-omega`
- `xai-colossus-energy`
- `xai-colossus-energy-alpha`
- `xai-colossus-energy-omega`
- `xai-colossus-nanosphere`
- `xai-colossus-security`
- `xai-colossus-servers`

**Audit:** strongest bounded company-family proof in the current public portfolio. Existing projections record substantial test evidence while correctly limiting hardware/production claims. The current `job-application` privacy defect involving the private microcode repository must be fixed before this family is safely re-projected publicly.

## Outside-rollout current support repositories

### `GlacierEQ/monolith`

Keep as private catalog, provenance, and company-track mapping layer. It proves the public 66 are not the whole application estate and records private direct-named company candidates. It currently contains conflicting promotion classifications for `mastermind`, so its ledgers require reconciliation before machine promotion decisions consume them.

### `GlacierEQ/Pro_Code`

Keep as private operator doctrine/validator support. It is not application lifecycle authority and should not leak into recruiter/public state.

### `GlacierEQ/megaminds-pdf`

Keep as a verified focused PDF-viewer exhibit. Demote its architectural description from "foundation PDF surface" to **portfolio evidence satellite** unless a real application-document contract is implemented. Its current README explicitly limits it to one bundled document and no backend/OCR/AI/application ingestion.

### `GlacierEQ/glaciereq-excellence-core`

Keep as shared APEX objective/utility infrastructure. It belongs in control dependency mapping, not the recruiter child count.

## Historical / excluded discoveries

### `GlacierEQ/portfolio-organization-master`

Preserve for provenance only. Its own current README identifies it as a December 2025 historical snapshot and defers current hiring authority to Helix/job-application.

### `cherry-resume`, `cherry-portfolio`

Discovered by repository-name search but empty/unrelated to the current Casey hiring estate based on available evidence. Excluded from the active count.

### General interview/learning repositories

Name/content search can surface broad learning repositories such as `awesome-generative-ai-guide`. They are not admitted to the application estate without an explicit machine relationship or application/proof role.

## Cross-estate structural defects

### 1. Branch protection gap

All four application planes allow their primary branch to advance without required CI status checks. This is the strongest shared reliability defect found.

### 2. Verification freshness fragmentation

The 2026-08-16 68-row audit proved presence and source/test hints, not current exact-head health. Many repositories changed afterward. Current recruiter projection needs a generated exact-head verification registry rather than narrative inheritance.

### 3. Projection lag

`job-application` pins an August 9 Helix commit while current Helix is August 21. Deterministic pinning is correct; failure to advance the pin after verified source evolution is not.

### 4. Documentation/state drift

- Helix STATUS is stale.
- `job-app` README understates its executable runtime/test state.
- Monolith promotion ledgers conflict on Mastermind.
- project-control `canonical` terminology remains across direct job-system docs/projections even after the APEX authority shift.

### 5. Shadow PR accumulation

Open PRs across all four planes include capabilities already superseded by stronger main-line implementations alongside genuinely useful donor branches. Required classification for every open PR:

- `CURRENTLY_REQUIRED`
- `UNIQUE_DONOR`
- `SUPERSEDED_BY_MAIN`
- `HISTORICAL_PROOF`
- `STALE_REPAIR_REBASE_REQUIRED`

Do not close or merge them in bulk without this classification.

## Winners vs. dead weight

### Winners / core keepers

- `job-app-helix`
- `job-app`
- `JOB-RESUME-BUILDER-`
- `job-application`
- `AKOS`
- `monolith`
- `the-tower-of-babel`
- `pro-code`
- `apex-control-plane`
- `glaciereq-excellence-core`

### Valuable satellites

- `Pro_Code`
- `megaminds-pdf`
- current 66 recruiter evidence children subject to refreshed verification
- company-specific SpaceX/xAI/AI-infrastructure families

### Quarantine / provenance only

- `mastermind` until promotion-ledger conflict is resolved and re-admission evidence exists
- `portfolio-organization-master` as historical snapshot
- obsolete PR branches after donor review

There is no support for deleting working source merely because it is not on the recruiter front door. "Not application authority" is not the same thing as "dead repository."

## Ranked execution sequence

### P0

1. **Restore `job-application` production:** fix/reapply PR #244's redaction/presentation delta on current main, build exact current source, deploy the intended bundle, verify `/`, `/recruiter-review/`, and machine recruiter JSON return expected 200 responses.
2. **Repair Helix Buildkite 923** without dropping the new opening-freshness capability.
3. **Protect all four application primary branches** with repository-specific required checks and explicit audited bypass semantics.

### P1

4. Advance `job-application`'s Helix pin from `8345955b...` to a newly proven Helix source identity, regenerate dependent projection receipts, deploy, read back.
5. Update topology contracts to show all four application planes and their ownership boundaries.
6. Refresh the full 66-repository exact-head verification registry and recompute recruiter freshness/role scores from receipts rather than the August 16 baseline.
7. Reconcile Monolith `mastermind` promotion conflict and regenerate private/public promotion ledgers.

### P2

8. Classify all open job-system PRs by required/donor/superseded/historical/rebase-required state and close only those conclusively displaced.
9. Refresh Helix STATUS and `job-app` README to current executable state.
10. Replace stale project-control `canonical` terminology with APEX wording where it is governance/status language; preserve technical uses where changing the term would alter domain semantics.

## Completion definition

The job-application estate should be considered coherent only when:

- each of the four application planes has an explicit non-overlapping ownership contract;
- primary branches cannot advance past required proof accidentally;
- Helix exact current head is green;
- the public deployment is bound to an exact source commit and live readback passes;
- private repository identities cannot enter public projections;
- the Helix pin/projection is current and receipt-bound;
- recruiter evidence freshness is generated from current child-repository proof;
- private application lifecycle/integrity state composes cleanly with resume transformation and Helix intelligence;
- historical and quarantined repositories cannot masquerade as current authority;
- open PR shadow state is classified rather than silently accumulating.

## Audit boundary

This audit inspected the current connected GitHub estate, live Helix manifests/receipts, current default-branch heads, branch protection metadata, current/open PR state, and live Vercel production behavior. It does **not** claim semantic line-by-line inspection of all 1,183 repositories or current exact-head CI execution for every one of the 66 recruiter children. Where current proof was not independently re-established, the report explicitly treats earlier receipts as baseline rather than present-tense verification.
