# GlacierEQ Job Application Hub

**Canonical root on disk:** `~/GlacierEQ_Swarm/job-app/`  
**Shortcut:** `~/job-app` → same folder  

**job-app-helix** is a reproducible build-and-verify campaign engine and evidence-bound README intelligence mesh. It provides deterministic campaign decisions (GO / NO-GO) with one transparent refinement stroke, plus tooling to audit and repair BrainSync skill index coverage.

---

## Start here

| Priority | Artifact | Description |
|----------|----------|-------------|
| **0** | [`src/job_app_helix/`](src/job_app_helix/) | Core Python package — campaign engine, pistons, README mesh |
| **0** | [`tests/`](tests/) | Pytest suite for campaign and README mesh |
| **0** | [`pyproject.toml`](pyproject.toml) | Build config, dependencies, lint rules |
| **1** | [`RECRUITER_EXECUTIVE_SUMMARY.md`](./RECRUITER_EXECUTIVE_SUMMARY.md) | Executive primer |
| **1** | [`HIERARCHICAL_PORTFOLIO_MAP.md`](./HIERARCHICAL_PORTFOLIO_MAP.md) | 6-tier architecture & repo catalog |
| **2** | [`hire_package/`](./hire_package/) | Resumes, outreach drafts, presentation notes |
| **2** | [`showcase/demo_15min_run.py`](./showcase/demo_15min_run.py) | Hero demo runner |
| **3** | [`apex_highway.py`](./apex_highway.py) | 61-node mesh health scanner |
| **3** | [`ci_audit_portfolio.py`](./ci_audit_portfolio.py) | Master CI audit (hashes, highway, hero tests, demo, links) |
| **3** | [`helix/`](./helix/) | BrainSync skill-index audit & repair automations |

---

## Layout

```
job-app/
├── src/job_app_helix/          ← Core package (campaign, pistons, README mesh, CLI)
│   ├── campaign.py             ← Deterministic GO/NO-GO campaign engine
│   ├── pistons.py              ← Flight / propulsion / ground assess/refine stages
│   ├── models.py               ← Dataclasses: CampaignReport, StageResult, Finding
│   ├── readme_mesh.py          ← README intelligence mesh (protobuf-backed)
│   ├── readme_mesh_manifest.py ← Manifest loader/validator
│   └── cli.py                  ← Entry points
├── tests/                      ← pytest suite
├── helix/                      ← BrainSync skill-index automations + proofs
│   ├── automations/            ← brainsync_index_skills, brainsync_kind_normalize
│   └── proofs/                 ← Proof tests for normalization logic
├── showcase/                   ← demo_15min_run.py (hero test runner)
├── hire_package/               ← Resumes, outreach staging, Musk-orbit variant
├── docs/                       ← Architecture, company morph map, mesh docs
├── apex_highway.py             ← 61-node mesh health engine
├── ci_audit_portfolio.py       ← Master CI audit script
├── generate_outreach_dms.py    ← Executive DM generator
└── pyproject.toml              ← hatchling build + ruff + mypy + pytest config
```

---

## Core Concepts

### Campaign Engine (`src/job_app_helix/campaign.py`)

A deterministic build-and-verify engine using three "pistons":

1. **Flight** — frame receipt completeness, event severity, backup margin
2. **Propulsion** — chamber pressure ratio, mixture ratio error, vibration
3. **Ground** — bandwidth availability, route health, backup capacity

Each piston:
- **Assess** → GO / WARN / NO-GO
- **Refine** (one stroke, if policy allows) → re-assess
- Campaign decides GO only if all stages pass after optional refinement

```python
from job_app_helix.campaign import run_campaign, LaunchScenario, CampaignPolicy

scenario = LaunchScenario.nominal()
report = run_campaign(scenario)
print(report.decision)  # CampaignDecision.GO or CampaignDecision.NO_GO
```

### README Mesh (`src/job_app_helix/readme_mesh.py`)

Protobuf-backed README intelligence mesh with:
- Manifest loading & validation (`readme_mesh_manifest.py`)
- Audience-aware section extraction (Recruiter / Expert / AI Agent)
- Evidence-bound highlights with SHA-256 integrity refs
- CLI: `job-app-helix-readme` (manifest, validate, export)

### BrainSync Skill Index (`helix/automations/brainsync_index_skills.py`)

Audits and repairs `.brainsync/index.json` to ensure all four expert-skill domains
(config, project, python, typescript) survive preview truncation.

```bash
python3 helix/automations/brainsync_index_skills.py audit
python3 helix/automations/brainsync_index_skills.py repair --dry-run
python3 helix/automations/brainsync_index_skills.py catalog
```

---

## Quick Start

```bash
# Install (editable)
uv pip install -e ".[dev]"

# Run tests
python3 -m pytest tests/ -v

# Lint
python3 -m ruff check .

# Type check
python3 -m mypy src/job_app_helix/

# Campaign demo
python3 -c "from job_app_helix.campaign import run_campaign, LaunchScenario; print(run_campaign(LaunchScenario.nominal()))"

# README mesh CLI
job-app-helix-readme manifest docs/readme_mesh.json
```

---

## CI Audit

```bash
python3 ci_audit_portfolio.py
```

Runs 5 steps:
1. Cryptographic baseline (SHA-256 hashes)
2. APEX Highway mesh health
3. Hero trio unit tests (TPS, Cooling, AKOS, Kimi)
4. Demo runner
5. Link verification

---

## Tech Stack

- **Language:** Python 3.11+
- **Build:** Hatchling
- **Lint:** Ruff (E, F, I, UP, B, SIM, RUF)
- **Types:** mypy (strict optional overrides for generated pb2)
- **Tests:** pytest
- **Serialization:** protobuf ≥ 6.31 (generated `readme_mesh_pb2.py`)
- **Style:** functional components, dataclasses with `slots=True`, PEP 604 union types

---

## License

MIT — see [LICENSE](./LICENSE).