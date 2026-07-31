# Library README and Branch Consolidation Program

This program extends Job-App Helix from the exact 66-repository recruiter portfolio into a controlled path for the wider GlacierEQ-owned library.

It does **not** collapse those scopes into one misleading number:

1. **Priority spine** — the named repositories that define policy, presentation, governance, engineering standards, intelligence, and consolidation order.
2. **Recruiter portfolio** — the exact 66 repositories already partitioned by `portfolio_repositories.json` and `portfolio_rollout.json`.
3. **Owned library** — the dynamic owner-accessible GitHub estate, discovered at execution time and classified before mutation.

## Definition of done

A repository is not complete because its README is impressive. It is complete for a claimed evidence level only when:

- the README identifies the real user value and system boundary;
- referenced files, commands, interfaces, and relationships exist;
- repository-native checks prove the promoted behavior;
- generated surfaces are reproducible and drift-checked;
- blocked, planned, illustrative, and unassessed work remain labeled;
- branch value is preserved on canonical ancestry;
- obsolete pull requests are closed;
- obsolete remote branch refs are separately retired;
- the final disposition is recorded without conflating those events.

## The README impact contract

Every hardened public project should move through three seamless depths.

### Human value and strategic signal

A recruiter, operator, customer, or non-technical reviewer should quickly understand:

- the problem solved;
- the result delivered;
- why the project matters;
- the shortest inspectable proof path;
- the current maturity and limits.

### Engineering anatomy and failure behavior

A senior engineer should be able to inspect:

- architectural boundaries and owned responsibilities;
- runtime, data, interface, and persistence flow;
- build, test, benchmark, and verification commands;
- failure and blocker semantics;
- design tradeoffs and intentional debt;
- exactly what is not claimed.

### Machine entrypoint and repository mesh

An AI system or toolchain should receive:

- canonical repository and branch identity;
- machine-readable purpose, inputs, outputs, commands, and evidence;
- relationship types that do not imply unproved connectivity;
- explicit verified, blocked, and unverified scopes;
- links to manifests, schemas, receipts, and integration contracts.

Private documentation projects use the same truth rules, but recruiter framing may become operator, maintainer, or agent framing where public hiring presentation is not the intended surface.

## Proof promotion

```text
INVENTORY
  → DOCUMENTATION
  → STATIC_ANALYSIS
  → BUILD
  → TEST
  → INTEGRATION
  → DEPLOYMENT
```

Promotion is monotonic and evidence-bound. A stronger adjective does not create a stronger state.

- `TEST` requires a positive executed test count, not exit code zero with zero tests.
- `INTEGRATION` requires an exercised boundary, not a link or architecture diagram.
- `DEPLOYMENT` requires environment-specific evidence, not source availability.
- Performance claims require repeatable measurements with environment, inputs, and method.
- Provider connectivity requires current authenticated invocation receipts.

## Branch consolidation protocol

```text
DISCOVER
  → COMPARE
  → PRESERVE
  → VERIFY
  → MERGE_OR_CLOSE
  → DELETE_REF
  → RECEIPT
```

### Discover

Inventory all non-canonical branches and open pull requests. Determine whether each is active, merged, superseded, experimental, blocked, or abandoned.

### Compare

Use content, purpose, and merge history. Do not decide from branch age or commit counts alone; squash merges can make a fully merged branch appear divergent.

### Preserve

Move unique useful work onto current canonical ancestry. Preserve attribution and record why the older line is no longer authoritative.

### Verify

Run repository-native checks on the consolidated candidate. A branch is not obsolete merely because a newer branch exists.

### Merge or close

Merge verified canonical work. Close superseded or rejected pull requests with a disposition explaining where useful work went or why it was not retained.

### Delete ref

Delete the obsolete remote branch only after preservation and verification. Pull-request closure is not branch deletion. Tooling without ref-deletion authority must emit `DELETE_REF_REQUIRED`, not `DELETED`.

### Receipt

Record repository, branch, comparison base, unique-value result, verification result, pull-request disposition, remote-ref disposition, canonical commit, actor, and timestamp.

## Priority spine

The machine authority is [`manifests/library_priority_spine.json`](../manifests/library_priority_spine.json). Its current order is:

1. Tower of Babel — technology placement and proof policy.
2. Job Application — recruiter-facing front door.
3. Job-App Helix — portfolio execution, audit, and consolidation control plane.
4. Monolith — owned-library catalog and evolution topology.
5. AKOS — identity, authority, evidence, persistence, and completion governance.
6. `pro-code` — public executable engineering and proof strand.
7. `Pro_Code` — private operator doctrine, style, and agent-context strand.
8. Mastermind — intelligence orchestration system.
9. `megaminds-pdf` — identity candidate for the user-named “megamind,” intentionally unresolved until confirmed.

After the spine, execution follows the existing evidence-weighted portfolio waves, then expands through a fresh full-library census.

## Commands

```bash
job-app-helix-library validate
job-app-helix-library render --output status/LIBRARY_PRIORITY.md

job-app-helix-portfolio validate
job-app-helix-portfolio plan --workspace /path/to/repos --fail-on-blockers
```

The first command validates the constitutional priority and branch rules. The second existing command discovers repository-native proof plans for the exact recruiter portfolio.
