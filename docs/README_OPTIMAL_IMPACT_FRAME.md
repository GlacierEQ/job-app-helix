# README Optimal Impact Frame — Recruiter, Expert, AI Mesh

## The README Is the Interface

Every portfolio README is an evidence interface. It must let three audiences reach the right conclusion without reverse-engineering the repository:

1. **Recruiter or hiring manager:** Should I care, and what should I open first?
2. **Principal engineer or domain expert:** Is the engineering real, bounded, and reviewable?
3. **AI system or toolchain:** What is this repository, what evidence exists, and how does it connect?

The README is not a marketing brochure, a code dump, a release note, or a substitute for tests. It is the highest-leverage navigation surface between claims and proof.

**Documentation profile:** `glaciereq.readme-impact.v2.1`  
**Machine schema:** `glaciereq.readme.v1`  
**Authority:** `GlacierEQ/job-app-helix`

## Header Voice Is Part of the Architecture

A README can be accurate and still erase the excellence of the work through lifeless section labels. Visible H2 headings must therefore carry a project-specific idea, tension, promise, or engineering truth. Audience orientation belongs immediately beneath the heading as a quiet italic subtitle.

**Required pattern**

```markdown
## Better Fit Without a Better Lie

*Recruiter lens · what the product changes and what it refuses to invent*
```

**Forbidden as visible primary headers**

- `## For recruiters and non-technical reviewers`
- `## For senior engineers and domain experts`
- `## For AI systems and toolchains`
- `## Portfolio mesh`

Those phrases may survive only as subtitles, accessibility cues, or hidden compatibility markers required by automation. The visible header must sound native to the repository; copying the same clever phrase across every project is merely a more decorative form of blandness.

## The Four-Act Read

```text
Title + one-line outcome
Repository role + visibility + verification status
Recruiter / non-technical impact layer
Proof in 60 seconds
Claim boundary and non-claims
Senior engineer / domain-expert layer
System boundary and architecture
Correctness, failure, security, and tradeoffs
Build / test / benchmark / receipt commands
Exact contribution and provenance
AI / toolchain contract
Typed portfolio mesh
Limits, non-goals, and unresolved work
```

A reader should never encounter a technology list before understanding the outcome, and should never encounter a material claim without a path to evidence.

## Every Repository Needs a Role, Not a Costume

The same architecture is applied differently according to repository role.

| Role | Primary reader | Required emphasis | Prohibited failure |
|---|---|---|---|
| `CONTROL_PLANE` | Portfolio owner, reviewer, automation | inventory, policy, verification, receipts, governance | presenting child-repository claims as inherited proof |
| `PUBLIC_PORTAL` | Recruiter, hiring manager | concentrated signal, review sequence, public evidence boundaries | leaking private operations or inflating portfolio state |
| `PRODUCT_FLAGSHIP` | Product and engineering reviewers | behavior, trust boundary, user flow, tests, product gaps | treating build or source presence as deployment proof |
| `PRIVATE_OPERATIONS` | Candidate or operator | application lifecycle, target state, privacy, audit discipline | copying contacts, credentials, or live outreach into public surfaces |
| `HISTORICAL_SNAPSHOT` | Maintainer, AI curator | date, original intent, current authority boundary, successor | presenting historical counts or plans as current operating truth |
| `TECHNICAL_EXHIBIT` | Domain expert | one differentiated technical problem and its proof path | generic capability claims disconnected from repository-native evidence |

The role must be stated near the top of the README and repeated in the machine block.

## The First Screen Must Earn the Second

*Recruiter and non-technical impact layer*

This layer should take 30–60 seconds to read.

### Required content

- **Outcome:** one sentence describing what becomes possible.
- **Problem:** the real operational or technical difficulty.
- **Contribution:** what Casey designed, implemented, integrated, repaired, or verified.
- **Why it matters:** reliability, safety, speed, cost, decision quality, or strategic leverage.
- **Repository role:** one role from the table above.
- **Visibility:** `PUBLIC`, `PRIVATE`, or `INTERNAL`.
- **Current status:** `VERIFIED`, `PARTIALLY_VERIFIED`, `BLOCKED`, `UNVERIFIED`, or `FAILED`, with date and exact scope.
- **Proof panel:** two to five artifacts or one runnable command that provides a useful review path.
- **Non-claims:** the most important things the repository does not prove.

### Strong pattern

```markdown
# Product Name — Outcome

> One sentence describing the valuable result.

**Role:** PRODUCT_FLAGSHIP  
**Visibility:** PUBLIC  
**Status:** PARTIALLY_VERIFIED — core contract tests pass; deployment remains unverified.

## The Problem Stops Here

*Recruiter lens · 60-second review*

[Project] turns [hard input or state] into [valuable outcome].
Casey designed [specific components and decisions].

### Sixty Seconds to Belief

| Open or run | What it proves |
|---|---|
| `src/...` | Core behavior |
| `tests/...` | Adversarial and nominal correctness |
| `command ...` | Reproducible verification |
| `artifact ...` | Dated receipt |

### Claim boundary

This repository does not claim [deployment, performance, affiliation, or scale].
```

