# Estate Work Queue

The estate work queue converts an authenticated owned-library census into a deterministic review backlog without turning repository names into unsupported provenance claims.

## Execution

Generate the private census receipt first:

```bash
python scripts/census_owned_library.py \
  --owner GlacierEQ \
  --output /secure/path/owned-library-census.json
```

Then route every holding:

```bash
python scripts/build_estate_work_queue.py \
  --input /secure/path/owned-library-census.json \
  --output /secure/path/estate-work-queue.json
```

The full census and queue may contain private repository names. Keep those outputs outside the public repository.

## Lanes

| Lane | Meaning | Default action |
|---|---|---|
| `NATIVE_CANDIDATE_AUDIT` | Explicit census candidate expansion | Audit first |
| `NATIVE_PUBLIC_AUDIT` | Ungoverned public native repository | Provenance + value audit |
| `NATIVE_PRIVATE_AUDIT` | Ungoverned private/internal native repository | Internal-only audit |
| `FORK_REFERENCE_REVIEW` | Non-archived fork | Review upstream/local delta separately |
| `PRESERVE_ARCHIVE_BACKUP` | Archived or backup-classified holding | Preserve; no blind cleanup |
| `PRESERVE_GOVERNED_PRIORITY` | Existing priority-spine member | Keep current governance |
| `PRESERVE_GOVERNED_RECRUITER` | Existing recruiter-portfolio member | Keep current governance |
| `MANUAL_TRIAGE` | Metadata outside known routing rules | Stop and review |

## Invariants

- Every census repository must route exactly once.
- `repository_count`, `native_repository_count`, and `fork_repository_count` must reconcile with the embedded repository records before routing proceeds.
- Native work and fork-reference work remain separate queues.
- Archived and backup-classified holdings are preserved by default.
- Existing governed repositories are not re-admitted or silently reclassified.
- Repository names are not used to infer authorship, technical domain, maturity, or business value.

## Native audit sequence

For each native work item, the next stage should gather repository-native evidence before making a thematic or promotion decision:

1. identity, visibility, default branch, archive state, and current head;
2. README and declared purpose;
3. source/language structure and executable entry points;
4. tests, CI, build, security, and deployment evidence where present;
5. provenance and upstream similarity;
6. duplicate/successor relationship to other GlacierEQ repositories;
7. unique technical value and reusable components;
8. disposition: promote, preserve, consolidate candidate, continue experiment, or archive candidate;
9. receipt with exact source revision and unresolved boundaries.

No destructive action follows automatically from a queue assignment.
