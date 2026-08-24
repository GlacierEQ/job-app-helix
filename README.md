# Job-App Helix — Evidence-Bound Employment Intelligence & Execution Engine

> **APEX job-ecosystem restoration is active.**
> Program: [`docs/apex/JOB_ECOSYSTEM_RESTORATION_PROGRAM.md`](docs/apex/JOB_ECOSYSTEM_RESTORATION_PROGRAM.md) · Status: [`STATUS.md`](STATUS.md)

Job-App Helix turns portfolio evidence, target-company intelligence, application state, recruiter presentation, and capability restoration into one inspectable employment system. Its job is to help produce stronger real-world hiring outcomes without flattening repository-native truth, inventing completion, or allowing a registry, receipt, projection, CI workflow, donor system, or AI agent to become project-direction authority.

**Package:** `job-app-helix`  
**Version:** `0.3.0`  
**APEX source branch:** `main`  
**Primary Operator:** Casey Barton  
**Current posture:** evidence-bound coordination, application execution, portfolio intelligence, restoration, innovation, and recruiter projection.

## Authority boundary

Helix is a **coordination and execution plane**, not an estate ruler.

- Casey Barton controls project direction, intended scope, priorities, architecture targets, and final project decisions.
- Each child repository remains authoritative for its own source, tests, receipts, releases, and factual runtime state.
- Helix may observe, compile, rank, verify, project, restore, and coordinate evidence.
- Helix may not redefine a peer repository's purpose merely because that repository appears in an inventory, graph, promotion state, or generated surface.
- AKOS, Tower, Monolith, registries, schemas, receipts, workflows, and other systems may provide scoped capabilities or evidence. Their existence does not create project-direction authority.

The active machine boundary is encoded in [`manifests/portfolio_root_truth.json`](manifests/portfolio_root_truth.json), [`manifests/readme_mesh.json`](manifests/readme_mesh.json), and [`agents.md`](agents.md).

## What Helix actually contains

| Capability | Current source surface | What it is for |
|---|---|---|
| Application outcome engine | [`src/job_app_helix/application_operations.py`](src/job_app_helix/application_operations.py), [`src/job_app_helix/campaign.py`](src/job_app_helix/campaign.py) | Prepare and advance evidence-bound application work without fabricating submission state. |
| Portfolio contract | [`src/job_app_helix/portfolio_contract.py`](src/job_app_helix/portfolio_contract.py) | Validate admitted inventory, rollout state, evidence levels, and partition invariants. |
| Native proof discovery | [`src/job_app_helix/portfolio_discovery.py`](src/job_app_helix/portfolio_discovery.py) | Detect repository stacks and produce stack-appropriate proof plans. |
| Bounded proof execution | [`src/job_app_helix/portfolio_execution.py`](src/job_app_helix/portfolio_execution.py) | Execute bounded non-shell checks with timeouts, explicit mutation authorization, and atomic evidence state. |
| Portfolio CLI | [`src/job_app_helix/portfolio_cli.py`](src/job_app_helix/portfolio_cli.py) | Validate, plan, render, and execute portfolio work. |
| Evidence and projection root | [`manifests/portfolio_root_truth.json`](manifests/portfolio_root_truth.json) | Coordinate source identities, evidence state, company alignment, public/private boundaries, and downstream projections without acquiring project authority. |
| README evidence mesh | [`src/job_app_helix/readme_mesh.py`](src/job_app_helix/readme_mesh.py), [`src/job_app_helix/readme_mesh_manifest.py`](src/job_app_helix/readme_mesh_manifest.py) | Render recruiter, expert, and machine-readable relationships while rejecting retired governor semantics. |
| Genius Engine | [`src/job_app_helix/genius_engine.py`](src/job_app_helix/genius_engine.py) | Invent, attack, rank, and advance candidate improvements under maximum coherent advance. |
| Capability archaeology | [`src/job_app_helix/capability_archaeology.py`](src/job_app_helix/capability_archaeology.py) | Find exact historical capability instead of guessing what was lost. |
| Surgical symbol restoration | [`src/job_app_helix/symbol_restoration.py`](src/job_app_helix/symbol_restoration.py) | Restore historical Python symbols without replacing later gains wholesale. |
| Cross-file restoration | [`src/job_app_helix/cross_file_restoration.py`](src/job_app_helix/cross_file_restoration.py) | Restore dependency closure across multiple source files with drift protection. |
| Federated restoration | [`src/job_app_helix/federated_restoration.py`](src/job_app_helix/federated_restoration.py) | Recover exact donor capability across repository boundaries with lineage evidence. |
| Reversible restoration executor | [`src/job_app_helix/restoration_executor.py`](src/job_app_helix/restoration_executor.py) | Apply targeted restoration packets with preflight, validation, receipts, and rollback. |
| Restoration CLI | [`src/job_app_helix/restoration_cli.py`](src/job_app_helix/restoration_cli.py) | Expose archaeology and restoration as executable operator workflows. |
| Recruiter site compiler | [`scripts/build_recruiter_site.py`](scripts/build_recruiter_site.py) | Compile public-safe evidence into the recruiter-facing surface. |
| Final-form package compiler | [`scripts/build_final_form_package.py`](scripts/build_final_form_package.py) | Produce deterministic recruiter/application packages from evidence-bound inputs. |
| Candidate machine surface | [`hire_package/casey-barton/candidate_node.json`](hire_package/casey-barton/candidate_node.json) | Provide an AI-readable candidate representation without donor-system authority inheritance. |

