#!/usr/bin/env python3
"""Proof: distinct BrainSync expert-skill domains remain discoverable.

DONE when skill domains are present in memory and/or SKILL.md files, and the
index audit passes without requiring title-duplicate rows in latestEntries.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
AUDIT = REPO / "helix" / "automations" / "brainsync_index_skills.py"


def main() -> int:
    r = subprocess.run(
        [sys.executable, str(AUDIT), "audit"],
        cwd=str(REPO),
        capture_output=True,
        text=True,
    )
    sys.stdout.write(r.stdout)
    if r.stderr:
        sys.stderr.write(r.stderr)
    if r.returncode != 0:
        print("PROOF_FAIL brainsync_skill_index", file=sys.stderr)
        return 1

    # Repair must pin domains into latestEntries (strict preview integrity).
    r2 = subprocess.run(
        [sys.executable, str(AUDIT), "repair", "--dry-run"],
        cwd=str(REPO),
        capture_output=True,
        text=True,
    )
    sys.stdout.write(r2.stdout)
    if r2.returncode != 0:
        print("PROOF_FAIL repair dry-run", file=sys.stderr)
        return 1

    # Strict check on repaired shape via in-memory expectation: re-run repair
    # to disk is optional; verify catalog domains include expected four.
    r3 = subprocess.run(
        [sys.executable, str(AUDIT), "catalog"],
        cwd=str(REPO),
        capture_output=True,
        text=True,
    )
    if r3.returncode != 0:
        sys.stderr.write(r3.stderr)
        print("PROOF_FAIL catalog", file=sys.stderr)
        return 1
    text = r3.stdout
    for domain in ("config", "project", "python", "typescript"):
        if f'"{domain}"' not in text:
            print(f"PROOF_FAIL missing domain in catalog: {domain}", file=sys.stderr)
            return 1

    print("PROOF_OK brainsync_skill_index domains preserved")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
