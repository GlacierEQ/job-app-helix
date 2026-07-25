# Job-app readiness scores (post-P0 complete)

**Scale:** 0–**99** interview/demo readiness (honest). Cap 99 — not fake production heritage.  
**Source:** `state/jobapp_repo_scores.json` · scorer `automations/score_jobapp_repos.py`  
**Updated:** 2026-07-13 after P0 priority batch + scorer Notion/APEX family fix

## Headline

| Band | Count |
|------|------:|
| **Elite ≥90** | **25** |
| **READY ≥80** | **41** |

**Flagships:** `xai-colossus-cooling` **99** · `spacex-thermal-protection` **97** · `Pro-comet-agent` **96**

## P1 batch (helix + servers + AEON)

See `P1_COMPLETIONS.md`. SpaceX helix modules elevated with src+tests+AKOS.

**Live counts:** Elite **25** · READY **41** (from latest scorer run).


## P0 batch completed (lowest-first)

| Repo | Score | Status |
|------|------:|--------|
| notion-workspace-optimizer | **83** | integrated · src+tests+AKOS |
| xai-colossus-energy-alpha | **88** | integrated · power budget |
| xai-colossus-energy-omega | **88** | integrated · load shed |
| xai-colossus-cooling-alpha | **92** | integrated · thermal envelope |
| xai-colossus-cooling-omega | **92** | integrated · flow controller |
| glaciereq-mcp-stack | **92** | integrated · MCP router |
| apex-control-plane | **96** | integrated · dispatch |
| notion-mcp-empowerment-engine | **96** | integrated · intent chains |
| Pro-comet-agent | **96** | integrated · plan/act/reflect |

Helix alpha/omega twins are **integrated** (not deferred).

## By company (avg)

| Company | Avg | Max | Notes |
|---------|----:|----:|-------|
| xAI | ~90 | 99 | twins elevated 88–92 |
| SpaceX | ~88 | 97 | broad helix |
| Agents/APEX | ~92 | 96 | control-plane + MCP |
| Anthropic | ~89 | 96 | Pro-comet elite |
| Notion | ~87 | 96 | optimizer 83 · empower 96 |
| NVIDIA | 88 | 88 | both demo-able |
| Microsoft | ~86 | 88 | azure-ops + zero-trust |
| Cross-cutting | ~86 | 94 | token_saver · mastermind |

## What “READY” means

- Demo-able portfolio code + AKOS bridge + tests where elevated  
- **Not** employment at SpaceX/xAI/NVIDIA/Anthropic/Microsoft  
- **Not** flight certification  

## Re-score

```bash
python3 ~/GlacierEQ_Swarm/automations/score_jobapp_repos.py
```

See also: `P0_COMPLETIONS.md` · `state/jobapp_priority_manifest.json`
