# Job-App Helix

[![CI](https://github.com/GlacierEQ/job-app-helix/actions/workflows/ci.yml/badge.svg)](https://github.com/GlacierEQ/job-app-helix/actions/workflows/ci.yml)

**A reproducible build-and-verify campaign engine for the GlacierEQ systems portfolio.**

<!-- README-MESH:BEGIN -->
## Three-audience project map

This section is generated from the versioned [README Mesh Protobuf contract](https://github.com/GlacierEQ/job-app-helix/blob/main/proto/readme_mesh.proto). Human explanation and machine-readable topology describe the same evidence-bound system.

### For recruiters and non-specialists

**What this project accomplishes.** A reproducible campaign engine that turns independent engineering modules into one transparent build-and-verify decision.

- It turns campaign orchestration into a concrete, reviewable software capability.
- The project is small enough to understand quickly and structured enough to connect into a larger system.
- Claims link to source or tests instead of resume language alone.

**Evidence**
- [Campaign control flow](https://github.com/GlacierEQ/job-app-helix/blob/main/src/job_app_helix/campaign.py) — Composes stage results into an explicit GO or NO-GO decision.

### For senior engineers and domain experts

**Engineering depth, innovation, and evolution.** It combines human explanation, typed evidence, fail-closed decisions, deterministic scenarios, and a real Protocol Buffers README graph. It evolved from a local multi-repository demonstration into a clean public control surface that can generate consistent recruiter, expert, and AI views for the portfolio.

- Primary engineering capabilities: campaign orchestration, verification engineering, README intelligence mesh, Protocol Buffers.
- The repository owns an explicit mesh responsibility rather than pretending to be an entire platform.
- Constraints and handoffs are visible through source structure and executable tests.

**Evidence**
- [Campaign control flow](https://github.com/GlacierEQ/job-app-helix/blob/main/src/job_app_helix/campaign.py) — Composes stage results into an explicit GO or NO-GO decision.
- [Evidence pistons](https://github.com/GlacierEQ/job-app-helix/blob/main/src/job_app_helix/pistons.py) — Implements typed assessments and bounded contingency refinements.
- [Executable claims](https://github.com/GlacierEQ/job-app-helix/blob/main/tests/test_campaign.py) — Tests nominal, recoverable, and hard-failure behavior.

### For AI systems and toolchains

**Machine contract and mesh role.** This repository is a typed node in the GlacierEQ/job-app-helix README Mesh and uses the glaciereq.readme.v1 Protobuf contract.

- Canonical repository identity: GlacierEQ/job-app-helix.
- Default branch: main.
- Typed edges describe composition; evidence URLs remain stable machine inputs.

**Evidence**
- [Executable claims](https://github.com/GlacierEQ/job-app-helix/blob/main/tests/test_campaign.py) — Tests nominal, recoverable, and hard-failure behavior.
- [README Mesh schema](https://github.com/GlacierEQ/job-app-helix/blob/main/proto/readme_mesh.proto) — Defines the real Protobuf contract for repository nodes, audience sections, evidence, and typed edges.

### Repository mesh

| Relationship | Connected repository | Combined value |
|---|---|---|
| is governed by | [GlacierEQ/AKOS](https://github.com/GlacierEQ/AKOS#readme) | AKOS defines evidence boundaries, execution authority, verification, and completion semantics for the README Mesh. |
| orchestrates | [GlacierEQ/spacex-ground-network](https://github.com/GlacierEQ/spacex-ground-network#readme) | Supplies verified capacity and failover evidence. |
| orchestrates | [GlacierEQ/spacex-launch-sequencer](https://github.com/GlacierEQ/spacex-launch-sequencer#readme) | Supplies dependency-aware launch progression. |
| orchestrates | [GlacierEQ/spacex-mission-control](https://github.com/GlacierEQ/spacex-mission-control#readme) | Presents combined campaign state to a human operator. |
| orchestrates | [GlacierEQ/spacex-orbital-mechanics](https://github.com/GlacierEQ/spacex-orbital-mechanics#readme) | Adds trajectory and orbital-state evidence. |
| orchestrates | [GlacierEQ/spacex-pad-weather-gate](https://github.com/GlacierEQ/spacex-pad-weather-gate#readme) | Adds an independent environmental readiness gate. |
| orchestrates | [GlacierEQ/spacex-propulsion-monitor](https://github.com/GlacierEQ/spacex-propulsion-monitor#readme) | Supplies propulsion-health evidence and hold signals. |
| orchestrates | [GlacierEQ/spacex-satellite-mesh](https://github.com/GlacierEQ/spacex-satellite-mesh#readme) | Extends the communications path beyond the ground segment. |
| orchestrates | [GlacierEQ/spacex-telemetry](https://github.com/GlacierEQ/spacex-telemetry#readme) | Supplies ordered telemetry evidence to the campaign. |
| orchestrates | [GlacierEQ/spacex-thermal-protection](https://github.com/GlacierEQ/spacex-thermal-protection#readme) | Adds predictive thermal evidence and bounded response. |

### Machine-readable contract

- Protobuf package: `glaciereq.readme.v1`
- Mesh schema version: `1.0.0`
- Canonical mesh: [`manifests/readme_mesh.json`](https://github.com/GlacierEQ/job-app-helix/blob/main/manifests/readme_mesh.json)
- Binary/ProtoJSON build: `python -m job_app_helix.readme_mesh_cli build`
- Repository identity: `GlacierEQ/job-app-helix`

```protobuf
repository: "GlacierEQ/job-app-helix"
display_name: "Job-App Helix"
one_line_purpose: "A reproducible campaign engine that turns independent engineering modules into one transparent build-and-verify decision."
```
<!-- README-MESH:END -->

Job-App Helix demonstrates how independently useful engineering components become a coherent system. A domain-building strand produces evidence; a verification strand challenges it; declared contingencies may refine the inputs once; the campaign then issues a transparent **GO** or **NO-GO** decision.

This repository is an independent software portfolio. It does not claim employment at, endorsement by, or operational deployment within any company whose problem domain inspired a demonstration.

## Run the proof

Requirements: Python 3.11 or newer.

```bash
python -m pip install -e ".[dev]"
python -m job_app_helix nominal
python -m job_app_helix recoverable --json
python -m job_app_helix.readme_mesh_cli validate
python -m job_app_helix.readme_mesh_cli build
pytest
```

The public core is self-contained. It does not require a specific home directory, private repositories, IDE state, or an external orchestration runtime.

### Built-in scenarios

| Scenario | Purpose | Expected result |
|---|---|---|
| `nominal` | All evidence begins inside the demonstrated envelope | `GO` |
| `recoverable` | Initial failures have explicitly declared contingency evidence | `NO-GO -> refine -> GO` |
| `hard-no-go` | Critical failures have no supplied contingency evidence | `NO-GO` |

## The model

1. **Piston** — one independently runnable assessment.
2. **Helix** — build and verification strands aimed at the same mission.
3. **Campaign** — several pistons composed into an end-to-end decision.
4. **Proof contract** — work is complete only when the stated problem is demonstrably solved.
5. **README Mesh** — one evidence-bound record rendered for human and machine audiences.

No component is allowed to silently modify values until it passes. No README claim is allowed to exist without an evidence pointer.

## Engineering qualities

- Typed immutable campaign inputs and result models
- Deterministic, fail-closed scenario execution
- Human-readable CLI and machine-readable JSON receipts
- Real Protocol Buffers schema, generated binding, binary round trip, ProtoJSON, textproto, and SHA-256
- Three-audience README rendering from one canonical record
- Typed, directional repository relationships
- Idempotent marker-based README updates that preserve human-authored material
- CI gates for lint, tests, Protobuf compilation, manifest validation, rendering, public-boundary hygiene, and artifact upload

## Repository map

```text
src/job_app_helix/       campaign and README Mesh engines
tests/                   executable behavioral and contract claims
proto/                   real glaciereq.readme.v1 schema
manifests/               reviewable repository nodes and typed edges
scripts/                 Protobuf and public-surface verification
.github/workflows/       reproducible GitHub evidence
docs/                    architecture, evidence, and README standards
```

Start with:

- [`src/job_app_helix/campaign.py`](src/job_app_helix/campaign.py) — campaign control flow
- [`src/job_app_helix/readme_mesh.py`](src/job_app_helix/readme_mesh.py) — validation, serialization, and rendering
- [`proto/readme_mesh.proto`](proto/readme_mesh.proto) — wire contract
- [`manifests/readme_mesh.json`](manifests/readme_mesh.json) — canonical mesh index
- [`tests/test_readme_mesh.py`](tests/test_readme_mesh.py) — executable documentation contract
- [`docs/README_MESH_STANDARD.md`](docs/README_MESH_STANDARD.md) — audience and evidence standard

## Evidence boundary

Generated IDE memory, local backups, machine-specific paths, private state, legal or family-case workstreams, forks, and unverifiable portfolio claims are excluded from the README Mesh. Visibility changes are not performed as a side effect of documentation work.

## License

MIT. See [`LICENSE`](LICENSE).
