# Contributing

## Standard

A change is complete when its stated behavior is implemented, tested, documented, and reproducible from a clean clone.

## Workflow

1. Create a focused branch.
2. Add or update typed behavior.
3. Add tests that fail before the change and pass after it.
4. Keep public documentation free of local paths, generated IDE state, private material, and unsupported claims.
5. Run:

```bash
python -m pip install -e ".[dev]"
ruff check src tests scripts
pytest
python scripts/check_public_surface.py
```

6. Describe the problem solved, evidence added, limitations, and rollback path in the pull request.

## Code principles

- Prefer explicit data models over unstructured dictionaries at public boundaries.
- Keep assessment functions deterministic.
- Preserve evidence; do not mutate inputs to manufacture a passing result.
- Fail closed when a required condition is unknown or unsatisfied.
- Use stable finding codes and plain-language messages.
- Add dependencies only when they provide a measurable benefit.
