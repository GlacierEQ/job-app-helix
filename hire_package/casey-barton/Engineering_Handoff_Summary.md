# Handoff — GitHub Mastermind session (2026-08-22)

**To resume in a new chat, paste this:**

> Read `/workspace/HANDOFF.md` and pick up at the "Awaiting your yes" section.

`CLAUDE.md` and the memory index load automatically. This file carries the rest.

---

## 1. Awaiting your explicit yes — nothing below has been touched

These are queued, scoped, and measured. They were **not** executed because each one
either changes security posture or touches a protected repo class.

### 1a. Dependabot fork cleanup — 588 PRs across 269 forks

```
844 Dependabot PRs total
  ├─ 588 in 269 forks     ← candidate for closure
  ├─ 256 in  62 own repos ← needs real triage, NOT bulk
  └─   0 in legal-pattern repos
fork PR idle: median 99 days, oldest 380
top forks: uv (24), mem0 (19), e2b-cookbook__public_fork_archive (17),
           openai-node (16), MemicOS (14), core (11)
```

**Correction to carry forward:** an earlier figure of "947" in conversation was *all* fork
PRs from *all* bots, not Dependabot. The Dependabot number is 588.

Two separable actions:

```bash
cd /workspace

# (i) close the 588 — reversible, in scope under "full PR triage"
uv run --env-file .env --with requests .claude/skills/github-ops/bulk.py \
  --kind pr --from github/prs.json --author 'dependabot[bot]' --match '.' \
  --fork-only --close --apply --max-writes 200      # run in 3 batches

# (ii) stop them regrowing — NOT reversible in bulk, needs the yes
#      DELETE /repos/{owner}/{repo}/automated-security-fixes  on 269 repos
```

(i) is safe: a security upgrade merged into your fork of someone else's project reaches
nobody. (ii) is the part that needs a decision — it turns off security automation on 269
repos, and re-enabling means knowing exactly which ones you changed.

### 1b. `Legal-AI_Project` — 21 Snyk PRs held back

It is a fork, so it met the `--fork-only` criteria, but the name is legal-adjacent so it
was excluded from the sweep by hand. Say yes or no.

### 1c. Re-enable the APEX daily audit

`apex-control-plane/.github/workflows/daily-audit.yml` is `disabled_manually`. **Merge
PR #63 first, then re-enable** — the fix and the anti-spam guard are both in that PR.

---

## 2. Done this session

| Item | Result |
|---|---|
| 99 mentat onboarding issues | closed |
| 8 stale APEX P0 replay issues | closed — 0 open `auto-audit` issues remain |
| 259 Snyk fork PRs | closed, 0 failures |
| 12 verified-stale own-repo Snyk PRs | closed, 0 failures |
| **PR #63** `apex-control-plane` | restores deleted `main()` entrypoint + stale-log guard |
| **PR #21** `Pro-apex-fs-commander` | fixes audit SyntaxError |
| **PR #6** `Yin_The_Legal_Visionary` | 14-month-old conflict markers in `requirements.txt`; now resolves to 702 packages |
| **PR #35** `computer-user` | conflict markers disabled 13 tool-policy tests since 2026-08-20 |

**Deliberately left open** (verified live, do not bulk-close): `blackboxapp` #2, #5 ·
`aifiles` #10, #12 · `AIQuickFix` #3 · all 4 Yin PRs.

### The APEX root cause, in one line

Commit `bc057604` (2026-08-11), labelled a *security fix*, silently deleted
`if __name__ == "__main__": main()` from `daily_audit.py`. The script then exited 0 doing
nothing → step green → no log written → nothing committed → the `if: always()` issue step
read the newest file in `audit_logs/` (frozen since 2026-08-10) and re-filed the same dead
P0 every day, #45 through #56. Proof it was accidental: 11 of 12 `main()`-bearing scripts
in that repo still have their guard.

### Still open, not fixable from the repo

