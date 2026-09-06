# Job-App System Audit — Source-bound Ownership and Evidence Flow

**Audit date:** 2026-07-30 HST
**Source-bound branch:** `main`
**Posture:** Evidence-bound. Repository names, README claims, hashes, branch age, and mergeability are not substitutes for current execution receipts.

## Executive verdict

Four repositories carry distinct responsibilities in the hiring system:

| Repository | Source-bound responsibility | Current decision |
|---|---|---|
| `GlacierEQ/job-app` | Private application operations | Retain privately and narrow to active campaign work. |
| `GlacierEQ/job-application` | Public recruiter distribution | Retain as the evidence-bound portfolio portal merged at `0ff1946f`. |
| `GlacierEQ/job-app-helix` | Portfolio truth, readiness, and verification control | Retain as the reference control plane merged at `04b86016`. |
| `GlacierEQ/the-tower-of-babel` | Technology and language-placement authority | Retain as the reference polyglot authority; consume pinned exports rather than duplicate source. |

The earlier ambiguity was not a lack of useful systems. It was competing authority: multiple repositories described themselves as the portfolio center, public visibility metadata had drifted, and historical aggregate claims exceeded current receipts.

## Resolution completed on 2026-07-30

### `job-application`

The public portal was rebuilt and merged into `main` at `0ff1946f22049bb22f614ea359b6c13ac0894f5f`.

Completed corrections:

- replaced repository-count marketing with a source-bound, evidence-bearing systems catalog;
- corrected stale visibility for AKOS, pro-code, and xAI Colossus Cooling;
- made the public showcase manifest-driven;
- hardened generation and tests against stale access claims and blocked content;
- linked the portal to Helix as its upstream evidence and governance authority;
- passed strict shared CI after repository-wide lint and formatting repair.

The portal is now reference for recruiter presentation, but it is not an independent portfolio-verification authority.

### `job-app-helix`

The root README and control-plane entrypoint were rebuilt and merged at `04b86016ce4282ad2c6d91a3db62810152bc824e`.

The current public surface now exposes:

- the exact sixty-six-repository boundary;
- the monotonic evidence ladder;
- four rollout waves covering all sixty-five child repositories;
- stack-native discovery and bounded execution;
- positive test-count enforcement;
- explicit authorization before mutating builds;
- atomic receipts that cannot preserve stale success;
- the README Mesh and machine integration contract.

Helix remains `PARTIALLY_VERIFIED` because child repositories retain independent states.

## Source-bound ownership rules

### Private application workspace — `job-app`

Owns:

- active applications and target-company packets;
- private resumes and contact routes;
- interview preparation;
- operator checklists and follow-up state.

Must not own:

- portfolio-wide verification law;
- public repository inventory;
- technology-placement authority;
- copied child-repository source trees.

### Public recruiter distribution — `job-application`

Owns:

- the evidence-bound portfolio front door;
- the generated public showcase;
- the public resume entrypoint;
- selected flagship links and review paths.

Must not own:

- independent portfolio grading;
- repository-wide execution state;
- technology doctrine;
- private application records.

### Portfolio control plane — `job-app-helix`

Owns:

- reference portfolio inventory;
- verification states and evidence semantics;
- rollout planning;
- campaign readiness;
- typed repository relationships;
- proof-weighted grades and receipts.

Must not own:

- private campaign material;
- a duplicate Tower registry;
- copied native source from child repositories;
- deployment claims unsupported by provider or repository-native evidence.

### Technology authority — `the-tower-of-babel`

Owns:

- technology-floor registry;
- language and format placement;
- W4H+How rationale;
- cross-language interfaces;
- polyglot proof classes;
- generated integration exports.

Helix consumes pinned Tower outputs. It does not duplicate Tower source or improvise competing language doctrine.

## Evidence flow

```text
Tower of Babel
technology placement and interface exports
                    │
                    ▼
Job-App Helix
inventory • verification • rollout • receipts • README Mesh
                    │
          ┌─────────┴─────────┐
          ▼                   ▼
job-application           job-app
public recruiter portal   private campaign operations
```

## Global controls

1. Exactly one repository owns each reference role.
2. Every aggregate count or grade names its source repository, source ref, scope, timestamp, and receipt.
3. Public source is not deployment proof.
4. A mergeable pull request is not a verified release.
5. A cancelled job is not an implementation failure.
6. Partial CI success is not portfolio-wide certification.
7. Machine-local paths are invalid public interfaces.
8. Private campaign material never enters public control-plane or recruiter artifacts.

## Next gates

1. Integrate the proof-weighted census and featured-verification assets onto current Helix `main`.
2. Validate ownership uniqueness in CI.
3. Generate recruiter-facing aggregate state from Helix receipts rather than duplicate calculations.
4. Record the current Tower release state and pin its integration exports.
5. Continue the README rollout repository by repository, promoting claims only when native receipts support them.

## Conclusion

The architecture is now explicit:

- **private execution:** `job-app`
- **public presentation:** `job-application`
- **portfolio truth and readiness:** `job-app-helix`
- **technology placement:** `the-tower-of-babel`

The repositories are strongest when they mesh through declared contracts while retaining separate authority and evidence boundaries.
