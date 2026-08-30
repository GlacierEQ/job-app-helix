# Live Repository Evidence Adapter

## Purpose

The adapter converts a current, source-linked repository observation into the exact input consumed by the SHA-bound Repository Health Engine.

It does not clone or copy child repositories into Helix. It stores public-safe metadata, immutable GitHub URLs, execution receipts, uncertainty, and blockers.

## Pipeline

```text
APEX repository
        │
        ├── repository metadata
        ├── current default-branch SHA
        ├── SHA-bound artifact URLs
        ├── workflow invocation receipts
        └── explicit probe errors
                │
                ▼
Repository Observation v1
                │
                ▼
Live Evidence Adapter
                │
        ├── validate provenance
        ├── reject copied bytes
        ├── reject branch-floating artifact URLs
        ├── separate presence from execution
        ├── score connector quality
        └── score data quality
                │
                ▼
Repository Health Input
                │
                ▼
SHA-bound Health Assessment
```

## Evidence boundaries

The adapter applies these rules:

- A repository, package manifest, source file, workflow, or test file proves presence only.
- A successful build requires a current provider receipt.
- A successful test run requires a current provider receipt and positive executed-test count.
- A README and documentation verifier may establish partial documentation evidence, but not current execution.
- Architecture, integration, recruiter, and AI artifacts remain partial until stronger verification exists.
- Ambiguous direct-push workflow state remains `UNVERIFIED`.
- A failure without a provider receipt is not promoted into a verified failure claim.
- All artifact URLs must include the observed immutable Git SHA.
- Connector authentication is represented only when directly evidenced; public reads may remain `NOT_ASSERTED`.

## Quality separation

### Connector quality

Measures whether the observation route successfully resolved:

- repository metadata;
- the current head commit;
- SHA-bound artifact links;
- the workflow invocation state.

A partial connector error is capped at 75. A blocked connector scores zero.

### Data quality

Measures whether the observation is:

- source linked;
- bound to the observed head SHA;
- populated across required artifact categories;
- explicit about critical execution state.

Data quality does not prove the repository works. Connector quality does not prove the data is complete.

## First real observation

The first source-linked observation targets:

```text
GlacierEQ/AKOS
head: 1607c0d27897ea963eb572062300342f1922b84c
```

The observation confirms a public APEX repository, current head identity, package manifest, substantive source, test files, workflows, documentation, architecture, integration surfaces, and AI manifests.

It does not claim current build, test, documentation-contract, or security execution because the available direct-main status probe did not provide a current provider run receipt. The resulting assessment must therefore remain partial.

## CLI

```bash
PYTHONPATH=src python scripts/compile_live_repository_evidence.py \
  observations/repositories/GlacierEQ__AKOS__1607c0d27897ea963eb572062300342f1922b84c.json \
  --output status/repository-assessments/GlacierEQ__AKOS__1607c0d27897ea963eb572062300342f1922b84c.json \
  --require-state PARTIALLY_VERIFIED
```

## Streaming integration

A future GitHub App or reconciliation worker should emit the same observation schema. The adapter remains independent of the transport:

```text
webhook or reconciliation
        ↓
current repository observation
        ↓
this deterministic adapter
        ↓
health assessment
        ↓
portfolio projection
```

This preserves one compiler even when event intake, queues, or connector implementations change.