`apex-control-plane/.github/workflows/daily_audit.yml` — note the underscore, it is a
*different* workflow from the one PR #63 fixes — fails daily at
`scripts/repo_atlas_enrich.py` with HTTP 502 from the Supabase function
`apex-github-oidc-estate-atlas-enrich`. Server-side.

---

## 3. Branch and merge maintenance — new this session

`branches.py` was added to the `github-ops` skill. Findings:

**Committed conflict markers** (62 search candidates → 3 real):
- `Yin_The_Legal_Visionary/requirements.txt` → PR #6
- `computer-user/tests/test_tool_policy.py` → PR #35
- `azure-mcp/eng/common/.../git-helpers.tests.ps1` → **false positive**, the markers are
  fixture data inside a here-string for a function named `Parse-ConflictedFile`

**Branch debt** — 3,292 non-default branches across 318 own repos, and **26 repos hold
2,319 of them (70%)**:

| repo | extra branches |
|---|---|
| `job-application` | 291 |
| `job-app-helix` | 266 |
| `AutoGPT` | 195 |
| `fileboss-whisperx-processor` | 175 |
| `public-actions-runner-host` | 138 |
| `CopilotKit` | 136 |
| `DeepSeek-Coder` | 110 |
| `mastermind` | 104 |

Full ranking in `github/branch-rank.json`. The 13 legal repos were skipped by the guard.

**Best repo to prove out the merge-maintenance loop: `job-application`.** Highest branch
count, pushed today, zero protected branches, and it is not a fork — so pruning is real
work rather than tidying someone else's project.

Audited already (`github/branch-audit-top2.json`):

| repo | branches | merged (prunable) | active-unmerged | stale |
|---|---|---|---|---|
| `job-application` | 291 | **62** | 229 | 0 |
| `job-app-helix` | 266 | **43** | 223 | 0 |

**105 branches are fully contained in `main` and safe to delete. Not deleted — deletion
is destructive and needs a yes.** Note the zero stale count: nothing here is abandoned
old work, it is a high-volume bot pushing recent branches. So pruning is hygiene, not
recovery, and the real fix is upstream — find what is creating 291 branches and cap it.

```bash
# dry run (prints the 62, deletes nothing)
uv run --env-file .env --with requests .claude/skills/github-ops/branches.py \
  --audit --repo GlacierEQ/job-application --prune
# then, only after you say go:
... --audit --repo GlacierEQ/job-application --prune --apply
```

---

## 4. Which agent should do which job

The rule this session earned: **delegate gathering, never delegate the verdict.** Four
times a pattern match looked conclusive and was wrong on inspection. A cheap model
applying a blanket rule would have closed two live security PRs and buried a 14-month
outage.

| Job | Use | Why |
|---|---|---|
| "Find every repo that has X" | `Explore` | Read-only fan-out, cheap, returns conclusions not file dumps |
| Deciding whether a finding is real | **main thread (Opus 5)** | This is where all four errors would have landed |
| Per-repo mechanical transform at scale | `Workflow` + `model-haiku-4-5`, `isolation: worktree` | Deterministic, parallel, isolated; only when the transform is already proven on one repo |
| Second opinion on a risky call | `model-gpt-5-6-sol` or `model-grok-4-6` | Different failure modes than mine; useful precisely because it is not another Claude |
| Legal drafting / case analysis | `litigator` (new, §5) | See below |
| Reading a web UI, settings pages | `web-browser` | Already carries the browsing playbook |

For the Dependabot job specifically: the *closing* is mechanical and parallelizes fine.
The *settings change* should stay on the main thread — it is 269 irreversible-ish writes
and wants one operator with the whole picture.

---

## 5. The `litigator` agent — and why personas usually don't work

New file: `/workspace/.claude/agents/litigator.md`. Invoke with
`Agent(subagent_type="litigator")`.

**Your diagnosis was right.** Most personas are written as *characterization* — "you are a
brilliant attorney with thirty years of experience, known for your razor-sharp mind." That
is a costume. It changes vocabulary and confidence and nothing else, which is exactly why
it reads as pretending: the output *sounds* more expert without *being* more checked.

