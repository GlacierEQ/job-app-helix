# Legal hire stack — official platform (HX-28)

**Track:** GlacierEQ Job-App Helix hire spine  
**Related:** HX-27 private overlay (`GlacierEQ/job_app_helix`) — merged [PR #1](https://github.com/GlacierEQ/job_app_helix/pull/1)  
**Operator vault:** `GlacierEQ/mega-skills` → `legal/`  
**Last updated:** 2026-11-17

This document is the **public** authority for what is officially part of the legal hire stack. AGPL skill bodies stay in private repos; this repo carries links, invariants, and benchmark placeholders only.

## Official layers

| Layer | Repository | What ships |
| --- | --- | --- |
| Public proof | `job-app-helix` (this repo) | Upstream URLs, `OFFICIAL_SKILLS.md`, benchmark receipts, redacted demos |
| Private overlay | `job_app_helix` | Vendored skills, `.agents/skills/`, Helix composites, LegalBench runner stub |
| Operator vault | `mega-skills` | Pinned `legal/` mirror + `INDEX.md` SHAs |

## Official skill set (Tier A legal hire)

### Upstream (install with `npx skills add` or vendor scripts)

| ID | Upstream | License | Hire use |
| --- | --- | --- | --- |
| `career-ops` | [career-ops-hq/career-ops](https://github.com/career-ops-hq/career-ops) @ `8831748b` | MIT | Search, score, tailor, tracker |
| `claude-legal-skill` | [evolsb/claude-legal-skill](https://github.com/evolsb/claude-legal-skill) @ `bca0d2e9` | MIT | Contract review |
| `legal-redline-tools` | [evolsb/legal-redline-tools](https://github.com/evolsb/legal-redline-tools) @ `1dbc70dd` | MIT | DOCX/PDF redlines |
| `lawve-irac` | lawve `irac-prompt-builder-stephane-boghossian` | AGPL-3.0 | JD → IRAC brief (private vend only) |
| `lawve-tech-contract` | lawve `tech-contract-review-parth-desai` | AGPL-3.0 | Tech MSA/DPA review |
| `lawve-eu-ai-act` | lawve `eu-ai-act-tanaji-hemant-naik` | AGPL (per skill) | AI Act narrative |
| `lawve-expertise-to-skill` | lawve `law-expertise-to-skill-adrian-lerer` | AGPL-3.0 | Custom review standards → skills |
| `lawve-privacy-generator` | lawve `privacy-policy-generator-malik-taiar` | AGPL-3.0 | CNIL-grounded policy drafting |
| `mcp-eu-compliance` | [matematicsolutions/mcp-eu-compliance](https://github.com/matematicsolutions/mcp-eu-compliance) | MIT | EUR-Lex citations (lean MCP, not full vend) |
| `legalbench` | [HazyResearch/legalbench](https://github.com/HazyResearch/legalbench) | Per-task | Five-task hire receipt |

Lawve catalog pin: [awesome-legal-skills](https://github.com/lawve-ai/awesome-legal-skills) @ `f9f28cdccbeb98bbdde010042ea9f525ca427c72`.

### Helix composites (private UNLICENSED — names only on public site)

| Composite | Purpose |
| --- | --- |
| `helix-legal-ops-apply` | Search → score → IRAC tailor → evidence → human apply; enforces `sent_state_requires_external_receipt` |
| `helix-contract-demo` | Redacted portfolio contract review via MIT upstream skills |
| `helix-compliance-talk-track` | Interview briefs grounded on `mcp-eu-compliance` |

Canonical paths: `job_app_helix/skills/{hire,legal}/` and `.agents/skills/`.

## Helix invariants (official)

- `sent_state_requires_external_receipt: true` — no `SENT` without a receipt object.
- `allow_public_evidence_promotion: false` for application secrets and full tailor logs.
- No mass unattended apply (no AIHawk-style bots).
- Public repo must not contain AGPL lawve skill text or private application evidence.

## Dynamic install (skills + plugins)

Official install path uses [vercel-labs/skills](https://github.com/vercel-labs/skills):

```bash
npx skills add career-ops-hq/career-ops -a cursor
npx skills add evolsb/claude-legal-skill -a cursor
npx skills add lawve-ai/awesome-legal-skills --skill irac-prompt-builder-stephane-boghossian -a cursor
# …see OFFICIAL_SKILLS.md for the full five lawve picks
```

Cursor marketplace **plugins** extend MCP and governance; keep EU compliance MCP install lean per private `connectors/mcp-eu-compliance/README.md` in `job_app_helix`.

## Benchmarks

Public receipts live under `benchmarks/`. Until a scored run is promoted from the private runner, use the schema placeholder:

- `benchmarks/legalbench-subset.placeholder.json`

Wire `call_model()` in private `scripts/run_legalbench_subset.py` before publishing real scores.

## Do not officialize

- feder-cr Jobs_Applier AI mass-apply patterns
- Whole `awesome-legal-skills` repo as one blob
- OpenContracts platform merge into Helix core
- `privacy-policy-stephane-boghossian` (replaced by malik-taiar generator)

## Cross-links

- [OFFICIAL_SKILLS.md](../OFFICIAL_SKILLS.md) — machine-readable manifest
- [skills/README.md](../skills/README.md) — short pointer table
- [job-search-agent-skills-playbook-summary.md](./job-search-agent-skills-playbook-summary.md) — converge pattern
- [legal-agentic-job-search-resources.md](./legal-agentic-job-search-resources.md) — resource tier list
