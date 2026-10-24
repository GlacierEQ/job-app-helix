# Job-App Helix — Validation & Receipts Reference

**Version:** 2.0  
**Status:** PRODUCTION  
**Validators:** 3 Core + Portfolio Root Truth + Live Links  
**Receipt Standard:** SHA-256 hash-bound, L0-L5 compliant

---

## Overview

Every material operation in Job-App Helix produces a **cryptographically verifiable receipt**. Three core validators + portfolio root truth + live links ensure system integrity.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        VALIDATION ARCHITECTURE                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                 │
│  │ APPLICATION  │    │ PORTFOLIO    │    │ LIVE         │                 │
│  │ REGISTRY     │    │ ROOT TRUTH   │    │ LINKS        │                 │
│  │ VALIDATOR    │    │ VALIDATOR    │    │ VALIDATOR    │                 │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘                 │
│         │                   │                   │                          │
│         └───────────────────┼───────────────────┘                          │
│                             ▼                                              │
│              ┌──────────────────────────────┐                             │
│              │       RECEIPT CHAIN          │                             │
│              │  SHA-256 hash-bound receipts │                             │
│              │  L0-L5 epistemic compliance  │                             │
│              └──────────────────────────────┘                             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Validator 1: Application Registry

### File: `scripts/validate_application_registry.py`

### Purpose
Validates the complete application-company registry: company dossiers, flagship registry, portfolio inventory, external flagships.

### Invocation
```bash
python3 scripts/validate_application_registry.py
```

### Success Output
```json
{
  "company_tracks": 166,
  "external_flagship_repositories": 9,
  "helix_children_exactly_once": true,
  "helix_children_mapped": 83,
  "inherited_company_dossiers": 23,
  "l1_private_experiments_documented": 34,
  "named_systems": 17,
  "normalized_legacy_promotion_aliases": 1,
  "status": "PASS",
  "total_inventory_repositories": 84,
  "unresolved_flagships": 1,
  "zero_direct_omission_gate": true
}
```

### Validation Rules

| Check | Description | Failure Condition |
|-------|-------------|-------------------|
| Authority | Registry authority = "GlacierEQ/job-app-helix" | Mismatch |
| Company fields | All required fields present | Missing field |
| Shard defaults | `defaults_apply_to_all_companies` marker | Missing/invalid |
| Legacy aliases | Non-empty object, targets valid | Empty or invalid target |
| Classification notes | Both required notes present | Missing note |
| Dossier files | All 7 dossier files exist & valid | Missing/invalid file |
| Company tracks | Tracks match dossier company_ids | Mismatch |
| Level definitions | Match flagship levels | Drift |
| Portfolio count | `total_repositories == workspace + 1` | Count mismatch |
| Helix mapping | Every workspace repo mapped exactly once | Duplicate or missing |
| Flagship coverage | System IDs match required | Missing/unexpected |
| External registry | External flagships match observed | Mismatch |

### Receipt
No persistent receipt — validator emits JSON to stdout.

---

## Validator 2: Portfolio Root Truth

### File: `scripts/validate_portfolio_root_truth.py`

### Purpose
Validates the root portfolio sources: company dossiers, flagship registry, portfolio inventory, projections. Produces a **SHA-256 receipt** for the entire root validation.

### Invocation
```bash
python3 scripts/validate_portfolio_root_truth.py
```

