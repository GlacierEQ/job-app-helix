# Job-App Helix

[![CI](https://github.com/GlacierEQ/job-app-helix/actions/workflows/ci.yml/badge.svg)](https://github.com/GlacierEQ/job-app-helix/actions/workflows/ci.yml)

**A reproducible build-and-verify campaign engine for the GlacierEQ systems portfolio.**

Job-App Helix demonstrates how independently useful engineering components become a coherent system. A domain-building strand produces evidence; a verification strand challenges it; declared contingencies may refine the inputs once; the campaign then issues a transparent **GO** or **NO-GO** decision.

This repository does **not** claim employment at SpaceX, xAI, NVIDIA, OpenAI, Anthropic, or any other referenced company. It is an independent software portfolio and orchestration demonstration.

## Run the proof

Requirements: Python 3.11 or newer.

```bash
python -m pip install -e .
python -m job_app_helix nominal
python -m job_app_helix recoverable --json
```

The public core is self-contained. It does not require Casey's home directory, private repositories, IDE state, or the GlacierEQ Swarm runtime.

### Built-in scenarios

| Scenario | Purpose | Expected result |
|---|---|---|
| `nominal` | All evidence begins inside the demonstrated envelope | `GO` |
| `recoverable` | Initial failures have explicitly declared contingency evidence | `NO-GO -> refine -> GO` |
| `hard-no-go` | Critical failures have no supplied contingency evidence | `NO-GO` |

A proof receipt can be written for inspection or automation:

```bash
python -m job_app_helix recoverable --output artifacts/campaign.json
```

## The model

The public vocabulary is deliberately small:

1. **Piston** — one independently runnable assessment.
2. **Helix** — build and verification strands aimed at the same mission.
3. **Campaign** — several pistons composed into an end-to-end decision.
4. **Proof contract** — work is complete only when the stated problem is demonstrably solved.

The launch campaign currently evaluates:

- Flight telemetry completeness and event severity
- Propulsion pressure, mixture-ratio error, and vibration
- Ground capacity and route availability
- One transparent contingency stroke using only evidence declared in the scenario
- A final campaign-level `GO` or `NO-GO`

No component is allowed to silently modify values until it passes.

## Engineering qualities

- Typed immutable inputs and result models
- Deterministic, dependency-free public runtime
- Human-readable CLI and machine-readable JSON
- Fail-closed campaign decisions
- Explicit findings explaining every warning or hold
- Tests for success, recoverable failure, disabled refinement, and hard failure
- GitHub Actions gates for lint, tests, package execution, public-link hygiene, and secret scanning

## Repository map

```text
src/job_app_helix/       public installable campaign engine
tests/                   behavioral and public-surface tests
.github/workflows/       reproducible GitHub evidence
hire_package/            resume and outreach artifacts
showcase/                longer-form portfolio demonstrations
helix/                   local multi-repository orchestration layer
docs/                    architecture, boundaries, and deeper rationale
```

Start with:

- [`src/job_app_helix/campaign.py`](src/job_app_helix/campaign.py) — campaign control flow
- [`src/job_app_helix/pistons.py`](src/job_app_helix/pistons.py) — evidence assessments and refinements
- [`tests/test_campaign.py`](tests/test_campaign.py) — executable behavioral claims
- [`HIERARCHICAL_PORTFOLIO_MAP.md`](HIERARCHICAL_PORTFOLIO_MAP.md) — curated portfolio map
- [`hire_package/RESUME_CASEY_GLACIEREQ.md`](hire_package/RESUME_CASEY_GLACIEREQ.md) — evidence-linked resume
- [`HELIX.md`](HELIX.md) — extended local-workspace architecture

## Public and local modes

### Public mode

The package under `src/job_app_helix` is the reviewer-facing product. It must clone, install, test, and run on a clean machine.

### Local portfolio mode

The older orchestration layer under `helix/` can connect many sibling GlacierEQ repositories in Casey's private/local workspace. It remains useful as a multi-repository integration harness, but it is not the reproducibility boundary for this public repository.

## Evidence boundaries

- Portfolio models are demonstrations, not operational flight or datacenter control systems.
- Thresholds in the fixture campaign are documented software-demo envelopes, not manufacturer limits.
- Legal and family-case systems are excluded from this hiring surface.
- Generated IDE memory, local backups, secrets, and machine-specific paths are not public product material.
- A badge is evidence only when the linked GitHub workflow is green for the displayed commit.

## Development

```bash
python -m pip install -e '.[dev]'
ruff check .
pytest
python -m job_app_helix recoverable --output artifacts/campaign.json
```

## License

MIT. See [`LICENSE`](LICENSE) when present; until then, all rights remain with the repository owner.
