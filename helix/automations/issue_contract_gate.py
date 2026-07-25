#!/usr/bin/env python3
"""Issue Contract Gate — DONE iff the leaf solves its stated pain.

No architecture theater. Each contract:
  pain, claim, proof (runnable), done when proof exits 0.

Usage:
  python3 issue_contract_gate.py
  python3 issue_contract_gate.py --only openai-reasoning-kv-sentinel
  python3 issue_contract_gate.py --write-missing   # scaffold only for leaves without contract
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HOME = Path.home()
REPOS = HOME / "job-app" / "repos"
JOB = HOME / "job-app"
CONTRACTS = JOB / "helix" / "issue_contracts.json"
STATE = HOME / "GlacierEQ_Swarm" / "state"
OUT = STATE / "issue_contract_gate_last.json"
PROOFS = JOB / "helix" / "proofs"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_contracts() -> dict:
    return json.loads(CONTRACTS.read_text(encoding="utf-8"))


def run_proof(cmd: list[str], cwd: Path, timeout: int = 120) -> dict:
    t0 = time.perf_counter()
    try:
        r = subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "ok": r.returncode == 0,
            "returncode": r.returncode,
            "seconds": round(time.perf_counter() - t0, 3),
            "tail": ((r.stdout or "") + (r.stderr or ""))[-800:],
        }
    except Exception as e:
        return {"ok": False, "error": str(e)[:300], "seconds": round(time.perf_counter() - t0, 3)}


def write_repo_contract_md(repo: str, c: dict) -> None:
    path = REPOS / repo / "ISSUE_CONTRACT.md"
    body = f"""# Issue Contract — `{repo}`

## Pain
{c['pain']}

## Claim
{c['claim']}

## Proof
```bash
{c['proof_display']}
```

## Done when
Proof exits 0. Architecture (strand/integrity/helix) is **not** a substitute for this proof.

## Anti-claim
{c.get('anti_claim', 'Does not claim production deployment at the named company.')}
"""
    path.write_text(body, encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", action="append", default=[])
    ap.add_argument("--write-md", action="store_true", help="Write ISSUE_CONTRACT.md into each repo")
    args = ap.parse_args()

    data = load_contracts()
    contracts = data["contracts"]
    if args.only:
        contracts = [c for c in contracts if c["repo"] in args.only]

    results = []
    for c in contracts:
        repo = c["repo"]
        repo_path = REPOS / repo
        if not repo_path.is_dir():
            results.append({"repo": repo, "ok": False, "error": "missing_repo"})
            continue

        if args.write_md:
            write_repo_contract_md(repo, c)

        # proof: list of argv; {REPO} substituted
        proof = c["proof"]
        cmd = [p.replace("{REPO}", str(repo_path)).replace("{PROOFS}", str(PROOFS)) for p in proof]
        # first token may be python3
        if cmd[0] == "python3":
            cmd[0] = sys.executable

        pr = run_proof(cmd, cwd=repo_path if c.get("cwd") != "proofs" else PROOFS)
        results.append(
            {
                "repo": repo,
                "pain": c["pain"][:120],
                "ok": pr.get("ok", False),
                "proof": pr,
            }
        )

    ok_n = sum(1 for r in results if r.get("ok"))
    fail = [r["repo"] for r in results if not r.get("ok")]
    report = {
        "ts": utc_now(),
        "protocol": "ISSUE_CONTRACT — done iff proof(pain)==green",
        "law": "Each leaf solves the issue it claims. Map/mesh/strand ≠ done.",
        "ok": len(fail) == 0,
        "passed": ok_n,
        "failed": fail,
        "total": len(results),
        "results": results,
    }
    STATE.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": report["ok"],
                "passed": ok_n,
                "total": len(results),
                "failed": fail,
                "ptr": str(OUT),
            },
            indent=2,
        )
    )
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
