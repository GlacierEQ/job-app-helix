# Job-App System Audit — Canonical Ownership, Duplication, and Tower Truth

**Audit date:** 2026-07-30 HST  
**Audit branch:** `audit/proof-weighted-portfolio-2026-07-29`  
**Posture:** evidence-bound; repository names, README claims, hashes, and local-only paths are not substitutes for current execution receipts.

## Executive verdict

The GlacierEQ job-application estate currently has four relevant repositories with overlapping historical language:

1. `GlacierEQ/job-app`
2. `GlacierEQ/job-application`
3. `GlacierEQ/job-app-helix`
4. `GlacierEQ/the-tower-of-babel`

The system is not missing its strongest Tower implementation. The 30-floor implementation exists in the correct standalone repository on branch `build/canonical-executable-tower`, represented by Tower PR #2. The primary defect is canonical promotion and stale control-plane truth: the default Tower branch still exposes a 21-language surface, while Job-App Helix still describes the stronger candidate as broadly blocked.

## Canonical ownership decision

| Repository | Canonical responsibility | Must own | Must not own | Current disposition |
|---|---|---|---|---|
| `GlacierEQ/job-app` | Private operator workspace for active applications | target-company packets, private resumes, access routes, interview preparation, operator checklists | portfolio-wide verification law, public language authority, duplicate source repositories | Retain private; narrow README and remove unsupported account-wide metrics. |
| `GlacierEQ/job-application` | Public recruiter-facing export bundle, if retained | generated resume, selected portfolio index, outreach templates, links to canonical evidence | independent audit engine, competing portfolio inventory, claims of universal CI verification | Consolidate into a generated/export role or archive after migration. |
| `GlacierEQ/job-app-helix` | Canonical portfolio evidence and campaign control plane | exact repository inventory, proof-weighted grades, verification states, README Mesh, campaign readiness, receipts | native source copies of child repositories, language-placement authority, private application materials | Retain as canonical control plane. |
| `GlacierEQ/the-tower-of-babel` | Canonical technology and language-placement authority | 30-floor registry, W4H+How placement, per-floor proof classes, cross-language interface graph, executable flagship, generated integration exports | portfolio scoring, active application tracking, duplicate copies inside Helix or job-app | Promote PR #2 after drift repair and complete verification receipt. |

## Repository findings

### 1. `GlacierEQ/job-app`

**Role observed:** private Job Application Command Center.

**Strengths**

- Appropriate location for private, operator-facing application work.
- Separates active execution tasks from the public portfolio.
- Can become the single private campaign workspace consumed by Helix decisions.

**Defects**

- The README includes broad account metrics that are not bound to a current receipt.
- Completion state is mixed with aspirational work and historical statements.
- Its name is close enough to Helix and `job-application` to create source-of-truth ambiguity.

**Decision**

Keep private. Declare that it consumes Helix evidence and Tower placement data but does not govern either. Add machine-readable links to the canonical repositories and prohibit copied child-repository source trees.

### 2. `GlacierEQ/job-application`

**Role observed:** public portfolio/resume and outreach bundle.

**Strengths**

- Recruiter-facing intent is useful.
- Resume and outreach generation are legitimate derived outputs.

**Defects**

- Its README claims broad portfolio verification and 100% passing tests without a current repository-by-repository proof boundary.
- It overlaps Helix inventory, audit, and public narrative responsibilities.
- Existing evidence-bound grading classifies it as unverified and requests a unique role or consolidation.

**Decision**

Do not let this repository remain an independent authority. Convert it to a generated distribution target sourced from Helix, or archive it after preserving any unique resume/outreach assets.

### 3. `GlacierEQ/job-app-helix`

**Role observed:** evidence-bound portfolio control plane.

**Strengths**

- Exact 66-repository historical boundary.
- Deterministic campaign and README Mesh contracts.
- Explicit distinction among documentation, runtime, deployment, and integrity evidence.
- Proof-weighted audit model with evidence caps.
- Existing PR #6 adds a reusable census and featured-repository verification engine.

**Defects**

- PR #6 previously contained only the audit engine skeleton, not this repository-ownership audit.
- Main-branch text still describes the Tower candidate as broadly blocked even though Tower PR #2 is now open, non-draft, and mergeable.
- Helix must not embed another Tower source tree; it must reference a pinned Tower revision and ingest generated exports.

**Decision**

