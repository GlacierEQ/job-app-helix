# Career proofs — Amgen Senior Forward Deployed Engineer, AI Studio (R-250799)

Keyed to the JD keyword set. Convention: Claim / Evidence / Verified date. All estate systems are independently developed; no claim of Amgen deployment, no pharma/biotech/GxP experience claimed anywhere.

---

## Proof: Evaluation with explicit release thresholds — the forge fails closed

## Claim
Evaluation gates every release as a hard threshold, not advice: the document forge raises HonestyError instead of rendering whenever a bold number isn't on the candidate kit-number allowlist; the campaign engine composes assessments into a GO / NO-GO with immutable evidence models, stable finding codes, and fail-closed decisions. Recovery is restricted to contingency evidence declared before reassessment — the engine never silently tunes values until they pass.

## Evidence
- `~/workspace/job-app-helix/hire_package/resume-forge/cover.py` — `honesty_gate()`; README: "The engine **fails closed**."
- `~/workspace/job-app-helix/` — attributable campaign engine with verification gates (this pack was researched, tailored, forged, and verified end to end by that engine tonight).

## Verified
2026-10-19 (this pack's provenance).

---

## Proof: Gold sets and LLM-as-judge eval harnesses

## Claim
Runs eval harnesses over retrieval, tool use, and multi-step agent behavior using gold sets and LLM-as-judge scoring before anything ships; prompt and configuration tuning is validated by the harness, never eyeballed.

## Evidence
- LLM-as-judge over local Mistral API, verified live 2026-10-06 (`~/workspace/custom-skills/local-mistral/SKILL.md`).
- Verification patterns and gates in `~/workspace/job-app-helix/tests/`; verification gates across the estate.

## Verified
2026-10-06–19.

---

## Proof: Error taxonomies and failure analysis with root-cause quarantine

## Claim
Failures are classified, not just logged: the stranded-files move worker moved 6,000+ files Dropbox → Google Drive with md5+size verification per file and per-file root-cause quarantine — quarantined items are analyzed by cause, not retried blindly; nothing deleted from source; sealed archives never opened. Idempotent JSONL ledger resume means reruns are safe, not hopeful.

## Evidence
- `~/workspace/stranded-files-move/worker.sh`; live hourly run scoreboards in `~/memory/2026-10-19.md`.

## Verified
2026-10-19 (live runs today).

---

## Proof: Expert adjudication and policy enforcement — human-in-the-loop control

## Claim
Consequential actions require human approval: the control plane runs approval gates on anything irreversible, with typed state transitions and recoverable runs. His standing method runs adversarial review before final artifacts — the agent proposes, a human (or explicit policy gate) adjudicates.

## Evidence
- Control-plane practice: 989-test suite, 62/62 verification checks green; audit receipts on every run (carried from Scale AI FDE variant lineage 2026-10-08).
- Adversarial-review lane in the operating doctrine (`~/workspace/job-app-helix/AGENTS.md` §6/§7 methods).

## Verified
2026-10-08 (variant lineage); 2026-10-19 (pack provenance).

---

## Proof: MCP-style integration — 65 connectors, typed, claim-tracked

## Claim
Integrates across a 65-MCP-connector surface plus APIs, webhooks, and data pipelines with typed schemas, claim tracking, evidence boundaries, and idempotent automation — every run emits audit receipts. This is the integration surface a forward-deployed engineer owns on the customer side.

## Evidence
- Connector inventory and claims from variant lineage (2026-10-08–13); multi-layer memory-gateway helper `~/workspace/doctrine/gateway_call.py` with provider/layer provenance preserved.

## Verified
2026-10-08–13 (lineage); re-verify counts before a live submit.

---

## Proof: Durable multi-agent workflows

## Claim
Multi-step agent runs that degrade gracefully instead of failing silently: planning with typed handoff contracts, memory across runs, tool use with typed schemas, error recovery with root-cause quarantine, human escalation on consequential actions. The memory gateway fans out across Mem / MemoryPlugin / Supermemory / XMemo / AiAkiv with layer provenance preserved and dedup that never erases source identity.

## Evidence
- `~/workspace/doctrine/gateway_call.py`; estate map `~/workspace/estate-map/`.

## Verified
2026-10-19 (memory architecture in active daily use).

---

## Proof: Observability / SLOs and rollback-recovery runbooks

## Claim
Every run is observable and recoverable by construction: structured logs, task IDs, correlation IDs, retry counts, success/failure metrics — planned / started / succeeded / failed / verified states distinguished on every run. Runs fail closed; recovery uses idempotent ledgers and declared contingency evidence; nothing silently retries.

## Evidence
- Estate observability conventions; stranded-files worker idempotent resume; campaign-engine recovery contract.

## Verified
2026-10-19.

---

## Proof: Production agent estate — 1,398 repos, live-verified tonight

## Claim
Built and operate a production-grade agent control plane across a 1,398-repository estate (GenAI/RAG/agent systems, MCP integrations, context externalization, document workflows, infrastructure modeling).

## Evidence
- Live readback 2026-10-19 ~23:47 HST: `gh api /user` → 695 public + 703 private = 1,398.

## Verified
2026-10-19 (live GitHub API readback, this pack).

---

## Boundary — responsible AI and regulated delivery, stated straight

## Claim
Zero pharma/biotech/GxP experience — claimed nowhere, disclaimed in the resume boundary note.

## Evidence
- What transfers: evidence discipline — SHA-256 receipts, provenance envelopes, chain-of-custody practice, audit receipts on every run, fail-closed gates on consequential actions. The governance posture a regulated environment demands, engineered into the tooling rather than asserted on paper.

## Verified
2026-10-19.
