#!/usr/bin/env python3
"""Build WHOLE.md + REGISTRY.md from registry.json — one beautiful hire whole."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REG = ROOT / "registry.json"
LEGAL = re.compile(
    r"1FDV|FEDERAL-WARFARE|SUPERLUMINAL|cathedrals_cases_distill",
    re.I,
)


def load() -> dict:
    return json.loads(REG.read_text())


def rows(items: list[dict]) -> str:
    lines = [
        "| ID | Status | Family | Role | Pointer | AKOS |",
        "|----|--------|--------|------|---------|------|",
    ]
    for it in items:
        lines.append(
            f"| **{it['id']}** | `{it['status']}` | {it['family']} | {it['role']} | "
            f"[{it['id']}]({it['pointer']}) | {it.get('akos_bridge', '—')} |"
        )
    return "\n".join(lines)


def build_registry_md(data: dict) -> str:
    all_items = data["frameworks"] + data["exhibits"]
    integrated = [i for i in all_items if i["status"] == "integrated"]
    deferred = [i for i in all_items if i["status"] == "deferred"]
    blocked = [i for i in all_items if i["status"] == "blocked"]
    return f"""# Exhibit registry — GlacierEQ Hire Whole

**Pass-reviewed one-by-one.** Status is explicit: `integrated` · `deferred` · `blocked`.  
Litigation material is **excluded** (never registered).

- Generated: {datetime.now(timezone.utc).strftime("%Y-%m-%d UTC")}
- Source: `registry.json`
- Counts: integrated **{len(integrated)}** · deferred **{len(deferred)}** · blocked **{len(blocked)}**
- One-by-one audit: [`PASS_LOG.md`](./PASS_LOG.md)

## Integrated

{rows(integrated)}

## Deferred (later pass)

{rows(deferred) if deferred else "_none_"}

## Blocked

{rows(blocked) if blocked else "_none_"}

## Policy
- private-first links OK  
- no fake metrics / employment claims  
- AKOS is canonical home of the whole  
"""


def build_pass_log(data: dict) -> str:
    """Ordered one-by-one pass audit — each item becomes part of the whole."""
    all_items = sorted(
        data["frameworks"] + data["exhibits"],
        key=lambda x: (x.get("pass") or 999, x["id"]),
    )
    lines = [
        "# Pass log — one by one into the beautiful whole",
        "",
        "Each row is a deliberate pass: role · status · pointer · AKOS home.",
        f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d UTC')}",
        "",
        "| # | ID | Status | Family | Role | Pointer |",
        "|--:|----|--------|--------|------|---------|",
    ]
    for it in all_items:
        n = it.get("pass") or "—"
        lines.append(
            f"| {n} | **{it['id']}** | `{it['status']}` | {it['family']} | {it['role']} | "
            f"[{it['id']}]({it['pointer']}) |"
        )
    all_items = data["frameworks"] + data["exhibits"]
    n_int = sum(1 for i in all_items if i.get("status") == "integrated")
    n_def = sum(1 for i in all_items if i.get("status") == "deferred")
    twin_ids = [
        i["id"]
        for i in all_items
        if i["id"].endswith("-alpha") or i["id"].endswith("-omega")
    ]
    twin_int = [
        i["id"]
        for i in all_items
        if (i["id"].endswith("-alpha") or i["id"].endswith("-omega"))
        and i.get("status") == "integrated"
    ]
    twin_def = [
        i["id"]
        for i in all_items
        if (i["id"].endswith("-alpha") or i["id"].endswith("-omega"))
        and i.get("status") == "deferred"
    ]
    if twin_def and not twin_int:
        twin_rule = (
            "4. Helix alpha/omega twins are **deferred** until a deeper file pass "
            f"({', '.join(twin_def)})."
        )
    elif twin_int and not twin_def:
        twin_rule = (
            "4. Helix alpha/omega twins are **integrated** "
            f"({', '.join(twin_int)})."
        )
    elif twin_int and twin_def:
        twin_rule = (
            f"4. Helix twins: integrated {twin_int}; deferred {twin_def}."
        )
    else:
        twin_rule = "4. No alpha/omega twin exhibits registered."

    lines.extend(
        [
            "",
            "## Composition rule",
            "",
            "1. **AKOS** is root (pass 1).",
            "2. Frameworks next (pro-code, token_saver, mastermind, AEON).",
            "3. Pro-* sample, then Colossus/xAI pillars, then full SpaceX helix, then APEX/MCP/NVIDIA/Notion/Microsoft, then hub surfaces.",
            twin_rule,
            f"5. Status counts: integrated **{n_int}** · deferred **{n_def}**.",
            "6. Litigation never enters this log.",
            "",
            f"See also: [`WHOLE.md`](./WHOLE.md) · [`REGISTRY.md`](./REGISTRY.md) · "
            f"[`../jobapp_showcase/SHOWCASE.md`](../jobapp_showcase/SHOWCASE.md) · "
            f"[`../jobapp_hire_package/README.md`](../jobapp_hire_package/README.md)",
            "",
        ]
    )
    return "\n".join(lines)


def build_whole_md(data: dict) -> str:
    fw = data["frameworks"]
    ex = data["exhibits"]
    by_fam: dict[str, list] = {}
    for e in ex:
        by_fam.setdefault(e["family"], []).append(e)

    def fam_block(name: str) -> str:
        items = by_fam.get(name, [])
        if not items:
            return ""
        lines = [f"### {name}", ""]
        for it in items:
            mark = "✓" if it["status"] == "integrated" else "…"
            lines.append(
                f"- {mark} **{it['id']}** — {it['role']} · [{it['pointer']}]({it['pointer']}) · `{it['status']}`"
            )
        lines.append("")
        return "\n".join(lines)

    fw_table = rows(fw)
    return f"""# GlacierEQ Hire Whole

