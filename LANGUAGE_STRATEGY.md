# Language diversification strategy (honest)

Diversify **where the runtime contract is real** — not for resume language bingo.

| Need | Prefer | Example |
|------|--------|---------|
| Portable inference / reasoning scores | **ONNX + ORT** | `openai-reasoning-kv-sentinel` keep-importance model |
| SI science + proofs | **Python** | thermal `Q=ṁcₚΔT`, orbital, gates |
| High-rate concurrent I/O | **Go / Rust** | telemetry bus, mesh (future hot path) |
| Driver / GPU APIs | **C++ / CUDA** | when talking bare metal (not claimed yet) |
| Operator UI / extensions | **TypeScript** | pro-code surfaces, VS Code extensions |
| Fast local agents / TUI | **Rust** | grok-build class tools |

## Shipped now

- **ONNX for reasoning KV:** `models/token_keep_importance.onnx` + `OnnxKeepScorer` + `ReasoningKVSentinel(use_onnx=True)`
- Export: `python3 scripts/export_onnx_importance.py`
- Docs: `openai-reasoning-kv-sentinel/LANGUAGE_STACK.md`

## Next advantageous moves (when hammering)

1. Go or Rust telemetry ingest for 100kHz-class demos  
2. ORT C++/Rust binding consuming the same ONNX weights  
3. Leave pure science in Python with contracts  
