# Unbounded Job Estate Contract

The GlacierEQ hiring estate is a graph, not a shortlist.

## Membership law

Repository membership is defined by **source exhaustion**. A fixed count may describe a
materialized snapshot, but it may never define the maximum size of the estate.

Forbidden as membership rules:

- `top_n`, `max_repos`, `max_companies`, or `first N`;
- fixed family counts used as admission gates;
- slicing company projections to a hand-picked subset and calling it complete;
- treating a provider page-size limit as estate size;
- dropping unassigned, archived, private-metadata, experimental, or unverified repositories.

Allowed mechanisms include UI pagination, configurable concurrency, backpressure, recruiter
ranking, evidence promotion/demotion, and public/private projection boundaries. Those may
change presentation or execution cost. They may not change what exists.

## Identity and evidence

Repository identity is provider ID where available plus full repository name for human
readability. Evidence state is independent of inventory membership.

A relation to a target company means **relevance only** unless separate evidence establishes
something stronger. Relevance never becomes employment, affiliation, proprietary access,
deployment, endorsement, customer status, production telemetry, or business outcome.

## Company projections

Each company projection is a view over the same estate graph:

```
complete repository inventory
        + evidence state
        + capability metadata
        + explicit company mappings
        ↓
company relevance graph
        ↓
role-specific ranking / recruiter projection
```

Company views never own duplicate repository truth.

## Snapshot counts

Historical counts such as 66 admitted children or 225 deserving records remain provenance for
the snapshot that produced them. They are not ceilings. New repositories and companies enter
through the same identity/evidence model without changing a magic number in code or tests.

## Test law

Tests assert invariants: unique identity, no dangling relations, source-exhaustion semantics,
truth boundaries, deterministic projection, and preservation of unassigned repositories.
Tests must not fail merely because the estate grew.
