# Repository Boundaries

## Why two runtimes exist

The repository serves a public reviewer who needs a clean clone-and-run proof and an operator workspace that composes separately versioned repositories. Those environments are now explicit modes.

## Public fixture mode

**Command:** `python -m helix.public_runtime`

Allowed: Python standard library, tracked files, and a user-selected output path.

Disallowed assumptions: a specific home directory, sibling clones, private GitHub access, external symlinks, a memory bus, or writes to operator state directories.

## Workspace integration mode

**Command:** `python helix/automations/jobapp_helix_spiral.py ...`

Expected integrations may include sibling repositories, configured portfolio and state roots, and optional local services. Legacy defaults are compatibility behavior, not public installation instructions. The next integration step is an environment/TOML configuration adapter.

## Data boundary

Do not commit court or legal evidence, family-case facts, credentials, session material, IDE-generated memory backups, or absolute personal workstation paths in public entry documents.

## Naming boundary

Names such as `spacex-*`, `xai-*`, `nvidia-*`, `openai-*`, or `anthropic-*` identify technical problem domains. They do not state employment, sponsorship, endorsement, production deployment, or certification.

## Change rule

Preserve working integrations. Add portable adapters rather than rewriting working systems merely for appearance.
