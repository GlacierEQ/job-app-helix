# Job-App Helix — Independent Audit

**Date:** 2026-11-19 (HST)
**Auditor:** Hermes agent (automated, E0 evidence below)
**Repository:** `GlacierEQ/job-app-helix`
**Commit audited:** `07124e2a12528640dc914b2bc7200ad0d91d6d09` (`main`, == `origin/main`, 0 ahead / 0 behind, working tree clean at start)
**Environment:** proot/Android, uv 0.13.7, project venv Python 3.11, pytest 9.2.0, ruff 0.16.0, mypy 1.20.2
**Scope:** full local re-run of every CI gate that can run offline, plus integrity, provenance, secret, version, and claim-vs-artifact checks.

---

## Executive Summary

| Area | Status | Evidence |
|---|---|---|
| Test suite | ✅ PASS | 1107 passed in 137.95s |
| Coverage gate | ✅ PASS | 76.49% (gate 75%) |
| Lint (ruff) | ✅ PASS | `All checks passed!` |
| Type check (mypy) | ❌ FAIL | 89 errors in 30 files — **not wired into CI** |
| Registry / root-truth / live-link validators | ✅ PASS | all three PASS |
| Portfolio rollout contract | ✅ PASS | `VALID`, 61 repositories |
| Public-surface boundary | ✅ PASS | 1499 tracked files |
| Proto contract | ✅ PASS | descriptor matches binding |
| README mesh | ✅ PASS | 21 repositories, 40 typed edges |
| Campaign fail-closed behavior | ✅ PASS | nominal/recoverable GO; hard-no-go exit 1 |
| Console entry points | ✅ PASS | 34/34 resolve |
| Secrets scan | ✅ PASS | no credential patterns |
| Version consistency | ❌ FAIL | three different versions |
| Doc ↔ manifest consistency | ❌ FAIL | 61 live vs 66/83/84 in docs |
| Hash-bound integrity surface | ❌ FAIL | 4 of 5 helix hashes mismatch |
| Machine portability | ❌ FAIL | 7 files hardcode Termux paths; ledger silently empty |

**Grade: B.** The engineering core is real and well-tested — 1107 tests, honest fail-closed behavior, clean lint, and three independent validators that pass. The failures are in the *evidence and integrity layer that is the repository's stated reason to exist*: the hash ledger is non-portable and returns an empty result off the original machine, the integrity manifest is stale, and the headline numbers in the docs no longer match the machine artifacts.

---

## 1. Evidence — commands actually run (E0)

```
uv run --frozen pytest --cov=job_app_helix --cov-report=term-missing
  → 1107 passed in 137.95s (0:02:17)
  → TOTAL 16911 statements, 3976 missed, 76%
  → Required test coverage of 75.0% reached. Total coverage: 76.49%

uv run --frozen ruff check src tests scripts showcase/demo_15min_run.py
  → All checks passed!

uv run --frozen mypy src/job_app_helix
  → Found 89 errors in 30 files (checked 112 source files)

uv run --frozen python scripts/validate_application_registry.py
  → PASS  {company_tracks: 166, helix_children_mapped: 61, total_inventory_repositories: 62,
           helix_children_exactly_once: true, unresolved_flagships: 1, zero_direct_omission_gate: true}

uv run --frozen python scripts/validate_portfolio_root_truth.py
  → PASS  receipt_sha256 673c8fa80e77631a6bf44de44f8b4562b2d0d56a8185c41f624d133044d11bc6
           counts {total_repositories: 62, workspace_repositories: 61, helix_admitted_memberships: 61,
                   company_tracks: 166, flagship_systems: 17, projections: 5}
           all 10 invariants true

uv run --frozen python scripts/validate_live_repository_links.py
  → PASS: Helix portfolio is link-bound to APEX repositories

uv run --frozen python -m job_app_helix.portfolio_cli validate
  → VALID  {schema glaciereq.portfolio.rollout.v2, waves: 4, repositories: 61}

uv run --frozen python scripts/check_public_surface.py
  → Public-surface check passed for 1499 tracked files.

uv run --frozen python scripts/check_proto_contract.py
  → Protobuf descriptor matches committed Python binding

uv run --frozen python -m job_app_helix.readme_mesh_cli validate
  → README mesh valid: 21 repositories, 40 typed edges, schema 1.0.0

uv run --frozen python -m job_app_helix nominal|recoverable
  → GO on all final verifications
uv run --frozen python -m job_app_helix hard-no-go --json
  → exit 1 (fail-closed preserved)

entry-point resolution: 34/34 console scripts import and expose their target
credential patterns (ghp_, github_pat_, AKIA, sk-, JWT, PRIVATE KEY): 0 hits
README relative links: 8 checked, 0 broken
```

