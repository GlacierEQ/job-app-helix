# Proof-Weighted Portfolio Audit Standard

**Source-bound owner:** `GlacierEQ/job-app-helix`
**Effective date:** 2026-07-30
**Purpose:** Grade portfolio repositories by what the current repository can actually prove while preserving strong human communication and machine-readable topology.

## Why this standard exists

A portfolio loses credibility when a polished README, a sidecar, a file hash, or an ambitious architecture statement receives the same weight as executable software. This standard separates concept strength from implementation proof and makes every score explainable.

The audit never treats any of the following as proof that a product works:

- a repository existing;
- a README claiming success;
- a source file compiling in theory;
- a sidecar returning `OPERATIONAL` without executing the product;
- a static SHA-256 manifest;
- tests that reproduce hard-coded values without invoking the advertised implementation;
- benchmark numbers without a reproducible harness and receipt;
- links to machine-local paths;
- generated portfolio scores that assign blanket grades.

## Score model — 100 points

| Dimension | Weight | What earns the score |
|---|---:|---|
| **Actual function and verification** | 30 | Current implementation exists; tests invoke it; build and run commands are valid; CI or a reproducible receipt confirms behavior and failure paths. |
| **Completeness** | 20 | The advertised product loop is closed: inputs, behavior, outputs, errors, configuration, documentation, and verification are present. |
| **Engineering quality** | 20 | Clear boundaries, typed contracts, validation, deterministic behavior where appropriate, maintainable structure, security hygiene, and meaningful tests. |
| **Innovation** | 15 | A defensible architectural contribution or unusual synthesis addresses a real bottleneck. Novel names alone do not score. |
| **README impact** | 10 | Three calibrated audience depths, a clear quick start, evidence-linked claims, limitations, and no unsupported numbers or inaccessible links. |
| **Mesh and technology fit** | 5 | Relationships are meaningful, machine identity exists, and language choices own real boundaries with measurable benefit. |

## Verification states

| State | Meaning | Maximum function score |
|---|---|---:|
| **V4 — current verified** | Current head has green CI or a reproducible receipt covering the advertised implementation. | 30 |
| **V3 — release verified** | A known release was independently verified and current changes do not invalidate that implementation. | 25 |
| **V2 — partial proof** | Source and tests exist, but independent CI is absent, narrow, or covers only part of the advertised function. | 20 |
| **V1 — illustrative** | Runnable or compilable example exists, but the broader product claim remains unverified. | 12 |
| **V0 — declared, failing, or unavailable** | Source is missing, tests do not invoke it, execution fails, or no reproducible path exists. | 5 |

A repository may have excellent innovation and still receive a modest total if it is not executable. This is intentional.

## README acceptance contract

Every portfolio README presents the same truth through three natural depths.

### Strategic entry

The opening answers:

- What important bottleneck does this solve?
- What did Casey build?
- Why does it matter?
- What can a reviewer verify in five minutes?

It begins with value and evidence, not internal mythology, unsupported scale, or a wall of implementation details.

### Engineering depth

The middle exposes:

- architecture and ownership boundaries;
- why each technology owns its layer;
- typed inputs and outputs;
- failure modes and limits;
- tradeoffs and rejected alternatives;
- tests, benchmarks, proof, and security evidence;
- current maturity and the next engineering gate.

### Machine entrypoint

The final depth provides:

- reference repository identity and role;
- schemas and machine-readable contracts;
- capabilities, commands, inputs, outputs, and limitations;
- evidence paths;
- typed relationships to providers, consumers, verifiers, extenders, orchestrators, and governors;
- technology ownership;
- deterministic artifact or receipt references.

The machine section may be compact, but it must be precise enough for an agent to connect the repository without inventing behavior.

## Claim calibration

Use verbs according to proof:

- **implements / verifies / passes** — current evidence directly supports the statement;
- **models / demonstrates / prototypes** — a bounded implementation exists;
- **is designed to / could extend to** — architectural intent only;
- **does not yet** — an explicit limitation.

Never use `production-grade`, `enterprise-ready`, `flight-ready`, `zero failures`, `100%`, throughput, latency, scale, safety, deployment, or employment claims without direct evidence linked in the same repository.

## Technology placement rule

Language diversity is valuable only when the repository can state:

- what the technology owns;
- where it lives;
- when it is activated;
- why it is superior for that boundary;
- a simple example;
- an advanced example;
- a proof or benchmark gate.

Tower of Babel is the technology-placement authority. Job-App Helix consumes those contracts; it does not duplicate or improvise technology doctrine.

## Portfolio admission classes

- **Source-bound mesh:** original, public, evidence-verifiable repositories admitted to the typed graph.
- **Candidate:** potentially valuable original work awaiting proof or public-boundary review.
- **Supporting reference:** fork, vendor mirror, sample, upstream dependency, or external codebase.
- **Private or excluded:** credentials, personal evidence, mixed private workstreams, or repositories unsuitable for public hiring claims.
- **Archive or retired:** preserved history, not active product proof.

Only reference mesh repositories contribute to headline portfolio metrics.

## Definition of `works`

A repository is reported as working only when the audit records:

1. the exact branch and commit;
2. the command or CI workflow;
3. the implementation path exercised;
4. the test, build, or proof result;
5. blockers or hardware dependencies;
6. the verification date.

Anything less receives a calibrated state rather than a binary success claim.
