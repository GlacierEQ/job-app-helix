# Portable Portfolio and Native-Language Index

## Purpose

This index maps the portfolio’s polyglot direction without depending on machine-local paths or treating the presence of a file extension as proof of mastery.

The governing rule is simple:

> A language earns a place only when it owns a real responsibility, a clear boundary, an interface contract, a build or compile command, a test/proof/benchmark command, and an evidence receipt.

## Core architecture references

- [Job-App Helix](https://github.com/GlacierEQ/job-app-helix) — portfolio control plane, evidence ledger, and README Mesh.
- [The Tower of Babel](https://github.com/GlacierEQ/the-tower-of-babel) — polyglot reference candidate; high innovation, currently blocked/unverified.
- [Polyglot Systems Architecture](https://github.com/GlacierEQ/polyglot-systems-architecture) — language-selection rationale and architecture exhibits; runtime unverified in the current audit.
- [README Optimal Impact Frame](README_OPTIMAL_IMPACT_FRAME.md) — recruiter, expert, AI, and language-fit contract.
- [66-Repository Evidence Audit](PORTFOLIO_EVIDENCE_AUDIT_2026-07-29.md) — current per-repository grades and verification states.

## Language-placement map

The table describes the intended architectural fit. It does **not** claim that each implementation currently builds or performs as designed.

| Language / format | Intended responsibility | Representative repository | Why the fit is plausible | Current proof state |
|---|---|---|---|---|
| Python | control planes, document intelligence, validation, orchestration | [Job-App Helix](https://github.com/GlacierEQ/job-app-helix) | strong testing/tooling and readable decision logic | partially verified at the portfolio root |
| TypeScript | MCP servers, web interfaces, typed integration surfaces | [glaciereq-mcp-stack](https://github.com/GlacierEQ/glaciereq-mcp-stack) | strong schema-driven application and connector ecosystem | unverified |
| Rust | safety governors, concurrent runtimes, deterministic systems utilities | [anthropic-safety-monitor](https://github.com/GlacierEQ/anthropic-safety-monitor) | memory safety and explicit ownership at critical boundaries | README verified; runtime unverified |
| Go | telemetry, network services, bounded daemons | [spacex-telemetry](https://github.com/GlacierEQ/spacex-telemetry) | simple concurrency and deployable static binaries | README verified; runtime unverified |
| C++ | low-level performance kernels and cache algorithms | [openai-reasoning-kv-sentinel](https://github.com/GlacierEQ/openai-reasoning-kv-sentinel) | control over memory layout and mature native tooling | unverified |
| CUDA / Triton | GPU kernels and fused tensor operations | [nvidia-deep-reasoning](https://github.com/GlacierEQ/nvidia-deep-reasoning) | explicit GPU execution and optimization boundaries | unverified; hardware receipt required |
| Julia | numerical integration and scientific models | [spacex-orbital-mechanics](https://github.com/GlacierEQ/spacex-orbital-mechanics) | expressive numerical programming and scientific libraries | README verified; runtime unverified |
| Elixir | supervised distributed services and fault recovery | [colossus-gateway](https://github.com/GlacierEQ/colossus-gateway) | BEAM supervision and message-passing semantics | unverified |
| Swift / Metal | Apple-device and neural-engine integration | [apple-ane-kv-quantizer](https://github.com/GlacierEQ/apple-ane-kv-quantizer) | native platform and accelerator access | unverified; device receipt required |
| Lean 4 | formalized invariants and proof-carrying gates | [grokodile](https://github.com/GlacierEQ/grokodile) | machine-checked propositions rather than prose assertions | unverified; proofs must compile without placeholders |
| Protobuf | versioned cross-language wire contracts | [Job-App Helix](https://github.com/GlacierEQ/job-app-helix) | deterministic schema evolution and generated bindings | verified for the README Mesh v1 contract |
| SQL | reference data, constraints, contradiction queries, vector search | [glaciereq-mcp-stack](https://github.com/GlacierEQ/glaciereq-mcp-stack) | transactional integrity and declarative data invariants | unverified |
| WebAssembly | sandboxed portable execution boundaries | [comet-browser-agent-bridge](https://github.com/GlacierEQ/comet-browser-agent-bridge) | constrained host interface and portable runtime | unverified |
| Odin / Zig / Mojo / Haskell / WAT | specialized systems, simulation, accelerator, proof, or sandbox exhibits | [The Tower of Babel](https://github.com/GlacierEQ/the-tower-of-babel) | each may be appropriate at a narrowly defined boundary | candidate branch blocked/unverified |

## Required proof packet for each language

A repository may advertise a language as production-relevant only when it supplies:

1. the named responsibility and system boundary;
2. the interface to adjacent components;
3. a clean-checkout build or compile command;
4. a test, proof, simulation, or benchmark command;
5. a receipt containing environment, date, revision, and result;
6. explicit `VERIFIED`, `PARTIALLY_VERIFIED`, `BLOCKED`, `UNVERIFIED`, or `FAILED` state.

Language count by itself earns no portfolio credit.

## Portable navigation

- [Executive Portfolio Summary](../RECRUITER_EXECUTIVE_SUMMARY.md)
- [Hierarchical Portfolio Map](../HIERARCHICAL_PORTFOLIO_MAP.md)
- [Exact Portfolio Inventory](../manifests/portfolio_repositories.json)
- [Language-Fit Manifest](../manifests/language_fit.json)
- [Portfolio Audit Runner](../scripts/ci_audit_portfolio.py)
