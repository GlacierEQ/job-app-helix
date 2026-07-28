# Public Readiness

**Status:** reproducible portfolio proof with a separate workspace integration layer.

This document replaces locally generated “production readiness” claims with evidence a public reviewer can independently reproduce.

## Public acceptance gates

A commit is publicly green only when GitHub Actions confirms:

1. Python source compiles.
2. Unit tests pass.
3. The nominal campaign returns `GO`.
4. The recoverable campaign demonstrates `NO-GO → GO`.
5. The terminal campaign fails closed with `NO-GO`.
6. A proof receipt is generated.
7. Public entry documents contain no absolute workstation links.
8. Generated IDE memory and legal-project paths are absent from the tracked public tree.

Workflow: [`.github/workflows/ci.yml`](.github/workflows/ci.yml).

## Public fixture mode

**Entry point:** `python -m helix.public_runtime`

- Standard-library Python
- Deterministic fixtures
- No network calls
- No private repositories
- No symlink assumptions
- No writes outside the selected receipt path
- Machine-readable output with SHA-256 proof hash

This proves architecture and control flow. It does not prove flight certification, production datacenter integration, or company employment.

## Workspace integration mode

**Entry point:** `helix/automations/jobapp_helix_spiral.py`

This runner composes implementations from the wider GlacierEQ workspace and may depend on sibling repositories, state directories, optional memory services, and local configuration. It is not represented as self-contained. See [docs/REPOSITORY_BOUNDARIES.md](docs/REPOSITORY_BOUNDARIES.md).

## Claim calibration

| Statement | Status |
|---|---|
| The helix model runs from a fresh clone | **Supported in fixture mode** |
| Terminal faults fail closed | **Supported by tests and CLI exit status** |
| The wider workspace can be orchestrated locally | **Supported when declared dependencies exist** |
| All portfolio repositories are production-grade | **Not claimed** |
| This is flight-certified or deployed at a named company | **Not claimed** |
| Local workspace audit equals GitHub CI | **Rejected** |
| A local file proves a public link works | **Rejected** |

## Remaining limitations

- Fixture mode uses representative deterministic models rather than live hardware.
- Workspace mode still needs a configuration adapter to replace legacy default paths.
- The broader repository family has uneven depth.
- Historical commits may contain material removed from the current tree; this PR does not rewrite history.

## Release rule

Do not label the repository “production ready” without a named production target, deployment evidence, service objectives, threat model, and operational ownership.

Accurate description:

> **A reproducible, proof-driven portfolio control plane with an optional multi-repository workspace integration.**
