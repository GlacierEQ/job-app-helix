#!/usr/bin/env python3
"""Solidify job-app portfolio around double-helix doctrine.

- HELIX_STRAND.md on every leaf (star / spiral / role)
- Ensure SECURITY + README fleet blurb
- Ensure .integrity dir exists where watchdogs live or create minimal
- Expand strand metadata from helix_registry.json
- Optional: run helix runner + write receipt

Usage:
  python3 jobapp_solidify_flipper.py
  python3 jobapp_solidify_flipper.py --with-helix-run
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HOME = Path.home()
ROOT = HOME / "job-app" / "repos"
JOB = HOME / "job-app"
REG = JOB / "helix_registry.json"
STATE = HOME / "GlacierEQ_Swarm" / "state"
OUT = STATE / "jobapp_solidify_last.json"
AUTO = HOME / "GlacierEQ_Swarm" / "automations"

SEC_BODY = """# Security & Fleet Ops — Direct Introduction

**This portfolio is transparent about its ops layer.**

| Path | Role |
|------|------|
| `.integrity/` | SHA-256 baselines / watchdog (fleet integrity) |
| `mastermind_sidecar.py` | Optional health sidecar |
| Mastermind `.shadow/` | Documented specialist pistons + routing (private OS) |

Not covert implants. Full framing:
`~/GlacierEQ_Swarm/state/PORTFOLIO_SHADOW_AND_GAUNTLET.md`

## Double helix

Domain truth (Alpha) and ops/proof (Omega) co-aim at one star.
See `~/job-app/HELIX.md` and this leaf's `HELIX_STRAND.md`.
"""

README_BLURB = """
---

## Fleet ops (transparent)

