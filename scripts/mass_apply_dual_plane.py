#!/usr/bin/env python3
"""Mass dual-plane enrollment across ANY list of GlacierEQ repos (full estate)."""
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
    meta = run(["gh", "api", f"repos/{OWNER}/{name}"])
    if meta.returncode != 0:
        return {"name": name, "ok": False, "err": "repo missing"}
    info = json.loads(meta.stdout)
    default = info.get("default_branch") or "main"
    cl = run(
        [
            "git",
            "clone",
            "--depth=20",
            "--branch",
            default,
            f"https://github.com/{OWNER}/{name}.git",
            str(dest),
        ]
    )
    if cl.returncode != 0:
        # retry without branch pin
        cl = run(["git", "clone", "--depth=20", f"https://github.com/{OWNER}/{name}.git", str(dest)])
        if cl.returncode != 0:
            return {"name": name, "ok": False, "err": cl.stderr[:200]}
    run(["git", "checkout", "-B", BRANCH], cwd=dest)
    rec = dest / "APEX_RECOVERY.md"
    if rec.exists() and "mass recovery" in rec.read_text().lower():
        return {"name": name, "ok": True, "skipped": True, "reason": "already enrolled"}
    rec.write_text(
        f"""# APEX Mass Recovery (Full Estate)

**Repository:** `{OWNER}/{name}`  
**Identity:** APEX is the counter to canonical destruction  
**Law:** MAXIMUM_COHERENT_ADVANCE  
**Estate boundary:** ALL native active owned repos — not the 66 hire projection

## Dual-plane rule

1. **VERIFIED** — exact-head proven claims  
2. **IMPLEMENTED** — real code retained; never deleted to green a smaller harness  
3. **TARGET** — north-star architecture preserved  

Governance routes power. It does not amputate mechanisms.
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
                "program": "full-estate-mass-recovery",
                "dual_plane": True,
                "estate_boundary": "ALL_NATIVE_ACTIVE",
            }
        )
        planes = data.setdefault("planes", {})
        planes.setdefault("verified", list(data.get("capabilities") or []))
        impl = list(planes.get("implemented") or [])
        if "apex-mass-recovery-enrolled" not in impl:
            impl.append("apex-mass-recovery-enrolled")
        planes["implemented"] = impl
        caps = list(data.get("capabilities") or [])
        if "apex-mass-recovery-enrolled" not in caps:
            caps.append("apex-mass-recovery-enrolled")
        data["capabilities"] = caps
        cap.write_text(json.dumps(data, indent=2) + "\n")
    run(["git", "add", "-A"], cwd=dest)
    if not run(["git", "status", "--porcelain"], cwd=dest).stdout.strip():
        return {"name": name, "ok": True, "skipped": True, "reason": "no changes"}
    run(
        [
            "git",
            "commit",
            "-m",
            "APEX: full-estate dual-plane recovery enrollment\n\n"
            "Estate boundary is ALL native active repos — not the 66 hire projection.\n"
            "Identity: APEX is the counter to canonical destruction\n"
            "Law: MAXIMUM_COHERENT_ADVANCE\n",
        ],
        cwd=dest,
    )
    push = run(["git", "push", "-u", "origin", BRANCH], cwd=dest)
    if push.returncode != 0:
        # try force-with-lease only if our branch
        push = run(["git", "push", "-u", "origin", BRANCH, "--force-with-lease"], cwd=dest)
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
            default,
            "--title",
            "APEX: full-estate dual-plane recovery enrollment",
            "--body",
            "Full-estate mass recovery (not 66-limited). Dual-plane truth. APEX counters canonical destruction.",
        ],
        cwd=dest,
    )
    return {
        "name": name,
        "ok": pr.returncode == 0 or "already exists" in (pr.stderr or "").lower(),
        "pr": (pr.stdout or pr.stderr).strip()[:300],
        "default_branch": default,
    }


def main() -> int:
    names = json.loads(Path(sys.argv[1]).read_text())
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 50
    offset = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    batch = names[offset : offset + limit]
    work = Path(tempfile.mkdtemp(prefix="full-estate-dual-"))
    results = []
    for name in batch:
        print("===", name, flush=True)
        row = apply_one(name, work)
        results.append(row)
        print(row, flush=True)
    out = Path("receipts/mass_recovery/FULL_ESTATE_DUAL_PLANE_BATCH.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    # append if exists
    prev = []
    if out.exists():
        try:
            prev = json.loads(out.read_text())
            if not isinstance(prev, list):
                prev = []
        except Exception:
            prev = []
    prev.extend(results)
    out.write_text(json.dumps(prev, indent=2) + "\n")
    ok = sum(1 for r in results if r.get("ok"))
    print(f"batch_done ok={ok}/{len(results)} offset={offset} receipt={out}")
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
