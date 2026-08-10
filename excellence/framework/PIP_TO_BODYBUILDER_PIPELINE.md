**Superseding precision:** full lifecycle is `REPO_EXCELLENCE_COMPILER.md` + monolith state machine. Bodybuilder DoD is a **compress of stages 5–10** for thin leaves; never skip identity/lineage/contract for new work.

# Pipsqueak → Bodybuilder Pipeline

**Goal:** Level ~80 thin repos to forward-thinking depth without melting the main session.  
**Law:** Orchestrator = **lean**. Workers = **make-it-heavy** (one leaf at a time).  
**Estate now:** ~16 bodybuilder-ish · ~16 gym · ~75 pipsqueak · ~5 seed (heuristic LOC/tests).

---

## Roles (token discipline)

| Role | Mode | Token job |
|------|------|-----------|
| **You / orchestrator** | Lean | Queue, receipts, promote/fail — **never** load full repos |
| **Scout workers** | Throughput | Read-only inventory JSON (paths, LOC, tests, gaps) |
| **Steel workers** | Make-it-heavy | One repo → bodybuilder DoD; return receipt only |
| **Proof worker** | Make-it-heavy | Run tests/CI; fail-closed gate |
| **Optional library worker** | Lean | Update monolith catalog pointer only |

**Hard rule:** Main chat receives **receipts ≤ ~40 lines**, never full source dumps.

---

## Bodybuilder Definition of Done (DoD)

A leaf is **BODYBUILDER** only when all pass:

| Gate | Requirement |
|------|-------------|
| G0 | `ISSUE_CONTRACT.md` — pain, non-goals, success |
| G1 | Real core (not README theater); refuse paths + reason codes |
| G2 | Tests ≥ **8** methods covering happy + ≥4 refuse/adversarial |
| G3 | Deterministic receipts / digests where side effects exist |
| G4 | `LICENSE` = GlacierEQ Proprietary v1.1 (except Babel MIT) |
| G5 | Claim ceiling / QUALITY honesty |
| G6 | CI workflow (unittest or multi-lang as present) |
| G7 | Babel W4H companion **if** domain physics earns a second language |
| G8 | `make integrity`-class: tests green; no overclaim language |
| G9 | Self-score **B or better** on depth — no self-A without G2+G3 |

**Not bodybuilder:** LOC spam, emoji READMEs, single happy-path test.

---

## Pipeline stages

```text
[0 INDEX] → [1 TRIAGE] → [2 WAVE] → [3 STEEL×N] → [4 PROOF] → [5 RECEIPT] → [6 PROMOTE]
     lean        lean       lean      heavy/worker    heavy         lean           lean
```

### 0 — INDEX (once / weekly)
- Script or scout: emit `excellence/grades/leaf_tier_board.json`
- Fields: `name, loc, tests, tier, has_ci, has_babel, has_license, next_action`
- **Orchestrator reads only the board**, not repos

### 1 — TRIAGE (lean)
- Sort: **company hire leverage × thinness × domain risk**
- Waves of **4–8** leaves (never 80 at once)
- Skip: already bodybuilder; true upstream forks; dead placeholders

### 2 — WAVE packet (lean)
One JSON blob workers get — no chat novel:

```json
{
  "wave_id": "W2026-08-09-a",
  "mode": "make-it-heavy",
  "dod_ref": "PIP_TO_BODYBUILDER_PIPELINE.md#bodybuilder-definition-of-done",
  "license": "GlacierEQ Proprietary v1.1",
  "leaves": ["repo-a", "repo-b", "..."],
  "forbidden": ["affiliation claims", "README-only", "new company logos"]
}
```

### 3 — STEEL workers (parallel, make-it-heavy)
- **1 worker = 1 leaf** (or 1 pack triad max if already multi-repo)
- Spawn with `isolation=worktree` when editing hot trees
- Worker prompt skeleton (paste once, fill leaf name):

```text
MODE: make-it-heavy. ONE REPO ONLY: <name>
DoD: excellence/framework/PIP_TO_BODYBUILDER_PIPELINE.md bodybuilder gates G0–G9.
Read ISSUE_CONTRACT or create it. Deepen core + tests to ≥8. Keep claim ceiling.
Babel second language only if W4H earns it. LICENSE v1.1 if missing.
Return ONLY: receipt JSON {repo, gates{}, tests_before, tests_after, loc_delta, commands_run, residual_risks[]}.
Do not dump source into chat.
```

- Cap concurrent workers to device (e.g. **2–3** on 8GB MBA; **4–6** on stronger box)

