# Proof-Weighted Portfolio Audit Standard

**Canonical owner:** `GlacierEQ/job-app-helix`  
**Audit date:** 2026-07-29  
**Purpose:** Grade portfolio repositories by what the current repository can actually prove, while preserving strong human communication and machine-readable portfolio topology.

## Why this standard exists

A portfolio loses credibility when a polished README, a sidecar, a file hash, or an ambitious architecture statement receives the same weight as executable software. This standard separates concept strength from implementation proof and makes every score explainable.

The audit never treats any of the following as proof that a product works:

- a repository existing;
- a README claiming success;
- a source file compiling in theory;
- a sidecar returning `OPERATIONAL` without executing the product;
- a static SHA-256 manifest;
- tests that reproduce hard-coded values without importing or invoking the advertised implementation;
- benchmark numbers without a reproducible benchmark harness and receipt;
- links to local `file:///` paths;
- generated portfolio scores that assign blanket grades.

## Score model — 100 points

| Dimension | Weight | What earns the score |
|---|---:|---|
| **Actual function and verification** | 30 | Current implementation exists; tests invoke it; build/run commands are valid; CI or a reproducible execution receipt confirms behavior, including failure paths. |
| **Completeness** | 20 | The advertised product loop is closed: inputs, core behavior, outputs, error handling, configuration, documentation, and verification are present. |
| **Engineering quality** | 20 | Clear boundaries, typed contracts, validation, deterministic behavior where appropriate, maintainable structure, security hygiene, and meaningful tests. |
| **Innovation** | 15 | A defensible architectural contribution or unusual synthesis that addresses a real bottleneck. Novel names alone do not score. |
| **README impact** | 10 | Three calibrated audience layers, clear quick start, evidence-linked claims, limitations, and no unsupported numbers or inaccessible links. |
| **Mesh and technology fit** | 5 | Directional relationships are meaningful; machine-readable identity exists; language choices follow Tower of Babel boundaries and measurably improve the system. |

## Verification states

| State | Meaning | Maximum functionality score |
|---|---|---:|
| **V4 — current verified** | Current branch/head has green CI or a reproducible execution receipt covering the advertised implementation. | 30 |
| **V3 — previously verified / current docs-only drift** | A known release commit was independently verified; current changes are documentation or metadata only and do not invalidate that implementation. | 25 |
| **V2 — locally testable / partial proof** | Source and tests exist, but current independent CI is absent, tests are narrow, or only part of the advertised function is exercised. | 20 |
| **V1 — illustrative implementation** | Runnable or compilable example exists, but it is a bounded demonstration and the broader product claim is unverified. | 12 |
| **V0 — declared only / failing / unavailable** | Advertised source is missing, tests do not invoke it, execution fails, or no reproducible path is present. | 5 |

A repository may have excellent innovation and still receive a modest overall score if it is not executable. This is intentional.

## README acceptance contract

Every portfolio README must present the same truth through three different views.

### 1. Recruiter and non-technical view

The opening must answer, without jargon:

- What important bottleneck does this solve?
- What did Casey build?
- Why does it matter to an organization?
- What can a reviewer verify in five minutes?

This section must be human, specific, and brief. It must not begin with internal mythology, unsupported scale numbers, or a wall of implementation details.

### 2. Master-of-the-trade view

The middle must expose:

- architecture and ownership boundaries;
- why each language or format owns its layer;
- typed inputs and outputs;
- failure modes and limits;
- tradeoffs and rejected alternatives;
- test, benchmark, proof, and security evidence;
- current maturity and next engineering step.

### 3. AI and interconnection view

The final section must provide:

- canonical repository identity and role;
- machine-readable contracts and schema packages;
- capabilities, commands, inputs, outputs, and limitations;
- evidence paths;
- typed directional relationships to providers, consumers, verifiers, extenders, orchestrators, and governors;
- Tower of Babel technology ownership;
- deterministic artifact or receipt references where available.

The AI section may be compact, but it must be precise enough for an agent to connect the repository without inventing missing behavior.

## Claim calibration

Use these verbs according to proof:

- **implements / verifies / passes** — only when the current evidence directly supports the statement;
- **models / demonstrates / prototypes** — for bounded portfolio implementations;
- **is designed to / could extend to** — for architectural intent;
- **does not yet** — for honest limitations.

Never use `production-grade`, `enterprise-ready`, `flight-ready`, `zero failures`, `100%`, throughput, latency, scale, safety, deployment, or employment claims without direct evidence linked in the same repository.

## Tower of Babel technology rule

Language diversity is valuable only when the repository can state:

- **What** the technology owns;
- **Where** it lives in the architecture;
- **When** it is activated;
- **Why** it is superior for that boundary;
- an easy example;
- an advanced example;
- a proof or benchmark gate.

The Tower of Babel is the authority for language and format placement. Job-App Helix consumes those contracts; it does not duplicate or improvise technology doctrine.

## Portfolio admission classes

- **Canonical mesh:** original, public, evidence-verifiable repositories admitted to the typed README graph.
- **Candidate:** potentially valuable original work awaiting proof or public-boundary review.
- **Supporting reference:** fork, vendor mirror, sample, upstream dependency, or external codebase; useful context but not scored as Casey-authored product.
- **Private or excluded:** legal/family/private evidence, credentials, mixed personal workstreams, or repositories unsuitable for public hiring claims.
- **Archive/retired:** preserved history, not active product proof.

Only canonical mesh repositories contribute to headline portfolio metrics.

## Definition of `works`

A repository is reported as working only when the audit records:

1. the exact branch and commit;
2. the command executed or CI workflow;
3. the implementation path exercised;
4. the test/build/proof result;
5. blockers or hardware dependencies;
6. the date of verification.

Anything less receives a calibrated state rather than a binary success claim.
