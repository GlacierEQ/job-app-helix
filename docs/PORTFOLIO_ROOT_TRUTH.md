# Portfolio Root Truth

## One governed source, many synchronized projections

`GlacierEQ/job-app-helix` is the canonical portfolio control plane. It does not copy child repository source and it does not replace repository-native proof. It compiles admission, classification, evidence state, company alignment, role fit, and projection policy into a single governed contract.

The canonical entrypoint is:

```text
manifests/portfolio_root_truth.json
```

Public raw URL:

```text
https://raw.githubusercontent.com/GlacierEQ/job-app-helix/main/manifests/portfolio_root_truth.json
```

## Authority split

| Plane | Authority |
|---|---|
| Code, README, tests, releases, native receipts | Each canonical child repository |
| Portfolio admission and 67-repository boundary | `manifests/portfolio_repositories.json` |
| Crown-jewel hierarchy and promotion gates | `manifests/flagship_registry.json` |
| Company alignment and company-specific repository sets | `manifests/company_dossiers.json` plus shards |
| Repository links and current evidence state | live-link and live-evidence manifests |
| Downstream projection policy | `manifests/portfolio_root_truth.json` |
| Public recruiter and machine presentation | `GlacierEQ/job-application` projection |
| Human, ATS, and machine résumé generation | `GlacierEQ/JOB-RESUME-BUILDER-` projection |

## Why this exists

The portfolio previously had several individually useful manifests, website data files, résumé facts, company matrices, and evidence summaries. The risk was not lack of information. The risk was **multiple surfaces becoming independent truth stores**.

The root-truth contract eliminates that failure mode:

1. Helix references the existing governed manifests rather than rebuilding them.
2. A deterministic validator reconciles inventory, flagships, company shards, and projections.
3. Every admitted repository must exist in the 67-repository inventory.
4. Every inventory child must map to at least one governed company or GlacierEQ Core track.
5. Public projections may not publish private records.
6. A source-head or evidence change makes dependent projections stale.
7. Consumers pull from Helix at build time or use a link-only projection.

## Projection model

### Public portal

`GlacierEQ/job-application` consumes the root manifest and public-safe source records. It may change navigation, visual hierarchy, density, and audience ordering. It may not change evidence states, IDs, test counts, blockers, or authority boundaries.

### Résumé Shapeshifter

`GlacierEQ/JOB-RESUME-BUILDER-` consumes the same source. It selects evidence according to role while preserving the factual record. Human, ATS, and machine views are projections of the same claims.

### Company packets

Company dossiers are generated from company shards, current flagship evidence, and the priority spine. Company naming is alignment only and never implies affiliation, endorsement, employment, proprietary access, or production use.

### Cloud resources

Google Drive, Dropbox, Box, and Notion should hold links, indexes, generated packets, and operational state. They do not become competing sources of portfolio truth. Private operational metadata may remain private, while public projections receive only public-safe fields.

## Validation

Run:

```bash
python scripts/validate_portfolio_root_truth.py
python scripts/validate_portfolio_root_truth.py \
  --write-receipt artifacts/portfolio-root-truth-receipt.json
python -m pytest -q tests/test_portfolio_root_truth.py
```

The validator checks:

- source-file presence and SHA-256 identity;
- source and projection ID uniqueness;
- projection source resolution;
- 67 total repositories and 66 unique workspace children;
- unique flagship IDs;
- complete required company-track coverage;
- six-column repository-row contracts;
- every `HELIX_ADMITTED` repository against inventory;
- every inventory child against the governed dossier mesh;
- public/private publication boundaries;
- deterministic receipt generation.

## Update lifecycle

```text
child repository changes
        ↓
Helix live evidence and classification refresh
        ↓
Portfolio Root Truth validation
        ↓
Deterministic receipt
        ↓
Public portal / résumé / machine / company projections
        ↓
Deployment or document-package verification
```

No projection is current merely because it renders. It is current only when its required Helix sources validate and its own build succeeds.

## Non-negotiable invariants

- No copied child source trees.
- No manually duplicated child READMEs as current truth.
- No private record in a public projection.
- No repository-count marketing as a substitute for proof.
- No company-affiliation implication.
- No promotion from source presence alone.
- No completion claim without a passing receipt.
