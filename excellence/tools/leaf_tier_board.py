#!/usr/bin/env python3
"""Emit leaf tier board for pipsqueak→bodybuilder pipeline (no LLM).

Usage:
  python3 excellence/tools/leaf_tier_board.py
  python3 excellence/tools/leaf_tier_board.py --top-pips 20
"""
from __future__ import annotations

import argparse
import contextlib
import json
from datetime import UTC, datetime
from pathlib import Path

REPOS = Path.home() / "job-app" / "repos"
OUT = Path.home() / "job-app" / "excellence" / "grades" / "leaf_tier_board.json"


def tier_of(loc: int, tests: int) -> str:
    if loc >= 400 and tests >= 8:
        return "bodybuilder"
    if loc >= 400 and tests >= 5:
        return "bodybuilder-ish"
    if loc >= 150 and tests >= 3:
        return "gym"
    if loc >= 50:
        return "pipsqueak"
    return "seed"


def analyze(p: Path) -> dict:
    py = [
        f
        for f in p.rglob("*.py")
        if ".git" not in f.parts
        and "venv" not in f.parts
        and "__pycache__" not in f.parts
        and "node_modules" not in f.parts
    ]
    tests = [f for f in py if "test" in f.name.lower() or "/tests/" in str(f)]
    # count test methods lightly
    tmethods = 0
    for f in tests:
        with contextlib.suppress(OSError):
            tmethods += f.read_text(errors="replace").count("def test_")
    loc = 0
    for f in py[:120]:
        with contextlib.suppress(OSError), open(f, "rb") as fh:
            loc += sum(1 for _ in fh)
    go = (p / "go").is_dir() or any(p.glob("**/*_test.go"))
    native = (p / "native").is_dir()
    ts = (p / "ts").is_dir()
    return {
        "name": p.name,
        "loc_py": loc,
        "py_files": len(py),
        "test_files": len(tests),
        "test_methods": tmethods,
        "tier": tier_of(loc, tmethods),
        "has_license": (p / "LICENSE").is_file(),
        "has_ci": (p / ".github" / "workflows").is_dir(),
        "has_babel_md": (p / "BABEL.md").is_file(),
        "has_go": go,
        "has_native_c": native,
        "has_ts": ts,
        "has_issue_contract": (p / "ISSUE_CONTRACT.md").is_file(),
        "has_quality": (p / "QUALITY.md").is_file(),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--top-pips", type=int, default=0, help="Print N thinnest pipsqueaks")
    args = ap.parse_args()
    rows = []
    for p in sorted(REPOS.iterdir()):
        if not p.is_dir() or p.name.startswith("."):
            continue
        rows.append(analyze(p))
    rows.sort(key=lambda r: (r["tier"], r["loc_py"], r["name"]))
    from collections import Counter

    counts = Counter(r["tier"] for r in rows)
    board = {
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%MZ"),
        "counts": dict(counts),
        "dod": "excellence/framework/PIP_TO_BODYBUILDER_PIPELINE.md",
        "leaves": rows,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(board, indent=2) + "\n")
    print(f"wrote {OUT} total={len(rows)} counts={dict(counts)}")
    if args.top_pips:
        pips = [r for r in rows if r["tier"] in ("pipsqueak", "seed")]
        pips.sort(key=lambda r: (r["loc_py"], r["test_methods"]))
        print("top pips:")
        for r in pips[: args.top_pips]:
            print(f"  {r['name']:45} loc={r['loc_py']:4} tests={r['test_methods']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
