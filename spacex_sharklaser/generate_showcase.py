#!/usr/bin/env python3
"""Generate SpaceX-first shark-laser showcase from jobapp_whole registry.

No invented employment, metrics, or legal content.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REG = Path.home() / "GlacierEQ_Swarm" / "jobapp_whole" / "registry.json"
OUT = ROOT / "SPACEX_SHARKLASER_SHOWCASE.md"
AZ = ROOT / "A_TO_Z_CAMPAIGN.md"

LEGAL = re.compile(
    r"1FDV|FEDERAL-WARFARE|SUPERLUMINAL|cathedrals_cases_distill",
    re.I,
)

# Problem-space themes (not claims of SpaceX employment)
BOTTLENECKS = [
    {
        "theme": "Reentry / thermal protection",
        "why": "Survivability under extreme heat flux; early anomaly detection",
        "exhibits": ["spacex-thermal-protection"],
    },
    {
        "theme": "Launch cadence & sequencing",
        "why": "Compress go/no-go decision loops; reduce ops friction",
        "exhibits": ["spacex-launch-sequencer", "spacex-mission-control"],
    },
    {
        "theme": "Telemetry & ground network",
        "why": "High-rate data paths; ground segment reliability",
        "exhibits": ["spacex-telemetry", "spacex-ground-network"],
    },
    {
        "theme": "Orbital mechanics & mission software",
        "why": "Trajectory/ops software hygiene; mission stack coherence",
        "exhibits": ["spacex-orbital-mechanics", "spacex-mission-control"],
    },
    {
        "theme": "Propulsion monitoring",
        "why": "Health signals under flight-like stress models",
        "exhibits": ["spacex-propulsion-monitor"],
    },
    {
        "theme": "Satellite mesh / constellation ops software",
        "why": "Mesh coordination patterns for multi-asset systems",
        "exhibits": ["spacex-satellite-mesh"],
    },
    {
        "theme": "Agent OS & multi-domain firefighting",
        "why": "On-demand special projects need OS + standards, not one-off scripts",
        "exhibits": ["AKOS", "pro-code", "token_saver", "Pro-comet-agent"],
    },
]


def load_registry() -> dict:
    return json.loads(REG.read_text())


def by_id(data: dict) -> dict:
    return {i["id"]: i for i in data["frameworks"] + data["exhibits"]}


def gh(name: str) -> str:
    return f"https://github.com/GlacierEQ/{name}"


def build_showcase(data: dict) -> str:
    idx = by_id(data)
    spacex = [
        i
        for i in data["frameworks"] + data["exhibits"]
        if i.get("family") == "SpaceX" and i["status"] == "integrated"
    ]
    fw = [idx[k] for k in ("AKOS", "pro-code", "token_saver", "mastermind") if k in idx]
    pro = [i for i in data["exhibits"] if i["id"] == "Pro-comet-agent"]

    def row(it: dict) -> str:
        return (
            f"| **{it['id']}** | `{it['status']}` | {it['role']} | "
            f"[{it['id']}]({it['pointer']}) |"
        )

    spacex_table = "\n".join(
        [
            "| Exhibit | Status | Role | Pointer |",
            "|---------|--------|------|---------|",
            *[row(i) for i in spacex],
        ]
    )
    fw_table = "\n".join(
        [
            "| Framework | Status | Role | Pointer |",
            "|-----------|--------|------|---------|",
            *[row(i) for i in fw + pro],
        ]
    )

    bn_lines = []
    for b in BOTTLENECKS:
        links = []
        for e in b["exhibits"]:
            if e in idx:
                links.append(f"[{e}]({gh(e)})")
            else:
                links.append(e)
        bn_lines.append(
            f"| **{b['theme']}** | {b['why']} | {', '.join(links)} |"
        )
    bn_table = "\n".join(
        [
            "| Bottleneck theme (problem space) | Why it matters | Portfolio motion |",
            "|----------------------------------|----------------|------------------|",
            *bn_lines,
        ]
    )

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d UTC")
    return f"""# SpaceX Shark-Laser Showcase

**Positioning:** All-domain / **on-demand special-projects** operator — the **shark-laser** seat: open a hard problem, leave working systems + governance, not slides.

**Not claiming:** employment at SpaceX, flight hardware heritage, or production SLA ownership.  
**Is claiming:** real portfolio motions (GitHub `GlacierEQ/*`) + agent OS (**AKOS**) + engineering law (**pro-code**) aimed at SpaceX-class bottlenecks.

> Generated: {ts} · data: `jobapp_whole/registry.json` · orchestration: [`A_TO_Z_CAMPAIGN.md`](./A_TO_Z_CAMPAIGN.md)

---

## 1. Why this package (ground-up jump)

SpaceX wins by **compressing iteration under physics and ops constraints**. This showcase is a coherent offer:

