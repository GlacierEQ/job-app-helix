# Estate Evolution Engine: horizontal / vertical feature lineage

This is an **additive analysis contract** under `docs/ESTATE_EVOLUTION_ENGINE.md` and `docs/REPO_EXCELLENCE_COMPILER.md`, not a replacement orchestrator, branch-retirement pipeline, or authority to auto-merge.

## Mission: best-of-all-worlds synthesis

- **Horizontal decomposition:** group each observed repository implementation into named capabilities and independently testable feature facets. Do not equate repository count with outcome count or assume similar names establish lineage.
- **Vertical archaeology:** within each facet, recover dated original intent, source revision/blob, behavior evidence, failures, subsequent attempts, and the current/neighboring implementations. Historical roots and current branches may have no common Git ancestor; compare capability semantics and evidence directly.
- **Dream / skill reconciliation:** original ambition remains a target, not an executable claim; subsequent working code supplies measurable operating mechanisms. Preserve both, select non-dominated beneficial traits, and synthesize on *current* ownership with fresh tests.
- **Hidden-harm detection:** missing modern proof of a formerly observed feature is `CURRENT_PRESERVATION_UNVERIFIED`; only a sourced actual failure can be `CURRENT_FAILURE_EVIDENCED`. Neither state by itself authorizes source deletion, mutation, merging, release, deployment, or claims of successful restoration.
- **Estate-wide integration:** link capability families and cross-repository consumers back through the current estate census, capability donor registry, actual interface owners, APEX/Spiral mission contracts, and provider-native execution/verification receipts.

## Source contract

`job_app_helix.feature_lineage_reconciliation` is the pure, read-only compiler. It accepts one input JSON object with `schema: glaciereq.feature-lineage.v1`, `estate_snapshot` and a nonempty list of `observations`. Each observation must specify:

- `observation_id`, `capability_id`, `facet_id`, `outcome_id`, `intent`, `implementation`, `observed_at`;
- `role`: `historical`, `current`, `successor`, `sibling`, or `backup`;
- `truth`: `symbolic`, `declared`, `discovered`, `observed`, or `verified`;
- `sensitivity`: `ENGINEERING`, `PRIVATE`, or `LEGAL_PRIVATE`;
- `source`: exact repository name, 40-hex commit SHA, path, and 40-hex Git blob SHA;
- nonempty `evidence_refs`, optional `traits[]` and `failures[]` with their own source references and proof states.

`outcome_id` identifies an underlying substantive outcome, **not** a commit, artifact, backup, or countable accomplishment. Multiple distinct implementations can support the same outcome without inflating the global outcome count. Trait evidence cannot exceed the containing observation's truth state. Candidate donors with equal evidence state are retained together; no arbitrary winner is selected. Sourced traits in another repository are candidates, not automatic cross-boundary deployments.

Run locally:

```bash
python -m job_app_helix.feature_lineage_reconciliation \
    /path/to/source-linked-feature-observations.json \
    --output /path/to/internal-feature-reconciliation-receipt.json
```

The output is a deterministic SHA-256 digested receipt containing grouped facets, historical purpose, source-linked vertical histories, potential non-regression gaps, independently observed failures, candidate traits, and explicit `mutation_performed: false`. A source-shaped identifier is not an authenticated Git API readback by itself; the owning worker must obtain, hash and independently compare those source objects before claims are promoted.

## Hard boundaries and next engineering frontier

1. **No destructive automation.** Restore never means hard reset, archive, delete, drop an older branch, collapse sibling repositories, or silently activate a historical worker. Implement on the owning repository's current ancestry only after protecting the unique previous mechanisms and their consumers.
2. **Keep sensitive evidence internal.** All private/legal-private facet output is flagged `INTERNAL_ONLY`. The compiler does not produce public-safe projections. The caller must enforce namespace isolation and authorization at storage, API, and projection boundaries, not merely render a UI flag.
3. **No automatic harvesting claim.** This first compiler consumes observations. It does **not** yet crawl every branch, classify every function, verify every Git object, or populate the entire estate. Those are bounded discovery workers to compose from the existing census, `recovery_ref_graph`, `estate_federated_recovery`, and estate compiler.
4. **Comparative verification required.** Before promoting a candidate: independently source-read each donor; build exact-symbol behavior tests; deliberately induce failures; measure relevant runtime, cost, and safety changes; test impacted consumers; confirm no capabilities regressed; then emit repository-native and provider-native readback receipts.
5. **No false perfection claim.** Even completed lineage coverage does not prove absence of hidden harms. It creates a systematic falsifiable search, triage, and continuous regression process.

This feature analysis enriches existing APEX system/lineage and capability-donor artifacts rather than replacing them or advertising "everything restored" before executable proof.
