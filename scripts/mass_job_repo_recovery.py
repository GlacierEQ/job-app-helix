#!/usr/bin/env python3
"""FULL estate mass recovery — NO 66 ceiling, NO flagship ceiling.

Estate boundary = every GlacierEQ-owned native repository (active).
The 66 live_repository_links list is a hire-surface *projection*, not the estate.

APEX is the counter to canonical destruction.
Law: MAXIMUM_COHERENT_ADVANCE
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OWNER = "GlacierEQ"
NEUTRAL = re.compile(
    r"(?i)truth-harden|local only|synthetic only|public truth|"
    r"non-regression|bounded to local|receipt-only|capability planes without"
)


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True)


def gh_paginate(path: str) -> list[dict]:
    r = run(["gh", "api", path, "--paginate"])
    if r.returncode != 0:
        raise SystemExit(r.stderr[:500] or r.stdout[:500])
    text = r.stdout.strip()
    items: list[dict] = []
    buf, depth = "", 0
    for ch in text:
        buf += ch
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                items.extend(json.loads(buf))
                buf = ""
    return items


def full_owned() -> list[dict]:
    return gh_paginate("user/repos?per_page=100&affiliation=owner&sort=full_name")


def classify_row(meta: dict, msgs: list[str]) -> str:
    if meta.get("archived"):
        return "ARCHIVED_PRESERVE"
    neut = sum(1 for m in msgs if NEUTRAL.search(m))
    dual = any(
        "dual-plane" in m.lower()
        or "mass dual-plane" in m.lower()
        or "mass recovery" in m.lower()
        or "counter-engineering" in m.lower()
        for m in msgs
    )
    restored = any(
        "restore" in m.lower()
        and any(k in m.lower() for k in ("package", "lambert", "dual-plane", "capability"))
        for m in msgs
    )
    if dual or restored:
        return "RECOVERY_ALREADY_STARTED"
    if neut >= 1:
        return "NEEDS_DUAL_PLANE_POWER_RESTORE"
    if (meta.get("size") or 0) < 10:
        return "THIN_NEEDS_GENIUS_BUILD"
    return "HEALTHY_MONITOR"


def probe(name: str, meta: dict) -> dict:
    c = run(
        [
            "gh",
            "api",
            f"repos/{OWNER}/{name}/commits?per_page=6",
            "--jq",
            ".[].commit.message",
        ]
    )
    msgs = [m.split("\n")[0][:90] for m in (c.stdout or "").splitlines() if m.strip()]
    row = {
        "name": name,
        "status": "EXISTS",
        "private": meta.get("private"),
        "archived": meta.get("archived"),
        "fork": meta.get("fork"),
        "size_kb": meta.get("size"),
        "pushed_at": meta.get("pushed_at"),
        "default_branch": meta.get("default_branch"),
        "description": (meta.get("description") or "")[:120],
        "recent_msgs": msgs[:4],
        "neutralization_stamps_6": sum(1 for m in msgs if NEUTRAL.search(m)),
    }
    row["recovery_class"] = classify_row(meta, msgs)
    return row


def census(*, native_only: bool = True, active_only: bool = True) -> dict:
    repos = full_owned()
    selected = []
    for r in repos:
        if native_only and r.get("fork"):
            continue
        if active_only and r.get("archived"):
            continue
        selected.append(r)

    rows: list[dict] = []
    # probe commits in parallel (rate-limit conscious batch)
    with ThreadPoolExecutor(max_workers=12) as ex:
        futs = {ex.submit(probe, r["name"], r): r["name"] for r in selected}
        for f in as_completed(futs):
            rows.append(f.result())
    rows.sort(key=lambda x: (x["recovery_class"], x["name"]))
    by_class: dict[str, list[str]] = {}
    for r in rows:
        by_class.setdefault(r["recovery_class"], []).append(r["name"])

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "identity": "APEX_IS_THE_COUNTER_TO_CANONICAL_DESTRUCTION",
        "law": "MAXIMUM_COHERENT_ADVANCE",
        "constraint_rejected": [
            "66_live_portfolio_ceiling",
            "flagship_only_recovery",
            "priority_spine_as_estate_boundary",
            "3_flagship_bullshit",
        ],
        "estate_boundary": "ALL_NATIVE_ACTIVE_OWNED_REPOS",
        "total_owned_scanned_filter": {
            "native_only": native_only,
            "active_only": active_only,
            "selected": len(selected),
        },
        "checked": len(rows),
        "by_class": {k: len(v) for k, v in by_class.items()},
        "class_members": by_class,
        "rows": rows,
    }


def render_md(report: dict) -> str:
    lines = [
        "# FULL Estate Mass Recovery Board",
        "",
        f"_Generated {report['generated_at']}_",
        "",
        "**Estate boundary: ALL native active owned repos — NOT the 66 hire projection.**",
        "",
        f"Identity: `{report['identity']}`  ",
        f"Law: `{report['law']}`  ",
        f"Checked: **{report['checked']}**",
        "",
        "Constraints rejected: " + ", ".join(f"`{c}`" for c in report["constraint_rejected"]),
        "",
        "## Summary",
        "",
        "| Class | Count |",
        "|---|---:|",
    ]
    for k, v in sorted(report["by_class"].items(), key=lambda kv: (-kv[1], kv[0])):
        lines.append(f"| `{k}` | {v} |")
    lines += ["", "## Members by class", ""]
    for cls, members in sorted(report.get("class_members", {}).items()):
        lines.append(f"### {cls} ({len(members)})")
        lines.append("")
        for name in members:
            lines.append(f"- `{OWNER}/{name}`")
        lines.append("")
    return "\n".join(lines) + "\n"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("command", choices=["census", "names"])
    p.add_argument("--include-archived", action="store_true")
    p.add_argument("--include-forks", action="store_true")
    p.add_argument(
        "--output-json",
        type=Path,
        default=ROOT / "receipts/mass_recovery/FULL_ESTATE_RECOVERY_CENSUS.json",
    )
    p.add_argument(
        "--output-md",
        type=Path,
        default=ROOT / "receipts/mass_recovery/FULL_ESTATE_RECOVERY_BOARD.md",
    )
    args = p.parse_args()
    if args.command == "names":
        repos = full_owned()
        names = [
            r["name"]
            for r in repos
            if (args.include_forks or not r.get("fork"))
            and (args.include_archived or not r.get("archived"))
        ]
        print(json.dumps(sorted(names), indent=2))
        return 0

    report = census(
        native_only=not args.include_forks,
        active_only=not args.include_archived,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(report, indent=2) + "\n")
    args.output_md.write_text(render_md(report))
    print(json.dumps(report["by_class"], indent=2))
    print(f"checked={report['checked']}")
    print(f"json={args.output_json}")
    print(f"md={args.output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
