# Job-App Helix — Evidence-Bound Portfolio Control Plane

> Turns a large engineering portfolio into a system that can be inspected, planned, tested, and trusted without flattening sixty-seven repositories into one oversized claim.

Job-App Helix is the governance and verification center of the GlacierEQ hiring portfolio. It maintains the exact repository boundary, decides what is ready for promotion, discovers each project's native proof path, executes bounded checks, and emits evidence records that humans and AI systems can read from the same source.

**Release:** `0.3.0`  
**Canonical branch:** `main`  
**Current posture:** `PARTIALLY_VERIFIED` — the Helix package and portfolio-program contract have repository-native TEST evidence; the connected sixty-six child repositories retain their own verified, blocked, failed, partially verified, or unverified states.

## The Portfolio Stops Bluffing Here

*Recruiter lens · the evidence signal in one minute*

<!-- Compatibility marker: ## For recruiters and non-technical reviewers -->

A large portfolio becomes weaker when every repository sounds finished, language count replaces engineering judgment, and a passing command is allowed to stand in for proof. Helix addresses that credibility problem as an architectural problem.

It does five things:

1. **Defines the boundary.** One control-plane root plus exactly sixty-six child repositories.
2. **Separates evidence levels.** Inventory, documentation, static analysis, build, test, integration, and deployment are distinct states.
3. **Finds the native proof path.** Python, Node.js, Rust, Go, Swift, Maven, Gradle, CMake, and .NET repositories receive stack-appropriate plans.
4. **Fails closed.** Missing tools, zero-test runs, timeouts, absent repositories, unsafe paths, and unauthorized build mutations do not become green evidence.
5. **Publishes one coherent record.** Recruiter views, engineering detail, deterministic artifacts, and AI relationships derive from the same manifests and receipts.

### The one-minute review

| Open or run | What it proves |
|---|---|
| [`docs/PORTFOLIO_EXECUTION_PROGRAM.md`](docs/PORTFOLIO_EXECUTION_PROGRAM.md) | The full operating model: evidence ladder, rollout waves, command planning, execution, receipts, and definition of done. |
| [`manifests/portfolio_repositories.json`](manifests/portfolio_repositories.json) | The exact live portfolio boundary: this root plus sixty-six workspace repositories. |
| [`manifests/portfolio_rollout.json`](manifests/portfolio_rollout.json) | The complete four-wave partition with targets and acceptance gates. |
| [`manifests/github_repository_curation_2026-07-31.json`](manifests/github_repository_curation_2026-07-31.json) | The dated admission, deferral, duplicate, private, fork, archive, and backup decisions from the GitHub sweep. |
| [`manifests/readme_mesh.json`](manifests/readme_mesh.json) | Typed repository identities, evidence references, and directional relationships. |
| [`manifests/language_fit.json`](manifests/language_fit.json) | The responsibility, boundary, command, receipt, and state for each language or format used here. |
| `job-app-helix-portfolio validate` | Proves that every child repository appears exactly once in the rollout program. |
| `python -m pytest -q` | Exercises campaign logic, portfolio contracts, evidence semantics, README Mesh behavior, and failure paths. |

### What is already real

- a deterministic campaign engine that produces reviewable `GO` or `NO-GO` decisions;
- an exact sixty-seven-repository inventory contract;
- a complete four-wave rollout partition for all sixty-six child repositories;
- stack-aware, non-shell command discovery;
- bounded execution with explicit timeouts and output tails;
- positive test-count enforcement rather than exit-code optimism;
- explicit authorization before workspace-mutating build commands run;
- atomic `RUNNING` to final-state receipts that cannot preserve stale success;
- a Protocol Buffers-backed README Mesh with deterministic serialization;
- recruiter, expert, and AI views derived from evidence-bearing records.

### July 31, 2026 boundary migration

`JOB-RESUME-BUILDER-` is the lead product flagship presented by `job-application`, but it was absent from the previous 66-repository Helix boundary. The live inventory now admits it as the sixty-sixth child and routes it through `wave-3-technical-exhibits`. Earlier 66-repository reports remain dated historical evidence; they are not rewritten to imply that the additional repository was part of their original scope.

