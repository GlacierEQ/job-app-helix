# job-app-helix — Project Audit

**Date:** 2026-11-20 (retrieval: live repository, active venv)
**Branch:** main (ahead 3 of origin/main)
**Commit:** `48625b7` (latest local)
**Python:** 3.11.18 in `.venv` (system is 3.9; project requires ≥3.11)
**Version:** 0.3.0 (synced across `pyproject.toml`, `src/job_app_helix/__init__.py`, `campaign.py`)

---

## Executive Summary

| Area | Status | Notes |
|------|--------|-------|
| **Tests** | ✅ **917 passing** | 917 tests in 4.2s (venv Python 3.11) |
| **CI/CD** | ✅ **Comprehensive** | 37+ GitHub Actions workflows; lint + test + validators + proof receipts |
| **Lint (Ruff)** | ✅ **Pass** (src/tests) | Legacy/excellence code excluded via per-file-ignores |
| **Type Check (mypy)** | ⚠️ **3 errors** | Not in CI; `StrEnum` redef + `map()` overload issues |
| **Security** | ✅ **Clean** | No secrets in git; `.gitignore` excludes `.env*` |
| **Deployment** | ✅ **Vercel** | Static site with security headers; GitHub deploy disabled |
| **Documentation** | ✅ **Extensive** | 100+ markdown files, README with verifiable claims |
| **Version Sync** | ✅ **0.3.0** | Synced across `pyproject.toml`, `__init__.py`, `campaign.py` |
| **Git Hygiene** | ⚠️ **2 files modified** | Uncommitted changes in `helix_flight_deck_bridge.py`, `repo_excellence.py` |

**Overall Grade: A−** — Excellent test coverage and CI, strong security posture, minor type-check gaps not enforced in CI.

---

## 1. Test Suite

```
917 passed in 4.2s (Python 3.11.18, .venv)
```

- Runs across Python 3.11 / 3.12 / 3.13 in CI
- Coverage gate set at **75%** (target 80%, not yet met)
- Test paths: `tests/` (121 test files)
- Includes validators, proof receipts, contract checks, README mesh generation

---

## 2. CI/CD Pipeline (`.github/workflows/ci.yml` + 37 workflows)

**Main CI (`ci.yml`)** runs on push/PR to `main`:
- Ruff lint on `src/`, `tests/`, `scripts/`, `showcase/`
- Pytest with coverage (`--cov=job_app_helix`)
- Portfolio CLI validation (`job_app_helix.portfolio_cli validate`)
- README mesh build + validation (render, contract check, protobuf comparison)
- Nominal / recoverable / hard-no-go campaign execution
- Public repository boundary check (`scripts/check_public_surface.py`)
- Proof receipt artifact upload

**Additional workflows (37 total):**
- Per-capability proof workflows (evidence-graph, application-execution, batch, etc.)
- Estate non-regression (calls `GlacierEQ/apex-control-plane` composite action)
- Branch lifecycle intelligence, crystallization crawls, portfolio census, etc.
- Concurrency control with `cancel-in-progress: true`
- Matrix: Python 3.11 / 3.12 / 3.13

**Gap:** **mypy not in CI** — type errors (see §4) do not block merges.

---

## 3. Lint (Ruff)

```
✅ src/ tests/ scripts/ showcase/ — clean
```

Per-file ignores in `pyproject.toml` for legacy/excellence code:
- `E501` (line length) on 16 files/patterns
- `E402`, `I001`, `UP017`, `B905` on specific scripts
- Rationale: "long embedded provenance, paths, and machine-readable literals are preserved for auditability"

---

## 4. Type Checking (mypy) — ⚠️ Not in CI

```
src/job_app_helix/portfolio_models.py:11: error: Name "StrEnum" already defined (possibly by an import)  [no-redef]
src/job_app_helix/estate_mesh.py:245-260: error: No overload variant of "map" matches argument types "type[str]", "object"  [call-overload] (8 occurrences)
```

**Impact:** Type errors exist but do not block CI (mypy not a CI step).
**Recommendation:** Add `mypy` to CI quality job or fix the 2 affected files.

---

## 5. Security & Secrets

| Check | Status |
|-------|--------|
| Credentials in git | ✅ None |
| `.env*` in `.gitignore` | ✅ Excluded (lines 4-6, 68) |
| `repos/` (cloned) in `.gitignore` | ✅ Line 1 |
| `.env.local` | ✅ Blocked from read (secret-bearing) |
| `.vercel/` in `.gitignore` | ✅ Line 67 |
| `artifacts/` in `.gitignore` | ✅ Line 69 |
| `state/` tracked | ✅ Explicitly allowed (`!state/`, line 65-66) |
| Hardcoded secrets | ✅ None found |
| Vercel config | Security headers present (CSP, frame deny, etc.) |

**Note:** `.gitignore` line 9 unblocks `state/` per operator mandate (verdicts + proof receipts tracked). Line 65-66: `!state/` + `!state/**`.

---

## 6. Deployment (Vercel)

