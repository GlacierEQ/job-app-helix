# GlacierEQ Job Application Hub

**Canonical root on disk:** `~/GlacierEQ_Swarm/job-app/`  
**Shortcut:** `~/job-app` → same folder  

All hire surfaces, reports, presentations, elevate scaffolds, and score state live here (or are linked in).  
Old paths under `GlacierEQ_Swarm/jobapp_*` remain as **symlinks** so existing scripts keep working.

---

## Start here

| Priority | Open |
|----------|------|
| **0** | **[`demo_heroes.sh`](./demo_heroes.sh)** — always-green hero demo (TPS · NVIDIA couple · cooling physics) |
| **0** | **[`state/PRODUCTION_READINESS_VERDICT.md`](./state/PRODUCTION_READINESS_VERDICT.md)** — measured green status |
| **0** | **[`ANALYSIS_2026-07-17.md`](./ANALYSIS_2026-07-17.md)** — full re-analysis (truth only) |
| **0** | **[`FAST_PATH_JOB_ACQUISITION.md`](./FAST_PATH_JOB_ACQUISITION.md)** — speedy + solid strategy |
| **0b** | **[`spacex_sharklaser/SHARK_LASER_OMNI.md`](./spacex_sharklaser/SHARK_LASER_OMNI.md)** — omni shark-laser seat |
| **0c** | **[`docs/FOUNDATION_STACK_RATIONALE.md`](./docs/FOUNDATION_STACK_RATIONALE.md)** — why NumPy not JAX, etc. |
| **0d** | **[`docs/AKOS_ECHO_RUNTIME.md`](./docs/AKOS_ECHO_RUNTIME.md)** — max token/runtime (AKOS+ECHO) |
| 1 | [`hire_package/RESUME_GLACIEREQ_ELITE.md`](./hire_package/RESUME_GLACIEREQ_ELITE.md) · also [`RESUME_MUSK_ORBIT.md`](./hire_package/RESUME_MUSK_ORBIT.md) |
| 2 | [`hire_package/PRESENTATION_SPECIAL_PROJECTS.pptx`](./hire_package/PRESENTATION_SPECIAL_PROJECTS.pptx) · notes MD sibling |
| 3 | [`hire_package/CONTACTS_PERFECT_FIT.md`](./hire_package/CONTACTS_PERFECT_FIT.md) · [`OUTREACH_BACKDOOR.md`](./hire_package/OUTREACH_BACKDOOR.md) |
| 4 | [`hire_package/HONEST_SKILL_ASSESSMENT.md`](./hire_package/HONEST_SKILL_ASSESSMENT.md) · [`REPORT_AGENT_CAPABILITY_STOCK_VS_NOW.md`](./hire_package/REPORT_AGENT_CAPABILITY_STOCK_VS_NOW.md) · [`LINKEDIN_BUILDOUT.md`](./hire_package/LINKEDIN_BUILDOUT.md) |
| 5 | [`repos/`](./repos/) — heroes: cooling · TPS · AKOS · token_saver · spiral · gpu-health |
| 6 | [`spacex_sharklaser/SPACEX_SHARKLASER_SHOWCASE.md`](./spacex_sharklaser/SPACEX_SHARKLASER_SHOWCASE.md) · [`whole/WHOLE.md`](./whole/WHOLE.md) |
| morph | [`docs/COMPANY_MORPH_MAP.json`](./docs/COMPANY_MORPH_MAP.json) · missed: [`docs/MISSED_ANGLES_AND_MERGES.md`](./docs/MISSED_ANGLES_AND_MERGES.md) |

**Hire excludes:** AEON-777 (legal) · Pro-comet-agent (stub connectors).  
**Scores** = portfolio/demo depth — **not** flight certification.

---

## Layout

```
job-app/
├── README.md                 ← this index
├── repos/                    ← ALL hire-registry GitHub clones (shallow)
├── repos_list.txt            ← clone list
├── repos_inventory.json      ← name + size + path
├── hire_package/             ← resume, deck, outreach, capability report
├── showcase/                 ← multi-co framework showcase
├── whole/                    ← registry, PASS_LOG, hire whole
├── spacex_sharklaser/        ← SpaceX lens + readiness + P0/P1 notes
├── elevate/                  ← local elevate scaffolds (p0/p1/…)
├── state/                    ← symlinks to Swarm state jobapp scores/manifests
├── docs/                     ← toolbelt/AZOP/CLI guides (symlinks)
└── jobapp_*                  ← alias links for relative path compat
```

