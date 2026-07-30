# Moonshot Kimi — Evidence-Bound Candidate Package

## Positioning

**Target:** systems architecture, model infrastructure, agent orchestration, or special-projects engineering roles related to long-context and distributed AI systems.

**Candidate signal:** Casey Barton builds interconnected control planes, evidence systems, agent governance, and polyglot infrastructure. This package does not imply employment, endorsement, production deployment, or access to Moonshot AI systems.

## Recruiter opening

The portfolio demonstrates an ability to move between model-serving concerns, context and KV-cache architecture, distributed tool systems, safety boundaries, and operational evidence. The strongest signal is not a single speculative benchmark; it is the design of systems that make their own limits and proof state visible.

## Lead exhibits

| Repository | Relevance | Current audit state |
|---|---|---|
| [kimi-mooncake-kv-stream](https://github.com/GlacierEQ/kimi-mooncake-kv-stream) | KV streaming, long-context infrastructure, and numerical/system boundary design | unverified; needs reference-correctness and throughput receipts |
| [deepseek-mla-moe-sentinel](https://github.com/GlacierEQ/deepseek-mla-moe-sentinel) | attention/MoE monitoring and kernel-routing concepts | unverified; needs benchmark and reference tests |
| [glaciereq-mcp-stack](https://github.com/GlacierEQ/glaciereq-mcp-stack) | typed MCP/JSON-RPC integration and cross-system composition | unverified; needs end-to-end contract receipts |
| [AKOS](https://github.com/GlacierEQ/AKOS) | authority, provenance, maturity, and completion semantics for agent systems | README verified; runtime unverified |
| [token_saver](https://github.com/GlacierEQ/token_saver) | context-efficiency and compression direction | unverified; needs quality-preserving savings benchmarks |
| [Job-App Helix](https://github.com/GlacierEQ/job-app-helix) | evidence control plane, deterministic decisions, README Mesh, and portfolio verification | partially verified |

## Technical narrative

The package is strongest when presented as one system:

```text
Long-context / KV architecture
              │
              ▼
Model and tool integration layer
              │
              ▼
Agent authority and safety controls
              │
              ▼
Evidence receipts and portfolio verification
```

This framing demonstrates architecture across layers while preserving the independence and current proof state of each repository.

## What not to claim

- measured latency, cache-hit, throughput, cost, or model-quality results without a current benchmark receipt;
- production use by Moonshot AI or any other company;
- hardware execution without a compatible runner receipt;
- portfolio-wide runtime verification based on hashes or a small sample;
- mastery of a language based only on checked-in example files.

## Verification path

Review the portfolio root first:

- [Executive Portfolio Summary](../RECRUITER_EXECUTIVE_SUMMARY.md)
- [66-Repository Evidence Audit](../docs/PORTFOLIO_EVIDENCE_AUDIT_2026-07-29.md)
- [README Optimal Impact Frame](../docs/README_OPTIMAL_IMPACT_FRAME.md)
- [Language-Fit Manifest](../manifests/language_fit.json)

From a clean Job-App Helix checkout:

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
python scripts/check_proto_contract.py
python -m job_app_helix.readme_mesh_cli validate
```

The bounded multi-repository audit requires the canonical local workspace:

```bash
python ci_audit_portfolio.py
```

Its output must be read by scope: exact inventory validation is not the same as runtime verification, and every executed repository is named in the resulting receipt.

## Recommended application emphasis

1. Lead with Job-App Helix and AKOS as the architectural and governance spine.
2. Use Kimi/Mooncake and DeepSeek repositories as technically ambitious domain exhibits, explicitly labeled unverified until benchmark receipts exist.
3. Present the polyglot trajectory as disciplined boundary selection, not language accumulation.
