# README Intelligence Mesh Standard

## Purpose

A portfolio README must work for three readers without forcing any of them to decode the other two:

1. **Recruiter / non-specialist** — what problem is solved, why it matters, and what evidence can be opened immediately.
2. **Senior engineer / domain expert** — architecture, constraints, failure behavior, innovations, tradeoffs, and the project's evolution.
3. **AI system / toolchain** — stable repository identity, typed relationships, evidence pointers, runnable commands, and a versioned serialization contract.

The three views are generated from one evidence-bound repository record. They may differ in vocabulary and depth, but they may not contradict one another.

## Required README sections

Each portfolio-eligible repository must contain one generated block between:

```text
<!-- README-MESH:BEGIN -->
<!-- README-MESH:END -->
```

The generator replaces only this block. Human-authored material outside the markers is preserved.

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

- canonical `owner/repository` identity;
- stable branch and README URL;
- versioned `glaciereq.readme.v1` Protobuf record;
- typed repository edges;
- exact evidence paths and runnable commands;
- deterministic binary, ProtoJSON, textproto, and SHA-256 outputs.

## Real Protobuf contract

`proto/readme_mesh.proto` is compiled in CI. The generated descriptor is compared with the committed Python binding. The manifest is then serialized deterministically to:

- `readme_mesh.pb`
- `readme_mesh.proto.json`
- `readme_mesh.textproto`
- `readme_mesh.sha256`

This is not a prose block merely labeled “protobuf.” It is a compilable Protocol Buffers schema with generated bindings and binary round-trip tests.

## Evidence contract

Every audience section requires at least one evidence reference. Claims must point to source, tests, schemas, workflows, or provider-backed receipts. Unsupported employment, endorsement, deployment, scale, performance, safety, and readiness claims are prohibited.

## Mesh contract

Repository edges are directional and typed. A link must state the combined engineering value rather than merely list another repository. Supported relations include orchestration, verification, capability provision, consumption, extension, governance, receipt persistence, and execution routing.

## Exclusions

The README Mesh excludes:

- legal and family-case repositories or identifiers;
- forks and vendored upstream mirrors unless original work is clearly separated;
- private evidence or credentials;
- repositories whose claims cannot be tied to their own code or receipts;
- bulk public promotion as a side effect of documentation work.

A repository may remain private while receiving the standard. Visibility changes remain governed by AKOS promotion policy.
