# PSYSOC-X Hiring-System Reconciliation

**Date:** 2026-08-03  
**Authority:** `GlacierEQ/job-app-helix`  
**Scope:** public recruiter portal, master résumé, Helix inventory and rollout, Crown Jewels, Infinity Stones, company-aligned repositories, private architecture references, upstream/reference repositories, and the deployed V12 Systems Atlas.

## Executive judgment

The hiring system is already unusually strong in architecture, truth boundaries, and presentation. Its main weakness is no longer a lack of ideas. It is **evidence synchronization and portfolio promotion discipline**:

- the deployed V12 website is ahead of the canonical `job-application` repository;
- the old `RESUME.md` materially overstated broad production and mastery claims while the live résumé used a stronger evidence-aware identity;
- Helix’s 67-repository inventory is broad, but the rollout manifest is stale and only a small subset has current-SHA behavioral receipts;
- several original personal systems are under-presented, especially ECHO and the newly implemented Sigma Glue slice;
- several visible repositories are upstream, mirrored, reference, or sample projects and must never become authorship evidence without an isolated contribution delta;
- company tracks are mostly inventoried correctly, but they need suite-level presentation, current verification, and one promoted flagship per company rather than a wall of similarly weighted repositories.

The governing correction is:

> **A strong claim is a target contract. Upgrade the implementation, tests, infrastructure, and receipts until the system earns it. Downgrade only claims that are technically false or indefensible.**

## Corrections completed during this reconciliation

- Replaced `GlacierEQ/job-application/RESUME.md` on the audit branch with one canonical PSYSOC-X master résumé.
  - Uses the live Vercel portfolio URL.
  - Removes blanket mastery, enterprise-scale, and production-grade assertions.
  - Adds stronger evidence-bound descriptions of the deployed portfolio, Helix, AKOS, Tower, Resume Shapeshifter, ECHO, and Sigma Glue.
  - Separates primary implementation languages from project/exhibit experience.
  - Preserves company alignment without implying affiliation or proprietary access.
- Rewrote `GlacierEQ/job-application/README.md` on the audit branch to reflect the deployed V12 architecture.
  - Documents the four routes.
  - Documents the live API and protocol surfaces.
  - Corrects the prior false state that production was unverified.
  - Adds partial-success, privacy, authority, and machine-ingestion boundaries.
  - Identifies canonical-source/deployment drift as the next release blocker.
- Added `manifests/portfolio_candidate_reconciliation_2026-08-03.json`.
  - Defines admission and flagship gates.
  - Classifies immediate candidates, promotion priorities, upstream/reference exclusions, private architecture references, and company-track gaps.
  - Prevents repository ownership from being mistaken for authorship.
  - Makes upgrade-to-claim the explicit promotion policy.

## What must happen next — ordered program

### P0 — make the hiring system internally canonical

- **Commit the complete V12 deployable website source to `GlacierEQ/job-application`.**
  - The public deployment, repository source, portfolio graph, serverless APIs, Protobuf schema, generated binary, and QA receipts must be reproducible from one Git commit.
  - Remove the current split where the live site is verified but the public repository still describes an earlier portal.
  - Add Git-triggered preview and production deployment.
  - Publish route, API, browser, mobile, accessibility, security-header, and protocol receipts per release.
  - Include the already validated PROTO//BOOT overflow repair: bounded graph viewport, wrapping control, copy/download controls, mobile containment, and long-token handling.

- **Make the new master résumé the only factual source.**
  - Generate ATS text, Markdown, PDF, and role-specific versions from the same structured résumé source.
  - Replace the stale GitHub Pages portfolio URL everywhere with the canonical Vercel URL.
  - Add regression tests that reject the retired overclaim phrases unless a current receipt is attached.
  - Add company-specific variants by changing emphasis, not facts.
  - Add a résumé claim ledger that maps each impact bullet to a repository, commit, evidence class, and expiration policy.

- **Rebuild Helix rollout around current-SHA evidence.**
  - The current rollout still carries historical commits and completion states.
  - Every promoted repository needs a fresh observation of canonical branch, current commit, source, tests, workflows, current workflow execution, security, README contract, and unresolved blockers.
  - Run the repository-health engine against every promoted node, not only synthetic fixtures and one AKOS observation.
  - Distinguish `INVENTORIED`, `SOURCE_REVIEWED`, `TEST_VERIFIED`, `DEPLOYMENT_VERIFIED`, and `ELITE_VERIFIED` directly in the public graph.

### P0 — complete the core Crown Jewels

