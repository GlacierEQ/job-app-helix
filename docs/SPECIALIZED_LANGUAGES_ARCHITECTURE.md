# Specialized-Language Architecture

## Thesis

The portfolio’s new trajectory is not “more languages.” It is **better boundary selection**.

A specialized language is justified when it produces a measurable advantage in one or more of these areas:

- correctness or formal verification;
- memory or concurrency safety;
- hardware access;
- numerical expressiveness;
- deterministic serialization;
- fault supervision;
- sandboxing;
- deployment simplicity;
- performance that is demonstrated against a reference implementation.

A language is not justified when it exists only to enlarge a résumé technology list.

## Decision process

```text
Workload and failure model
           │
           ▼
Required properties
correctness • latency • hardware • safety • portability
           │
           ▼
Candidate language comparison
           │
           ▼
Boundary + interface contract
           │
           ▼
Build/test/proof/benchmark command
           │
           ▼
Evidence receipt and verification state
```

## Placement matrix

| Boundary | Candidate technology | Why it may fit | Required verification |
|---|---|---|---|
| Portfolio orchestration and evidence processing | Python | readable control logic, mature validation/testing, Protobuf support | lint, typecheck, tests, deterministic receipt |
| MCP and web-facing integration | TypeScript | typed JSON contracts and strong connector/UI ecosystem | compile, lint, contract tests, integration fixture |
| Safety-critical concurrent governor | Rust | ownership, memory safety, explicit error semantics | `cargo test`, denial-path fixtures, concurrency checks |
| Telemetry and network service | Go | straightforward concurrency and static deployment | race-enabled tests, packet fixtures, ordering tests |
| Native cache or numerical kernel | C++ | memory-layout control and mature performance tooling | reference-correctness suite and benchmark environment |
| GPU kernel | CUDA or Triton | direct accelerator execution and fusion opportunities | hardware-backed correctness and performance receipt |
| Orbital or scientific integration | Julia | numerical expressiveness and scientific computing ecosystem | comparison against known solutions and error bounds |
| Fault-tolerant distributed gateway | Elixir | supervision trees and message-passing isolation | process-failure and restart tests |
| Apple accelerator integration | Swift and Metal | native access to Apple frameworks and hardware | device-specific build and execution receipt |
| Machine-checked invariant | Lean 4 | propositions verified by a proof kernel | successful compile with no `sorry` or equivalent placeholder |
| Cross-language identity and event schema | Protocol Buffers | versioned contracts and generated bindings | compile, descriptor comparison, round-trip test |
| Sandboxed portable execution | WebAssembly | constrained host capabilities and portable runtime | host-boundary tests and capability-denial fixtures |

## Current portfolio posture

### Verified at Job-App Helix

The current repository uses Python, Protocol Buffers, JSON, and Markdown at explicit boundaries. Their responsibilities, commands, receipts, and verification states are declared in [`manifests/language_fit.json`](../manifests/language_fit.json).

### Promising but runtime-unverified

Several portfolio repositories have plausible language/domain pairings—for example Go telemetry, Julia orbital mechanics, Rust safety controls, and Protobuf-based contracts—but still require repository-native current receipts before they can be described as working implementations.

### Tower of Babel

[The Tower of Babel](https://github.com/GlacierEQ/the-tower-of-babel) is the portfolio’s most ambitious polyglot reference candidate. Its core idea is strong: match language semantics to workload semantics. Its current public and candidate states must remain separate:

- **innovation:** high;
- **candidate architecture:** materially stronger than the public baseline;
- **current release state:** blocked/unverified;
- **promotion requirement:** close correctness/security findings, obtain green CI, and produce per-language build/test/proof receipts.

A blocked toolchain is not a failure, but it is also not a pass.

## Interface rule

Polyglot systems fail when language boundaries become informal. Every cross-language edge must define:

- message or ABI schema;
- ownership of state;
- serialization and versioning rules;
- timeout and retry behavior;
- error translation;
- idempotency expectations;
- observability and receipt format;
- backward-compatibility policy.

## Acceptance gate

A specialized implementation is eligible for recruiter-facing promotion only when all conditions are true:

1. the language owns a named responsibility;
2. the repository explains why the primary language is less suitable at that boundary;
3. the interface is versioned and testable;
4. a clean-checkout build or compile command exists;
5. at least one real test, proof, simulation, or benchmark executes;
6. the receipt identifies revision and environment;
7. failure modes are documented;
8. status is stated without converting blocked or unverified work into success.

## Related artifacts

- [README Optimal Impact Frame](README_OPTIMAL_IMPACT_FRAME.md)
- [Portable Language Index](LIBRARY_OF_LINKS_AND_NATIVE_LANGUAGES.md)
- [Language-Fit Manifest](../manifests/language_fit.json)
- [66-Repository Evidence Audit](PORTFOLIO_EVIDENCE_AUDIT_2026-07-29.md)
