# APEX Job-App Architecture — Pillars, Pistons, Helix, Activation

**Status:** Authoritative portfolio map (solidified + helix + highway)  
**Law:** One wheel rolls; four wheels + chassis is the vehicle.

---

## 1. Four Strategic Pillars & Twelve Ring-3 Pistons

Pistons here are **named leaf engines** (repos) under each pillar.  
Each carries domain truth + `.integrity/` + `HELIX_STRAND.md` + optional `mastermind_sidecar.py`.

### Pillar I — Cognitive OS

| # | Piston (repo) | Role |
|---|---------------|------|
| 1 | **AKOS** | Operating law / federation / cognitive kernel |
| 2 | **pro-code** | Vehicle UI / worker mesh / production surface |
| 3 | **token_saver** | Context discipline / pure_pointer / externalization |

### Pillar II — Compute Physics

| # | Piston (repo) | Role |
|---|---------------|------|
| 4 | **xai-colossus-cooling** | Thermal truth `Q=ṁcₚΔT` |
| 5 | **colossus-gateway** | Bridge / control ingress |
| 6 | **nvidia-gpu-health** | GPU health / fleet compute vitals |

### Pillar III — Aerospace Helix

| # | Piston (repo) | Role |
|---|---------------|------|
| 7 | **spacex-thermal-protection** | TPS / aero-thermal domain |
| 8 | **spacex-telemetry** | Bus, rate/gap, bridge spiral |
| 9 | **spacex-autonomy** | Autonomy / closed-loop ops |

### Pillar IV — Reasoners & Safety

| # | Piston (repo) | Role |
|---|---------------|------|
| 10 | **openai-reasoning-kv-sentinel** | Entropy / KV pressure |
| 11 | **deepmind-tpu-mesh-optimizer** | Mesh / ICI step model |
| 12 | **anthropic-safety-monitor** | Safety / governance watch |

**Note:** The classic Mastermind shadow matrix (MICROWAVE, SUPERNOVA, …) is the *execution* piston vocabulary. These twelve are the *portfolio* pistons — the wheels bolted to the hire vehicle.

---

## 2. Double Helix Topology

Two **separate spiral engines** pointed at the same star.

| Strand | This architecture | Helix runner casting |
|--------|-------------------|----------------------|
| **Alpha** | High-speed **production** engine logic (*what gets built*) | Domain truth pistons (math, health, plan) |
| **Omega** | **Adversarial prosecutor** test harness (*how it gets verified*) | Ops / integrity / gate / console / holds |

**Spiral engine:** every piston output is the next input.  
**Mutual acceleration:** Omega findings refine Alpha; Alpha truth loads Omega.

Executable pairs + multi-star **`launch_campaign`**: see `HELIX.md`, `helix_registry.json`.

```bash
python3 ~/job-app/helix/automations/jobapp_helix_spiral.py run --all
python3 ~/job-app/helix/automations/jobapp_helix_spiral.py run --pair launch_campaign
```

---

## 3. Activation Stack (L0 → L3)

| Level | Name | Behavior |
|-------|------|----------|
| **L0** | Local zero-LLM | Flippers, filesystem, integrity watchdogs, highway scan |
| **L1** | MICROWAVE / token_saver | pure_pointer, externalize bodies, ~95% context reduction target |
| **L2** | Swarm Orchestrator VP | 5W1H, spiral compound revolutions, delegation |
| **L3** | Path-of-highest-power | Adaptive matrix → ring pistons / gauntlet when stakes escalate |

---

## 4. Morpheus OS Control Plane & APEX Highway Mesh

| Component | Path / role |
|-----------|-------------|
| **Morpheus** | `mastermind/morpheus/` — consent personalization, observe-first |
| **Sidecars** | `*/mastermind_sidecar.py` — per-node heartbeat (61) |
| **Highway** | `apex_highway.py` — discover sidecars, mesh health, inter-orbit route |
| **Integrity** | `*/.integrity/` — SHA-256 baselines fleet-wide |
| **Mastermind cortex** | `mastermind/.shadow/` — specialist FULLPOWER engines (documented, dual-use framed) |

```bash
python3 ~/job-app/apex_highway.py
```

---

## 5. Vehicle test

| Layer | Count / status |
|-------|----------------|
| Pillar pistons (named 12) | All present on disk |
| Mesh leaves | 61 repos, sidecars, integrity, strands |
| Executable helix pairs | 8 + `launch_campaign` meta-spiral |
| Control plane git | [GlacierEQ/job-app-helix](https://github.com/GlacierEQ/job-app-helix) |

**Innovation posture:** not 12 new laws of physics — **four pillars + chassis** so each wheel becomes a vehicle aimed at real stars (flight, thermal, reasoning, safety).

## 6. Issue Contract Law (non-negotiable)

**DONE ⇔ proof(pain) == green.**

Strand / integrity / helix / highway / push are **not** substitutes.

```bash
python3 ~/job-app/helix/automations/issue_contract_gate.py --write-md
```

Receipt: `~/GlacierEQ_Swarm/state/issue_contract_gate_last.json`
