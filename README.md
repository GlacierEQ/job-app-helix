# Job-App Helix — Evidence-Bound Portfolio Control Plane

Job-App Helix turns a large engineering portfolio into a reviewable system: it decides whether a campaign is ready, verifies what the portfolio can actually prove, and renders one evidence record for recruiters, senior engineers, and AI toolchains.

**Current status:** `PARTIALLY VERIFIED`  
The README Mesh release passed its Python 3.11–3.13 CI matrix at commit `3a1f0c033bb18309cc8678f91541ae54a7400709`. The current 66-repository runtime surface is not fully verified; the portfolio audit reports verified, blocked, failed, and unverified scope separately.

## For recruiters and non-technical reviewers

### What this proves

I designed a portfolio control plane that does more than list projects. It separates attractive claims from executable evidence, models readiness as a deterministic decision, and makes related repositories understandable as one system without hiding their individual boundaries.

The work demonstrates:

- **systems architecture:** a canonical control plane coordinating 66 portfolio repositories;
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
| [`docs/README_OPTIMAL_IMPACT_FRAME.md`](docs/README_OPTIMAL_IMPACT_FRAME.md) | Recruiter → expert → AI documentation contract, including the language-fit gate. |
| [`src/job_app_helix/campaign.py`](src/job_app_helix/campaign.py) | Deterministic campaign decision engine with bounded refinement. |
| [`src/job_app_helix/readme_mesh.py`](src/job_app_helix/readme_mesh.py) | Evidence-bound README graph and Protobuf serialization. |
| [`tests/`](tests/) | Campaign, failure-path, manifest, rendering, and serialization tests. |
| `python -m pytest -q` | Repository-native test command. |

## For senior engineers and domain experts

### System boundary

Job-App Helix owns:

- campaign readiness decisions;
- repository identity and README Mesh topology;
- evidence references and deterministic serialization;
- portfolio audit semantics and scoped receipts;
- rendering of recruiter, expert, and AI views.

It does **not** prove that every connected repository builds, deploys, performs, or operates correctly. Those claims require repo-native CI or provider-backed receipts. Hash coverage proves inventory integrity, not runtime function.

### Architecture

```text
Repository manifests + evidence paths
                 │
                 ▼
      Manifest validation layer
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
       scoped receipts and audit output
```

### Core components

| Component | Responsibility |
|---|---|
| [`campaign.py`](src/job_app_helix/campaign.py) | Runs deterministic flight, propulsion, and ground assessment/refinement stages. |
| [`pistons.py`](src/job_app_helix/pistons.py) | Encapsulates bounded stage-specific decision logic. |
| [`models.py`](src/job_app_helix/models.py) | Defines typed reports, findings, policies, and decisions. |
| [`readme_mesh_manifest.py`](src/job_app_helix/readme_mesh_manifest.py) | Loads and validates repository identity, evidence, and typed edges. |
| [`readme_mesh.py`](src/job_app_helix/readme_mesh.py) | Renders audience views and deterministic Protobuf/ProtoJSON/text outputs. |
| [`ci_audit_portfolio.py`](ci_audit_portfolio.py) | Audits workspace integrity and mesh health, executes an explicit runtime sample, and writes a scope-bound receipt. |
| [`apex_highway.py`](apex_highway.py) | Scans portfolio-sidecar metadata and mesh health. |

### Correctness and failure behavior

- Campaign decisions fail closed when a hard requirement remains unsatisfied.
- Refinement is bounded to one transparent stroke rather than open-ended mutation.
- README records must include stable identity, evidence, and typed relationships.
- Protobuf bindings are compiled and descriptor-compared in CI.
- Serialization is deterministic and round-tripped.
- Missing workspace repositories, missing integrity manifests, failed sample tests, unhealthy mesh state, failed demo execution, and broken local catalog links stop the local portfolio audit.
- `UNVERIFIED` and `BLOCKED` are preserved as states; they are never rewritten as `PASSED`.

### Verification commands

```bash
# Install development dependencies
uv pip install -e ".[dev]"

# Lint
python -m ruff check .

# Type check
python -m mypy src/job_app_helix/

# Test package, campaign states, README mesh, and failure paths
python -m pytest -q

# Run the canonical campaign scenario
python -c "from job_app_helix.campaign import LaunchScenario, run_campaign; print(run_campaign(LaunchScenario.nominal()))"

# Validate and build the README Mesh
job-app-helix-readme --manifest manifests/readme_mesh.json validate
job-app-helix-readme --manifest manifests/readme_mesh.json build --output-dir artifacts/readme_mesh

# Run the local multi-repository audit from the canonical workspace
python ci_audit_portfolio.py
```

