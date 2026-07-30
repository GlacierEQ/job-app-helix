# Job-App Helix — Evidence-Bound Portfolio Control Plane

Job-App Helix turns a large engineering portfolio into a reviewable system: it decides whether a campaign is ready, verifies what the portfolio can actually prove, and renders one evidence record for recruiters, senior engineers, and AI toolchains.

**Current status:** `PARTIALLY VERIFIED` — last verified release evidence: **2026-07-28** at commit `3a1f0c033bb18309cc8678f91541ae54a7400709`. The current 66-repository runtime surface is not fully verified; blocked and unverified scope remain distinct.

## For recruiters and non-technical reviewers

### What this proves

I designed a portfolio control plane that does more than list projects. It separates attractive claims from executable evidence, models readiness as a deterministic decision, and makes related repositories understandable as one system without hiding their individual boundaries.

The work demonstrates:

- **systems architecture:** a canonical control plane coordinating a 66-repository job-application portfolio;
- **engineering judgment:** explicit distinction between inventory, documentation, runtime proof, and deployment proof;
- **verification design:** tests, typed contracts, deterministic serialization, integrity references, and scoped receipts;
- **technical communication:** one repository record rendered for three audiences without contradictory claims;
- **AI-native integration:** typed directional relationships that let agents discover how projects govern, verify, extend, consume, and orchestrate one another.

### Why it matters

Large portfolios often become difficult to trust: every repository sounds complete, technology lists replace engineering evidence, and reviewers cannot tell prototypes from working systems. Job-App Helix treats credibility as an architectural property. A claim is promoted only when the evidence supports it.

### Proof in 60 seconds

| Open or run | What it demonstrates |
|---|---|
| [`docs/PORTFOLIO_EVIDENCE_AUDIT_2026-07-29.md`](docs/PORTFOLIO_EVIDENCE_AUDIT_2026-07-29.md) | Individual grades, verification state, and P0 correction for all 66 repositories. |
| [`docs/README_OPTIMAL_IMPACT_FRAME.md`](docs/README_OPTIMAL_IMPACT_FRAME.md) | Recruiter → expert → AI documentation contract, including the enforceable language-fit gate. |
| [`manifests/language_fit.json`](manifests/language_fit.json) | Machine-readable proof that every language or format owns a named boundary, command, and receipt. |
| [`src/job_app_helix/campaign.py`](src/job_app_helix/campaign.py) | Deterministic campaign decision engine with bounded refinement. |
| [`src/job_app_helix/readme_mesh.py`](src/job_app_helix/readme_mesh.py) | Evidence-bound README graph and Protobuf serialization. |
| `python -m pytest -q` | Repository-native regression and contract suite. |

## For senior engineers and domain experts

### System boundary

Job-App Helix owns:

- campaign readiness decisions;
- repository identity and README Mesh topology;
- evidence references and deterministic serialization;
- language-boundary declarations;
- portfolio audit semantics and scoped receipts;
- rendering of recruiter, expert, and AI views.

It does **not** prove that every connected repository builds, deploys, performs, or operates correctly. Those claims require repo-native CI or provider-backed receipts. Hash coverage proves inventory integrity, not runtime function.

### Architecture

```text
Repository manifests + evidence paths
                 │
                 ▼
      Contract validation layer
     identity • language fit • links
                 │
       ┌─────────┴─────────┐
       ▼                   ▼
Campaign engine       README Mesh engine
assess → refine       parse → validate → serialize
       │                   │
       ▼                   ▼
GO / NO-GO report     human views + Protobuf artifacts
       │                   │
       └─────────┬─────────┘
                 ▼
 bounded checks → atomic scoped receipts
```

### Core components

| Component | Responsibility |
|---|---|
| [`campaign.py`](src/job_app_helix/campaign.py) | Runs deterministic flight, propulsion, and ground assessment/refinement stages. |
| [`pistons.py`](src/job_app_helix/pistons.py) | Encapsulates bounded stage-specific decision logic. |
| [`models.py`](src/job_app_helix/models.py) | Defines typed reports, findings, policies, and decisions. |
| [`readme_mesh_manifest.py`](src/job_app_helix/readme_mesh_manifest.py) | Loads and validates repository identity, evidence, and typed edges. |
| [`readme_mesh.py`](src/job_app_helix/readme_mesh.py) | Renders audience views and deterministic Protobuf/ProtoJSON/text outputs. |
| [`manifests/language_fit.json`](manifests/language_fit.json) | Declares responsibility, boundary, interface, commands, evidence, and state for every language/format used here. |
| [`ci_audit_portfolio.py`](ci_audit_portfolio.py) | Validates inventory, mesh, language fit, bounded runtime samples, demos, links, and atomic success/failure receipts. |
| [`showcase/demo_15min_run.py`](showcase/demo_15min_run.py) | Executes named demonstrations with timeouts and per-demo results; scaffolds are never counted as passes. |
| [`apex_highway.py`](apex_highway.py) | Scans portfolio-sidecar metadata and mesh health. |