### What Helix deliberately does not claim

- that every connected repository currently builds or passes tests;
- that public source proves production deployment;
- that hash coverage proves behavior;
- that one bounded runtime sample certifies the entire portfolio;
- that language diversity has value without a real architectural boundary;
- that a repository is complete because its README is polished.

## Inside the Evidence Engine

*Masters of the trade · architecture, failure semantics, and proof execution*

<!-- Compatibility marker: ## For senior engineers and domain experts -->

Helix operates as two coordinated systems.

```text
HIGH-LEVEL PROGRAM CONTROL
inventory → rollout policy → promotion / repair / consolidation / archive
                              │
                              ▼
LOW-LEVEL PROOF EXECUTION
stack discovery → command plan → bounded execution → atomic receipt
                              │
                              ▼
PORTFOLIO REPRESENTATION
campaign report + README views + Protobuf artifacts + typed repository mesh
```

### Evidence is monotonic

```text
INVENTORY
    ↓
DOCUMENTATION
    ↓
STATIC_ANALYSIS
    ↓
BUILD
    ↓
TEST
    ↓
INTEGRATION
    ↓
DEPLOYMENT
```

A repository cannot inherit a higher state from a lower artifact. A README proves documentation. A successful compiler proves a build boundary. A test runner must report a positive proof count before it can establish test evidence. Deployment requires deployment evidence.

### Program pipeline

```text
manifests/portfolio_repositories.json
            │ exact 66-child boundary
            ▼
manifests/portfolio_rollout.json
            │ complete wave partition and targets
            ▼
portfolio_contract.py
            │ schema, policy, enum, and partition validation
            ▼
portfolio_discovery.py
            │ README contract, stack detection, safe command planning
            ▼
portfolio_execution.py
            │ bounded non-shell execution and proof extraction
            ▼
RUNNING ───────────────► VERIFIED / PARTIALLY_VERIFIED
   │                     BLOCKED / UNVERIFIED / FAILED
   └──── atomic replacement; stale success cannot survive
```

### Rollout program

| Priority | Wave | Scope | Decision | Target |
|---:|---|---:|---|---|
| 1 | `wave-1-native-ci` | 20 repositories | Add repository-native CI, positive-count test receipts, and the optimal README contract | `TEST` |
| 2 | `wave-2-tower-repair` | 1 repository | Repair Tower of Babel until every advertised language boundary has executable proof | `TEST` plus build evidence |
| 3 | `wave-3-technical-exhibits` | 17 repositories | Promote the strongest unverified technical exhibits with native tests and reference-correctness evidence | `TEST` |
| 4 | `wave-4-consolidation` | 28 repositories | Complete, merge, package, or archive overlapping systems with explicit successor records | `DOCUMENTATION` decision |

The wave manifest exact-partitions all sixty-six children. Missing, duplicated, or unexpected repository declarations invalidate the program before any command executes.

### Core components

| Component | Responsibility |
|---|---|
| [`src/job_app_helix/campaign.py`](src/job_app_helix/campaign.py) | Runs deterministic flight, propulsion, and ground assessment/refinement stages. |
| [`src/job_app_helix/pistons.py`](src/job_app_helix/pistons.py) | Encapsulates bounded stage-specific decision logic. |
| [`src/job_app_helix/models.py`](src/job_app_helix/models.py) | Defines campaign reports, findings, policies, and decisions. |
| [`src/job_app_helix/portfolio_contract.py`](src/job_app_helix/portfolio_contract.py) | Validates exact inventory, rollout policy, evidence ladder, and wave partition. |
| [`src/job_app_helix/portfolio_discovery.py`](src/job_app_helix/portfolio_discovery.py) | Detects repository stacks, validates README structure, and builds deterministic command vectors. |
| [`src/job_app_helix/portfolio_execution.py`](src/job_app_helix/portfolio_execution.py) | Executes bounded commands without shell interpolation and produces proof-bearing receipts. |
| [`src/job_app_helix/portfolio_cli.py`](src/job_app_helix/portfolio_cli.py) | Exposes validate, render-program, plan, and execute workflows. |
| [`src/job_app_helix/readme_mesh_manifest.py`](src/job_app_helix/readme_mesh_manifest.py) | Loads and validates repository identity, evidence references, and typed edges. |
| [`src/job_app_helix/readme_mesh.py`](src/job_app_helix/readme_mesh.py) | Renders audience views and deterministic Protobuf, ProtoJSON, textproto, and hash artifacts. |
| [`ci_audit_portfolio.py`](ci_audit_portfolio.py) | Runs the scoped workspace audit and writes an atomic portfolio receipt. |
| [`scripts/check_public_surface.py`](scripts/check_public_surface.py) | Rejects machine-local links, forbidden generated trees, secret patterns, and broken relative links. |
| [`showcase/demo_15min_run.py`](showcase/demo_15min_run.py) | Executes bounded named demonstrations with timeouts and positive test-count requirements. |

