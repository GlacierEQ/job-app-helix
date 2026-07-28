# Job-App Double Helix

## Core law

- A **piston** is one runnable unit: input → work → output.
- A **spiral** feeds one piston’s output into the next piston.
- A **helix** has two strands aimed at the same star:
  - **Alpha:** domain truth, construction, or planning.
  - **Omega:** verification, operational gating, or adversarial checking.
- A **campaign** composes several stars into one final decision.
- A system is done only when its stated pain has a runnable green proof.

```text
Alpha:  truth/build ──► handoff ──► refinement
                         │               ▲
                         ▼               │
Omega:  verify/gate ──► finding ─────────┘
                         │
                         ▼
                     mission star
```

## Public runtime

```bash
python -m helix.public_runtime list
python -m helix.public_runtime demo --scenario nominal
python -m helix.public_runtime demo --scenario recoverable
python -m helix.public_runtime demo --scenario terminal
```

| Star | Alpha | Omega | Refinement |
|---|---|---|---|
| Flight | Circular-orbit truth | Telemetry and mission gate | Restore sequence continuity |
| Propulsion | Health score | Launch hold gate | Derate and rebalance |
| Ground | Capacity plan | Mesh route gate | Add capacity or fail closed |

The launch campaign combines all three final states into one GO/NO-GO receipt.

## Workspace integration

```bash
python helix/automations/jobapp_helix_spiral.py list
python helix/automations/jobapp_helix_spiral.py run --pair launch_campaign
```

That deeper runner imports implementations from the wider workspace. It is an integration mode with external dependencies, not the public portability test.

## Proof receipt

```json
{
  "protocol": "job-app-helix/public-v1",
  "mode": "fixture",
  "initial_decision": "NO-GO",
  "final_decision": "GO",
  "proof_sha256": "..."
}
```

The receipt hash is an integrity address, not a security signature or certification.