What actually moves behavior is constraint, and there are four kinds that work:

1. **Refusals** — a named list of things the agent may not assert. "Never emit a citation
   you have not verified" is load-bearing in a way that "be rigorous" is not.
2. **Output contracts** — the actual skeleton of a motion, a declaration, an exhibit index.
   A form the agent must fill is harder to fake than prose it may write freely.
3. **A verification gate** — every factual claim carries a tag: record-cited, inference,
   argument, or unsupported. Nothing may be untagged.
4. **A visible self-audit** — a required footer counting verified vs. unverified citations,
   naming the weakest link, and listing what it could not finish. This is the anti-pretend
   mechanism: an agent that is bluffing has to either fill the block honestly, which
   exposes the bluff, or fake the block, which is a much more obvious tell than fluent
   prose.

The `litigator` agent is built entirely out of those four. It also does the thing a real
litigator does that a flattering assistant never does: an **"Opposing Counsel's Best
Attack"** section on every substantive output, and an instruction that if the theory
loses, that goes in the first three sentences.

One counterintuitive point worth keeping: the anti-hallucination discipline *is* the
power, not a limitation on it. Fabricated citations are the single most common way AI
legal work blows up, and they draw Rule 11 sanctions. An agent that reliably says
`[AUTHORITY NEEDED — proposition stated, no case located]` is more useful than one that
confidently invents a case, because you can act on a named gap.

It defaults to Hawaii First Circuit Family Court (HRS / HFCR / HRE) and states that
assumption at the top of every analysis. It treats the case repos as read-mostly and will
not bulk-modify them.

**Tuning it:** edit the file directly. The high-leverage sections are §1 (Refusals), §5
(Output contracts — add your actual local forms), and §2 (jurisdiction). If it ever feels
like it is pretending again, the fix is almost always to add a required output, not to add
more adjectives to the role description.

---

## 6. Hard-won operational facts

- **Auth:** `GITHUB_TOKEN` in `/workspace/.env`. The OAuth connected-account proxy is
  broken for GitHub on this container. Always run from `/workspace` so `--env-file .env`
  resolves.
- **`/rate_limit` lies.** It read `core: 4736/5000` while live response headers said
  `X-RateLimit-Remaining: 0` and returned 403. Trust the headers on a real call.
  `gh.py` now paces writes at 1/sec.
- **Quota is 5,000/hr** and one 259-PR sweep plus surveys exhausted it. Batch large jobs.
- **Search caps at 1,000 results** per query regardless of pagination; code search is
  10 req/min and indexes default branches only.
- **`repo.open_issues_count` includes PRs.** It is not an issue count.
- **Never quote a raw count.** Split fork vs. own and bot vs. human first. Raw open PRs
  were 1,673; the real human backlog was 439.
- Closing a PR requires `PATCH /repos/{o}/{r}/pulls/{n}`; `state_reason` is issue-only.
- `git config` had a plaintext token in a remote URL. Scrubbed. Push with an
  env-substituted URL instead.

## 7. Files

```
.claude/skills/github-ops/     survey · triage · prs · bulk · branches · digest · gh
.claude/agents/litigator.md    the legal agent
github/                        all reports, backups, and JSON state
  ├─ branch-rank.json          3,292 branches ranked by repo
  ├─ conflicts.json            conflict scan, bucketed
  ├─ prs.json                  full PR corpus — bulk.py reads this
  └─ *-backup.json             every bulk operation's undo record
```

## 8. Remaining backlog

1. Dependabot cleanup — §1a, needs yes
2. 65 `[APEX JOB]` records misusing the issue tracker, all in
   `GlacierEQ/public-actions-runner-host` — these are machine job records, not issues;
   they want a database or artifacts, not `--close`
3. Prune merged branches, starting with `job-application` — §3
4. Merge PR #63, then re-enable the audit workflow — §1c