### Stack-native planning

| Detected boundary | Planned evidence |
|---|---|
| Python | Bytecode compilation plus pytest or unittest with a positive test count |
| Node.js / TypeScript | Declared lint, typecheck, build, and test scripts through the repository lockfile runner |
| Rust | Formatting, Clippy with warnings denied, and positive-count tests |
| Go | `go vet` and package tests |
| Swift | `swift test` |
| Maven / Gradle | Native test lifecycle |
| CMake | Configure and build inside an isolated proof directory |
| .NET | `dotnet test` |

Languages are admitted because they own a responsibility or boundary—not because a larger language list looks impressive.

### Install and verify Helix itself

```bash
python -m pip install -e ".[dev]"
python -m ruff check src tests scripts ci_audit_portfolio.py showcase/demo_15min_run.py
python -m mypy src/job_app_helix/
python -m pytest -q
python scripts/check_proto_contract.py
python scripts/check_public_surface.py
```

### Validate and render the portfolio program

```bash
job-app-helix-portfolio validate

job-app-helix-portfolio render-program \
  --output artifacts/portfolio-rollout.md
```

### Discover proof commands without executing them

```bash
job-app-helix-portfolio plan \
  --workspace repos \
  --json-output artifacts/portfolio-plan.json \
  --markdown-output artifacts/portfolio-plan.md
```

### Execute one bounded verification wave

```bash
job-app-helix-portfolio execute \
  --workspace repos \
  --wave wave-1-native-ci \
  --receipt artifacts/wave-1-receipt.json
```

Build commands that modify a workspace remain blocked unless the operator has reviewed the plan and supplies `--allow-mutating`.

### Validate and build the README Mesh

```bash
job-app-helix-readme \
  --manifest manifests/readme_mesh.json \
  validate

job-app-helix-readme \
  --manifest manifests/readme_mesh.json \
  build \
  --output-dir artifacts/readme-mesh
```

### Failure semantics

| Condition | State or control |
|---|---|
| Repository directory is absent | `BLOCKED` |
| Required executable is absent | `BLOCKED` |
| Test process exits zero after running zero tests | `UNVERIFIED` |
| Required check exits nonzero | `FAILED` |
| Command exceeds its timeout | `FAILED` |
| Build would mutate the workspace without authorization | `BLOCKED` |
| README exposes a machine-local path | Contract failure |
| Inventory and rollout do not exact-partition the portfolio | Program failure before execution |
| A rerun fails after an older success | Atomic receipt is replaced with `FAILED`; stale success is not retained |

The aggregate receipt uses the strongest adverse state. Many passing repositories cannot average away one required failure.

### Repository layout

```text
src/job_app_helix/          campaign, portfolio, README Mesh, and CLI packages
proto/                      versioned README Mesh wire contract
manifests/                  exact inventory, rollout, graph, curation, and language-fit declarations
schemas/                    validation contracts
artifacts/                  deterministic exports and atomic receipts
rendered/                   generated audience views
tests/                      unit, contract, failure, and idempotency tests
docs/                       architecture, standards, audits, and rollout records
showcase/                   bounded demonstration runner
hire_package/               application and outreach staging
helix/                      supporting audit and repair tooling
```

## Enter Through the Manifests

