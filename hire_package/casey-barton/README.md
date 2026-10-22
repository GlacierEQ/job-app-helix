# casey-barton/ — candidate data lanes

Reorganized 2026-10-13 (his order). `git mv` — history preserved, nothing deleted.

| lane | what lives here |
|---|---|
| `package/` | Shippable surfaces: READMEs, executive resume, portfolio brief, SEND_THIS, licensing, Tower of Babel integration |
| `proof/` | Proof surfaces: proof matrix (+JSON), claim register, role power matrix, promotion queue |
| `strategy/` | Strategy: expansion mandate, portfolio map, roadmap |
| `dossiers/` | Target dossiers: Anthropic, SpaceX, xAI Colossus bottleneck dossiers |
| `records/` | Machine JSONs: ledgers, receipts, manifests, censuses, package mesh, application spiral |
| `applications/` | Per-target outreach packets (INDEX.md each) — untouched by the reorg |

## Path contract (read before moving anything)

- `records/*.json` embed paths **relative to `casey-barton/`** (package_mesh audiences, FINAL_FORM_MANIFEST reading_order/machine_entrypoints, evidence_ledger coordinator evidence). Move a file → update the JSON.
- `evidence_ledger.json` `../../` evidence paths are relative to `records/` (one deeper than before).
- Builders keep the **artifact flat**: `scripts/build_final_form_package.py` reads from lanes but stages bare filenames into the package; `_rebase_staged_manifest` rewrites the staged manifest to flat names.
- `site/template.html` and `scripts/build_recruiter_site.py` hardcode `hire_package/casey-barton/<lane>/<file>` blob URLs — update on moves.
- Tests pin all of the above. Run the affected suites after any move:
  `test_final_form_package.py test_candidate_application_surface.py test_candidate_portfolio_boundary.py test_complete_delivery_package.py test_owned_library_census.py test_recruiter_site_deployment.py test_final_form_package_builder.py`
