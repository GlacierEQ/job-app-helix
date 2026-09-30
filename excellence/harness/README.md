# Excellence Cross-Link Harness

Composes multi-repo packs without merging them into a monorepo.

## Packs tested
- **Lockheed triad**: dual-key fence + thread isolator + evidence binding
- **SpaceX stack**: mission-thread quorum + hold-reason compiler

```bash
cd ~/job-app/excellence/harness
PYTHONPATH=src python3 -m unittest discover -s tests -v
```