## The employment loop

```text
TARGET COMPANY / ROLE
        │
        ▼
company + role intelligence
        │
        ▼
portfolio / capability evidence
        │
        ├──────────────► capability gap discovered
        │                         │
        │                         ▼
        │              Genius + restoration engines
        │                         │
        │                         ▼
        │                stronger verified system
        │                         │
        └───────────────◄─────────┘
        │
        ▼
evidence selection + claim boundaries
        │
        ▼
resume / recruiter package / technical packet
        │
        ▼
application preparation
        │
        ▼
external acceptance evidence
        │
        ▼
verified lifecycle state
        │
        ▼
response / interview / outcome evidence
        │
        └──────────────► next stronger turn
```

The loop is designed around a simple standard: **real solutions to real hiring and engineering problems, proven at the layer actually claimed.**

## Truth model

Helix separates evidence states instead of letting one green artifact impersonate another.

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
DEPLOYMENT / EXTERNAL EFFECT
```

Examples:

- a README proves documentation, not runtime behavior;
- a successful build does not prove tests ran;
- a zero-test process is not test evidence;
- a local packet does not prove an external application was accepted;
- a receipt proves the observation it records, not project authority;
- a repository relationship proves a declared relationship, not inherited implementation quality;
- repository ownership does not by itself prove authorship, originality, deployment, or recruiter readiness.

## Application lifecycle safety

The current application path intentionally rejects the historical failure mode where a generic transport or one-file packet could be treated as a completed application.

A submission claim must be tied to the intended artifact set and external acceptance evidence. Preparation and dry-run behavior may exist without promoting state to `SUBMITTED`.

See:

- [`src/job_app_helix/application_operations.py`](src/job_app_helix/application_operations.py)
- [`tests/test_application_lifecycle.py`](tests/test_application_lifecycle.py)

## Restoration without amnesia

The restoration subsystem exists because reverting whole files is often the wrong answer when later commits contain real gains.

The preferred sequence is:

```text
observe current state
        ↓
find exact historical capability
        ↓
resolve symbol / dependency closure
        ↓
compare against current source
        ↓
compose only the missing gain
        ↓
compile / test / adversarial proof
        ↓
read back exact delta
        ↓