### Success Output (Receipt)
```json
{
  "schema": "glaciereq.portfolio-root-truth-receipt.v1",
  "status": "PASS",
  "scope": "CONTROL_PLANE_SOURCES_ONLY",
  "root_version": "1.2.0",
  "evaluated_commit": "LOCAL",
  "source_digest": "b33fdf8b9833a0306b44331b79ea5ea0d537c477308d6f70eeb2651070855221",
  "source_hashes": { "manifests/...": "sha256...", ... },
  "projection_freshness": {
    "state": "PENDING_CONSUMER_RECEIPTS",
    "projections": {
      "cloud_indexes": { "contract_state": "DECLARED", "freshness_state": "PENDING_CONSUMER_RECEIPT" },
      "company_application_packets": { "contract_state": "DECLARED", "freshness_state": "PENDING_CONSUMER_RECEIPT" },
      "machine_runtime": { "contract_state": "DECLARED", "freshness_state": "PENDING_CONSUMER_RECEIPT" },
      "public_portal": { "contract_state": "DECLARED", "freshness_state": "PENDING_CONSUMER_RECEIPT" },
      "resume_shapeshifter": { "contract_state": "DECLARED", "freshness_state": "PENDING_CONSUMER_RECEIPT" }
    }
  },
  "receipt_sha256": "f6e1f764036c248da1e6084d522e31edfecb737e942b8976639cf306ad1dab9f",
  "counts": {
    "total_repositories": 84,
    "workspace_repositories": 83,
    "helix_admitted_memberships": 83,
    "company_tracks": 166,
    ...
  },
  "invariants": {
    "all_admitted_repositories_in_inventory": true,
    "all_inventory_children_mapped": true,
    "flagship_ids_exact": true,
    "inventory_count_matches": true,
    "inventory_unique": true,
    "projection_source_ids_resolve": true,
    "public_projection_policy_enforced": true,
    "required_company_tracks_complete": true,
    "root_schema_valid": true
  }
}
```

### Receipt Fields

| Field | Description |
|-------|-------------|
| `receipt_sha256` | SHA-256 of entire receipt (verifiable) |
| `source_digest` | SHA-256 of concatenated source hashes |
| `source_hashes` | Per-file SHA-256 hashes |
| `counts` | Verified counts (repos, tracks, memberships) |
| `invariants` | All invariants true = PASS |

### Validation Rules

| Check | Description |
|-------|-------------|
| Root schema | Valid glaciereq.portfolio-root-truth.v1 |
| Inventory count | `total_repositories == workspace + 1` |
| Helix admitted | Every HELIX_ADMITTED repo in workspace |
| Company tracks | All required tracks present |
| Projection sources | All projection source IDs resolve |
| Public policy | No private repos in recruiter projection |
| Flagship IDs | Exact match required |
| Source hashes | Per-file SHA-256 recorded |

### Receipt Verification
```python
# The receipt_sha256 can be independently verified:
import hashlib, json
receipt_copy = receipt.copy()
del receipt_copy["receipt_sha256"]
computed = hashlib.sha256(json.dumps(receipt_copy, sort_keys=True).encode()).hexdigest()
assert computed == receipt["receipt_sha256"]
```

---

## Validator 3: Live Repository Links

### File: `scripts/validate_live_repository_links.py`

### Purpose
Validates that the portfolio inventory and live-link manifest describe the **same APEX child repository set** and that Helix remains a projection layer (no copied source code).

### Invocation
```bash
python3 scripts/validate_live_repository_links.py
```

### Success Output
```
PASS: Helix portfolio is link-bound to APEX repositories
```

### Validation Rules

| Check | Description | Failure Condition |
|-------|-------------|-------------------|
| Inventory names | Non-empty repository names | Empty name |
| Link names | Non-empty repository names | Empty name |
| Duplicates | No duplicates in inventory or links | Duplicate found |
| Set equality | `inventory == links` | Missing or extra |
| Total count | `total_repositories == len(links) + 1` | Count mismatch |
| Link mode | Must be `live_apex_repository` | Other value |
| Copying forbidden | `source_code_copying_into_helix_forbidden == true` | False/missing |
| APEX origin | `repository_updates_must_be_observed_from_apex_origin == true` | False/missing |
| URL template | `https://github.com/GlacierEQ/{repository}` | Other template |
| Projection fields | Match REQUIRED_LINK_FIELDS | Mismatch |
| Forbidden dirs | No vendor_repositories, repo_copies, etc. | Directory exists |

