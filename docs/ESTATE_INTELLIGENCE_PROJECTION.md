# Estate Intelligence Projection

## Authority boundary

`src/job_app_helix/estate_compiler.py` remains the APEX estate compiler. This layer does not replace lineage, namespace isolation, APEX-system identity, capability donors, experiment routing, receipts, or the base public-safe filter.

The projection stage consumes the APEX compiler bundle and adds only information that is contextual rather than APEX authority:

```text
APEX estate bundle
  -> support/reference ancestry
  -> source-backed company intelligence
  -> role-capability fit
  -> company-specific promotion score
  -> audience projection
  -> recruiter website
```

## Support and reference ancestry

Dependency and reference relationships are not duplicate lineage. An evidence-bound `DEPENDENCY_OF` or `REFERENCE_OF` assertion may explain technology ancestry or supporting infrastructure without collapsing either repository into the other.

Support-only systems are retained internally but do not count as independent accomplishments and are omitted from the public accomplishment projection. Every support assertion requires explicit evidence references.

## APEX accomplishment projection

The raw APEX graph remains preserved. The downstream accomplishment count excludes systems that are only support/reference ancestry, current experiments, unresolved lineage candidates, or archived roots. This is a projection over the APEX graph, not a rewrite of APEX identity.

## Role relevance

The fifth promotion-score dimension is recalculated per company from capability overlap with declared target roles. Role profiles are policy-defined and use capability IDs already emitted by the APEX Capability Donor Registry.

A high role-fit score means that a system exposes capabilities relevant to a declared target-role profile. It is not a hiring prediction, affiliation claim, or evidence that an employer uses or needs the system.

## Company intelligence

The external Bottleneck Atlas is replayed as a dated source snapshot for external company tracks only. Each record preserves two distinct layers:

- **Observed operating pressure** - grounded in a named public source and SHA-256 receipt.
- **GlacierEQ inference** - inferred bottleneck, brick wall, leverage mechanism, expected impact, and application move.

The snapshot is historical and must be refreshed before a live application. GlacierEQ Core is excluded because estate cardinality is recomputed from the authenticated live census rather than inherited from the older atlas.

## Public boundary

The APEX `public_safe_projection()` remains the first public filter. The intelligence projection then tightens it further by omitting support-only systems, experiments, unresolved-lineage systems, private identities, legal-private records, and raw estate cardinalities.

The public page receives only `public-safe-company-projection-v2.json`. Full census and internal registries remain runner-local.

## Recruiter experience

The recruiter website wraps the existing verified site builder. It adds:

- company selection;
- target-role selection;
- recruiter / company-reviewer / senior-engineer depth;
- source-backed operating pressure;
- explicitly labeled GlacierEQ inference;
- role-specific proof systems ranked by capability fit and evidence;
- machine-readable public projection.

The page uses a same-origin JSON fetch only. CSP remains closed to external connections, and dynamic rendering uses DOM APIs rather than `innerHTML`.
