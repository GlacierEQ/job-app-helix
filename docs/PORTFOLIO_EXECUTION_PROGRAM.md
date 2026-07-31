# Portfolio Execution Program

Job-App Helix carries a programmatic path from an honest portfolio audit to repository-native proof. The program is intentionally split into two layers:

1. **High-level program control** decides what should be promoted, repaired, consolidated, or archived.
2. **Low-level proof execution** discovers each repository's actual stack, chooses non-shell command vectors, executes bounded checks, and emits atomic receipts.

The program never converts inventory, prose, or a zero-test exit into runtime proof.

## Executive outcome

The 67-repository job-application portfolio is managed as one reviewable system without flattening the responsibility of its individual repositories. Each repository moves through an explicit evidence ladder:

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

Promotion is monotonic. A repository cannot claim a higher state because a lower-level artifact exists. A README can prove documentation quality; it cannot prove a build. A build can prove compilation; it cannot prove behavior. A passing test process must report a positive proof count before it can establish test evidence.

## Program architecture

```text
portfolio_repositories.json
          │ exact 66-child boundary
          ▼
portfolio_rollout.json
          │ complete wave partition + evidence targets
          ▼
portfolio_contract.py
          │ schema, enum, policy, and partition validation
          ▼
portfolio_discovery.py
          │ README contract + stack detection + command planning
          ▼
portfolio_execution.py
          │ bounded non-shell execution + proof extraction
          ▼
RUNNING ───────────────► VERIFIED / PARTIALLY_VERIFIED
   │                     BLOCKED / UNVERIFIED / FAILED
   └──── atomic replacement, never stale-success retention
```

## Four approved rollout waves

| Priority | Wave | Repositories | Program decision | Promotion target |
|---:|---|---:|---|---|
| 1 | `wave-1-native-ci` | 20 | Add repository-native CI and positive-count test receipts to the README Mesh nodes | `TEST` |
| 2 | `wave-2-tower-repair` | 1 | Repair Tower of Babel until each advertised language boundary has executable proof | `TEST` plus build receipt |
| 3 | `wave-3-technical-exhibits` | 17 | Promote the strongest unverified technical exhibits with reference correctness and native tests | `TEST` |
| 4 | `wave-4-consolidation` | 28 | Complete, merge, package, or archive overlapping repositories with an explicit successor record | `DOCUMENTATION` decision |

The wave manifest exact-partitions all 66 child repositories. Missing, duplicate, or unexpected repositories invalidate the entire program before any command runs.

`JOB-RESUME-BUILDER-` entered the live boundary on July 31, 2026 because it is the lead public product presented by `job-application`, exposes an executable TypeScript truthfulness test suite, and must not remain outside the control plane that governs its recruiter-facing claims. The prior 66-repository audit artifacts remain immutable historical snapshots of their named boundary.

## Repository acceptance contract

A repository may be promoted only when all required gates for its wave are satisfied.

### Recruiter-facing gate

The README must contain, in this order:

1. `For recruiters and non-technical reviewers`
2. `For senior engineers and domain experts`
3. `For AI systems and toolchains`

The first layer communicates value and ownership. The second exposes architecture, tradeoffs, commands, failures, and proof. The third publishes stable machine contracts and typed relationships. Machine-local paths are rejected.

### Engineering gate

The planner detects repository-native boundaries rather than forcing one stack onto every project.

| Detected boundary | Planned evidence |
|---|---|
| Python | bytecode compilation plus pytest or unittest with a positive test count |
| Node.js / TypeScript | declared lint, typecheck, build, and test scripts using the repository lockfile runner |
| Rust | `cargo fmt --check`, Clippy with warnings denied, and positive-count tests |
| Go | `go vet` and package tests |
| Swift | `swift test` |
| Maven / Gradle | native test lifecycle |
| CMake | configure and build in an isolated proof directory |
| .NET | `dotnet test` |

A language is valuable only when it owns a real responsibility, interface, command, and receipt. Polyglot breadth is therefore measured as architectural fit, not language count.

### Evidence gate

Every command records:

- repository and wave identity;
- exact argument vector;
- evidence level;
- whether the command was required;
- return code;
- elapsed time;
- timeout state;
- observed proof count;
- bounded stdout and stderr tails;
- final verification state.

Commands run with an argument vector, never shell interpolation. Missing executables become `BLOCKED`. Timeouts become `FAILED`. Zero-test success becomes `UNVERIFIED`. Build commands that write workspace artifacts remain blocked until `--allow-mutating` is explicitly supplied.

