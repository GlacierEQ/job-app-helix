# GlacierEQ Repository Estate Census

## Current live estate

Observed through the connected GitHub account on 2026-08-07:

- **1,180 total GitHub holdings**
- **598 native/non-fork repositories**
- **582 forks**
- **578 active native repositories**
- **20 archived native repositories**
- **75 public native repositories**
- **523 private native repositories**

The arithmetic closes exactly: `598 native + 582 forks = 1,180 total holdings`, and `578 active native + 20 archived native = 598 native`.

## Scope semantics

These counts describe different boundaries and must not be substituted for one another:

1. **Total holdings** — every repository owned by the GlacierEQ account, including forks.
2. **Native estate** — owned repositories with `fork == false`. This is the engineering-estate denominator for estate governance. It does not by itself establish authorship, originality, maturity, deployment, or business impact.
3. **Fork layer** — repositories with `fork == true`. These remain useful as reference, upstream, study, or customized-delta candidates, but they are not counted as native projects.
4. **Recruiter portfolio** — the separately governed hiring surface. Its repository count is intentionally smaller than the native estate and should not be presented as the total GlacierEQ repository count.
5. **Priority spine** — the smallest explicitly prioritized subset used for focused verification and promotion work.

## Census contract

`scripts/census_owned_library.py` is the authoritative authenticated census mechanism. It paginates the complete owned repository library and emits an internal receipt. The receipt now exposes:

- `repository_count` — all owned holdings, retained for backward compatibility;
- `native_repository_count` — all non-fork repositories;
- `fork_repository_count` — all forks;
- `active_native_repository_count` — non-fork and not archived;
- `archived_native_repository_count` — non-fork and archived;
- `native_visibility_counts` and `fork_visibility_counts` — visibility distributions by estate layer.

The CLI can fail closed against all three primary cardinalities with `--expected-count`, `--expected-native-count`, and `--expected-fork-count`.

## Historical receipts

Older checked-in census snapshots remain historical records. Their recorded counts should not be silently rewritten to match the current account. Current operational decisions should use a fresh authenticated census receipt or a separately dated live observation.

## Governance rule

The 598 native repositories are the top-level estate to classify, reconcile, and govern. The 582 forks are a separate reference/upstream layer. Neither layer is automatically recruiter evidence. Promotion still requires repository-specific provenance, unique-value analysis, verification, and an explicit governance decision.