preserve receipt + rollback path
```

This is the opposite of destructive simplification: recover the lost capability while retaining later improvements.

## Genius Engine

The Genius Engine is the innovation path for candidate improvements:

```text
invent → attack → rank → advance
```

It is designed to penalize theater, thin mechanism, and capability-neutralizing changes while preserving ambitious candidates that survive evidence and adversarial comparison.

- Engine: [`src/job_app_helix/genius_engine.py`](src/job_app_helix/genius_engine.py)
- Documentation: [`docs/apex/GENIUS_ENGINE.md`](docs/apex/GENIUS_ENGINE.md)
- Tests: [`tests/test_genius_engine.py`](tests/test_genius_engine.py)

## Public recruiter surface

Recruiter-facing output should concentrate signal without changing underlying evidence.

The public compiler may improve:

- ordering;
- visual hierarchy;
- role-specific evidence selection;
- recruiter/expert/AI navigation;
- company and capability projection.

It may not silently change:

- factual repository identity;
- evidence state;
- blockers;
- test counts;
- private/public boundaries;
- provenance;
- project authority.

Useful surfaces:

- [`scripts/build_recruiter_site.py`](scripts/build_recruiter_site.py)
- [`RECRUITER_EXECUTIVE_SUMMARY.md`](RECRUITER_EXECUTIVE_SUMMARY.md)
- [`docs/RECRUITER_SITE_DEPLOYMENT.md`](docs/RECRUITER_SITE_DEPLOYMENT.md)
- [`hire_package/casey-barton/candidate_node.json`](hire_package/casey-barton/candidate_node.json)

## Typed relationships, without accidental rulers

The README Mesh retains a legacy v1 protobuf wire value named `GOVERNED_BY` for compatibility, but active mesh validation rejects that authority semantic. Current source relationships must express functional composition such as:

- `ORCHESTRATES`
- `VERIFIES`
- `PROVIDES_CAPABILITY`
- `CONSUMES`
- `EXTENDS`
- `PERSISTS_RECEIPTS_TO`
- `EXECUTES_THROUGH`

AKOS relationships are capability/evidence relationships. AKOS does not acquire project-direction authority over Helix or peer repositories.

The active index also declares `project_direction_authority: false` in [`manifests/readme_mesh.json`](manifests/readme_mesh.json).

## Install and verify

```bash
python -m pip install -e ".[dev]"
python -m ruff check src tests scripts ci_audit_portfolio.py showcase/demo_15min_run.py
python -m mypy src/job_app_helix/
python -m pytest -q
python scripts/check_proto_contract.py
python scripts/check_public_surface.py
```

Package entry points from [`pyproject.toml`](pyproject.toml):

```text
job-app-helix
job-app-helix-readme
job-app-helix-portfolio
job-app-helix-library
job-app-helix-genius
job-app-helix-restore
```

### Portfolio workflow

```bash
job-app-helix-portfolio validate
job-app-helix-portfolio render-program --output artifacts/portfolio-rollout.md
job-app-helix-portfolio plan --workspace repos --json-output artifacts/portfolio-plan.json
job-app-helix-portfolio execute --workspace repos --wave wave-1-native-ci --receipt artifacts/wave-1-receipt.json
```

Workspace-mutating build commands remain blocked unless the operator has reviewed the plan and explicitly authorizes mutation.

### Genius workflow

```bash
job-app-helix-genius --help
```

The historical script surface is also documented in [`STATUS.md`](STATUS.md).

### Restoration workflow

```bash
job-app-helix-restore --help
```

## Core machine sources

| Surface | Purpose |
|---|---|
| [`manifests/portfolio_repositories.json`](manifests/portfolio_repositories.json) | Admitted portfolio inventory |
| [`manifests/portfolio_rollout.json`](manifests/portfolio_rollout.json) | Rollout partition and targets |
| [`manifests/portfolio_root_truth.json`](manifests/portfolio_root_truth.json) | Evidence-bound coordination and projection contract |
| [`manifests/live_repository_links.json`](manifests/live_repository_links.json) | Repository identity/link state |
| [`manifests/live_repository_evidence.json`](manifests/live_repository_evidence.json) | SHA-bound repository observations |
| [`manifests/flagship_registry.json`](manifests/flagship_registry.json) | Evidence-backed flagship registry |
| [`manifests/company_dossiers.json`](manifests/company_dossiers.json) | Company/role evidence mapping |
| [`manifests/company_second_depth.json`](manifests/company_second_depth.json) | Company-specific evidence progression and claim ceilings |
| [`manifests/estate_compiler.json`](manifests/estate_compiler.json) | Estate compilation policy |
| [`manifests/estate_projection_policy.json`](manifests/estate_projection_policy.json) | Public/private projection policy |
| [`manifests/estate_facts.json`](manifests/estate_facts.json) | Evidence-bound estate assertions |
| [`manifests/readme_mesh.json`](manifests/readme_mesh.json) | Non-governing legacy public evidence mesh index |
| [`schemas/readme_apex.schema.json`](schemas/readme_apex.schema.json) | Active APEX README machine contract |

## Failure semantics

| Condition | Required behavior |
|---|---|
| Repository absent | explicit blocked state |
| Required executable absent | explicit blocked state |
| Test command exits zero with zero tests | not test evidence |
| Required check fails | failed evidence state |
| Command exceeds timeout | failed evidence state |
| Build would mutate without authorization | blocked before mutation |
| Source head changes | dependent evidence becomes stale |
| External effect cannot be verified | do not promote external-success state |
| Historical capability is missing | recover exact capability or record the gap; do not cosmetically hide it |
| Authority appears through a registry/edge/receipt | reject or demote the authority semantic while preserving useful capability |

## Historical compatibility

Helix has substantial history under older `canonical`, governor, promotion-authority, and federation terminology. That history remains valuable for provenance and capability archaeology.

Current APEX semantics distinguish **historical evidence** from **active authority**:

- old names may remain where a wire format or dated receipt requires compatibility;
- current machine projections must not interpret those names as project-direction authority;
- current source should prefer functional relations, evidence state, composition, and explicit Operator control;
- history is preserved rather than rewritten to pretend the earlier architecture never existed.

The retired README frame remains available for historical comparison at [`docs/README_OPTIMAL_IMPACT_FRAME.md`](docs/README_OPTIMAL_IMPACT_FRAME.md). The active direction is [`docs/README_APEX_TEMPLATE.md`](docs/README_APEX_TEMPLATE.md).

## Definition of progress

Helix improves when it produces a stronger verified outcome, not when it accumulates more ceremony.

```text
MISSION
  ↓
INTELLIGENT ACTION
  ↓
VERIFIED OUTCOME
  ↓
STRONGER NEXT STATE
```

The target is an employment engine that can continuously discover leverage, strengthen the portfolio, produce evidence-backed recruiter surfaces, prepare truthful applications, recover lost capability, and learn from outcomes without surrendering project direction to its own machinery.
