# GlacierEQ Estate README Standard

## One README, Five Depths

A GlacierEQ README is not a flat project description. It is **one factual system projected at five useful depths**:

1. **01 · RECRUITER** — the complete human overview for recruiters, collaborators, hiring managers, and normal people.
2. **02 · EXPERT** — the full technical account for senior engineers and domain experts.
3. **03 · GENIUS** — evidence-bound synthesis: what mechanisms compound, what design intelligence emerged, what transfers, and what remains bounded.
4. **04 · MACHINE** — the deterministic contract for agents, retrieval systems, compilers, and future automated operators.
5. **05 · MESH** — the typed relationships that show how the repository becomes more valuable in the wider GlacierEQ estate without collapsing identity or ownership.

The topology is stable. **The weight is not.** A tiny utility may need only a few lines in Recruiter, a compact Expert section, and a very small Genius synthesis. A flagship may justify serious depth. Machine is structured rather than ornamental. Mesh contains only relationships that add real understanding or capability.

Every depth is a valid stopping point. A reader who stops after Recruiter should understand the project. A technical reviewer who stops after Expert should be able to evaluate it seriously. Genius should reveal higher-order engineering meaning without inventing facts. A machine should not need to scrape prose to locate the contract. A reader entering Mesh should see additional value, not link clutter.

## PSYSOC-X Is the Presentation Engine

The presentation law is owned by the verified PSYSOC-X Infinity Stone in `GlacierEQ/AKOS`, not reimplemented here.

Canonical sources:

- Contract: `GlacierEQ/AKOS/stones/psysoc-x/STONE.md`
- Manifest: `GlacierEQ/AKOS/stones/psysoc-x/stone.json`
- Engine: `GlacierEQ/AKOS/infinity_stones/psysoc_x.py`
- Verification: `GlacierEQ/AKOS/receipts/2026-08-02_psysoc-x_v0.1.0_promotion.json`
- Presentation profile: `GlacierEQ/job-application/site-v15/data/psysoc-x-profiles.json`

PSYSOC-X controls **attention strategy, tone, density, logic order, skepticism response, humor fit, emotional-weight handling, memory anchors, dignity controls, and warnings** from explicit context. It may change how truth arrives. It may not change truth.

Core rule:

> **Fixed truth. Adaptive expression.**

The sequence, density, framing, title, warmth, and amount of explanation may change with the audience and stakes. Facts, evidence state, uncertainty, provenance, dignity, authority, and reader agency may not.

### Dynamic judgment

Do not optimize for uniform README length.

Use the **shortest form that preserves the reader's needed understanding** and the **longest form justified by technical or evidentiary value**.

As cognitive load rises, use progressive disclosure. As skepticism rises, move limits and reproducible proof earlier. As stakes or privacy rise, remove humor and reduce ornamental language. As evidence weakens, make uncertainty more visible. As technical depth becomes useful, expand Expert rather than forcing complexity into Recruiter. Expand Genius only when there is real synthesis to expose.

### Titles must carry weight

Stable layer identifiers stay machine-recognizable:

- `01 · RECRUITER`
- `02 · EXPERT`
- `03 · GENIUS`
- `04 · MACHINE`
- `05 · MESH`

The subtitle after the identifier is **project-native and dynamic**. It should be clever enough to reward attention and concrete enough to carry information.

Good title behavior:

- names the real problem, mechanism, transformation, or tension;
- uses vocabulary native to the project;
- creates curiosity without hiding meaning;
- can be serious, warm, dry, or lightly playful when context permits;
- never uses hype as a substitute for evidence.

Bad title behavior:

- generic `Overview`, `Technical Details`, `Architecture`, `Links` when something more specific is available;
- marketing slogans with no factual payload;
- jokes in sensitive or high-stakes repositories;
- cleverness that makes the section harder to understand.

## 01 · RECRUITER — Earn the Next Minute

This is the overview. It answers quickly:

- **What is this?**
- **What problem does it solve?**
- **What does it actually do?**
- **Why does that matter?**
- **What is the strongest observable proof?**
- **Where should I go if I want more?**

The Recruiter layer must feel complete rather than teaser-like. It should be low-to-medium density, translate jargon, and lead with decision-relevant consequence or one concrete outcome when possible.

A strong Recruiter section normally uses:

