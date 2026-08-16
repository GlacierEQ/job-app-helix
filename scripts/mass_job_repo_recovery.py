#!/usr/bin/env python3
"""Mass job-repo recovery census and dual-plane power routing.

APEX is the counter to canonical destruction.
Law: MAXIMUM_COHERENT_ADVANCE

Modes:
  census   — check every live_repository_links + critical ownership repo
  classify — assign recovery class per leaf
  report   — write markdown board + JSON receipt

Does not force-push. Optional --apply-dual-plane clones and opens PRs
(only with --apply and explicit --limit).
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
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


def load_names() -> list[str]:
    names: set[str] = set()
    links = json.loads((ROOT / "manifests/live_repository_links.json").read_text())
    for r in links.get("repositories") or []:
        names.add(str(r))
    for p in (
        "manifests/library_priority_spine.json",
        "manifests/job_app_repository_ownership.json",
        "manifests/flagship_registry.json",
    ):
        data = json.loads((ROOT / p).read_text())
        repos = data.get("repositories") or data.get("flagships") or []
        for item in repos:
            if isinstance(item, str):
                names.add(item.split("/")[-1])
            elif isinstance(item, dict):
                repo = item.get("repository") or item.get("name")
                if repo:
                    names.add(str(repo).split("/")[-1])
    # critical extras
    for extra in (
        "job-app",
        "monolith",
        "Pro_Code",
        "FILEBOSS",
        "make-it-heavy",
        "megamind",
        "JOB-RESUME-BUILDER-",
        "Pro-DOCTOR-STRANGE",
        "glaciereq-excellence-core",
    ):
        names.add(extra)
    return sorted(names)


def gh_repo(name: str) -> dict:
    r = run(["gh", "api", f"repos/{OWNER}/{name}"])
    if r.returncode != 0:
        return {"name": name, "status": "MISSING", "err": (r.stderr or "")[:160]}
    meta = json.loads(r.stdout)
    c = run(
        [
            "gh",
            "api",
            f"repos/{OWNER}/{name}/commits?per_page=8",
            "--jq",
            ".[].commit.message",
        ]
    )
    msgs = [m.split("\n")[0][:90] for m in (c.stdout or "").splitlines() if m.strip()]
    neut = sum(1 for m in msgs if NEUTRAL.search(m))
    dual = any("dual-plane" in m.lower() or "counter-engineering" in m.lower() or "counter neutralization" in m.lower() for m in msgs)
    restored = any(
        "restore" in m.lower() and ("package" in m.lower() or "lambert" in m.lower() or "dual-plane" in m.lower())
        for m in msgs
    )
    return {
        "name": name,
        "status": "EXISTS",
        "private": meta.get("private"),
        "visibility": meta.get("visibility"),
        "archived": meta.get("archived"),
        "disabled": meta.get("disabled"),
        "fork": meta.get("fork"),
        "size_kb": meta.get("size"),
        "pushed_at": meta.get("pushed_at"),
        "default_branch": meta.get("default_branch"),
        "description": (meta.get("description") or "")[:120],
        "html_url": meta.get("html_url"),
        "recent_msgs": msgs[:5],
        "neutralization_stamps_8": neut,
        "has_dual_plane_commit": dual,
        "has_restore_commit": restored,
    }


def classify(row: dict) -> str:
    if row.get("status") == "MISSING":
        return "DELETED_OR_NEVER_EXISTED"
    if row.get("archived"):
        return "ARCHIVED_PRESERVE"
    if row.get("has_dual_plane_commit") or row.get("has_restore_commit"):
        return "RECOVERY_ALREADY_STARTED"
    if (row.get("neutralization_stamps_8") or 0) >= 1:
        return "NEEDS_DUAL_PLANE_POWER_RESTORE"
    if (row.get("size_kb") or 0) < 15:
        return "THIN_NEEDS_GENIUS_BUILD"
    return "HEALTHY_MONITOR"


def census() -> dict:
    names = load_names()
    rows = []
    with ThreadPoolExecutor(max_workers=18) as ex:
        futs = {ex.submit(gh_repo, n): n for n in names}
        for f in as_completed(futs):
            row = f.result()
            row["recovery_class"] = classify(row)
            rows.append(row)
    rows.sort(key=lambda r: (r["recovery_class"], r["name"]))
    by_class: dict[str, list] = {}
    for r in rows:
        by_class.setdefault(r["recovery_class"], []).append(r["name"])
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "identity": "APEX_IS_THE_COUNTER_TO_CANONICAL_DESTRUCTION",
        "law": "MAXIMUM_COHERENT_ADVANCE",
        "owner": OWNER,
        "checked": len(rows),
        "by_class": {k: len(v) for k, v in by_class.items()},
        "class_members": by_class,
        "missing": [r for r in rows if r["status"] == "MISSING"],
        "rows": rows,
    }


def render_md(report: dict) -> str:
    lines = [
        "# Mass Job-Repo Recovery Board",
        "",
        f"_Generated {report['generated_at']}_",
        "",
        f"**Identity:** {report['identity']}  ",
        f"**Law:** {report['law']}  ",
        f"**Checked:** {report['checked']}",
        "",
        "## Summary by class",
        "",
        "| Class | Count |",
        "|---|---:|",
    ]
    for k, v in sorted(report["by_class"].items(), key=lambda kv: (-kv[1], kv[0])):
        lines.append(f"| `{k}` | {v} |")
    lines += ["", "## Missing / deleted", ""]
    missing = report.get("missing") or []
    if not missing:
        lines.append("_None. No job-ecosystem GitHub repositories in the recovery set are deleted._")
    else:
        for m in missing:
            lines.append(f"- `{m['name']}` — {m.get('err','')[:80]}")
    lines += ["", "## Class members", ""]
    for cls, members in sorted(report.get("class_members", {}).items()):
        lines.append(f"### {cls} ({len(members)})")
        lines.append("")
        for name in members:
            lines.append(f"- `{OWNER}/{name}`")
        lines.append("")
    lines += [
        "## Recovery order",
        "",
        "1. Confirm no DELETED (restore from backup/donor if any)",
        "2. `NEEDS_DUAL_PLANE_POWER_RESTORE` — invent + implement (Genius Engine)",
        "3. `THIN_NEEDS_GENIUS_BUILD` — invent profound mechanism",
        "4. `RECOVERY_ALREADY_STARTED` — finish merge/CI",
        "5. `ARCHIVED_PRESERVE` — do not delete; optional unarchive by operator",
        "6. `HEALTHY_MONITOR` — anti-neutralization gate only",
        "",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("command", choices=["census", "report"])
    p.add_argument("--output-json", type=Path, default=ROOT / "receipts/mass_recovery/MASS_RECOVERY_CENSUS.json")
    p.add_argument("--output-md", type=Path, default=ROOT / "receipts/mass_recovery/MASS_RECOVERY_BOARD.md")
    args = p.parse_args()
    report = census()
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(report, indent=2) + "\n")
    md = render_md(report)
    args.output_md.write_text(md)
    print(json.dumps(report["by_class"], indent=2))
    print(f"missing={len(report['missing'])}")
    print(f"json={args.output_json}")
    print(f"md={args.output_md}")
    if report["missing"]:
        for m in report["missing"]:
            print("MISSING", m["name"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
