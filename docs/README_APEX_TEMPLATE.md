# `<Project Name>` — `<One-line capability outcome>`

> `<What stronger result becomes possible because this system exists?>`

**Role:** `<CONTROL_PLANE | PRODUCT_FLAGSHIP | SPECIALIST_COMPONENT | PRIVATE_OPERATIONS | TECHNICAL_EXHIBIT | HISTORICAL_SNAPSHOT>`  
**Visibility:** `<PUBLIC | PRIVATE | INTERNAL>`  
**APEX source branch:** `<main | master | other>`  
**Current proof:** `<VERIFIED | PARTIALLY_VERIFIED | BLOCKED | UNVERIFIED | FAILED>` — `<date and exact scope>`

## The frontier this project owns

`<State the consequential problem, the present bottleneck, and the strongest intended architecture. Do not shrink the target to match current implementation.>`

### APEX target

- **Capability:** `<what it should ultimately do>`
- **Intelligence:** `<reasoning/adaptation/learning boundary>`
- **Reliability:** `<failure isolation, recovery, observability, rollback>`
- **Leverage:** `<what one implementation unlocks elsewhere>`
- **Composability:** `<systems/interfaces it strengthens>`
- **Reach:** `<users/domains/systems affected>`
- **Frontier fitness:** `<how it uses the best technology currently available>`

### Current / gap / next

| Layer | State |
|---|---|
| CURRENT / PROVEN | `<what exact source and tests prove now>` |
| APEX TARGET | `<strongest coherent intended system>` |
| GAP | `<what still has to be built or proven>` |
| FRONTIER | `<credible current technologies or designs worth testing>` |

## Tower of Babel boundary map

| Lane | Concern | Technology | Why this technology owns the lane | Interface | Proof | Replacement trigger |
|---|---|---|---|---|---|---|
| `<kernel>` | `<runtime>` | `<Rust/Zig/C++/...>` | `<measurable fit>` | `<ABI/schema/protocol>` | `<tests/runtime>` | `<what would displace it>` |
| `<memory>` | `<durable/graph/vector/...>` | `<SQL/Datalog/...>` | `<measurable fit>` | `<schema/protocol>` | `<recovery/query tests>` | `<what would displace it>` |

One language or twelve are both valid. Each lane must earn its existence at the boundary.

## Proof in 60 seconds

| Open or run | What it proves | Current state |
|---|---|---|
| `<path or command>` | `<specific behavior>` | `<state>` |
| `<path or command>` | `<failure or adversarial behavior>` | `<state>` |
| `<receipt/workflow/runtime>` | `<exact verified boundary>` | `<state>` |

## Preservation ledger

| Prior gain | Current owner | Preserved? | Evidence |
|---|---|---:|---|
| `<capability>` | `<lane/component>` | `<yes/no/partial>` | `<path/receipt>` |

A refactor, migration, or technology replacement is incomplete while a required prior gain disappears without an explicit stronger replacement.

## Architecture

```text
<source/input>
      │
      ▼
<specialized lane A> ⇄ <specialized lane B>
      │                    │
      └──── versioned interface ────┘
                   │
                   ▼
            <runtime effect>
                   │
                   ▼
        <observation + receipt>
```

## APEX candidate comparison

| Candidate | Capability | Intelligence | Reliability | Leverage | Composition | Reach | Frontier fit | Fragility | Coordination cost | Result |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| incumbent |  |  |  |  |  |  |  |  |  |  |
| candidate A |  |  |  |  |  |  |  |  |  |  |

Preserve non-dominated tradeoffs. Do not declare a smaller candidate superior merely because it has fewer moving parts.

## Verification

```bash
# install/build
<command>

# deterministic proof
<command>

# adversarial/failure proof
<command>

# runtime/benchmark/receipt
<command>
```

## Exact contribution and provenance

- **Original:** `<authored architecture, implementation, tests, analysis>`
- **Adapted:** `<upstream source and modifications>`
- **Generated:** `<tool/AI output and verification boundary>`
- **External:** `<services, models, datasets, connectors>`
- **Unresolved:** `<unknown provenance or missing proof>`

## Machine contract

```yaml
schema: glaciereq.readme.apex.v1
repository: GlacierEQ/<repo>
apex_source_branch: <branch>
role: <ROLE>
visibility: <VISIBILITY>
apex_target:
  purpose: <strongest intended outcome>
  capability: <0..10-or-domain-vector>
  intelligence: <0..10-or-domain-vector>
  reliability: <0..10-or-domain-vector>
  leverage: <0..10-or-domain-vector>
  composability: <0..10-or-domain-vector>
  reach: <0..10-or-domain-vector>
  frontier_fitness: <0..10-or-domain-vector>
current:
  proof_state: <STATE>
  verified_at: <date-or-null>
  exact_head: <sha-or-null>
gap:
  - <engineering work>
frontier_candidates:
  - <technology/design candidate>
lanes:
  - id: <lane>
    concern: <concern>
    technology: <technology>
    interface: <interface>
    proof: <proof>
    replacement_trigger: <trigger>
preserved_gains:
  - capability: <capability>
    evidence: <path-or-receipt>
relationships:
  - target: GlacierEQ/<repo>
    relation: <ORCHESTRATES | VERIFIES | PROVIDES_CAPABILITY | CONSUMES | EXTENDS | PERSISTS_RECEIPTS_TO | EXECUTES_THROUGH | COMPOSES_WITH>
next_apex_turn: <highest-value next frontier move>
```

## Human authority

Casey Barton's project intent controls development direction. Machine state proves what exists. It does not acquire authority to redefine what the system is supposed to become.
