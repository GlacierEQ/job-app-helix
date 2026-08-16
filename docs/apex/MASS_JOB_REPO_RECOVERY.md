# Mass Job-Repo Recovery

**Identity:** APEX is the counter to canonical destruction  
**Law:** MAXIMUM_COHERENT_ADVANCE

## Finding: nothing deleted

Authenticated census of the job-ecosystem recovery set:

- **Live portfolio links (66):** all **EXIST** (0 missing)
- **Critical ownership / flagships:** all mapped repos **EXIST**
- Apparent “missing” names were **system_ids** (`job_app_helix`, `tower_of_babel`, …) not GitHub names
- Only unresolved identity without a repo field: **aos** (never created)
- **Archived (preserve):** `MEGA-PDF`, `megaminds-pdf`

Destruction mode was **capability neutralization**, not mass hard-delete.

## Classes

| Class | Meaning |
|---|---|
| `NEEDS_DUAL_PLANE_POWER_RESTORE` | Recent truth-harden / synthetic-only stamps |
| `RECOVERY_ALREADY_STARTED` | Dual-plane / package / Lambert restore already on history |
| `HEALTHY_MONITOR` | No recent neutralization stamp |
| `ARCHIVED_PRESERVE` | Keep; unarchive only with operator order |
| `DELETED_OR_NEVER_EXISTED` | Must restore from backup/donor (none in this pass) |

## Commands

```bash
python scripts/mass_job_repo_recovery.py census
python scripts/mass_apply_dual_plane.py receipts/mass_recovery/NEEDS_DUAL_PLANE_ORDERED.json 15
```

## Receipts

- `receipts/mass_recovery/MASS_RECOVERY_CENSUS.json`
- `receipts/mass_recovery/MASS_RECOVERY_BOARD.md`
- `receipts/mass_recovery/MASS_ENROLLMENT_PRS.json`
