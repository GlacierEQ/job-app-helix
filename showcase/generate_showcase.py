#!/usr/bin/env python3
"""Generate / refresh hireable SHOWCASE.md from local state maps.

Does not invent metrics. Does not include legal/case repos.
Writes SHOWCASE.md next to this script; exit 0 on success.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STATE = Path.home() / "GlacierEQ_Swarm" / "state"
OUT = ROOT / "SHOWCASE.md"

# Must appear in output (verification contract)
MUST = (
    "AKOS",
    "pro-code",
    "Pro-",
    "xAI",
    "SpaceX",
    "Anthropic",
    "NVIDIA",
    "Notion",
)

# Block case-PII / court labels in *repo names* and body (avoid matching policy prose)
LEGAL_BLOCK = re.compile(
    r"1FDV|FEDERAL.?WARFARE|CASE.?MATRIX|SUPERLUMINAL|DOCKETS?\b|KEKOA|CATACLYSM|ASPEN.?GROVE|"
    r"cathedrals_cases|legal-case|legal_case|family.?court|criminal.?court|"
    r"\bcsea\b|civil.?rico|§1983|apex-legal|Pro-Legal|Pro-Kekoa|casey-legal",
    re.I,
)


def load_json(name: str) -> dict:
    p = STATE / name
    if not p.exists():
        return {}
    return json.loads(p.read_text())


def sample_repos(slim: dict, label_substr: str, n: int = 8) -> list[str]:
    cats = slim.get("categories") or {}
    for label, block in cats.items():
        if label_substr.lower() in label.lower():
            repos = [r for r in (block.get("repos") or []) if not LEGAL_BLOCK.search(r)]
            return repos[:n]
    return []


def gh(name: str) -> str:
    return f"https://github.com/GlacierEQ/{name}"


def build() -> str:
    slim = load_json("ultimate_repo_map_slim.json")
    vis = load_json("repo_visibility_policy.json")
    legal_policy = vis.get("legal_policy") or "private_first"
    colossus = sample_repos(slim, "Colossus", 6)
    spacex = sample_repos(slim, "SpaceX", 8)
    apex = sample_repos(slim, "APEX", 6)
    akos = sample_repos(slim, "AKOS", 6)

    def bullets(names: list[str]) -> str:
        if not names:
            return "_see ultimate_repo_map_"
        return " · ".join(f"[{n}]({gh(n)})" for n in names)

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d UTC")
    return f"""# GlacierEQ — Hireable Framework Showcase

**Single entry for recruiters & engineers.**  
Operator: **GlacierEQ** · Hireable systems: **AKOS**, **pro-code**, **Pro-*** / motion families.  
Targets: **xAI** · **SpaceX** · **Anthropic** · **NVIDIA** · **Notion**.

> **Visibility:** private-first portfolio. Litigation material: **{legal_policy}** — never linked here.  
> Regenerated: {ts} · source maps under `GlacierEQ_Swarm/state/`

---

## 1. Core frameworks

| Framework | Role | Location | Use |
|-----------|------|----------|-----|
| **AKOS** | Apex Knowledge OS — identity, sessions, governance, portfolio map, swarm bridge | [{gh("AKOS")}]({gh("AKOS")}) | Canonical how-we-work; IDENTITY / GOVERNANCE / REPOS / EASTER_EGGS |
| **pro-code** | Pro_Code standards + APEX control-surface strand | [{gh("pro-code")}]({gh("pro-code")}) | Engineering law for agents that ship real code |
| **Pro-*** | Productized motion agents/tools (Pro-comet-agent, Pro-Mastermind, Pro-Swarm, …) | e.g. [{gh("Pro-comet-agent")}]({gh("Pro-comet-agent")}) | Ship capabilities, not prompt piles |
| **token_saver** | Token-efficiency stack (pure_pointer, MICROWAVE, ledgers) | [{gh("token_saver")}]({gh("token_saver")}) | Measure savings; keep agent context lean |
| **mastermind** | Control-plane / multi-repo orchestration | [{gh("mastermind")}]({gh("mastermind")}) | Boss API + piston coordination |
| **Double Helix** | Alpha (what) ↔ Omega (how) | Colossus `*-alpha` / `*-omega` | Split recognition from execution |

