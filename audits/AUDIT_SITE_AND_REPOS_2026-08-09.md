# Audit: casey-barton-GlacierEQ.vercel.app + connected repos

**TS:** 2026-08-09T23:11Z  
**Live:** https://casey-barton-GlacierEQ.vercel.app  
**Deploy source:** GlacierEQ/job-application (`job-app/repos/job-application`, site-v15)  
**Scope:** site-named + machine/portfolio/atlas-projected + local excellence cohort backing those claims (not full org crawl)

---

## Executive scorecard

| Surface | HTTP | Primary content | Evidence |
|--------|------|-----------------|----------|
| `/` home | **200** | Non-empty (V23 brand) | `site/home.log`, `site/home_text.txt` |
| `/master` | **200** | Non-empty technical master | `site/master.log` |
| `/machine` | **200** | Non-empty machine contracts | `site/machine.log`, `site/machine_text.txt` |
| `/resume` | **200** | Non-empty | `site/resume.log` |
| `/companies` | **200** | Non-empty (49 lenses claim) | `site/companies.log`, `site/companies_text.txt` |
| `/atlas` | **200** | Non-empty index | `site/atlas.log` |
| `/data/resume.json` | **200** | Valid JSON (~9.7KB) | `site/data_resume.json.log` |
| `/data/portfolio.json` | **200** | Valid JSON flagships×10 | `site/data_portfolio.json.log` |
| `/portfolio`, `/proofs` | **404** | — | `site/portfolio.log`, `site/proofs.log` |
| `/data/atlas.json`, `/data/machine.json`, `/data/companies.json` | **404** | — | `site_scorecard.json` → `routes_bad` |

**Overall presentation grade: B−** — recruiter shell is alive and relatively honest about limits, but **proof surface lags** behind (a) branded V23, (b) local Wave A/B PROMOTED excellence, and (c) reproducible cold-start tests for several flagships.

Full scorecard: `site_scorecard.json`

---

## 1. Missing

1. **`xai-colossus-microcode` not in local `job-app/repos`** while still a live portfolio flagship (`REVIEWED_EXECUTION_BLOCKED`, labeled primary pending).  
   Evidence: `connected_repos.json` → `xai-colossus-microcode.local_path_or_missing=MISSING`; `site/data_portfolio.json.body` flagships.

2. **Sixteen Wave A/B leaves at `principal_state=PROMOTED` are invisible on the hire site flagship list** (Anduril/Palantir/xAI/Cloudflare/Vercel/Waymo/NVIDIA/Groq/Databricks/AWS Trainium mechanisms). Site still leads with colossus-era flagships.  
   Evidence: `connected_repos.json` (16× PROMOTED); `job-app/excellence/receipts/wave_b_closed.json`; `job-app/excellence/receipts/go_run_latest.json`; portfolio flagships only 10 entries in `site/data_portfolio.json.body`.

3. **Machine JSON APIs incomplete:** `/data/atlas.json`, `/data/machine.json`, `/data/companies.json`, `/data/helix.json` → HTTP 404. Only resume + portfolio machine files load.  
   Evidence: `site/data_*.log`; `site_scorecard.json.routes_bad`.

4. **No `machine/excellence-state.json` on hire-critical colossus flagships** (`xai-colossus-2`, energy, cooling, security, servers, …) — excellence FSM never applied to the repos the site ranks highest.  
   Evidence: `connected_repos.json` `principal_state_if_any=null` for those names.

5. **Unmerged proof work:** `portfolio.proof.source_prs_merged = 0`; receipt-router limit still says draft hardening unmerged.  
   Evidence: `site/data_portfolio.json.body` `proof` + flagships[0].limit.

6. **Routes `/portfolio` and `/proofs` 404** (optional, but named mental model for recruiters).  
   Evidence: `site/portfolio.log`, `site/proofs.log`.

---

## 2. Not good enough

1. **V23 vs V15 authority desync (high).** Home copy: “V23 TRUTH SYNC”. Portfolio release still **V15 Final Hiring Release / 2026-08-04** (with `truth_sync_release` string bolted on).  
   Evidence: `site/home_text.txt`; `site/data_portfolio.json.body` → `release`; `site_scorecard.json.branding_note`.

2. **Live portfolio ≠ local site-v15 portfolio (high).** Content hashes differ; helix `state` live=`PARTIALLY_VERIFIED` vs local=`TEST_VERIFIED_WITH_RELEASE_GATES`. Live HTTP is presentation truth; local is not a faithful checkout of what is deployed.  
   Evidence: audit capture (live sha vs local sha); `site_source_notes.json`.

3. **Flagship claim > cold-start local proof (high).**  
   - `anthropic-agent-coordinator`: site `TEST_VERIFIED_WITH_PROMOTION_GATES`; local unittest discover → `ModuleNotFoundError`.  
   - `xai-colossus-2`: site 69 tests / `TEST_VERIFIED`; local `unittest discover -s tests` → **0 tests ran**.  
   - `xai-colossus-nanosphere`: site bounded-verified; local test path fails/thin.  
   Evidence: `repo_tests/*.log`; portfolio flagship states.

