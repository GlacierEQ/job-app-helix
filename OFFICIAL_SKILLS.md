# Official agent skills manifest (public)

Vendored skill **bodies** are in private `GlacierEQ/job_app_helix`. This file is the public registry for portfolio and Cursor discovery.

## Composite (Helix-native, private install)

| Skill | Purpose |
| --- | --- |
| `helix-legal-ops-apply` | Search → score → tailor → evidence → human apply |
| `helix-contract-demo` | Redacted contract review portfolio artifact |
| `helix-compliance-talk-track` | EU AI Act / GDPR interview talking points |

## Upstream (install via `npx skills add`)

- `career-ops-hq/career-ops`
- `evolsb/claude-legal-skill`
- lawve-ai picks (5 skills, see private `skills/legal/INDEX.md`)

## Paths

- Project: `.agents/skills/<name>/` and `skills/README.md`
- Personal: `~/.cursor/skills/` or `~/.agents/skills/`

## Licenses

Each vendored folder includes `UPSTREAM.md` + LICENSE in private overlay. AGPL lawve skills are **not** republished in this public repo.
