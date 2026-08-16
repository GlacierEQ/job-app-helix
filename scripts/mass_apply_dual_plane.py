#!/usr/bin/env python3
"""Apply dual-plane recovery stamp to a list of GlacierEQ repos.

Creates branch apex/mass-dual-plane-recovery, updates machine/capabilities
when present, adds RECOVERY.md, commits, pushes, opens PR.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

OWNER = "GlacierEQ"
BRANCH = "apex/mass-dual-plane-recovery"


def run(cmd, cwd=None):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


def apply_one(name: str, work: Path) -> dict:
    dest = work / name
    if dest.exists():
        run(["rm", "-rf", str(dest)])
    cl = run(["git", "clone", "--depth=40", f"https://github.com/{OWNER}/{name}.git", str(dest)])
    if cl.returncode != 0:
        return {"name": name, "ok": False, "err": cl.stderr[:200]}
    run(["git", "checkout", "-B", BRANCH], cwd=dest)
    # recovery marker
    rec = dest / "APEX_RECOVERY.md"
    rec.write_text(
        f"""# APEX Mass Recovery

**Repository:** `{OWNER}/{name}`  
**Identity:** APEX is the counter to canonical destruction  
**Law:** MAXIMUM_COHERENT_ADVANCE  
**Program:** job-app-helix mass job-repo recovery

## Dual-plane rule

1. **VERIFIED** — exact-head proven claims (may be local/lab-scoped)  
2. **IMPLEMENTED** — real code paths retained; not deleted to green a smaller harness  
3. **TARGET** — north-star architecture preserved

Governance routes power. It does not amputate mechanisms.

## Status

This stamp places the repository on the mass recovery board. Follow-on PRs expand
implemented power (Genius Engine invent → implement → test).
"""
    )
    cap = dest / "machine" / "capabilities.json"
    if cap.is_file():
        try:
            data = json.loads(cap.read_text())
        except Exception:
            data = {}
        data.setdefault("recovery", {})
        data["recovery"].update(
            {
                "identity": "APEX_IS_THE_COUNTER_TO_CANONICAL_DESTRUCTION",
                "law": "MAXIMUM_COHERENT_ADVANCE",
                "program": "mass-job-repo-recovery",
                "dual_plane": True,
            }
        )
        planes = data.setdefault("planes", {})
        planes.setdefault("verified", data.get("capabilities") or [])
        planes.setdefault(
            "implemented",
            list(
                dict.fromkeys(
                    (planes.get("implemented") or [])
                    + ["apex-mass-recovery-enrolled"]
                )
            ),
        )
        caps = list(data.get("capabilities") or [])
        if "apex-mass-recovery-enrolled" not in caps:
            caps.append("apex-mass-recovery-enrolled")
        data["capabilities"] = caps
        cap.write_text(json.dumps(data, indent=2) + "\n")
    run(["git", "add", "-A"], cwd=dest)
    st = run(["git", "status", "--porcelain"], cwd=dest)
    if not st.stdout.strip():
        return {"name": name, "ok": True, "skipped": True, "reason": "no changes"}
    msg = """APEX: mass dual-plane recovery enrollment

Enroll repository in job-ecosystem mass recovery under dual-plane truth.
Do not amputate mechanisms to satisfy a smaller proof harness.

Identity: APEX is the counter to canonical destruction
Law: MAXIMUM_COHERENT_ADVANCE
"""
    run(["git", "commit", "-m", msg], cwd=dest)
    push = run(["git", "push", "-u", "origin", BRANCH], cwd=dest)
    if push.returncode != 0:
        return {"name": name, "ok": False, "err": push.stderr[:300]}
    pr = run(
        [
            "gh",
            "pr",
            "create",
            "--repo",
            f"{OWNER}/{name}",
            "--head",
            BRANCH,
            "--base",
            "main",
            "--title",
            "APEX: mass dual-plane recovery enrollment",
            "--body",
            "Mass job-repo recovery enrollment. Dual-plane truth; power routing not amputation. Part of GlacierEQ/job-app-helix mass recovery program.",
        ],
        cwd=dest,
    )
    return {
        "name": name,
        "ok": pr.returncode == 0,
        "pr": (pr.stdout or pr.stderr).strip(),
        "push_err": push.stderr[:120] if push.returncode else None,
    }


def main() -> int:
    names = json.loads(Path(sys.argv[1]).read_text()) if len(sys.argv) > 1 else []
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 15
    names = names[:limit]
    work = Path(tempfile.mkdtemp(prefix="mass-dual-"))
    results = []
    for name in names:
        print("===", name, flush=True)
        results.append(apply_one(name, work))
        print(results[-1], flush=True)
    out = Path("receipts/mass_recovery/MASS_DUAL_PLANE_BATCH.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2) + "\n")
    ok = sum(1 for r in results if r.get("ok"))
    print(f"done ok={ok}/{len(results)} receipt={out}")
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
