# Executive Portfolio Summary

## Candidate signal

Casey Barton built Job-App Helix to turn a 67-repository engineering portfolio into an evidence-bound review system. The portfolio spans agent governance, distributed systems, model infrastructure, telemetry, safety controls, document intelligence, product engineering, and polyglot architecture.

The differentiator is not the number of repositories or languages. It is making a large body of work **legible, composable, and falsifiable**:

- every repository receives an individual completeness, innovation, quality, function, and README grade;
- documentation distinguishes verified, partially verified, blocked, unverified, failed, and candidate scope;
- recruiter, expert, and AI-toolchain views are separated without contradicting one another;
- language choices must own a real system boundary and provide a build/test receipt;
- typed repository relationships describe combined value rather than merely cross-linking projects.

**Current live portfolio status:** `PARTIALLY VERIFIED`. The July 29 evidence audit covered the prior 66-repository boundary and classified one repository as partially verified, twenty as README-verified/runtime-unverified, one as blocked/unverified, and forty-four as unverified. `UNVERIFIED` means that current evidence is insufficient to make a working/not-working claim; it does not mean the repository is defective. Later component promotions and the July 31 admission of Resume Shapeshifter do not silently rewrite that dated audit.

The live boundary now contains one Helix root and sixty-six children. `JOB-RESUME-BUILDER-` was admitted because it is the lead product flagship presented by `job-application`; its absence created a governance gap between the recruiter portal and the evidence control plane.

## What a recruiter should open first

| Priority | Artifact | Why it matters |
|---:|---|---|
| 1 | [Live recruiter presentation](https://glaciereq.github.io/job-app-helix/) | Deployed recruiter, engineering, and AI reading paths generated from canonical Helix evidence records. |
| 2 | [Resume Shapeshifter](https://github.com/GlacierEQ/JOB-RESUME-BUILDER-) | Lead product flagship: source-grounded résumé tailoring with deterministic truthfulness checks and executable TypeScript tests. |
| 3 | [Casey Barton candidate source](hire_package/casey-barton/README.md) | Résumé source, technical proof, claim policy, typed candidate metadata, and immutable evidence links. |
| 4 | [Root README](README.md) | Portfolio control-plane outcome, expert architecture, and machine contract. |
| 5 | [Historical 66-repository evidence audit](docs/PORTFOLIO_EVIDENCE_AUDIT_2026-07-29.md) | Individual grades, verification states, and the highest-priority correction for the original audit boundary. |
| 6 | [Exact live portfolio inventory](manifests/portfolio_repositories.json) | Pins the current boundary to one root and sixty-six child repositories. |
| 7 | [GitHub curation ledger](manifests/github_repository_curation_2026-07-31.json) | Records admission, deferral, duplicate, private, backup, archive, and external-source decisions. |
| 8 | [README impact standard](docs/README_OPTIMAL_IMPACT_FRAME.md) | Defines the recruiter → expert → AI documentation architecture. |
| 9 | [Recruiter deployment contract](docs/RECRUITER_SITE_DEPLOYMENT.md) | Explains how canonical records become a hash-bound Pages deployment from `main`. |

## Strongest current exhibits

### Job-App Helix

**Role:** portfolio control plane, evidence ledger, and deployed candidate presentation source.  
**Signal:** systems architecture, deterministic decision logic, Protobuf contracts, CI design, documentation engineering, proof-weighted auditing, and truth-preserving deployment semantics.  
**Status:** partially verified; repository CI and the Pages deployment workflow are authoritative for their named scopes.

### Resume Shapeshifter

**Role:** source-grounded résumé analysis and tailoring product.  
**Signal:** Next.js/TypeScript product engineering, model-boundary failure semantics, Zod contracts, deterministic anti-fabrication controls, and human review.  
**Status:** hardening; source, tests, lint, and build workflow are inspectable. Production deployment, document export, persistence, and calibrated applicant-tracking outcomes remain unverified.

### AKOS

**Role:** authority, provenance, maturity, and completion semantics for agentic systems.  
**Signal:** governance architecture, operational cognition, read-only action boundaries, and evidence-bound verification.  
**Status:** repository-native TEST evidence exists at its named promotion commit; later receipts should be consulted for exact counts and canonical SHAs.

### Agent Coordinator

**Role:** deterministic dependency-aware scheduling under global and specialist-role budgets.  
**Signal:** typed scheduling policy, graph validation, hardened JUnit evidence, compatibility preservation, and explicit candidate-versus-hosted proof boundaries.  
**Status:** 62 executed Python 3.13 tests are recorded at the named promotion receipt; hosted cross-version scope remains explicit in that receipt.

### The Tower of Babel

**Role:** reference architecture for choosing the right language for the right workload.  
**Signal:** polyglot design with languages assigned to performance, safety, proof, hardware, interoperability, or deployment boundaries.  
**Status:** later repository-native TEST promotion exists in the rollout manifest; claims remain bounded to the recorded proof.

## Engineering qualities demonstrated

- **Architecture over accumulation:** related repositories are modeled as systems with directional relationships.
- **Evidence discipline:** inventory hashes, README validation, runtime execution, benchmarks, hardware execution, and deployment receipts are treated as different proof classes.
- **Polyglot judgment:** languages are accepted only when they materially improve a boundary.
- **Failure semantics:** timeouts, zero-test runs, missing repositories, missing receipts, and blocked toolchains cannot silently become passes.
- **Deployment integrity:** the recruiter site is generated from canonical source records and every public payload is SHA-256 listed.
- **Human communication:** the first screen explains value; deeper sections reward technical scrutiny; machine blocks support ingestion and orchestration.

## Application spiral

The candidate surface uses one evidence-accumulating path:

`OBSERVE → RECOVER → PLAN → ROUTE → ACT → VERIFY → PERSIST → RESUME`

Each revolution begins from accumulated context, authority, artifacts, failures, and receipts. Improvement is the consequence of verified persistence and resumption, not an unbounded rewrite loop.

## Current limitations

- The complete 67-repository runtime surface has not been executed in one authoritative environment.
- The README Mesh rollout receipt covers twenty-one declared nodes, not all sixty-seven repositories.
- Resume Shapeshifter has been admitted to the live inventory but still requires Wave 3 repository-native promotion evidence.
- Many repositories still need clean-checkout CI, current test receipts, and README rewrites.
- Publishing the recruiter surface proves a static deployment from a named Helix commit; it does not establish portfolio-wide production deployment.
- Provider deployment, customer impact, portfolio-wide scale, and performance remain unverified unless a specific repository supplies a current receipt.
- The connected Mac worktree was offline during the July 31 GitHub reconciliation, so local-only and uncommitted work was not inspected.

## Verification

From a clean checkout of Job-App Helix:

```bash
python -m pip install -e ".[dev]"
python -m ruff check src tests scripts ci_audit_portfolio.py showcase/demo_15min_run.py
python -m pytest -q
python scripts/check_proto_contract.py
python -m job_app_helix.readme_mesh_cli validate
job-app-helix-portfolio validate
```

Build the recruiter surface from canonical records:

```bash
python scripts/build_recruiter_site.py \
  --output artifacts/pages-site \
  --source-commit "$(git rev-parse HEAD)"

python -m pytest -q tests/test_recruiter_site_deployment.py
```

The multi-repository audit additionally requires the canonical local `repos/` workspace:

```bash
python ci_audit_portfolio.py
```

That command validates the exact live inventory before executing its bounded runtime sample and demo suite. Its receipt names every repository process that actually ran.