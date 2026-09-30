# README Intelligence Mesh Standard

## Purpose

A portfolio README must support progressive disclosure across five coherent depths without forcing one reader to decode another:

1. **Recruiter / non-specialist** — what problem is solved, why it matters, and what evidence can be opened immediately.
2. **Expert / senior engineer** — architecture, constraints, failure behavior, innovations, tradeoffs, and the project's evolution.
3. **Genius / synthesis layer** — how the mechanisms compound, what was learned across iterations, what higher-order design principle emerges, and how the repository participates in a mastery loop without overstating evidence.
4. **Machine / AI system** — stable repository identity, typed interfaces, evidence pointers, runnable commands, authority boundaries, and a versioned serialization contract.
5. **Mesh / estate context** — typed relationships, lineage, combined engineering value, boundaries, and the repository's role in the wider GlacierEQ system.

The five depths are projections of one evidence-bound repository record. They may differ in vocabulary and compression, but they may not contradict one another or invent capability beyond source and receipts.

## Required README sections

Portfolio leaf repositories contain one generated block between:

```text
<!-- README-MESH:BEGIN -->
<!-- README-MESH:END -->
```

The generator replaces only this block. Human-authored material outside the markers is preserved.

### APEX orchestrator superset

The APEX portfolio orchestrator may use a richer human-authored README instead of embedding a second, duplicative generated block when all of the following are enforced in CI:

- recruiter, expert, genius, machine, and mesh depths exist in that order;
- the human README exposes the current schema, evidence, verification state, language declarations, relationships, and limits;
- the generated progressive-disclosure projection is rendered and validated independently;
- the human README and generated projection derive from compatible evidence and do not contradict each other.

This exception exists to preserve elite human communication at the portfolio root without weakening deterministic machine output. It does not exempt leaf repositories from their generated blocks.

### Recruiter layer

Must answer:

- What does this project do in plain language?
- Why is the problem valuable or difficult?
- What did Casey design or implement?
- What can a reviewer open or run to verify it?

### Expert layer

Must identify:

- system boundary and component responsibility;
- noteworthy architecture or algorithm;
- failure behavior and explicit limits;
- how the repository evolved beyond a standalone demonstration;
- evidence in source, tests, schemas, workflows, or receipts.

### Genius layer

Must identify higher-order engineering meaning without becoming marketing copy:

- what mechanisms compound rather than merely coexist;
- what design principle, abstraction, or reusable method emerged from the work;
- how evidence, implementation, verification, and iteration form a mastery loop;
- what transfers to adjacent systems and what does not;
- what remains unresolved, falsifiable, or bounded.

The Genius layer is a synthesis projection. It does not own new facts, create authority, or replace the Expert, Machine, or Mesh layers.

### Machine layer

Must expose:

- APEX `owner/repository` identity;
- stable branch and README URL;
- versioned `glaciereq.readme.v1` Protobuf record;
- typed repository edges;
- exact evidence paths and runnable commands;
- deterministic binary, ProtoJSON, textproto, and SHA-256 outputs;
- explicit authority and execution boundaries where relevant.

### Mesh layer

Must expose:

- directional typed relationships rather than flat related-project lists;
- combined engineering value for each relationship;
- lineage, extension, verification, provision, consumption, persistence, and execution-routing relationships where supported;
- repository boundaries so composition does not imply ownership or authority.

## Real Protobuf contract

`proto/readme_mesh.proto` is compiled in CI. The generated descriptor is compared with the committed Python binding. The manifest is then serialized deterministically to:

- `readme_mesh.pb`
- `readme_mesh.proto.json`
- `readme_mesh.textproto`
- `readme_mesh.sha256`

This is not a prose block merely labeled “protobuf.” It is a compilable Protocol Buffers schema with generated bindings and binary round-trip tests.

The Protobuf record remains the evidence-bearing source for recruiter, expert, and machine facts. Genius and Mesh are deterministic projections over that source plus the typed relationship graph; they must not manufacture unsupported claims.

## Evidence contract

Every factual depth requires evidence appropriate to its claims. Claims must point to source, tests, schemas, workflows, or provider-backed receipts. Unsupported employment, endorsement, deployment, scale, performance, safety, and readiness claims are prohibited.

## Mesh contract

Repository edges are directional and typed. A link must state the combined engineering value rather than merely list another repository. Supported relations include orchestration, verification, capability provision, consumption, extension, receipt persistence, and execution routing. Relationship presence never grants project-direction authority by itself.

## Language-fit contract

Every language or format must declare a responsibility, boundary, interface contract, build/compile command, test/proof/benchmark command, evidence receipt, and current state. The declarations must be machine-readable and auditable. Language count is not evidence of mastery.

## Progressive-disclosure invariant

The canonical reading order is:

```text
RECRUITER → EXPERT → GENIUS → MACHINE → MESH
```

Each layer must be a truthful stopping point. Deeper layers may add mechanism, synthesis, deterministic structure, and relationships; they may not reverse or silently reinterpret claims made above them.

## Exclusions

The README Mesh excludes:

- legal and family-case repositories or identifiers;
- forks and vendored upstream mirrors unless original work is clearly separated;
- private evidence or credentials;
- repositories whose claims cannot be tied to their own code or receipts;
- bulk public promotion as a side effect of documentation work.

A repository may remain private while receiving the standard. Visibility changes remain governed by the repository's actual promotion and access policy.