- one human hook or project-native tension;
- one concise explanation of mechanism;
- up to three memorable capabilities/outcomes;
- one or two strong proof links;
- a clean handoff to Expert.

Do not dump every feature here. Do not withhold the point merely to force scrolling.

For sensitive/private/legal repositories, use the same cognitive role — immediate human orientation — but do not turn sensitive facts into recruiter copy or leak private evidence.

## 02 · EXPERT — Show the Work

This is for senior engineers, domain specialists, principal-level reviewers, and anyone doing real diligence.

Expert may cover, as justified by the repository:

- architecture and decomposition;
- mechanism and algorithms;
- important implementation choices;
- interfaces and data contracts;
- tradeoffs and rejected alternatives;
- reliability and recovery behavior;
- security and authority boundaries;
- performance characteristics where measured;
- tests and verification;
- failure domains and known limits;
- historical evolution when it explains the current design;
- why the technical choices matter.

This is where jargon is allowed when it is native and defined. It should be precise, engineering-led, and evidence-bound — not merely longer marketing prose.

Depth is earned. A five-file utility should not receive an artificial dissertation. A complicated control plane should not be compressed into six bullets merely for visual symmetry.

## 03 · GENIUS — Show What Compounds

Genius is not a superlative badge and it is not a second truth source. It is the **synthesis layer**.

It answers:

- What mechanisms become more powerful together than they are separately?
- What reusable design principle or abstraction emerged from the work?
- What did iteration teach that is not obvious from a component list?
- What can transfer to another system, and under what assumptions?
- What cannot transfer safely?
- What unresolved question, falsifiable claim, or boundary still matters?

A strong Genius section links implementation, evidence, verification, and evolution into a mastery loop. It may reference the repository's `GENIUS.yaml`, Genius Engine receipts, or Genius-family repositories when those sources actually apply.

Genius must never manufacture capability, deployment state, endorsement, scale, safety, authority, or proof. If the higher-order claim cannot be traced back to source/evidence, it does not belong here.

## 04 · MACHINE — Plug In Without Guessing

Every writable repository should expose exactly one versioned machine contract between:

```text
<!-- glacier-eq-protocol:start -->
```

and:

```text
<!-- glacier-eq-protocol:end -->
```

Current schema:

```yaml
schema: glacier-eq.readme.machine-mesh/v1
```

The machine layer is a **source index and integration contract**, not a runtime receipt. It may establish:

- exact `owner/repository` identity and repository URL;
- README/profile contract;
- repository kind;
- source/default branch when known;
- protocol files and decisive entrypoints;
- current Monolith primary placement or migration-residue state;
- typed routes to Monolith and peer systems;
- evidence pointers;
- lifecycle and authority boundaries;
- license path and rights status;
- generator identity and deterministic contract digest.

It must never independently promote a repository to deployed, production-ready, provider-connected, externally verified, safe, complete, or authoritative. Those states require their own evidence.

Estate tools consume a repository in this order:

1. identity + current default branch;
2. machine contract;
3. entrypoints/protocol files named by the contract;
4. strongest decisive implementation/test surface needed for unresolved questions;
5. provider-native receipts for deployment or external-action claims.

Absence of a block is `MISSING_CONTRACT`, not evidence of missing capability. Malformed, contradictory, unsupported-schema, or identity-mismatched contracts fail closed into repair.

## 05 · MESH — Show What Becomes Possible Together

Mesh answers a different question from Expert or Genius:

> **What becomes stronger, possible, safer, faster, or more intelligible when this repository connects to the rest of the estate?**

Use typed relationships, not a random related-links list.

Useful relationships include:

- provides capability to;
- consumes;
- verifies;
- executes through;
- persists receipts to;
- derives from;
- composes with;
- routes to;
- maps;
- supersedes / migrated from;
- supports a named Matter/Mission while preserving source identity.

Mesh should preserve lineage, boundaries, and current-vs-aspirational state. It may expose blockers, missing pieces, next promotions, or future composition when labeled honestly.

Do not flatten connected repositories into one identity. Connection is not ownership. Routing is not evidence transfer. A richer graph should make each source easier to understand without erasing where it came from.

## Licensing — Protect GlacierEQ Work

The rule is simple:

> **Copyright (c) 2026 Casey Del Carpio Barton / GlacierEQ. All rights reserved.**

