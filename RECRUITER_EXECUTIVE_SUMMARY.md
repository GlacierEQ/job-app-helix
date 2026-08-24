# Executive Portfolio Summary

## Candidate signal

Casey Barton built Job-App Helix to turn a large engineering portfolio into an evidence-bound employment intelligence and execution system. The portfolio spans agent infrastructure, distributed systems, model infrastructure, telemetry, safety controls, document intelligence, product engineering, and polyglot architecture.

The differentiator is not repository count or language count. It is making a large body of work **legible, composable, falsifiable, and useful for real hiring decisions**:

- repository evidence remains distinct as verified, partially verified, blocked, unverified, failed, or candidate scope;
- recruiter, expert, and AI-toolchain views can be generated from the same evidence without changing the underlying facts;
- language choices must own a real system boundary and provide a build/test/proof path;
- typed repository relationships describe combined capability rather than silently creating hierarchy;
- portfolio intelligence can rank, route, restore, and project capability without becoming project-direction authority;
- application state cannot advance beyond the strongest externally supported evidence.

**Current portfolio posture:** `PARTIALLY VERIFIED`. Dated audits remain historical evidence at their original scope. Later promotions, restorations, and admissions do not silently rewrite those observations.

The admitted public boundary currently contains one Helix root and sixty-six child repositories. That inventory is a coordination/projection surface, not a claim that Helix owns the purpose or factual source state of those repositories.

## What a recruiter should open first

| Priority | Artifact | Why it matters |
|---:|---|---|
| 1 | [Live recruiter presentation](https://casey-barton-glaciereq.vercel.app/) | Recruiter, engineering, and AI reading paths generated from public-safe evidence. |
| 2 | [Resume Shapeshifter](https://github.com/GlacierEQ/JOB-RESUME-BUILDER-) | Lead product flagship: source-grounded résumé tailoring with deterministic truthfulness controls and executable TypeScript tests. |
| 3 | [Casey Barton candidate source](hire_package/casey-barton/README.md) | Résumé source, technical proof, claim policy, typed candidate metadata, and evidence links. |
| 4 | [Job-App Helix](README.md) | Employment intelligence, application execution, evidence compilation, Genius innovation, and capability-restoration architecture. |
| 5 | [Historical 66-repository evidence audit](docs/PORTFOLIO_EVIDENCE_AUDIT_2026-07-29.md) | Individual grades and verification states at the dated audit boundary. |
| 6 | [Admitted portfolio inventory](manifests/portfolio_repositories.json) | Current public-portfolio coordination boundary. |
| 7 | [GitHub curation ledger](manifests/github_repository_curation_2026-07-31.json) | Dated admission, deferral, duplicate, private, backup, archive, and external-source decisions. |
| 8 | [Active APEX README contract](docs/README_APEX_TEMPLATE.md) | Current Operator-first, capability-preserving documentation architecture. |
| 9 | [Recruiter deployment contract](docs/RECRUITER_SITE_DEPLOYMENT.md) | Explains the Vercel hire surface and its public evidence boundary. |

## Strongest current exhibits

### Job-App Helix

**Role:** employment intelligence and execution plane, evidence compiler, application lifecycle engine, restoration system, and candidate-presentation source.  
**Signal:** systems architecture, deterministic decision logic, portfolio intelligence, Protobuf contracts, application truth-state design, capability archaeology, reversible restoration, innovation ranking, recruiter compilation, and proof-weighted auditing.  
**Boundary:** Helix coordinates and verifies evidence. It does not acquire project-direction authority over the Operator or peer repositories.

### Resume Shapeshifter

**Role:** source-grounded résumé analysis and tailoring product.  
**Signal:** Next.js/TypeScript product engineering, model-boundary failure semantics, Zod contracts, deterministic anti-fabrication controls, and human review.  
**Status:** source, tests, lint, and build workflow are inspectable; production deployment and applicant-tracking outcomes require their own evidence.

### AKOS

**Role:** capability donor for operational cognition, evidence/provenance conventions, and agent-system design.  
**Signal:** repository-native tests, cognition architecture, read-only action boundaries, and evidence-aware verification.  
**Boundary:** AKOS evidence may strengthen Helix and other systems; it does not receive project-direction authority by being referenced or consumed.

### Agent Coordinator

**Role:** deterministic dependency-aware scheduling under global and specialist-role budgets.  
**Signal:** typed scheduling policy, graph validation, hardened JUnit evidence, compatibility preservation, and explicit candidate-versus-hosted proof boundaries.

### Tower of Babel

**Role:** technology-placement, interoperability, and proof capability donor.  
**Signal:** polyglot design with technologies assigned to performance, safety, proof, hardware, interoperability, or deployment boundaries.  
**Boundary:** Tower can inform technology placement at a scoped engineering boundary; it is not an estate-wide project-direction ruler.

## Engineering qualities demonstrated

- **Architecture over accumulation:** related repositories are modeled as systems with directional, scoped relationships.
- **Function over governance:** useful software and real outcome paths remain the dominant criterion; gates and receipts support function rather than substitute for it.
- **Evidence discipline:** inventory hashes, source identity, tests, runtime execution, benchmarks, hardware execution, and deployment receipts remain different proof classes.
- **Capability preservation:** restoration tooling recovers exact historical capability while protecting later verified gains.
- **Innovation with attack surfaces:** Genius candidates are invented, attacked, ranked, and advanced instead of being promoted because they sound novel.
- **Polyglot judgment:** technologies earn their place at a boundary rather than by increasing a language count.
- **Failure semantics:** timeouts, zero-test runs, missing repositories, stale receipts, unsafe mutation, and unverifiable external effects cannot silently become passes.
- **Human communication:** the first screen explains value; deeper sections reward technical scrutiny; machine surfaces support deterministic continuation.

## Application spiral

The candidate surface uses one evidence-accumulating path:

`OBSERVE → RECOVER → PLAN → ROUTE → ACT → VERIFY → PERSIST → RESUME`

Each revolution begins from accumulated context, artifacts, failures, receipts, and current Operator direction. Improvement is the consequence of verified persistence and stronger action, not an unbounded rewrite loop.

## Current limitations

- The complete admitted portfolio has not been executed in one authoritative runtime environment.
- The README Mesh rollout receipt covers a bounded declared subset rather than every repository.
- Many repositories still require current clean-checkout proof and stronger implementation depth.
- Publishing a recruiter surface proves a deployment of that presentation, not portfolio-wide production operation.
- Provider deployment, customer impact, portfolio-wide scale, and performance remain unverified unless a specific source supplies current evidence.

## Verification

From a clean checkout of Job-App Helix:

```bash
python -m pip install -e ".[dev]"
python -m ruff check src tests scripts ci_audit_portfolio.py showcase/demo_15min_run.py
python -m pytest -q
python scripts/check_proto_contract.py
python scripts/check_public_surface.py
job-app-helix-portfolio validate
```

Build the recruiter surface:

```bash
python scripts/build_recruiter_site.py \
  --output artifacts/pages-site \
  --source-commit "$(git rev-parse HEAD)"

python -m pytest -q tests/test_recruiter_site_deployment.py
```

Multi-repository verification additionally requires an available workspace containing the referenced repositories. A receipt proves only what actually ran.