*Machine contract · deterministic inventory, receipts, and typed relationships*

<!-- Compatibility marker: ## For AI systems and toolchains -->

AI systems should begin with the manifests and contract commands, not infer truth from repository prose.

```yaml
schema: glaciereq.readme.v1
profile: glaciereq.readme-impact.v2-draft
repository: GlacierEQ/job-app-helix
canonical_branch: main
package_version: 0.3.0
purpose: >-
  Govern evidence-bound campaign decisions, the exact portfolio inventory,
  rollout policy, repository-native proof planning, bounded execution,
  atomic receipts, language-fit declarations, and recruiter/expert/AI views.

status:
  state: PARTIALLY_VERIFIED
  verified_at: 2026-07-30
  verified_release: b0973cf621212621a23bf2d2032a816ab79eb78b
  verified_scope:
    - Python 3.11, 3.12, and 3.13 package CI at the named verified release
    - exact portfolio rollout contract validation
    - deterministic rollout-program rendering
    - campaign nominal, recoverable, and fail-closed scenarios
    - Protobuf compilation and descriptor comparison
    - README Mesh validation and deterministic serialization
    - public-surface and failure-path checks
  blocked_scope:
    - repository-native tools or build authorization unavailable to a selected wave
    - hardware-backed execution without a compatible runner or provider receipt
  unverified_scope:
    - child repositories without current repository-native receipts
    - portfolio-wide deployment, scale, performance, and operational reliability
    - the July 31 inventory migration until the migration pull request receives green CI and is merged

interfaces:
  inputs:
    - manifests/portfolio_repositories.json
    - manifests/portfolio_rollout.json
    - manifests/github_repository_curation_2026-07-31.json
    - manifests/readme_mesh.json
    - manifests/language_fit.json
    - repository source, build manifests, tests, workflows, and receipts
    - campaign scenarios and policy
  outputs:
    - deterministic campaign decision reports
    - portfolio rollout plans in JSON and Markdown
    - per-command and per-repository execution receipts
    - atomic aggregate portfolio receipts
    - rendered README audience views
    - deterministic Protobuf, ProtoJSON, textproto, descriptor, and SHA-256 artifacts
  commands:
    install: python -m pip install -e ".[dev]"
    test: python -m pytest -q
    validate_program: job-app-helix-portfolio validate
    render_program: job-app-helix-portfolio render-program --output artifacts/portfolio-rollout.md
    plan: job-app-helix-portfolio plan --workspace repos --json-output artifacts/portfolio-plan.json
    execute_wave: job-app-helix-portfolio execute --workspace repos --wave wave-1-native-ci --receipt artifacts/wave-1-receipt.json
    verify_proto: python scripts/check_proto_contract.py
    verify_mesh: job-app-helix-readme --manifest manifests/readme_mesh.json validate
    build_mesh: job-app-helix-readme --manifest manifests/readme_mesh.json build --output-dir artifacts/readme-mesh

policy:
  evidence_ladder:
    - INVENTORY
    - DOCUMENTATION
    - STATIC_ANALYSIS
    - BUILD
    - TEST
    - INTEGRATION
    - DEPLOYMENT
  fail_closed: true
  exact_inventory_partition: true
  positive_test_count_required: true
  shell_interpolation: forbidden
  workspace_mutation_requires_explicit_authorization: true
  receipts_are_atomic: true
  stale_success_survival: forbidden

languages:
  manifest: manifests/language_fit.json
  entries:
    - name: Python
      responsibility: campaign logic, validation, planning, execution, rendering, CLI, and audit orchestration
      verification_state: PARTIALLY_VERIFIED
    - name: Protocol Buffers
      responsibility: versioned cross-language repository identity and graph serialization
      verification_state: VERIFIED
    - name: JSON
      responsibility: inventories, rollout policy, deterministic plans, manifests, and receipts
      verification_state: VERIFIED
    - name: Markdown
      responsibility: recruiter, engineering, and machine-readable review surfaces
      verification_state: VERIFIED

relationships:
  - target: GlacierEQ/AKOS
    relation: GOVERNED_BY
    combined_value: AKOS supplies authority and completion semantics; Helix supplies portfolio representation and evidence promotion.
  - target: GlacierEQ/job-application
    relation: ORCHESTRATES
    combined_value: Helix governs the evidence boundary and machine entrypoint behind the public hiring portal.
  - target: GlacierEQ/JOB-RESUME-BUILDER-
    relation: ORCHESTRATES
    combined_value: Helix governs the lead public product flagship's evidence promotion and prevents the recruiter portal from outrunning repository-native proof.
  - target: GlacierEQ/spacex-telemetry
    relation: ORCHESTRATES
    combined_value: Ordered telemetry evidence becomes an explicit campaign-readiness input.
  - target: GlacierEQ/spacex-mission-control
    relation: ORCHESTRATES
    combined_value: Combined campaign state becomes a reviewable human-operator surface.
  - target: GlacierEQ/spacex-thermal-protection
    relation: ORCHESTRATES
    combined_value: Predictive thermal evidence and bounded response become part of the campaign decision.

limits:
  - A typed relationship is not proof that the target repository works.
  - Hash coverage is file-identity evidence, not runtime verification.
  - A zero-test process is not test evidence.
  - README quality is not deployment proof.
  - Local multi-repository execution requires the canonical repos workspace.
  - Provider, hardware, scale, and performance claims require specific external receipts.
```

