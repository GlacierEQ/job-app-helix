# BrainSync path portability

## Problem

BrainSync embeds absolute local paths (`/Users/<you>/...`) in generated
artifacts (`memory.jsonl`, `index.json`, `project.json`, shadows, mirrors).
Committing them reduces portability and can leak environment details.

## `index.json` / skill-entry consumers

`.brainsync/index.json` → `latestEntries` is a **capped preview** (not a full
catalog). Multiple `memory.jsonl` rows can share one title while carrying
**distinct** content (e.g. Expert Skills for `config` / `project` / `python` /
`typescript`). Title-only dedupe or window rotation can omit domain rows from
the preview without deleting them from memory.

| Authoritative | Non-authoritative |
|---------------|-------------------|
| `.brainsync/memory.jsonl` (id + content) | `index.json` `latestEntries` title counts |
| `index.json` `skillRules[]` (domain + skillPath + id) | Same-title row counts in the preview |
| `.agent/skills/auto/*/SKILL.md` | Ordering of preview stubs |
| `.agent/skills/auto/skills-manifest.json` | |

After BrainSync sync or kind-normalize, rebuild so distinct skill rows stay pinned:

```bash
# Kind normalize + rebuild index (pins skills into latestEntries + skillRules)
python3 helix/automations/brainsync_kind_normalize.py apply --skip-context

# Audit skill domain survival (does not require title-duplicate preview rows)
python3 helix/automations/brainsync_index_skills.py audit
python3 helix/automations/brainsync_index_skills.py audit --strict-index

# Pin distinct expert-skill rows into latestEntries after a BrainSync sync
python3 helix/automations/brainsync_index_skills.py repair

# Machine-readable catalog for tooling
python3 helix/automations/brainsync_index_skills.py catalog

# Contract proofs
python3 helix/proofs/proof_brainsync_skill_index.py
python3 helix/proofs/proof_brainsync_kind_normalize.py
```

## Policy

| Keep tracked | Leave local (gitignored) |
|--------------|---------------------------|
| `.brainsync/ip_rules.md` | `.brainsync/memory.jsonl`, `index.json`, `project.json`, … |
| Hand-authored project docs | `AGENTS.md` / `GEMINI.md` / `CLAUDE.md` mirrors |
| | `.brainsync/backups/`, `shadows/`, `sync-state.json` |
| | `.mcp.json` (absolute MCP binary + secret env paths) |

## Commands

Canonical tool: `helix/automations/brainsync_path_sanitize.py`

```bash
# Scrub absolute paths in local generated files
python3 helix/automations/brainsync_path_sanitize.py scrub

# Fail if tracked / staged BrainSync files still leak absolute paths
python3 helix/automations/brainsync_path_sanitize.py check
python3 helix/automations/brainsync_path_sanitize.py check --staged

# Enable repo pre-commit hook (once per clone)
git config core.hooksPath .githooks
```

## Untrack after policy change

```bash
git rm -r --cached --ignore-unmatch \
  .brainsync/memory.jsonl .brainsync/index.json .brainsync/project.json \
  .brainsync/generated-context.md .brainsync/sync-state.json \
  .brainsync/shared-context.json .brainsync/.context-key \
  .brainsync/rules .brainsync/shadows .brainsync/backups \
  .brainsync/agent-rules.md \
  AGENTS.md GEMINI.md CLAUDE.md \
  .cursor/active-context.md .cursor/rules/brainsync.mdc \
  .kiro/steering/brainsync.md .windsurf/rules/brainsync.md \
  .agents/rules/brainsyncory.md .mcp.json
```