### Prohibited patterns

- “Revolutionary,” “world-class,” “production-grade,” “federal-grade,” or “enterprise-ready” without current receipts.
- Company affiliation, deployment, capacity, scale, performance, safety, security, or cost claims not demonstrated by the repository.
- Repository counts used as a proxy for quality.
- Badges that imply checks, releases, or deployments not tied to live evidence.
- “Ready,” “complete,” or “operational” when the repository only contains plans, scripts, or documentation.
- Personal, legal, medical, financial, or private outreach content on a public recruiter surface.
- A status checklist that silently mixes completed documentation with unverified execution.

## Proof in 60 seconds

Every README must provide a compact proof table. Review paths are chosen by evidence value, not by file prestige.

| Evidence class | Strong example | Weak substitute |
|---|---|---|
| Behavior | executable test or deterministic demo | architecture prose |
| Correctness | adversarial tests, invariants, validation | “works as intended” |
| Build | clean-checkout build command and CI receipt | dependency manifest alone |
| Performance | benchmark, environment, and dated result | unqualified speed claim |
| Deployment | provider URL, ID, date, or release receipt | source code or Dockerfile |
| Provenance | original, adapted, and generated boundary | generic “built by” statement |
| Portfolio relationship | typed edge and combined value | untyped link list |

## Claims on Trial

Material claims should be reviewable as a ledger.

| Claim | Evidence | Command | Result | State |
|---|---|---|---|---|
| Core behavior | `src/...` | `...` | concise current result | VERIFIED / ... |
| Correctness | `tests/...` | `...` | positive proof count | VERIFIED / ... |
| Build | workflow or local receipt | `...` | clean-checkout result | VERIFIED / ... |
| Deployment | provider receipt | `...` | URL, ID, and date | UNVERIFIED / ... |

Rules:

1. A higher evidence level cannot be inferred from a lower one.
2. A passing command with zero tests is not test evidence.
3. A README is documentation evidence only.
4. A historical result retains its date and original boundary.
5. `BLOCKED`, `UNVERIFIED`, and `FAILED` may never be rewritten as passed.

## Where the Claim Meets the Workbench

*Principal engineers, architects, and masters of the trade*

This layer must reward expert scrutiny.

### Required content

1. **System boundary:** what the repository owns and deliberately does not own.
2. **Architecture:** components, state, interfaces, inputs, outputs, and data or control flow.
3. **Core innovation:** the non-obvious design decision, algorithm, or integration.
4. **Correctness model:** invariants, validation, deterministic behavior, proofs, or error bounds.
5. **Failure behavior:** malformed input, dependency failure, partial state, retries, idempotency, rollback, and stale state.
6. **Security boundary:** trust assumptions, secrets, permissions, path or input safety, supply-chain controls, and data exposure.
7. **Tradeoffs:** why the architecture was selected and what it gives up.
8. **Verification:** clean-checkout install, lint, typecheck, build, test, benchmark, and receipt commands.
9. **Evolution:** what changed from prototype to current architecture.
10. **Exact contribution:** original work, adapted upstream work, generated code, external services, and unresolved provenance.

### Architecture guidance

Prefer a small diagram that names control and evidence flow:

```text
source of truth
      │
      ▼
validation / policy
      │
      ▼
execution / transformation
      │
      ▼
receipt / generated surface
```

A diagram must clarify ownership or failure behavior. Decorative diagrams do not satisfy the architecture requirement.

### Correctness and failure table

| Condition | Expected behavior | Evidence |
|---|---|---|
| malformed input | reject before state mutation | test or validator |
| dependency unavailable | surface explicit blocked or error state | test or receipt |
| partial write | rollback or atomic replacement | code or test |
| rerun after prior success | stale success cannot survive | idempotency test |
| unauthorized mutation | fail closed | policy or test |

### Security boundary

At minimum, state:

- where secrets may enter;
- which files must remain private;
- what inputs are untrusted;
- what permissions are required;
- whether network, filesystem, shell, or connector actions can mutate external state;
- what the repository does not currently protect against.

Private operational repositories additionally document:

- public and private export boundaries;
- contact and outreach confidentiality;
- prohibition on publishing credentials or application tracking;
- redaction expectations before material is copied into public repositories.

### Tradeoffs

Every major design choice should include both value and cost.

| Decision | Value | Cost or limitation |
|---|---|---|
| deterministic manifest | reproducible public surface | requires synchronized updates |
| fail-closed validation | prevents unsupported output | rejects some recoverable cases |
| private operational split | protects outreach and tracking | requires explicit synchronization |
| historical preservation | retains provenance | can confuse readers without a successor boundary |

## Every Language Must Earn Its Seat

A language or format is justified only when it owns a real boundary.

| Language or format | Responsibility | Boundary | Interface contract | Build command | Test or proof command | Receipt | State |
|---|---|---|---|---|---|---|---|

