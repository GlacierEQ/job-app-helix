# Status

**State:** APEX_JOB_ECOSYSTEM_RESTORATION_ACTIVE  
**Identity:** APEX restores and governs the strongest verified project state  
**Law:** MAXIMUM_COHERENT_ADVANCE  
**Program:** [docs/apex/JOB_ECOSYSTEM_RESTORATION_PROGRAM.md](docs/apex/JOB_ECOSYSTEM_RESTORATION_PROGRAM.md)  
**Machine:** [machine/job_ecosystem_restoration.json](machine/job_ecosystem_restoration.json)  
**Last updated:** 2026-09-03

## Live architecture

child repos → **job-app-helix** (control) → **job-application** (projection) → **casey-barton-glaciereq.vercel.app**

## Governed projection bindings

| Capability source | Control | Public projection source | Public route | State |
|---|---|---|---|---|
| `GlacierEQ/mega-skills` | `job-app-helix` | `job-application/site-v15/mega-skills/` | `/mega-skills/` | SOURCE_VALIDATED · PUBLIC_READBACK_UNRESOLVED |

Mega-Skills binding law: **every node in a Mega-Skill pyramid is a proper Skill at its scale**. Atomic Skills compound into proper reusable workflow Skills; those compound Skills form the complete mission-scale Mega Skill workflow/pipeline. Current canonical registry state at binding: 709 atomic Skills, 33 compound workflow Skills, 29 Mega apex Skills, 123 resolved internal compound→atomic references, 10 explicit external-Skill references, and zero unresolved internal references.

Binding receipt: `receipts/MEGA_SKILLS_PROJECTION_BINDING_2026-09-03.json`

## Wave status

| Wave | Focus | Status |
|---|---|---|
| 0 | Control identity + program bind | PR #194 |
| 1 | Critical hire path + leaf restores (MCP, Lambert) | LEAF PRs MERGED |
| 2 | Colossus + SpaceX family power restore | PENDING |
| 3 | Company excellence exhibits | PENDING |
| 4 | Operator runtime mesh (ECHO, apex-cli, swarm) | PENDING |
| 5 | Atlas closure + site re-project | ACTIVE — Mega-Skills projection source-bound |

## Portfolio surface

- 66 live-linked repositories in `manifests/live_repository_links.json`
- Priority spine in `manifests/library_priority_spine.json`
- Flagship registry in `manifests/flagship_registry.json`
- Mega-Skills public architecture binding in `receipts/MEGA_SKILLS_PROJECTION_BINDING_2026-09-03.json`

## Next rotor

1. Verify fresh public HTTP readback for `/mega-skills/` and `/data/mega-skills.json`; promote binding receipt only after provider-side proof.
2. Keep Mega-Skills pyramid generation synchronized with canonical Skills / Compound Skills / Mega registries.
3. Re-audit portfolio 66 for missing / neutralized / thin.
4. Restore Wave-2 physics family under dual-plane truth.
5. Continue Atlas closure and site re-projection without overwriting governed public bindings.

## Portfolio audit (2026-08-16)

- **68** checked (66 links + control extras)
- **0 missing** live links
- Heavy recent neutralization: apex-control-plane, spacex-orbital/launch/pad/propulsion/telemetry
- Receipt: `receipts/JOB_ECOSYSTEM_AUDIT_2026-08-16.json`

## Genius Engine

Executable invent runtime: `src/job_app_helix/genius_engine.py`  
Docs: `docs/apex/GENIUS_ENGINE.md`  
CLI: `PYTHONPATH=src python scripts/genius_engine.py invent --repository GlacierEQ/<leaf> --markdown`
