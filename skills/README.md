# Agent skills (public pointers)

Full vendored skills live in the private overlay **`GlacierEQ/job_app_helix`** and operator vault **`GlacierEQ/mega-skills`**. This public repo publishes **upstream links and redacted outputs only** — not AGPL lawve skill text.

## Upstream (Tier A)

| Resource | URL | Use |
| --- | --- | --- |
| career-ops | https://github.com/career-ops-hq/career-ops | Search, score, tailor (MIT) |
| claude-legal-skill | https://github.com/evolsb/claude-legal-skill | Contract review (MIT) |
| legal-redline-tools | https://github.com/evolsb/legal-redline-tools | DOCX/PDF redlines (MIT) |
| awesome-legal-skills | https://github.com/lawve-ai/awesome-legal-skills | IRAC, EU AI Act, tech contract review (per-skill AGPL) |
| mcp-eu-compliance | https://github.com/matematicsolutions/mcp-eu-compliance | EUR-Lex MCP (MIT) |
| LegalBench | https://github.com/HazyResearch/legalbench | Benchmark receipts |
| skills.sh / vercel-labs/skills | https://github.com/vercel-labs/skills | `npx skills add` standard |

## Helix composites (private)

| Skill | Purpose |
| --- | --- |
| `helix-legal-ops-apply` | Evidence-bound apply FSM + IRAC tailor |
| `helix-contract-demo` | Redacted portfolio contract review |
| `helix-compliance-talk-track` | MCP-grounded interview briefs |

Install with `npx skills add` for upstream packages, or sync from private `job_app_helix/skills/` and `.agents/skills/`.