### Genius instructs
- **AKOS** GOVERNANCE · IDENTITY · EASTER_EGGS · REPOS  
- **pro-code** standards / KNOWLEDGE  
- **AGENTS.md** L0–L5 progressive agent OS (`~/.grok/AGENTS.md`)  
- **repo-public-promotion-flipper** — intelligent private→public (legal hard-lock)

---

## 2. Motion families × company targets

| Target | Motion family | Concrete exhibits |
|--------|---------------|-------------------|
| **xAI** | Colossus-class infra (cooling, energy, security, gateway, helix) | [{gh("xai-colossus-cooling")}]({gh("xai-colossus-cooling")}) · [{gh("colossus-gateway")}]({gh("colossus-gateway")}) · [{gh("xai-colossus-2")}]({gh("xai-colossus-2")}) · {bullets(colossus)} |
| **SpaceX** | Flight / ground / thermal / orbital helix | [{gh("spacex-thermal-protection")}]({gh("spacex-thermal-protection")}) · [{gh("spacex-orbital-mechanics")}]({gh("spacex-orbital-mechanics")}) · [{gh("spacex-telemetry")}]({gh("spacex-telemetry")}) · {bullets(spacex)} |
| **Anthropic** | Agent OS, MCP discipline, tool-use orchestration | [{gh("AKOS")}]({gh("AKOS")}) · [{gh("pro-code")}]({gh("pro-code")}) · [{gh("Pro-comet-agent")}]({gh("Pro-comet-agent")}) · {bullets(akos)} |
| **NVIDIA** | GPU/NPU thermal & acceleration-aware compute | [{gh("xai-colossus-cooling")}]({gh("xai-colossus-cooling")}) · [{gh("xai-colossus-energy")}]({gh("xai-colossus-energy")}) · [{gh("xai-colossus-servers")}]({gh("xai-colossus-servers")}) · [{gh("nvidia-gpu-health")}]({gh("nvidia-gpu-health")}) · [{gh("nvidia-deep-reasoning")}]({gh("nvidia-deep-reasoning")}) |
| **Notion** | Workspace / MCP ops craft (automation, optimizer, MCP bridge) — *engineering only* | [{gh("notion-workflow-intelligence")}]({gh("notion-workflow-intelligence")}) · [{gh("notion-workspace-optimizer")}]({gh("notion-workspace-optimizer")}) · [{gh("notion-mcp-empowerment-engine")}]({gh("notion-mcp-empowerment-engine")}) · [{gh("glaciereq-mcp-stack")}]({gh("glaciereq-mcp-stack")}) |
| **APEX runtime** | CLI / control plane / workers | [{gh("apex-cli")}]({gh("apex-cli")}) · {bullets(apex)} |

---

## 3. Three checkable deep-dives

### AKOS
**Role:** Operator OS for knowledge, governance, portfolio truth.  
**Location:** {gh("AKOS")}  
**Read:** IDENTITY.md · GOVERNANCE.md · REPOS.md · EASTER_EGGS.md

### pro-code
**Role:** Pro_Code engineering standards for hireable agent work.  
**Location:** {gh("pro-code")}  
**Pairs with:** AKOS + mastermind

### Pro-* / motion sample (xAI cooling)
**Role:** Physics-first Colossus thermal motion (H100/H200-class).  
**Location:** {gh("xai-colossus-cooling")}  
**Also:** {gh("colossus-gateway")} · {gh("spacex-thermal-protection")} (SpaceX family)

---

## 4. 10-minute review path
1. This file  
2. AKOS → IDENTITY + REPOS  
3. pro-code  
4. xai-colossus-cooling + spacex-thermal-protection  
5. Pro-comet-agent  

---

## 5. Policy
| Rule | Statement |
|------|-----------|
| Litigation material | Absolute private until processed — **not in this showcase** |
| Metrics | No invented scores |
| Secrets | Never embedded |

Local maps: `state/ultimate_repo_map.md` · `ecosystem_map.json` · `repo_visibility_policy.json`

---

*GlacierEQ live job application — frameworks are real code and instruct systems.*
"""


def main() -> int:
    text = build()
    for m in MUST:
        if m not in text:
            raise SystemExit(f"missing required string: {m}")
    if LEGAL_BLOCK.search(text):
        # allow only if we accidentally matched something benign — fail hard on known case tokens
        raise SystemExit("legal/case content detected — abort")
    OUT.write_text(text)
    print(f"wrote {OUT} bytes={OUT.stat().st_size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
