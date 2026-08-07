# Estate Evolution Engine

## Mission

Continuously reduce repository and branch entropy while preserving every useful contribution, keeping upstream sources refreshable, and improving the estate with evidence-backed maintenance and current engineering intelligence.

The engine is not a blind merge bot. It is a synthesis system.

```text
CURRENT INTELLIGENCE
  -> TOPOLOGY + PRIORITY
  -> BRANCH / REPO INSPECTION
  -> UNIQUE-VALUE ANALYSIS
  -> SYNTHESIS ON CURRENT ANCESTRY
  -> REPOSITORY-NATIVE VERIFICATION
  -> PROMOTION
  -> RETIREMENT
  -> RECEIPT
  -> NEXT PRIORITY
```

## One hourly pass, many useful actions

The engine is deliberately not limited to one repository or one branch per invocation. It continues from the prior cursor until the execution environment reaches a real time or tool boundary.

Each pass may:

- refresh Monolith topology and legal-spine projections;
- ingest important AI coding and software-engineering developments into Mastermind's Library of Links;
- repair concrete defects and stale automation;
- update dependencies when repository-native proof supports the change;
- strengthen tests before risky refactors;
- analyze multiple branches across multiple repositories;
- preserve useful deltas from old branches on fresh canonical ancestry;
- merge verified low-risk work;
- prepare focused integration branches or PRs for work requiring stronger proof;
- retire branches only after unique-value exhaustion is proven;
- write a durable cursor and receipt for the next run.

## The stale-branch rule

A branch being `ahead` does not make it safe to merge.

A branch that is behind or diverged from `main`/`master` is evaluated relative to its merge base. Its useful patch value is identified, then recreated or merged onto a synthesis branch starting from the current canonical head.

```text
old branch tip ----- unique delta
       \            /
        merge base
             \
              current main ----> synthesis branch ----> tests ----> canonical
```

The old tip itself is never treated as the desired repository state merely because it contains commits that `main` does not.

## Patch equivalence

Commit SHAs are not sufficient evidence of unique value. Cherry-picks, squashes, and rewritten history can leave an old branch looking divergent even after its useful change is already present.

The branch steward therefore distinguishes:

- `ANCESTRY_EXHAUSTED` — no commits remain outside canonical ancestry;
- `PATCH_EQUIVALENT_EXHAUSTED` — history differs but no unique patch remains;
- `CURRENT_UNIQUE_VALUE` — branch is based on current canonical ancestry and contains useful delta;
- `DIVERGED_UNIQUE_VALUE` — useful delta exists but the branch is behind and must be synthesized on fresh ancestry.

## Fork model: source stays pure, GlacierEQ builds around it

A fork has two durable logical lines:

1. **upstream-tracking** — a clean mirror of the source project's canonical line;
2. **canonical-overlay** — GlacierEQ's maintained product line built around refreshed upstream state.

Short-lived synthesis branches may exist while integrating changes, but are retired after promotion.

Rules:

- upstream-tracking advances only from the source/upstream repository;
- GlacierEQ custom commits never land on the upstream-tracking line;
- upstream is refreshed before a major overlay synthesis;
- custom behavior should use extension points, adapters, plugins, wrappers, configuration, or clearly isolated modifications when possible;
- unavoidable source modifications remain narrow and reviewable;
- the overlay is tested after every upstream refresh;
- upstream and overlay identities remain separately recoverable.

This preserves the original engineering balance while allowing GlacierEQ innovation to evolve independently.

## Intelligence loop

Mastermind owns current technical intelligence through `knowledge/ai_coding_radar.json` and its Library-of-Links adapter.

An item is promoted only when it can materially affect one of:

- agent harness design;
- context engineering;
- testing and verification;
- security;
- branch/PR automation;
- model routing;
- developer workflow;
- runtime cost;
- reliability.

News does not automatically trigger refactoring. It creates a candidate innovation. Adoption requires a measurable benefit and repository-native proof.

## Maintenance loop

While a repository is already open for branch work, the engine may repair nearby problems instead of paying the context cost twice. The order is:

1. correctness and broken behavior;
2. failing or missing tests;
3. stale APIs/dependencies/configuration;
4. automation reliability;
5. documentation truth;
6. measurable performance or maintainability improvements;
7. innovation candidates from the current intelligence radar.

`repair before expand` and `no refactoring for novelty` remain hard rules.

## Retirement gate

A branch is eligible for retirement only when all applicable conditions hold:

- its useful content is already canonical or was deliberately rejected with a recorded reason;
- patch-equivalent unique value is zero;
- no active PR or dependency still requires the branch;
- the canonical result has adequate verification;
- upstream/fork preservation rules are satisfied;
- the remote ref deletion is actually performed by a capable tool and separately receipted.

Closing a PR is not branch deletion. Marking a branch obsolete is not branch deletion. Only a confirmed remote-ref deletion may be recorded as deleted.

## Control-plane split

| System | Owns |
|---|---|
| `job-app-helix` | maintenance policy, branch stewardship, consolidation execution, proof gates, receipts |
| `monolith` | estate topology, ownership, priority and generated status projections |
| `mastermind` | current engineering intelligence and Library of Links |
| owning repository | code, tests, branches, releases, runtime truth |

The control planes coordinate; they do not swallow the repositories they govern.