### repos/ (GitHub clones)

**46+** clones/scaffolds: hire-registry exhibits + **spiral-engine** + **GlacierEQ_Swarm** + **grokodile** (scaffold).  
**Hire exclude:** `AEON-777` (legal/MOC — never outreach).

```bash
ls ~/job-app/repos
cd ~/job-app/repos/xai-colossus-cooling
python3 ../nvidia-deep-reasoning/src/coupled_demo.py  # health-gated reasoning
```

Refresh list from registry then re-clone missing:

```bash
# re-pull all (example)
for d in ~/job-app/repos/*/; do git -C "$d" pull --ff-only --depth=1 2>/dev/null; done
```

Inventory: [`repos_inventory.json`](./repos_inventory.json)

### hire_package/
| File | Role |
|------|------|
| `RESUME_GLACIEREQ_ELITE.md` | Primary resume |
| `RESUME_MUSK_ORBIT.md` | Musk-orbit variant |
| `PRESENTATION_SPECIAL_PROJECTS.pptx` | Deck |
| `PRESENTATION_SPECIAL_PROJECTS.md` | Speaker notes |
| `REPORT_AGENT_CAPABILITY_STOCK_VS_NOW.md` | Stock vs OS capability report |
| `HONEST_SKILL_ASSESSMENT.md` | Strengths/gaps |
| `LINKEDIN_BUILDOUT.md` | LinkedIn copy |
| `OUTREACH_BACKDOOR.md` | Message drafts |
| `CONTACTS_PERFECT_FIT.md` | Who to contact |

### whole/
| File | Role |
|------|------|
| `WHOLE.md` | Unified structure |
| `REGISTRY.md` / `registry.json` | Exhibit status |
| `PASS_LOG.md` | One-by-one audit |
| `generate_whole.py` / `test_whole.py` | Generator + tests |

### spacex_sharklaser/
| File | Role |
|------|------|
| `SPACEX_SHARKLASER_SHOWCASE.md` | SpaceX-first showcase |
| `READINESS_SCORES.md` | Score headline |
| `P0_COMPLETIONS.md` / `P1_COMPLETIONS.md` | Iteration logs |
| `generate_showcase.py` | Generator |

### showcase/
Multi-company framework showcase (`SHOWCASE.md`).

### elevate/
Local source trees used to elevate GitHub repos (`elevate_p0`, `elevate_p1`, …).

### state/ (symlinks into `GlacierEQ_Swarm/state/`)
| Link | Role |
|------|------|
| `jobapp_repo_scores.json` | Demo readiness scores |
| `jobapp_priority_manifest.json` | P0 order |
| `jobapp_priority_p1_manifest.json` | P1 order |
| `jobapp_*_push.json` | Push logs |
| `quality_eval_research.json` | Code study eval |

### docs/ (symlinks)
| Link | Role |
|------|------|
| `TOOLBELT.md` | Toolbelt map |
| `AZOP_ORCHESTRATION.md` | A–Z agent waves |
| `GROK_BUILD_CLI.md` | CLI architecture |

---

## GitHub job-app repos

| Where | What |
|-------|------|
| **Local** | `~/job-app/repos/<name>/` — full shallow clones |
| **Remote** | `https://github.com/GlacierEQ/<name>` (mostly private) |
| **List** | `whole/registry.json` · `repos_list.txt` · scores in `state/` |

---

## Compat paths (do not delete)

| Old path | Points to |
|----------|-----------|
| `~/GlacierEQ_Swarm/jobapp_hire_package` | `job-app/hire_package` |
| `~/GlacierEQ_Swarm/jobapp_whole` | `job-app/whole` |
| `~/GlacierEQ_Swarm/jobapp_showcase` | `job-app/showcase` |
| `~/GlacierEQ_Swarm/jobapp_spacex_sharklaser` | `job-app/spacex_sharklaser` |
| `~/job-app` | `~/GlacierEQ_Swarm/job-app` |

---

## Quick commands

```bash
cd ~/job-app
open hire_package/RESUME_GLACIEREQ_ELITE.md
open hire_package/PRESENTATION_SPECIAL_PROJECTS.pptx
python3 whole/test_whole.py
python3 ~/GlacierEQ_Swarm/automations/score_jobapp_repos.py
```

---

*Consolidated 2026-07-13 · one hub for all job-app artifacts*

## Double helix

See [HELIX.md](HELIX.md). Runner: `jobapp_helix_spiral.py`.
