# Job-App Helix

[![Public CI](https://github.com/GlacierEQ/job-app-helix/actions/workflows/ci.yml/badge.svg)](https://github.com/GlacierEQ/job-app-helix/actions/workflows/ci.yml)

**A proof-driven portfolio control plane:** domain truth and operational verification run as two strands aimed at the same mission.

This repository has two deliberately separate execution modes:

| Mode | Purpose | Dependencies |
|---|---|---|
| **Public fixture mode** | Cloneable proof of the helix contract | Python standard library only |
| **Workspace integration mode** | Orchestrates the broader GlacierEQ multi-repository workspace | Explicit sibling repositories and optional Swarm services |

## Run the public proof

```bash
git clone https://github.com/GlacierEQ/job-app-helix.git
cd job-app-helix
python -m helix.public_runtime list
python -m helix.public_runtime demo --scenario nominal
python -m unittest discover -s tests -v
python tools/public_surface_audit.py
```

The campaign demo composes three stars:

1. **Flight:** orbital truth → telemetry verification → mission gate
2. **Propulsion:** health assessment → launch-sequencer hold logic
3. **Ground:** capacity planning → mesh-route gate

It emits a JSON proof receipt with initial and final GO/NO-GO decisions, Alpha/Omega results, refinements, and a SHA-256 receipt hash.

```bash
# Initial NO-GO, refinement closes the loop, final GO
python -m helix.public_runtime demo --scenario recoverable

# Persistent fault, final NO-GO and non-zero exit
python -m helix.public_runtime demo --scenario terminal
```

## Four public terms

- **Piston:** one runnable unit of work.
- **Helix:** an Alpha build/truth strand and an Omega verification/ops strand.
- **Campaign:** multiple stars composed into an end-to-end decision.
- **Proof contract:** **DONE iff proof(pain) is green.**

See [HELIX.md](HELIX.md) and [APEX_ARCHITECTURE.md](APEX_ARCHITECTURE.md).

## Public evidence

| Claim | Evidence |
|---|---|
| Executable helix model | `helix/public_runtime.py` |
| Fail-closed terminal faults | `terminal` scenario |
| Verification-driven refinement | `recoverable` scenario |
| Machine-readable receipts | JSON output and `proof_sha256` |
| Fresh-clone portability | Standard-library fixture mode |
| Independent checks | `.github/workflows/ci.yml` |

Detailed scope and limitations: [PUBLIC_READINESS.md](PUBLIC_READINESS.md).

## Workspace integration mode

The deeper runner remains intact:

```bash
python helix/automations/jobapp_helix_spiral.py list
python helix/automations/jobapp_helix_spiral.py run --pair launch_campaign
```

It is a workspace integration, not a fresh-clone promise. See [docs/REPOSITORY_BOUNDARIES.md](docs/REPOSITORY_BOUNDARIES.md).

## Portfolio entry points

| Surface | Purpose |
|---|---|
| [Public readiness](PUBLIC_READINESS.md) | Claims, boundaries, and gaps |
| [Architecture](APEX_ARCHITECTURE.md) | Pillars, helix topology, proof contract |
| [Portfolio map](HIERARCHICAL_PORTFOLIO_MAP.md) | Focused public navigation |
| [Casey resume](hire_package/RESUME_CASEY_GLACIEREQ.md) | Honest systems-builder profile |
| [Fast acquisition path](FAST_PATH_JOB_ACQUISITION.md) | Three-hero outreach strategy |
| [15-minute showcase](showcase/SHOWCASE.md) | Guided demonstration |

## Boundaries

This is portfolio software, not flight-certified software, frontier-lab employment history, or peer-reviewed research. Company-aligned names describe technical problem domains, not employer affiliation.

Legal, family-court, evidentiary, and private agent-memory material are outside this public hire surface.

Built by [GlacierEQ](https://github.com/GlacierEQ).
