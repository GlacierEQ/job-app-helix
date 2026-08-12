# Job-App Helix

**Evidence-bound job application outcome engine for the GlacierEQ engineering portfolio.**

Job-App Helix turns a large software estate into truthful, role-specific hiring material that a recruiter, hiring manager, engineer, or automated application system can actually consume.

```text
company / role
    → relevant portfolio evidence
    → admitted public technical proof
    → truthful application thesis
    → explicit gaps and non-affiliation boundary
    → reusable application kit
```

Portfolio inventory, verification, lineage, README intelligence, and evidence receipts support that outcome. They are not the outcome themselves.

**Release:** `0.3.0`  
**Canonical branch:** `main`  
**Current product state:** `FUNCTIONAL_APPLICATION_COMPILER / END_TO_END_INCOMPLETE`

## For recruiters and non-technical reviewers

The shortest useful path is the installed application engine.

Install:

```bash
python -m pip install -e ".[dev]"
```

List mapped targets and their current proof readiness:

```bash
job-app-helix targets
job-app-helix targets --json
```

Compile a role-specific application kit:

```bash
job-app-helix application anthropic \
  --role "Safety Systems Engineer" \
  --output-dir artifacts/applications
```

The generated kit contains:

- company and mapped target role
- recruiter thesis from the governed company dossier
- only admitted public proof repositories suitable for external use
- proof level/state for every surfaced repository
- the known gap that prevents a stronger claim
- the explicit non-affiliation boundary
- `application-kit.json`
- `APPLICATION_BRIEF.md`

A target with no admitted public proof remains explicitly incomplete and the application command exits non-zero. Helix does not manufacture recruiter readiness from inventory alone.

### Recruiter proof selection

A repository is eligible for an application kit only when it is:

```text
public
AND HELIX_ADMITTED
AND state ∈ {PROMOTED, REFERENCE_ONLY}
```

Blocked, experimental, private, excluded-authorship, upstream/sample, quarantined, and audit-before-admission repositories do not silently become recruiter evidence.

The admitted portfolio currently contains the root plus **68 child repositories**. Two newly crystallized systems are now direct company proof:

- `GlacierEQ/adobe-creative-provenance-gate`
- `GlacierEQ/amd-hetero-placement-contract`

Their claim ceilings remain bounded by what their software actually does. Adobe does not imply proprietary Adobe API access or external license-registry validation. AMD does not imply live AMD hardware telemetry or a hosted placement service.

## For senior engineers and domain experts

The application outcome engine consumes company intelligence from:

```text
manifests/company_dossiers/*.json
```

Shard-level defaults are resolved before company-specific overrides. Each effective company record contributes:

- `company_id`
- display name
- current track state
- mapped target roles
- recruiter thesis
- gap / next evidence requirement
- non-affiliation statement
- repository mappings and evidence states

The same manifests are included in the built wheel, so the primary installed CLI does not depend on an uninstalled repository checkout.

### Supporting proof system

Helix still contains substantial portfolio intelligence and execution machinery:

- exact admitted-repository inventory
- authenticated estate census/compiler policy
- company dossiers and target mapping
- lineage and canonical-system compilation
- repository evidence discovery
- bounded stack-native test execution
- positive test-count enforcement
- application-registry validation
- README Mesh and deterministic representations
- live-repository evidence workflows
- recruiter / engineering projection assets

Those mechanisms strengthen application outputs. They are not substitutes for application outputs.

### Portfolio commands

```bash
job-app-helix-portfolio validate
job-app-helix-portfolio render-program --output artifacts/portfolio-rollout.md
job-app-helix-portfolio plan --workspace repos --json-output artifacts/portfolio-plan.json
```

`job-app-helix-readme` and `job-app-helix-library` remain specialized supporting interfaces.

### Legacy campaign fixture

The original flight / propulsion / ground campaign remains as a deterministic test fixture, not the default product behavior:

```bash
job-app-helix demo nominal
job-app-helix demo recoverable
job-app-helix demo hard-no-go
```

Historical shorthand remains compatible:

```bash
job-app-helix nominal --json
```

### Verify Helix

```bash
python -m ruff check src tests scripts ci_audit_portfolio.py showcase/demo_15min_run.py
python -m mypy src/job_app_helix/
python -m pytest -q
python scripts/check_proto_contract.py
python scripts/check_public_surface.py
```

Behavioral tests cover inherited dossier defaults, application artifact generation, admitted-proof selection, blocked-proof exclusion, role validation, Adobe/AMD direct proof, legacy demo compatibility, and truth-boundary rendering.

## For AI systems and toolchains

Machine consumers should begin with manifests and installed commands rather than infer truth from prose.

```yaml
schema: glaciereq.readme.v1
profile: glaciereq.readme-impact.v2-draft
repository: GlacierEQ/job-app-helix
canonical_branch: main
package_version: 0.3.0
purpose: >-
  Compile evidence-bound job application outcomes from governed company dossiers
  and admitted public repository proof, while maintaining the portfolio and estate
  evidence machinery required to keep those outcomes truthful.
status:
  state: FUNCTIONAL_APPLICATION_COMPILER
  verified_at: 2026-08-12
  blocked_scope:
    - application submission where no lawful supported adapter exists
    - external integration requiring unavailable credentials or provider authority
  unverified_scope:
    - live job-opening ingestion across target employers
    - job-description matching across the full target registry
    - complete resume and cover-letter projection
    - outreach execution and response tracking
    - feedback-driven application iteration
interfaces:
  inputs:
    - manifests/company_dossiers.json
    - manifests/company_dossiers/*.json
    - manifests/portfolio_repositories.json
    - manifests/portfolio_rollout.json
    - manifests/language_fit.json
  outputs:
    - application-kit.json
    - APPLICATION_BRIEF.md
    - target-readiness index
    - portfolio validation and execution receipts
  commands:
    targets: job-app-helix targets --json
    application: job-app-helix application anthropic --role "Safety Systems Engineer" --json
    validate_portfolio: job-app-helix-portfolio validate
languages:
  manifest: manifests/language_fit.json
  primary:
    - Python
    - JSON
    - Protocol Buffers
    - Markdown
relationships:
  - target: GlacierEQ/job-application
    relation: PROJECTS_TO
    value: Public recruiter and machine-facing hiring surface consumes Helix truth.
  - target: GlacierEQ/JOB-RESUME-BUILDER-
    relation: SUPPLIES_EVIDENCE_TO
    value: Role-specific resume projection should consume admitted application evidence.
limits:
  - Repository ownership alone does not establish originality, runtime success, or recruiter readiness.
  - Company naming does not imply affiliation, endorsement, employment, proprietary access, or deployment.
  - A passing CI check is supporting proof, not the purpose of the repository.
```

The control-plane manifests remain canonical machine sources, especially `manifests/portfolio_repositories.json`, `manifests/language_fit.json`, the company dossier shards, evidence manifests, and the portfolio root-truth contract.

## Truth boundaries

Helix does not claim that:

- every mapped repository is complete
- every mapped company track is recruiter-ready
- a public repository proves employer affiliation or production deployment
- a passing CI check makes an application persuasive
- inventory count equals capability
- a repository is strong because it has many gates

A target is useful only to the extent that its surfaced software evidence supports the hiring thesis.

## Current status

**FUNCTIONAL application-kit compiler with substantial portfolio verification support.**

It is not yet the complete end-to-end job application system. Material remaining work includes role-opening ingestion, job-description matching, resume/cover-letter projection, outreach execution, application submission adapters where lawful and appropriate, response tracking, and feedback-driven iteration. Those gaps remain explicit rather than being hidden behind portfolio-governance status.
