# GitHub Distillation — GlacierEQ estate (2026-10-07)

Method: full GraphQL estate census (14 pages, 1,386 repos) + shallow clones of the
5 flagship originals with file/LOC/test-function counts. All numbers below are
measured, not estimated. LOC counts include test code; flagged where relevant.

## Estate level (verified live 2026-10-07)

- **1,386 repositories** under GlacierEQ — 686 public, 700 private.
  (Kit said 1,313; live count is 1,386 — estate grew.)
- Original work vs forks: the big-size leaders (airbyte, authentik, CopilotKit,
  affine, wordpress) are **forks** — never claim them. The flagships below are
  all `fork=false`, authored in-house, pushed within the last 48h.

## Flagship systems (all original, all active)

| repo | commits | Python files | Python LOC | test files | test fns | other |
|---|---|---|---|---|---|---|
| job-app-helix | 20 | 337 | ~81,000 | 166 | **989** | public site deployed |
| apex-control-plane | 771 | 224 | ~44,600 | 103 | **897** | +18 TS, PLpgSQL 464KB |
| AKOS | 706 | 126 | ~22,200 | 49 | 360 | "Live job application" |
| colossus-gateway | 232 | 36 | ~5,700 | 9 | 66 | **127 TypeScript files** — universal MCP bridge |
| Forward-Deployed-Agentic-Powerhouse | 48 | 50 | ~6,700 | 20 | 97 | FDE-pattern repo, created 2026-09-20 |

- **Combined: ~160,000 lines of Python, 2,409 test functions, 347 test files**
  across the five flagships.
- apex-control-plane: 771 commits since 2026-05-27 — the highest-velocity repo.
  "APEX worker registry + capacity dispatch."
- AKOS: 706 commits — "identity, sessions, governance, swarm bridge."
- glaciereq-memory-gateway: live on Render (Supabase L1 + Supermemory/Mem0 L2)
  — the estate's shared memory MCP gateway, in production use.

## Kit-number verification

- **62/62** — VERIFIED in-repo: Agent Coordinator behavioral suite,
  "62/62 deterministic tests" (job-app-helix test + receipt JSON).
- **961-test control plane** — live count is **989** test functions in
  job-app-helix (kit froze at 961; estate grew). Recommend updating to 989.
- **65 MCP connectors** — his kit number; not independently re-counted here.
- **1,313-repo platform** — live count **1,386**. Recommend updating to 1,386
  (or "1,300+").

## Suggested resume bullets (awaiting his pick)

- "Own a 1,386-repository engineering estate (686 public); five flagship
  systems total ~160K lines of Python with 2,400+ test functions."
- "job-app-helix: 81K-line Python campaign engine, 989 test functions —
  immutable evidence models, fail-closed GO/NO-GO decisions, JSON proof receipts."
- "apex-control-plane: 45K-line worker registry + capacity dispatch, 897 test
  functions, 771 commits — typed state transitions, approval gates."
- "colossus-gateway: universal MCP bridge (TypeScript) for Colossus-class
  multi-agent orchestration."
- "Operate a production memory gateway (MCP): Supabase + Supermemory/Mem0
  layered memory, live serving the estate."

## Honesty boundaries

- Never cite fork repos (airbyte, authentik, CopilotKit, affine, etc.).
- Stars are ~0 across the estate — the story is volume + tests + architecture,
  not popularity. Don't imply community adoption.
- LOC includes test code; the test-function counts are the cleaner proof metric.
