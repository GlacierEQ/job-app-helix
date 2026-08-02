# Repository Health Engine — Evidence Before Adjectives

## Purpose

The Repository Health Engine measures the current, provable condition of a canonical child repository. It does not grade repository names, README polish, language count, source-file count, or account ownership as substitutes for working software.

Every assessment is bound to:

- one canonical `owner/name` repository identity;
- one observed Git head SHA;
- one versioned scoring policy;
- dimension-specific evidence receipts;
- separate connector-quality and data-quality context.

A score is a projection of evidence. It is not evidence itself.

## Dimensions

| Dimension | Weight | Critical | Required proof direction |
|---|---:|---:|---|
| Reality | 15 | Yes | substantive code or executable behavior rather than placeholders |
| Build | 15 | Yes | clean, reproducible build or repository-native validation |
| Tests | 20 | Yes | positive executed-test evidence or equivalent executable verification |
| Documentation | 10 | Yes | current purpose, commands, architecture, limits, and evidence paths |
| Architecture | 10 | No | coherent boundaries, interfaces, failure behavior, and tradeoffs |
| Security | 10 | Yes | bounded secret, dependency, permission, and trust-surface evidence |
| Integration | 10 | No | real interfaces and typed portfolio relationships |
| Recruiter impact | 5 | No | truthful, quickly reviewable evidence presentation |
| AI readiness | 5 | No | deterministic machine contract and ingestion-safe metadata |

Weights total exactly 100. Connector quality and data quality are not hidden inside this score; they remain independent promotion gates.

## Evidence-state caps

A dimension receives points only after its raw score is multiplied by confidence and the evidence-state cap:

```text
points = weight × raw_score/100 × confidence × state_cap
```

| State | Cap | Meaning |
|---|---:|---|
| `VERIFIED` | 1.00 | current receipt is bound to the observed head SHA |
| `PARTIALLY_VERIFIED` | 0.70 | bounded proof exists, but named scope remains unverified |
| `STALE` | 0.40 | prior proof exists for an older SHA or is explicitly stale |
| `UNVERIFIED` | 0.00 | no adequate evidence exists |
| `BLOCKED` | 0.00 | verification cannot proceed and the blocker is preserved |
| `FAILED` | 0.00 | executed verification failed |

A requested `VERIFIED` state without a receipt is automatically downgraded to `UNVERIFIED`. A receipt targeting a different SHA is automatically normalized to `STALE`.

## Promotion gates

`ELITE_VERIFIED` requires all of the following:

1. health score of at least 90;
2. evidence coverage of at least 95%;
3. data-quality score of at least 90;
4. connector-quality score of at least 80;
5. every critical dimension currently `VERIFIED`;
6. no unresolved blockers.

A repository with a high numerical score but weak provenance, stale tests, unknown security, or poor connector reliability is not elite.

`RECRUITER_READY` requires a health score of at least 80 but remains below elite whenever any elite gate fails. The assessment preserves the exact failures so the next action is mechanical rather than subjective.

## Input contract

```json
{
  "repository": "GlacierEQ/example-repository",
  "observed_head_sha": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "observed_at": "2026-08-01T19:38:00-10:00",
  "dimensions": {
    "tests": {
      "state": "VERIFIED",
      "raw_score": 96,
      "confidence": 1.0,
      "verified_sha": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
      "receipts": ["receipts/tests/aaaaaaaa.json"],
      "findings": [],
      "blockers": []
    }
  },
  "quality_context": {
    "connector_quality_score": 95,
    "data_quality_score": 96
  },
  "blockers": []
}
```

Missing dimensions normalize to `UNVERIFIED` with zero points. Unknown dimensions fail closed rather than being silently accepted.

## Determinism and integrity

The engine emits:

- canonical input SHA-256;
- canonical policy SHA-256;
- deterministic assessment ID;
- normalized state for every dimension;
- exact weighted points;
- evidence coverage and confidence;
- elite-gate failures;
- blockers and next actions.

Identical input and policy produce an identical assessment. Time is supplied as evidence data rather than generated inside the scorer.

## Command

```bash
python scripts/compute_repository_health.py evidence/repository.json \
  --output status/repository-health.json
```

To enforce an elite-only promotion gate:

```bash
python scripts/compute_repository_health.py evidence/repository.json \
  --require-elite
```

Exit codes:

- `0`: assessment completed and any requested elite gate passed;
- `1`: assessment completed but `--require-elite` failed;
- `2`: input, policy, or filesystem validation failed.

## Portfolio integration

Repository health is one projection in the wider Helix compiler:

```text
canonical repository SHA
        │
        ▼
repository-native evidence receipts
        │
        ▼
repository health assessment
        │
        ├── current repository twin
        ├── capability graph confidence
        ├── recruiter inclusion gate
        └── next verification work packet
```

A new child-repository head SHA makes older dimension receipts stale. Helix may preserve their historical value, but it may not present them as current proof.