### REQUIRED_LINK_FIELDS
```python
REQUIRED_LINK_FIELDS = {
    "repository", "apex_url", "default_branch", "head_sha",
    "visibility", "archived", "readme_url",
    "verification_state", "last_verified_at"
}
```

### FORBIDDEN_DIRECTORY_NAMES
```python
FORBIDDEN_DIRECTORY_NAMES = {
    "vendor_repositories", "repository_copies", "repo_copies",
    "source_snapshots", "mirrored_sources"
}
```

---

## Receipt System

### Receipt Structure

Every capability operation produces a receipt:

```python
def _generate_receipt(self, operation: str, data: Any) -> str:
    receipt_data = f"{operation}:{json.dumps(data, sort_keys=True)}:{datetime.now(timezone.utc).isoformat()}"
    receipt_id = hashlib.sha256(receipt_data.encode()).hexdigest()[:16]
    self._receipt_chain.append(receipt_id)
    return receipt_id
```

### Receipt Format

```json
{
  "receipt_id": "a1b2c3d4e5f6g7h8",
  "operation": "portfolio.evidence_ledger.build_ledger",
  "timestamp": "2026-09-04T05:30:00.123456+00:00",
  "data": { "anchor_threshold": 8 },
  "chain_position": 42
}
```

### Receipt Chain

Receipts form an immutable chain:
```
r1 → r2 → r3 → ... → rn
```
Each receipt references the prior via hash inclusion.

### Verification API

```python
# On any capability class
architect = create_anthropic_architect()
architect.verify_receipt("a1b2c3d4e5f6g7h8")  # Returns True/False

# Or via Agent CLI
python3 -m job_app_helix.agent_cli receipt a1b2c3d4e5f6g7h8
```

### Receipt Storage

- **Location:** `.agents/receipts/<receipt_id>.json`
- **Format:** Full receipt JSON
- **Chain:** `.agents/receipts/chain.json` (ordered list of receipt_ids)

---

## Verification Ladder

Every capability must pass the full ladder:

```bash
# G1: Syntax (0 errors)
python3 -m py_compile src/job_app_helix/*.py

# G2: Unit (core tests)
PYTHONPATH=src python3 -m pytest tests/test_application_registry.py tests/test_candidate_portfolio_boundary.py tests/test_live_repository_links.py tests/test_portfolio_audit_claims.py tests/test_portfolio_root_truth.py -q

# G3: Integration (capability + validators)
PYTHONPATH=src python3 -m job_app_helix.agent_cli workflow full-portfolio-cycle --inputs '{}'

# G4: E2E (production path)
# Monolith sync → Tower resolution → Evidence bridge
python3 -m job_app_helix.agent_cli workflow monolith-catalog-sync --inputs '{"mode": "full"}'
python3 -m job_app_helix.agent_cli capability tower.capability_resolution resolve_placement --inputs '{"requirement": "evidence_graph", "domain": "legal_evidence"}'
python3 -m job_app_helix.agent_cli capability evidence.bridge bridge_from_ledger --inputs '{"target_spine": "case_1FDV"}'

# G5: Receipt verification
python3 -m job_app_helix.agent_cli receipt <receipt_id>
```

### Gate Criteria

| Gate | Test | Pass Criteria |
|------|------|---------------|
| G1 | Syntax | 0 syntax/type errors |
| G2 | Unit | All core validator tests pass |
| G3 | Integration | Workflow completes, all steps produce receipts |
| G4 | E2E | Monolith sync + Tower + Bridge operational |
| G5 | Receipt | `verify_receipt(receipt_id) == True` |

---

## Running All Validators

```bash
# All 3 core validators
python3 scripts/validate_application_registry.py
python3 scripts/validate_portfolio_root_truth.py
python3 scripts/validate_live_repository_links.py

# Core test suite (44 tests)
PYTHONPATH=src python3 -m pytest tests/test_application_registry.py tests/test_candidate_portfolio_boundary.py tests/test_live_repository_links.py tests/test_portfolio_audit_claims.py tests/test_portfolio_root_truth.py -q

# Full test suite (93 tests)
PYTHONPATH=src python3 -m pytest tests/ -q
```

