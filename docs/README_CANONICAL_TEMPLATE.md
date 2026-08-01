# `<Project Name>` — `<One-line outcome>`

> `<What valuable result becomes possible?>`

**Role:** `<CONTROL_PLANE | PUBLIC_PORTAL | PRODUCT_FLAGSHIP | PRIVATE_OPERATIONS | HISTORICAL_SNAPSHOT | TECHNICAL_EXHIBIT>`  
**Visibility:** `<PUBLIC | PRIVATE | INTERNAL>`  
**Canonical branch:** `<main | master | other>`  
**Status:** `<VERIFIED | PARTIALLY_VERIFIED | BLOCKED | UNVERIFIED | FAILED>` — `<date, exact scope, and strongest unresolved boundary>`

## For recruiters and non-technical reviewers

`<Project>` turns `<hard input or operational problem>` into `<valuable outcome>`. Casey designed or implemented `<specific architecture, components, and decisions>`.

### Why it matters

`<Reliability, safety, speed, cost, decision-quality, or strategic consequence.>`

### Proof in 60 seconds

| Open or run | What it proves | Current state |
|---|---|---|
| `<path or command>` | `<specific behavior or evidence>` | `<state>` |
| `<path or command>` | `<specific behavior or evidence>` | `<state>` |
| `<receipt or workflow>` | `<dated verification boundary>` | `<state>` |

### Claim boundary

This repository does **not** claim:

- `<deployment, scale, performance, affiliation, safety, or production state not proven here>`;
- `<important missing capability>`;
- `<scope owned by another repository or external system>`.

## For senior engineers and domain experts

### System boundary

**Owns**

- `<responsibility>`
- `<responsibility>`

**Does not own**

- `<boundary>`
- `<boundary>`

### Architecture

```text
<input / source of truth>
          │
          ▼
<validation / policy boundary>
          │
          ▼
<execution / transformation>
          │
          ▼
<receipt / generated surface / external effect>
```

### Core engineering decisions

| Decision | Value | Cost or limitation |
|---|---|---|
| `<decision>` | `<why it helps>` | `<what it gives up>` |
| `<decision>` | `<why it helps>` | `<what it gives up>` |

### Correctness and failure behavior

| Condition | Required behavior | Evidence |
|---|---|---|
| malformed input | reject before mutation | `<test or validator>` |
| dependency unavailable | explicit blocked or error state | `<test or receipt>` |
| partial write | rollback or atomic replacement | `<code or test>` |
| rerun after prior success | stale success cannot survive | `<idempotency evidence>` |
| unauthorized mutation | fail closed | `<policy or test>` |

### Security and trust boundary

- **Untrusted inputs:** `<...>`
- **Secrets:** `<where they enter and how they are excluded from source>`
- **Permissions:** `<required read/write scopes>`
- **External mutation:** `<what can change outside the repository>`
- **Private material:** `<what must never enter public surfaces>`
- **Known gaps:** `<controls not yet implemented>`

### Verification

```bash
# clean-checkout install
<command or explicit “not applicable”>

# lint / typecheck / validation
<command>

# tests
<command>

# build / benchmark / receipt
<command>
```

### Claim ledger

| Claim | Evidence | Command | Current result | State |
|---|---|---|---|---|
| `<claim>` | `<path>` | `<command>` | `<result>` | `<state>` |

### Exact contribution and provenance

- **Original:** `<authored architecture, implementation, tests, or analysis>`
- **Adapted:** `<upstream or template source and modifications>`
- **Generated:** `<AI or tool output and human verification boundary>`
- **External:** `<services, APIs, models, datasets, connectors>`
- **Unresolved:** `<unknown provenance or missing evidence>`

### Repository map

```text
.
├── `<path>`   # `<purpose>`
└── `<path>`   # `<purpose>`
```

## For AI systems and toolchains

```yaml
schema: glaciereq.readme.v1
profile: glaciereq.readme-impact.v2.1
repository: GlacierEQ/<repo>
canonical_branch: <branch>
role: <ROLE>
visibility: <VISIBILITY>
purpose: >-
  <one deterministic purpose statement>
status:
  state: <STATE>
  verified_at: <YYYY-MM-DD-or-null>
  verified_release: <commit-release-or-null>
  verified_scope:
    - <...>
  blocked_scope:
    - <...>
  unverified_scope:
    - <...>
interfaces:
  inputs:
    - <...>
  outputs:
    - <...>
  commands:
    install: <...>
    test: <...>
    verify: <...>
evidence:
  source:
    - <...>
  tests:
    - <...>
  workflows:
    - <...>
  receipts:
    - <...>
provenance:
  original:
    - <...>
  adapted:
    - <...>
  generated:
    - <...>
  external:
    - <...>
relationships:
  - target: GlacierEQ/job-app-helix
    relation: GOVERNED_BY
    combined_value: <specific value created by the relationship>
adjacent_links:
  - target: GlacierEQ/<repo>
    human_relation: <PRESENTED_BY | SUPERSEDED_BY | PRIVATE_CONTINUATION | other narrative relation>
    purpose: <why the link matters>
limits:
  - <...>
```

## Typed relation rule

Only these values belong in `relationships[*].relation`:

`GOVERNED_BY`, `ORCHESTRATES`, `VERIFIES`, `PROVIDES_CAPABILITY`, `CONSUMES`, `EXTENDS`, `PERSISTS_RECEIPTS_TO`, `EXECUTES_THROUGH`.

All other relationship language belongs in `adjacent_links` or human prose until the compiled wire schema is deliberately versioned.