## State semantics

| State | Meaning |
|---|---|
| `VERIFIED` | Every required gate passed and the target evidence level was reached |
| `PARTIALLY_VERIFIED` | Valid evidence exists, but it stops below the wave target |
| `BLOCKED` | Required repository, tool, contract, or authorization is unavailable |
| `UNVERIFIED` | A command did not produce enough positive evidence to support its claim |
| `FAILED` | A required check returned nonzero, timed out, or violated the contract |

The aggregate receipt uses the strongest adverse state. A single required failure cannot be averaged away by many passing repositories.

## Command surface

Validate the exact program contract:

```bash
job-app-helix-portfolio validate
```

Render the high-level program:

```bash
job-app-helix-portfolio render-program \
  --output artifacts/portfolio-rollout.md
```

Discover low-level commands without executing them:

```bash
job-app-helix-portfolio plan \
  --workspace repos \
  --json-output artifacts/portfolio-plan.json \
  --markdown-output artifacts/portfolio-plan.md
```

Plan only the first promotion wave and fail when blockers are found:

```bash
job-app-helix-portfolio plan \
  --workspace repos \
  --wave wave-1-native-ci \
  --fail-on-blockers
```

Execute non-mutating proof commands and atomically replace the receipt:

```bash
job-app-helix-portfolio execute \
  --workspace repos \
  --wave wave-1-native-ci \
  --receipt artifacts/wave-1-receipt.json
```

Authorize build commands only after reviewing the plan:

```bash
job-app-helix-portfolio execute \
  --workspace repos \
  --wave wave-2-tower-repair \
  --allow-mutating \
  --receipt artifacts/tower-repair-receipt.json
```

## Operational workflow

### Phase 1 — Contract validation

- Verify the exact 67-repository boundary.
- Verify that every child appears in exactly one rollout wave.
- Verify the complete evidence ladder and fail-closed policy.
- Reject unsafe repository identifiers and path traversal.

### Phase 2 — Deterministic discovery

- Inspect checked-in build manifests and test locations.
- Validate the three-layer README contract.
- Generate command vectors and classify mutating behavior.
- Surface unsupported stacks and missing proof paths as blockers.

### Phase 3 — Reviewable planning

- Emit JSON for automation and Markdown for human review.
- Keep generated plans deterministic; timestamps belong only in receipts.
- Review required versus optional commands before execution.

### Phase 4 — Bounded execution

- Run without shell interpolation.
- Set CI-safe environment variables.
- Enforce per-command timeouts.
- Parse runner-native positive evidence.
- Preserve output tails for diagnosis without unbounded logs.

### Phase 5 — Evidence promotion

- Compute the highest verified evidence level.
- Compare it with the declared wave target.
- Write one atomic repository and aggregate receipt.
- Update grades and README status only from the receipt.

### Phase 6 — Portfolio integration

- Add verified nodes to the typed README Mesh.
- Describe combined value through supported directional edge types.
- Keep blocked and unverified scope explicit.
- Preserve the audit trail for merges, archives, and successor repositories.

## Failure modes and controls

| Failure mode | Control |
|---|---|
| Partial workspace silently passes | Exact inventory partition and directory checks |
| One sample becomes a portfolio-wide claim | Per-repository receipts and achieved evidence levels |
| Zero tests return exit code 0 | Positive proof-count requirement |
| Hung compiler or test runner | Explicit timeout and `FAILED` receipt |
| Stale green receipt survives a failure | Atomic `RUNNING` → final replacement |
| Build modifies a repository unexpectedly | Mutating commands require explicit authorization |
| Shell injection through repository metadata | Direct argument vectors; no shell interpolation |
| README markets more than code proves | Audience contract plus evidence-state fields |
| Polyglot code becomes decorative | Stack-specific responsibility, command, and proof requirements |
| Thin repositories dilute the portfolio | Consolidate/package/archive wave with successor records |

## Definition of done

The program is complete when:

1. every Wave 1 repository has repository-native CI, a positive-count test receipt, and the optimal README frame;
2. Tower of Babel has green native proof for every advertised language boundary;
3. every Wave 3 exhibit has reference-correctness evidence and no unsupported performance claim;
4. every Wave 4 repository has a documented completion, merge, package, or archive decision;
5. the control plane can regenerate the portfolio plan and receipts from a clean canonical workspace;
6. recruiter, expert, and AI views all derive their state from the same evidence source.

This is not a campaign to make every repository sound finished. It is a system for finishing the right repositories, proving them precisely, and making the resulting portfolio unusually easy to trust.