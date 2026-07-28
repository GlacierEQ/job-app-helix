# AGENTS.md

## Mission

Keep `job-app-helix` a truthful, reproducible public portfolio control plane.

## Non-negotiable rules

- Preserve working integrations; extend rather than rewrite for novelty.
- Public claims require public evidence.
- `DONE` means the stated pain has a runnable green proof.
- Keep public fixture mode standard-library-only unless a dependency has measured benefit.
- Do not commit secrets, tokens, private evidence, legal material, or generated IDE-memory backups.
- Do not add absolute workstation paths to public documentation.
- Company-aligned names must never be described as employment or deployment.
- Destructive Git history changes require explicit owner approval.

## Required verification

```bash
python -m compileall helix tools
python -m unittest discover -s tests -v
python -m helix.public_runtime demo --scenario nominal
python tools/public_surface_audit.py
```

Use four public terms consistently: **piston**, **helix**, **campaign**, and **proof contract**.