### Correctness and failure behavior

- Campaign decisions fail closed when a hard requirement remains unsatisfied.
- Refinement is bounded to one transparent stroke rather than open-ended mutation.
- README records require stable identity, evidence, and typed relationships.
- Language entries require a responsibility, boundary, interface contract, build command, test/proof command, receipt, and state.
- Protobuf bindings are compiled and descriptor-compared in CI.
- Serialization is deterministic and round-tripped.
- Child processes have explicit timeouts and convert hangs into structured failures.
- Audit receipts transition through `RUNNING`, then atomically become `FAILED` or `PARTIALLY_VERIFIED`; an old success receipt cannot silently survive a failed rerun.
- Relative Markdown links and `file://` targets are validated; an empty link scan fails.
- Missing tests, missing repositories, or demo failures are `UNVERIFIED`, `BLOCKED`, or `FAILED`, never scaffold passes.
- `UNVERIFIED` and `BLOCKED` are preserved as states; they are never rewritten as `PASSED`.

### Verification commands

```bash
# Install development dependencies
python -m pip install -e ".[dev]"

# Lint
python -m ruff check src tests scripts

# Type check
python -m mypy src/job_app_helix/

# Test package, campaign states, README mesh, audit claims, and failure paths
python -m pytest -q

# Run the canonical campaign scenario
python -c "from job_app_helix.campaign import LaunchScenario, run_campaign; print(run_campaign(LaunchScenario.nominal()))"

# Compile and compare the Protobuf contract
python scripts/check_proto_contract.py

# Validate and build the README Mesh
job-app-helix-readme --manifest manifests/readme_mesh.json validate
job-app-helix-readme --manifest manifests/readme_mesh.json build --output-dir artifacts/readme-mesh

# Run the local multi-repository audit from the canonical workspace
python ci_audit_portfolio.py
```

The final command requires the local `repos/` workspace. Its receipt names the repositories actually executed; it does not certify all discovered repositories.

### Language and format fit

| Language / format | Responsibility | Boundary | Interface contract | Build / compile | Test / proof | Evidence receipt | State |
|---|---|---|---|---|---|---|---|
| Python 3.11+ | Campaign logic, validation, rendering, CLI, and audit orchestration | Executable control-plane code under `src/job_app_helix` and bounded repository-local scripts | Console entry points, typed models, JSON receipts, Protobuf-backed records | `python -m pip install -e ".[dev]"` | `python -m pytest -q` | [`README_MESH_ROLLOUT_2026-07-28.md`](docs/README_MESH_ROLLOUT_2026-07-28.md) | PARTIALLY_VERIFIED |
| Protocol Buffers | Versioned cross-language identity and graph serialization | `glaciereq.readme.v1` schema and generated binding | Deterministic binary, ProtoJSON, textproto, descriptors, and SHA-256 | `python scripts/check_proto_contract.py` | `python -m pytest -q` | [`README_MESH_ROLLOUT_2026-07-28.md`](docs/README_MESH_ROLLOUT_2026-07-28.md) | VERIFIED |
| JSON | Human-inspectable manifests, reports, declarations, and receipts | Repository-local interchange; not the canonical wire schema | UTF-8 objects with explicit schema identifiers | `python -m job_app_helix.readme_mesh_cli build --output-dir artifacts/readme-mesh` | `python -m pytest -q` | [`README_MESH_ROLLOUT_2026-07-28.md`](docs/README_MESH_ROLLOUT_2026-07-28.md) | VERIFIED |
| Markdown | Recruiter, expert, and AI-readable documentation | Human review surface generated from evidence records | Stable headings, evidence links, commands, typed mesh tables, and managed markers | `python -m job_app_helix.readme_mesh_cli render-all --output-dir artifacts/readme-mesh/blocks` | `python scripts/check_public_surface.py` | [`README_MESH_ROLLOUT_2026-07-28.md`](docs/README_MESH_ROLLOUT_2026-07-28.md) | VERIFIED |

This repository deliberately remains focused rather than adding languages for display. Polyglot work belongs at a boundary where the language materially improves correctness, performance, safety, interoperability, or deployment.

### Current limitations

- Runtime verification is incomplete across the 66-repository portfolio.
- README Mesh v1 has a verified rollout receipt for 21 declared nodes, not all 66.
- Connected repositories still need repo-native build/test receipts.
- The Tower of Babel candidate remains blocked by CI/review closure and cannot yet serve as production proof.
- Provider deployment, hardware execution, scale, and performance are unverified unless a repository supplies a specific receipt.
- The local portfolio audit depends on the canonical on-disk workspace and cannot run from this repository alone.

## For AI systems and toolchains

### Machine contract