For GlacierEQ-owned material, no copying, modification, reproduction, redistribution, sublicensing, sale, publication, deployment, hosting, commercialization, model training, dataset inclusion, derivative work, or other use is permitted without prior express written permission from the rights holder.

Public visibility does not grant additional rights.

The controlling license is the **GlacierEQ Proprietary License v1.0** in `LICENSE`.

Do not claim rights GlacierEQ does not own and do not overwrite rights already validly granted for earlier versions. That is a legal boundary, not a separate licensing program.

## Repository Profiles

The five depths remain stable across profiles. The profile changes exposure and weight.

### `estate-core`

Default. Five-depth structure + machine contract. Existing strong human prose should be adopted and reorganized rather than erased.

### `portfolio`

Public portfolio-eligible repository. Uses full PSYSOC-X Recruiter/Expert/Genius/Machine/Mesh projection with source-bound proof and no private legal/case material.

### `flagship`

A deliberately curated primary system. Same five depths, with greater Expert, Genius, and Mesh depth justified by source complexity and evidence.

### `sensitive`

Legal, evidence, family, private-record, or other high-sensitivity repository. Same five-depth topology, but Recruiter means **safe human orientation**, not public promotion. Private facts stay private; humor normally disappears; evidence links respect access and disclosure boundaries.

### `fork-archive`

Preserve origin, upstream license, lineage, and local modifications. Archived GitHub repositories remain represented in the estate manifest even when README mutation is impossible.

## Adoption Before Regeneration

Bulk automation is adopt-first.

- Strong existing human prose is evidence of project identity and should be preserved or reorganized, not flattened into generated boilerplate.
- A valid existing machine block remains authoritative local contract state unless newer source evidence requires regeneration.
- Missing human layers may be filled from repository evidence.
- Missing machine blocks receive deterministic minimum contracts.
- Malformed or identity-mismatched machine blocks are repaired explicitly, never silently overwritten.
- Generated content must state only what source evidence supports.

The compiler is a **projection system**, not a new source authority.

## Whole-Estate Rollout

The rollout is source-exhaustive, resumable, controlled, and idempotent.

For each live GlacierEQ repository:

1. resolve stable repository identity from the live GitHub App installation;
2. read current default branch, root tree, README, license, and decisive source surfaces;
3. reconcile current Monolith classification/evidence when present;
4. recover/adopt existing human language worth preserving;
5. derive explicit audience context for PSYSOC-X;
6. produce the five-depth projection at the amount of detail justified by source and audience;
7. validate the machine contract and rights notice;
8. compare-before-write using the current README blob SHA;
9. mutate only authorized paths;
10. reread provider state and verify exact content/digest;
11. append an immutable receipt/checkpoint so interrupted runs resume without redoing verified work.

No visibility changes. No repository deletion, archival, or unarchival. No credential collection. No private evidence copied into Helix. No runtime claim inferred from documentation.

## Relationship to the Existing README Mesh

The existing `proto/readme_mesh.proto`, README Mesh manifests, deterministic artifacts, Genius Engine sources, and renderer remain useful evidence/projection infrastructure. They are not separate competing architectures.

Their semantic mapping is now explicit:

- legacy `RECRUITER` → `01 · RECRUITER`;
- legacy `EXPERT` → `02 · EXPERT`;
- Genius Engine / `GENIUS.yaml` / evidence-bound synthesis → `03 · GENIUS` where applicable;
- legacy `AI_AGENT` + machine-mesh contract → `04 · MACHINE`;
- typed repository edges → `05 · MESH`.

One factual graph can therefore feed all five surfaces without contradictory hand-authored versions.

## Acceptance

The estate README program is successful when:

- every writable live GlacierEQ repository has the five-depth structure at an appropriate weight;
- every writable repository has exactly one valid machine contract or an explicit repair receipt;
- GlacierEQ-owned work carries the intended all-rights-reserved protection;
- existing rights not owned by GlacierEQ are not overwritten;
- every archived/read-only repository remains represented in the rollout manifest;
- PSYSOC-X changes presentation without changing factual or evidentiary state;
- Genius synthesizes without creating new truth or authority;
- every depth works as a truthful stopping point;
- generated updates are idempotent and preserve project-native human value;
- Monolith placement/provenance can be recovered without broad crawling when a sufficient machine block exists;
- no README claims more authority or runtime state than its evidence establishes.