- **AKOS**
  - Generate a fresh current-main Helix observation and attach actual workflow-run receipts.
  - Exercise one real connector through `INVOKED → RETURNED → VERIFIED → PERSISTED`.
  - Exercise one real artifact through `READY_FOR_USE`.
  - Publish one reversible authorized-write receipt.
  - Keep Infinity Stone and PSYSOC-X receipts bound to the exact current head.
  - Add cross-system contract tests against ECHO, Sigma Glue, Tower, and the website graph.

- **Tower of Babel**
  - Preserve the anti-theater evidence gate, but turn demoted frontier paths into executable promotion programs.
  - Add real JAX/XLA verification runners.
  - Add CUDA correctness and disclosed-hardware benchmark runners.
  - Add hardware-simulation or toolchain gates for HDL and accelerator exhibits.
  - Compare outputs against trusted references.
  - Activate and verify the repository main ruleset rather than only storing policy-as-code.
  - Automatically promote evidence states only when exact thresholds are met.
  - Keep unsupported paths blocked without removing the engineering target.

- **Resume Shapeshifter**
  - Add route-level integration tests for analysis, generation, malformed model output, missing credentials, upstream errors, and deterministic truthfulness rejection.
  - Add browser end-to-end tests.
  - Add downloadable DOCX/PDF output.
  - Add request-size controls, rate limiting, audit logs, observability, and abuse controls.
  - Define privacy, retention, deletion, and external-model disclosure policy.
  - Build a semantic evaluation corpus for supported and unsupported résumé claims.
  - Deploy preview and production instances and persist provider receipts.

- **ECHO**
  - Admit as a Crown Jewel candidate after current-SHA verification.
  - Pin GitHub Actions dependencies and create a positive-count receipt.
  - Verify managed PostgreSQL migrations, rollback, and SQLite fallback behavior.
  - Add authenticated write/read integration tests.
  - Test retry exhaustion, duplicate suppression, restart recovery, receipt tampering, and outage behavior.
  - Publish a deployment receipt and a bounded load/reliability profile.
  - Synchronize the README with the current security and persistence implementation.

- **Sigma Glue**
  - Upgrade from emerging flagship to verified federation component.
  - Synchronize the stale Draft-v1 README with the current reversible execution slice.
  - Add pinned read-only CI and package/install verification.
  - Persist a current-SHA 24-test receipt.
  - Add concurrency and multi-process idempotency tests.
  - Implement dynamic no-scope-broadening enforcement.
  - Exercise a live read-only Gatekeeper/Colossus adapter.
  - Add offline/resume and provider-reconciliation tests before mutation promotion.

- **Mastermind**
  - Do not promote the current repository as a finished control plane.
  - Inventory and cluster branch families by function.
  - Compare branches against current main and each other.
  - Preserve unique code before closure.
  - Extract canonical runnable modules.
  - Replace configured or simulated health with real bounded probes.
  - Rotate historically exposed credentials and document revocation.
  - Either produce one coherent verified runtime or preserve Mastermind honestly as a consolidation laboratory.

### P1 — present company tracks as systems, not link collections

- **Anthropic**
  - Public coverage is complete: Agent Coordinator and Safety Monitor.
  - Present them as one bounded coordination-and-safety track.
  - Refresh exact-head CI receipts.
  - Add concurrency, restart, adversarial, and distribution-shift tests.
  - Promote Agent Coordinator as the flagship and Safety Monitor as the supporting verified subsystem once current receipts pass.

- **SpaceX**
  - Public coverage is complete with twelve repositories, not ten.
  - Correct every stale count.
  - Present a single Mission Systems Suite with autonomy, telemetry, launch sequencing, orbital mechanics, mission control, ground network, satellite mesh, cryogenics, propulsion, weather, conjunction, and thermal-protection modules.
  - Promote `spacex-autonomy` or `spacex-telemetry` as the flagship only after native CI, scenario tests, fault injection, simulation-boundary documentation, and reproducible receipts.
  - Keep private recovery-dynamics and orbital-assembly repositories as private references.

- **xAI / Colossus**
  - Public coverage is broad, but presentation is fragmented.
  - Use `xai-colossus-cooling` as the flagship candidate.
  - Group energy, servers, and security as supporting infrastructure systems.
  - Group nanosphere, Colossus-2, and training-flux as experiments.
  - Convert alpha/omega repositories into release lines, branches, or historical comparisons rather than separate recruiter systems.
  - Add physical-unit checks, sensitivity analysis, reproducible fixtures, assumption ledgers, and benchmark boundaries.

- **NVIDIA**
  - Public coverage is complete with GPU Health and Deep Reasoning.
  - Both are currently thin exhibits, not flagships.
  - Add real CUDA or accelerator-toolchain integration, correctness references, disclosed hardware, health telemetry fixtures, fault injection, and benchmark receipts.
  - Consolidate private consensus, gradient-shield, and circuit-breaker ideas into the public track only after unique value is proven and sanitized.

