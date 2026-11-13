# Status

**State:** APEX_JOB_ECOSYSTEM_RESTORATION_ACTIVE  
**Identity:** APEX restores and governs the strongest verified project state  
**Law:** MAXIMUM_COHERENT_ADVANCE  
**Program:** [docs/apex/JOB_ECOSYSTEM_RESTORATION_PROGRAM.md](docs/apex/JOB_ECOSYSTEM_RESTORATION_PROGRAM.md)  
**Machine:** [machine/job_ecosystem_restoration.json](machine/job_ecosystem_restoration.json)  
**Last updated:** 2026-11-13

## Live architecture

child repos → **job-app-helix** (control) → **job-application** (projection) → **casey-barton-glaciereq.vercel.app**

## Governed projection bindings

| Capability source | Control | Public projection source | Public route | State |
|---|---|---|---|---|
| `GlacierEQ/mega-skills` | `job-app-helix` | `job-application/site-v15/mega-skills/` | `/mega-skills/` | SOURCE_VALIDATED · PUBLIC_HTTP_READBACK_VERIFIED |

Mega-Skills binding law: **every node in a Mega-Skill pyramid is a proper Skill at its scale**. Atomic Skills compound into proper reusable workflow Skills; those compound Skills form the complete mission-scale Mega Skill workflow/pipeline.

**Current verified public state (2026-11-13):** schema `glaciereq.public-mega-skills.v2`, **723 atomic Skills, 39 compound workflow Skills, 34 Mega Skills / pyramids**, 10 external-member references, zero unresolved owned references, and zero compound cycles. Source: `GlacierEQ/mega-skills@60face3915605909b9c7d3ed05a81dd289be3ba1`. The owning-site validator passed with 34 Mega routes and 197 detail blocks.

Current readback receipt: [receipts/MEGA_SKILLS_PUBLIC_READBACK_2026-11-13.json](receipts/MEGA_SKILLS_PUBLIC_READBACK_2026-11-13.json). Parent evidence observed the human route, machine JSON, source lock, and homepage at HTTP 200 with exact byte/hash matches to `GlacierEQ/job-application@dbbcde73e370ed442b8366a6964b2dbe85e07be1`; Vercel project `prj_5i9v2K5MyET7Yi7JwN2PCIj1AGZ1`, deployment `dpl_FsSBVngxeEQuCvHVFnVm6iLEFaxE`, provider state READY / production. This verifies HTTP delivery only, not Skill runtime execution, production adoption, every public detail route, or full Wave-5/program completion.

**Historical binding (2026-09-03, unchanged):** schema v1 completion target; 709 atomic Skills, 33 compound workflow Skills, 29 Mega apex Skills, 123 resolved internal compound→atomic references, 10 explicit external-Skill references, and zero unresolved internal references. These are historical counts, not the current public counts. Historical receipt: [receipts/MEGA_SKILLS_PROJECTION_BINDING_2026-09-03.json](receipts/MEGA_SKILLS_PROJECTION_BINDING_2026-09-03.json), SHA-256 `5a20f8933efeaccbd4e6f4aa596c112c66b46916946dc5bbd7849766f4769c9a`; its unresolved-at-that-time readback evidence and lineage remain intact.

## Wave status

| Wave | Focus | Status |
|---|---|---|
| 0 | Control identity + program bind | PR #194 |
| 1 | Critical hire path + leaf restores (MCP, Lambert) | LEAF PRs MERGED |
| 2 | Colossus + SpaceX family power restore | PENDING |
| 3 | Company excellence exhibits | PENDING |
| 4 | Operator runtime mesh (ECHO, apex-cli, swarm) | PENDING |
| 5 | Atlas closure + site re-project | ACTIVE — Mega-Skills public HTTP readback verified; broader closure remains open |

## Portfolio surface

- 66 live-linked repositories in `manifests/live_repository_links.json`
- Priority spine in `manifests/library_priority_spine.json`
- Flagship registry in `manifests/flagship_registry.json`
- Current Mega-Skills public HTTP readback in [receipts/MEGA_SKILLS_PUBLIC_READBACK_2026-11-13.json](receipts/MEGA_SKILLS_PUBLIC_READBACK_2026-11-13.json)
- Historical Mega-Skills architecture binding preserved in [receipts/MEGA_SKILLS_PROJECTION_BINDING_2026-09-03.json](receipts/MEGA_SKILLS_PROJECTION_BINDING_2026-09-03.json)

## Next rotor

1. Keep Mega-Skills pyramid generation synchronized with source Skills / Compound Skills / Mega registries.
2. Re-audit portfolio 66 for missing / neutralized / thin.
3. Restore Wave-2 physics family under dual-plane truth.
4. Continue Atlas closure and site re-projection without overwriting governed public bindings.

## Portfolio audit (2026-08-16)

- **68** checked (66 links + control extras)
- **0 missing** live links
- Heavy recent neutralization: apex-control-plane, spacex-orbital/launch/pad/propulsion/telemetry
- Receipt: `receipts/JOB_ECOSYSTEM_AUDIT_2026-08-16.json`

## Genius Engine

Executable invent runtime: `src/job_app_helix/genius_engine.py`  
Docs: `docs/apex/GENIUS_ENGINE.md`  
CLI: `PYTHONPATH=src python scripts/genius_engine.py invent --repository GlacierEQ/<leaf> --markdown`