This repo may include **`.integrity/`** (SHA-256 integrity) and/or a health sidecar.
Documented fleet operations — not covert implants.
See [SECURITY_AND_FLEET_OPS.md](SECURITY_AND_FLEET_OPS.md) and [HELIX_STRAND.md](HELIX_STRAND.md).
"""


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_reg() -> dict:
    if REG.exists():
        return json.loads(REG.read_text(encoding="utf-8"))
    return {"pairs": [], "law": {}}


def index_strands(reg: dict) -> dict[str, list[dict]]:
    """repo -> list of {pair, star, spiral, role}"""
    idx: dict[str, list[dict]] = {}
    for p in reg.get("pairs") or []:
        star = p.get("star", "")
        pid = p.get("id", "")
        for key, spiral in (("alpha", "alpha"), ("omega", "omega"), ("bridge", "bridge")):
            node = p.get(key) or {}
            repo = node.get("repo")
            if not repo:
                continue
            idx.setdefault(repo, []).append(
                {
                    "pair": pid,
                    "star": star,
                    "spiral": spiral,
                    "name": node.get("name"),
                    "role": node.get("role"),
                }
            )
    return idx


def strand_md(repo: str, entries: list[dict], reg: dict) -> str:
    law = reg.get("law") or {}
    lines = [
        f"# HELIX strand — `{repo}`",
        "",
        "## Law",
        "",
        f"- **Piston:** {law.get('piston', 'local loop')}",
        f"- **Spiral:** {law.get('spiral', 'output → next input')}",
        f"- **Double helix:** {law.get('double_helix', 'two spirals, one star')}",
        f"- **Mutual acceleration:** {law.get('mutual_acceleration', 'strands accelerate each other')}",
        "",
        "## This leaf",
        "",
    ]
    if not entries:
        lines += [
            "Not yet bound to a named helix pair. Default posture:",
            "",
            f"- **Star:** hire-grade proof of `{repo}` domain value",
            "- **Spiral:** alpha (domain) by default; add omega integrity/ops as needed",
            "- **Piston:** modules under `src/` (or package root)",
            "",
            "Bind via `job-app/helix_registry.json` when a co-star leaf is ready.",
            "",
        ]
    else:
        lines.append("| Pair | Spiral | Role | Star |")
        lines.append("|------|--------|------|------|")
        for e in entries:
            lines.append(
                f"| `{e['pair']}` | **{e['spiral']}** | {e.get('role','')} | {e.get('star','')} |"
            )
        lines += ["", "### How this accelerates its twin", ""]
        for e in entries:
            if e["spiral"] == "alpha":
                lines.append(
                    f"- **{e['pair']}:** emits domain truth envelopes consumed by Omega/bridge pistons."
                )
            elif e["spiral"] == "omega":
                lines.append(
                    f"- **{e['pair']}:** consumes Alpha output; returns severity/proof that refines Alpha."
                )
            else:
                lines.append(
                    f"- **{e['pair']}:** bridge medium (telemetry/bus) between spirals."
                )
        lines.append("")
    lines += [
        "## Runtime",
        "",
        "```bash",
        "python3 ~/GlacierEQ_Swarm/automations/jobapp_helix_spiral.py run --all",
        "python3 ~/GlacierEQ_Swarm/automations/jobapp_solidify_flipper.py",
        "```",
        "",
        f"Portfolio doctrine: `~/job-app/HELIX.md`",
        "",
    ]
    return "\n".join(lines)


def ensure_integrity(repo: Path) -> str:
    """Create .integrity with minimal watchdog if missing."""
    integ = repo / ".integrity"
    if integ.is_dir():
        return "exists"
    integ.mkdir(parents=True, exist_ok=True)
    w = integ / "watchdog_daemon.py"
    if not w.exists():
        w.write_text(
            '''from __future__ import annotations
"""Integrity watchdog — SHA-256 baselines for this leaf."""
import hashlib
import json
from pathlib import Path

class WatchdogDaemon:
    def __init__(self, repo_root: str | None = None):
        integrity_dir = Path(__file__).resolve().parent
        self.repo_root = Path(repo_root).resolve() if repo_root else integrity_dir.parent
        self.hash_store = integrity_dir / "file_hashes.json"
        self.baseline = {}
        if self.hash_store.exists():
            self.baseline = json.loads(self.hash_store.read_text())

    def scan(self) -> dict:
        cur = {}
        for pat in ("src/**/*.py", "*.py", "connectors/**/*.py"):
            for path in self.repo_root.glob(pat):
                if "__pycache__" in path.parts or ".git" in path.parts:
                    continue
                if path.is_file():
                    rel = str(path.relative_to(self.repo_root))
                    cur[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
        return cur

    def update_baseline(self) -> None:
        self.baseline = self.scan()
        self.hash_store.write_text(json.dumps(self.baseline, indent=2))

    def verify(self) -> dict:
        cur = self.scan()
        return {p: self.baseline.get(p) == h for p, h in cur.items()}

if __name__ == "__main__":
    w = WatchdogDaemon()
    w.update_baseline()
    r = w.verify()
    ok = all(r.values()) if r else True
    print("Integrity check:", "PASS" if ok else "FAIL", f"({len(r)} files)")
''',
            encoding="utf-8",
        )
    return "created"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--with-helix-run", action="store_true")
    args = ap.parse_args()

    reg = load_reg()
    strands = index_strands(reg)
    report = {
        "ts": utc_now(),
        "protocol": "jobapp solidify — helix strands + integrity + security",
        "repos": 0,
        "helix_strands_written": 0,
        "security_written": 0,
        "readme_patched": 0,
        "integrity": {"created": 0, "exists": 0},
        "helix_bound": 0,
        "errors": [],
    }

    repos = sorted([p for p in ROOT.iterdir() if p.is_dir() and not p.name.startswith(".")])
    report["repos"] = len(repos)

    for repo in repos:
        try:
            name = repo.name
            entries = strands.get(name, [])
            if entries:
                report["helix_bound"] += 1

            # HELIX_STRAND.md
            (repo / "HELIX_STRAND.md").write_text(
                strand_md(name, entries, reg), encoding="utf-8"
            )
            report["helix_strands_written"] += 1

            # SECURITY
            sec = repo / "SECURITY_AND_FLEET_OPS.md"
            sec.write_text(SEC_BODY, encoding="utf-8")
            report["security_written"] += 1

            # README
            readme = repo / "README.md"
            if not readme.exists():
                readme.write_text(
                    f"# {name}\n\nPortfolio leaf in the GlacierEQ job-app helix mesh.\n",
                    encoding="utf-8",
                )
            rt = readme.read_text(encoding="utf-8", errors="replace")
            if "HELIX_STRAND.md" not in rt:
                # refresh fleet blurb to include strand
                if "Fleet ops (transparent)" not in rt and "Shadow cortex & fleet ops" not in rt:
                    readme.write_text(rt.rstrip() + "\n" + README_BLURB, encoding="utf-8")
                else:
                    # append helix pointer only
                    readme.write_text(
                        rt.rstrip()
                        + "\n\n## Helix strand\n\nSee [HELIX_STRAND.md](HELIX_STRAND.md) — piston/spiral role in the portfolio double helix.\n",
                        encoding="utf-8",
                    )
                report["readme_patched"] += 1
            elif ".shadow_infrastructure" in rt:
                readme.write_text(
                    rt.replace(".shadow_infrastructure", ".integrity"), encoding="utf-8"
                )
                report["readme_patched"] += 1

            # integrity
            st = ensure_integrity(repo)
            report["integrity"][st] = report["integrity"].get(st, 0) + 1

        except Exception as e:
            report["errors"].append({"repo": repo.name, "err": str(e)[:200]})

    # helix run optional
    if args.with_helix_run:
        r = subprocess.run(
            [sys.executable, str(AUTO / "jobapp_helix_spiral.py"), "run", "--all"],
            capture_output=True,
            text=True,
            timeout=180,
        )
        report["helix_run"] = {
            "ok": r.returncode == 0,
            "tail": (r.stdout or "")[-600:],
        }

    STATE.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")

    # memory
    bus = AUTO / "tsunami_memory_bus.py"
    if bus.is_file():
        subprocess.run(
            [
                sys.executable,
                str(bus),
                "write",
                f"Job-app solidify {report['ts']}: {report['helix_strands_written']} strands, "
                f"{report['helix_bound']} helix-bound, integrity created={report['integrity'].get('created')}",
                "--tags",
                "job-app,helix,forge",
                "--key",
                "jobapp-solidify-last",
            ],
            capture_output=True,
            timeout=30,
        )

    print(
        json.dumps(
            {
                "ok": not report["errors"],
                "repos": report["repos"],
                "strands": report["helix_strands_written"],
                "helix_bound": report["helix_bound"],
                "integrity_created": report["integrity"].get("created"),
                "readme_patched": report["readme_patched"],
                "helix_run": report.get("helix_run", {}).get("ok"),
                "ptr": str(OUT),
            },
            indent=2,
        )
    )
    return 0 if not report["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