**External dependency:** GitHub Actions is operator-gated on an account budget, so remote CI status could not be read. Every CI gate that does not require GitHub was re-run locally instead; results above are local E0, not CI-reported.

---

## 2. Findings

### P0 — Integrity layer is non-portable and silently empty

**F1. Seven source files hardcode Termux machine paths.**
`src/job_app_helix/{evidence_ledger,agent_cli,automation_engine,capability_federation,evidence_bridge,monolith_sync,tower_resolution}.py` all pin `/data/data/com.termux/files/home/{job-app-helix,monolith,the-tower-of-babel}` as module-level constants and CLI defaults.

Observed consequence (E0):

```
build_ledger() → total_repos 0, verified_anchors 0, entries 0,
                 merkle_root e3b0c44298fc1c14…  (SHA-256 of the empty byte string)
```

The ledger does not raise, warn, or skip — it returns a structurally valid but entirely empty ledger with an empty-string Merkle root. Any consumer that trusts `merkle_root` will accept "no evidence" as "evidence of nothing". This is a fail-open in the component whose documented purpose is hash-bound proof.

This also violates the repository's own boundary: `SECURITY.md` states the repository "must not contain … personal machine paths". `scripts/check_public_surface.py` cannot catch it — `FORBIDDEN_CONTENT` covers `/Users/` and `C:\Users\` but has no pattern for `/data/data/`, `/root/`, or any Android/Termux prefix. The boundary checker has a gap exactly where the violation is.

**F2. The helix hash-integrity manifest is stale — 4 of 5 hashes mismatch.**

| File | Declared | Actual |
|---|---|---|
| `proofs/proof_brainsync_skill_index.py` | `216041e1…` | `216041e1…` ✅ |
| `proofs/proof_brainsync_kind_normalize.py` | `acacdc2e…` | `84d94a42…` ❌ |
| `automations/brainsync_kind_normalize.py` | `ee2f9d6d…` | `7924f7a2…` ❌ |
| `automations/brainsync_index_skills.py` | `6c70655d…` | `d8237cb8…` ❌ |
| `automations/brainsync_path_sanitize.py` | `fdb1415c…` | `49342b66…` ❌ |

The manifest declares `repo_name: job-app-helix-meta` and was last touched in `8a18651`; the bounded files changed in `f22ef19` ("Remove CANONICAL authority from active engine") without the manifest being regenerated. The hash-bound surface is therefore not maintained, and its `file_count: 5` is the only field still accurate.

### P1 — Consistency defects

**F3. Three different version identifiers.**

| Location | Value |
|---|---|
| `pyproject.toml` | `0.3.0` |
| `src/job_app_helix/__init__.py` (`__version__`) | `1.0.0-capability` |
| `src/job_app_helix/campaign.py` (`engine_version`) | `0.2.0` |

`AUDIT_REPORT.md` asserts "Version consistency ✅ Synced to 0.2.0" and its table lists `0.3.0`. Neither is true of the tree.

**F4. Headline counts in the docs do not match the manifests.**

| Claim | Source | Actual artifact |
|---|---|---|
| 83 workspace + 1 root | `README.md` | `manifests/portfolio_repositories.json` → 61 + 1 = 62 |
| 83 live APEX links | `README.md` | `manifests/live_repository_links.json` → 61 |
| 83 helix children mapped | `VALIDATION.md` | validator output → 61 |
| 84 total / 83 workspace | `VALIDATION.md` | 62 / 61 |
| 66 live-linked repositories | `STATUS.md` (updated 2026-11-13) | 61 |
| "225 repos, **83 VERIFIED anchors**" | `README.md` line 108 | code constant `VERIFIED_ANCHORS` has **8** entries |

`README.md` is explicitly a dated 2026-09-04 reconciliation, so its 83 is defensible as history — but `STATUS.md` (2026-11-13) and `VALIDATION.md` (undated, presented as "Success Output") are not dated and read as current. `README.md:108` is internally inconsistent with the code regardless of date.

**F5. Two CI workflows call scripts at a path that does not exist.**
`.github/workflows/portfolio-census.yml:122` and `.github/workflows/proof-weighted-portfolio-audit.yml:124,236` invoke `python audit/scripts/…`. There is no `audit/` directory; the scripts live at `scripts/proof_weighted_repo_census.py` and `scripts/run_featured_verification.py`. Both jobs would fail at that step.

