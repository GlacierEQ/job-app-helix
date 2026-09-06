#!/usr/bin/env python3
"""Rank the 53-company innovation fleet by impact and expose upgrade queues."""
from __future__ import annotations
import argparse,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
DEFAULT=ROOT/"status"/"company-innovation-impact-upgrade-2026-08-30.json"
def load(path:Path): return json.loads(path.read_text())
def main():
 p=argparse.ArgumentParser();p.add_argument("--manifest",type=Path,default=DEFAULT);p.add_argument("--top",type=int,default=15);p.add_argument("--kind");p.add_argument("--protected",action="store_true");a=p.parse_args(); rows=load(a.manifest)["rows"]
 if a.kind: rows=[r for r in rows if r["kind"]==a.kind]
 if a.protected: rows=[r for r in rows if r["protected_prior_wave"]]
 rows=sorted(rows,key=lambda r:(r["design_impact_score"],r["long_term_leverage"],r["cross_repo_compounding"]),reverse=True)
 for r in rows[:a.top]: print(f'{r["design_impact_score"]:5.3f}  {r["company"]:16} {r["innovation"]} :: {r["next_frontier"]}')
 return 0
if __name__=="__main__": raise SystemExit(main())