```yaml
schema: glaciereq.readme.v1
profile: glaciereq.readme-impact.v2-draft
repository: GlacierEQ/job-app-helix
canonical_branch: main
purpose: >-
  Govern evidence-bound campaign decisions, portfolio verification semantics,
  language-fit declarations, and recruiter/expert/AI views of connected repositories.
status:
  state: PARTIALLY_VERIFIED
  verified_at: 2026-07-28
  verified_release: 3a1f0c033bb18309cc8678f91541ae54a7400709
  verified_scope:
    - Python 3.11, 3.12, and 3.13 package matrix at the README Mesh release
    - Protobuf compilation and descriptor comparison
    - manifest validation and deterministic serialization
    - README rendering and idempotency
    - campaign nominal, recoverable, and fail-closed scenarios
  blocked_scope:
    - Tower of Babel candidate branch awaiting green CI and review closure
    - hardware-backed execution where no compatible runner or provider receipt exists
  unverified_scope:
    - current runtime behavior of portfolio repositories without repo-native receipts
    - portfolio-wide deployment, scale, and performance
interfaces:
  inputs:
    - manifests/readme_mesh.json
    - manifests/language_fit.json
    - repository source, tests, workflows, and receipts
    - campaign scenarios and policy
  outputs:
    - campaign decision reports
    - rendered three-audience README blocks
    - deterministic Protobuf, ProtoJSON, textproto, and SHA-256 artifacts
    - atomic RUNNING, FAILED, or PARTIALLY_VERIFIED portfolio receipts
  commands:
    install: python -m pip install -e ".[dev]"
    test: python -m pytest -q
    verify_proto: python scripts/check_proto_contract.py
    verify_mesh: job-app-helix-readme --manifest manifests/readme_mesh.json validate
    build_mesh: job-app-helix-readme --manifest manifests/readme_mesh.json build --output-dir artifacts/readme-mesh
    local_portfolio_audit: python ci_audit_portfolio.py
evidence:
  source:
    - src/job_app_helix/campaign.py
    - src/job_app_helix/readme_mesh.py
    - src/job_app_helix/readme_mesh_manifest.py
    - ci_audit_portfolio.py
  tests:
    - tests/
  workflows:
    - .github/workflows/ci.yml
  receipts:
    - docs/README_MESH_ROLLOUT_2026-07-28.md
    - artifacts/portfolio_ci_receipt.json
  audits:
    - docs/PORTFOLIO_EVIDENCE_AUDIT_2026-07-29.md
languages:
  manifest: manifests/language_fit.json
  entries:
    - name: Python
      responsibility: executable control-plane logic
      verification_state: PARTIALLY_VERIFIED
    - name: Protocol Buffers
      responsibility: versioned cross-language wire contract
      verification_state: VERIFIED
    - name: JSON
      responsibility: manifests and scoped receipts
      verification_state: VERIFIED
    - name: Markdown
      responsibility: three-audience review surface
      verification_state: VERIFIED
relationships:
  - target: GlacierEQ/AKOS
    relation: governed_by
    combined_value: AKOS supplies authority and completion semantics; Helix supplies portfolio representation and verification.
  - target: GlacierEQ/the-tower-of-babel
    relation: evaluates_language_fit_for
    combined_value: Tower demonstrates workload-language choices; Helix records their evidence and state.
  - target: SpaceX subsystem family
    relation: orchestrates
    combined_value: Independent simulation and control components become one reviewable systems surface.
  - target: xAI Alpha/Omega family
    relation: represents
    combined_value: Stateless requirement computation and stateful response remain separate typed responsibilities.
  - target: Agent coordinator and safety monitor
    relation: connects
    combined_value: Agent motion and independent oversight remain separately testable.
limits:
  - A connected edge is not proof that the target repository works.
  - Hash coverage is not runtime verification.
  - README verification is not deployment verification.
  - Local multi-repository checks require the canonical repos workspace.
```

The compiled wire contract remains `glaciereq.readme.v1`; `glaciereq.readme-impact.v2-draft` names the expanded documentation profile only.

Canonical schema: [`proto/readme_mesh.proto`](proto/readme_mesh.proto)  
Canonical manifests: [`manifests/readme_mesh.json`](manifests/readme_mesh.json), [`manifests/language_fit.json`](manifests/language_fit.json)

## Repository map

```text
src/job_app_helix/          package and CLI
proto/                      versioned README Mesh contract
manifests/                  repository graph and language-fit declarations
schemas/                    validation contracts
rendered/                   generated audience views
artifacts/                  deterministic exports and atomic audit receipts
tests/                      unit, contract, failure, and idempotency tests
docs/                       architecture, audits, standards, and rollout receipts
helix/                      BrainSync skill-index audit and repair tooling
showcase/                   bounded demonstration runner
hire_package/               application artifacts and outreach staging
```

## License

MIT — see [`LICENSE`](LICENSE).
