# Curated Portfolio Map

This map describes how Job-App Helix connects to Casey Barton's broader systems practice without turning the repository into a mirror of a private workstation.

## Tier 1 — Public proof

| Surface | Purpose | Evidence |
|---|---|---|
| Campaign engine | Compose typed assessments into one decision | `src/job_app_helix/` |
| Behavioral contract | Prove nominal, recoverable, and hard-failure behavior | `tests/` |
| Public boundary | Reject machine paths, generated memory, legal identifiers, suspicious credential patterns, and broken relative links | `scripts/check_public_surface.py` |
| Independent verification | Re-run the same claims on clean GitHub runners | `.github/workflows/ci.yml` |

## Tier 2 — Engineering capabilities represented

| Capability | Demonstrated here |
|---|---|
| Systems architecture | Explicit boundaries, typed handoffs, composable stages |
| Verification engineering | Stable findings, fail-closed decisions, proof receipts |
| Agent and automation design | Human-readable and machine-readable execution surfaces |
| Infrastructure reasoning | Capacity, telemetry, contingency, and operational-state modeling |
| Portfolio governance | Claims and limits documented beside the code |

## Tier 3 — Broader portfolio domains

The wider GlacierEQ portfolio explores agent operating systems, context discipline, compute and thermal models, aerospace-aligned software demonstrations, MCP integrations, and multi-repository orchestration. Those projects are supporting exhibits; this repository does not import them or require them to run.

## Tier 4 — Human hiring surface

- [`README.md`](README.md) — first-click explanation and runnable proof
- [`hire_package/RESUME_CASEY_GLACIEREQ.md`](hire_package/RESUME_CASEY_GLACIEREQ.md) — concise resume grounded in demonstrable work
- [`docs/CLAIMS_AND_LIMITS.md`](docs/CLAIMS_AND_LIMITS.md) — credibility boundary
- [GlacierEQ on GitHub](https://github.com/GlacierEQ) — broader public account

## Exclusions

This map intentionally excludes legal and family-case systems, private evidence, generated IDE state, local filesystem topology, and unverified score claims.