**One system.** Not a pile of repos — an operating whole: **AKOS** + **pro-code** + **Pro-*** motions + domain families (xAI/Colossus · SpaceX · agents · GPU · Notion ops).

> Private-first portfolio. Litigation excluded. No invented metrics or employment claims.  
> Generated: {datetime.now(timezone.utc).strftime("%Y-%m-%d UTC")} · registry: [`REGISTRY.md`](./REGISTRY.md) · data: `registry.json`

---

## How the whole fits

```
                    ┌──────────── AKOS ────────────┐
                    │  identity · governance · map │
                    └──────────────┬───────────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              ▼                    ▼                    ▼
         pro-code            token_saver           mastermind
        standards            efficiency            control plane
              │                    │                    │
              └────────────────────┼────────────────────┘
                                   ▼
              ┌────────────────────────────────────────┐
              │     Pro-*  ·  APEX  ·  MCP agents        │
              └────────────────────────────────────────┘
                     │                    │
           xAI / Colossus              SpaceX helix
        cooling·energy·servers      thermal·orbital·telem
```

---

## Frameworks (operating core)

{fw_table}

---

## Motion families (company-aligned exhibits)

{fam_block("xAI/Colossus")}
{fam_block("SpaceX")}
{fam_block("Pro-*")}
{fam_block("APEX")}
{fam_block("Agents/MCP")}
{fam_block("NVIDIA")}
{fam_block("Notion")}
{fam_block("hub")}

---

## Related surfaces (same whole)

| Surface | Path |
|---------|------|
| Framework showcase | [`../jobapp_showcase/SHOWCASE.md`](../jobapp_showcase/SHOWCASE.md) |
| Musk-orbit hire pack | [`../jobapp_hire_package/README.md`](../jobapp_hire_package/README.md) |
| Per-item registry | [`REGISTRY.md`](./REGISTRY.md) |
| One-by-one pass log | [`PASS_LOG.md`](./PASS_LOG.md) |
| GitHub hub | https://github.com/GlacierEQ/job-application |

---

## Reading order (beautiful whole in 15 minutes)

1. This file (structure)  
2. **PASS_LOG** — see every piece enter the whole  
3. **AKOS** → IDENTITY · GOVERNANCE · REPOS  
4. **pro-code**  
5. **xai-colossus-cooling** + **spacex-thermal-protection**  
6. **Pro-comet-agent**  
7. Hire pack resume + honest assessment  

---

## Status legend

| Status | Meaning |
|--------|---------|
| `integrated` | Pass-reviewed into the whole; role + pointer + AKOS home |
| `deferred` | Job-related; later pass (when any remain) |
| `blocked` | Explicitly not for hire surface |

---

*One whole · many motions · AKOS at the root · each piece logged in PASS_LOG*
"""


def main() -> int:
    data = load()
    blob = json.dumps(data)
    if LEGAL.search(blob):
        raise SystemExit("legal token in registry.json")
    reg_md = build_registry_md(data)
    whole_md = build_whole_md(data)
    pass_md = build_pass_log(data)
    for text, name in ((reg_md, "REGISTRY.md"), (whole_md, "WHOLE.md"), (pass_md, "PASS_LOG.md")):
        if LEGAL.search(text):
            raise SystemExit(f"legal token in {name}")
        if "AKOS" not in text or "pro-code" not in text:
            raise SystemExit(f"missing anchors in {name}")
    (ROOT / "REGISTRY.md").write_text(reg_md)
    (ROOT / "WHOLE.md").write_text(whole_md)
    (ROOT / "PASS_LOG.md").write_text(pass_md)
    # stamp
    all_items = data["frameworks"] + data["exhibits"]
    integrated = sum(1 for i in all_items if i["status"] == "integrated")
    deferred = sum(1 for i in all_items if i["status"] == "deferred")
    (ROOT / "STAMP.md").write_text(
        f"# Whole stamp\n\n- ts: {datetime.now(timezone.utc).isoformat()}\n"
        f"- integrated: {integrated}\n- deferred: {deferred}\n"
        f"- total_items: {len(all_items)}\n"
        f"- entry: WHOLE.md\n- registry: REGISTRY.md\n- pass_log: PASS_LOG.md\n"
    )
    print(
        f"wrote WHOLE.md + REGISTRY.md + PASS_LOG.md "
        f"integrated={integrated} deferred={deferred}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
