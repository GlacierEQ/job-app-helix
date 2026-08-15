# GlacierEQ 2026 Trajectory Lattice

The 2026 trajectory lattice is the canonical temporal model for measuring how the GlacierEQ engineering estate changed across expansion, acceleration, composition, rupture, diagnosis, counter-engineering, recovery, and stronger expansion.

## Authority

The machine-readable authority is `machine/trajectory/2026_schedule.json` in `GlacierEQ/job-app-helix` on canonical `main`. The schema is `schemas/trajectory_lattice.schema.json`. Captured checkpoint envelopes conform to `schemas/trajectory_checkpoint.schema.json`.

The schedule contains exactly 19 checkpoints:

`2026-01-01 → 2026-02-01 → 2026-03-01 → 2026-04-01 → 2026-05-01 → 2026-06-01 → 2026-06-15 → 2026-07-01 → 2026-07-15 → 2026-07-20 → 2026-07-25 → 2026-07-30 → 2026-08-01 → 2026-08-03 → 2026-08-05 → 2026-08-07 → 2026-08-10 → 2026-08-15 → 2026-08-20`

All time semantics use `Pacific/Honolulu`.

## State contract

Every materialized checkpoint records absolute state plus delta from the previous materialized checkpoint. Required dimensions are:

- repository inventory
- exact canonical default-branch heads
- genealogy
- capability ontology
- original intent
- development target
- implementation
- verification
- deployment/public projection
- job-application evolution
- company coverage
- company-specific inventions
- control-plane topology
- receipts
- blockers
- experiments
- source hashes

The checkpoint executor captures authenticated owned-repository metadata from GitHub and hashes the corresponding Helix authority surfaces. Source files are represented by SHA-256 so later reconstruction can prove which evidence surface was observed.

## No false backdating

`historical_reconstruction` and `contemporary` are different evidence classes.

`scripts/capture_trajectory_checkpoint.py` refuses to use current GitHub state to manufacture a historical checkpoint. Historical nodes must be reconstructed from dated Git history, receipts, workflow runs, release/deployment evidence, and other time-bounded sources. A missing prior materialized checkpoint is recorded explicitly rather than replaced with an invented delta.

## Contemporary preservation

`.github/workflows/trajectory-lattice.yml` is scheduled for 10:17 HST on August 15 and August 20. A year gate makes scheduled capture effective only for the 2026 lattice.

The workflow:

1. verifies the lattice contract;
2. requires `GLACIEREQ_ESTATE_TOKEN` and refuses public-only fallback;
3. captures authenticated owned-repository inventory and exact default-branch heads;
4. records Helix dimension tree hashes and source hashes;
5. computes delta when the previous checkpoint is already materialized;
6. writes the checkpoint to `machine/trajectory/checkpoints/YYYY-MM-DD.json`;
7. preserves the contemporary bytes on the `trajectory-captures-2026` branch;
8. uploads the exact checkpoint as a workflow artifact.

This preservation branch is evidence storage. Canonical promotion into `main` remains governed by normal Helix review and proof gates.

## Phase portrait

The governing interpretation is:

`expansion → acceleration → composition → rupture → diagnosis → counter-engineering → recovery → stronger expansion`

The purpose is not to count commits or repositories for vanity. The lattice exists to distinguish accumulation from structural phase change and to preserve enough evidence to explain what actually changed, when, and why.