Acceptance requires:

1. named responsibility;
2. clear boundary;
3. interface contract;
4. build or validation command;
5. test, proof, or benchmark command;
6. evidence receipt or explicit absence;
7. current verification state.

A language used only to increase the language count must be removed or moved to a clearly labeled learning or exhibit directory outside the production architecture.

## Fingerprints: What Is Actually Ours

Every recruiter-facing README distinguishes:

- **Original:** authored architecture, code, tests, or analysis.
- **Adapted:** upstream or template-derived work, with source and modifications.
- **Generated:** AI- or tool-generated material and the human verification boundary.
- **External:** hosted services, APIs, models, datasets, and connectors.
- **Unknown or unresolved:** provenance that has not yet been established.

Forks and imported projects must never be presented as original portfolio work merely because they exist under the account.

## The Machine Handshake and the Living Mesh

*AI ingestion, deterministic contracts, and portfolio relationships*

The machine block must be deterministic, compact, versioned, and consistent with the human claim boundary.

```yaml
schema: glaciereq.readme.v1
profile: glaciereq.readme-impact.v2.1
repository: GlacierEQ/example
canonical_branch: main
role: PRODUCT_FLAGSHIP
visibility: PUBLIC
purpose: ...
status:
  state: PARTIALLY_VERIFIED
  verified_at: 2026-07-31
  verified_release: <commit-or-release-id-or-null>
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
provenance:
  original: [...]
  adapted: [...]
  generated: [...]
  external: [...]
relationships:
  - target: GlacierEQ/job-app-helix
    relation: GOVERNED_BY
    combined_value: ...
limits:
  - ...
```

### Typed relationship enum

Machine-facing `relation` values must match the compiled `glaciereq.readme.v1` enum exactly:

- `GOVERNED_BY`
- `ORCHESTRATES`
- `VERIFIES`
- `PROVIDES_CAPABILITY`
- `CONSUMES`
- `EXTENDS`
- `PERSISTS_RECEIPTS_TO`
- `EXECUTES_THROUGH`

Concepts such as `PRESENTS`, `PRESENTED_BY`, `SUPERSEDES`, `EXCLUDES_FROM_PUBLIC_SURFACE`, or `ARCHIVED_BY` are useful human relationships but are **not typed edges** until the wire schema is deliberately versioned. Put them in `adjacent_links` or narrative prose, not in `relationships`.

A link without a supported relation and a concrete combined value is not a mesh edge.

## The Mesh Cannot Contradict Itself

For the hiring portfolio:

1. `job-app-helix` is the README and evidence authority.
2. `job-application` is the public recruiter entrypoint.
3. `JOB-RESUME-BUILDER-` is the lead product flagship.
4. `job-app` is private application operations and must not be implied public.
5. Historical portfolio-planning repositories identify their snapshot date and current successor.
6. Public portals may summarize child repositories but may not promote them beyond repository-native proof.
7. Private operational state may be summarized publicly only after redaction and deliberate export.
8. Repository identity, visibility, status, and typed edges must not contradict the Helix manifests.

## Status Words Must Mean Something

- **VERIFIED:** the stated scope passed a reproducible current check.
- **PARTIALLY_VERIFIED:** named parts passed; named parts remain blocked or untested.
- **BLOCKED:** verification could not run because a dependency, toolchain, permission, service, or hardware prerequisite is unavailable.
- **UNVERIFIED:** no current authoritative receipt exists.
- **FAILED:** a verification command ran and failed.

The status belongs to a named scope, not to the repository as an emotional grade.

## The Door Does Not Open Until

A README is ready to place in an application only when:

- the first screen states outcome, contribution, role, visibility, status, and proof;
- every material claim points to evidence or is explicitly labeled unverified;
- the quick-start or verification path works from a clean checkout, or the blocker is named;
- architecture, failure behavior, security, tradeoffs, and exact contribution are documented;
- language choices are functional and machine-declared;
- AI metadata is deterministic and uses only compiled typed relations;
- private and historical repositories have explicit public-authority boundaries;
- limits and unresolved areas are visible without scrolling to a disclaimer graveyard.

## Final Pass: No Dead Headers, No Hollow Claims

```text
[ ] Outcome appears before technology list
[ ] Role and visibility are explicit
[ ] Status includes scope and date
[ ] Proof panel uses current repository artifacts
[ ] Non-claims are near the top
[ ] System boundary is explicit
[ ] Architecture diagram clarifies control or evidence flow
[ ] Correctness and failure behavior are documented
[ ] Security and private-data boundaries are documented
[ ] Tradeoffs are stated
[ ] Verification commands are copyable
[ ] Exact contribution and provenance are separated
[ ] Machine block matches human claims
[ ] Typed relations use the compiled enum only
[ ] Adjacent narrative links are not mislabeled typed edges
[ ] Historical counts and statuses retain dates
[ ] Public surfaces do not expose private operations
```
