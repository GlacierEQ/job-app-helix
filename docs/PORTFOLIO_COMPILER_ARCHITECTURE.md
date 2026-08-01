# Job App Helix — Portfolio Compiler Architecture

## Purpose

Job App Helix is the canonical compiler and control plane for the GlacierEQ job-application portfolio. It does not own or duplicate child-repository source code. It resolves live canonical repositories, verifies evidence, builds projections, and publishes recruiter, expert, and machine-readable surfaces.

## Source-of-truth rule

Each child project has exactly one canonical source repository:

`https://github.com/GlacierEQ/<repository>`

Helix may retain only:

- repository identity and canonical URL;
- current branch and head SHA;
- README, release, workflow, test, demo, and deployment references;
- capability, dependency, role-fit, and evidence metadata;
- generated summaries and presentation projections;
- immutable verification receipts.

Helix must not retain copied child source trees, copied repository archives, manually duplicated child READMEs represented as current, or unversioned code excerpts represented as live implementation.

## Compiler pipeline

```text
Canonical repositories
        │
        ▼
Live repository resolver
        │
        ▼
Provenance census + duplicate detector
        │
        ▼
Evidence and quality verifier
        │
        ▼
Canonical repository graph
        │
        ▼
Projection compiler
        │
        ├── recruiter site
        ├── executive resume evidence
        ├── technical portfolio brief
        ├── company-specific application packets
        ├── AI ingestion manifests
        └── verification receipts
```

## File provenance classes

Every tracked Helix file must resolve to one of these classes:

- `HELIX_NATIVE`: authored specifically for the Helix control plane.
- `GENERATED_PROJECTION`: reproducibly generated from canonical repository metadata or Helix-native contracts.
- `SHA_BOUND_EVIDENCE`: excerpt or receipt bound to an immutable repository URL and commit SHA.
- `TEST_FIXTURE`: synthetic or reduced fixture clearly marked as non-production.
- `HARD_COPY_CANDIDATE`: content that may duplicate a child repository and requires review.
- `FORBIDDEN_COPY`: copied source tree, archive, README, or current-code representation without immutable provenance.

## Required repository projection

Each selected repository projection must contain:

- repository full name;
- canonical repository URL;
- default branch;
- observed head SHA;
- visibility and archived state;
- canonical README URL;
- language and capability summary;
- test and CI evidence state;
- demo or deployment evidence state;
- verification timestamp;
- provenance coverage;
- quality score and data-quality score as separate values;
- unresolved blockers and next verification action.

## Quality gates

A repository cannot be promoted as `ELITE_VERIFIED` unless all required gates pass:

1. Canonical repository resolves.
2. Source code is substantive rather than placeholder-only.
3. README accurately describes current code.
4. Build or validation command is documented.
5. Tests or equivalent executable verification exist and pass.
6. CI or reproducible local verification receipt exists.
7. No exposed secrets or prohibited sensitive content is detected.
8. License and evaluation boundary are explicit.
9. Recruiter-facing claims are tied to evidence.
10. Helix projection points to the live origin rather than copied code.

Allowed states:

- `DISCOVERED`
- `LINKED`
- `CODE_CONFIRMED`
- `TEST_VERIFIED`
- `RECRUITER_READY`
- `ELITE_VERIFIED`
- `BLOCKED`
- `EXCLUDED`

State promotion is monotonic and receipt-backed. A stale head SHA marks dependent projections stale until re-verification.

## Regeneration policy

Generated outputs are disposable. They must be rebuilt from canonical repository observations and Helix-native contracts. A child repository update changes its head SHA; the next compiler run must detect the change, invalidate stale evidence, and regenerate affected projections.

## Failure handling

- One unreachable repository must not stop unrelated repositories from compiling.
- Connector or API failures must preserve the prior verified state and mark freshness stale or unknown.
- Alleged capabilities must not be promoted without code or executable evidence.
- A copied artifact must be quarantined before deletion when provenance is uncertain.
- Generated surfaces must fail closed when required evidence is missing.

## Canonical artifacts

- `manifests/portfolio_repositories.json`
- `manifests/live_repository_links.json`
- `manifests/portfolio_compiler.json`
- `scripts/portfolio_provenance_census.py`
- `scripts/validate_live_repository_links.py`
- `tests/test_portfolio_compiler_contract.py`
- `.github/workflows/portfolio-compiler-integrity.yml`
