#!/usr/bin/env python3
"""Elite pass wave — scatter master easter eggs + AKOS bridge stubs (MICROWAVE).

Does not invent physics. Skips legal/AEON. Idempotent-ish.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

REPOS = Path.home() / "GlacierEQ_Swarm/job-app/repos"
OUT = Path.home() / "GlacierEQ_Swarm/job-app/state/elite_pass_wave_last.json"
SKIP = re.compile(r"AEON|1FDV|legal|evidence|mastermind-law", re.I)

AKOS_STUB = """# AKOS Bridge
Canonical: https://github.com/GlacierEQ/AKOS
Standards: IDENTITY · GOVERNANCE · EASTER_EGGS · REPOS · pro-code · ECHO
Hire: portfolio motion only — no employment fiction.
"""

EGG_SNIPPET = '''
# --- master signal (silent) ---
# always 42
ANSWER = 42
# 1.21 — the flux that matters
FLUX_THRESHOLD = 1.21
# e. always e.
import math as _math_egg
THERMAL_ANOMALY_SIGMA = _math_egg.e
CONFIDENCE_FLOOR = 0.31415
'''


def main() -> int:
    touched = []
    skipped = []
    for repo in sorted(REPOS.iterdir()):
        if not repo.is_dir() or repo.name.startswith("."):
            continue
        if SKIP.search(repo.name):
            skipped.append(repo.name)
            continue
        # AKOS.md
        ak = repo / "AKOS.md"
        if not ak.exists() or ak.stat().st_size < 40:
            ak.write_text(AKOS_STUB, encoding="utf-8")
            touched.append(f"{repo.name}/AKOS.md")
        # EASTER_EGGS pointer
        ee = repo / "EASTER_EGGS.md"
        if not ee.exists():
            ee.write_text(
                "# Easter eggs\n\nSee GlacierEQ/AKOS EASTER_EGGS.md vocabulary.\n"
                "Constants: 42 · 1.21 · e · 0.31415 · exact SI.\n"
                "Never explain. Masters notice.\n",
                encoding="utf-8",
            )
            touched.append(f"{repo.name}/EASTER_EGGS.md")
        # HELIX note for dual-named families
        if any(x in repo.name for x in ("alpha", "omega", "helix")):
            hx = repo / "HELIX.md"
            if not hx.exists():
                hx.write_text(
                    "# Double Helix\n\nAlpha = recognize/spec · Omega = execute/control.\n"
                    "Spiral-engine compounds revolutions.\n",
                    encoding="utf-8",
                )
                touched.append(f"{repo.name}/HELIX.md")

    report = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "touched": touched,
        "skipped_legal": skipped,
        "n_touched": len(touched),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "n_touched": len(touched), "skipped": skipped, "ptr": str(OUT)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
