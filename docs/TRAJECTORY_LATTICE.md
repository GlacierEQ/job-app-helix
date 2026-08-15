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

The contemporary checkpoint executor captures authenticated owned-repository metadata from GitHub and hashes the corresponding Helix authority surfaces. Source files are represented by SHA-256 so later reconstruction can prove which evidence surface was observed.

## No false backdating

`historical_reconstruction` and `contemporary` are different evidence classes.

`scripts/capture_trajectory_checkpoint.py` refuses to use current GitHub state to manufacture a historical checkpoint. Historical nodes use `scripts/reconstruct_trajectory_checkpoint.py`, which queries authenticated Git history at an explicit HST cutoff and records the limits of what GitHub can actually prove.

Historical reconstruction has two distinct evidence strengths:

1. **Exact authority-tree evidence.** The executor resolves the Helix commit at the historical cutoff, retrieves its exact Git tree and blobs, and computes SHA-256 source and dimension hashes from those historical bytes.
2. **Bounded estate-survivor evidence.** For repositories that still exist and remain visible to the authenticated owner, the executor resolves the latest commit at or before the cutoff on the repository's surviving current default-branch lineage.

The second class is intentionally not called an exact historical estate census. GitHub's current repository enumeration cannot prove that repositories deleted or transferred away before reconstruction are absent, and current repository names, visibility, archive state, fork state, and default-branch names are not relabeled as historical metadata. Exact historical repository counts therefore remain `null` until corroborating evidence closes those gaps.

The default reconstruction cutoff is `23:59:59` HST on the checkpoint date. The exact cutoff is embedded in every reconstructed checkpoint. A different cutoff can be supplied explicitly when stronger dated evidence requires it.

`.github/workflows/trajectory-reconstruction.yml` provides a governed manual reconstruction path. It requires full-estate authority, refuses public-only fallback, preserves reconstructed evidence on `trajectory-reconstruction-2026`, and uploads the exact checkpoint artifact. Reconstructed evidence remains separate from canonical `main` until normal review and proof gates promote it.

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
