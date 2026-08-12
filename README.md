# Job-App Helix

**Evidence-bound job application outcome engine for the GlacierEQ engineering portfolio.**

Job-App Helix exists to turn a large software estate into truthful, role-specific hiring material that a recruiter, hiring manager, engineer, or automated application system can actually consume.

The governing principle is simple:

```text
company / role
    → relevant portfolio evidence
    → admitted public technical proof
    → truthful application thesis
    → explicit gaps and non-affiliation boundary
    → reusable application kit
```

Portfolio inventory, verification, lineage, README intelligence, and evidence receipts remain important, but they support this outcome. They are not the outcome themselves.

**Release:** `0.4.0`

## Primary workflow

Install:

```bash
python -m pip install -e ".[dev]"
```

List mapped company targets:

```bash
job-app-helix targets
```

Machine-readable target index:

```bash
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
- recruiter thesis already present in the company dossier
- only admitted, public proof repositories suitable for external use
- proof level/state for each surfaced repository
- the known gap that prevents stronger claims
- the explicit non-affiliation boundary
- a machine-readable JSON artifact
- a human-readable Markdown application brief

A target with no admitted public proof remains explicitly incomplete and the application command exits non-zero. Helix does not manufacture recruiter readiness from inventory alone.

## Recruiter proof selection

A repository is eligible for the application kit only when it is:

```text
public
AND HELIX_ADMITTED
AND state ∈ {PROMOTED, REFERENCE_ONLY}
```

Blocked, experimental, private, excluded-authorship, upstream/sample, quarantined, and audit-before-admission repositories are not silently promoted into recruiter evidence.

This means a company dossier can be richly mapped while still producing an incomplete application state. That is intentional.

## What the application engine uses

Company intelligence is loaded from:

```text
manifests/company_dossiers/*.json
```

Each company record contributes:

- `company_id`
- display name
- current track state
- mapped target roles
- recruiter thesis
- gap / next evidence requirement
- non-affiliation statement
- repository mappings and evidence states

The same manifests are included in the built wheel, so the primary application CLI does not depend on an uninstalled repository checkout.

## Legacy campaign fixture

The original flight / propulsion / ground campaign remains available as a deterministic test/demo fixture, but it is no longer the default product path:

```bash
job-app-helix demo nominal
job-app-helix demo recoverable
job-app-helix demo hard-no-go
```

Historical shorthand remains compatible:

```bash
job-app-helix nominal --json
```

The synthetic campaign is evidence of deterministic decision/refinement logic. It is not represented as a job application campaign.

## Portfolio verification system

Helix still contains substantial portfolio intelligence and proof machinery, including:

- exact repository inventory and estate census
- company dossiers and target mapping
- estate / lineage compiler
- repository evidence discovery
- bounded stack-native test execution
- positive test-count enforcement
- application-registry validation
- README Mesh and deterministic representations
- live-repository evidence workflows
- recruiter / engineering projection assets

Those surfaces should be used to improve the truth and strength of generated application kits, not as a substitute for them.

### Portfolio commands

```bash
job-app-helix-portfolio validate
job-app-helix-portfolio render-program --output artifacts/portfolio-rollout.md
job-app-helix-portfolio plan --workspace repos --json-output artifacts/portfolio-plan.json
```

`job-app-helix-readme` and `job-app-helix-library` remain specialized supporting interfaces.

## Verification

```bash
python -m ruff check src tests scripts ci_audit_portfolio.py showcase/demo_15min_run.py
python -m mypy src/job_app_helix/
python -m pytest -q
python scripts/check_proto_contract.py
python scripts/check_public_surface.py
```

The application outcome tests prove, among other things, that:

- Anthropic produces a role-specific kit using admitted public proof
- blocked/experimental xAI repositories are not surfaced as recruiter proof
- unmapped roles are rejected rather than invented
- kits persist as executable JSON/Markdown artifacts
- the primary no-argument CLI lists real hiring targets instead of launching a spacecraft scenario
- the legacy synthetic campaign remains available only as an explicit demo/compatibility path

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
