# Executive Portfolio Summary

## Candidate signal

Casey Barton built Job-App Helix to turn a 66-repository engineering portfolio into an evidence-bound review system. The portfolio spans agent governance, distributed systems, model infrastructure, telemetry, safety controls, document intelligence, and polyglot architecture.

The differentiator is not the number of repositories or languages. It is making a large body of work **legible, composable, and falsifiable**:

- every repository receives an individual completeness, innovation, quality, function, and README grade;
- documentation distinguishes verified, partially verified, blocked, unverified, failed, and candidate scope;
- recruiter, expert, and AI-toolchain views are separated without contradicting one another;
- language choices must own a real system boundary and provide a build/test receipt;
- typed repository relationships describe combined value rather than merely cross-linking projects.

**Current portfolio status:** `PARTIALLY VERIFIED`. The current audit classifies one repository as partially verified, twenty as README-verified/runtime-unverified, one as blocked/unverified, and forty-four as unverified. `UNVERIFIED` means that current evidence is insufficient to make a working/not-working claim; it does not mean the repository is defective. AKOS has since received its own repository-native TEST promotion and immutable three-version receipt; that later component evidence does not silently rewrite the dated portfolio audit.

## What a recruiter should open first

| Priority | Artifact | Why it matters |
|---:|---|---|
| 1 | [Casey Barton candidate surface](hire_package/casey-barton/README.md) | Direct recruiter entry with résumé source, technical proof, claim policy, and AI-readable metadata. |
| 2 | [Root README](README.md) | Portfolio control-plane outcome, expert architecture, and machine contract. |
| 3 | [66-repository evidence audit](docs/PORTFOLIO_EVIDENCE_AUDIT_2026-07-29.md) | Individual grades, verification states, and the highest-priority correction for every repository. |
| 4 | [Exact portfolio inventory](manifests/portfolio_repositories.json) | Pins the audit boundary to one root and sixty-five child repositories. |
| 5 | [README impact standard](docs/README_OPTIMAL_IMPACT_FRAME.md) | Defines the recruiter → expert → AI documentation architecture. |
| 6 | [Language-fit manifest](manifests/language_fit.json) | Shows how language choices are tied to responsibilities, interfaces, commands, receipts, and state. |

## Strongest current exhibits

### Job-App Helix

**Role:** portfolio control plane and evidence ledger.  
**Signal:** systems architecture, deterministic decision logic, Protobuf contracts, CI design, documentation engineering, and truth-preserving audit semantics.  
**Status:** partially verified; repository CI is authoritative for the current branch.

### AKOS

**Role:** authority, provenance, maturity, and completion semantics for agentic systems.  
**Signal:** governance architecture, operational cognition, read-only action boundaries, and evidence-bound verification.  
**Status:** TEST verified at promotion commit `d00eb4a9889fb4b78621d422a70c2677e12a467d`; 94/94 tests across Python 3.11, 3.12, and 3.13.

### Agent Coordinator

**Role:** deterministic dependency-aware scheduling under global and specialist-role budgets.  
**Signal:** typed scheduling policy, graph validation, hardened JUnit evidence, compatibility preservation, and explicit candidate-versus-hosted proof boundaries.  
**Status:** candidate proof includes 62/62 independent Python 3.13 tests; hosted multi-version promotion remains unverified.

### The Tower of Babel

**Role:** reference architecture for choosing the right language for the right workload.  
**Signal:** ambitious polyglot design, with languages assigned to performance, safety, proof, hardware, interoperability, or deployment boundaries.  
**Status:** high-innovation candidate, currently blocked/unverified until CI and correctness/security review close. It is not presented as production proof.

## Engineering qualities demonstrated

- **Architecture over accumulation:** related repositories are modeled as systems with directional relationships.
- **Evidence discipline:** inventory hashes, README validation, runtime execution, benchmarks, hardware execution, and deployment receipts are treated as different proof classes.
- **Polyglot judgment:** languages are accepted only when they materially improve a boundary.
- **Failure semantics:** timeouts, zero-test runs, missing repositories, missing receipts, and blocked toolchains cannot silently become passes.
- **Human communication:** the first screen explains value; deeper sections reward technical scrutiny; machine blocks support ingestion and orchestration.

## Application spiral

The candidate surface uses one evidence-accumulating path:

`OBSERVE → RECOVER → PLAN → ROUTE → ACT → VERIFY → PERSIST → RESUME`

Each revolution begins from accumulated context, authority, artifacts, failures, and receipts. Improvement is the consequence of verified persistence and resumption, not an unbounded rewrite loop.

## Current limitations

- The complete 66-repository runtime surface has not yet been executed in one authoritative environment.
- The README Mesh rollout receipt covers twenty-one declared nodes, not all sixty-six repositories.
- Many repositories still need clean-checkout CI, current test receipts, and README rewrites.
- Provider deployment, customer impact, portfolio-wide scale, and performance remain unverified unless a specific repository supplies a current receipt.

## Verification

From a clean checkout of Job-App Helix:

```bash
python -m pip install -e ".[dev]"
python -m ruff check src tests scripts ci_audit_portfolio.py showcase/demo_15min_run.py
python -m pytest -q
python scripts/check_proto_contract.py
python -m job_app_helix.readme_mesh_cli validate
```

The multi-repository audit additionally requires the canonical local `repos/` workspace:

```bash
python ci_audit_portfolio.py
```

That command validates the exact inventory before executing its bounded runtime sample and demo suite. Its receipt names every repository process that actually ran.
