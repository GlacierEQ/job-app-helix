# Job-App Helix

[![CI](https://github.com/GlacierEQ/job-app-helix/actions/workflows/ci.yml/badge.svg)](https://github.com/GlacierEQ/job-app-helix/actions/workflows/ci.yml)

**A reproducible build-and-verify campaign engine for the GlacierEQ systems portfolio.**

Job-App Helix demonstrates how independently useful engineering components become a coherent system. A domain-building strand produces evidence; a verification strand challenges it; declared contingencies may refine the inputs once; the campaign then issues a transparent **GO** or **NO-GO** decision.

This repository is an independent software portfolio. It does not claim employment at, endorsement by, or operational deployment within any company whose problem domain inspired a demonstration.

## Run the proof

Requirements: Python 3.11 or newer.

```bash
python -m pip install -e ".[dev]"
python -m job_app_helix nominal
python -m job_app_helix recoverable --json
pytest
```

The public core is self-contained. It does not require a specific home directory, private repositories, IDE state, or an external orchestration runtime.

### Built-in scenarios

| Scenario | Purpose | Expected result |
|---|---|---|
| `nominal` | All evidence begins inside the demonstrated envelope | `GO` |
| `recoverable` | Initial failures have explicitly declared contingency evidence | `NO-GO -> refine -> GO` |
| `hard-no-go` | Critical failures have no supplied contingency evidence | `NO-GO` |

Write a machine-readable proof receipt:

```bash
python -m job_app_helix recoverable --output artifacts/campaign.json
```

## The model

The public vocabulary is deliberately small:

1. **Piston** — one independently runnable assessment.
2. **Helix** — build and verification strands aimed at the same mission.
3. **Campaign** — several pistons composed into an end-to-end decision.
4. **Proof contract** — work is complete only when the stated problem is demonstrably solved.

The launch campaign evaluates:

- Flight telemetry completeness and event severity
- Propulsion pressure, mixture-ratio error, and vibration
- Ground capacity and route availability
- One transparent contingency stroke using only evidence declared in the scenario
- A final campaign-level `GO` or `NO-GO`

No component is allowed to silently modify values until it passes.

## Engineering qualities

- Typed immutable inputs and result models
- Deterministic, dependency-free runtime
- Human-readable CLI and machine-readable JSON
- Fail-closed campaign decisions
- Explicit findings explaining every warning or hold
- Tests for success, recoverable failure, disabled refinement, and hard failure
- GitHub Actions gates for lint, tests, executable scenarios, link integrity, credential patterns, and public-boundary hygiene

## Repository map

```text
src/job_app_helix/       installable campaign engine
tests/                   executable behavioral claims
scripts/                 public-surface verification
.github/workflows/       reproducible GitHub evidence
docs/                    architecture and evidence boundaries
hire_package/            concise evidence-linked resume
```

Start with:

- [`src/job_app_helix/campaign.py`](src/job_app_helix/campaign.py) — campaign control flow
- [`src/job_app_helix/pistons.py`](src/job_app_helix/pistons.py) — evidence assessments and refinements
- [`tests/test_campaign.py`](tests/test_campaign.py) — executable claims
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — design and extension points
- [`docs/CLAIMS_AND_LIMITS.md`](docs/CLAIMS_AND_LIMITS.md) — what the project proves and does not prove
- [`HIERARCHICAL_PORTFOLIO_MAP.md`](HIERARCHICAL_PORTFOLIO_MAP.md) — curated portfolio hierarchy
- [`hire_package/RESUME_CASEY_GLACIEREQ.md`](hire_package/RESUME_CASEY_GLACIEREQ.md) — human-facing resume

## Evidence boundary

The public branch is intentionally curated. Generated IDE memory, local backups, machine-specific paths, private state, and legal or family-case workstreams are excluded. Deeper local multi-repository orchestration can exist outside this repository without becoming a prerequisite for evaluating the public proof.

## License

MIT. See [`LICENSE`](LICENSE).
