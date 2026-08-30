# Portfolio Root Truth

## One governed source, many synchronized projections

`GlacierEQ/job-app-helix` is the APEX portfolio control plane. It does not copy child repository source and it does not replace repository-native proof. It compiles admission, classification, evidence state, company alignment, role fit, estate intelligence policy, and projection boundaries into a single governed contract.

The APEX entrypoint is:

```text
manifests/portfolio_root_truth.json
```

Public raw URL:

```text
https://raw.githubusercontent.com/GlacierEQ/job-app-helix/main/manifests/portfolio_root_truth.json
```

## Two inventory planes, one authority

The portfolio now distinguishes two different things that must never be conflated:

1. **Admitted public portfolio subset** — the governed 67-repository inventory used for public proof, recruiter presentation, company dossiers, and stable downstream contracts.
2. **Authenticated owned-estate substrate** — the larger private repository field compiled at runtime into lineage-collapsed APEX systems, capability donors, experiment state, support/reference ancestry, and company/role projections.

The public 67-repository inventory is not a claim about the size of the owned estate. The authenticated estate census is runtime-private. Its raw cardinality, private identities, and legal-private records are intentionally absent from public root truth and downstream public bundles.

## Authority split

| Plane | Authority |
|---|---|
| Code, README, tests, releases, native receipts | Each APEX child repository |
| Admitted 67-repository public-portfolio boundary | `manifests/portfolio_repositories.json` |
| Authenticated estate compiler policy | `manifests/estate_compiler.json` |
| Role-capability, audience-cap, and support ancestry policy | `manifests/estate_projection_policy.json` |
| Evidence-bound estate assertion seed | `manifests/estate_facts.json` |
| Crown-jewel hierarchy and promotion gates | `manifests/flagship_registry.json` |
| Company alignment and company-specific repository sets | `manifests/company_dossiers.json` plus shards |
| External company operating-pressure snapshot | `manifests/application_intelligence/company_bottleneck_atlas.external.json` |
| Repository links and current evidence state | live-link and live-evidence manifests |
| Downstream projection policy | `manifests/portfolio_root_truth.json` |
| Public recruiter and machine presentation | `GlacierEQ/job-application` projection |
| Human, ATS, and machine résumé generation | `GlacierEQ/JOB-RESUME-BUILDER-` projection |

## Why this exists

The portfolio previously had several individually useful manifests, website data files, résumé facts, company matrices, evidence summaries, and a growing repository estate. The risk was not lack of information. The risk was **multiple surfaces becoming independent truth stores** or repository volume being mistaken for independent accomplishment.

The root-truth contract eliminates that failure mode:

1. Helix references existing governed manifests rather than rebuilding them.
2. A deterministic validator reconciles admitted inventory, flagships, company shards, and projections.
3. Every `HELIX_ADMITTED` repository must exist in the 67-repository admitted inventory.
4. Every admitted inventory child must map to at least one governed company or GlacierEQ Core track.
5. Authenticated estate compilation happens separately and never rewrites the admitted inventory into a repository-count résumé.
6. Duplicate, backup, archive, successor, dependency, and reference relationships are typed rather than counted as separate accomplishments.
7. Public projections may not publish private records, legal-private identities, authenticated census rows, or raw owned-estate cardinality.
8. A source-head, evidence, estate-policy, or company-intelligence change makes dependent projections stale.
9. Consumers pull from Helix at build time or use a link-only projection.

## Estate intelligence compiler

The estate compiler turns repository volume into a private intelligence substrate:

```text
authenticated owned estate
        ↓
namespace isolation
        ↓
lineage collapse
        ↓
APEX systems
        ↓
capability donors
        ↓
proof binding
        ↓
company + role projections
        ↓
public-safe bounded proof surfaces
```

The hard boundaries are intentional:

- legal-private material is isolated from recruiter, company, résumé, and public machine projections;
- support/reference ancestry does not collapse lineage and does not count as an independent accomplishment;
- unresolved duplicate/successor candidates remain unresolved until evidence-bound assertions exist;
- experiment state is not promoted as completed flagship work merely because a repository exists;
- company relevance is capability overlap, not employer affiliation, endorsement, or hiring prediction;
- external company operating-pressure records preserve the distinction between official-source observations and GlacierEQ inference;
- public recruiter surfaces remain compressed even when the private estate is large.

## Projection model

### Public portal

`GlacierEQ/job-application` consumes the root manifest and public-safe source records. It may change navigation, visual hierarchy, density, and audience ordering. It may not change evidence states, IDs, test counts, blockers, or authority boundaries.

The public portal may consume estate compiler policy, role-capability projection policy, and dated external company-intelligence metadata. It may not consume authenticated census rows, private estate identities, legal-private records, or the private estate assertion layer.

### Résumé Shapeshifter

`GlacierEQ/JOB-RESUME-BUILDER-` consumes the same public-safe authority. It selects evidence according to role while preserving the factual record. Human, ATS, and machine views are projections of the same claims.

### Company packets

Company dossiers are generated from company shards, current flagship evidence, the priority spine, and the estate intelligence layer. Private estate data may inform internal compilation, but any company packet that leaves Helix must pass the public-safe projection boundary. Company naming is alignment only and never implies affiliation, endorsement, employment, proprietary access, or production use.

### Machine runtime

Machine-public outputs may expose stable public-safe policy and proof metadata, not the private census. Exact code, receipts, schemas, and public repository identities remain source-bound; private identities remain withheld.

### Cloud resources

Google Drive, Dropbox, Box, and Notion may hold links, indexes, generated packets, private operational state, and evidence-bound internal assertions. They do not become competing sources of portfolio truth. Public projections receive only public-safe fields.

## Validation

Run:

```bash
python scripts/validate_portfolio_root_truth.py
python scripts/validate_portfolio_root_truth.py \
  --write-receipt artifacts/portfolio-root-truth-receipt.json
python -m pytest -q tests/test_portfolio_root_truth.py
```

The validator and contract tests check:

- source-file presence and SHA-256 identity;
- source and projection ID uniqueness;
- projection source resolution;
- the admitted 67 total repositories and 66 unique workspace children;
- the distinction between admitted inventory and authenticated estate policy;
- estate compiler, estate projection, estate-facts seed, and external company-intelligence source binding;
- public projections exclude the estate-facts layer;
- the live compiler policy names only the v2 public-safe workflow artifact and keeps internal receipts runner-local;
- unique flagship IDs;
- complete required company-track coverage;
- six-column repository-row contracts;
- every `HELIX_ADMITTED` repository against admitted inventory;
- every admitted inventory child against the governed dossier mesh;
- public/private publication boundaries;
- deterministic receipt generation.

## Update lifecycle

```text
child repository / estate policy / evidence changes
        ↓
Helix live evidence + authenticated estate refresh
        ↓
lineage / capability / company projection compilation
        ↓
Portfolio Root Truth validation
        ↓
deterministic internal + public-safe receipts
        ↓
public portal / résumé / machine / company projections
        ↓
deployment or document-package verification
```

No projection is current merely because it renders. It is current only when its required Helix sources validate and its own build succeeds. A public projection never becomes more authoritative by exposing more repository identities.

## Non-negotiable invariants

- No copied child source trees.
- No manually duplicated child READMEs as current truth.
- No private record in a public projection.
- No authenticated census row or raw owned-estate cardinality in a public bundle.
- No repository-count marketing as a substitute for proof.
- No support/reference edge counted as an independent accomplishment.
- No legal-private identity crossing into recruiter, company, résumé, or public machine surfaces.
- No company-affiliation implication.
- No promotion from source presence alone.
- No completion claim without a passing receipt.
