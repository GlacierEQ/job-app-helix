# Job-search agent skills playbook (summary)

Public excerpt for **Job-App Helix** hire spine. Full playbook and store docs live in the Cursor project store.

## Converge pattern

Import **skills + workflows**, not 32k-star auto-apply bots or whole awesome lists.

## Top actions

1. **career-ops** — score 1–5, tailor, tracker (human submit).
2. **claude-legal-skill** + **legal-redline-tools** — contract demo pipeline.
3. **lawve** — five pinned skills (IRAC, tech contract review, EU AI Act, law-expertise-to-skill, privacy policy generator); private only.
4. **LegalBench** — 5-task subset → `benchmarks/legalbench-subset-*.json`.
5. **mcp-eu-compliance** — lean MCP for compliance talk-tracks.

## Helix invariants

- `sent_state_requires_external_receipt: true`
- `allow_public_evidence_promotion: false` for application secrets
- No mass LinkedIn auto-apply

## Do not clone

AIHawk mass apply, entire awesome-legal-skills repo, OpenContracts platform into core.
