# Estate Compiler Graph

## Decision

The authenticated estate census is the **intelligence substrate**, not a recruiter catalog.

```text
owned GitHub estate
  -> namespace isolation
  -> evidence-bound lineage collapse
  -> canonical systems
  -> reusable capability donors
  -> proof binding
  -> company operating problems
  -> target roles
  -> bounded application projections
```

The full native estate sits upstream of the existing governed recruiter portfolio. The smaller portfolio remains a projection; it is no longer the ceiling on what Helix can discover or prove.

## Canonical outputs

A successful compile emits three primary registries:

1. **Canonical System Registry** — one engineering-system identity per reconciled lineage root, with backups and archives retained as historical members and forks retained outside the accomplishment count.
2. **Capability Donor Registry** — reusable capabilities linked to one or more canonical systems and their proof references. Repeated implementation across independent systems is represented explicitly.
3. **Company Projection Registry** — company track -> operating problem -> target roles -> canonical systems -> capabilities -> ranked evidence -> bounded proof surface.

Generated full registries remain internal because the authenticated census can contain private repository identities. Only the compiler receipt and separately generated public-safe projection are publication-eligible.

## Namespace boundary

`LEGAL_PRIVATE` is a graph boundary, not a UI filter. Raw legal repository identities and case material cannot feed company projections. A legal system may donate a sanitized engineering pattern only through a separately reviewed public-safe engineering artifact.

Forks are isolated as `FORK_REFERENCE`. They may prove ancestry or an attributable downstream delta, but they are never counted as native accomplishments.

## Lineage

Automatic collapse is conservative:

- explicit typed lineage with evidence may collapse;
- high-confidence backup/archive identity plus authenticated census metadata may collapse;
- similar normalized names without sufficient evidence emit `UNRESOLVED_LINEAGE_CANDIDATE`;
- cycles fail closed;
- historical members remain preserved after canonicalization.

The canonical-system count therefore emerges from reconciliation rather than from a guessed target number.

## Capability donors

Capability extraction begins from evidence-bound flagship metadata. Generic capability families are derived only from explicit role/evidence text, and runtime proof is never inferred from a repository name.

Each capability records donor systems, independent donor count, proof references, repeat-pattern status, and verification state. This makes “I repeatedly implemented this engineering pattern across unrelated systems” a graph-supported claim instead of résumé prose.

## Promotion score

Every canonical system receives five equal-weight dimensions:

- originality;
- technical depth;
- verification strength;
- transferability;
- target-company relevance.

Visibility is intentionally separate. A technically strong private or sensitive system may score highly while remaining internal or sanitized-only.

## Bounded proof-surface compiler

Company projection uses a bounded greedy capability set-cover. For each target, Helix chooses at most five canonical systems that maximize distinct capability coverage and proof strength. This minimizes redundant repository exposure while preserving the full ranked evidence graph internally.

This is the key transformation from catalog to compiler: repository volume becomes a hidden search space, while each reviewer receives the smallest high-signal proof surface relevant to them.

## Experiments

Rows already classified as `EXPERIMENT` or `PRIVATE_EXPERIMENT` enter a monotonic R&D pipeline:

`EXPERIMENT -> DISTINCT_VALUE -> TESTED -> SYSTEM_COMPONENT -> FLAGSHIP_DONOR`

Each transition has an evidence requirement. Experiments survive as R&D capital without polluting flagship claims.

## Self-healing behavior

The compiler is deterministic and source-digest bound:

- census drift triggers recompilation;
- unresolved lineage becomes an explicit reconciliation queue;
- unsupported capability inference remains metadata-only;
- one unresolved family does not block independent systems;
- registry hashes support stale detection downstream;
- public output is regenerated from the internal bundle, never edited by hand.

## Runtime

```bash
python scripts/census_owned_library.py --token "$GITHUB_TOKEN"
python scripts/compile_estate_graph.py \
  --public-output artifacts/estate-compiler/public-safe-company-projection.json
```

Optional explicit lineage assertions are accepted only when every relationship includes a typed relation, target repository, and non-empty evidence references.

## Completion contract

A run is complete only after it emits the canonical-system registry, capability-donor registry, company-projection registry, experiment pipeline, deterministic receipt, and—when requested—a public-safe projection. Unresolved lineage is a valid fail-visible state; it is never permission to guess.
