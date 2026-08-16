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
- **Efficiency:** `<latency/throughput/cost/resource efficiency appropriate to this boundary>`
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

| Lane | Concern | Technology | Owner | Why this technology owns the lane | Interface | Proof | Replacement trigger |
|---|---|---|---|---|---|---|---|
| `<kernel>` | `<runtime>` | `<Rust/Zig/C++/...>` | `<component/team>` | `<measurable fit>` | `<ABI/schema/protocol>` | `<tests/runtime>` | `<what would displace it>` |
| `<memory>` | `<durable/graph/vector/...>` | `<SQL/Datalog/...>` | `<component/team>` | `<measurable fit>` | `<schema/protocol>` | `<recovery/query tests>` | `<what would displace it>` |

One language or twelve are both valid. Each lane must earn its existence at the boundary.

## Proof in 60 seconds

| Open or run | What it proves | Current state |
|---|---|---|
| `<path or command>` | `<specific behavior>` | `<state>` |
| `<path or command>` | `<failure or adversarial behavior>` | `<state>` |
| `<receipt/workflow/runtime>` | `<exact verified boundary>` | `<state>` |

## Lineage

- **Confidence:** `<0..1>`
- **Evidence source:** `<direct ancestry/compare/manifest/receipt>`
- **Predecessors:** `<repos or none>`
- **Successors:** `<repos or none>`

Lineage is evidence about implementation history. It cannot override the human project target.

## Preservation ledger

| Prior gain | Current owner | Status | Evidence |
|---|---|---|---|
| `<capability>` | `<lane/component>` | `<PRESERVED, SUPERSEDED_BY_STRONGER, PARTIAL, AT_RISK>` | `<path/receipt>` |

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

| Candidate | Capability | Intelligence | Reliability | Efficiency | Leverage | Composition | Reach | Frontier fit | Fragility | Coordination cost | Decision |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| incumbent |  |  |  |  |  |  |  |  |  |  |  |
| candidate A |  |  |  |  |  |  |  |  |  |  |  |

For every material frontier candidate record the boundary, advantages, costs, evidence, and one explicit decision: `IGNORE_WITH_REASON`, `WATCH`, `EXPERIMENT`, `ADMIT`, `MIGRATE`, or `RETIRE`.

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

Every `VERIFIED` or `PARTIALLY_VERIFIED` machine contract must identify an exact source head and a deterministic receipt path plus SHA-256. A receipt proves only the observation it contains; it does not become project authority.

## Exact contribution and provenance

- **Original:** `<authored architecture, implementation, tests, analysis>`
- **Adapted:** `<upstream source and modifications>`
- **Generated:** `<tool/AI output and verification boundary>`
- **External:** `<services, models, datasets, connectors>`
- **Unresolved:** `<unknown provenance or missing proof>`

## Machine contract

The executable contract is [`schemas/readme_apex.schema.json`](../schemas/readme_apex.schema.json). The JSON below must validate against it. The schema deliberately has **no** project-direction relation such as `GOVERNED_BY`.

```json
{
  "schema": "glaciereq.readme.apex.v1",
  "repository": "GlacierEQ/<repo>",
  "human_project_authority": "Casey Barton",
  "apex_source_branch": "<branch>",
  "role": "<ROLE>",
  "visibility": "PUBLIC",
  "lineage": {
    "confidence": 0.0,
    "source": "<direct evidence pointer>",
    "predecessors": [],
    "successors": []
  },
  "apex_target": {
    "purpose": "<strongest intended outcome>",
    "capability": 0,
    "intelligence": 0,
    "reliability": 0,
    "efficiency": 0,
    "leverage": 0,
    "composability": 0,
    "reach": 0,
    "frontier_fitness": 0
  },
  "current": {
    "proof_state": "UNVERIFIED",
    "verified_at": null,
    "exact_head": null,
    "receipt": {
      "path": "<receipt path or explicit pending receipt path>",
      "sha256": "0000000000000000000000000000000000000000000000000000000000000000"
    }
  },
  "gap": ["<engineering work>"],
  "frontier_candidates": [
    {
      "candidate": "<technology/design>",
      "boundary": "<architecture concern>",
      "decision": "WATCH",
      "advantages": ["<measurable upside>"],
      "costs": ["<measurable cost>"],
      "evidence": ["<benchmark/source/experiment>"]
    }
  ],
  "lanes": [
    {
      "id": "<lane>",
      "concern": "<concern>",
      "technology": "<technology>",
      "owner": "<component/team>",
      "interface": "<interface>",
      "proof": "<proof>",
      "replacement_trigger": "<trigger>"
    }
  ],
  "preserved_gains": [
    {
      "capability": "<prior gain>",
      "owner": "<lane/component>",
      "status": "PRESERVED",
      "evidence": "<path-or-receipt>"
    }
  ],
  "relationships": [
    {
      "target": "GlacierEQ/<repo>",
      "relation": "COMPOSES_WITH",
      "value": "<specific combined capability>"
    }
  ],
  "next_apex_turn": "<highest-value next frontier move>"
}
```

Allowed relationship semantics describe composition, execution, evidence, or projection only:

`ORCHESTRATES`, `VERIFIES`, `PROVIDES_CAPABILITY`, `CONSUMES`, `EXTENDS`, `PERSISTS_RECEIPTS_TO`, `EXECUTES_THROUGH`, `COMPOSES_WITH`, `EVIDENCE_TRACKED_BY`, `PROJECTED_BY`.

No relationship grants a repository, assistant, CI system, registry, receipt, or projection authority over Casey Barton's intended target.

## Human authority

Casey Barton's project intent controls development direction. Machine state proves what exists. It does not acquire authority to redefine what the system is supposed to become.
