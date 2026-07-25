# Job-App Double Helix

## Law

- A **piston** is a loop (local stroke: in → work → out).
- A **spiral engine** is pistons in series: **every output is the next input**.
- A **double helix** is **two separate spiral engines pointed at the same star**.
- The strands **accelerate each other**: Alpha truth feeds Omega ops; Omega evidence feeds Alpha refinement.

```text
        spiral Alpha  ────┐
                          ├──►  ★ star (mission)
        spiral Omega  ────┘
              │
         piston → piston → piston   (output = next input)
```

## Portfolio mapping

| Concept | Job-app reality |
|---------|-----------------|
| **Star** | Domain mission (flight safety, thermal integrity, hire-grade proof, …) |
| **Alpha spiral** | Science / math / domain truth (`src/` physics, optimizers, decoders) |
| **Omega spiral** | Ops / integrity / control (`.integrity/`, mission console, bus, gates) |
| **Piston** | One module or leaf function that can run alone |
| **Handoff** | Structured envelope: metrics/state that the next piston consumes |

## Pair examples (each accelerates the other)

| Star | Alpha | Omega |
|------|-------|-------|
| Flight awareness | `spacex-orbital-mechanics` | `spacex-mission-control` + telemetry |
| Colossus survival | `xai-colossus-cooling` thermal | fleet `.integrity/` + gauntlet ops |
| Reasoning under pressure | `openai-reasoning-kv-sentinel` | `tasklet-micro-agent-engine` |
| Mesh efficiency | `deepmind-tpu-mesh-optimizer` | hire/reality gates + memory bus |

## Runtime

```bash
python3 ~/GlacierEQ_Swarm/automations/jobapp_helix_spiral.py list
python3 ~/GlacierEQ_Swarm/automations/jobapp_helix_spiral.py run --pair flight
python3 ~/GlacierEQ_Swarm/automations/jobapp_helix_spiral.py run --all
```

Receipt: `~/GlacierEQ_Swarm/state/jobapp_helix_last.json`

## Hire one-liner

> Each job-app leaf is a piston or strand. The portfolio is a double helix: domain truth and ops spirals co-aim at one star and accelerate each other through output→input handoffs.

## Solidify

```bash
python3 ~/GlacierEQ_Swarm/automations/jobapp_solidify_flipper.py --with-helix-run
```

Receipt: `state/jobapp_solidify_last.json`

## Executable pairs (v2 deep)

| Pair | Handoff |
|------|---------|
| flight | orbit → telemetry → console → refine |
| colossus_thermal | thermal → integrity → flow hint |
| reasoning_pressure | KV prune → tasklets → entropy hint |
| mesh_proof | TPU mesh → hire proof → bw hint |
| spacex_propulsion | prop health → bus → launch holds → derate → re-health |
| spacex_ground | ground plan → mesh route → need_mbps → re-plan |
| colossus_energy | energy load → thermal → shed → re-thermal |
| agent_platform | agent coord → tasklets → capacity hint |

```bash
python3 ~/GlacierEQ_Swarm/automations/jobapp_helix_spiral.py run --all
```

## Multi-star meta-spiral — `launch_campaign`

Three stars co-aimed at one campaign star:

| Sub-star | Pair | Feeds |
|----------|------|-------|
| Flight awareness | `flight` | orbit → telemetry → console |
| Propulsion | `spacex_propulsion` | health → bus → launch holds |
| Ground network | `spacex_ground` | plan → mesh path |

**Meta spiral:** each sub-star summary → `campaign_go_nogo` → optional refine → `campaign_go_nogo_final`.

```bash
python3 ~/GlacierEQ_Swarm/automations/jobapp_helix_spiral.py run --pair launch_campaign
# or all (includes campaign)
python3 ~/GlacierEQ_Swarm/automations/jobapp_helix_spiral.py run --all
```