`vercel.json` config:
- **Static site** build: `python3 scripts/build_recruiter_site.py`
- Output: `artifacts/pages-site`
- Install: `pip install --break-system-packages -e .`
- **Security headers**: CSP, frame deny, referrer policy, permissions policy
- Custom headers: `X-GlacierEQ-Source-bound-Public-Surface`, `X-GlacierEQ-Deploy-Source`
- GitHub integration: **disabled** (`"github": {"enabled": false}`)
- Framework: Vite (though build is Python script)

---

## 7. Git State

```
## main...origin/main [ahead 3]
 M src/job_app_helix/helix_flight_deck_bridge.py
 M src/job_app_helix/repo_excellence.py
```

**Uncommitted changes (2 files):**
1. `helix_flight_deck_bridge.py`: `BridgeStatus` changed to `StrEnum`; import cleanup (`sys`, `Enum` removed); matching logic now checks `display_name` or `company_id`
2. `repo_excellence.py`: `_require_text(company_evidence.get("claim_ceiling"), ...)` — result no longer assigned to `ceiling` variable (unused)

**Recommendation:** Commit or stash these changes.

---

## 8. Documentation & Evidence

- **100+ markdown files** across `docs/`, `audits/`, `excellence/`, `incidents/`, `manifests/`, `policies/`, `schemas/`, `status/`
- **README.md** with verifiable claims: 8 VERIFIED anchors (SHA-bound), 24 forward-deployed capabilities, 225 deserving repos
- **AUDIT_REPORT.md** (2026-07-28/08-08) documents quality gates: mypy clean at time of writing (now 3 errors)
- **Evidence surfaces**: `solidify/*.json`, `evidence_ledger_unified.json`, `manifests/*.json`, `ASPEN_GROVE_POINTER_INDEX.json`, `.agents/receipts/`

---

## 9. Architecture Highlights

- **Package**: `job_app_helix` (src layout, hatchling build)
- **Entry points**: 50+ CLI commands (`job-app-helix-*`)
- **Protobuf**: `readme_mesh.proto` → generated `readme_mesh_pb2.py` (mypy ignored)
- **Agent framework**: 10 worker roles, 5 execution modes, 7 workflows, 30 capabilities (6 core + 24 forward-deployed)
- **Forward-deployed capabilities**: 10 Anthropic, 7 NVIDIA, 7 SpaceX — all produce SHA-256 receipts
- **Estate**: 225 deserving repos, 83 admitted helix boundary, 8 VERIFIED anchors

---

## 10. Findings & Recommendations

### High Priority
| # | Finding | Recommendation |
|---|---------|----------------|
| 1 | **mypy not in CI** — 3 type errors unblocked | Add `mypy src/job_app_helix` to CI quality job or fix `portfolio_models.py` (StrEnum redef) and `estate_mesh.py` (map overloads) |
| 2 | **Uncommitted changes** — 2 modified files | Commit or stash the pending changes in `helix_flight_deck_bridge.py` and `repo_excellence.py` |

### Medium Priority
| # | Finding | Recommendation |
|---|---------|----------------|
| 3 | **Coverage gate at 75%** — target 80% | Track coverage gap; raise `fail_under` when 80% is reached |
| 4 | **System Python is 3.9** — project requires 3.11+ | Document `.venv` requirement in README/QUICKSTART for contributors |
| 5 | **mypy errors in portfolio_models & estate_mesh** | Fix StrEnum import conflict; fix `map(type[str], ...)` type annotations |

### Low Priority / Enhancement
| # | Finding | Recommendation |
|---|---------|----------------|
| 6 | **Ruff legacy ignores** — 16 per-file exclusions | Periodically review if code can be modernized to reduce ignore surface |
| 7 | **AUDIT_REPORT.md** dated 2026-08-08 | Update audit report to reflect current state (mypy errors, test count 917) |
| 8 | **Vercel `installCommand` uses `--break-system-packages`** | Acceptable for isolated Vercel build; no action needed |

---

## 11. Verification Commands

```bash
# Activate venv
cd /Users/kcbflux/Workspace/job-app-helix && . .venv/bin/activate

# Full quality gate (matches CI)
ruff check src tests scripts showcase/demo_15min_run.py
python -m pytest --cov=job_app_helix --cov-report=term-missing
python -m job_app_helix.portfolio_cli validate
python -m job_app_helix.readme_mesh_cli validate
python scripts/check_proto_contract.py
python scripts/check_public_surface.py

# Type check (not in CI)
python -m mypy src/job_app_helix

# Build recruiter site (Vercel)
python scripts/build_recruiter_site.py --output artifacts/pages-site --source-commit $(git rev-parse HEAD)
```

---

## 12. Memory Consolidation Note

Per compaction trigger: earlier free-tier-max setup fact (`mem_8831345bb45b4177`) already saved. No new durable facts from this audit require OMH capture.

---

**Audit complete.** The project is production-ready with strong evidence discipline; the primary action is adding mypy to CI and committing the two pending changes.