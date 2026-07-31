# Tower of Babel Integration

The hardened Casey Barton recruiter package binds Job-App Helix to the Tower of Babel as a technology-authority layer.

## Why the Tower belongs here

Job-App Helix governs candidate identity, portfolio boundaries, evidence states, README rollout, and release receipts. Tower governs a different boundary: **which technology should own which responsibility, when that technology should activate, how it interoperates, and what proof is required before promotion**.

The two systems therefore compose without duplicating authority:

```text
candidate objective / target role
              │
              ▼
      Job-App Helix
identity · inventory · claim state · package surface
              │
              ▼
      Tower of Babel
technology placement · interfaces · build gates · blockers
              │
              ▼
 recruiter / engineer / AI presentation
              │
              ▼
 deterministic package and repository receipts
```

## Canonical Tower boundary

Package pull anchor: `GlacierEQ/the-tower-of-babel@1028a58986be6bedd1d8d09a63593876aab52d1d`

At that anchor, Tower exposes:

- 30 governed technology floors;
- 60 linked easy and advanced exhibits;
- 13 behavioral-proof floors;
- 3 formal-proof floors;
- 8 explicitly gated floors;
- an Advanced Exhibit Atlas for human and machine review.

These counts describe the Tower repository at the anchored commit. They do not establish portfolio-wide deployment, production scale, or customer impact.

## Recruiter signal

Tower demonstrates that polyglot engineering is treated as governed placement rather than language collection. A technology earns its place through a measurable boundary such as native safety, browser reach, statistical rigor, database correctness, hardware acceleration, formal proof, or interoperability.

## Evidence rules

- `verified`, `tested`, `integrated`, and `formally_verified` remain stronger than `illustrative`.
- `hardware_gated`, `toolchain_gated`, and `service_gated` remain explicit blockers.
- Repository source is not silently promoted into deployment proof.
- New languages may not replace working components merely for novelty.
- Machine ingestion must preserve the same claim and blocker states shown to humans.

## Package surfaces

The hardened package exposes Tower through:

- `04_TOWER_OF_BABEL_LANGUAGE_ENGINEERING.md`;
- `04_TOWER_OF_BABEL/ADVANCED_EXHIBIT_ATLAS_SNAPSHOT.md`;
- `04_TOWER_OF_BABEL/tower_candidate_contract.json`;
- `04_TOWER_OF_BABEL/tower_sync_receipt.json`;
- `09_MACHINE_AND_INTEROP/portfolio_graph.mmd`.

The distributable archive is released separately with a SHA-256 receipt; private contact data is not copied into this public repository.
