# Executive Portfolio Summary

## Candidate signal

Casey Barton built Job-App Helix to turn a 66-repository engineering portfolio into an evidence-bound review system. The portfolio spans agent governance, distributed systems, model infrastructure, aerospace simulation, telemetry, safety controls, document intelligence, and polyglot architecture.

The differentiator is not the number of repositories or languages. It is the attempt to make a large body of work **legible, composable, and falsifiable**:

- every repository receives an individual completeness, innovation, quality, function, and README grade;
- documentation distinguishes verified, partially verified, blocked, unverified, and failed scope;
- recruiter, expert, and AI-toolchain views are separated without contradicting one another;
- language choices must own a real system boundary and provide a build/test receipt;
- typed repository relationships describe combined value rather than merely cross-linking projects.

**Current portfolio status:** `PARTIALLY VERIFIED`. The current audit classifies one repository as partially verified, twenty as README-verified/runtime-unverified, one as blocked/unverified, and forty-four as unverified. `UNVERIFIED` means that current evidence is insufficient to make a working/not-working claim; it does not mean the repository is defective.

## What a recruiter should open first

| Priority | Artifact | Why it matters |
|---:|---|---|
| 1 | [Root README](README.md) | Fast recruiter view, expert architecture, and machine contract in one document. |
| 2 | [66-repository evidence audit](docs/PORTFOLIO_EVIDENCE_AUDIT_2026-07-29.md) | Individual grades, verification states, and the highest-priority correction for every repository. |
| 3 | [Exact portfolio inventory](manifests/portfolio_repositories.json) | Pins the audit boundary to one root and sixty-five child repositories. |
| 4 | [README impact standard](docs/README_OPTIMAL_IMPACT_FRAME.md) | Defines the recruiter → expert → AI documentation architecture. |
| 5 | [Language-fit manifest](manifests/language_fit.json) | Shows how language choices are tied to responsibilities, interfaces, commands, receipts, and state. |
| 6 | [GitHub pull request #5](https://github.com/GlacierEQ/job-app-helix/pull/5) | Reviewable implementation of the evidence-bound audit and documentation system. |

## Strongest current exhibits

### Job-App Helix

**Role:** portfolio control plane and evidence ledger.  
**Signal:** systems architecture, deterministic decision logic, Protobuf contracts, CI design, documentation engineering, and truth-preserving audit semantics.  
**Status:** partially verified; repository CI is authoritative for the current branch.

### AKOS

**Role:** authority, provenance, maturity, and completion semantics for agentic systems.  
**Signal:** governance architecture and evidence-bound operational reasoning.  
**Status:** README-verified/runtime-unverified in the current portfolio audit.

### SpaceX subsystem family

**Role:** independent telemetry, mission-control, thermal, orbital, network, sequencing, weather, propulsion, and autonomy components.  
**Signal:** decomposition of a complex domain into typed, separately reviewable systems.  
**Status:** documentation quality is strongest in the README Mesh nodes; runtime verification still requires repository-native receipts.

### The Tower of Babel

**Role:** reference architecture for choosing the right language for the right workload.  
**Signal:** unusually ambitious polyglot design, with languages assigned to performance, safety, proof, hardware, interoperability, or deployment boundaries.  
**Status:** high-innovation candidate, currently blocked/unverified until CI and correctness/security review close. It is not presented as production proof.

## Engineering qualities demonstrated

- **Architecture over accumulation:** related repositories are modeled as systems with directional relationships.
- **Evidence discipline:** inventory hashes, README validation, runtime execution, benchmarks, hardware execution, and deployment receipts are treated as different proof classes.
- **Polyglot judgment:** languages are accepted only when they materially improve a boundary.
- **Failure semantics:** timeouts, zero-test runs, missing repositories, missing receipts, and blocked toolchains cannot silently become passes.
- **Human communication:** the first screen explains value; deeper sections reward technical scrutiny; machine blocks support ingestion and orchestration.

## Current limitations

- The complete 66-repository runtime surface has not yet been executed in one authoritative environment.
- The README Mesh rollout receipt covers twenty-one declared nodes, not all sixty-six repositories.
- Many repositories still need clean-checkout CI, current test receipts, and README rewrites.
- Several historical recruiting documents contained machine-local links and overbroad readiness language; the current remediation removes those defects rather than preserving them as marketing copy.

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