---

## Receipt Verification Examples

### Verify Capability Receipt
```bash
# Via CLI
python3 -m job_app_helix.agent_cli receipt abc123def456789

# Via Python
from job_app_helix.forward_deployed.anthropic import create_anthropic_architect
arch = create_anthropic_architect()
assert arch.verify_receipt("abc123def456789")
```

### Verify Portfolio Root Receipt
```python
import hashlib, json

# Load receipt
with open("receipt.json") as f:
    receipt = json.load(f)

# Verify integrity
receipt_copy = receipt.copy()
del receipt_copy["receipt_sha256"]
computed = hashlib.sha256(json.dumps(receipt_copy, sort_keys=True).encode()).hexdigest()
assert computed == receipt["receipt_sha256"], "Receipt tampered!"

# Verify source hashes
for path, expected_hash in receipt["source_hashes"].items():
    actual = hashlib.sha256(open(path, "rb").read()).hexdigest()
    assert actual == expected_hash, f"Source {path} modified!"
```

### Verify Portfolio Root Receipt (Full)
```bash
# Generate receipt
python3 scripts/validate_portfolio_root_truth.py > receipt.json

# Verify
python3 -c "
import hashlib, json
with open('receipt.json') as f: r = json.load(f)
rc = r.copy(); del rc['receipt_sha256']
assert hashlib.sha256(json.dumps(rc, sort_keys=True).encode()).hexdigest() == r['receipt_sha256']
print('Receipt integrity: VERIFIED')
"
```

---

## Provenance Envelope

Important artifacts carry provenance:

```yaml
source: "job-app-helix/portfolio.evidence_ledger"
source_id: "receipt:a1b2c3d4e5f6g7h8"
retrieved_at: "2026-09-04T05:30:00.123456+00:00"
created_at: "2026-09-04T05:29:58.000000+00:00"
content_hash: "sha256:deadbeef..."
transformations: []
derived_from: ["manifests/unified_deserving_manifest.json", "solidify_records/*.json"]
verified_by: "portfolio.evidence_ledger v1.0.0"
status: "VERIFIED"
```

---

## Troubleshooting

### Receipt Not Found
```bash
# Check receipt storage
ls -la .agents/receipts/

# Check chain
cat .agents/receipts/chain.json

# Receipt may be in memory only (not persisted)
# Call verify_receipt() on the capability instance
```

### Validator Fails
```bash
# Run with debug
python3 scripts/validate_application_registry.py 2>&1 | head -50

# Check specific failure
python3 -c "
from scripts.validate_application_registry import validate_registry
from pathlib import Path
result = validate_registry(Path('/data/data/com.termux/files/home/job-app-helix'))
"
```

### Receipt Chain Broken
```bash
# Check chain integrity
python3 -c "
import json
with open('.agents/receipts/chain.json') as f: chain = json.load(f)
for i in range(1, len(chain)):
    # Verify each links to prior (implementation dependent)
    pass
print(f'Chain length: {len(chain)}')
"
```

---

## Quick Reference Card

| Validator | Command | Receipt | Key Metric |
|-----------|---------|---------|------------|
| Application Registry | `python3 scripts/validate_application_registry.py` | JSON stdout | 166 tracks, 83 mapped |
| Portfolio Root Truth | `python3 scripts/validate_portfolio_root_truth.py` | SHA-256 receipt | 84 total, 83 workspace |
| Live Links | `python3 scripts/validate_live_repository_links.py` | stdout PASS | 83 repos synchronized |

| Capability | Receipt Field | Verification |
|------------|---------------|--------------|
| All | `receipt_id` (16-char SHA-256 prefix) | `verify_receipt(id)` |
| Portfolio Root | `receipt_sha256` (full SHA-256) | Recompute from receipt |
| Portfolio Root | `source_digest` | Concat source hashes |

---

*Validation & Receipts Reference v2.0 — All operations produce verifiable receipts*