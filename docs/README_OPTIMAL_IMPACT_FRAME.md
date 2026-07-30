# README Optimal Impact Frame — Recruiter, Expert, AI Mesh

## Objective

Every portfolio README must answer three different questions, in order:

1. **Should I care?** — recruiter, hiring manager, executive, non-specialist.
2. **Is the engineering real?** — principal engineer, architect, domain expert.
3. **Can a machine understand and connect it?** — AI agent, MCP toolchain, portfolio graph.

The README is not marketing copy, a design diary, or a code dump. It is a compact evidence interface between the work and the reader.

## Required ordering

```text
Title + one-line outcome
Verification status
Recruiter / non-technical impact layer
Proof in 60 seconds
Senior engineer / domain-expert layer
Architecture and data/control flow
Correctness, failure modes, security, tradeoffs
Build, test, benchmark, and receipt commands
Evolution and exact contribution
AI / toolchain contract
Typed portfolio mesh
Machine-readable metadata
Limits, non-goals, and claim boundary
```

## Layer 1 — Recruiter and non-technical impact

This layer should take 30–60 seconds to read.

### Required content

- **Outcome:** one sentence describing what becomes possible.
- **Problem:** the real operational or technical difficulty.
- **Casey’s contribution:** what was designed, implemented, integrated, or verified.
- **Why it matters:** business, reliability, safety, cost, speed, or strategic value.
- **Proof panel:** 2–4 openable artifacts or one runnable command.
- **Current status:** `VERIFIED`, `PARTIALLY VERIFIED`, `BLOCKED`, `UNVERIFIED`, or `FAILED`, with date and scope.

### Strong pattern

```markdown
## What this proves

[Project] turns [hard input/state] into [valuable verified outcome].
I designed [specific architecture/components], including [two differentiators].

**Current status:** PARTIALLY VERIFIED — core engine and contract tests pass;
hardware-backed execution remains unverified.

**Proof in 60 seconds**
- Run: `...`
- Inspect: `src/...`
- Tests: `tests/...`
- Receipt: `artifacts/...`
```

### Prohibited patterns

- “Revolutionary,” “world-class,” “production-grade,” or “enterprise-ready” without receipts.
- Long technology lists before the reader understands the outcome.
- Generic “why this matters” paragraphs repeated across repositories.
- Claims of company affiliation, deployment, scale, safety, or performance not demonstrated by the repository.
- Portfolio-wide grades in an individual README.

## Layer 2 — Masters of the trade

This layer must make expert scrutiny rewarding.

### Required content

1. **System boundary:** what this repository owns and deliberately does not own.
2. **Architecture:** components, state, inputs/outputs, data/control flow, and interfaces.
3. **Core innovation:** the non-obvious design or algorithm.
4. **Correctness model:** invariants, validation, deterministic behavior, proofs, or error bounds.
5. **Failure behavior:** malformed input, dependency failure, partial state, retries, idempotency, rollback.
6. **Security boundary:** trust assumptions, secrets, permissions, path/input safety, supply-chain controls.
7. **Tradeoffs:** why this architecture was selected and what it gives up.
8. **Verification:** clean-checkout build, lint, typecheck, test, benchmark, and receipt commands.
9. **Evolution:** what changed from prototype to current architecture.
10. **Exact contribution:** distinguish original work, adapted upstream work, generated code, and external systems.

### Evidence table

| Claim | Evidence | Command | Current result |
|---|---|---|---|
| Core behavior | `src/...` | `...` | verified / blocked / failed |
| Correctness | `tests/...` | `...` | N passed |
| Performance | `bench/...` | `...` | result + environment |
| Contract | `proto/...` | `...` | compiled + round-tripped |
| Deployment | provider receipt | `...` | URL/ID/date or unverified |

## Language-fit gate

A language is justified only when it owns a real boundary.

For every language or format, document every required field separately:

| Language / format | Responsibility | Boundary | Interface contract | Build / compile command | Test / proof / benchmark command | Evidence receipt | State |
|---|---|---|---|---|---|---|---|
| Rust | ... | ... | ... | `cargo build` | `cargo test` | `artifacts/...` | VERIFIED / BLOCKED / UNVERIFIED |

Acceptance requires all six substantive elements plus an explicit state:

1. named responsibility;
2. clear boundary;
3. interface contract;
4. build/compile command;
5. test/proof/benchmark command;
6. evidence receipt;
7. current verification state.

These fields must also exist in a machine-readable language-fit manifest so the audit can reject incomplete declarations. A language used only to increase the language count must be removed or moved to a clearly labeled learning/exhibit directory outside the production architecture.

## Layer 3 — AI ingestion and portfolio mesh

This layer must be deterministic, compact, and versioned.

### Required machine fields

The machine block must use the current compiled wire schema. Documentation-profile evolution must be identified separately so prose requirements do not pretend a new Protobuf package already exists.

```yaml
schema: glaciereq.readme.v1
profile: glaciereq.readme-impact.v2-draft
repository: GlacierEQ/example
canonical_branch: main
purpose: ...
status:
  state: PARTIALLY_VERIFIED
  verified_at: 2026-07-29
  verified_release: <commit-or-release-id>
  verified_scope:
    - ...
  blocked_scope:
    - ...
  unverified_scope:
    - ...
interfaces:
  inputs: [...]
  outputs: [...]
  commands:
    install: ...
    test: ...
    verify: ...
evidence:
  source: [...]
  tests: [...]
  workflows: [...]
  receipts: [...]
languages:
  - name: Rust
    responsibility: ...
    boundary: ...
    interface_contract: ...
    build_command: ...
    test_command: ...
    evidence_receipt: ...
    verification_state: ...
relationships:
  - target: GlacierEQ/AKOS
    relation: governed_by
    combined_value: ...
limits:
  - ...
```

### Typed relationship verbs

Use directional verbs such as:

- `governed_by`
- `orchestrates`
- `verified_by`
- `provides_capability_to`
- `consumes`
- `extends`
- `persists_receipts_for`
- `routes_execution_to`
- `shares_contract_with`

A link without a relationship and combined value is not a mesh edge.

## Verification-status semantics

- **VERIFIED:** the stated scope passed a reproducible current check.
- **PARTIALLY VERIFIED:** named parts passed; named parts remain blocked or untested.
- **BLOCKED:** verification could not run because a dependency, toolchain, permission, service, or hardware prerequisite is unavailable.
- **UNVERIFIED:** no current authoritative receipt exists.
- **FAILED:** a verification command ran and failed.

Never convert `BLOCKED` or `UNVERIFIED` into `PASSED`.

## Tone

- Clear enough for a strong generalist.
- Precise enough for a principal engineer.
- Confident because evidence is visible, not because adjectives are loud.
- Humanized through decisions, constraints, and consequences.
- No mythology or grandiosity unless it is clearly project branding and never substitutes for engineering facts.

## Minimum recruiter-ready gate

A README is ready to place in an application only when:

- the first screen states outcome, contribution, status, and proof;
- every material claim points to evidence;
- the quick start works from a clean checkout;
- architecture and failure behavior are documented;
- language choices are functional and machine-declared;
- AI metadata parses deterministically;
- typed edges explain combined value;
- limits and unverified areas are explicit.
