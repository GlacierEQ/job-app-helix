# Full Estate Mass Recovery

**Identity:** APEX is the counter to canonical destruction  
**Law:** MAXIMUM_COHERENT_ADVANCE

## Estate boundary (binding)

```text
ESTATE = every GlacierEQ-owned NATIVE repository (active)
```

**NOT:**
- the 66 `live_repository_links` hire projection
- “flagship only”
- priority spine as the whole world
- any 3-repo cosplay ceiling

The 66-list is a **recruiter projection** compiled from helix. Recovery operates on the **full owned native estate**.

## Live numbers (authenticated)

See `receipts/mass_recovery/FULL_ESTATE_CENSUS.json`:

| Layer | Count |
|---|---:|
| Total owned | ~1182 |
| Native | ~670 |
| Forks | ~512 |
| Native active | ~642 |
| Native public | ~160 |
| Native private | ~510 |

## Commands

```bash
# Full estate census + recovery classes (all native active)
python scripts/mass_job_repo_recovery.py census

# Name dump
python scripts/mass_job_repo_recovery.py names > /tmp/all_native_active.json

# Dual-plane enroll ANY slice of the full estate
python scripts/mass_apply_dual_plane.py receipts/mass_recovery/FULL_NATIVE_ACTIVE_NAMES.json 50 0
python scripts/mass_apply_dual_plane.py receipts/mass_recovery/FULL_NATIVE_ACTIVE_NAMES.json 50 50
```

## Deletion truth

Hard deletes vs never-created noise are listed in  
`receipts/mass_recovery/TRUE_MISSING_FROM_MANIFESTS.json`.  
Most “missing” names were `.git` suffixes, system_ids, or planned excellence leaves never created — not mass portfolio wipe.
