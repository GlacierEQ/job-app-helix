# Audit: casey-barton-GlacierEQ.vercel.app + connected repos

**TS:** 2026-08-09T23:23Z  
**Live:** https://casey-barton-GlacierEQ.vercel.app  
**Version authority (use this):** Vercel production headers + `/data/current-proof.json` + `/data/helix-root.json` + `job-app-helix` manifests  
**Do not use as version:** `portfolio.release.name = "V15 Final Hiring Release"` — **stale residue**

---

## Live version stack (from Vercel)

| Layer | Value | Evidence |
|-------|-------|----------|
| PSYSOC-X release header | `V25-APPLICATION-COMPILER` | `vercel_live_headers.json` |
| Title release header | `V26-TRUE-ALGERIAN-TITLE` | same |
| current-proof release | `V21 First Star Completion` · `PRODUCTION_READY_VERIFIED` | `site/data_current-proof.json.log` |
| Helix root ref | `83549cda4af3714304f202d0f4d35b29d28da9f7` | `site/data_helix-root.json.body` |
| Helix authority | `job-app-helix` manifests | helix-root `source.authority` |
| portfolio.release.name | **V15 Final Hiring Release (STALE)** | `live_vs_local_portfolio.json` |
| Local site trees | site-v13 / v14 / **v15 only** (no site-v23+) | `job-application/` |

**Conclusion:** Production is a **V21–V26 compiled stack**. V15 is an old static folder + a fossil field inside portfolio.json — not the product version.

Full: `live_version_stack.json`

---

## Executive scorecard

| Surface | HTTP | Notes | Evidence |
|---------|------|-------|----------|
| `/` home | **200** | Non-empty; V23/V22/V21 UI copy | `site/home.log` |
| `/master` `/machine` `/resume` `/companies` `/atlas` | **200** | Non-empty | `site/*.log` |
| `/data/resume.json` | **200** | Valid JSON | `site/data_resume.json.log` |
| `/data/portfolio.json` | **200** | Valid JSON; **release name still V15** | `site/data_portfolio.json.log` |
| `/data/company-families.json` | **200** | Advertised on `/machine` | `machine_data_endpoints.json` |
| `/data/psysoc-x-profiles.json` | **200** | Advertised on `/machine` | same |
| `/data/current-proof.json` | **200** | V21 star proof | same |
| `/data/helix-root.json` | **200** | Public helix projection | same |
| `/data/atlas.json`, `/data/machine.json`, `/data/companies.json`, `/data/helix.json` | **404** | Not loaded | `machine_data_endpoints.json` → `not_200` |

**Grade: B−** — live shell is advanced; **version labeling and some flagship cold-starts lag**.

---

## 1. Missing

1. **`xai-colossus-microcode` absent under `job-app/repos`** while still a portfolio flagship.  
   Evidence: `connected_repos.json`.

2. **Wave A/B `PROMOTED` leaves mostly absent from hire flagship narrative** (excellence earned, presentation lag).  
   Evidence: `connected_repos.json` PROMOTED ×16; excellence receipts.

3. **404 machine routes only (not “only resume+portfolio”):** /data/atlas.json, /data/companies.json, /data/helix.json, /data/machine.json.  
   **HTTP 200 machine data:** /data/company-families.json, /data/current-proof.json, /data/helix-root.json, /data/portfolio.json, /data/psysoc-x-profiles.json, /data/resume.json.  
   Evidence: `machine_data_endpoints.json`, `site/data_company-families.json.log`, `site/data_psysoc-x-profiles.json.log`.

4. **No `job-app/repos/job-app-helix` directory** — control plane is `~/job-app` (remote `job-app-helix`). Inventory must not call a missing repos leaf “present”.  
   Evidence: `connected_repos.json` job-app-helix.

5. **No excellence-state FSM on colossus flagships** ranked by portfolio artifact.  
   Evidence: `connected_repos.json` principal_state null.

6. **`source_prs_merged = 0`** in portfolio proof block.  
   Evidence: portfolio body.

---

## 2. Not good enough

1. **P0 — V15 portfolio release name vs live V21–V26 Vercel stack.**  
   Evidence: `live_version_stack.json`, `vercel_live_headers.json`.

2. **Live portfolio ≠ local site-v15 portfolio** (sha mismatch; helix live=`PARTIALLY_VERIFIED` vs local=`TEST_VERIFIED_WITH_RELEASE_GATES`).  
   Evidence: **`live_vs_local_portfolio.json`** (sha256, bytes, helix states side-by-side).

3. **`anthropic-agent-coordinator`:** site verified; local unittest import-broken.  
   Evidence: `repo_tests/anthropic-agent-coordinator.log`.

4. **`xai-colossus-2`:** site 69 tests; unittest discover **Ran 0**; `local_tests_green=false` (pytest suite, not green via cold unittest).  
   Evidence: `repo_tests/xai-colossus-2.log`, `connected_repos.json`.

5. **Microcode** still flagship-ranked while missing/blocked.  
6. **nanosphere** local test fail (py3.9 `dataclass(slots=…)`).  
7. **Atlas breadth** without binding Wave A/B PROMOTED mechanisms.  
8. **Claim dialect split** (portfolio / helix registry / excellence FSM).

---

## 3. Needs to be done

| P | Action |
|---|--------|
| **1** | Kill V15 as version: rewrite `portfolio.release` to live stack or drop; authority = helix + current-proof + headers |
| **2** | Stop treating `site-v15` as deploy source of truth; sync or generate portfolio from helix projection |
| **3** | Cold-start green: coordinator imports; document pytest for colossus-2; fix nanosphere |
| **4** | Restore or demote microcode |
| **5** | Publish Wave A/B PROMOTED leaves on site/atlas |
| **6** | Ship or unlink remaining 404 `/data/*` routes |

---

## Connected-repo inventory

File: `connected_repos.json` (27 entries).

| Bucket | Count |
|--------|------:|
| PROMOTED | 16 |
| present | 6 |
| not-good-enough | 3 |
| thin | 1 |
| missing | 1 |

### Site-named flagships (portfolio artifact — partially legacy list)

| Repo | Site state | Local | Grade |
|------|------------|-------|-------|
| xai-colossus-2 | TEST_VERIFIED | present; unittest 0 / pytest | not-good-enough |
| xai-colossus-microcode | REVIEWED_EXECUTION_BLOCKED | **MISSING** | missing |
| job-app-helix | PARTIALLY_VERIFIED | **MISSING under repos/**; alias `~/job-app` | thin |
| xai-colossus-security/servers/energy/cooling | BOUNDED_* | present | present / mixed |
| xai-colossus-nanosphere | BOUNDED_TEST_VERIFIED | test fail | not-good-enough |
| anthropic-agent-coordinator | TEST_VERIFIED_WITH_PROMOTION_GATES | import-broken | not-good-enough |
| AKOS | TEST_VERIFIED | present | present |
| job-application | deploy source | present (site-v15 fossil + newer commits) | present |

Helix **current** flagships (from local `manifests/flagship_registry.json` / live helix-root) include L5 helix+AKOS **PROMOTED** — prefer that list over V15-shaped portfolio flagships when ranking.

---

## Evidence index

- `live_version_stack.json`, `vercel_live_headers.json` — **current version**  
- `live_vs_local_portfolio.json` — sha + helix state comparison  
- `machine_data_endpoints.json` — full /data/* probe  
- `site_scorecard.json`, `connected_repos.json`, `findings.json`  
- `repo_tests/*.log`  
- `browser_skip.log`  
- this file: `AUDIT_SITE_AND_REPOS.md`
