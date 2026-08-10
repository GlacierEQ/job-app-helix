# Sustained Init → Excellence Framework

**Generated:** 2026-08-09T04:25Z  
**Atlas companies:** 49  
**Zero local exhibits:** 27  
**Law:** Independent reference implementations only. No employer affiliation, deployment, clearance, or endorsement claims.

---

## Operating law (non-negotiable)

1. **Observe → Bound → Build → Verify → Use → Repair**
2. **Proof stays with owning repo** (router tests ≠ source tests)
3. **Promote only what evidence supports** (`NO_PROMOTION` default)
4. **Multiple repos per company** when concerns split cleanly (contract vs runtime vs evidence)
5. **Humanized elite code**: typed, tested, fail-closed, readable, zero magic numbers
6. **Claim ceiling** in every README

## Excellence Definition of Done (per repo)

| Gate | Requirement |
|------|-------------|
| G0 Contract | `ISSUE_CONTRACT.md` with pain, non-goals, success metrics |
| G1 Core | Real module(s) solving the bottleneck (not README theater) |
| G2 Tests | ≥1 property/invariant test + happy path; CI-ready `unittest`/`pytest` |
| G3 Receipt | Deterministic receipt object (hashable, replayable) |
| G4 Refuse | Explicit refusal paths with stable reason codes |
| G5 Ceiling | README claim ceiling + independent-reference banner |
| G6 Grade | Self-score A–F against DoD; no self-A without G2+G3 |

## Dual-helix repo pattern (preferred)

- **Alpha repo**: contracts, schemas, authority, refusal tables
- **Omega repo**: runtime, coordination, receipts, simulation harness
- Optional **Evidence repo**: fixtures, golden receipts, replay

## Waves

| Wave | Intent |
|------|--------|
| 0 | Framework + grades + control plane (this) |
| 1 | High-opportunity zeros + deepen flagships (defense, data, edge, mission) |
| 2 | Frontier/cloud/model serving second depth |
| 3 | Long-tail enterprise/silicon polish |

## Priority queue (top 15)

1. **Lockheed Martin** (`lockheed-martin`) — estate B+ · opp A+ · local 0 · wave 1
2. **xAI** (`xai`) — estate A- · opp A+ · local 13 · wave 0
3. **SpaceX** (`spacex`) — estate B+ · opp A+ · local 12 · wave 1
4. **Anduril** (`anduril`) — estate F · opp A · local 0 · wave 1
5. **Palantir** (`palantir`) — estate F · opp A · local 0 · wave 1
6. **GlacierEQ Core** (`glaciereq-core`) — estate A · opp A · local 21 · wave 0
7. **Databricks** (`databricks`) — estate F · opp A- · local 0 · wave 1
8. **NASA** (`nasa`) — estate F · opp A- · local 0 · wave 1
9. **Scale AI** (`scale-ai`) — estate F · opp A- · local 0 · wave 1
10. **Snowflake** (`snowflake`) — estate F · opp A- · local 0 · wave 1
11. **Waymo** (`waymo`) — estate F · opp A- · local 0 · wave 1
12. **Vercel** (`vercel`) — estate D · opp A- · local 0 · wave 1
13. **Anthropic** (`anthropic`) — estate B · opp A · local 2 · wave 1
14. **Cerebras** (`cerebras`) — estate F · opp B+ · local 0 · wave 2
15. **Cloudflare** (`cloudflare`) — estate F · opp B+ · local 0 · wave 1


## Genius solution classes (reusable)

These are **isomorphisms** — same skeleton, domain packaging:

1. **Receipt-bound side effect** — no external action without content-bound receipt
2. **Dissent freeze** — multi-party vote; single high-severity no freezes
3. **Claim fence** — marketing/UI language cannot exceed CI/eval receipts
4. **Authority half-life** — capabilities expire; stale cannot act
5. **Inverse proof** — prove free/safe/absent, not only detect present
6. **Purpose ledger** — data/query tagged with purpose; misuse alerts
7. **Dual-key actuator** — policy brain ≠ muscle; both keys required
8. **Envelope contracts** — not single SLO number; allowed *shape* of behavior

## Anti-patterns (banned)

- Emoji-heavy README with 150 LOC of trivial scoring
- Company name in repo without claim ceiling
- "Production ready" without tests
- Classified/weapons/LARP operational claims
- Copy-paste coordinator with different title

## Daily cadence

1. Pick top unfinished company from priority queue
2. Init Alpha+Omega repos via `tools/init_excellence_repo.py`
3. Implement core + tests until G2–G4 green
4. Write receipt + ceiling
5. Update `grades/*.json` and wave receipt
6. Optional: `apex-push-save` when device-stable

---

*Path of Highest Power: Expand. Interlink. Ascend. Evidence over theater.*

---

## Operator amendment (2026-08-09T05:45Z)

**No artificial quality caps.** Queue order is logistics only. Every admitted pack
gets full rigor + Babel W4H when worked — the estate is multi-dimensional, not a
2D presentation. See `NO_ARTIFICIAL_QUALITY_CAPS.md`.