The final command requires the local `repos/` workspace. Its receipt names the repositories actually executed; it does not certify all discovered repositories.

### Language choice

| Language/format | Responsibility | Why it fits |
|---|---|---|
| Python 3.11+ | campaign logic, validation, rendering, CLI, audit orchestration | Fast iteration, strong test ecosystem, readable decision logic, and mature Protobuf tooling. |
| Protocol Buffers | versioned repository identity and graph serialization | Cross-language deterministic contract for AI and toolchain ingestion. |
| JSON | human-inspectable manifests and receipts | Broad interoperability and straightforward validation. |
| Markdown | recruiter and engineering review surface | Openable, diffable, and native to repository workflows. |

This repository deliberately remains focused rather than adding languages for display. Polyglot work belongs at a boundary where the language materially improves correctness, performance, safety, interoperability, or deployment.

### Current limitations

- Runtime verification is incomplete across the 66-repository portfolio.
- README Mesh v1 has a verified rollout receipt for 21 declared nodes, not all 66.
- Connected repositories still need repo-native build/test receipts.
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
  and recruiter/expert/AI views of connected repositories.
status:
  state: PARTIALLY_VERIFIED
  verified_release: 3a1f0c033bb18309cc8678f91541ae54a7400709
  verified_scope:
    - Python 3.11, 3.12, and 3.13 package matrix at the README Mesh release
    - Protobuf compilation and descriptor comparison
    - manifest validation and deterministic serialization
    - README rendering and idempotency
    - campaign nominal, recoverable, and fail-closed scenarios
  unverified_scope:
    - current runtime behavior of every connected repository
    - portfolio-wide deployment, hardware execution, scale, and performance
interfaces:
  inputs:
    - manifests/readme_mesh.json
    - repository source, tests, workflows, and receipts
    - campaign scenarios and policy
  outputs:
    - campaign decision reports
    - rendered three-audience README blocks
    - deterministic Protobuf, ProtoJSON, textproto, and SHA-256 artifacts
    - scoped portfolio audit receipt
  commands:
    install: uv pip install -e ".[dev]"
    test: python -m pytest -q
    verify_mesh: job-app-helix-readme --manifest manifests/readme_mesh.json validate
    build_mesh: job-app-helix-readme --manifest manifests/readme_mesh.json build --output-dir artifacts/readme_mesh
    local_portfolio_audit: python ci_audit_portfolio.py
evidence:
  source:
    - src/job_app_helix/campaign.py
    - src/job_app_helix/readme_mesh.py
    - src/job_app_helix/readme_mesh_manifest.py
  tests:
    - tests/
  workflows:
    - .github/workflows/ci.yml
  audits:
    - docs/PORTFOLIO_EVIDENCE_AUDIT_2026-07-29.md
    - docs/README_MESH_ROLLOUT_2026-07-28.md
```

The compiled wire contract remains `glaciereq.readme.v1`; `glaciereq.readme-impact.v2-draft` names the expanded documentation profile only.

### Typed portfolio relationships

| Repository/family | Relation | Combined value |
|---|---|---|
| [`GlacierEQ/AKOS`](https://github.com/GlacierEQ/AKOS) | `governed_by` | AKOS supplies authority, provenance, maturity, and completion semantics; Helix renders and verifies the portfolio representation. |
| [`GlacierEQ/the-tower-of-babel`](https://github.com/GlacierEQ/the-tower-of-babel) | `evaluates_language_fit_for` | Tower proves whether a language owns a justified boundary; Helix records the evidence and verification state. |
| SpaceX subsystem family | `orchestrates` | Independent simulation, control, network, telemetry, and mission components become a reviewable systems-engineering surface. |
| xAI Alpha/Omega family | `represents` | Stateless requirement computation and stateful response remain distinct, typed responsibilities. |
| Agent coordinator + safety monitor | `connects` | Motion and independent oversight are presented as separate, composable boundaries. |

Canonical schema: [`proto/readme_mesh.proto`](proto/readme_mesh.proto)  
Canonical manifest: [`manifests/readme_mesh.json`](manifests/readme_mesh.json)

## Repository map

```text
src/job_app_helix/          package and CLI
proto/                      versioned README Mesh contract
manifests/                  canonical repository graph
schemas/                    validation contracts
rendered/                   generated audience views
artifacts/                  deterministic exports and audit receipts
tests/                      unit, contract, failure, and idempotency tests
docs/                       architecture, audits, standards, and rollout receipts
helix/                      BrainSync skill-index audit and repair tooling
showcase/                   bounded demonstration runner
hire_package/               application artifacts and outreach staging
```

## License

MIT — see [`LICENSE`](LICENSE).