Keep as the canonical evidence and campaign control plane. Replace stale Tower status with exact fields: repository, branch, PR, head SHA, mergeability, verified jobs, failed gate, cancelled jobs, and release state.

### 4. `GlacierEQ/the-tower-of-babel`

#### Default branch

`main` remains the older 21-language implementation.

#### Canonical candidate

- Branch: `build/canonical-executable-tower`
- PR: `#2 — Build the canonical executable Tower of Babel`
- Head: `86e6e387cca1af65cd543d4d8a60a61c4485ed45`
- Relative state: 86 commits ahead of `main`, zero behind
- Scope: 97 changed files, 4,967 additions, 201 deletions
- Registry: 30 governed technology floors
- Root authority: `registry/tower.yml` plus contained `registry/tower.d/*.json` fragments

#### Verified evidence at the audited head

GitHub Actions run `30535686985` reached executable jobs rather than failing at startup.

Successful jobs observed:

- portable C floor compilation
- portable Go floor compilation
- portable Rust floor compilation
- portable Protobuf floor compilation
- strict portable flagship mission pipeline

The flagship pipeline crosses TypeScript, Python, Rust, Go, SQL, WebAssembly, Lean 4, and Protobuf.

#### Current failing gate

The governance job installed the Tower and validated the canonical registry successfully, then failed the generated-surface drift gate. The exact stale outputs were:

- `README.md`
- `generated/smithery.registry.json`
- `generated/spiral-engine.registry.json`

Later governance steps were skipped because that fail-closed gate correctly stopped the job.

#### Cancelled surface

The TypeScript portable-floor job was cancelled during Rust toolchain setup before the TypeScript build command ran. It is not evidence that the TypeScript floor failed.

#### Correct status

`PARTIALLY_VERIFIED — MERGEABLE — RELEASE BLOCKED BY THREE-FILE GENERATED DRIFT`

This supersedes the older broad `Blocked / unverified` description. The project is not release-verified and must not be described as fully green until the three generated artifacts are regenerated, the workflow completes, and a release receipt is recorded.

## Duplication and source-of-truth rules

1. No repository may contain a second authoritative Tower registry.
2. `job-app-helix` may ingest a pinned Tower export but may not copy Tower source as a nested project.
3. `job-application` must consume generated Helix outputs rather than recalculate portfolio truth independently.
4. `job-app` may link private application packets to public evidence but may not publish private operator material into Helix.
5. Local `file:///Users/...` links are invalid public interfaces and must be replaced by repository-relative or canonical GitHub references.
6. Repository counts, language counts, grades, and verification states must name their exact scope and receipt.
7. A mergeable PR is not a verified release; a cancelled job is not a failed implementation; a partial CI success is not portfolio-wide certification.

## P0 remediation order

1. Regenerate the three stale Tower outputs from `registry/tower.yml` on `build/canonical-executable-tower`.
2. Re-run Tower Verification and require the governance gate, portable floors, flagship, integrity, proof, and receipt paths to complete according to their declared policy.
3. Merge Tower PR #2 only against its expected head after the receipt is captured.
4. Update Helix inventory and audit state to reference the merged Tower commit on `main`.
5. Convert `job-application` into a generated recruiter distribution surface or archive it after unique assets are migrated.
6. Narrow private `job-app` to application operations and declare Helix/Tower as upstream authorities.

## P1 control-plane hardening

- Add `manifests/job_app_repository_ownership.json` as the machine-readable authority for repository roles.
- Add a guard that fails when more than one repository claims `portfolio_control_plane` or `technology_placement_authority`.
- Add a duplicate-Tower detector for `registry/tower.yml`, `src/babel_registry.py`, and Tower test signatures outside the canonical repository.
- Require every recruiter-facing aggregate to carry `source_repository`, `source_ref`, `verified_at`, `verification_scope`, and `receipt`.
- Generate the public `job-application` bundle from Helix rather than editing it independently.

## Audit conclusion

The estate contains strong systems work, but its names and historical generation behavior produced competing authorities. The correct architecture is now explicit:

- private execution: `job-app`
- public export: `job-application`
- portfolio truth and readiness: `job-app-helix`
- technology placement and polyglot proof: `the-tower-of-babel`

The 30-floor Tower is the king. It is not lost; it is isolated on the correct standalone repository branch and requires a bounded three-file drift repair plus a complete CI receipt before promotion to `main`.
