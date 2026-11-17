# Official legal agentic job search (GlacierEQ Helix)

**Public surface.** Full vendored skills live in private `GlacierEQ/job_app_helix` (merged). This repo documents the portfolio-safe manifest, benchmarks, and evidence workflow.

## Three-repo system

| Repo | Role |
| --- | --- |
| **job-app-helix** (this) | Public control plane, Vercel site, docs, benchmark receipts |
| **job_app_helix** | Private overlay: `.agents/skills/`, career/legal vendored skills, Helix composites |
| **mega-skills** | Operator vault: `legal/INDEX.md` pins + career rubric |

## Agent skills layout

- **Standard:** [Agent Skills](https://agentskills.io) via `.agents/skills/` and `skills/` (see `OFFICIAL_SKILLS.md`).
- **Install upstream:** `npx skills add` (vercel-labs/skills) for career-ops, claude-legal-skill; lawve picks stay private (AGPL).

## Evidence-bound apply workflow

1. **Search & score** (career-ops pattern, master CV).
2. **Tailor** with IRAC + legal skills (`helix-legal-ops-apply` composite in private overlay).
3. **Evidence** in private `applications/`; public gets redacted proofs only.
4. **Apply** human-submits; `sent_state_requires_external_receipt` before SENT.

See `docs/job-search-agent-skills-playbook-summary.md` and private overlay `skills/hire/helix-legal-ops-apply/SKILL.md`.

## Benchmarks

Run subset per `benchmarks/README.md`; publish scores JSON only (no proprietary prompts).

## MCP (lean)

EU compliance grounding: `matematicsolutions/mcp-eu-compliance` (optional, documented in private `connectors/`). Colab/OCI for heavy compute — operator Mac config, not committed here.