4. **Microcode as rank-2 “primary pending”** is honest about blocked CI but **still consumes flagship oxygen** without a local tree or green CI.  
   Evidence: portfolio flagships[microcode]; `connected_repos.json`.

5. **Atlas breadth without excellence depth (medium).** 49 company routes compile; Wave A/B PROMOTED mechanism leaves for those companies are not clearly elevated as the proof objects.  
   Evidence: `site/sitemap_locs.json` (49 atlas routes); `site/atlas_anduril.body` / `site/atlas_xai.body`; PROMOTED inventory.

6. **Dual claim dialects (medium).** Site: `TEST_VERIFIED` / `BOUNDED_*`. Estate: `PROMOTED` / gates. No recruiter-facing map between them.  
   Evidence: portfolio flagship `state` fields vs `machine/excellence-state.json` on Wave leaves.

7. **Helix partially verified (medium)** as control-plane flagship while job-app is the actual deploy/intelligence plane — easy to over-read.  
   Evidence: portfolio flagships[helix]; home “Estate Intelligence” branding.

---

## 3. Needs to be done (priority order)

| P | Action | Closes |
|---|--------|--------|
| **1** | Single-source truth-sync: home brand + `portfolio.release` + local `site-v15/data/portfolio.json` must match one authority commit (fix helix state drift). | V15/V23 + live≠local |
| **2** | Make flagship proofs cold-start green: fix `anthropic-agent-coordinator` imports; document/run real `xai-colossus-2` test entry from repo root; fix nanosphere. Capture dual-run logs. | Claim-ahead-of-proof |
| **3** | Restore or demote `xai-colossus-microcode` (clone + re-prove **or** remove from top flagships until CI green). | Missing + pending flagship |
| **4** | Surface Wave A/B **PROMOTED** leaves on hire UI (secondary flagship tier and/or atlas company proof cards). | Invisible excellence |
| **5** | Attach `machine/excellence-state` + operate/proof receipts to remaining colossus flagships **or** explicitly label them REFERENCE. | No FSM on flagships |
| **6** | Either ship `/data/companies.json` + atlas machine summary or stop implying a richer machine API than resume/portfolio. | 404 data routes |
| **7** | Merge or drop receipt-router hardening; keep `source_prs_merged` honest. | Unmerged PR tension |

Non-goal reminder: this audit does not redesign the site or mass-promote the estate.

---

## Connected-repo inventory (summary)

Full file: `connected_repos.json` (27 entries).

| Bucket | Count | Notes |
|--------|------:|-------|
| PROMOTED | 16 | Wave A/B excellence cohort — **not on site flagships** |
| present | 6 | Local trees with some tests |
| thin | 1 | Partial / desynced / blocked |
| missing | 1 | Named on site, absent locally |
| not-good-enough | 3 | Site claim stronger than local cold-start |

### Site-named flagships (from live portfolio)

| Repo | Site state | Local | Grade |
|------|------------|-------|-------|
| xai-colossus-2 | TEST_VERIFIED | present, discover=0 tests | not-good-enough |
| xai-colossus-microcode | REVIEWED_EXECUTION_BLOCKED | **MISSING** | missing |
| job-app-helix | PARTIALLY_VERIFIED | present, desynced | thin |
| xai-colossus-security | BOUNDED_TEST_VERIFIED | present | present |
| xai-colossus-servers | BOUNDED_TEST_VERIFIED | present | present |
| xai-colossus-energy | BOUNDED_TEST_VERIFIED | present | present |
| xai-colossus-cooling | BOUNDED_TEST_VERIFIED | present (13 tests green) | present |
| xai-colossus-nanosphere | BOUNDED_TEST_VERIFIED | thin/failing | not-good-enough |
| anthropic-agent-coordinator | TEST_VERIFIED_WITH_PROMOTION_GATES | import-broken tests | not-good-enough |
| AKOS (psysoc-x) | TEST_VERIFIED | present | present |
| job-application | deploy source | present | present |

---

## Claim vs proof tensions (high-signal)

1. Home **V23** vs portfolio **V15** release name/date — `site/home_text.txt` + portfolio `release`.  
2. Live portfolio hash ≠ local site-v15 portfolio — deploy/source drift.  
3. Flagship test counts on site not reproduced by naive local unittest discover for receipt-router + coordinator.  
4. PROMOTED excellence cohort earns gates the site never shows.  
5. `source_prs_merged=0` undercuts “executed public flagship” narrative if unmerged work is load-bearing.

---

## Evidence index (SCRATCH)

- `site/*.log` / `site/*.body` — HTTP captures  
- `site_scorecard.json` — route scorecard + tensions  
- `connected_repos.json` — inventory  
- `findings.json` — structured Missing / Not good enough / Needs  
- `repo_tests/*.log` — flagship local proof attempts  
- `browser_skip.log` — no Playwright; HTTP fallback used  
- `AUDIT_SITE_AND_REPOS.md` — this report  

---

## Method notes

- Live HTTP treated as presentation truth; local repos as proof truth.  
- Connected set = portfolio/resume-named GitHub repos + deploy source + Wave A/B excellence cohort. Full GlacierEQ org crawl deferred (would be a follow-on if site claims volume without inventory).  
