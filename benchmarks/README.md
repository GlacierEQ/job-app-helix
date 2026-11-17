# LegalBench subset receipts

Public JSON only (scores, task ids, model id, timestamp). No proprietary prompts.

## Run (private overlay)

```bash
python scripts/run_legalbench_subset.py <path-to-legalbench-clone> benchmarks/legalbench-subset-YYYY-MM-DD.json
```

Commit resulting file here after human review.

Schema: see private `job_app_helix` `schemas/helix_benchmark_evidence.json`.
