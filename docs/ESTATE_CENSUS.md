# GlacierEQ Repository Estate Census

## Current authenticated owner listing — 2026-11-16 HST

The connected GitHub owner listing was exhausted on November 16, 2026, with
repository identity deduplicated by GitHub's stable provider repository ID:

- **1,438 total GlacierEQ repositories accessible to the connected account**
- **714 public repositories**
- **724 private repositories**
- **15 result pages** at a page size of 100: pages 0–13 returned 100 each;
  page 14 returned 38 and terminated the enumeration
- **0 duplicate provider IDs** encountered

These figures are an observed, dated inventory, **not a maximum estate size**.
New holdings, removals, permission changes, and later source discoveries can change
them. Repository inclusion does not assert authorship, originality, maturity,
performance, production deployment, or recruiter readiness.

The connector's `page_offset` argument is documented as a zero-based item
offset, but **in this observed invocation it behaved as a zero-based page
index**. Incrementing it by 100 returned no results after the first page.
Enumerating page indices consecutively (0, 1, 2, …), checking stable provider
IDs, and exhausting the final partial page recovered the full 1,438 visible
holdings. Do not reuse item-offset assumptions across provider interfaces.

**Not established by this connector's normalized result:** the current
native-versus-fork split or archived counts. The list exposes identity,
visibility and archived metadata, but not a reliable `fork` classification.
For an exact native/fork breakdown, execute the existing authenticated
`scripts/census_owned_library.py` against GitHub's REST endpoint; that
implementation already uses the proper **one-based REST page parameter**,
iterates to source exhaustion, includes private/archived/fork records, rejects
duplicates, and stores full private identities only in ignored local state.
Do not rewrite that correct REST pagination to imitate this connector.

## Historical observations — not current ceilings

**August 7, 2026:** the earlier connected-account census observed 1,180 total
GitHub holdings: 598 native/non-fork repositories and 582 forks. Among native
repositories were 578 active and 20 archived, and 75 public and 523 private.
This arithmetic was accurate for that historical snapshot, not an immutable
membership boundary.

**July 31, 2026:** the public-safe summary
`manifests/owned_library_census_2026-07-31.json` recorded 1,171
owner-accessible repositories. Preserve this record and its historical
tests without silently updating it to current figures.

**September 23, 2026:** Monolith's
`catalog/COUNTING_SEMANTICS_RECONCILIATION.json` reconciled a 1,353-node
historical distinct universe including catalog-only and auxiliary placements.
It is a different source and counting boundary and must not replace the fresh
provider-native owner listing.

## Scope semantics

1. **Total holdings** — every accessible repository owned by GlacierEQ,
   including forks, public, private and archives; complete only for the
   observed provider view at the recorded time.
2. **Native estate** — holdings whose REST `fork == false`, the principal
   engineering-estate governance denominator; native does not prove
   original authorship or deployment.
3. **Fork layer** — holdings whose REST `fork == true`, tracked for
   upstream reference, study and any unique-value modifications.
4. **Recruiter portfolio** — a governed public projection, intentionally
   narrower than the complete inventory; it does not define membership.
5. **Priority spine** — a work-prioritization projection; never a ceiling
   on source discovery, estate classification or implementation recovery.

## Census and confidentiality contract

`scripts/census_owned_library.py` is the existing authenticated GitHub REST
owner-census mechanism. It produces a private, ignored full receipt containing
stable repository IDs, visibility, fork and archive states, native/fork
cardinalities, provenance classifications, and source-exhaustion positions.
Its optional `--expected-count`, `--expected-native-count` and
`--expected-fork-count` are drift assertions against an explicitly supplied
snapshot — **not defaults, inclusion gates or permanent project limits**.

Never publish private repository names or full private-census receipts on the
public hiring site. Privacy, authorization and evidence promotion are separate
from whether a repository is discovered and represented internally.

## Governance rule

**Membership is defined by source exhaustion, never by an arbitrary fixed
count.** Both native repositories and forks remain in the complete estate
graph with independent provenance, lifecycle, visibility and proof state.
Role-specific ranking, pagination, privacy and public promotion may alter
presentation; they must not silently erase engineering identities or reduce
the target architecture. Live observations supersede older totals for
present-tense inventory claims; historical evidence stays intact.
