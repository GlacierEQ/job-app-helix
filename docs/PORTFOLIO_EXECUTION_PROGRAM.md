# Portfolio Execution Program — Maximum Coherent Advance

Job-App Helix manages the recruiter portfolio as a set of distinct systems that must become **stronger, more complete, more integrated, and more demonstrable** without flattening their unique capability.

The execution program has two coordinated layers:

1. **High-level capability evolution** decides what purpose should be fulfilled, what missing or buried capability must be restored, what complementary systems should be composed, and what stronger operable form should exist.
2. **Low-level proof execution** discovers each repository's actual stack, chooses repository-native command vectors, executes bounded checks, and emits atomic receipts.

Proof serves capability. Proof does not decide whether a repository deserves to exist.

## Direction

```text
PURPOSE
  → CAPABILITY INVENTORY
  → LINEAGE / DONOR DISCOVERY
  → RESTORE LOST GAINS
  → IMPLEMENT MISSING FUNCTION
  → COMPOSE COMPLEMENTARY SYSTEMS
  → REPOSITORY-NATIVE PROOF
  → INTEGRATION
  → DEPLOYMENT / PACKAGE / OPERABLE DELIVERY
  → NEXT UPWARD CHECKPOINT
```

The portfolio never uses `INVENTORY`, `UNVERIFIED`, naming similarity, age, a failed test, or a generated category as authority to archive, kill, merge away, or close a system.

## Evidence ladder

```text
INVENTORY
    ↓
DOCUMENTATION
    ↓
STATIC_ANALYSIS
    ↓
BUILD
    ↓
TEST
    ↓
INTEGRATION
    ↓
DEPLOYMENT
```

Promotion remains monotonic. A README proves documentation; it does not prove behavior. A successful build does not prove integration. A test process must report positive executed evidence when test proof is claimed. Deployment requires environment-specific execution evidence.

**Evidence level is not a worth score.** An unverified repository may contain strategically valuable algorithms, interfaces, integrations, research, specialist logic, or architectural donors that should be completed rather than discarded.

## Program architecture

```text
portfolio_repositories.json
          │ exact presentation boundary
          ▼
portfolio_rollout.json
          │ upward execution waves + evidence targets
          ▼
portfolio_contract.py
          │ anti-contraction policy + program validation
          ▼
portfolio_discovery.py
          │ README contract + stack detection + command planning
          ▼
portfolio_execution.py
          │ bounded execution + proof extraction
          ▼
portfolio_productization.py
          │ strongest useful delivery form
          ▼
capability archaeology / restoration
          │ recover prior gains without rewinding later gains
          ▼
INTEGRATED / DEPLOYED / OPERABLE SYSTEM
```

## Four upward waves

| Priority | Wave | Scope | Upward objective | Target |
|---:|---|---:|---|---|
| 1 | `wave-1-native-ci` | 20 | Evolve README Mesh nodes into stronger repository-native execution and proof while preserving distinct capability | `TEST` |
| 2 | `wave-2-tower-repair` | 1 | Advance Tower of Babel beyond native proof into stronger cross-language composition and integration | `INTEGRATION` |
| 3 | `wave-3-technical-exhibits` | 17 | Raise high-innovation technical exhibits into complete, executable, integrated systems | `TEST` minimum |
| 4 | `wave-4-capability-elevation` | 28 | Restore and productize every repository formerly placed in the consolidation/archive lane | `TEST` minimum |

Wave 4 is intentionally the counter-engineered replacement for the former `CONSOLIDATE_OR_ARCHIVE` program. The old classification is historical evidence only.

## Wave 4 hard contract

For every formerly labeled thin, overlapping, consolidation, or archive candidate:

1. reconstruct full intended purpose;
2. inspect current and historical implementation;
3. discover predecessor, successor, sibling, archive, backup, and branch donors;
4. identify unique value and complementary mechanisms;
5. restore buried or removed useful capability;
6. complete missing central functions;
7. compose with stronger estate capabilities without erasing specialization;
8. prove behavior with repository-native tests/builds/integration checks;
9. choose the strongest useful delivery form;
10. deploy or package where the natural purpose supports it.

No automated path may retire the repository.

## Anti-contraction invariants

- **Inventory cannot authorize retirement.**
- **Similarity cannot establish redundancy.**
- **A proof gap cannot establish irrelevance.**
- **A successor does not automatically supersede predecessor capability.**
- **A projection does not replace the source system.**
- **A public portfolio boundary does not define the full engineering estate.**
- **Local bounded-execution rules may not become global minimalism.**
- **No assistant-generated hierarchy outranks the repository's purpose or OPERATOR direction.**
- **Retirement requires explicit OPERATOR authorization plus verified preservation of valuable capability and lineage.**

## Repository-native proof

The planner detects actual technology boundaries rather than forcing one stack onto every repository.

| Detected boundary | Planned evidence |
|---|---|
| Python | bytecode compilation plus pytest or unittest with a positive test count |
| Node.js / TypeScript | declared lint, typecheck, build, and test scripts using the repository's package manager |
| Rust | `cargo fmt --check`, Clippy, and positive-count tests |
| Go | `go vet` and package tests |
| Swift | `swift test` |
| Maven / Gradle | native test lifecycle |
| CMake | isolated configure/build |
| .NET | `dotnet test` |

Polyglot breadth is valuable when languages own real technical responsibilities. Working software is not rewritten merely to increase language count.

## Execution receipts

Each command records repository identity, exact argument vector, evidence level, required/optional status, return code, elapsed time, timeout state, observed proof count, bounded output tails, blockers, and final state.

Commands execute without shell interpolation. Timeouts and required failures do not become green evidence. Receipts replace stale state atomically.

## Recovery before replacement

The program includes capability archaeology and restoration. If a historical commit contains useful functionality missing from current state, the preferred operation is additive recovery:

```text
strong donor capability
        +
current later gains
        ↓
combined stronger system
```

Do not restore an older file by overwriting a stronger later implementation without explicit replacement authority. Prefer composition and adaptation.

## Productization

The target is the strongest useful operable form supported by purpose, including:

- deployable service or application;
- operational agent/worker;
- installable package;
- powerful CLI;
- reusable protocol or schema layer;
- integrated specialist node;
- demonstrable engineering or research system.

Documentation-only completion is insufficient where executable behavior is implied.

## Commands

```bash
job-app-helix-portfolio validate

job-app-helix-portfolio render-program \
  --output artifacts/portfolio-rollout.md

job-app-helix-portfolio plan \
  --workspace repos \
  --json-output artifacts/portfolio-plan.json \
  --markdown-output artifacts/portfolio-plan.md

job-app-helix-portfolio execute \
  --workspace repos \
  --wave wave-1-native-ci \
  --receipt artifacts/wave-1-receipt.json
```

Workspace-mutating proof commands still require explicit execution authorization. That authorization boundary protects code while the **strategic direction remains upward**.

## Definition of done

The portfolio program is not complete merely because a curated subset is polished. It advances toward completion when every in-scope repository has:

- reconstructed purpose and consumer;
- known lineage and capability donors;
- unique value identified;
- buried useful capability restored;
- material central functionality implemented;
- repository-native proof appropriate to its claims;
- useful integrations exercised;
- an operable delivery form;
- documentation matching actual execution;
- no silent loss of predecessor, sibling, or branch capability.

The wider owned estate remains a dynamic discovery substrate beyond the recruiter-facing boundary. Relevant systems outside the presentation set remain valid capability donors and future productization targets.
