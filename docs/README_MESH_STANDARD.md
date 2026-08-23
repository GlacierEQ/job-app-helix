# README Intelligence Mesh Standard

## Purpose

A portfolio README must work for three readers without forcing any of them to decode the other two:

1. **Recruiter / non-specialist** — what problem is solved, why it matters, and what evidence can be opened immediately.
2. **Senior engineer / domain expert** — architecture, constraints, failure behavior, innovations, tradeoffs, and the project's evolution.
3. **AI system / toolchain** — stable repository identity, typed relationships, evidence pointers, runnable commands, and a versioned serialization contract.

The three views are generated from or validated against one evidence-bound repository record. They may differ in vocabulary and depth, but they may not contradict one another.

**Project direction remains with the Operator.** This standard describes presentation and evidence interfaces; it does not appoint a portfolio root, repository hierarchy, lifecycle authority, visibility authority, or machine-controlled source of project truth.

## Required README sections

Portfolio leaf repositories may contain one generated block between:

```text
<!-- README-MESH:BEGIN -->
<!-- README-MESH:END -->
```

When the generator is used, it replaces only this block. Human-authored material outside the markers is preserved.

### Portfolio orchestrator superset

A portfolio orchestrator may use a richer human-authored README instead of embedding a second, duplicative generated block when all of the following are enforced in CI:

- recruiter, expert, and AI layers exist in that order;
- the human README exposes the current schema, evidence, verification state, language declarations, relationships, and limits;
- the generated three-audience projection is rendered and validated independently where that projection is actually used;
- the human README and generated projection derive from compatible evidence and do not contradict each other.

This preserves strong human communication without turning the orchestrator, generator, schema, or CI into project authority. Leaf repositories may use the generated block where it adds value; the presence of that block is not a legitimacy or lifecycle gate.

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

### AI layer

Must expose:

- stable `owner/repository` identity;
- observed branch and README URL where relevant;
- versioned `glaciereq.readme.v1` Protobuf record when the mesh contract is implemented;
- typed repository edges;
- exact evidence paths and runnable commands;
- deterministic binary, ProtoJSON, textproto, and SHA-256 outputs when generated.

Repository identity fields are descriptive identifiers. They do not assign hierarchy, ownership, lifecycle, or project-direction authority.

## Real Protobuf contract

`proto/readme_mesh.proto` is compiled in CI. The generated descriptor is compared with the committed Python binding. The manifest is then serialized deterministically to:

- `readme_mesh.pb`
- `readme_mesh.proto.json`
- `readme_mesh.textproto`
- `readme_mesh.sha256`

This is not a prose block merely labeled “protobuf.” It is a compilable Protocol Buffers schema with generated bindings and binary round-trip tests.

A successful serialization or CI result proves only the named representation/validation behavior. It does not create project authority.

## Evidence contract

Every audience section requires at least one evidence reference. Claims must point to source, tests, schemas, workflows, or provider-backed receipts. Unsupported employment, endorsement, deployment, scale, performance, safety, and readiness claims are prohibited.

`UNKNOWN != FALSE` and `PARTIAL != COMPLETE`. Missing proof creates a proof gap, not an automatic repository downgrade or disposition.

## Mesh contract

Repository edges are directional and typed. A link must state the combined engineering value rather than merely list another repository. Supported relations describe composition, verification, capability provision, consumption, extension, receipt persistence, execution routing, evidence tracking, or projection.

No relation may mean that one repository governs another, owns its lifecycle, becomes its truth root, or may publish/suppress/retire/merge/delete it without Operator direction.

## Language-fit contract

Every language or format must declare a responsibility, boundary, interface contract, build/compile command, test/proof/benchmark command, evidence receipt, and current state where those fields materially apply. The declarations must be machine-readable and auditable. Language count is not evidence of mastery.

## Exclusions and visibility safety

The README Mesh should not expose:

- private evidence or credentials;
- sensitive legal/family-case material unless intentionally prepared for the public surface;
- vendored/upstream work as if it were original work;
- claims that cannot be tied to source, tests, or receipts;
- bulk public promotion as a side effect of documentation work.

Sensitive repositories require stronger disclosure review. That safety requirement does not make AKOS, Helix, a registry, a category, or a generated policy the visibility authority.

```text
inventory != authority
technical_permission != project_direction
visibility_readiness != visibility_authorization
```

Visibility changes occur under the Operator-selected objective after appropriate security/evidence review. An AKOS bridge, AKOS homepage, mesh score, CI result, or generated README is never a publication authorization by itself.

## Authority boundary

- Project direction: **OPERATOR**.
- Source evidence controls factual claims within its scope.
- Job App Helix may compile, compare, verify, and project portfolio evidence; it does not acquire ownership of peer repositories.
- AKOS may provide optional architecture/cognition/verification support; it does not govern peer repositories.
- README Mesh records and receipts are evidence/projection artifacts, not project constitutions.

**Compatibility is not control. Selection is not ownership. Persistence is not authority.**