### 4 — PROOF worker (make-it-heavy, fail-closed)
- After each steel (or batch of 2): `unittest` / `go test` / `clang` / `node` as applicable
- Exit non-zero → leaf stays **GYM** or **PIP**; no promote

### 5 — RECEIPT (lean)
Append to `excellence/receipts/bodybuilder_wave_<id>.jsonl` one line per leaf:

```json
{"repo":"…","tier_after":"bodybuilder|gym|pip","gates":{"G2":true,…},"tests":12,"pushed":false}
```

### 6 — PROMOTE (lean, batch)
- `git commit` + push only after proof green
- Optional: atlas `record.json` state bump remains REFERENCE_ONLY until separate REPRODUCED path

---

## Token budget model

| Component | Budget |
|-----------|--------|
| Orchestrator turn | **Lean** — board + wave JSON + N receipts |
| Scout | One board file; no prose essays |
| Steel worker | Full context **inside worker only** (make-it-heavy) |
| Proof | Command output tails, not full logs |
| Memory | Dual-write receipt pointers; not full trees |

**Anti-patterns (burn tokens):**
- Main agent reads every repo “to understand”
- Serial deepen of 80 leaves in one chat
- Re-explaining DoD every message (point at this file)
- make-it-heavy on the orchestrator

**Pro-patterns (save tokens):**
- Pointer index / board JSON
- Parallel steel workers
- Receipt-only returns
- Cache: skip leaf if receipt `tier_after=bodybuilder` and hash unchanged

---

## Wave templates (priority)

### Wave A — Flagship adjacency (hire leverage)
Lockheed triad already heavy → **SpaceX quorum pack deepen**, Palantir third, OpenAI/Anthropic/NVIDIA/xAI frontier  
*~8 leaves*

### Wave B — Excellence zeros with Babel companions
Anduril / Vercel / Scale / Groq / Waymo / NASA / data-cloud / Cloudflare  
*~12 leaves — deepen Python + keep multi-lang green*

### Wave C — Estate thin seeds (spacex-*, notion-*, old portfolio motions)
Replace scoring theater with real mechanism or **demote from recruiter surface**  
*Honest incomplete > fake bodybuilder*

### Wave D — Mastermind / Megamind binding
Not LOC inflation — **registry links + integrity gates + one verified mission path**

---

## Automation hooks (minimal)

### Make-it-heavy REALITY wave (zero LLM)

```bash
# refresh board + verify up to 8 pipsqueaks/gym (parallel workers)
python3 ~/GlacierEQ_Swarm/automations/make-heavy-bodybuilder-wave-flipper.py --from-board --limit 8 --workers 3

# explicit wave
python3 ~/GlacierEQ_Swarm/automations/make-heavy-bodybuilder-wave-flipper.py \
  --names waymo-uncertainty-lane-graph,anduril-sensor-health-quorum,nvidia-nan-circuit-breaker

# pure_pointer summary on stdout; full report:
#   ~/GlacierEQ_Swarm/state/make_heavy_bodybuilder_wave_last.json
#   excellence/receipts/bodybuilder_wave_runs.jsonl
```

Steel workers (make-it-heavy *code*) still deepen leaves; this flipper is the **proof lane**.

## Automation hooks (minimal)

```bash
# 1) Board (orchestrator or cron)
python3 excellence/tools/leaf_tier_board.py   # emit grades/leaf_tier_board.json

# 2) Human/orchestrator picks wave of N names

# 3) Workers (manual spawn or workflow):
#    steel worker × N parallel, proof, receipt

# 4) Optional
make -C ~/monolith integrity-check
```

`leaf_tier_board.py` should be **dumb metrics only** (LOC, test count, flags) — no LLM.

---

## make-it-heavy scope (worker only)

Inside a steel worker, make-it-heavy means:
- Full functions, no `TODO` cores
- Refuse matrix + concurrency/property tests where relevant
- Multi-lang companions tested if present
- QUALITY.md honesty preserved (no REPRODUCED inflation)

It does **not** mean rewrite the whole estate in one agent.

---

## Success metrics (estate)

| Metric | Target |
|--------|--------|
| pipsqueak+seed count | ↓ each wave |
| bodybuilder count | ↑ with proof receipts |
| Orchestrator tokens / wave | ≈ constant (receipts only) |
| Overclaim incidents | 0 |

---

## Operator one-liner

> **Lean queue. Heavy leaf. Parallel workers. Receipt or it didn’t happen.**

When ready: pick Wave A list → spawn 2–4 steel workers → proof → push.
