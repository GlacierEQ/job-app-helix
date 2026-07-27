# Job-App Helix — Purpose, Topic Map, and Perfection Plan

**Date:** 2026-07-26  
**Operating law:** Truth first. One claim must resolve to one artifact, one test, and one reproducible demo.  
**Optimization law:** Spend tokens only when retrieval or computation changes a decision.

## 1. Purpose

This repository is a **career-intelligence and technical-proof control plane**. It converts a large private engineering portfolio into a small, verifiable hiring surface:

1. select the strongest original systems;
2. prove them with tests and runnable demonstrations;
3. explain their assumptions and limits honestly;
4. tailor the evidence to a company or role;
5. package the result as a resume, deck, outreach message, and live walkthrough.

It is not evidence of employment at the companies named in the portfolio, flight certification, peer review, production SLAs, or equal maturity across every repository.

## 2. Topic map

| Pillar | Core topic | Primary proof surface | Hiring value |
|---|---|---|---|
| Cognitive OS | agent governance, memory, orchestration, token discipline | AKOS, pro-code, token_saver | Govern complex AI-assisted work |
| Compute physics | cooling, power, GPU health, infrastructure control | xai-colossus-cooling, colossus-gateway, nvidia-gpu-health | First-principles infrastructure reasoning |
| Aerospace helix | thermal protection, telemetry, autonomy | spacex-thermal-protection, spacex-telemetry, spacex-autonomy | Safety-aware real-time systems thinking |
| Reasoners and safety | KV pressure, scheduling, policy gates, adversarial validation | openai-reasoning-kv-sentinel, deepmind-tpu-mesh-optimizer, anthropic-safety-monitor | Reliable model and accelerator operations |
| Evidence intelligence | source provenance, public records, declassified releases, OSINT | new public-source intake pillar | Turn newly public records into traceable knowledge |
| Hire delivery | resume, deck, company morphs, outreach, live demo | hire_package, showcase, whole | Convert technical evidence into interviews |

The three lead exhibits remain:

1. `xai-colossus-cooling`;
2. `spacex-thermal-protection`;
3. `AKOS + pro-code + token_saver`.

Everything else should support one of those stories or remain outside the primary hiring path.

## 3. Truth snapshot

Measured locally on 2026-07-26:

- 64 directories exist under `repos/`; 63 contain `.git`.
- 62 repositories contain `mastermind_sidecar.py`.
- APEX Highway reports 61 of 62 discovered nodes healthy (98.39%); `openclaw` lacks the standard integrity files.
- The bounded control-plane test run produced 23 passes and 2 failures.
  - `test_apex_highway.py` expects `OPERATIONAL`, but the real mesh is `DEGRADED`.
  - `helix/test_helix_meta.py` supplies the project root where the engine expects the `repos/` root, producing zero discovered nodes.
- `spacex_sharklaser/test_showcase.py` passes separately (4 tests), but combining it with `showcase/test_showcase.py` creates a duplicate-module-name collection error.
- `repos_inventory.json` reports 43 repositories and is stale.

These are repairable control-plane defects. Until repaired, “all green” and fixed repository-count claims should not be repeated.

## 4. Target architecture

```text
Official/public sources + private repos
                |
         immutable evidence records
       (URI, hash, time, provenance)
                |
       compact claim and capability graph
     (claim -> source -> code -> test -> demo)
                |
        role/company projection layer
                |
    resume | deck | demo | outreach | interview
```

The graph is the durable center. Documents are generated views, not competing sources of truth.

## 5. Highest-token-savings protocol

### Context tiers

| Tier | Contents | Loading rule |
|---|---|---|
| T0 | objective, constraints, current decision, pointers | always load; target under 800 tokens |
| T1 | claim registry, test summary, selected hero metadata | load only for the active role or task |
| T2 | source excerpts, code summaries, prior decisions | retrieve by stable ID and relevance |
| T3 | full documents, repositories, transcripts, binaries | open only to verify a disputed fact or execute work |

### Required mechanics

- Store large bodies once and address them by SHA-256 pointer.
- Keep one canonical claim registry; generate prose from it.
- Retrieve small evidence windows instead of copying whole documents.
- Put the decisive facts at the beginning and the requested output contract at the end of context.
- Cache deterministic transforms by source hash + tool version + parameters.
- Record exact input/output byte and token counts; never convert bytes into claimed tokens.
- Compress only after a measured break-even test. Recent research finds prompt compression can help in the right operating window but can also cost more than it saves.
- Evaluate token reduction and task correctness together. Savings that change an answer, drop a citation, or break a test are failures.

### Minimum telemetry

`input_tokens`, `output_tokens`, `cache_hit`, `retrieved_bytes`, `compression_ratio`, `latency_ms`, `task_pass`, `citation_pass`, and `estimated_cost`.

## 6. Perfection sequence

### P0 — Restore truth (one focused engineering pass)

