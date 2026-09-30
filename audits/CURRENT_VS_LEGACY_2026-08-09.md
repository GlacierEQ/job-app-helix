# Current vs legacy — importance assessment

## What is current (trust this)

| Surface | What it is | Why it matters |
|---------|------------|----------------|
| **Vercel response headers** | V25 APPLICATION-COMPILER · V26 title · helix/source/truth commits | Production identity of the deploy |
| **`/data/current-proof.json`** | **V21 First Star Completion** · Mission Agentic AI Assurance · PRODUCTION_READY_VERIFIED | The active “what did we prove” star |
| **`/data/helix-root.json`** | 49 companies · helix projection from `job-app-helix` | Public machine atlas authority |
| **`job-app/manifests/*`** especially `flagship_registry.json` | 17 systems · L5 helix+AKOS **PROMOTED** · sigma_glue, doctor_strange, etc. | Control-plane ranking of the estate |
| **Home UI** | Speaks V23 / V22 / V21 (not V15) | Recruiter-facing brand |
| **`/data/resume.json`**, **company-families**, **psysoc-x** | Live 200 on machine layer | Hire-critical feeds |

**Current flagship ranking (helix registry, not V15 portfolio):**  
L5: `job_app_helix`, `akos` · L4 PROMOTED: `doctor_strange`, `sigma_glue`, `job_application` · others REFERENCE/BLOCKED with explicit next gates.

---

## What is old — importance rank

### Still live on CDN → HIGH risk if wrong
| Artifact | Importance | Verdict |
|----------|------------|---------|
| **`/data/portfolio.json`** with `release.name = V15 Final Hiring Release` | **HIGH (risk)** | Still HTTP 200; **linked from `/machine` and `/resume`**. Misleading version field. Flagship list is a **different world** from helix registry (almost no overlap except helix). **Rewrite or stop linking — do not ignore.** |
| Portfolio flagship list (colossus-2, microcode, nanosphere, …) | **MEDIUM–HIGH narrative debt** | Hire story still can surface these; helix already moved on. Microcode especially is liability. |

### Local trees → declining importance
| Artifact | Importance | Verdict |
|----------|------------|---------|
| **`site-v15/`** (188 files) | **MEDIUM** | Archaeology + possible build input residue; **live portfolio hash already ≠ local**. Not version authority. Label archive; stop hand-editing as SoT. |
| **`site-v14/`**, **`site-v13/`** | **LOW** | Superseded static trees. Keep in git only; zero product work. |

### Old code that still has value as proof, not brand
| Artifact | Importance | Verdict |
|----------|------------|---------|
| **Colossus family repos** (cooling, energy, security, servers, receipt-router) | **MEDIUM–HIGH as demos** | Real mechanisms; cooling tests green. Fine as **REFERENCE** case studies. **Not** the control plane or version name. |
| **Wave A/B PROMOTED leaves** | **HIGH under-exposed** | Newest gate-earned excellence; more “current” than V15 flagships, less visible on site. Worth elevating. |
| **V15 release *name* as brand** | **NONE** | Dead product version. Only matters as a bug to delete. |

---

## Overlap truth (why V15 list feels antique)

- Helix registry repos vs portfolio flagship repos: **almost no overlap** (shared: effectively helix only).
- Portfolio-only: colossus-*, microcode, coordinator, nanosphere, …  
- Registry has the **real** L5/L4 estate (AKOS, sigma_glue, doctor_strange, babel, …) that V15 portfolio never absorbed.

So the “old ones” aren’t just older numbers — they’re a **parallel ranking** that never got retired when helix became authority.

---

## Priority if you only fix three things

1. **Retire V15 as version** on `/data/portfolio.json` (or generate portfolio from helix so it can’t drift).  
2. **Align flagship list** with `flagship_registry` (demote microcode; don’t lead with blocked/missing).  
3. **Leave site-v13/v14 alone**; treat site-v15 as archive unless the build still copies from it (then fix the build).