1. **Agent operating system** — multi-domain firefighting without entropy (**AKOS**)  
2. **Pro-grade standards** — agents that ship real code (**pro-code**)  
3. **SpaceX helix software motions** — thermal, orbital, telemetry, launch, ground, propulsion, mesh, mission control  
4. **Honest assessment culture** — measure or unknown; no hype metrics  

Related: [`../jobapp_whole/WHOLE.md`](../jobapp_whole/WHOLE.md) · [`../jobapp_hire_package/RESUME_MUSK_ORBIT.md`](../jobapp_hire_package/RESUME_MUSK_ORBIT.md)

---

## 2. Frameworks (operating core)

{fw_table}

---

## 3. SpaceX helix exhibits (integrated)

{spacex_table}

Deferred (later pass): `spacex-autonomy`, `spacex-cryogenics` — see whole PASS_LOG.

---

## 4. Bottleneck map → motions

{bn_table}

---

## 5. Shark-laser / special-projects pitch (paste-ready)

**One-liner:**  
I build multi-domain systems — **AKOS** (agent OS), **pro-code**, and a SpaceX-aligned software helix (thermal-protection, orbital, telemetry, launch, ground, propulsion, mesh, mission-control) — and I want the **on-demand special-projects** seat where hard problems do not fit a single stack.

**What you get on day one:** live code walk of `spacex-thermal-protection` + `AKOS` governance + one ops motion (telemetry or launch-sequencer).

**What you do not get:** fake FAANG tenure or invented flight heritage.

---

## 6. 15-minute review path

1. This file  
2. **AKOS** → IDENTITY · GOVERNANCE  
3. **pro-code**  
4. **spacex-thermal-protection**  
5. **spacex-telemetry** or **spacex-launch-sequencer**  
6. Hire pack: honest assessment + outreach draft B (SpaceX)  

---

## 7. Policy

| Rule | Statement |
|------|-----------|
| Litigation | Never linked here |
| Employment | No SpaceX/xAI employment claim |
| Metrics | No invented scores |
| Visibility | Private-first GitHub may 401 without access |

---

*SpaceX-first · shark-laser · real exhibits · AKOS at the root*
"""


def build_az() -> str:
    return f"""# A–Z Campaign — SpaceX Shark-Laser (Master Mode)

Operational path using **AZOP** + toolbelt + job surfaces.  
Full AZOP: [`../toolbelt/AZOP_ORCHESTRATION.md`](../toolbelt/AZOP_ORCHESTRATION.md)

| Step | Wave | Action |
|-----:|------|--------|
| **A** | Boot | token-saver · sequential_thinking · humanizer final only |
| **B** | Map | Open `jobapp_whole/registry.json` · ecosystem_map |
| **C** | MICROWAVE | explore subagents (read-only) on spacex-* + AKOS READMEs |
| **D** | CORE-THINK | Synth bottleneck map → this showcase |
| **E** | Generate | `python3 generate_showcase.py` |
| **F** | Verify | `python3 test_showcase.py` |
| **G** | VIPER | Worktree-only if editing helix code; never invent heritage |
| **H** | Whole | Confirm exhibits `integrated` in PASS_LOG |
| **I** | Hire pack | Align resume + outreach Draft B to this entry |
| **J** | Toolbelt | Doctor + AZOP waves if multi-repo deep dive |
| **K** | Proof | Launch capture to SCRATCH (gating) |
| **L–Z** | Ship readiness | Human review → optional private share / back-door outreach |

**Parent stays lean:** children return facts + pointers; large bodies stay on disk.

**Surfaces**

| Surface | Path |
|---------|------|
| This showcase | `jobapp_spacex_sharklaser/SPACEX_SHARKLASER_SHOWCASE.md` |
| Hire whole | `jobapp_whole/WHOLE.md` |
| Hire pack | `jobapp_hire_package/` |
| AZOP | `toolbelt/AZOP_ORCHESTRATION.md` |

Generated: {datetime.now(timezone.utc).strftime("%Y-%m-%d UTC")}
"""


def main() -> int:
    data = load_registry()
    show = build_showcase(data)
    az = build_az()
    for text, name in ((show, "showcase"), (az, "az")):
        if LEGAL.search(text):
            raise SystemExit(f"legal token in {name}")
        for a in ("AKOS", "pro-code", "SpaceX", "spacex-thermal-protection"):
            if a not in text and name == "showcase":
                raise SystemExit(f"missing {a}")
    if "shark-laser" not in show.lower() and "shark-laser" not in show:
        if "Shark-Laser" not in show:
            raise SystemExit("missing shark-laser positioning")
    OUT.write_text(show)
    AZ.write_text(az)
    print(f"wrote {OUT.name} + {AZ.name} bytes={OUT.stat().st_size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