- **Apple**
  - Public coverage contains ANE KV Quantizer; Apple MCP and Pro-iOS remain private.
  - Build an executable Swift/Metal/ANE path with deterministic correctness tests and device/hardware receipts.
  - Add Core ML or ANE fallback and capability reporting.
  - Keep private integrations private unless a public-safe original core is extracted.

- **OpenAI / Codex**
  - `openai-reasoning-kv-sentinel` is the admitted original exhibit.
  - Audit `openai-codex-mcp`, `project_openai_codex`, and `MCP-Bridge` for original contribution, overlap, security, tests, and current compatibility.
  - Exclude OpenAI SDK/framework mirrors from authorship evidence unless a separate contribution delta exists.
  - Treat `codex-supermemory` as upstream Supermemory integration, not a GlacierEQ flagship.
  - Connect original Codex/MCP work to AKOS authority, ECHO continuity, and Sigma federation only through tested contracts.

- **Google / DeepMind**
  - Public coverage contains TPU Mesh Optimizer.
  - Add XLA/HLO or simulator-based correctness, topology fixtures, failure cases, and measurable optimization evidence.
  - Private thin variants remain private until consolidated into one coherent public system.

- **Microsoft**
  - Public inventory currently includes Azure Ops and Identity Zero Trust.
  - Exclude Office Word MCP and Microsoft Build samples from authorship claims because their canonical sources are external.
  - Audit TextCraft and Browser Operator Core for original contribution and provenance.
  - Build a first-party public-safe Microsoft document workflow that integrates Word generation, evidence validation, and operator review.

- **AWS**
  - Public inventory includes Trainium/Neuron Sentinel.
  - Audit `products-suggestions-api` as a possible practical cloud product exhibit.
  - Publish only public-safe Cloud Institute work.
  - Add deployment, IAM-boundary, observability, cost, failure, and rollback receipts.

- **Tasklet**
  - Inventory is complete with one public repository.
  - Implement the real micro-agent runtime, typed task contract, bounded resources, deterministic scheduling, cancellation, timeout, retry, and receipt behavior.
  - Add positive-count tests and one end-to-end workload before promotion.

- **Meta and Tesla**
  - Existing sentinels are correctly included as technical exhibits.
  - Do not promote until current behavioral tests and domain-relevant measurements exist.

### P1 — correct the personal-system map

- **ECHO:** add after current-SHA verification; it is a genuine missing Crown Jewel candidate.
- **Sigma Glue:** add as `EMERGING_FLAGSHIP`, not production complete.
- **FILEBOSS:** retain as private architecture reference until a public-safe authority model, mock filesystem, schemas, tests, and receipts are extracted.
- **MEGA-PDF:** retain as private architecture reference; create a first-party public document-intelligence contract/exhibit rather than using upstream `megapdf-sdk` as proof.
- **Mastermind:** retain as consolidation-required until canonical runtime extraction.
- **AEON-777:** audit as a potential memory/evidence flagship and distinguish it clearly from ECHO.
- **Colossus Gateway:** audit as a possible federation/runtime supporting system.
- **Pro-Code:** audit current runtime value and relationship to Tower/AKOS rather than presenting it generically.
- **Spiral Engine:** determine whether it is an independent flagship or a Tower-owned subsystem; avoid double-counting.

### P2 — portfolio hygiene and stability

- Replace numeric portfolio-size prestige with verified-capability density.
- Keep the full inventory machine-accessible but show only promoted systems by default.
- Require every public card to expose:
  - canonical repository;
  - current commit;
  - evidence class;
  - latest verified commit;
  - test receipt;
  - deployment state;
  - known blocker;
  - promotion target;
  - relationship to other systems.
- Add a provenance scanner that classifies:
  - original;
  - substantially modified fork;
  - upstream mirror;
  - sample/reference;
  - generated;
  - private architecture;
  - duplicate/historical variant.
- Fail CI when upstream/reference repositories appear in Crown Jewels.
- Fail CI when public counts drift across README, résumé, website graph, inventory, rollout, or downloadable packets.
- Fail CI when a current claim points to an older commit without being labeled stale.
- Add dependency, secret, license, and large-binary scans to flagship promotion.
- Add deterministic application-packet generation from the master résumé and portfolio graph.

## Final desired state

A reviewer should be able to move through the system as follows:

```text
one tailored résumé
  → one role-calibrated portfolio URL
  → one curated company or capability journey
  → one internal system case study
  → current source, tests, receipts, limitations, and promotion target
  → raw repository inventory only when desired
```

The portfolio succeeds when every strong statement has a matching implementation contract, every implementation has executable proof, every proof is current, and every audience can understand the value without being asked to interpret a wall of repositories.