1. Make APEX Highway roots explicit and repository-relative; remove hidden dependence on `~/job-app`.
2. Fix the meta-test to target `repos/`.
3. Resolve the duplicate `test_showcase` module names.
4. Decide whether `openclaw` joins the governed mesh or is explicitly excluded.
5. Regenerate repository inventory and all derived counts from one script.
6. Add a machine-readable claim registry with `verified`, `inferred`, `proposed`, and `excluded` states.
7. Replace “all green” summaries with generated test receipts.

**Gate:** one clean verification command, no collection errors, no contradictory counts.

### P1 — Build the one-click proof path

1. Provide four stable commands: `verify`, `demo`, `pack`, and `audit`.
2. Make the 15-minute demonstration deterministic and offline-capable.
3. For each hero, expose:
   - problem and assumptions;
   - implementation entry point;
   - test command;
   - one measured output;
   - limitations and next experiment.
4. Generate one reviewer index that reaches every proof in two clicks or fewer.

**Gate:** a clean machine can reproduce the hero evidence from documented commands.

### P2 — Make token_saver the shared context kernel

1. Define a common pointer envelope for local files, GitHub artifacts, cloud documents, and public records.
2. Add content-addressed caching, selective retrieval, deduplication, and invalidation receipts.
3. Benchmark baseline vs pointer retrieval vs compression on real job-app tasks.
4. Add regression cases for missing evidence, contradictory claims, stale caches, and citation loss.
5. Publish only measured savings by workload.

**Gate:** lower median input tokens without a task-pass or citation-pass regression.

### P3 — Add the declassified-technology and OSINT pillar

Start with official release channels:

- National Archives National Declassification Center release lists;
- CIA FOIA Electronic Reading Room / CREST;
- later adapters only after their official access and reuse terms are verified.

For every record store:

- issuing agency and official URL;
- record group, collection, document identifier, title, and release date;
- retrieval time, byte hash, media type, and OCR status;
- exact excerpts separated from analyst inference;
- privacy, legal, export-control, and redistribution review state.

Use a staged pipeline:

`watch -> acquire -> hash -> OCR -> normalize -> extract claims -> cross-check -> analyst review -> publish pointer`

“Declassified” means publicly released by the responsible authority. It does not mean accurate, current, safe to operationalize, or free of remaining restrictions.

**Gate:** every surfaced claim resolves to the official record and preserves fact/inference separation.

### P4 — Convert proof into job outcomes

1. Select one primary role family for each two-week campaign.
2. Generate a company-specific evidence projection from the canonical graph.
3. Send a small number of reviewed, exhibit-first messages.
4. Track replies, demo requests, interview progression, objections, and proof gaps.
5. Feed objections back into hero tests and documentation.

**Gate:** measure qualified conversations and interviews, not repository count or message volume.

### P5 — Expand integrations only when they remove manual work

Use local-first adapters with optional free-tier sync for GitHub, Notion, Supabase, Vercel, Google Workspace, Microsoft 365, object/vector stores, and analytics systems. Every connector must support:

- least privilege;
- runtime secret injection;
- health and freshness receipts;
- export and replay;
- graceful offline behavior;
- provider-independent canonical records.

Pinecone, Qdrant, MotherDuck, Airtable, or another service is a replaceable projection. None becomes the sole memory authority.

## 7. Research foundations

- [LongLLMLingua](https://arxiv.org/abs/2310.06839): prompt compression can reduce long-context cost, but must be evaluated on the actual task.
- [Prompt Compression in the Wild](https://arxiv.org/abs/2604.02985): compression has a hardware- and workload-dependent break-even point.
- [Lost in the Middle](https://arxiv.org/abs/2307.03172): longer context does not guarantee reliable retrieval; relevant position matters.
- [MemGPT](https://arxiv.org/abs/2310.08560): hierarchical memory and controlled movement between fast and slow tiers fit this project better than loading everything.
- [NIST AI RMF Generative AI Profile](https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence): govern, map, measure, and manage AI risks with provenance and evaluation.
- [National Declassification Center release lists](https://www.archives.gov/declassification/ndc/release-lists): official rolling intake point for newly declassified U.S. records.
- [CIA CREST Electronic Reading Room](https://www.cia.gov/readingroom/collection/crest-25-year-program-archive): official searchable declassified-record collection.

## 8. Stop list

- Do not elevate every repository equally.
- Do not add a new named subsystem without a unique capability and test.
- Do not repeat entire documents in prompts.
- Do not treat byte savings as token savings.
- Do not describe a green unit test as production, flight, or field validation.
- Do not mix legal/case repositories into hiring materials.
- Do not publish automated OSINT conclusions without source-level human review.
- Do not add cloud dependencies where a local pointer and replay log are sufficient.

## 9. Definition of perfect

Perfect here is not maximum size. It is:

- one canonical truth graph;
- three undeniable hero demonstrations;
- zero contradictory claims;
- reproducible verification;
- bounded, measured context use;
- official-source provenance;
- graceful offline operation;
- a short path from technical proof to a qualified hiring conversation.