### Canonical integration surfaces

- **Inventory:** [`manifests/portfolio_repositories.json`](manifests/portfolio_repositories.json)
- **Rollout:** [`manifests/portfolio_rollout.json`](manifests/portfolio_rollout.json)
- **GitHub curation ledger:** [`manifests/github_repository_curation_2026-07-31.json`](manifests/github_repository_curation_2026-07-31.json)
- **Repository graph:** [`manifests/readme_mesh.json`](manifests/readme_mesh.json)
- **Language fit:** [`manifests/language_fit.json`](manifests/language_fit.json)
- **Wire schema:** [`proto/readme_mesh.proto`](proto/readme_mesh.proto)
- **Program guide:** [`docs/PORTFOLIO_EXECUTION_PROGRAM.md`](docs/PORTFOLIO_EXECUTION_PROGRAM.md)
- **Historical 66-repository evidence audit:** [`docs/PORTFOLIO_EVIDENCE_AUDIT_2026-07-29.md`](docs/PORTFOLIO_EVIDENCE_AUDIT_2026-07-29.md)
- **README standard:** [`docs/README_OPTIMAL_IMPACT_FRAME.md`](docs/README_OPTIMAL_IMPACT_FRAME.md)

### System mesh

```text
                              AKOS
                  authority • completion semantics
                                │
                                │ GOVERNED_BY
                                ▼
┌──────────────────────────────────────────────────────────────┐
│                        job-app-helix                         │
│ inventory • rollout • discovery • execution • receipts     │
│ campaign decisions • README Mesh • machine contracts       │
└───────────────┬──────────────────────┬───────────────────────┘
                │ ORCHESTRATES         │ ORCHESTRATES
                ▼                      ▼
        job-application         technical repository waves
        public hiring portal    native CI • repair • proof
                │
                │ PRESENTS
                ▼
       JOB-RESUME-BUILDER-
       Resume Shapeshifter
```

The control plane succeeds when the public story becomes easier to understand, the engineering proof becomes easier to reproduce, and an AI system can continue the work without inventing relationships, capabilities, or completion states.

## The Living Evidence Mesh

*System mesh · how Helix connects the hiring portfolio without collapsing repository boundaries*

Helix is the control plane, not a warehouse of copied projects. The canonical typed edges live in [`manifests/readme_mesh.json`](manifests/readme_mesh.json); this human map shows the combined value without pretending one repository owns another repository's proof.

```text
job-app-helix
├── governs the public signal      → job-application
├── promotes product evidence      → JOB-RESUME-BUILDER-
├── verifies bounded proof paths   → portfolio child repositories
└── preserves deliberate borders  → private operations + historical snapshots
```

A healthy mesh amplifies evidence while preserving provenance: no copied source trees, no inherited deployment claims, no private operational leakage, and no relationship without declared combined value.