**F6. mypy is not enforced and currently fails.**
`Found 89 errors in 30 files`. `ci.yml` runs ruff and pytest only. `AUDIT_REPORT.md` reports "Type checking (mypy) ✅ 0 errors" for a 10-file source tree; the tree is now 112 files. The claim is unreproducible.

### P2 — Hygiene

**F7. Scaffold artifacts still present.** `CHANGELOG.md` is one line ("Scaffolded by mermicorn-mega-boot"). `ROADMAP.md`, `goals.md`, `strategy.md`, `quality.md` are boot-template text. `mermicorn.repo.yaml` has `first_proof.status: planned` while `ROADMAP.md` step 1 says foundation is done — and `quality.md` requires "First-proof status uses an approved value".

**F8. Capability counts do not reconcile.** `README.md` lists 24 forward-deployed capabilities (10 Anthropic / 7 NVIDIA / 7 SpaceX). The modules expose 14 / 13 / 14 public capability methods respectively (16 / 15 / 16 minus `get_receipt_chain` and `verify_receipt`). The named README rows are a subset, so this is presentational — but the "24" is not derivable from the code.

**F9. `AUDIT_REPORT.md` is a stale artifact presented as current.** Dated 2026-07-28/08-08, it reports 12 tests; the suite is 1107. It sits at the repository root next to `README.md` and is the first file a reviewer reads.

---

## 3. What is genuinely healthy

- **Real test depth.** 1107 tests across 164 files, zero skip/xfail markers, network access mocked (`test_crystallization_crawler.py`, `test_owned_library_census.py`), no absolute-path assertions.
- **Fail-closed behavior verified, not asserted.** `hard-no-go` exits 1; `repo_excellence.py` actively rejects placeholder proof values (`tbd`, `todo`, `placeholder`, `resolved`, `hyper_validated_*`).
- **Three independent validators agree** and produce a re-computable SHA-256 receipt (`673c8fa8…`).
- **No secrets.** Credential-pattern scan clean across 1499 tracked files; the only `token =` assignment is a mock fixture.
- **Clean git state.** `main` == `origin/main`, 0 ahead / 0 behind, no dirty tracked files, no submodules, no files over ~220 KB.
- **Honest scope disclosure.** `docs/CLAIMS_AND_LIMITS.md` explicitly disclaims production deployment, manufacturer thresholds, and employment claims.

---

## 4. Recommended remediation (ordered)

1. **Make the ledger path-relative and fail-closed.** Replace the seven `/data/data/...` constants with paths derived from `Path(__file__)` plus optional CLI override, and make `build_ledger()` raise when the portfolio root is absent instead of returning an empty ledger. Add a test that asserts `merkle_root != sha256(b"")`.
2. **Regenerate `helix/.integrity/file_hashes.json`** from the current five files and add a CI step that re-verifies it, so drift fails the build.
3. **Close the public-surface gap.** Add `/data/data/`, `/root/`, and `com.termux` to `FORBIDDEN_CONTENT` in `scripts/check_public_surface.py`, with the seven affected files as the test case.
4. **Fix the two workflow paths** (`audit/scripts/` → `scripts/`) and add a CI lint that asserts every `python <path>.py` reference in `.github/workflows/` resolves.
5. **Pick one version.** Decide the release identifier, then set `pyproject.toml`, `__version__`, and `campaign.engine_version` from a single source.
6. **Refresh or date the docs.** Either update `README.md`/`STATUS.md`/`VALIDATION.md` to the current 61/62 counts, or mark each count with its observation date. Fix `README.md:108` (83 → 8 anchors).
7. **Wire mypy into CI** with a pinned baseline (or an explicit `[tool.mypy]` ignore list), so the 89 errors become visible instead of ornamental.
8. **Replace the scaffold files** (`CHANGELOG.md`, `ROADMAP.md`, `goals.md`, `strategy.md`, `mermicorn.repo.yaml` first-proof status) with real content or delete them.

---

## 5. Limits of this audit

- Remote GitHub CI status was not read (operator-gated). All results are local E0.
- The audit did not execute the network-dependent workflows (live freshness, estate crawl, census) or the Vercel/Cloudflare deployment paths.
- Capability-count and "verified anchor" claims were checked against code constants and manifests, not re-derived from upstream repositories.
- No changes were made to source, tests, manifests, or CI by this audit; this file is the only artifact produced.
